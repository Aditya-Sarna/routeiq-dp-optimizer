"""
Backend tests for RouteIQ DP Optimizer API
Tests health, root, optimize (validation + correctness), history endpoints.
"""
import math
import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://optimize-routes-1.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"


@pytest.fixture(scope="module")
def session():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


# ─── Health & root ─────────────────────────────
class TestMeta:
    def test_root(self, session):
        r = session.get(f"{API}/")
        assert r.status_code == 200
        data = r.json()
        assert data["service"] == "RouteIQ DP Optimizer"
        assert "Held-Karp" in data["algorithm"]
        assert data["complexity"] == "O(n^2 * 2^n)"

    def test_health(self, session):
        r = session.get(f"{API}/health")
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "ok"
        assert data["cpp_solver"] == "available", f"Got: {data}"


# ─── /api/optimize correctness ─────────────────
class TestOptimize:
    def _euclid(self, a, b):
        return math.sqrt((a["x"] - b["x"]) ** 2 + (a["y"] - b["y"]) ** 2)

    def test_optimize_5_locations(self, session):
        locs = [
            {"x": 0, "y": 0, "name": "Depot"},
            {"x": 10, "y": 5, "name": "A"},
            {"x": 7, "y": 12, "name": "B"},
            {"x": -3, "y": 8, "name": "C"},
            {"x": 4, "y": -6, "name": "D"},
        ]
        r = session.post(f"{API}/optimize", json={"locations": locs, "mode": "euclidean"})
        assert r.status_code == 200, r.text
        d = r.json()

        # required keys
        for k in ["total_cost", "route", "segments", "path_indices",
                  "n_locations", "elapsed_ms", "states_explored", "subproblems"]:
            assert k in d, f"Missing key {k}"

        assert d["n_locations"] == 5
        # path_indices length & depot start/end
        assert len(d["path_indices"]) == 6
        assert d["path_indices"][0] == 0
        assert d["path_indices"][-1] == 0
        # all stops visited
        assert sorted(d["path_indices"][:-1]) == [0, 1, 2, 3, 4]

        # segment distance verification
        total = 0.0
        for seg in d["segments"]:
            i, j = seg["from"], seg["to"]
            expected = self._euclid(locs[i], locs[j])
            assert abs(seg["distance"] - expected) < 1e-2, f"seg {i}->{j} mismatch"
            total += seg["distance"]
        assert abs(d["total_cost"] - total) < 1e-2

        # DP metrics
        assert d["states_explored"] == (1 << 5)
        assert d["subproblems"] == 5 * (1 << 5)

    def test_optimize_min_validation(self, session):
        r = session.post(f"{API}/optimize", json={"locations": [{"x": 0, "y": 0}], "mode": "euclidean"})
        assert r.status_code == 422

    def test_optimize_max_validation(self, session):
        locs = [{"x": float(i), "y": float(i * 2)} for i in range(16)]
        r = session.post(f"{API}/optimize", json={"locations": locs, "mode": "euclidean"})
        assert r.status_code == 422

    def test_optimize_haversine_missing_latlng(self, session):
        locs = [{"x": 0, "y": 0}, {"x": 1, "y": 1}, {"x": 2, "y": 2}]
        r = session.post(f"{API}/optimize", json={"locations": locs, "mode": "haversine"})
        assert r.status_code == 400
        assert "haversine" in r.json().get("detail", "").lower()

    def test_optimize_haversine_full(self, session):
        # Delhi NCR rough coords
        locs = [
            {"x": 0, "y": 0, "lat": 28.6139, "lng": 77.2090, "name": "Delhi"},
            {"x": 1, "y": 1, "lat": 28.4595, "lng": 77.0266, "name": "Gurugram"},
            {"x": 2, "y": 2, "lat": 28.5355, "lng": 77.3910, "name": "Noida"},
            {"x": 3, "y": 3, "lat": 28.4089, "lng": 77.3178, "name": "Faridabad"},
        ]
        r = session.post(f"{API}/optimize", json={"locations": locs, "mode": "haversine"})
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["n_locations"] == 4
        assert d["path_indices"][0] == 0 == d["path_indices"][-1]
        assert d["total_cost"] > 0

    def test_optimize_2_locations(self, session):
        locs = [{"x": 0, "y": 0}, {"x": 3, "y": 4}]
        r = session.post(f"{API}/optimize", json={"locations": locs, "mode": "euclidean"})
        assert r.status_code == 200
        d = r.json()
        # 0 -> 1 -> 0 round trip = 10
        assert abs(d["total_cost"] - 10.0) < 1e-2
        assert d["path_indices"] == [0, 1, 0]


# ─── /api/history ──────────────────────────────
class TestHistory:
    def test_history_returns_list(self, session):
        # Trigger at least one optimize first
        session.post(f"{API}/optimize", json={
            "locations": [{"x": 0, "y": 0}, {"x": 5, "y": 5}, {"x": 10, "y": 0}],
            "mode": "euclidean",
        })
        r = session.get(f"{API}/history?limit=5")
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data, list)
        if data:
            assert "total_cost" in data[0]
            assert "_id" not in data[0]  # Must not leak Mongo ObjectId
