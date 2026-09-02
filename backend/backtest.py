import sys
import os
import random
import threading
import numpy as np
import pandas as pd
import time
# Add parent dir
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.data import get_all_tw_stocks, load_from_db as _load_from_db
from core.ai import predict_prob

from core import config
from core.ai.common import BACKTEST_AI_THRESHOLD
from core.logger import setup_logger

logger = setup_logger("backend.backtest")

MODEL_PATH = config.MODEL_PATH
if not os.path.exists(MODEL_PATH):
    logger.warning("AI model not found at %s", MODEL_PATH)

from typing import Optional

# The backtest EXIT parameters (target_gain / stop_loss / holding_days) are USER-TUNABLE
# request args with the defaults below — they define an exit STRATEGY, not the ML training
# labels. Training-label barriers live in core/config.py (ATR_*_MULT in the default 'atr'
# mode; TARGET_GAIN / STOP_LOSS / BUY_TARGET in 'fixed' mode). The only config-sourced
# constant used here is BACKTEST_AI_THRESHOLD (the candidate filter).

# How far before `as_of` a ticker's last bar may sit and still count as "trading on that date".
# Covers a long weekend plus a public holiday; beyond that the ticker is not in this cross-section
# and is excluded from the run rather than entered on some other day.
ENTRY_DATE_TOLERANCE_DAYS = 6


def _model_trained_at(entry):
    """When the model behind a models_history entry was trained, or None.

    Real entries carry `timestamp` in `%Y%m%d_%H%M` form and have **no** `trained_at` key at all --
    that one lives inside the pickled model metadata, which nothing here loads.
    `backend/routes/transparency.py` already compensates the same way. Reading only `trained_at`
    hard-wired `model_temporal_scope` to "in_sample" forever, and `pd.to_datetime` raises on the
    compact timestamp form, so a naive key swap would have landed in the caller's `except` and
    stayed just as inert.
    """
    raw = (entry or {}).get("trained_at") or (entry or {}).get("timestamp")
    if not raw:
        return None
    try:
        return pd.to_datetime(raw, format="%Y%m%d_%H%M")
    except (ValueError, TypeError):
        pass
    try:
        return pd.to_datetime(raw)
    except Exception:
        return None


def resolve_as_of_date_from_db(days_ago: int):
    """The run's entry date, straight from the table's own trading calendar. None if unavailable.

    One query over every date in stock_history, so the answer does not depend on which candidates
    were sampled, on BACKTEST_CANDIDATE_POOL, or on whether the volume prefilter reordered them.
    """
    try:
        from core.data import get_db_connection
    except Exception:
        return None
    conn = None
    try:
        conn = get_db_connection()
        rows = conn.execute(
            "SELECT DISTINCT date FROM stock_history ORDER BY date DESC LIMIT ?",
            (int(days_ago),),
        ).fetchall()
    except Exception:
        return None
    finally:
        if conn is not None:
            try:
                conn.close()
            except Exception:
                pass
    if len(rows) < days_ago:
        return None
    try:
        return pd.to_datetime(rows[days_ago - 1][0])
    except Exception:
        return None


def resolve_as_of_date(frames, days_ago: int):
    """The single calendar date every candidate enters on, `days_ago` trading days back.

    Built from the panel's OWN calendar -- the union of dates in the frames this run actually
    loaded -- so it needs no holiday table, no DB round-trip, and no assumption that every ticker
    trades every day. Returns None when the calendar is too short; the caller reports that rather
    than papering over it.
    """
    all_dates = set()
    for df in frames:
        if df is None or getattr(df, 'empty', True) or 'date' not in df.columns:
            continue
        all_dates.update(pd.to_datetime(df['date']).tolist())
    if len(all_dates) < days_ago:
        return None
    ordered = sorted(all_dates, reverse=True)
    # days_ago counts BACK FROM THE LATEST BAR, matching the previous row-offset semantics
    # (`len(df) - days_ago`): days_ago=1 is the most recent date, 2 the one before it. Only the
    # unit changes -- rows become trading days -- not the meaning of the argument.
    return ordered[days_ago - 1]


