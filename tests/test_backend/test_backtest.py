import sys
import types
import pandas as pd

# Prevent heavy module side effects during import.
fake_data = types.ModuleType('core.data')
fake_data.get_all_tw_stocks = lambda: []
fake_data.fetch_stock_data = lambda *args, **kwargs: pd.DataFrame()
fake_data.load_from_db = lambda *args, **kwargs: pd.DataFrame()
sys.modules['core.data'] = fake_data

from backend import backtest


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

    assert top["sniper_result"] == "STOP"
    assert top["actual_return"] == -0.1


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

    # Test Case 1: Custom Target Gain (0.07) hits on Day 3
    res1 = backtest.run_time_machine(days_ago=5, limit=1, target_gain=0.07, stop_loss=0.10, holding_days=5)
    pick1 = res1["top_picks"][0]
    assert pick1["sniper_result"] == "HIT"
    assert pick1["actual_return"] == 0.08
    assert pick1["holding_days"] == 3

    # Test Case 2: Custom Stop Loss (0.06) hits on Day 4 (with high target_gain=0.20)
    res2 = backtest.run_time_machine(days_ago=5, limit=1, target_gain=0.20, stop_loss=0.06, holding_days=5)
    pick2 = res2["top_picks"][0]
    assert pick2["sniper_result"] == "STOP"
    assert pick2["actual_return"] == -0.08
    assert pick2["holding_days"] == 4

    # Test Case 3: Custom Holding Days (2) exit on Day 2
    res3 = backtest.run_time_machine(days_ago=5, limit=1, target_gain=0.20, stop_loss=0.10, holding_days=2)
    pick3 = res3["top_picks"][0]
    assert pick3["sniper_result"] == "PENDING"
    assert pick3["holding_days"] == 2
