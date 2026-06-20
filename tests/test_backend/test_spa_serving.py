"""SPA single-port serving: the backend must serve the built index.html for
react-router deep links (BrowserRouter) without shadowing API or asset routes.

Covers spec docs/specs/onboarding-single-command-launch.md AC4.
Note: frontend/v4/index.html exists in the repo, so GET / and the SPA fallback
return 200 even before `npm run build` produces frontend/v4/dist/.
"""
from fastapi.testclient import TestClient

from backend.main import app

client = TestClient(app)


def _looks_like_html(text: str) -> bool:
    lowered = text.lower()
    return "<html" in lowered or "<!doctype html" in lowered


def test_root_serves_index():
    """GET / must serve an HTML entry document."""
    response = client.get("/")
    assert response.status_code == 200
    assert _looks_like_html(response.text)


def test_spa_fallback_serves_index_for_client_route():
    """A react-router deep link (/backtest) must return the SPA index, not 404."""
    response = client.get("/backtest")
    assert response.status_code == 200
    assert _looks_like_html(response.text)


def test_spa_fallback_serves_index_for_other_client_routes():
    """Every client route (/risk, /indicators) resolves to the SPA index."""
    for route in ("/risk", "/indicators"):
        response = client.get(route)
        assert response.status_code == 200, route
        assert _looks_like_html(response.text), route


def test_spa_fallback_does_not_shadow_unknown_api():
    """Unknown /api/* paths must 404 as a JSON error — never the SPA index."""
    response = client.get("/api/this-endpoint-does-not-exist")
    assert response.status_code == 404
    assert not _looks_like_html(response.text)


def test_spa_fallback_404s_bare_reserved_segments():
    """Bare /api, /assets, /static (no trailing slash) must 404, not serve HTML."""
    for segment in ("/api", "/assets", "/static"):
        response = client.get(segment)
        assert response.status_code == 404, segment
        assert not _looks_like_html(response.text), segment


def test_known_api_route_still_works():
    """The catch-all must not break a real API route registered before it."""
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json().get("status") == "ok"
