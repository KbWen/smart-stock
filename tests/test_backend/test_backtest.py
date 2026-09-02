import sys
import types

import numpy as np
import pandas as pd
import pytest

# Prevent heavy module side effects during import.
fake_data = types.ModuleType('core.data')
fake_data.get_all_tw_stocks = lambda: []
fake_data.fetch_stock_data = lambda *args, **kwargs: pd.DataFrame()
fake_data.load_from_db = lambda *args, **kwargs: pd.DataFrame()
sys.modules['core.data'] = fake_data

from backend import backtest


@pytest.fixture(autouse=True)
def _no_db_calendar(monkeypatch):
    """Every test in this module builds synthetic OHLC frames, so the run's `as_of` must come from
    those frames -- not from the developer's real storage.db.

    Without this the module passes in isolation (its core.data stub has no get_db_connection, so
    the DB path returns None) but fails in a full-suite run, where another module has imported the
    real core.data and the DB calendar wins: a 2026 as_of against 2024 fixtures excludes every
    ticker. An order-dependent test is worse than a failing one.
    """
    monkeypatch.setattr(backtest, "resolve_as_of_date_from_db", lambda days_ago: None)


def test_run_time_machine_uses_entry_day_features_and_limit(monkeypatch):
    dates = pd.date_range("2024-01-01", periods=6, freq="D")
    df = pd.DataFrame(
        {
            "date": dates,
            "open": [10, 11, 12, 13, 14, 15],
            "high": [10, 11, 12, 13, 14, 15],
            "low": [10, 11, 12, 13, 14, 15],
            "close": [10, 11, 12, 13, 14, 15],
            "volume": [1000, 1000, 1000, 1000, 1000, 1000],
        }
    )

    monkeypatch.setattr(backtest, "get_all_tw_stocks", lambda: [{"code": "2330", "name": "TSMC"}, {"code": "2317", "name": "HonHai"}])
    monkeypatch.setattr(backtest, "_load_from_db", lambda ticker, **_kwargs: df)

    from core import indicators_v2
    monkeypatch.setattr(indicators_v2, "compute_v4_indicators", lambda in_df: in_df)

    from core import rise_score_v2

    def _score(in_df):
        out = in_df.copy()
        out["total_score_v2"] = list(range(1, len(out) + 1))
        return out

    monkeypatch.setattr(rise_score_v2, "calculate_rise_score_v2", _score)
    monkeypatch.setattr(backtest, "predict_prob", lambda *_args, **_kwargs: {"prob": 0.8})

    result = backtest.run_time_machine(days_ago=2, limit=1)

    assert len(result["top_picks"]) == 1
    top = result["top_picks"][0]
    assert top["entry_date"] == dates[-2]
    assert top["rise_score_at_entry"] == 5.0


def test_run_time_machine_returns_requested_top_n(monkeypatch):
    dates = pd.date_range("2024-01-01", periods=8, freq="D")

    monkeypatch.setattr(
        backtest,
        "get_all_tw_stocks",
        lambda: [{"code": f"STK{i}", "name": f"Stock{i}"} for i in range(5)],
    )

    def _load(_ticker, **_kwargs):
        return pd.DataFrame(
            {
                "date": dates,
                "open": [10] * len(dates),
                "high": [10] * len(dates),
                "low": [10] * len(dates),
                "close": [10] * len(dates),
                "volume": [1000] * len(dates),
            }
        )

    monkeypatch.setattr(backtest, "_load_from_db", _load)

    from core import indicators_v2
    monkeypatch.setattr(indicators_v2, "compute_v4_indicators", lambda in_df: in_df)

    from core import rise_score_v2
    monkeypatch.setattr(
        rise_score_v2,
        "calculate_rise_score_v2",
        lambda in_df: in_df.assign(total_score_v2=1.0),
    )

    monkeypatch.setattr(backtest, "predict_prob", lambda *_args, **_kwargs: {"prob": 0.9})

    result = backtest.run_time_machine(days_ago=3, limit=3)

    assert len(result["top_picks"]) == 3


def test_run_time_machine_caps_outcome_window_to_20_days(monkeypatch):
    dates = pd.date_range("2024-01-01", periods=40, freq="D")
    closes = [100.0] * 31 + [120.0] * 9
    highs = closes[:]
    lows = closes[:]

    monkeypatch.setattr(backtest, "get_all_tw_stocks", lambda: [{"code": "2330", "name": "TSMC"}])

    def _load(_ticker, **_kwargs):
        return pd.DataFrame(
            {
                "date": dates,
                "open": closes,
                "high": highs,
                "low": lows,
                "close": closes,
                "volume": [1000] * len(dates),
            }
        )

    monkeypatch.setattr(backtest, "_load_from_db", _load)

    from core import indicators_v2
    monkeypatch.setattr(indicators_v2, "compute_v4_indicators", lambda in_df: in_df)

    from core import rise_score_v2
    monkeypatch.setattr(rise_score_v2, "calculate_rise_score_v2", lambda in_df: in_df.assign(total_score_v2=1.0))

    monkeypatch.setattr(backtest, "predict_prob", lambda *_args, **_kwargs: {"prob": 0.9})

    result = backtest.run_time_machine(days_ago=30, limit=1)
    top = result["top_picks"][0]

    assert top["sniper_result"] == "PENDING"
    assert top["holding_days"] == 20


