"""
Unit tests for V4MetaService (docs/specs/meta-service-tests.md).

AC1: _to_bool covers all 6 type branches.
AC2: get_meta() maps scores/indicators correctly (macd_diff, volume_spike, signals).
AC3: Unknown ticker (no DB entry) returns safe zeros — no exception.
AC4: updated_at falls back to indicators' timestamp when score has none.
AC5: No regression (all 101 pre-existing tests still pass).
"""
import pytest
from unittest.mock import MagicMock
from backend.services.v4_meta_service import V4MetaService


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_service(scores=None, indicators=None, names=None):
    """Build a V4MetaService with fully mocked repositories."""
    score_repo = MagicMock()
    indicator_repo = MagicMock()
    stock_repo = MagicMock()

    score_repo.load_latest_scores_for_tickers.return_value = scores or {}
    indicator_repo.load_for_tickers.return_value = indicators or {}
    stock_repo.get_stock_name.side_effect = lambda t: (names or {}).get(t, t)

    return V4MetaService(
        score_repo=score_repo,
        indicator_repo=indicator_repo,
        stock_repo=stock_repo,
    )


# ---------------------------------------------------------------------------
# AC1: _to_bool
# ---------------------------------------------------------------------------

class TestToBool:
    def test_none_is_false(self):
        assert V4MetaService._to_bool(None) is False

    def test_zero_int_is_false(self):
        assert V4MetaService._to_bool(0) is False

    def test_nonzero_int_is_true(self):
        assert V4MetaService._to_bool(1) is True
        assert V4MetaService._to_bool(-1) is True

    def test_zero_float_is_false(self):
        assert V4MetaService._to_bool(0.0) is False

    def test_nonzero_float_is_true(self):
        assert V4MetaService._to_bool(0.5) is True

    def test_true_strings(self):
        for s in ["1", "true", "True", "TRUE", "yes", "Yes", "y", "Y"]:
            assert V4MetaService._to_bool(s) is True, f"Expected True for {s!r}"

    def test_false_strings(self):
        for s in ["0", "false", "False", "no", "No", "n", "", "random"]:
            assert V4MetaService._to_bool(s) is False, f"Expected False for {s!r}"

    def test_bool_passthrough(self):
        assert V4MetaService._to_bool(True) is True
        assert V4MetaService._to_bool(False) is False

    def test_unknown_type_is_false(self):
        assert V4MetaService._to_bool([1, 2]) is False
        assert V4MetaService._to_bool({"a": 1}) is False


# ---------------------------------------------------------------------------
# AC2: core get_meta logic
# ---------------------------------------------------------------------------

class TestGetMeta:
    def _pairs(self, *tickers):
        """Helper: build (ticker, ticker) pairs (already normalized)."""
        return [(t, t) for t in tickers]

    def test_score_fields_mapped_correctly(self):
        svc = _make_service(
            scores={"2330": {"total_score": 85.5, "trend_score": 70.0,
                             "momentum_score": 60.0, "volatility_score": 50.0,
                             "last_price": 1000.0, "change_percent": 1.5,
                             "ai_probability": 0.72, "updated_at": "2026-03-18T10:00:00"}},
            indicators={"2330": {"macd": 5.0, "macd_signal": 3.0, "rel_vol": 1.0,
                                 "rsi": 55.0, "is_squeeze": 0, "kd_cross_flag": 1}},
        )
        result = svc.get_meta(self._pairs("2330"))
        d = result["data"]["2330"]

        assert d["total_score"] == pytest.approx(85.5)
        assert d["trend_score"] == pytest.approx(70.0)
        assert d["ai_prob"] == pytest.approx(0.72)
        assert d["last_price"] == pytest.approx(1000.0)
        assert d["change_percent"] == pytest.approx(1.5)

    def test_macd_diff_is_macd_minus_signal(self):
        """AC2: macd_diff = macd - macd_signal, not just macd."""
        svc = _make_service(
            indicators={"AAPL": {"macd": 8.0, "macd_signal": 3.0, "rel_vol": 1.0,
                                 "rsi": 50.0, "is_squeeze": 0, "kd_cross_flag": 0}},
        )
        result = svc.get_meta([("AAPL", "AAPL")])
        assert result["data"]["AAPL"]["signals"]["macd_diff"] == pytest.approx(5.0)

    def test_volume_spike_true_above_threshold(self):
        """AC2: volume_spike = True when rel_vol > 1.5."""
        svc = _make_service(indicators={"X": {"macd": 0, "macd_signal": 0,
                                              "rel_vol": 2.0, "rsi": 50,
                                              "is_squeeze": 0, "kd_cross_flag": 0}})
        result = svc.get_meta([("X", "X")])
        assert result["data"]["X"]["signals"]["volume_spike"] is True

    def test_volume_spike_false_at_threshold(self):
        """AC2: volume_spike = False when rel_vol == 1.5 (not strictly greater)."""
        svc = _make_service(indicators={"X": {"macd": 0, "macd_signal": 0,
                                              "rel_vol": 1.5, "rsi": 50,
                                              "is_squeeze": 0, "kd_cross_flag": 0}})
        result = svc.get_meta([("X", "X")])
        assert result["data"]["X"]["signals"]["volume_spike"] is False

    def test_volume_spike_false_below_threshold(self):
        svc = _make_service(indicators={"X": {"macd": 0, "macd_signal": 0,
                                              "rel_vol": 1.2, "rsi": 50,
                                              "is_squeeze": 0, "kd_cross_flag": 0}})
        result = svc.get_meta([("X", "X")])
        assert result["data"]["X"]["signals"]["volume_spike"] is False

    def test_squeeze_signal_from_indicator(self):
        svc = _make_service(indicators={"X": {"macd": 0, "macd_signal": 0,
                                              "rel_vol": 1.0, "rsi": 50,
                                              "is_squeeze": 1, "kd_cross_flag": 0}})
        result = svc.get_meta([("X", "X")])
        assert result["data"]["X"]["signals"]["squeeze"] is True

    def test_golden_cross_signal_from_indicator(self):
        svc = _make_service(indicators={"X": {"macd": 0, "macd_signal": 0,
                                              "rel_vol": 1.0, "rsi": 50,
                                              "is_squeeze": 0, "kd_cross_flag": 1}})
        result = svc.get_meta([("X", "X")])
        assert result["data"]["X"]["signals"]["golden_cross"] is True

    def test_response_contains_all_expected_keys(self):
        svc = _make_service()
        result = svc.get_meta([("Z", "Z")])
        d = result["data"]["Z"]
        for key in ["total_score", "trend_score", "momentum_score", "volatility_score",
                    "last_price", "change_percent", "ai_prob", "signals",
                    "updated_at", "model_version", "name"]:
            assert key in d, f"Missing key: {key}"
        for sig_key in ["squeeze", "golden_cross", "volume_spike", "rsi", "macd_diff", "rel_vol"]:
            assert sig_key in d["signals"], f"Missing signal key: {sig_key}"


