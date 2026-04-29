"""
RouteIQ — FastAPI backend that bridges the C++ Held-Karp DP TSP solver
with the React frontend.
"""

from fastapi import FastAPI, APIRouter, HTTPException, Query
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, Field
from typing import List, Literal, Optional
from pathlib import Path
import os
import math
import subprocess
import logging
import time
import asyncio
import httpx

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

# MongoDB (kept for future persistence — runs are saved as history)
mongo_url = os.environ["MONGO_URL"]
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ["DB_NAME"]]

# Path to compiled C++ Held-Karp binary (compiled at /app/backend/route_optimizer)
CPP_BINARY = str(ROOT_DIR / "route_optimizer")

app = FastAPI(title="RouteIQ DP Optimizer API")
api_router = APIRouter(prefix="/api")


# ─────────────────── Models ───────────────────
class Location(BaseModel):
    x: float
    y: float
    name: Optional[str] = None
    lat: Optional[float] = None
    lng: Optional[float] = None


class OptimizeRequest(BaseModel):
    locations: List[Location] = Field(..., min_length=2, max_length=15)
    mode: Literal["euclidean", "haversine"] = "euclidean"
    algorithm: Literal["held-karp", "backtracking", "greedy"] = "held-karp"


class Segment(BaseModel):
    from_idx: int = Field(..., alias="from")
    to_idx: int = Field(..., alias="to")
    distance: float

    class Config:
        populate_by_name = True


class OptimizeResponse(BaseModel):
    total_cost: float
    route: List[dict]
    segments: List[dict]
    path_indices: List[int]
    n_locations: int
    elapsed_ms: float
    states_explored: int
    subproblems: int
    algorithm: str = "held-karp"
    algorithm_meta: dict | None = None


# ─────────────────── Helpers ───────────────────
def haversine(lat1, lon1, lat2, lon2):
    R = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlmb = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlmb / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))


def euclidean(x1, y1, x2, y2):
    return math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)


# ─────────────────── Pure-Python TSP solvers ───────────────────
INF = float("inf")


def solve_backtracking(dist: List[List[float]], n: int):
    """Exact brute-force backtracking with branch-and-bound. O(n!) worst case."""
    visited = [False] * n
    visited[0] = True
    best = {"cost": INF, "path": []}
    cur_path = [0]

    def dfs(u: int, depth: int, cost_so_far: float):
        if cost_so_far >= best["cost"]:
            return  # prune
        if depth == n:
            total = cost_so_far + dist[u][0]
            if total < best["cost"]:
                best["cost"] = total
                best["path"] = cur_path + [0]
            return
        for v in range(1, n):
            if visited[v]:
                continue
            visited[v] = True
            cur_path.append(v)
            dfs(v, depth + 1, cost_so_far + dist[u][v])
            cur_path.pop()
            visited[v] = False

    dfs(0, 1, 0.0)
    if best["cost"] == INF:
        return None
    return best["cost"], best["path"]


def solve_greedy(dist: List[List[float]], n: int):
    """Greedy nearest-neighbor heuristic. O(n²). NOT guaranteed optimal."""
    visited = [False] * n
    visited[0] = True
    path = [0]
    cur = 0
    total = 0.0
    for _ in range(n - 1):
        best_v, best_d = -1, INF
        for v in range(n):
            if not visited[v] and dist[cur][v] < best_d:
                best_d, best_v = dist[cur][v], v
        if best_v == -1:
            return None
        visited[best_v] = True
        path.append(best_v)
        total += best_d
        cur = best_v
    total += dist[cur][0]
    path.append(0)
    return total, path


def solve_held_karp_via_cpp(dist: List[List[float]], n: int):
    """Calls the compiled C++ Held-Karp binary. Returns (cost, path) or None."""
    if not (os.path.isfile(CPP_BINARY) and os.access(CPP_BINARY, os.X_OK)):
        raise HTTPException(status_code=500, detail="C++ solver binary not found.")
    input_lines = [str(n)]
    for row in dist:
        input_lines.append(" ".join(f"{v:.6f}" for v in row))
    input_str = "\n".join(input_lines) + "\n"

    try:
        result = subprocess.run(
            [CPP_BINARY],
            input=input_str,
            capture_output=True,
            text=True,
            timeout=30,
        )
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=504, detail="Solver timed out")

    if result.returncode != 0:
        raise HTTPException(
            status_code=500,
            detail=f"Solver failed: {result.stderr.strip() or 'unknown error'}",
        )

    lines = result.stdout.strip().split("\n")
    if not lines or lines[0] == "NO_ROUTE":
        return None
    cost = float(lines[0])
    path = list(map(int, lines[1].split())) if len(lines) > 1 else [0]
    return cost, path