def test_run_time_machine_uses_intraday_stop_before_target(monkeypatch):
    dates = pd.date_range("2024-01-01", periods=8, freq="D")

    # Entry index for days_ago=3 is 5 (close=100), future starts at index 6
    opens = [100, 100, 100, 100, 100, 100, 100, 100]
    highs = [100, 100, 100, 100, 100, 100, 120, 100]  # +20% on first future day
    lows = [100, 100, 100, 100, 100, 100, 90, 100]    # -10% on first future day
    closes = [100, 100, 100, 100, 100, 100, 105, 100]

    monkeypatch.setattr(backtest, "get_all_tw_stocks", lambda: [{"code": "2330", "name": "TSMC"}])

    def _load(_ticker, **_kwargs):
        return pd.DataFrame(
            {
                "date": dates,
                "open": opens,
                "high": highs,
                "low": lows,
                "close": closes,
                "volume": [1000] * len(dates),
            }
        )

    monkeypatch.setattr(backtest, "_load_from_db", _load)

    from core import indicators_v2
    monkeypatch.setattr(indicators_v2, "compute_v4_indicators", lambda in_df: in_df)

    from core import rise_score_v2
    monkeypatch.setattr(rise_score_v2, "calculate_rise_score_v2", lambda in_df: in_df.assign(total_score_v2=1.0))

    monkeypatch.setattr(backtest, "predict_prob", lambda *_args, **_kwargs: {"prob": 0.9})

    result = backtest.run_time_machine(days_ago=3, limit=1)
    top = result["top_picks"][0]

    # Precedence guard: the bar touches BOTH barriers (+20% high, -10% low) and the stop wins.
    assert top["sniper_result"] == "STOP"
    # Settlement is the stop price, not the session low — the bar opened at the entry price,
    # so there is no gap and the stop order filled exactly at -5%.
    assert top["actual_return"] == pytest.approx(-0.05)


def test_run_time_machine_rejects_non_positive_days_ago():
    result = backtest.run_time_machine(days_ago=0, limit=1)
    assert result["error"] == "days_ago must be > 0"


def test_run_time_machine_rejects_non_positive_limit():
    result = backtest.run_time_machine(days_ago=5, limit=0)
    assert result["error"] == "limit must be > 0"


def test_run_time_machine_summary_best_stock_uses_highest_return(monkeypatch):
    dates = pd.date_range("2024-01-01", periods=8, freq="D")

    monkeypatch.setattr(
        backtest,
        "get_all_tw_stocks",
        lambda: [
            {"code": "HIGH_AI_LOW_RET", "name": "HighAI"},
            {"code": "LOW_AI_HIGH_RET", "name": "HighRet"},
        ],
    )

    def _load(ticker, **_kwargs):
        if ticker == "HIGH_AI_LOW_RET":
            closes = [100, 100, 100, 100, 100, 100, 99, 99]
        else:
            closes = [100, 100, 100, 100, 100, 100, 110, 110]
        return pd.DataFrame(
            {
                "date": dates,
                "open": closes,
                "high": closes,
                "low": closes,
                "close": closes,
                "volume": [1000] * len(dates),
            }
        )

    monkeypatch.setattr(backtest, "_load_from_db", _load)

    from core import indicators_v2
    monkeypatch.setattr(indicators_v2, "compute_v4_indicators", lambda in_df: in_df)

    from core import rise_score_v2
    monkeypatch.setattr(
        rise_score_v2,
        "calculate_rise_score_v2",
        lambda in_df: in_df.assign(total_score_v2=1.0),
    )

    def _predict(df, **_kwargs):
        # HIGH_AI_LOW_RET has higher AI prob but lower realized return
        if df.iloc[-1]["close"] <= 100:
            return {"prob": 0.95}
        return {"prob": 0.80}

    monkeypatch.setattr(backtest, "predict_prob", _predict)

    result = backtest.run_time_machine(days_ago=3, limit=2)

    assert result["summary"]["best_stock"] == "HighRet"
    assert result["summary"]["best_return"] == 0.1


def test_run_time_machine_applies_liquidity_prefilter(monkeypatch):
    import os
    dates = pd.date_range("2024-01-01", periods=10, freq="D")

    monkeypatch.setattr(
        backtest,
        "get_all_tw_stocks",
        lambda: [{"code": "HI", "name": "Hi"}, {"code": "LO", "name": "Lo"}],
    )

    def _load(ticker, **_kwargs):
        vol = [100000] * len(dates) if ticker == "HI" else [100] * len(dates)
        return pd.DataFrame({
            "date": dates, "open": [10]*len(dates), "high": [10]*len(dates), "low": [10]*len(dates),
            "close": [10]*len(dates), "volume": vol
        })

    monkeypatch.setattr(backtest, "_load_from_db", _load)
    from core import indicators_v2
    monkeypatch.setattr(indicators_v2, "compute_v4_indicators", lambda in_df: in_df)
    from core import rise_score_v2
    monkeypatch.setattr(rise_score_v2, "calculate_rise_score_v2", lambda in_df: in_df.assign(total_score_v2=1.0))
    monkeypatch.setattr(backtest, "predict_prob", lambda *_args, **_kwargs: {"prob": 0.9})

    monkeypatch.setenv("BACKTEST_MIN_AVG_VOLUME", "10000")
    result = backtest.run_time_machine(days_ago=3, limit=5, candidate_pool_limit=2)
    assert result["candidate_pool_size"] == 1
    assert result["top_picks"][0]["ticker"] == "HI"
    monkeypatch.delenv("BACKTEST_MIN_AVG_VOLUME", raising=False)


