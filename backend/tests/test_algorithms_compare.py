"""
Backend tests for new TSP algorithm endpoints:
- POST /api/optimize with algorithm in {held-karp, backtracking, greedy}
- POST /api/compare
- GET  /api/algorithms
"""
import math
import os
import pytest
import requests

BASE_URL = os.environ.get(
    "REACT_APP_BACKEND_URL",
    "https://optimize-routes-1.preview.emergentagent.com",
).rstrip("/")
API = f"{BASE_URL}/api"


@pytest.fixture(scope="module")
def session():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


# Helpers ────────────────────────────────────────────────────────────────────
def _euclid(a, b):
    return math.sqrt((a["x"] - b["x"]) ** 2 + (a["y"] - b["y"]) ** 2)


SAMPLE_5 = [
    {"x": 0, "y": 0, "name": "Depot"},
    {"x": 10, "y": 5, "name": "A"},
    {"x": 7, "y": 12, "name": "B"},
    {"x": -3, "y": 8, "name": "C"},
    {"x": 4, "y": -6, "name": "D"},
]

MANHATTAN_8 = [
    {"x": 0, "y": 0, "lat": 40.7033, "lng": -73.9881, "name": "Depot · DUMBO"},
    {"x": 0, "y": 0, "lat": 40.7074, "lng": -74.0113, "name": "Wall Street"},
    {"x": 0, "y": 0, "lat": 40.7233, "lng": -74.0030, "name": "SoHo"},
    {"x": 0, "y": 0, "lat": 40.7580, "lng": -73.9855, "name": "Times Square"},
    {"x": 0, "y": 0, "lat": 40.7829, "lng": -73.9654, "name": "Central Park"},
    {"x": 0, "y": 0, "lat": 40.7489, "lng": -73.9680, "name": "UN Plaza"},
    {"x": 0, "y": 0, "lat": 40.7466, "lng": -74.0011, "name": "Chelsea"},
    {"x": 0, "y": 0, "lat": 40.8116, "lng": -73.9465, "name": "Harlem"},
]


# ─── /api/algorithms ─────────────────────────────────────────────────────────
class TestAlgorithmsMeta:
    def test_algorithms_metadata(self, session):
        r = session.get(f"{API}/algorithms")
        assert r.status_code == 200
        data = r.json()
        assert "algorithms" in data
        algos = data["algorithms"]
        for key in ("held-karp", "backtracking", "greedy"):
            assert key in algos, f"missing algorithm {key}"
            for f in ("label", "complexity", "space", "optimal", "engine"):
                assert f in algos[key], f"{key} missing meta field {f}"
        assert algos["held-karp"]["complexity"] == "O(n² · 2ⁿ)"
        assert algos["backtracking"]["complexity"] == "O(n!)"
        assert algos["greedy"]["complexity"] == "O(n²)"
        assert algos["held-karp"]["optimal"] is True
        assert algos["backtracking"]["optimal"] is True
        assert algos["greedy"]["optimal"] is False