ALGO_META = {
    "held-karp": {
        "label": "Held-Karp (DP)",
        "complexity": "O(n² · 2ⁿ)",
        "space": "O(n · 2ⁿ)",
        "optimal": True,
        "engine": "C++17 · -O2",
    },
    "backtracking": {
        "label": "Backtracking",
        "complexity": "O(n!)",
        "space": "O(n)",
        "optimal": True,
        "engine": "Python (branch-and-bound)",
    },
    "greedy": {
        "label": "Nearest Neighbor",
        "complexity": "O(n²)",
        "space": "O(n)",
        "optimal": False,
        "engine": "Python",
    },
}


def build_distance_matrix(locations: list, mode: str) -> List[List[float]]:
    n = len(locations)
    dist = [[0.0] * n for _ in range(n)]
    for i in range(n):
        for j in range(n):
            if i == j:
                continue
            if mode == "haversine":
                if locations[i].get("lat") is None or locations[j].get("lat") is None:
                    raise HTTPException(
                        status_code=400,
                        detail="haversine mode requires lat/lng on every location",
                    )
                dist[i][j] = haversine(
                    locations[i]["lat"], locations[i]["lng"],
                    locations[j]["lat"], locations[j]["lng"],
                )
            else:
                dist[i][j] = euclidean(
                    locations[i]["x"], locations[i]["y"],
                    locations[j]["x"], locations[j]["y"],
                )
    return dist


def run_algorithm(name: str, dist: List[List[float]], n: int):
    if name == "held-karp":
        return solve_held_karp_via_cpp(dist, n)
    if name == "backtracking":
        return solve_backtracking(dist, n)
    if name == "greedy":
        return solve_greedy(dist, n)
    raise HTTPException(status_code=400, detail=f"Unknown algorithm: {name}")


# ─────────────────── Routes ───────────────────
@api_router.get("/")
async def root():
    return {
        "service": "RouteIQ DP Optimizer",
        "algorithm": "Held-Karp Dynamic Programming",
        "complexity": "O(n^2 * 2^n)",
    }


@api_router.get("/health")
async def health():
    cpp_exists = os.path.isfile(CPP_BINARY) and os.access(CPP_BINARY, os.X_OK)
    return {
        "status": "ok",
        "cpp_solver": "available" if cpp_exists else "missing",
        "binary_path": CPP_BINARY,
    }


@api_router.post("/optimize", response_model=OptimizeResponse)
async def optimize(req: OptimizeRequest):
    locations = [loc.model_dump() for loc in req.locations]
    n = len(locations)

    dist = build_distance_matrix(locations, req.mode)

    t0 = time.perf_counter()
    result_pair = run_algorithm(req.algorithm, dist, n)
    elapsed_ms = (time.perf_counter() - t0) * 1000.0

    if result_pair is None:
        raise HTTPException(status_code=400, detail="No valid route found")

    total_cost, path_indices = result_pair

    # Build ordered route
    route = []
    for idx in path_indices:
        loc = dict(locations[idx])
        loc["index"] = idx
        route.append(loc)

    # Per-segment distances
    segments = []
    for k in range(len(path_indices) - 1):
        i, j = path_indices[k], path_indices[k + 1]
        segments.append({"from": i, "to": j, "distance": round(dist[i][j], 4)})

    # DP metrics — kept for backward compat (only meaningful for held-karp)
    states_explored = (1 << n)
    subproblems = n * states_explored

    response = {
        "total_cost": round(total_cost, 4),
        "route": route,
        "segments": segments,
        "path_indices": path_indices,
        "n_locations": n,
        "elapsed_ms": round(elapsed_ms, 3),
        "states_explored": states_explored,
        "subproblems": subproblems,
        "algorithm": req.algorithm,
        "algorithm_meta": ALGO_META[req.algorithm],
    }

    # Persist run history (best-effort)
    try:
        await db.optimizations.insert_one({
            **response,
            "mode": req.mode,
            "input_locations": locations,
        })
    except Exception as e:
        logger.warning(f"Failed to persist optimization: {e}")

    return response


class CompareRequest(BaseModel):
    locations: List[Location] = Field(..., min_length=2, max_length=12)
    mode: Literal["euclidean", "haversine"] = "euclidean"