def test_run_time_machine_reuses_loaded_frames_for_prefilter_and_scoring(monkeypatch):
    dates = pd.date_range("2024-01-01", periods=12, freq="D")

    monkeypatch.setattr(
        backtest,
        "get_all_tw_stocks",
        lambda: [{"code": "A1", "name": "A1"}, {"code": "A2", "name": "A2"}],
    )

    calls = {"A1": 0, "A2": 0}

    def _load(ticker, **_kwargs):
        calls[ticker] += 1
        return pd.DataFrame(
            {
                "date": dates,
                "open": [10] * len(dates),
                "high": [10] * len(dates),
                "low": [10] * len(dates),
                "close": [10] * len(dates),
                "volume": [20000] * len(dates),
            }
        )

    monkeypatch.setattr(backtest, "_load_from_db", _load)

    from core import indicators_v2
    monkeypatch.setattr(indicators_v2, "compute_v4_indicators", lambda in_df: in_df)

    from core import rise_score_v2
    monkeypatch.setattr(rise_score_v2, "calculate_rise_score_v2", lambda in_df: in_df.assign(total_score_v2=1.0))

    monkeypatch.setattr(backtest, "predict_prob", lambda *_args, **_kwargs: {"prob": 0.9})

    monkeypatch.setenv("BACKTEST_MIN_AVG_VOLUME", "10000")
    _ = backtest.run_time_machine(days_ago=3, limit=2, candidate_pool_limit=2)

    assert calls["A1"] == 1
    assert calls["A2"] == 1
    monkeypatch.delenv("BACKTEST_MIN_AVG_VOLUME", raising=False)


def test_run_time_machine_singleflight_cache_for_duplicate_ticker(monkeypatch):
    import threading

    dates = pd.date_range("2024-01-01", periods=12, freq="D")
    same_ticker_candidates = [
        {"code": "2330", "name": "TSMC-A"},
        {"code": "2330", "name": "TSMC-B"},
    ]

    monkeypatch.setattr(backtest, "get_all_tw_stocks", lambda: same_ticker_candidates)

    call_count = {"count": 0}
    load_barrier = threading.Barrier(2)

    def _load(_ticker, **_kwargs):
        call_count["count"] += 1
        try:
            load_barrier.wait(timeout=0.2)
        except threading.BrokenBarrierError:
            pass
        return pd.DataFrame(
            {
                "date": dates,
                "open": [10] * len(dates),
                "high": [10] * len(dates),
                "low": [10] * len(dates),
                "close": [10] * len(dates),
                "volume": [20000] * len(dates),
            }
        )

    monkeypatch.setattr(backtest, "_load_from_db", _load)

    from core import indicators_v2
    monkeypatch.setattr(indicators_v2, "compute_v4_indicators", lambda in_df: in_df)

    from core import rise_score_v2
    monkeypatch.setattr(rise_score_v2, "calculate_rise_score_v2", lambda in_df: in_df.assign(total_score_v2=1.0))

    monkeypatch.setattr(backtest, "predict_prob", lambda *_args, **_kwargs: {"prob": 0.9})

    result = backtest.run_time_machine(days_ago=3, limit=2, candidate_pool_limit=2)

    assert call_count["count"] == 1
    assert len(result["top_picks"]) == 2


def test_run_time_machine_applies_transaction_costs_and_sharpe(monkeypatch):
    dates = pd.date_range("2024-01-01", periods=8, freq="D")

    monkeypatch.setattr(
        backtest,
        "get_all_tw_stocks",
        lambda: [
            {"code": "STK1", "name": "Stock1"},
            {"code": "STK2", "name": "Stock2"},
        ],
    )

    def _load(ticker, **_kwargs):
        if ticker == "STK1":
            closes = [100, 100, 100, 100, 100, 100, 110, 110]
            lows = closes
        else:
            closes = [100, 100, 100, 100, 100, 100, 90, 90]
            lows = [100, 100, 100, 100, 100, 100, 98, 98]
        return pd.DataFrame(
            {
                "date": dates,
                "open": [100] * len(dates),
                "high": closes,
                "low": lows,
                "close": closes,
                "volume": [1000] * len(dates),
            }
        )

    monkeypatch.setattr(backtest, "_load_from_db", _load)

    from core import indicators_v2
    monkeypatch.setattr(indicators_v2, "compute_v4_indicators", lambda in_df: in_df)

    from core import rise_score_v2
    monkeypatch.setattr(rise_score_v2, "calculate_rise_score_v2", lambda in_df: in_df.assign(total_score_v2=1.0))

    monkeypatch.setattr(backtest, "predict_prob", lambda *_args, **_kwargs: {"prob": 0.9})

    # Custom costs: commission_rate=0.002, tax_rate=0.003, slippage_rate=0.001
    result = backtest.run_time_machine(
        days_ago=3,
        limit=2,
        commission_rate=0.002,
        tax_rate=0.003,
        slippage_rate=0.001,
    )

    picks = result["top_picks"]
    assert len(picks) == 2

    # Verify Stock 1: raw return = 10%, net return = (1.1 * 0.994 / 1.003) - 1 = ~9.01%
    s1 = next(p for p in picks if p["ticker"] == "STK1")
    assert s1["actual_return"] == 0.1
    assert round(s1["net_return"], 4) == 0.0901

    # Verify Stock 2: raw return = -10%, net return = (0.9 * 0.994 / 1.003) - 1 = ~-10.81%
    s2 = next(p for p in picks if p["ticker"] == "STK2")
    assert s2["actual_return"] == -0.1
    assert round(s2["net_return"], 4) == -0.1081

    # Drawdown verification: STK2 worst drawdown should be -2.0%
    assert result["summary"]["worst_drawdown"] == -2.0  # -0.02 * 100
    
    # Sharpe Ratio: mean / std
    net_returns = [s1["net_return"], s2["net_return"]]
    mean_val = sum(net_returns) / 2
    import math
    variance = sum((x - mean_val) ** 2 for x in net_returns) / 1 # sample variance (ddof=1)
    std_val = math.sqrt(variance)
    expected_sharpe = mean_val / std_val
    assert abs(result["summary"]["sharpe_ratio"] - round(expected_sharpe, 3)) < 1e-5


