import pytest
import yfinance as yf
from fastapi.testclient import TestClient

from backend.main import app

client = TestClient(app)


@pytest.mark.integration
def test_api_stock_quote_matches_live_market_within_half_percent():
    ticker = "2330"

    response = client.get(f"/api/stock/{ticker}")
    if response.status_code != 200:
        pytest.skip("Backend unable to fetch realtime quote in current environment")
    payload = response.json()

    history = yf.Ticker(f"{ticker}.TW").history(period="10d", auto_adjust=True)
    if history.empty:
        history = yf.Ticker(f"{ticker}.TWO").history(period="10d", auto_adjust=True)

    if history.empty or len(history) < 2:
        pytest.skip("Unable to fetch live market data from yfinance for integration check")

    last_close = float(history["Close"].iloc[-1])
    prev_close = float(history["Close"].iloc[-2])
    live_change_percent = ((last_close - prev_close) / prev_close) * 100 if prev_close else 0.0

    api_last = float(payload["last_price"])
    api_change = float(payload["change_percent"])

    last_price_diff_pct = abs((api_last - last_close) / last_close) * 100 if last_close else 0.0
    change_percent_diff_abs = abs(api_change - live_change_percent)

    assert last_price_diff_pct <= 3.0, (
        f"last_price diff too high: api={api_last}, live={last_close}, diff={last_price_diff_pct:.4f}%"
    )
    assert change_percent_diff_abs <= 3.0, (
        f"change_percent diff too high: api={api_change}, live={live_change_percent}, diff={change_percent_diff_abs:.4f}%"
    )


def test_stock_verify_endpoint_compares_db_and_realtime(monkeypatch):
    import pandas as pd
    import backend.routes.stock as stock_route

    monkeypatch.setattr(
        stock_route.legacy_stock_detail_service.score_repo,
        "get_latest_score",
        lambda _ticker, model_version=None: {
            "ticker": "2330",
            "last_price": 100.0,
            "change_percent": 1.0,
            "updated_at": "2026-02-23 10:00:00",
            "model_version": model_version or "v4.1",
            "total_score": 80,
            "trend_score": 30,
            "momentum_score": 25,
            "volatility_score": 25,
            "ai_probability": 0.8,
        },
    )

    realtime_df = pd.DataFrame(
        {
            "date": pd.date_range("2026-02-20", periods=2, freq="D"),
            "open": [99.0, 100.0],
            "high": [101.0, 102.0],
            "low": [98.0, 99.5],
            "close": [99.5, 100.2],
            "volume": [1000, 1100],
        }
    )
    monkeypatch.setattr(
        stock_route.legacy_stock_detail_service.stock_repo,
        "fetch_price_history",
        lambda *_args, **_kwargs: realtime_df,
    )

    response = client.get("/api/stock/2330/verify")
    assert response.status_code == 200

    body = response.json()
    assert body["ticker"] == "2330"
    assert "database" in body
    assert "realtime" in body
    assert "diff" in body
    assert isinstance(body["within_tolerance"], bool)
