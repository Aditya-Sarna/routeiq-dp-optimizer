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

    if not (os.path.isfile(CPP_BINARY) and os.access(CPP_BINARY, os.X_OK)):
        raise HTTPException(status_code=500, detail="C++ solver binary not found. Compile cpp_engine first.")

    # Build distance matrix
    dist = [[0.0] * n for _ in range(n)]
    for i in range(n):
        for j in range(n):
            if i == j:
                continue
            if req.mode == "haversine":
                if locations[i].get("lat") is None or locations[j].get("lat") is None:
                    raise HTTPException(status_code=400, detail="haversine mode requires lat/lng on every location")
                dist[i][j] = haversine(locations[i]["lat"], locations[i]["lng"], locations[j]["lat"], locations[j]["lng"])
            else:
                dist[i][j] = euclidean(locations[i]["x"], locations[i]["y"], locations[j]["x"], locations[j]["y"])

    # Format input for C++ solver
    input_lines = [str(n)]
    for row in dist:
        input_lines.append(" ".join(f"{v:.6f}" for v in row))
    input_str = "\n".join(input_lines) + "\n"

    t0 = time.perf_counter()
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

    elapsed_ms = (time.perf_counter() - t0) * 1000.0

    if result.returncode != 0:
        raise HTTPException(status_code=500, detail=f"Solver failed: {result.stderr.strip() or 'unknown error'}")

    lines = result.stdout.strip().split("\n")
    if not lines or lines[0] == "NO_ROUTE":
        raise HTTPException(status_code=400, detail="No valid route found")

    total_cost = float(lines[0])
    path_indices = list(map(int, lines[1].split())) if len(lines) > 1 else [0]

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

    # DP metrics
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