def resolve_entry_index(df, as_of_date, tolerance_days: int = ENTRY_DATE_TOLERANCE_DAYS):
    """Row index this ticker enters on for a run whose single entry date is `as_of_date`.

    Returns None when the ticker cannot honestly join the cross-section: no bar at or before
    `as_of`, its last such bar is more than `tolerance_days` earlier (it was not trading in this
    window), or that bar is the frame's last one (no outcome window to walk).

    Excluding a ticker is honest; entering it on some other day is not -- which is what the old
    `len(df) - days_ago` row offset did whenever row counts differed.
    """
    if df is None or getattr(df, 'empty', True) or 'date' not in df.columns:
        return None
    dates = pd.to_datetime(df['date'])
    at_or_before = np.flatnonzero((dates <= as_of_date).to_numpy())
    if len(at_or_before) == 0:
        return None
    idx = int(at_or_before[-1])
    if idx >= len(df) - 1:
        return None
    if (as_of_date - dates.iloc[idx]).days > tolerance_days:
        return None
    return idx


def _passes_liquidity_filter(df: pd.DataFrame, min_avg_volume: int) -> bool:
    if min_avg_volume <= 0:
        return True
    if df.empty or 'volume' not in df.columns:
        return False
    avg_vol = float(df['volume'].tail(min(20, len(df))).mean() or 0)
    return avg_vol >= float(min_avg_volume)


