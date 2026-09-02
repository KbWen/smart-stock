"""The refusal must survive the route, not just the unit.

Spec: docs/specs/unknown-is-not-zero-ml-features.md (GH #14)

Two of the three request paths ran `df = df.fillna(0)` *before* handing the frame to
``predict_prob`` -- to keep NaN out of the JSON payload. That fill also erased the evidence the
model needs: with ``sma_240 = 0``, ``dist_sma240`` becomes a finite astronomical number instead
of NaN, and a fill applied to ``dist_sma240`` itself asserts "the price sits exactly on its
240-day mean". Either way the finite check in ``predict_prob`` sees nothing wrong.

A unit test built from raw OHLCV cannot catch that, because ``prepare_features`` computes the
indicators itself and the NaN is real. Only the route reproduces the shape.
"""
import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from backend.main import app

client = TestClient(app)

SHORT_ROWS = 150  # clears MIN_PREDICT_ROWS (120), far below what sma_240 needs (250)


def price_frame(rows: int) -> pd.DataFrame:
    rng = np.random.default_rng(7)
    close = 100 + np.cumsum(rng.normal(0.15, 1.0, rows))
    return pd.DataFrame({
        "date": pd.bdate_range("2023-01-02", periods=rows),
        "open": close,
        "high": close * 1.01,
        "low": close * 0.99,
        "close": close,
        "volume": rng.integers(1_000, 5_000, rows).astype(float),
    })


class _Classifier:
    """Stand-in for a fitted estimator, so the test does not depend on a model file.

    `model_sniper.pkl` is gitignored, so in a fresh clone or in CI `predict_prob` returns None
    because the model cannot be loaded -- which would satisfy `ai_probability is None` even with
    the defect restored. Installing a model makes the refusal the only explanation.
    """

    def __init__(self):
        self.classes_ = np.array([0, 1, 2])
        self.calls = 0

    def predict_proba(self, X):
        self.calls += 1
        return np.array([[0.5, 0.3, 0.2]] * len(X))


def install_model(monkeypatch) -> "_Classifier":
    from core.ai import predictor

    clf = _Classifier()
    monkeypatch.setattr(predictor, "_cache_get",
                        lambda _p: {"ensemble": {"gb": clf}, "version": "v4.test"})
    return clf


@pytest.fixture
def v4_short_history(monkeypatch):
    """Serve /api/v4/stock/2330 from a deliberately short price history."""
    import backend.routes.stock as stock_route
    import backend.services.v4_stock_detail_service as detail_mod

    stock_route.clear_api_caches()
    stock_route.v4_stock_detail_service.clear_cache()

    svc = stock_route.v4_stock_detail_service
    monkeypatch.setattr(svc.stock_repo, "load_price_history", lambda _t: price_frame(SHORT_ROWS))
    monkeypatch.setattr(svc.stock_repo, "get_stock_name", lambda _t: "TSMC")
    monkeypatch.setattr(svc.score_repo, "get_latest_score", lambda _t: None)
    monkeypatch.setattr(svc.indicator_repo, "load_for_ticker", lambda _t: None)
    # A model exists; only the data is short. Without this the honest answer would be
    # "no model", which model_health already reports and this feature must not relabel.
    monkeypatch.setattr(detail_mod, "get_model_version", lambda: "v4.test")
    monkeypatch.setattr(detail_mod, "get_model_health",
                        lambda: {"status": "ok", "version": "v4.test", "message": ""})
    return install_model(monkeypatch)


class TestV4DetailRefusesOnShortHistory:
    def test_no_number_and_the_reason_is_stated(self, v4_short_history):
        clf = v4_short_history
        body = client.get("/api/v4/stock/2330").json()
        assert body["ai_probability"] is None
        assert body["ai_unavailable_reason"] == "insufficient_history"
        assert clf.calls == 0, "the model was scored on an invented feature"

    def test_the_technical_scores_still_work(self, v4_short_history):
        """Only the AI number is withheld. A short-history stock is not blanked out."""
        body = client.get("/api/v4/stock/2330").json()
        assert body["rise_score_breakdown"]["total"] is not None
        assert body["price"] > 0

    def test_long_history_still_gets_a_number(self, monkeypatch):
        import backend.routes.stock as stock_route
        import backend.services.v4_stock_detail_service as detail_mod

        stock_route.clear_api_caches()
        stock_route.v4_stock_detail_service.clear_cache()
        svc = stock_route.v4_stock_detail_service
        monkeypatch.setattr(svc.stock_repo, "load_price_history", lambda _t: price_frame(400))
        monkeypatch.setattr(svc.stock_repo, "get_stock_name", lambda _t: "TSMC")
        monkeypatch.setattr(svc.score_repo, "get_latest_score", lambda _t: None)
        monkeypatch.setattr(svc.indicator_repo, "load_for_ticker", lambda _t: None)
        monkeypatch.setattr(svc, "predict_prob", lambda _df: {"prob": 0.62})
        monkeypatch.setattr(detail_mod, "get_model_version", lambda: "v4.test")
        monkeypatch.setattr(detail_mod, "get_model_health",
                            lambda: {"status": "ok", "version": "v4.test", "message": ""})

        body = client.get("/api/v4/stock/2330").json()
        assert body["ai_probability"] == 62.0
        assert body["ai_unavailable_reason"] is None


class TestDisplayFillNeverReachesTheModel:
    """The legacy path fills the frame for the payload. That fill must not reach predict_prob.

    Falsifiable: pass `df` instead of `df_for_model` and the captured frame has no NaN left,
    so `dist_sma240` arrives as a real-looking number and the refusal never fires.
    """

    def test_legacy_detail_hands_the_model_an_unfilled_frame(self, monkeypatch):
        import backend.routes.stock as stock_route

        stock_route.clear_api_caches()
        svc = stock_route.legacy_stock_detail_service
        captured = {}

        def capture(df):
            captured["frame"] = df.copy()
            return None

        monkeypatch.setattr(svc.stock_repo, "load_price_history", lambda _t: price_frame(SHORT_ROWS))
        monkeypatch.setattr(svc.score_repo, "get_latest_score", lambda _t: None)
        monkeypatch.setattr(svc, "predict_prob", capture)

        svc.get_stock_detail("2330")

        frame = captured["frame"]
        assert "dist_sma240" in frame.columns
        assert frame["dist_sma240"].isna().all(), (
            "the model was handed a display-filled frame; an uncomputable feature "
            "arrived as a real value and predict_prob cannot refuse it"
        )

    def test_the_payload_itself_is_still_free_of_nan(self, monkeypatch):
        """The display fill still does its job — the response must not carry NaN."""
        import backend.routes.stock as stock_route

        stock_route.clear_api_caches()
        svc = stock_route.legacy_stock_detail_service
        monkeypatch.setattr(svc.stock_repo, "load_price_history", lambda _t: price_frame(SHORT_ROWS))
        monkeypatch.setattr(svc.score_repo, "get_latest_score", lambda _t: None)
        monkeypatch.setattr(svc, "predict_prob", lambda _df: None)

        body = svc.get_stock_detail("2330")
        for key in ("total_score", "trend_score", "momentum_score", "volatility_score"):
            assert not pd.isna(body["score"][key])
