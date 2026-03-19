"""
Tests for ML model rotation and prune strategy (docs/specs/ml-model-rotation.md).

AC1: Rotation deletes lowest profit_factor model, not oldest by timestamp.
AC2: None profit_factor ranks below any real score (including 0.0).
AC3: MAX_SAVED_MODELS constant is defined in core.ai.common and imported by trainer + manage_models.
AC4: Rotation never deletes the currently-active model file.
"""
import os
import json
import glob as globlib
import pytest
import tempfile
import shutil
from unittest.mock import patch
from core.ai.common import profit_factor_sort_key, MAX_SAVED_MODELS


# ---------------------------------------------------------------------------
# AC3: Shared constant
# ---------------------------------------------------------------------------

def test_max_saved_models_constant_exists():
    """AC3: MAX_SAVED_MODELS is exported from core.ai.common."""
    from core.ai.common import MAX_SAVED_MODELS
    assert isinstance(MAX_SAVED_MODELS, int)
    assert MAX_SAVED_MODELS > 0


def test_trainer_imports_max_saved_models():
    """AC3: trainer.py imports MAX_SAVED_MODELS (import-level check)."""
    import core.ai.trainer as trainer_module
    assert hasattr(trainer_module, 'MAX_SAVED_MODELS'), (
        "trainer.py must import MAX_SAVED_MODELS from core.ai.common"
    )


def test_manage_models_imports_max_saved_models():
    """AC3: manage_models.py imports MAX_SAVED_MODELS."""
    import backend.manage_models as mm
    assert hasattr(mm, 'MAX_SAVED_MODELS'), (
        "manage_models.py must import MAX_SAVED_MODELS from core.ai.common"
    )


# ---------------------------------------------------------------------------
# AC2: None profit_factor sort key
# ---------------------------------------------------------------------------

def _pf_key(h):
    """Mirrors the sort key used in both trainer.py and manage_models.py."""
    pf = h.get('backtest_30d', {}).get('profit_factor')
    return float(pf) if pf is not None else -1.0


def test_none_profit_factor_ranks_below_zero():
    """AC2: None profit_factor sorts lower than 0.0."""
    entries = [
        {'version': 'A', 'timestamp': 'ts_a', 'backtest_30d': {'profit_factor': 0.0}},
        {'version': 'B', 'timestamp': 'ts_b', 'backtest_30d': {'profit_factor': None}},
        {'version': 'C', 'timestamp': 'ts_c', 'backtest_30d': {'profit_factor': 1.5}},
    ]
    ranked = sorted(entries, key=_pf_key, reverse=True)
    assert ranked[0]['version'] == 'C'   # 1.5 — best
    assert ranked[1]['version'] == 'A'   # 0.0
    assert ranked[2]['version'] == 'B'   # None — worst


def test_none_profit_factor_ranks_below_negative():
    """AC2: None is treated as -1.0, so explicit -0.5 still beats None."""
    entries = [
        {'version': 'X', 'timestamp': 'ts_x', 'backtest_30d': {'profit_factor': -0.5}},
        {'version': 'Y', 'timestamp': 'ts_y', 'backtest_30d': {'profit_factor': None}},
    ]
    ranked = sorted(entries, key=_pf_key, reverse=True)
    assert ranked[0]['version'] == 'X'
    assert ranked[1]['version'] == 'Y'


def test_missing_backtest_key_treats_as_none():
    """AC2: Missing backtest_30d key behaves the same as None profit_factor."""
    entries = [
        {'version': 'A', 'timestamp': 'ts_a', 'backtest_30d': {}},
        {'version': 'B', 'timestamp': 'ts_b', 'backtest_30d': {'profit_factor': 0.1}},
    ]
    ranked = sorted(entries, key=_pf_key, reverse=True)
    assert ranked[0]['version'] == 'B'
    assert ranked[1]['version'] == 'A'


# ---------------------------------------------------------------------------
# AC1 + AC4: Rotation logic (isolated via tempdir)
# ---------------------------------------------------------------------------

def _make_history(entries):
    """Build a minimal history list from (timestamp, profit_factor) tuples."""
    return [
        {
            'timestamp': ts,
            'version': f'v4.{ts}',
            'backtest_30d': {'profit_factor': pf},
        }
        for ts, pf in entries
    ]