def test_run_time_machine_custom_strategy_params(monkeypatch):
    dates = pd.date_range("2024-01-01", periods=10, freq="D")
    # Entry index for days_ago=5 is 5 (10 - 5 = 5)
    opens =  [100] * 10
    highs =  [100, 100, 100, 100, 100, 100, 104, 104, 108, 104] # index 8 is Future Day 3
    lows =   [100, 100, 100, 100, 100, 100, 96,  96,  96,  92]  # index 9 is Future Day 4
    closes = [100] * 10

    monkeypatch.setattr(backtest, "get_all_tw_stocks", lambda: [{"code": "2330", "name": "TSMC"}])
    monkeypatch.setattr(backtest, "_load_from_db", lambda *args, **kwargs: pd.DataFrame({
        "date": dates, "open": opens, "high": highs, "low": lows, "close": closes, "volume": [1000]*len(dates)
    }))

    from core import indicators_v2
    monkeypatch.setattr(indicators_v2, "compute_v4_indicators", lambda in_df: in_df)
    from core import rise_score_v2
    monkeypatch.setattr(rise_score_v2, "calculate_rise_score_v2", lambda in_df: in_df.assign(total_score_v2=1.0))
    monkeypatch.setattr(backtest, "predict_prob", lambda *_args, **_kwargs: {"prob": 0.9})

    # Test Case 1: Custom Target Gain (0.07) hits on Day 3.
    # Settles at the custom target, not the +8% session high (the bar opens at 100, no gap).
    res1 = backtest.run_time_machine(days_ago=5, limit=1, target_gain=0.07, stop_loss=0.10, holding_days=5)
    pick1 = res1["top_picks"][0]
    assert pick1["sniper_result"] == "HIT"
    assert pick1["actual_return"] == pytest.approx(0.07)
    assert pick1["holding_days"] == 3

    # Test Case 2: Custom Stop Loss (0.06) hits on Day 4 (with high target_gain=0.20).
    # Settles at the custom stop, not the -8% session low (the bar opens at 100, no gap).
    res2 = backtest.run_time_machine(days_ago=5, limit=1, target_gain=0.20, stop_loss=0.06, holding_days=5)
    pick2 = res2["top_picks"][0]
    assert pick2["sniper_result"] == "STOP"
    assert pick2["actual_return"] == pytest.approx(-0.06)
    assert pick2["holding_days"] == 4

    # Test Case 3: Custom Holding Days (2) exit on Day 2
    res3 = backtest.run_time_machine(days_ago=5, limit=1, target_gain=0.20, stop_loss=0.10, holding_days=2)
    pick3 = res3["top_picks"][0]
    assert pick3["sniper_result"] == "PENDING"
    assert pick3["holding_days"] == 2


def test_profit_factor_is_none_when_no_losses(monkeypatch):
    """Honesty (#4): zero losing trades → profit_factor None (N/A), not a 9999 sentinel."""
    dates = pd.date_range("2024-01-01", periods=6, freq="D")
    df = pd.DataFrame(
        {
            "date": dates,
            "open": [10, 11, 12, 13, 14, 15],
            "high": [10, 11, 12, 13, 14, 15],
            "low": [10, 11, 12, 13, 14, 15],
            "close": [10, 11, 12, 13, 14, 15],
            "volume": [1000] * 6,
        }
    )

    monkeypatch.setattr(backtest, "get_all_tw_stocks", lambda: [{"code": "2330", "name": "TSMC"}])
    monkeypatch.setattr(backtest, "_load_from_db", lambda ticker, **_kwargs: df)

    from core import indicators_v2
    monkeypatch.setattr(indicators_v2, "compute_v4_indicators", lambda in_df: in_df)

    from core import rise_score_v2

    def _score(in_df):
        out = in_df.copy()
        out["total_score_v2"] = list(range(1, len(out) + 1))
        return out

    monkeypatch.setattr(rise_score_v2, "calculate_rise_score_v2", _score)
    monkeypatch.setattr(backtest, "predict_prob", lambda *_a, **_k: {"prob": 0.8})

    result = backtest.run_time_machine(days_ago=2, limit=1)
    # The only pick rises in price → no losing trades → profit factor is undefined.
    assert result["summary"]["profit_factor"] is None
    assert result["summary"]["net_profit_factor"] is None


# --- Settlement realism (docs/specs/backtest-settlement-realism.md) -------------------------
#
# run_time_machine used to book a winning trade at the session HIGH and a losing trade at the
# session LOW. The error was one-directional, so every headline summary metric was inflated.
# These tests pin the achievable-fill model: an order resting at a barrier fills AT that
# barrier, or at the open when the bar gapped straight through it.


