"""Unknown-is-not-zero: the prediction path must refuse, never substitute.

Spec: docs/specs/unknown-is-not-zero-ml-features.md (GH #14)

A feature that cannot be computed used to be filled with ``0``. That is not a blank:
``dist_sma240 = 0`` asserts *the price sits exactly on its 240-day mean*, and a slope of ``0``
asserts *flat*. Measured on ticker 2330's real last trading day, full history gives
``dist_sma240 = +0.3429`` (34.3% above the annual mean) and 150 rows gives ``0.0``.
"""
import numpy as np
import pandas as pd
import pytest

from core.ai import predict_prob
from core.ai.common import FEATURE_COLS, MIN_FEATURE_ROWS, uncomputable_features
from core.ai.trainer import prepare_features


def make_frame(rows: int, seed: int = 0) -> pd.DataFrame:
    """OHLCV with a persistent drift, so long-window features have a non-zero true value.

    A flat series would make this suite unfalsifiable: the fabricated 0 and the true value
    would coincide, and every assertion below would pass with the defect restored.
    """
    rng = np.random.default_rng(seed)
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
    """Minimal stand-in for a fitted sklearn estimator."""

    def __init__(self, feature_names=None):
        self.classes_ = np.array([0, 1, 2])
        self.calls = 0
        if feature_names is not None:
            self.feature_names_in_ = np.array(feature_names)

    def predict_proba(self, X):
        self.calls += 1
        return np.array([[0.5, 0.3, 0.2]] * len(X))


@pytest.fixture
def loaded_model(monkeypatch):
    """Install a model in the predictor's cache so no .pkl file is needed."""

    def _install(feature_names=None):
        from core.ai import predictor

        clf = _Classifier(feature_names)
        model = {"ensemble": {"gb": clf}, "version": "v4.test"}
        monkeypatch.setattr(predictor, "_cache_get", lambda _path: model)
        return clf

    return _install


class TestPredictionRefusesRatherThanSubstitutes:
    def test_short_history_yields_no_prediction(self, loaded_model):
        """AC1/AC2: 150 rows clears MIN_PREDICT_ROWS but cannot support sma_240 -> no number.

        Falsifiable: restoring `.fillna(0)` on the prediction path makes this return a dict.
        The model must not even be consulted — `None` alone would also be produced by a crash,
        so the call count is what distinguishes a refusal from a failure.
        """
        clf = loaded_model()
        assert predict_prob(make_frame(150)) is None
        assert clf.calls == 0, "the model was handed a row containing an invented feature"

    def test_full_history_still_predicts(self, loaded_model):
        """The refusal is targeted: the same frame with enough history still produces a number."""
        loaded_model()
        result = predict_prob(make_frame(400))
        assert isinstance(result, dict)
        assert 0.0 <= result["prob"] <= 1.0

    def test_the_substitution_would_have_been_a_specific_claim(self):
        """The point of the feature: 0 is not a blank, it is a plausible wrong value.

        With full history this stock sits well away from its 240-day mean; the fill would have
        reported it as sitting exactly on it.
        """
        df = make_frame(400)
        full, _ = prepare_features(df.copy(), is_training=False)
        short, _ = prepare_features(df.tail(150).copy(), is_training=False)

        true_value = full.iloc[-1]["dist_sma240"]
        assert abs(true_value) > 0.02, "fixture drift too weak to distinguish 0 from the truth"
        assert pd.isna(short.iloc[-1]["dist_sma240"]), "uncomputable must stay NaN, not become 0.0"

    def test_infinity_is_uncomputable_too(self, loaded_model):
        """AC1: +/-inf comes from the same divisions as NaN and must not reach the model."""
        clf = loaded_model()
        df = make_frame(400)
        with pytest.MonkeyPatch.context() as mp:
            real = prepare_features

            def poisoned(frame, is_training=True):
                X, y = real(frame, is_training=is_training)
                if not X.empty:
                    X = X.copy()
                    X.iloc[-1, X.columns.get_loc("rsi")] = np.inf
                return X, y

            mp.setattr("core.ai.trainer.prepare_features", poisoned)
            assert predict_prob(df) is None
        assert clf.calls == 0


class TestTrainingPathIsUnchanged:
    """`core/ai/trainer.py` drops warm-up rows for training. That line is load-bearing."""

    def test_training_output_contains_no_uncomputable_feature(self):
        """Falsifiable: removing the `dropna` leaves NaN warm-up rows in the training panel."""
        X, y = prepare_features(make_frame(400), is_training=True)
        assert not X.empty
        assert not X.isna().to_numpy().any()
        assert len(X) == len(y)

    def test_training_drops_the_warmup_rows(self):
        """The warm-up rows are removed, not filled — and specifically the ones sma_240 needs.

        `len(X) < rows` alone proves nothing: the PRED_DAYS truncation guarantees it with the
        dropna deleted. The count has to be measured against the warm-up boundary itself.
        """
        from core.ai.common import MIN_FEATURE_ROWS, PRED_DAYS

        rows = 400
        X, _ = prepare_features(make_frame(rows), is_training=True)
        # Every surviving row must be one where the 250-row warm-up had completed.
        assert len(X) <= rows - (MIN_FEATURE_ROWS - 1) - PRED_DAYS, (
            "rows from inside the sma_240 warm-up survived; the training dropna is gone"
        )


