"""
Backend failure-state honesty tests.

Spec: .agentcortex/specs/backend-failure-state-honesty.md
A failed/unavailable AI prediction must be represented as None/NULL — never a
fake 0.0 that is indistinguishable from a genuine low probability.
"""
import pandas as pd

from core.ai import predict_prob
from core.utils import to_ai_percent


class TestToAiPercent:
    def test_none_stays_none(self):
        """AC2: unavailable prediction → None (not 0.0)."""
        assert to_ai_percent(None) is None

    def test_genuine_zero_is_zero(self):
        """A genuine 0.0 probability stays 0.0 — distinct from unavailable."""
        assert to_ai_percent(0.0) == 0.0

    def test_scales_to_percent(self):
        assert to_ai_percent(0.721) == 72.1


class TestPredictProbFailure:
    def test_empty_df_returns_none(self):
        """AC1: a failure path (insufficient data) returns None, never a 0.0 dict."""
        result = predict_prob(pd.DataFrame())
        assert result is None


class TestSaveScoreNullAiProb:
    def test_none_ai_prob_stored_as_null(self, mock_db, monkeypatch, tmp_path):
        """AC3: save_score_to_db preserves NULL when ai_prob is None (no fake 0.0)."""
        from core import data
        import core.config

        monkeypatch.setattr(core.config, "DB_PATH", str(tmp_path / "test_stocks.db"))

        scores = {
            'total_score_v2': 50.0,
            'trend_score_v2': 20.0,
            'momentum_score_v2': 15.0,
            'volatility_score_v2': 15.0,
            'last_price': 100.0,
            'change_percent': 1.0,
        }
        data.save_score_to_db("9999", scores, ai_prob=None, model_version="v4.test")

        rows = data.get_top_scores_from_db(limit=10)
        row = next(r for r in rows if r['ticker'] == "9999")
        assert row['ai_probability'] is None  # NULL preserved, not coerced to 0.0

    def test_genuine_ai_prob_still_stored(self, mock_db, monkeypatch, tmp_path):
        """A genuine probability is stored unchanged (regression guard)."""
        from core import data
        import core.config

        monkeypatch.setattr(core.config, "DB_PATH", str(tmp_path / "test_stocks.db"))

        scores = {
            'total_score_v2': 50.0,
            'trend_score_v2': 20.0,
            'momentum_score_v2': 15.0,
            'volatility_score_v2': 15.0,
            'last_price': 100.0,
            'change_percent': 1.0,
        }
        data.save_score_to_db("8888", scores, ai_prob=0.55, model_version="v4.test")

        rows = data.get_top_scores_from_db(limit=10)
        row = next(r for r in rows if r['ticker'] == "8888")
        assert row['ai_probability'] == 0.55


class TestModelHealth:
    """Spec: ui-model-state-disclosure.md — get_model_health assessment."""

    def test_unavailable_when_version_unknown(self, monkeypatch):
        import core.ai.predictor as predictor
        monkeypatch.setattr(predictor, "get_model_version", lambda: "unknown")
        h = predictor.get_model_health()
        assert h["status"] == "unavailable"
        assert h["message"]

    def test_degraded_when_buy_signal_power_zero(self, monkeypatch):
        import core.ai.predictor as predictor
        monkeypatch.setattr(predictor, "get_model_version", lambda: "v4.test")
        monkeypatch.setattr(predictor, "list_available_models", lambda: [
            {"version": "v4.test", "oos_metrics": {
                "accuracy": 0.94, "precision_buy": 0.0, "recall_buy": 0.0,
                "precision_strong": 0.0, "recall_strong": 0.0}},
        ])
        h = predictor.get_model_health()
        assert h["status"] == "degraded"
        assert h["message"]

    def test_ok_when_model_has_buy_power(self, monkeypatch):
        import core.ai.predictor as predictor
        monkeypatch.setattr(predictor, "get_model_version", lambda: "v4.good")
        monkeypatch.setattr(predictor, "list_available_models", lambda: [
            {"version": "v4.good", "oos_metrics": {
                "precision_buy": 0.4, "recall_buy": 0.3,
                "precision_strong": 0.2, "recall_strong": 0.1}},
        ])
        h = predictor.get_model_health()
        assert h["status"] == "ok"
        assert h["message"] == ""
