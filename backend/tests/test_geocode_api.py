"""
Backend tests for /api/geocode (Nominatim proxy).
Uses a single module-level requests.Session to avoid hammering Nominatim.
Tests are serialised (no parallel) — backend already throttles to 1 req/sec.
"""
import os
import time
import pytest
import requests

BASE_URL = os.environ.get(
    "REACT_APP_BACKEND_URL",
).rstrip("/")
API = f"{BASE_URL}/api"


@pytest.fixture(scope="module")
def session():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


# ─── Geocoder ─────────────────────────────────
class TestGeocode:
    def test_geocode_validation_too_short(self, session):
        # q has min_length=2
        r = session.get(f"{API}/geocode", params={"q": "x"})
        assert r.status_code == 422, r.text

    def test_geocode_bandra(self, session):
        r = session.get(f"{API}/geocode", params={"q": "Bandra"}, timeout=20)
        # If upstream blocked, mark explicit so main agent can act
        if r.status_code == 502:
            pytest.skip("Nominatim upstream blocked in test env")
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["query"] == "Bandra"
        assert isinstance(data["results"], list)
        assert len(data["results"]) >= 1, "expected at least one result for Bandra"

        for item in data["results"]:
            # required fields
            for k in ["name", "label", "display_name", "country", "lat", "lng", "type"]:
                assert k in item, f"missing key {k} in {item}"
            assert isinstance(item["lat"], (int, float))
            assert isinstance(item["lng"], (int, float))
            assert -90.0 <= item["lat"] <= 90.0
            assert -180.0 <= item["lng"] <= 180.0
            assert isinstance(item["label"], str) and len(item["label"]) > 0

    def test_geocode_soho_with_country_state(self, session):
        r = session.get(f"{API}/geocode", params={"q": "SoHo"}, timeout=20)
        if r.status_code == 502:
            pytest.skip("Nominatim upstream blocked in test env")
        assert r.status_code == 200, r.text
        data = r.json()
        assert len(data["results"]) >= 1
        # at least one should expose country info
        any_country = any(item.get("country") for item in data["results"])
        assert any_country, f"no result had country populated: {data['results']}"

    def test_geocode_limit_respected(self, session):
        r = session.get(f"{API}/geocode", params={"q": "Bandra", "limit": 3}, timeout=20)
        if r.status_code == 502:
            pytest.skip("Nominatim upstream blocked in test env")
        assert r.status_code == 200
        data = r.json()
        assert len(data["results"]) <= 3

    def test_geocode_cache_second_call_faster(self, session):
        """Soft check: second identical call should hit in-memory cache → much faster."""
        # Warm cache (may incur full network + 1s throttle wait)
        r1 = session.get(f"{API}/geocode", params={"q": "Bandra"}, timeout=20)
        if r1.status_code == 502:
            pytest.skip("Nominatim upstream blocked in test env")
        assert r1.status_code == 200

        t0 = time.perf_counter()
        r2 = session.get(f"{API}/geocode", params={"q": "Bandra"}, timeout=20)
        elapsed = time.perf_counter() - t0
        assert r2.status_code == 200
        # cached response should be sub-500ms (no throttle, no network)
        assert elapsed < 0.5, f"cached call took too long: {elapsed:.3f}s"
        # payloads identical
        assert r1.json() == r2.json()

    def test_geocode_rate_limit_serial_calls_succeed(self, session):
        """Rapid-fire (3) calls must all succeed thanks to backend asyncio.Lock throttling."""
        queries = ["Camden", "Colaba", "Powai"]
        for q in queries:
            r = session.get(f"{API}/geocode", params={"q": q}, timeout=25)
            if r.status_code == 502:
                pytest.skip("Nominatim upstream blocked in test env")
            assert r.status_code == 200, f"q={q} -> {r.status_code} {r.text}"
            data = r.json()
            assert isinstance(data["results"], list)