def _settle(monkeypatch, *, opens, highs, lows, closes, **kwargs):
    """Run a single-ticker backtest over a hand-built OHLC frame and return its one pick.

    8 bars, days_ago=3 → entry at index 5, outcome window starts at index 6.
    """
    dates = pd.date_range("2024-01-01", periods=len(closes), freq="D")

    monkeypatch.setattr(backtest, "get_all_tw_stocks", lambda: [{"code": "2330", "name": "TSMC"}])
    monkeypatch.setattr(
        backtest,
        "_load_from_db",
        lambda _ticker, **_kwargs: pd.DataFrame(
            {
                "date": dates,
                "open": opens,
                "high": highs,
                "low": lows,
                "close": closes,
                "volume": [1000] * len(dates),
            }
        ),
    )

    from core import indicators_v2
    monkeypatch.setattr(indicators_v2, "compute_v4_indicators", lambda in_df: in_df)

    from core import rise_score_v2
    monkeypatch.setattr(
        rise_score_v2, "calculate_rise_score_v2", lambda in_df: in_df.assign(total_score_v2=1.0)
    )
    monkeypatch.setattr(backtest, "predict_prob", lambda *_a, **_k: {"prob": 0.9})

    result = backtest.run_time_machine(days_ago=3, limit=1, **kwargs)
    return result["top_picks"][0]


def test_hit_settles_at_target_not_session_high(monkeypatch):
    # Bar 6 opens at the entry price and runs to +30%, far past the 15% target. A limit sell
    # resting at +15% fills at +15% — it does not capture the session high.
    top = _settle(
        monkeypatch,
        opens=[100] * 8,
        highs=[100, 100, 100, 100, 100, 100, 130, 100],
        lows=[100] * 8,
        closes=[100, 100, 100, 100, 100, 100, 125, 100],
    )

    assert top["sniper_result"] == "HIT"
    assert top["actual_return"] == pytest.approx(0.15)
    # The excursion measure still reports the real intraday extreme (spec AC4).
    assert top["max_gain"] == pytest.approx(0.30)


def test_hit_gap_open_above_target_settles_at_open(monkeypatch):
    # Bar 6 GAPS OPEN at +22%, above the 15% target. A resting limit sell is filled at the
    # open, which is better than the limit — but still not the +35% session high.
    top = _settle(
        monkeypatch,
        opens=[100, 100, 100, 100, 100, 100, 122, 100],
        highs=[100, 100, 100, 100, 100, 100, 135, 100],
        lows=[100, 100, 100, 100, 100, 100, 121, 100],
        closes=[100, 100, 100, 100, 100, 100, 130, 100],
    )

    assert top["sniper_result"] == "HIT"
    assert top["actual_return"] == pytest.approx(0.22)


def test_stop_settles_at_stop_not_session_low(monkeypatch):
    # Bar 6 opens at the entry price and sinks to -18%, past the 5% stop. The stop triggers
    # and fills at -5%; the position never actually paid the session low.
    top = _settle(
        monkeypatch,
        opens=[100] * 8,
        highs=[100] * 8,
        lows=[100, 100, 100, 100, 100, 100, 82, 100],
        closes=[100, 100, 100, 100, 100, 100, 85, 100],
    )

    assert top["sniper_result"] == "STOP"
    assert top["actual_return"] == pytest.approx(-0.05)
    # The excursion measure still reports the real intraday extreme (spec AC4).
    assert top["max_drawdown"] == pytest.approx(-0.18)


def test_stop_gap_open_below_stop_settles_at_open(monkeypatch):
    # Bar 6 GAPS OPEN at -12%, straight through the 5% stop. The stop becomes a market order
    # and fills at that worse open — this is the one case where a loss exceeds the stop.
    top = _settle(
        monkeypatch,
        opens=[100, 100, 100, 100, 100, 100, 88, 100],
        highs=[100, 100, 100, 100, 100, 100, 89, 100],
        lows=[100, 100, 100, 100, 100, 100, 80, 100],
        closes=[100, 100, 100, 100, 100, 100, 85, 100],
    )

    assert top["sniper_result"] == "STOP"
    assert top["actual_return"] == pytest.approx(-0.12)


def test_net_of_cost_arithmetic_applies_to_settled_roi(monkeypatch):
    # The buy/sell cost asymmetry must compound onto the SETTLED roi, not the session high.
    top = _settle(
        monkeypatch,
        opens=[100] * 8,
        highs=[100, 100, 100, 100, 100, 100, 130, 100],
        lows=[100] * 8,
        closes=[100, 100, 100, 100, 100, 100, 125, 100],
    )

    commission_rate, tax_rate, slippage_rate = 0.001425, 0.003, 0.001
    buy_cost = commission_rate + slippage_rate
    sell_cost = commission_rate + tax_rate + slippage_rate
    expected_net = ((1.0 + 0.15) * (1.0 - sell_cost) / (1.0 + buy_cost)) - 1.0

    assert top["actual_return"] == pytest.approx(0.15)
    assert top["net_return"] == pytest.approx(expected_net)


def test_settlement_never_leaves_the_bar_on_dirty_open(monkeypatch):
    # A dirty feed can put `open` outside [low, high] — an unadjusted open against
    # split-adjusted extremes, or a column-order shift in a bulk parser. The high/low are the
    # bar's extremes by construction, so settlement is clamped back into them; without the
    # clamp this books a fill 5 points worse than the session's worst print.
    top = _settle(
        monkeypatch,
        opens=[100, 100, 100, 100, 100, 100, 80, 100],   # open BELOW the low — impossible bar
        highs=[100] * 8,
        lows=[100, 100, 100, 100, 100, 100, 85, 100],
        closes=[100, 100, 100, 100, 100, 100, 90, 100],
    )

    assert top["sniper_result"] == "STOP"
    assert top["actual_return"] == pytest.approx(-0.15)  # the low, not the -0.20 open

    # Mirror case: an open above the high on a target bar.
    top = _settle(
        monkeypatch,
        opens=[100, 100, 100, 100, 100, 100, 160, 100],  # open ABOVE the high — impossible bar
        highs=[100, 100, 100, 100, 100, 100, 130, 100],
        lows=[100] * 8,
        closes=[100, 100, 100, 100, 100, 100, 125, 100],
    )

    assert top["sniper_result"] == "HIT"
    assert top["actual_return"] == pytest.approx(0.30)  # the high, not the +0.60 open