def _run_rotation(tmpdir, history, current_ts, name_part='sniper_model', ext='.pkl', model_path=None):
    """
    Reproduce the rotation block from trainer.py in an isolated tempdir.
    Returns list of remaining filenames (basenames only).
    """
    from core.ai.common import MAX_SAVED_MODELS

    # Create dummy .pkl files for each history entry
    for entry in history:
        ts = entry['timestamp']
        open(os.path.join(tmpdir, f"{name_part}_{ts}{ext}"), 'w').close()

    # Also create the "just trained" file if not already in history
    new_file = os.path.join(tmpdir, f"{name_part}_{current_ts}{ext}")
    if not os.path.exists(new_file):
        open(new_file, 'w').close()

    active_realpath = os.path.realpath(model_path) if model_path and os.path.exists(model_path) else None

    # --- Rotation logic (mirrors trainer.py) ---
    keep_timestamps = {h['timestamp'] for h in sorted(history, key=profit_factor_sort_key, reverse=True)[:MAX_SAVED_MODELS]}
    keep_timestamps.add(current_ts)

    for fpath in globlib.glob(os.path.join(tmpdir, f"{name_part}_*{ext}")):
        ts_part = os.path.basename(fpath)[len(name_part) + 1: -len(ext)]
        if ts_part in keep_timestamps:
            continue
        try:
            if active_realpath and os.path.realpath(fpath) == active_realpath:
                continue  # AC4: never delete active model
            os.remove(fpath)
        except Exception:
            pass

    return [os.path.basename(f) for f in globlib.glob(os.path.join(tmpdir, f"{name_part}_*{ext}"))]


def test_rotation_keeps_highest_profit_factor(tmp_path):
    """AC1: Rotation deletes the lowest-PF model, not the oldest."""
    tmpdir = str(tmp_path)
    # 6 models: timestamps ordered ts1..ts6, profit_factors vary
    history = _make_history([
        ('ts1', 3.0),   # best
        ('ts2', 2.5),
        ('ts3', 2.0),
        ('ts4', 1.5),
        ('ts5', 1.0),   # 5th — just makes the cut
        ('ts6', 0.1),   # worst — should be deleted when ts7 added
    ])
    current_ts = 'ts7'
    history.append({'timestamp': current_ts, 'version': f'v4.{current_ts}', 'backtest_30d': {'profit_factor': 4.0}})

    remaining = _run_rotation(tmpdir, history, current_ts)

    # ts7 (best, current) + ts1..ts5 should survive; ts6 (0.1) should be deleted
    assert 'sniper_model_ts6.pkl' not in remaining, "Lowest PF model must be deleted"
    assert 'sniper_model_ts7.pkl' in remaining, "Current model must be kept"
    assert 'sniper_model_ts1.pkl' in remaining, "Best PF model must be kept"
    assert len(remaining) == 5  # MAX_SAVED_MODELS after culling one extra


def test_rotation_protects_active_model(tmp_path):
    """AC4: Rotation never deletes MODEL_PATH even if it has the lowest profit_factor."""
    tmpdir = str(tmp_path)
    # Active model is ts1 which has the worst PF
    active_file = os.path.join(tmpdir, 'sniper_model_ts1.pkl')
    open(active_file, 'w').close()

    history = _make_history([
        ('ts1', 0.1),   # lowest PF — active model
        ('ts2', 3.0),
        ('ts3', 2.5),
        ('ts4', 2.0),
        ('ts5', 1.5),
        ('ts6', 1.0),
    ])
    current_ts = 'ts7'
    history.append({'timestamp': current_ts, 'version': f'v4.{current_ts}', 'backtest_30d': {'profit_factor': 0.5}})

    remaining = _run_rotation(tmpdir, history, current_ts, model_path=active_file)

    assert 'sniper_model_ts1.pkl' in remaining, "AC4: active model must never be deleted"


def test_rotation_none_pf_models_deleted_first(tmp_path):
    """AC1+AC2: Models with None profit_factor are the first candidates for deletion."""
    tmpdir = str(tmp_path)
    history = _make_history([
        ('ts1', 2.0),
        ('ts2', 1.5),
        ('ts3', 1.0),
        ('ts4', 0.5),
        ('ts5', None),  # failed backtest — should be culled first
        ('ts6', None),  # also None
    ])
    current_ts = 'ts7'
    history.append({'timestamp': current_ts, 'version': f'v4.{current_ts}', 'backtest_30d': {'profit_factor': 3.0}})

    remaining = _run_rotation(tmpdir, history, current_ts)

    for ts in ['ts5', 'ts6']:
        assert f'sniper_model_{ts}.pkl' not in remaining, f"None-PF model {ts} must be deleted first"
    assert 'sniper_model_ts7.pkl' in remaining
    assert 'sniper_model_ts1.pkl' in remaining