# ─── /api/optimize per algorithm ─────────────────────────────────────────────
class TestOptimizePerAlgorithm:
    def _validate_tour(self, d, n):
        assert d["n_locations"] == n
        assert d["path_indices"][0] == 0
        assert d["path_indices"][-1] == 0
        assert sorted(d["path_indices"][:-1]) == list(range(n))
        # Check segment costs are consistent with total_cost
        total = sum(s["distance"] for s in d["segments"])
        assert abs(d["total_cost"] - total) < 1e-2

    def test_held_karp_default(self, session):
        # No algorithm field — should default to held-karp
        r = session.post(f"{API}/optimize", json={"locations": SAMPLE_5, "mode": "euclidean"})
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["algorithm"] == "held-karp"
        assert d["algorithm_meta"]["optimal"] is True
        assert d["algorithm_meta"]["complexity"] == "O(n² · 2ⁿ)"
        self._validate_tour(d, 5)

    def test_backtracking_correct(self, session):
        r = session.post(f"{API}/optimize", json={
            "locations": SAMPLE_5, "mode": "euclidean", "algorithm": "backtracking"
        })
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["algorithm"] == "backtracking"
        assert d["algorithm_meta"]["complexity"] == "O(n!)"
        assert d["algorithm_meta"]["optimal"] is True
        self._validate_tour(d, 5)

    def test_greedy_returns(self, session):
        r = session.post(f"{API}/optimize", json={
            "locations": SAMPLE_5, "mode": "euclidean", "algorithm": "greedy"
        })
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["algorithm"] == "greedy"
        assert d["algorithm_meta"]["complexity"] == "O(n²)"
        assert d["algorithm_meta"]["optimal"] is False
        self._validate_tour(d, 5)

    def test_held_karp_and_backtracking_match(self, session):
        # On small n, both exact algorithms should yield the same total_cost.
        r1 = session.post(f"{API}/optimize", json={
            "locations": SAMPLE_5, "mode": "euclidean", "algorithm": "held-karp"
        })
        r2 = session.post(f"{API}/optimize", json={
            "locations": SAMPLE_5, "mode": "euclidean", "algorithm": "backtracking"
        })
        assert r1.status_code == 200 and r2.status_code == 200
        assert abs(r1.json()["total_cost"] - r2.json()["total_cost"]) < 1e-2

    def test_greedy_geq_optimal(self, session):
        # Greedy may be sub-optimal but must be >= optimal cost.
        r_opt = session.post(f"{API}/optimize", json={
            "locations": MANHATTAN_8, "mode": "haversine", "algorithm": "held-karp"
        })
        r_g = session.post(f"{API}/optimize", json={
            "locations": MANHATTAN_8, "mode": "haversine", "algorithm": "greedy"
        })
        assert r_opt.status_code == 200 and r_g.status_code == 200
        opt = r_opt.json()["total_cost"]
        gre = r_g.json()["total_cost"]
        assert gre >= opt - 1e-6
        # Sanity: Manhattan-8 reference values from agent: greedy≈30.01, hk≈27.69
        assert 5.0 < opt < 100.0
        assert 5.0 < gre < 200.0

    def test_invalid_algorithm_returns_422(self, session):
        r = session.post(f"{API}/optimize", json={
            "locations": SAMPLE_5, "mode": "euclidean", "algorithm": "ant-colony"
        })
        assert r.status_code == 422, r.text


# ─── /api/compare ────────────────────────────────────────────────────────────
class TestCompare:
    def test_compare_basic_5(self, session):
        r = session.post(f"{API}/compare", json={
            "locations": SAMPLE_5, "mode": "euclidean"
        })
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["n_locations"] == 5
        assert d["mode"] == "euclidean"
        assert isinstance(d["runs"], list) and len(d["runs"]) == 3
        algs = [r["algorithm"] for r in d["runs"]]
        assert algs == ["held-karp", "backtracking", "greedy"]

        for run in d["runs"]:
            for k in ("algorithm", "meta", "total_cost", "path_indices",
                      "segments", "elapsed_ms", "gap_pct", "is_optimal", "error"):
                assert k in run, f"run missing key {k}"
            assert run["error"] is None
            assert run["total_cost"] is not None
            assert run["path_indices"][0] == 0 == run["path_indices"][-1]
            assert sorted(run["path_indices"][:-1]) == [0, 1, 2, 3, 4]

        # held-karp & backtracking are both exact algorithms — costs should
        # agree within floating-point tolerance. (Strict is_optimal flag may
        # flip due to C++ binary 2-decimal truncation; we allow a tiny gap.)
        by = {r["algorithm"]: r for r in d["runs"]}
        assert abs(by["held-karp"]["total_cost"] - by["backtracking"]["total_cost"]) < 0.05
        assert abs(by["held-karp"]["gap_pct"]) < 0.01
        assert abs(by["backtracking"]["gap_pct"]) < 0.01
        assert by["greedy"]["gap_pct"] is not None
        assert by["greedy"]["gap_pct"] >= -1e-6
        assert d["optimum_cost"] is not None
        assert abs(d["optimum_cost"] - by["held-karp"]["total_cost"]) < 1e-2

    def test_compare_manhattan_8_haversine(self, session):
        r = session.post(f"{API}/compare", json={
            "locations": MANHATTAN_8, "mode": "haversine"
        })
        assert r.status_code == 200, r.text
        d = r.json()
        by = {r["algorithm"]: r for r in d["runs"]}
        # Greedy may differ; exact algos should match
        assert abs(by["held-karp"]["total_cost"] - by["backtracking"]["total_cost"]) < 1e-2
        assert by["greedy"]["total_cost"] >= by["held-karp"]["total_cost"] - 1e-6
        # gap_pct sanity
        assert by["greedy"]["gap_pct"] >= -1e-6

    def test_compare_max_13_locations_rejected(self, session):
        # /api/compare is capped at 12
        locs = [{"x": float(i), "y": float(i * 2)} for i in range(13)]
        r = session.post(f"{API}/compare", json={"locations": locs, "mode": "euclidean"})
        assert r.status_code == 422, r.text

    def test_compare_min_validation(self, session):
        r = session.post(f"{API}/compare", json={
            "locations": [{"x": 0, "y": 0}], "mode": "euclidean"
        })
        assert r.status_code == 422
