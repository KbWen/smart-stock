import pytest
from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)

def test_health_check_api():
    """Verify the health check endpoint."""
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data['status'] == 'ok'
    assert 'db' in data

def test_api_stocks_list():
    """Verify the stock list endpoint."""
    response = client.get("/api/stocks")
    assert response.status_code == 200
    assert isinstance(response.json(), list)

def test_api_top_picks():
    """Verify the top picks endpoint."""
    response = client.get("/api/top_picks?sort=score")
    assert response.status_code == 200
    assert isinstance(response.json(), list)

def test_api_sync_status():
    """Verify the sync status endpoint."""
    response = client.get("/api/sync/status")
    assert response.status_code == 200
    data = response.json()
    assert 'is_syncing' in data


def test_smart_scan_requires_xhr_header():
    """smart_scan POST must reject requests without X-Requested-With: XMLHttpRequest (CSRF guard)."""
    response = client.post("/api/smart_scan", json=[])
    assert response.status_code == 403


def test_smart_scan_accepts_xhr_header():
    """smart_scan POST with correct header must return 200 and a list."""
    response = client.post(
        "/api/smart_scan",
        json=[],
        headers={"X-Requested-With": "XMLHttpRequest"},
    )
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_api_init_returns_expected_keys():
    """Smoke test: /api/init returns all dashboard keys."""
    response = client.get("/api/init")
    assert response.status_code == 200
    data = response.json()
    for key in ("market", "top_picks", "models", "sync", "perf_ms"):
        assert key in data, f"Missing key in /api/init response: {key!r}"
    assert isinstance(data["top_picks"], list)
    assert isinstance(data["models"], list)
    assert isinstance(data["perf_ms"], int)


def test_api_search_returns_list():
    """Smoke test: /api/search?q=<term> returns a list."""
    response = client.get("/api/search?q=2330")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_api_search_rejects_empty_query():
    """/api/search?q= (empty) must be rejected with 422 (min_length=1)."""
    response = client.get("/api/search?q=")
    assert response.status_code == 422


def test_root_serves_legacy_index_when_default_missing(monkeypatch, tmp_path):
    import backend.main as main

    frontend_dir = tmp_path / "frontend"
    frontend_dir.mkdir()
    legacy = frontend_dir / "index_legacy.html"
    legacy.write_text("<html><body>legacy</body></html>", encoding="utf-8")

    monkeypatch.setattr(main, "frontend_path", str(frontend_dir))

    response = client.get("/")

    assert response.status_code == 200
    assert "legacy" in response.text


def test_root_returns_404_when_no_frontend_entry(monkeypatch, tmp_path):
    import backend.main as main

    frontend_dir = tmp_path / "frontend_empty"
    frontend_dir.mkdir()

    monkeypatch.setattr(main, "frontend_path", str(frontend_dir))

    response = client.get("/")

    assert response.status_code == 404
    assert response.json().get("message") == "Frontend entry file not found"