def run_time_machine(
    days_ago=30,
    limit=20,
    version: Optional[str] = None,
    candidate_pool_limit: Optional[int] = None,
    commission_rate: float = 0.001425,
    tax_rate: float = 0.003,
    slippage_rate: float = 0.001,
    target_gain: float = 0.15,
    stop_loss: float = 0.05,
    holding_days: int = 20,
):
    """
    Simulates Top Picks from 'days_ago' and calculates their actual return until now.
    Supports specific model version analysis.
    """
    print(f"[Time Machine] Started (Version: {version or 'latest'}): Traveling back {days_ago} days...")
    start_time = time.perf_counter()

    if days_ago <= 0:
        return {"error": "days_ago must be > 0"}
    if days_ago < 2:
        # With as_of on the latest bar every ticker's entry row is its last, so nothing has an
        # outcome window to walk. Say that, rather than returning "No stocks met requirements".
        return {"error": "days_ago must be >= 2 so each pick has at least one day of outcome"}
    if limit <= 0:
        return {"error": "limit must be > 0"}
    
    # --- FIX LOOK-AHEAD BIAS ---
    # Instead of picking top candidates FROM THE FUTURE, we pick a random sample from the pool.
    all_stocks = get_all_tw_stocks()
    if not all_stocks:
        # Fallback to DB list (but without future sorting bias)
        from core.data import get_db_connection
        conn = get_db_connection()
        tickers = [row[0] for row in conn.execute("SELECT ticker FROM stock_scores ORDER BY ticker").fetchall()]
        all_stocks = [{"code": t} for t in tickers]
        conn.close()

    if not all_stocks:
        return {"error": "Failed to load stock list"}
    
    # We use a random sample to avoid hitting just ETFs at the start of the list.
    random.seed(42) # Deterministic for consistent backtests
    configured_pool_limit = candidate_pool_limit or int(os.getenv("BACKTEST_CANDIDATE_POOL", "300"))
    sample_size = min(len(all_stocks), configured_pool_limit)
    candidates = random.sample(all_stocks, sample_size)

    # We increase the padding to 450 to ensure at least 300+ trading days 
    # are available for indicators (SMA240) even when traveling back 60 days.
    lookback_days = max(days_ago + 450, 730)
    frame_cache = {}
    inflight_loads = {}
    cache_lock = threading.Lock()

    def get_stock_frame(ticker: str) -> pd.DataFrame:
        while True:
            with cache_lock:
                if ticker in frame_cache:
                    return frame_cache[ticker]

                loading_event = inflight_loads.get(ticker)
                if loading_event is None:
                    loading_event = threading.Event()
                    inflight_loads[ticker] = loading_event
                    is_loader = True
                else:
                    is_loader = False

            if is_loader:
                df = pd.DataFrame()
                try:
                    df = _load_from_db(ticker, days=lookback_days)
                finally:
                    with cache_lock:
                        frame_cache[ticker] = df
                        inflight_loads.pop(ticker, None)
                        loading_event.set()
                return df

            loading_event.wait()

    min_avg_volume = int(os.getenv("BACKTEST_MIN_AVG_VOLUME", "0"))
    if min_avg_volume > 0:
        prefiltered = []
        for s in candidates:
            t = s.get("ticker") or s.get("code")
            if not t:
                continue
            df_full = get_stock_frame(t)
            if _passes_liquidity_filter(df_full, min_avg_volume=min_avg_volume):
                prefiltered.append(s)
        candidates = prefiltered
    
    # One calendar date for the whole run. Every candidate enters on its last bar at or before
    # this date, or leaves the run -- a cross-section assembled from different days is not a
    # cross-section.
    # Frames are cached by get_stock_frame, so this pre-pass costs no extra I/O -- the run loads
    # every candidate anyway. It walks the WHOLE candidate list but stops as soon as it has a few
    # populated frames: a fixed head slice is not safe here, because the universe is ~1,800 codes
    # while the DB may hold far fewer, so the first N candidates can all be empty.
    # The calendar comes from the WHOLE table, in one query. Deriving it from a sample of frames
    # made as_of depend on which candidates happened to be sampled first -- so changing
    # BACKTEST_CANDIDATE_POOL, enabling the volume prefilter, or adding tickers would silently
    # shift every number, against this project's own reproducibility claim. It also cost ~90
    # serial loads before the thread pool could start.
    as_of_date = resolve_as_of_date_from_db(days_ago)
    if as_of_date is None:
        # No DB (tests stub core.data) -- fall back to the frames this run will load anyway.
        _calendar_sample = []
        for _s in candidates:
            _t = _s.get("ticker") or _s.get("code")
            if not _t:
                continue
            _df = get_stock_frame(_t)
            if _df is None or _df.empty:
                continue
            _calendar_sample.append(_df)
            if resolve_as_of_date(_calendar_sample, days_ago) is not None:
                break
            if len(_calendar_sample) >= 40:
                break
        as_of_date = resolve_as_of_date(_calendar_sample, days_ago)
    if as_of_date is None:
        return {"error": f"Not enough trading history to resolve an entry date {days_ago} days back"}
    # Why each candidate left the run. Counting them under one label would have been a number
    # a reader cannot act on: "no bar at as_of" and "no outcome window after it" are
    # different facts about the cross-section.
    excluded = []           # no usable bar at or near as_of
    excluded_no_data = []   # ticker has no price rows at all

    print(f"[Analysis] Analyzing {len(candidates)} random candidates as of {as_of_date.date()}...")
    
    from concurrent.futures import ThreadPoolExecutor
    
    def process_stock(stock):
        ticker = stock["ticker"] if "ticker" in stock else stock["code"]
        try:
            # 1. Name Lookup (Improved)
            name = stock.get("name") or ticker
            
            # 2. Fetch/Load Data (bounded window for speed)
            df_full = get_stock_frame(ticker)
            if df_full.empty:
                excluded_no_data.append(ticker)
                return None
            
            # 3. Time Machine Slicing, by CALENDAR DATE rather than row offset.
            # `len(df) - days_ago` is a row offset, and row counts differ per ticker: halts
            # drop rows, stale tickers stop updating, partial backfills leave gaps. A ticker
            # with missing rows entered on a different DAY, so "Top Picks from 30 days ago"
            # was never one cross-section. Rows are not time -- the same confusion that
            # produced the zero-day training embargo, in a different file.
            # No row-count gate here. `len(df) <= days_ago` was the very confusion AC1 removes:
            # a ticker with 25 bars that cover as_of AND a full outcome window is perfectly
            # usable in a days_ago=30 run. resolve_entry_index already rejects the real reasons.
            entry_idx = resolve_entry_index(df_full, as_of_date)
            if entry_idx is None:
                excluded.append(ticker)
                return None

            simulated_date = df_full.iloc[entry_idx]['date']
            entry_price = float(df_full.iloc[entry_idx]['close'])
            current_price = float(df_full.iloc[-1]['close'])
            
            # Use data up to entry day for signal generation, and strictly after entry for outcomes.
            df_past = df_full.iloc[:entry_idx + 1].copy()
            df_future = df_full.iloc[entry_idx + 1: entry_idx + 1 + holding_days].copy()
            
            if df_past.empty:
                return None
                
            # Verify score calculation
            from core.indicators_v2 import compute_v4_indicators
            from core.rise_score_v2 import calculate_rise_score_v2
            df_past = compute_v4_indicators(df_past)
            df_past = calculate_rise_score_v2(df_past)
            
            if 'total_score_v2' not in df_past.columns:
                return None
                
            total_score = float(df_past.iloc[-1]['total_score_v2'])
            
            # AI Probability (with version support)
            ai_result = predict_prob(df_past, version=version)
            ai_prob = ai_result.get('prob', 0.0) if isinstance(ai_result, dict) else (ai_result or 0.0)
            
            # --- STRATEGY FILTER ---
            # Threshold sourced from config.BACKTEST_AI_THRESHOLD (currently {BACKTEST_AI_THRESHOLD})
            if ai_prob < BACKTEST_AI_THRESHOLD: 
                return None
            
            last_observed_close = float(df_future.iloc[-1]['close']) if not df_future.empty else current_price
            roi = (last_observed_close - entry_price) / entry_price if entry_price > 0 else 0.0
            
            # --- SNIPER HIT/MISS ANALYSIS ---
            # Did price hit +target_gain before -stop_loss within the holding window?
            # (target_gain / stop_loss / holding_days are user-tunable — see run_time_machine args.)
            sniper_result = 'PENDING'
            max_drawdown_pct = 0.0
            max_gain_pct = 0.0
            
            # Default holding days and exit date if no target or stop is hit
            actual_holding_days = max(len(df_future), 0)
            default_exit_row = df_future.iloc[-1] if not df_future.empty else df_full.iloc[-1]
            exit_date_actual = default_exit_row['date'].strftime('%Y-%m-%d') if hasattr(default_exit_row['date'], 'strftime') else str(default_exit_row['date'])
            locked_roi = roi # Default to final day ROI
            
            for i in range(len(df_future)):
                row = df_future.iloc[i]
                day_high_pct = (row['high'] - entry_price) / entry_price
                day_low_pct = (row['low'] - entry_price) / entry_price
                day_close_pct = (row['close'] - entry_price) / entry_price
                # Settlement (below) needs the OPEN only for the gap case: an order resting at a
                # barrier fills at the open when the bar opens straight through that barrier.
                # Frames without a usable 'open' fall back to the barrier price itself.
                raw_open = row.get('open')
                day_open_pct = (
                    (float(raw_open) - entry_price) / entry_price
                    if raw_open is not None and pd.notna(raw_open) and entry_price > 0
                    else None
                )
                if day_open_pct is not None:
                    # The high/low are the bar's extremes by construction, but the open is a
                    # separate field a dirty feed can place outside them (an unadjusted open
                    # against split-adjusted extremes, or a column-order shift in a bulk
                    # parser). Settlement must never leave the bar it happened in.
                    day_open_pct = min(max(day_open_pct, day_low_pct), day_high_pct)

                max_gain_pct = max(max_gain_pct, day_high_pct)
                max_drawdown_pct = min(max_drawdown_pct, day_low_pct)

                # A bar that GAPS OPEN at or above the target is not ambiguous: the resting
                # limit sell was marketable on the session's first print, so it filled there
                # before any intrabar path could reach the stop. The stop-before-target
                # precedence below exists for genuine intrabar ambiguity, which this is not.
                # (#1 deferred this on measured grounds -- only 4 of 99,287 real bars are wide
                # enough to touch both barriers -- and #3 closes the deferral.)
                if day_open_pct is not None and day_open_pct >= target_gain:
                    sniper_result = 'HIT'
                    locked_roi = day_open_pct
                    actual_holding_days = i + 1
                    exit_date_actual = row['date'].strftime('%Y-%m-%d') if hasattr(row['date'], 'strftime') else str(row['date'])
                    break

                # Conservative same-day ordering: stop has precedence over target.
                if day_low_pct <= -stop_loss:  # Hit stop loss
                    sniper_result = 'STOP'
                    # A stop fills AT the stop, not at the session low — booking the worst
                    # intraday print charges a loss the position never actually paid. If the
                    # bar gapped open below the stop, the stop became a market order and
                    # filled at that (worse) open.
                    locked_roi = -stop_loss
                    if day_open_pct is not None:
                        if day_open_pct < locked_roi:
                            locked_roi = day_open_pct
                    else:
                        # Without an open we cannot see a gap-down, so the loss is capped at the
                        # stop — the only direction in which this fallback flatters the result.
                        # Say so rather than let it pass silently.
                        logger.warning(
                            "settlement degraded: %s %s has no usable open; stop capped at -%.4f",
                            ticker, row['date'], stop_loss,
                        )
                    actual_holding_days = i + 1
                    exit_date_actual = row['date'].strftime('%Y-%m-%d') if hasattr(row['date'], 'strftime') else str(row['date'])
                    break
                if day_high_pct >= target_gain:  # Hit target
                    sniper_result = 'HIT'
                    # A resting limit sell fills AT the target, not at the session high —
                    # booking the best intraday print credits a gain no order could have
                    # captured. If the bar gapped open above the target, the limit filled at
                    # that (better) open.
                    locked_roi = target_gain
                    if day_open_pct is not None and day_open_pct > locked_roi:
                        locked_roi = day_open_pct
                    actual_holding_days = i + 1
                    exit_date_actual = row['date'].strftime('%Y-%m-%d') if hasattr(row['date'], 'strftime') else str(row['date'])
                    break
                locked_roi = day_close_pct
            
            buy_cost = commission_rate + slippage_rate
            sell_cost = commission_rate + tax_rate + slippage_rate
            net_roi = ((1.0 + locked_roi) * (1.0 - sell_cost) / (1.0 + buy_cost)) - 1.0

            return {
                "ticker": ticker,
                "name": name,
                "entry_date": simulated_date,
                "entry_price": entry_price,
                "current_price": current_price,
                "ai_prob_at_entry": ai_prob,
                "rise_score_at_entry": total_score,
                "actual_return": locked_roi,
                "net_return": net_roi,
                "sniper_result": sniper_result,
                "max_gain": max_gain_pct,
                "max_drawdown": max_drawdown_pct,
                "holding_days": actual_holding_days,
                "exit_date": exit_date_actual
            }
        except Exception as e:
            logger.warning("Backtest skipped %s: %s", ticker, e)
            return None

    results = []
    # Optimize workers based on CPU count (I/O reading DB + CPU processing indicators)
    max_threads = min(config.CPU_COUNT * 2, len(candidates), 20)
    with ThreadPoolExecutor(max_workers=max_threads) as executor:
        futures = [executor.submit(process_stock, s) for s in candidates]
        for f in futures:
            res = f.result()
            if res: results.append(res)

    # 4. RANKING
    df_res = pd.DataFrame(results)
    
    if df_res.empty:
        return {"error": "No stocks met requirements", "summary": {"avg_return": 0, "win_rate": 0, "sniper_hit_rate": 0}}
        
    df_res = df_res.sort_values(by="ai_prob_at_entry", ascending=False)
    
    # Top N for Concentrated Strategy
    top_n = max(1, int(limit)) if limit else 10
    top_picks = df_res.head(top_n).to_dict('records')
     # Summary Stats for Top Picks
    top_df = df_res.head(top_n)
    avg_return = float(top_df['actual_return'].mean())
    avg_net_return = float(top_df['net_return'].mean())
    win_count = len(top_df[top_df['actual_return'] > 0])
    net_win_count = len(top_df[top_df['net_return'] > 0])
    
    # Sniper-specific stats
    sniper_hits = len(top_df[top_df['sniper_result'] == 'HIT'])
    sniper_stops = len(top_df[top_df['sniper_result'] == 'STOP'])
    sniper_total = sniper_hits + sniper_stops
    sniper_hit_rate = sniper_hits / sniper_total if sniper_total > 0 else 0
    
    # Max drawdown across all top picks
    avg_max_drawdown = top_df['max_drawdown'].mean() if 'max_drawdown' in top_df.columns else 0
    worst_drawdown = top_df['max_drawdown'].min() if 'max_drawdown' in top_df.columns else 0
    
    # Profit factor: total gains / total losses
    gains = top_df[top_df['actual_return'] > 0]['actual_return'].sum()
    losses = abs(top_df[top_df['actual_return'] < 0]['actual_return'].sum())
    profit_factor = gains / losses if losses > 0 else None  # None = undefined (no losses) → shown as N/A, not a fake 9999

    # Net Profit factor
    net_gains = top_df[top_df['net_return'] > 0]['net_return'].sum()
    net_losses = abs(top_df[top_df['net_return'] < 0]['net_return'].sum())
    net_profit_factor = net_gains / net_losses if net_losses > 0 else None

    # Sharpe Ratio (Period Sharpe Ratio: mean of net returns divided by std of net returns)
    net_returns = top_df['net_return']
    std_net = net_returns.std()
    # std is NaN for a single pick and exactly 0.0 when every settled trade landed on the same
    # barrier — which settlement realism made reachable, since a no-gap HIT now settles at exactly
    # target_gain and a no-gap STOP at exactly -stop_loss. Both cases mean "dispersion is
    # undefined here", not "this strategy has no edge", but the UI styles 0.00 as a real result.
    # Report None, matching the profit_factor precedent in this same summary; both frontend
    # surfaces already render null as "—".
    sharpe_ratio = (
        float(net_returns.mean() / std_net)
        if pd.notna(std_net) and std_net > 0
        else None
    )

    # Since settlement realism landed, every no-gap HIT settles at exactly target_gain, so ties on
    # actual_return are the norm and idxmax() picked whichever row sorted first. Break ties on
    # net_return, then ticker, so the answer is deterministic rather than an artifact of ordering.
    best_pick = None
    if not top_df.empty:
        ranked = top_df.sort_values(
            ['actual_return', 'net_return', 'ticker'], ascending=[False, False, True]
        )
        best_pick = ranked.iloc[0]
    
    # Does the model that scored this run predate the window it scored? Fails toward the
    # pessimistic reading: an unmarked in-sample number is the failure this epic exists to remove,
    # so anything indeterminate reports `in_sample`.
    model_temporal_scope = "in_sample"
    try:
        from core.ai.predictor import get_model_version, list_available_models
        # "latest" is a sentinel, not a version string -- it matches no models_history entry,
        # so resolving it here is what made as_of_model unreachable on the default UI path.
        _v = version if version and version != "latest" else get_model_version()
        _entry = next((h for h in list_available_models() if h.get("version") == _v), None)
        _trained = _model_trained_at(_entry)
        if _trained is not None and _trained < as_of_date:
            model_temporal_scope = "as_of_model"
    except Exception:
        pass  # indeterminate -> keep the pessimistic default

    return {
        "days_ago": days_ago,
        "model_version": version or "latest",
        # The run's own as_of, not top_picks[0]'s date. A summary-level field must never be taken
        # from an arbitrary member of a collection.
        "simulated_date": as_of_date.strftime('%Y-%m-%d'),
        "excluded_no_data_at_as_of": len(excluded),
        "excluded_no_price_rows": len(excluded_no_data),
        # "in_sample": the scoring model was trained on data covering this window, so the numbers
        # measure recall over data it has seen -- not predictive skill. Making the backtest
        # genuinely out-of-sample needs an as-of model per window; this marks the situation.
        "model_temporal_scope": model_temporal_scope,
        "candidate_pool_size": len(results),
        "top_picks": top_picks,
        "summary": {
            # These were read off top_picks[0] and presented as the whole run's. Picks exit on
            # different days, so a single value is only honest when they agree.
            "holding_days": (
                top_picks[0]['holding_days']
                if top_picks and len({p['holding_days'] for p in top_picks}) == 1
                else None
            ),
            "exit_date_actual": (
                top_picks[0]['exit_date']
                if top_picks and len({p['exit_date'] for p in top_picks}) == 1
                else None
            ),
            "avg_return": avg_return,
            "avg_net_return": avg_net_return,
            "win_rate": win_count / len(top_picks) if top_picks else 0,
            "net_win_rate": net_win_count / len(top_picks) if top_picks else 0,
            "sniper_hit_rate": sniper_hit_rate,
            "sniper_hits": sniper_hits,
            "sniper_stops": sniper_stops,
            "profit_factor": round(profit_factor, 2) if profit_factor is not None else None,
            "net_profit_factor": round(net_profit_factor, 2) if net_profit_factor is not None else None,
            "sharpe_ratio": round(sharpe_ratio, 3) if sharpe_ratio is not None else None,
            "avg_max_drawdown": round(avg_max_drawdown * 100, 2),
            "worst_drawdown": round(worst_drawdown * 100, 2),
            "best_stock": best_pick['name'] if best_pick is not None else "N/A",
            "best_return": float(best_pick['actual_return']) if best_pick is not None else 0,
            "execution_time_sec": round(time.perf_counter() - start_time, 2)
        }
    }

if __name__ == "__main__":
    # Test run
    print("Running test backtest (10 days ago)...")
    result = run_time_machine(days_ago=10)
    print(result['summary'])