def test_settlement_falls_back_to_the_barrier_when_open_is_missing(monkeypatch):
    # yfinance returns NaN opens for halted/partial sessions. Settlement must not raise, and
    # must fall back to the barrier price rather than reaching for a value it does not have.
    nan = float("nan")

    top = _settle(
        monkeypatch,
        opens=[100, 100, 100, 100, 100, 100, nan, 100],
        highs=[100] * 8,
        lows=[100, 100, 100, 100, 100, 100, 82, 100],
        closes=[100, 100, 100, 100, 100, 100, 85, 100],
    )
    assert top["sniper_result"] == "STOP"
    assert top["actual_return"] == pytest.approx(-0.05)

    top = _settle(
        monkeypatch,
        opens=[100, 100, 100, 100, 100, 100, nan, 100],
        highs=[100, 100, 100, 100, 100, 100, 130, 100],
        lows=[100] * 8,
        closes=[100, 100, 100, 100, 100, 100, 125, 100],
    )
    assert top["sniper_result"] == "HIT"
    assert top["actual_return"] == pytest.approx(0.15)


def test_settlement_at_a_bar_that_opens_exactly_on_the_barrier(monkeypatch):
    # The gap comparisons are strict, so an open sitting exactly on the barrier must be a
    # no-op rather than flipping the fill. Nothing pinned this before.
    top = _settle(
        monkeypatch,
        opens=[100, 100, 100, 100, 100, 100, 115, 100],  # exactly +15%, the target
        highs=[100, 100, 100, 100, 100, 100, 130, 100],
        lows=[100, 100, 100, 100, 100, 100, 114, 100],
        closes=[100, 100, 100, 100, 100, 100, 125, 100],
    )
    assert top["sniper_result"] == "HIT"
    assert top["actual_return"] == pytest.approx(0.15)

    top = _settle(
        monkeypatch,
        opens=[100, 100, 100, 100, 100, 100, 95, 100],   # exactly -5%, the stop
        highs=[100, 100, 100, 100, 100, 100, 96, 100],
        lows=[100, 100, 100, 100, 100, 100, 82, 100],
        closes=[100, 100, 100, 100, 100, 100, 85, 100],
    )
    assert top["sniper_result"] == "STOP"
    assert top["actual_return"] == pytest.approx(-0.05)


def test_sharpe_is_none_when_dispersion_is_undefined(monkeypatch):
    # Settlement realism makes zero dispersion reachable: a no-gap HIT settles at exactly
    # target_gain, so a sample where every trade landed on the same barrier has std == 0.
    # That means "undefined", not "no edge" — report None, like profit_factor already does.
    dates = pd.date_range("2024-01-01", periods=8, freq="D")

    monkeypatch.setattr(
        backtest,
        "get_all_tw_stocks",
        lambda: [{"code": "AAA", "name": "AAA"}, {"code": "BBB", "name": "BBB"}],
    )
    # Both tickers run the same bars, so both settle at exactly +15% → std of net returns is 0.
    monkeypatch.setattr(
        backtest,
        "_load_from_db",
        lambda _ticker, **_kwargs: pd.DataFrame(
            {
                "date": dates,
                "open": [100] * 8,
                "high": [100, 100, 100, 100, 100, 100, 130, 100],
                "low": [100] * 8,
                "close": [100, 100, 100, 100, 100, 100, 125, 100],
                "volume": [1000] * 8,
            }
        ),
    )

    from core import indicators_v2
    monkeypatch.setattr(indicators_v2, "compute_v4_indicators", lambda in_df: in_df)

    from core import rise_score_v2
    monkeypatch.setattr(
        rise_score_v2, "calculate_rise_score_v2", lambda in_df: in_df.assign(total_score_v2=1.0)
    )
    monkeypatch.setattr(backtest, "predict_prob", lambda *_a, **_k: {"prob": 0.9})

    result = backtest.run_time_machine(days_ago=3, limit=2)

    assert len(result["top_picks"]) == 2
    assert all(p["sniper_result"] == "HIT" for p in result["top_picks"])
    assert result["summary"]["sharpe_ratio"] is None


# --- Temporal guard and calendar-aligned entry (docs/specs/backtest-temporal-guard.md) --------


def _two_ticker_run(monkeypatch, frames, days_ago=3, **kwargs):
    """Run a backtest over per-ticker frames that deliberately differ in length."""
    monkeypatch.setattr(backtest, "get_all_tw_stocks",
                        lambda: [{"code": t, "name": t} for t in frames])
    monkeypatch.setattr(backtest, "_load_from_db", lambda t, **_k: frames[t])

    from core import indicators_v2
    monkeypatch.setattr(indicators_v2, "compute_v4_indicators", lambda in_df: in_df)
    from core import rise_score_v2
    monkeypatch.setattr(rise_score_v2, "calculate_rise_score_v2",
                        lambda in_df: in_df.assign(total_score_v2=1.0))
    monkeypatch.setattr(backtest, "predict_prob", lambda *_a, **_k: {"prob": 0.9})
    return backtest.run_time_machine(days_ago=days_ago, limit=5, **kwargs)