@api_router.post("/compare")
async def compare(req: CompareRequest):
    """Run all three TSP algorithms on the same input and return a comparison report."""
    locations = [loc.model_dump() for loc in req.locations]
    n = len(locations)
    dist = build_distance_matrix(locations, req.mode)

    runs = []
    for algo in ("held-karp", "backtracking", "greedy"):
        t0 = time.perf_counter()
        try:
            pair = run_algorithm(algo, dist, n)
        except HTTPException as e:
            runs.append({
                "algorithm": algo,
                "meta": ALGO_META[algo],
                "error": e.detail,
                "elapsed_ms": None,
                "total_cost": None,
                "path_indices": None,
                "segments": None,
            })
            continue
        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        if pair is None:
            runs.append({
                "algorithm": algo,
                "meta": ALGO_META[algo],
                "error": "No valid route",
                "elapsed_ms": round(elapsed_ms, 3),
                "total_cost": None,
                "path_indices": None,
                "segments": None,
            })
            continue
        cost, path = pair
        segments = [
            {"from": path[k], "to": path[k + 1], "distance": round(dist[path[k]][path[k + 1]], 4)}
            for k in range(len(path) - 1)
        ]
        runs.append({
            "algorithm": algo,
            "meta": ALGO_META[algo],
            "total_cost": round(cost, 4),
            "path_indices": path,
            "segments": segments,
            "elapsed_ms": round(elapsed_ms, 3),
            "error": None,
        })

    # Determine the optimum cost (any "optimal:true" algorithm that succeeded)
    optimum = None
    for r in runs:
        if r.get("error") is None and r["meta"]["optimal"]:
            if optimum is None or r["total_cost"] < optimum:
                optimum = r["total_cost"]

    # Tag each run with optimality gap
    for r in runs:
        if r.get("error") or optimum is None or r["total_cost"] is None:
            r["gap_pct"] = None
            r["is_optimal"] = None
        else:
            r["gap_pct"] = round(((r["total_cost"] - optimum) / optimum) * 100.0, 3) if optimum > 0 else 0.0
            r["is_optimal"] = abs(r["total_cost"] - optimum) < 1e-6

    return {
        "n_locations": n,
        "mode": req.mode,
        "optimum_cost": optimum,
        "runs": runs,
    }


@api_router.get("/algorithms")
async def algorithms():
    """Static metadata about available algorithms."""
    return {"algorithms": ALGO_META}


@api_router.get("/history")
async def history(limit: int = 20):
    docs = await db.optimizations.find({}, {"_id": 0}).sort("_id", -1).to_list(limit)
    return docs


# ─────────────────── Geocoder (Nominatim proxy) ───────────────────
# Tiny in-memory cache + simple rate-limit guard. Nominatim's usage policy:
#   - max 1 req/sec
#   - identifying User-Agent required
NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
NOMINATIM_UA = "RouteIQ/1.0 (held-karp-tsp-demo; contact via emergent.sh)"
_geocode_cache: dict = {}
_geocode_lock = asyncio.Lock()
_geocode_last_call = {"t": 0.0}


@api_router.get("/geocode")
async def geocode(
    q: str = Query(..., min_length=2, max_length=120, description="Place name to look up"),
    limit: int = Query(6, ge=1, le=10),
):
    key = f"{q.strip().lower()}::{limit}"
    if key in _geocode_cache:
        return _geocode_cache[key]

    # Throttle to ≤ 1 request / second across the whole process
    async with _geocode_lock:
        now = time.time()
        wait = 1.05 - (now - _geocode_last_call["t"])
        if wait > 0:
            await asyncio.sleep(wait)
        _geocode_last_call["t"] = time.time()

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                r = await client.get(
                    NOMINATIM_URL,
                    params={
                        "q": q,
                        "format": "jsonv2",
                        "addressdetails": 1,
                        "limit": limit,
                    },
                    headers={
                        "User-Agent": NOMINATIM_UA,
                        "Accept-Language": "en",
                    },
                )
                r.raise_for_status()
                data = r.json()
        except httpx.HTTPError as e:
            logger.warning(f"Nominatim error: {e}")
            raise HTTPException(status_code=502, detail="Geocoder upstream error")

    results = []
    for item in data:
        try:
            lat = float(item.get("lat"))
            lon = float(item.get("lon"))
        except (TypeError, ValueError):
            continue
        addr = item.get("address") or {}
        display_name = item.get("display_name", "") or ""
        primary = item.get("name") or display_name.split(",")[0].strip()
        # Build a concise "Place · Region · Country" label
        region = (
            addr.get("city")
            or addr.get("town")
            or addr.get("village")
            or addr.get("suburb")
            or addr.get("state")
            or addr.get("county")
            or ""
        )
        country = addr.get("country") or ""
        short_parts = [primary]
        if region and region.lower() != primary.lower():
            short_parts.append(region)
        if country:
            short_parts.append(country)
        results.append({
            "name": primary[:60] or display_name[:60],
            "label": " · ".join(short_parts)[:90],
            "display_name": display_name,
            "country": country,
            "lat": lat,
            "lng": lon,
            "type": item.get("type") or item.get("class") or "place",
            "importance": item.get("importance"),
        })

    payload = {"query": q, "results": results}
    _geocode_cache[key] = payload
    # Cap cache size
    if len(_geocode_cache) > 500:
        _geocode_cache.pop(next(iter(_geocode_cache)))
    return payload


app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get("CORS_ORIGINS", "*").split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("routeiq")


@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
