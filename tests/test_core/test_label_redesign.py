"""Tests for ATR (volatility)-scaled triple-barrier labels.

spec_ref: docs/specs/ml-label-volatility-scaling.md
Covers: AC1 (config-driven), AC2 (per-row ATR, no look-ahead), AC3/AC6 (fixed
back-compat + rebalance), AC4 (reproducible distribution analysis).
"""
import numpy as np
import pandas as pd
import pytest

from core.ai import common, trainer
from core.ai import label_analysis
import core.config as cfg


PRED = common.PRED_DAYS  # 20


def _series(entry, future_highs, future_lows, atr0):
    """Build minimal arrays: 1 labelable entry row (index 0) + PRED future rows."""
    n = PRED + 1
    closes = np.full(n, float(entry))
    highs = np.full(n, float(entry))
    lows = np.full(n, float(entry))
    # future rows are indices 1..PRED
    highs[1:] = future_highs
    lows[1:] = future_lows
    atr = np.full(n, float(atr0))
    return closes, highs, lows, atr


# --- AC2: ATR barrier hit/miss correctness (pure helper, no look-ahead) -----

def test_compute_targets_atr_strong_before_stop():
    # entry 100, atr 10 -> strong=130, buy=118, stop=85 (mults 3.0/1.8/1.5)
    fh = np.full(PRED, 100.0); fl = np.full(PRED, 100.0)
    fh[2] = 131.0  # hits strong at offset 3, stop never
    c, h, l, a = _series(100, fh, fl, 10)
    t = trainer._compute_targets(c, h, l, a, "atr")
    assert t[0] == 2


def test_compute_targets_atr_buy_before_stop():
    fh = np.full(PRED, 100.0); fl = np.full(PRED, 100.0)
    fh[1] = 120.0  # >=buy(118) but <strong(130); stop never
    c, h, l, a = _series(100, fh, fl, 10)
    t = trainer._compute_targets(c, h, l, a, "atr")
    assert t[0] == 1


def test_compute_targets_atr_stop_first():
    fh = np.full(PRED, 100.0); fl = np.full(PRED, 100.0)
    fl[0] = 80.0   # hits stop(85) at offset 1...
    fh[5] = 131.0  # ...strong later -> stop wins -> Hold
    c, h, l, a = _series(100, fh, fl, 10)
    t = trainer._compute_targets(c, h, l, a, "atr")
    assert t[0] == 0


def test_compute_targets_atr_none():
    fh = np.full(PRED, 105.0); fl = np.full(PRED, 96.0)  # neither target nor stop
    c, h, l, a = _series(100, fh, fl, 10)
    t = trainer._compute_targets(c, h, l, a, "atr")
    assert t[0] == 0


def test_compute_targets_atr_nan_atr_is_hold():
    fh = np.full(PRED, 200.0); fl = np.full(PRED, 100.0)  # huge rise
    c, h, l, a = _series(100, fh, fl, np.nan)  # ATR NaN -> no learnable label
    t = trainer._compute_targets(c, h, l, a, "atr")
    assert t[0] == 0


# --- AC3/AC6: fixed mode is byte-for-byte the legacy behavior ---------------

def test_compute_targets_fixed_matches_legacy():
    # entry 100 -> strong=115, buy=110, stop=95 (TARGET_GAIN .15 / BUY .10 / STOP .05)
    fh = np.full(PRED, 100.0); fl = np.full(PRED, 100.0)
    fh[3] = 116.0  # strong
    c, h, l, a = _series(100, fh, fl, 10)
    assert trainer._compute_targets(c, h, l, a, "fixed")[0] == 2

    fh2 = np.full(PRED, 100.0); fl2 = np.full(PRED, 100.0)
    fh2[1] = 111.0  # buy not strong
    c2, h2, l2, a2 = _series(100, fh2, fl2, 10)
    assert trainer._compute_targets(c2, h2, l2, a2, "fixed")[0] == 1


def test_compute_targets_fixed_ignores_atr():
    # In fixed mode, ATR value must not affect the outcome.
    fh = np.full(PRED, 100.0); fl = np.full(PRED, 100.0)
    fh[2] = 116.0
    c, h, l, a = _series(100, fh, fl, 999.0)  # absurd ATR
    assert trainer._compute_targets(c, h, l, a, "fixed")[0] == 2


# --- AC1: config constants wired through common -----------------------------

def test_config_constants_wired():
    assert common.LABEL_MODE == cfg.LABEL_MODE
    assert common.ATR_TARGET_MULT == cfg.ATR_TARGET_MULT
    assert common.ATR_BUY_MULT == cfg.ATR_BUY_MULT
    assert common.ATR_STOP_MULT == cfg.ATR_STOP_MULT
    assert cfg.ATR_TARGET_MULT > cfg.ATR_BUY_MULT  # strong target above buy target


# --- AC3/AC4: rebalancing is demonstrable + reproducible --------------------

def _lowvol_uptrend(n=340, daily=0.003, seed=7):
    """A LOW-volatility steady uptrend: the case where fixed barriers degenerate.

    +0.3%/day compounding (~+6% over a 20-day window) with tiny intraday range, so
    the fixed +10%/+15% targets are essentially never hit (-> ~all Hold), while the
    ATR-scaled targets (a few * a small ATR) are reachable (-> learnable Buy/Strong).
    This is the volatility-dependence mechanism the redesign fixes.
    """
    rng = np.random.default_rng(seed)
    close = 100 * (1 + daily) ** np.arange(n) + rng.normal(0, 0.1, n)
    return pd.DataFrame({
        "date": pd.date_range("2020-01-01", periods=n, freq="D"),
        "open": close,
        "high": close * 1.003,
        "low": close * 0.997,
        "close": close,
        "volume": 1_000_000,
    })


def test_label_distribution_atr_rebalances_vs_fixed():
    """On a low-vol uptrend, fixed labels degenerate (~all Hold) but ATR labels are learnable."""
    dfs = [_lowvol_uptrend()]
    fixed = label_analysis.label_distribution(dfs, mode="fixed")
    atr = label_analysis.label_distribution(dfs, mode="atr")
    assert fixed["n"] > 0 and atr["n"] > 0
    fixed_signal = fixed["buy"] + fixed["strong"]
    atr_signal = atr["buy"] + atr["strong"]
    assert atr_signal > fixed_signal          # rebalanced toward learnable positive classes
    assert atr_signal > 0.25                  # ATR labels carry real positive signal
    assert fixed_signal < 0.10                 # fixed labels are near-degenerate here


def test_label_distribution_restores_config_mode(sample_stock_data):
    """The analysis helper must not leak its temporary LABEL_MODE override."""
    before = common.LABEL_MODE
    label_analysis.label_distribution([sample_stock_data], mode="fixed")
    assert common.LABEL_MODE == before


def test_prepare_features_runs_both_modes(sample_stock_data, monkeypatch):
    """Regression: prepare_features produces valid 3-class labels in both modes."""
    for mode in ("fixed", "atr"):
        monkeypatch.setattr(common, "LABEL_MODE", mode)
        X, y = trainer.prepare_features(sample_stock_data)
        assert not X.empty
        assert set(y.unique()).issubset({0, 1, 2})