def _frame(dates, price=100.0):
    return pd.DataFrame({
        "date": dates,
        "open": [price] * len(dates),
        "high": [price] * len(dates),
        "low": [price] * len(dates),
        "close": [price] * len(dates),
        "volume": [1000] * len(dates),
    })


def test_every_pick_enters_on_the_same_calendar_date(monkeypatch):
    """`len(df) - days_ago` is a ROW offset, and row counts differ per ticker, so a ticker with
    missing bars entered on a different DAY. Rows are not time."""
    full = pd.bdate_range("2024-01-01", periods=10)
    # The gap must sit AFTER the entry window, or the row offset and the calendar agree by
    # accident and the test proves nothing. An earlier draft deleted [4,5,6] -- both schemes then
    # produced 2024-01-10 and the test was vacuous. Deleting [8] makes the old scheme land on
    # 2024-01-09 for SHORT and 2024-01-10 for FULL: two tickers, two days, one "cross-section".
    short = full.delete([8])
    days_ago = 3
    assert (
        pd.to_datetime(_frame(full).iloc[10 - days_ago]['date'])
        != pd.to_datetime(_frame(short).iloc[9 - days_ago]['date'])
    ), "fixture must actually exercise the defect"

    result = _two_ticker_run(monkeypatch, {"FULL": _frame(full), "SHORT": _frame(short)},
                             days_ago=days_ago)

    picks = result["top_picks"]
    assert len(picks) == 2
    as_of = pd.to_datetime(result["simulated_date"])
    # Both tickers traded on as_of, so both must enter exactly there -- not merely "somewhere at
    # or before it". The weaker form would pass under the row offset too.
    for p in picks:
        assert pd.to_datetime(p["entry_date"]) == as_of, (
            f"{p['ticker']} entered {p['entry_date']}, run as_of is {as_of}"
        )
    # And the run reports its own as_of, not whichever pick happened to sort first.
    assert result["simulated_date"] == str(as_of.date())


def test_a_ticker_with_no_data_at_as_of_is_excluded_and_counted(monkeypatch):
    """Excluding a ticker is honest; entering it on some other day is not. The count is reported
    so a thin cross-section is visible rather than inferred."""
    full = pd.bdate_range("2024-01-01", periods=12)
    stale = pd.bdate_range("2023-06-01", periods=12)   # stopped trading long before as_of
    result = _two_ticker_run(monkeypatch, {"FULL": _frame(full), "STALE": _frame(stale)})

    assert [p["ticker"] for p in result["top_picks"]] == ["FULL"]
    assert result["excluded_no_data_at_as_of"] == 1


def test_model_temporal_scope_fails_toward_in_sample(monkeypatch):
    """An unmarked in-sample number is the failure this epic exists to remove, so anything
    indeterminate reports the pessimistic reading."""
    full = pd.bdate_range("2024-01-01", periods=10)
    frames = {"FULL": _frame(full)}

    import core.ai.predictor as predictor
    monkeypatch.setattr(predictor, "get_model_version", lambda: "v4.x")

    # REAL models_history.json entries carry `timestamp` in %Y%m%d_%H%M form and have NO
    # `trained_at` key at all -- that lives inside the pickled metadata. Reading only trained_at
    # hard-wired this field to "in_sample" forever, and pd.to_datetime RAISES on the compact form,
    # so a naive key swap would have stayed just as inert. These fixtures use the real shape.
    monkeypatch.setattr(predictor, "list_available_models",
                        lambda: [{"version": "v4.x", "timestamp": "20240601_2031"}])
    assert _two_ticker_run(monkeypatch, frames)["model_temporal_scope"] == "in_sample"

    monkeypatch.setattr(predictor, "list_available_models",
                        lambda: [{"version": "v4.x", "timestamp": "20230101_0900"}])
    assert _two_ticker_run(monkeypatch, frames)["model_temporal_scope"] == "as_of_model"

    # An explicit trained_at still works, in either form.
    monkeypatch.setattr(predictor, "list_available_models",
                        lambda: [{"version": "v4.x", "trained_at": "2023-01-01T00:00:00"}])
    assert _two_ticker_run(monkeypatch, frames)["model_temporal_scope"] == "as_of_model"

    # Neither key -> pessimistic, not optimistic.
    monkeypatch.setattr(predictor, "list_available_models", lambda: [{"version": "v4.x"}])
    assert _two_ticker_run(monkeypatch, frames)["model_temporal_scope"] == "in_sample"


def test_gap_open_above_target_on_a_stop_bar_settles_hit_at_the_open(monkeypatch):
    """A bar that gaps open through the target is NOT ambiguous: the resting limit sell was
    marketable on the session's first print, so it filled before any tick could reach the stop.
    Deferred from #1 on measured grounds; closed here."""
    top = _settle(
        monkeypatch,
        opens=[100, 100, 100, 100, 100, 100, 122, 100],   # gaps open at +22%, above the target
        highs=[100, 100, 100, 100, 100, 100, 135, 100],
        lows=[100, 100, 100, 100, 100, 100, 80, 100],     # and also breaches the stop intrabar
        closes=[100, 100, 100, 100, 100, 100, 90, 100],
    )

    assert top["sniper_result"] == "HIT"
    assert top["actual_return"] == pytest.approx(0.22)