# ---------------------------------------------------------------------------
# AC3: Unknown ticker safe defaults
# ---------------------------------------------------------------------------

class TestUnknownTicker:
    def test_unknown_ticker_returns_zeros_no_exception(self):
        """AC3: ticker with no DB entry produces zeros and False signals — no crash."""
        svc = _make_service()  # empty scores and indicators
        result = svc.get_meta([("GHOST", "GHOST")])

        d = result["data"]["GHOST"]
        assert d["total_score"] == 0
        assert d["ai_prob"] == 0
        assert d["signals"]["squeeze"] is False
        assert d["signals"]["golden_cross"] is False
        assert d["signals"]["volume_spike"] is False
        assert d["signals"]["rsi"] == pytest.approx(50.0)  # default

    def test_unknown_ticker_no_exception_raised(self):
        svc = _make_service()
        try:
            svc.get_meta([("DOESNOTEXIST", "DOESNOTEXIST")])
        except Exception as exc:
            pytest.fail(f"get_meta raised unexpectedly: {exc}")


# ---------------------------------------------------------------------------
# AC4: updated_at fallback
# ---------------------------------------------------------------------------

class TestUpdatedAt:
    def test_score_updated_at_preferred(self):
        svc = _make_service(
            scores={"T": {"updated_at": "2026-03-18T10:00:00"}},
            indicators={"T": {"updated_at": "2026-03-17T08:00:00",
                               "macd": 0, "macd_signal": 0, "rel_vol": 1.0,
                               "rsi": 50, "is_squeeze": 0, "kd_cross_flag": 0}},
        )
        result = svc.get_meta([("T", "T")])
        assert result["data"]["T"]["updated_at"] == "2026-03-18T10:00:00"

    def test_fallback_to_indicator_updated_at(self):
        """AC4: When score has no updated_at, use indicators' timestamp."""
        svc = _make_service(
            scores={"T": {"updated_at": None}},
            indicators={"T": {"updated_at": "2026-03-17T08:00:00",
                               "macd": 0, "macd_signal": 0, "rel_vol": 1.0,
                               "rsi": 50, "is_squeeze": 0, "kd_cross_flag": 0}},
        )
        result = svc.get_meta([("T", "T")])
        assert result["data"]["T"]["updated_at"] == "2026-03-17T08:00:00"

    def test_both_missing_updated_at_is_none(self):
        svc = _make_service(scores={"T": {}}, indicators={"T": {}})
        result = svc.get_meta([("T", "T")])
        assert result["data"]["T"]["updated_at"] is None


# ---------------------------------------------------------------------------
# Deduplication (B1 side-effect test)
# ---------------------------------------------------------------------------

class TestDeduplication:
    def test_duplicate_normalized_ticker_queries_repo_once(self):
        """Same normalized ticker from two original forms should not double-query repos."""
        score_repo = MagicMock()
        indicator_repo = MagicMock()
        stock_repo = MagicMock()
        score_repo.load_latest_scores_for_tickers.return_value = {}
        indicator_repo.load_for_tickers.return_value = {}
        stock_repo.get_stock_name.return_value = "Test"

        svc = V4MetaService(score_repo=score_repo,
                            indicator_repo=indicator_repo,
                            stock_repo=stock_repo)

        # Two original tickers normalizing to the same code
        pairs = [("2330.TW", "2330"), ("2330", "2330")]
        result = svc.get_meta(pairs)

        # Both keys in response
        assert "2330.TW" in result["data"]
        assert "2330" in result["data"]

        # Repos called with deduplicated list (only "2330" once)
        called_tickers = indicator_repo.load_for_tickers.call_args[0][0]
        assert called_tickers.count("2330") == 1
