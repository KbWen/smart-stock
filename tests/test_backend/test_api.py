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