def test_intrabar_both_barriers_still_resolves_to_the_stop(monkeypatch):
    """Regression guard: precedence is unchanged for genuine intrabar ambiguity, where the order
    of the two touches really is unknowable."""
    top = _settle(
        monkeypatch,
        opens=[100] * 8,                                   # opens BETWEEN the barriers
        highs=[100, 100, 100, 100, 100, 100, 130, 100],
        lows=[100, 100, 100, 100, 100, 100, 80, 100],
        closes=[100, 100, 100, 100, 100, 100, 90, 100],
    )

    assert top["sniper_result"] == "STOP"
    assert top["actual_return"] == pytest.approx(-0.05)


def test_resolve_entry_index_picks_the_last_bar_at_or_before_as_of():
    """Directly pins the contract the end-to-end run depends on."""
    dates = pd.bdate_range("2024-01-01", periods=10)
    df = _frame(dates)
    as_of = dates[6]

    assert backtest.resolve_entry_index(df, as_of) == 6
    # A ticker that did not trade on as_of enters on its last earlier bar...
    gapped = _frame(dates.delete(6))
    assert backtest.resolve_entry_index(gapped, as_of) == 5
    # ...but only within tolerance. Beyond it, the ticker was not trading in this window.
    stale = _frame(pd.bdate_range("2023-06-01", periods=10))
    assert backtest.resolve_entry_index(stale, as_of) is None
    # And a bar with no outcome window cannot be an entry.
    assert backtest.resolve_entry_index(_frame(dates), dates[-1]) is None
    assert backtest.resolve_entry_index(_frame(dates), pd.Timestamp("2020-01-01")) is None


def test_calendar_entry_is_bounded_by_as_of_where_the_row_offset_was_not():
    """The defect in one assertion.

    A row offset says nothing about WHEN a ticker enters: with different row counts, `len(df) -
    days_ago` lands on a different date per ticker, and for a stale ticker it can be months away
    from the rest of the run. Calendar resolution bounds every entry to `as_of` minus a few days,
    or removes the ticker from the run.
    """
    dates = pd.bdate_range("2024-01-01", periods=10)
    full = _frame(dates)
    short = _frame(dates.delete([7, 8]))                    # gaps straddling the entry window
    stale = _frame(pd.bdate_range("2023-06-01", periods=10))  # stopped trading long ago
    days_ago = 3
    as_of = backtest.resolve_as_of_date([full, short, stale], days_ago)

    def old_entry_date(df):
        return pd.to_datetime(df.iloc[len(df) - days_ago]['date'])

    # The old scheme spreads the same run across unrelated dates -- half a year apart here.
    assert old_entry_date(full) != old_entry_date(short)
    assert (as_of - old_entry_date(stale)).days > 180

    # The new one bounds every surviving entry, and drops what it cannot place.
    for df in (full, short):
        idx = backtest.resolve_entry_index(df, as_of)
        assert idx is not None
        entered = pd.to_datetime(df.iloc[idx]['date'])
        assert entered <= as_of
        assert (as_of - entered).days <= backtest.ENTRY_DATE_TOLERANCE_DAYS
    assert backtest.resolve_entry_index(stale, as_of) is None


def test_a_long_suspension_straddling_as_of_is_excluded_by_the_tolerance():
    """The case the tolerance actually exists for: a stock suspended across `as_of` and resuming
    later. It has bars on BOTH sides, so the "no outcome window" rule does not catch it -- its
    last bar at or before as_of is months stale, and entering there would price a position that
    could not have been opened."""
    suspended = _frame(
        pd.bdate_range("2023-06-01", periods=5).append(pd.bdate_range("2024-02-01", periods=5))
    )
    as_of = pd.Timestamp("2024-01-15")

    idx = backtest.resolve_entry_index(suspended, as_of)
    assert idx is None, "a bar months before as_of is not an entry for this cross-section"

    # Sanity: it is NOT the outcome-window rule doing the work here -- there are later bars.
    dates = pd.to_datetime(suspended['date'])
    last_before = int(np.flatnonzero((dates <= as_of).to_numpy())[-1])
    assert last_before < len(suspended) - 1


def test_calendar_prepass_survives_a_long_run_of_empty_candidates(monkeypatch):
    """The universe is ~1,800 codes while the DB may hold far fewer, so a fixed head slice of the
    candidate list can be entirely empty — which is exactly what happened on the real panel: the
    first 25 candidates all had no data and the run aborted with "not enough trading history".
    The pre-pass must walk the whole list until it finds populated frames."""
    dates = pd.bdate_range("2024-01-01", periods=20)
    populated = {f"HAS{i}": _frame(dates) for i in range(3)}
    empty = {f"NONE{i}": pd.DataFrame() for i in range(400)}
    frames = {**empty, **populated}   # every empty ticker sorts before the populated ones

    monkeypatch.setattr(backtest, "get_all_tw_stocks",
                        lambda: [{"code": t, "name": t} for t in frames])
    monkeypatch.setattr(backtest, "_load_from_db", lambda t, **_k: frames[t])
    from core import indicators_v2
    monkeypatch.setattr(indicators_v2, "compute_v4_indicators", lambda in_df: in_df)
    from core import rise_score_v2
    monkeypatch.setattr(rise_score_v2, "calculate_rise_score_v2",
                        lambda in_df: in_df.assign(total_score_v2=1.0))
    monkeypatch.setattr(backtest, "predict_prob", lambda *_a, **_k: {"prob": 0.9})

    result = backtest.run_time_machine(days_ago=3, limit=5)

    assert "error" not in result or result.get("error") is None
    assert result["simulated_date"] is not None
    assert len(result["top_picks"]) == 3