class TestModelFeatureMismatch:
    def test_model_expecting_an_absent_feature_refuses(self, loaded_model):
        """AC3: a column the model wants but the frame lacks is not invented as 0.

        Asserting only `is None` cannot tell a refusal from an exception swallowed by the
        caller — with `fill_value=0` restored this returned None too. The call count is the
        assertion that actually falsifies.
        """
        clf = loaded_model(feature_names=list(FEATURE_COLS) + ["feature_from_another_model"])
        assert predict_prob(make_frame(400)) is None
        assert clf.calls == 0, "the model was invoked with a column invented as 0"

    def test_model_matching_the_frame_predicts(self, loaded_model):
        clf = loaded_model(feature_names=list(FEATURE_COLS))
        assert isinstance(predict_prob(make_frame(400)), dict)
        assert clf.calls == 1


class TestUncomputableFeatures:
    def test_reports_nan_inf_and_absent_columns(self):
        row = pd.Series({col: 1.0 for col in FEATURE_COLS})
        row["rsi"] = np.nan
        row["k"] = np.inf
        row["d"] = -np.inf
        row = row.drop(labels=["bb_width"])
        assert sorted(uncomputable_features(row)) == sorted(["rsi", "k", "d", "bb_width"])

    def test_a_complete_row_reports_nothing(self):
        assert uncomputable_features(pd.Series({col: 0.5 for col in FEATURE_COLS})) == []

    def test_a_genuine_zero_is_computable(self):
        """0 is a legitimate feature value; only NaN/inf mean 'could not be computed'."""
        assert uncomputable_features(pd.Series({col: 0.0 for col in FEATURE_COLS})) == []


class TestMinFeatureRowsMatchesReality:
    """MIN_FEATURE_ROWS explains the refusal to the user. It must not drift from the code.

    If a longer-window feature is ever added to FEATURE_COLS without updating the constant,
    these fail — which is the point. The constant never gates; it only explains.
    """

    def test_at_the_stated_requirement_every_feature_is_computable(self):
        X, _ = prepare_features(make_frame(MIN_FEATURE_ROWS), is_training=False)
        assert not X.empty
        assert uncomputable_features(X.iloc[-1]) == []

    def test_one_row_short_something_is_not(self):
        X, _ = prepare_features(make_frame(MIN_FEATURE_ROWS - 1), is_training=False)
        assert not X.empty
        assert uncomputable_features(X.iloc[-1]) != []


class TestPredictionDoesNotCarryStaleValues:
    """AC1 (amended): a stale value is still a value the model reads as today's observation.

    The prediction path used to `ffill().bfill()`. The bfill could never reach the prediction
    row — it is the last one — but the ffill could, substituting yesterday's indicator whenever
    today's could not be computed.
    """

    def test_yesterdays_value_is_not_carried_into_today(self, loaded_model):
        clf = loaded_model()
        df = make_frame(400)
        # Today's volume is unknown; every volume-derived feature becomes uncomputable.
        df.loc[df.index[-1], "volume"] = np.nan

        assert predict_prob(df) is None
        assert clf.calls == 0, "the model was given a value carried forward from a previous day"

    def test_the_same_frame_with_todays_volume_still_predicts(self, loaded_model):
        clf = loaded_model()
        assert isinstance(predict_prob(make_frame(400)), dict)
        assert clf.calls == 1


class TestTheRefusalIsAttributable:
    """AC4: a refusal nobody can trace to a stock is not attributable.

    `sync.py` runs prediction across the universe under a thread pool, so an unattributed
    warning is N identical lines an operator cannot act on.
    """

    def test_the_log_names_the_ticker(self, loaded_model, caplog):
        loaded_model()
        df = make_frame(150)
        df["ticker"] = "2330"

        with caplog.at_level("WARNING", logger="core.ai.predictor"):
            assert predict_prob(df) is None

        messages = [r.getMessage() for r in caplog.records]
        assert any("2330" in m for m in messages), f"no ticker in {messages}"
        assert any("dist_sma240" in m for m in messages), f"no feature names in {messages}"

    def test_a_frame_without_a_ticker_column_still_logs(self, loaded_model, caplog):
        """Best-effort: the absence of a ticker must not turn a refusal into an exception."""
        loaded_model()
        with caplog.at_level("WARNING", logger="core.ai.predictor"):
            assert predict_prob(make_frame(150)) is None
        assert any("could not be computed" in r.getMessage() for r in caplog.records)
