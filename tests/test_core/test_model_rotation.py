"""
Tests for ML model rotation and prune strategy (docs/specs/ml-model-rotation.md).

AC1: Rotation deletes lowest profit_factor model, not oldest by timestamp.
AC2 (SUPERSEDED 2026-09-02 by docs/specs/model-rotation-ranking-honesty.md): a None
profit_factor is UNKNOWN, not worst -- it is protected from deletion, not ranked last.
AC3: MAX_SAVED_MODELS constant is defined in core.ai.common and imported by trainer + manage_models.
AC4: Rotation never deletes the currently-active model file.
"""
import os
import json
import glob as globlib

import pandas as pd
import pytest
import tempfile
import shutil
from unittest.mock import patch
from core.ai.common import profit_factor_sort_key, MAX_SAVED_MODELS
from core.ai.common import BENCHMARK_WINDOW, CURRENT_SETTLEMENT


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
# Superseded 2026-09-02 by docs/specs/model-rotation-ranking-honesty.md
# ---------------------------------------------------------------------------
# Three tests lived here asserting "None profit_factor ranks below 0.0", using a LOCAL copy of the
# old `-1.0` sentinel rather than the production sort key. They passed regardless of what the code
# did, and they encoded the defect: `None` meant both "no losing trades" (a flawless run) and "the
# backtest raised", and ranking both below a model that lost money on every trade is what deleted
# them first. The rule is now "unrankable means PROTECTED, not last", covered by
# test_rotation_protects_none_pf_models_instead_of_culling_them and
# test_select_for_deletion_never_returns_an_unrankable_entry below.


def _make_history(entries, settlement=CURRENT_SETTLEMENT):
    """Build a minimal history list from (timestamp, profit_factor) tuples.

    Entries carry the current settlement marker by default, because without it they are not
    comparable and rotation refuses to delete them -- see docs/specs/model-rotation-ranking-honesty.md.
    Pass ``settlement=None`` to build pre-2026-09-02 entries and exercise that protection.
    """
    return [
        {
            'timestamp': ts,
            'version': f'v4.{ts}',
            'backtest_30d': (
                {'profit_factor': pf, 'settlement': settlement,
                 'days_ago': BENCHMARK_WINDOW[0], 'holding_days': BENCHMARK_WINDOW[1]}
                if settlement else {'profit_factor': pf}
            ),
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

    # --- Rotation logic ---
    # Calls the REAL selection function rather than reproducing it, so this harness cannot drift
    # from trainer.py the way it did through the settlement change.
    from core.ai.common import timestamps_to_delete

    delete_timestamps = timestamps_to_delete(
        history, keep=MAX_SAVED_MODELS,
        protected_versions={f'v4.{current_ts}'}, fresh_timestamp=current_ts,
    )

    for ts_part in sorted(delete_timestamps):
        fpath = os.path.join(tmpdir, f"{name_part}_{ts_part}{ext}")
        if not os.path.exists(fpath):
            continue
        try:
            if active_realpath and os.path.realpath(fpath) == active_realpath:
                continue  # never delete the active model file
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
    history.append({'timestamp': current_ts, 'version': f'v4.{current_ts}',
                'backtest_30d': {'profit_factor': 4.0, 'settlement': CURRENT_SETTLEMENT,
                                 'days_ago': BENCHMARK_WINDOW[0], 'holding_days': BENCHMARK_WINDOW[1]}})

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


def test_rotation_protects_none_pf_models_instead_of_culling_them(tmp_path):
    """A `None` profit factor is UNKNOWN, not worst, so rotation must protect it.

    This test previously asserted the opposite -- that None-PF models are "culled first" -- which
    encoded the defect: `backend/backtest.py` returns None when there are **no losing trades** (a
    flawless run) and the trainer wrote None when the backtest **raised**, and the old `-1.0` sort
    key ranked both below a model that lost money on every trade. Whichever it was, it was deleted
    first, irreversibly. See docs/specs/model-rotation-ranking-honesty.md.
    """
    tmpdir = str(tmp_path)
    history = _make_history([
        ('ts1', 2.0),
        ('ts2', 1.5),
        ('ts3', 1.0),
        ('ts4', 0.5),
        ('ts5', None),  # flawless run OR a crashed one -- indistinguishable, so unrankable
        ('ts6', None),
    ])
    current_ts = 'ts7'
    history.append({'timestamp': current_ts, 'version': f'v4.{current_ts}',
                'backtest_30d': {'profit_factor': 3.0, 'settlement': CURRENT_SETTLEMENT,
                                 'days_ago': BENCHMARK_WINDOW[0], 'holding_days': BENCHMARK_WINDOW[1]}})

    remaining = _run_rotation(tmpdir, history, current_ts)

    for ts in ['ts5', 'ts6']:
        assert f'sniper_model_{ts}.pkl' in remaining, (
            f"None-PF model {ts} is unrankable and must be PROTECTED, not deleted"
        )
    assert 'sniper_model_ts7.pkl' in remaining   # freshly trained, always protected
    assert 'sniper_model_ts1.pkl' in remaining   # best comparable score
    # Only 5 entries are comparable here (ts1-ts4 + ts7), which is exactly MAX_SAVED_MODELS, so
    # nothing is culled. The store holds 7 files rather than 5 -- that is the disclosed cost of
    # refusing to rank the two unknowns, not a leak.
    assert len(remaining) == 7


def test_rotation_never_deletes_an_entry_measured_with_a_different_ruler(tmp_path):
    """The irreversible-deletion rule. A pre-2026-09-02 entry booked winning trades at the session
    high, so its profit factor is not comparable with a post-fix one -- on the same seed and window
    that difference moved PF 0.74 -> 0.80. Ranking them together could delete a genuinely better
    old model, and the .pkl does not come back."""
    tmpdir = str(tmp_path)
    # The pre-fix entry has the LOWEST profit factor present, so a naive ranking deletes it first.
    history = _make_history([('old1', 0.1)], settlement=None)
    history += _make_history([('ts1', 3.0), ('ts2', 2.0), ('ts3', 1.5), ('ts4', 1.2), ('ts5', 1.1)])
    current_ts = 'ts6'
    history.append({'timestamp': current_ts, 'version': f'v4.{current_ts}',
                    'backtest_30d': {'profit_factor': 2.5, 'settlement': CURRENT_SETTLEMENT,
                                     'days_ago': BENCHMARK_WINDOW[0], 'holding_days': BENCHMARK_WINDOW[1]}})

    remaining = _run_rotation(tmpdir, history, current_ts)

    assert 'sniper_model_old1.pkl' in remaining, (
        "an entry measured under a different settlement rule must never be auto-deleted"
    )
    assert 'sniper_model_ts6.pkl' in remaining
    # The store is now allowed to exceed MAX_SAVED_MODELS. That is the correct outcome of
    # refusing a bad comparison, not a bug to be tuned away.
    assert len(remaining) > 5


# ---------------------------------------------------------------------------
# Sidecar handling: cmd_activate and cmd_delete copy/clean sidecar files
# ---------------------------------------------------------------------------

def test_cmd_activate_copies_sidecars(tmp_path, monkeypatch):
    """cmd_activate must copy .sha256 and .sig sidecars alongside the .pkl."""
    import backend.manage_models as mm

    # Create versioned model files (pkl + sidecars)
    base = str(tmp_path)
    name = "sniper_model"
    ts = "20260321_0000"
    src_pkl = os.path.join(base, f"{name}_{ts}.pkl")
    src_sha = src_pkl + ".sha256"
    src_sig = src_pkl + ".sig"
    open(src_pkl, 'wb').close()
    open(src_sha, 'w').write("deadbeef")
    open(src_sig, 'w').write("cafebabe")

    dst_pkl = os.path.join(base, f"{name}.pkl")

    monkeypatch.setattr(mm, "MODEL_PATH", dst_pkl)

    mm.cmd_activate(f"v4.{ts}")

    assert os.path.exists(dst_pkl), ".pkl must be copied"
    assert os.path.exists(dst_pkl + ".sha256"), ".sha256 sidecar must be copied on activate"
    assert os.path.exists(dst_pkl + ".sig"), ".sig sidecar must be copied on activate"
    assert open(dst_pkl + ".sha256").read() == "deadbeef"
    assert open(dst_pkl + ".sig").read() == "cafebabe"


def test_cmd_activate_skips_missing_sidecars(tmp_path, monkeypatch):
    """cmd_activate works cleanly when no sidecar files exist (legacy model)."""
    import backend.manage_models as mm

    base = str(tmp_path)
    name = "sniper_model"
    ts = "20260321_0001"
    src_pkl = os.path.join(base, f"{name}_{ts}.pkl")
    open(src_pkl, 'wb').close()

    dst_pkl = os.path.join(base, f"{name}.pkl")
    monkeypatch.setattr(mm, "MODEL_PATH", dst_pkl)

    mm.cmd_activate(f"v4.{ts}")  # must not raise even with no sidecars

    assert os.path.exists(dst_pkl)
    assert not os.path.exists(dst_pkl + ".sha256")
    assert not os.path.exists(dst_pkl + ".sig")


def test_cmd_delete_removes_sidecars(tmp_path, monkeypatch):
    """cmd_delete must remove .sha256 and .sig sidecar files alongside the .pkl."""
    import backend.manage_models as mm

    base = str(tmp_path)
    name = "sniper_model"
    ts = "20260321_0002"
    target_pkl = os.path.join(base, f"{name}_{ts}.pkl")
    target_sha = target_pkl + ".sha256"
    target_sig = target_pkl + ".sig"
    open(target_pkl, 'wb').close()
    open(target_sha, 'w').write("deadbeef")
    open(target_sig, 'w').write("cafebabe")

    monkeypatch.setattr(mm, "MODEL_PATH", os.path.join(base, f"{name}.pkl"))
    monkeypatch.setattr(mm, "HISTORY_PATH", os.path.join(base, "models_history.json"))

    mm.cmd_delete(f"v4.{ts}")

    assert not os.path.exists(target_pkl), ".pkl must be removed"
    assert not os.path.exists(target_sha), ".sha256 sidecar must be removed on delete"
    assert not os.path.exists(target_sig), ".sig sidecar must be removed on delete"


# ---------------------------------------------------------------------------
# Comparability rule (docs/specs/model-rotation-ranking-honesty.md)
# ---------------------------------------------------------------------------

def test_is_rankable_requires_a_matching_marker_and_a_finite_number():
    from core.ai.common import CURRENT_SETTLEMENT, is_rankable

    ok = {'backtest_30d': {'profit_factor': 1.5, 'settlement': CURRENT_SETTLEMENT,
                          'days_ago': BENCHMARK_WINDOW[0], 'holding_days': BENCHMARK_WINDOW[1]}}
    assert is_rankable(ok)

    # Pre-2026-09-02: no marker at all.
    assert not is_rankable({'backtest_30d': {'profit_factor': 1.5}})
    # A future/other fill model.
    assert not is_rankable({'backtest_30d': {'profit_factor': 1.5, 'settlement': 'session_extremes'}})
    # Right marker, different window. PRED_DAYS is env-configurable, so this is reachable with
    # no code change at all -- the window is part of the ruler, not decoration.
    assert not is_rankable({'backtest_30d': {'profit_factor': 1.5, 'settlement': CURRENT_SETTLEMENT,
                                            'days_ago': 99, 'holding_days': BENCHMARK_WINDOW[1]}})
    # Marker present, window not recorded at all.
    assert not is_rankable({'backtest_30d': {'profit_factor': 1.5, 'settlement': CURRENT_SETTLEMENT}})
    # Undefined or unusable numbers. json.loads accepts bare NaN/Infinity, so both are reachable
    # from a hand-edited history file.
    for pf in (None, float('nan'), float('inf'), 'abc', True):
        assert not is_rankable({'backtest_30d': {'profit_factor': pf, 'settlement': CURRENT_SETTLEMENT,
                                       'days_ago': BENCHMARK_WINDOW[0], 'holding_days': BENCHMARK_WINDOW[1]}}), pf
    # No backtest block at all.
    assert not is_rankable({})


def test_select_for_deletion_never_returns_an_unrankable_entry():
    """The rule the whole spec exists for: an irreversible action requires a comparable
    measurement. The pre-fix entry below has the LOWEST profit factor present, so a naive ranking
    would delete it first."""
    from core.ai.common import CURRENT_SETTLEMENT, select_for_deletion

    S = CURRENT_SETTLEMENT
    history = [
        {'version': 'pre_fix', 'backtest_30d': {'profit_factor': 0.1}},
        {'version': 'flawless', 'backtest_30d': {'profit_factor': None, 'settlement': S, 'days_ago': BENCHMARK_WINDOW[0], 'holding_days': BENCHMARK_WINDOW[1], 'status': 'no_losing_trades'}},
        {'version': 'crashed', 'backtest_30d': {'profit_factor': None, 'settlement': S, 'days_ago': BENCHMARK_WINDOW[0], 'holding_days': BENCHMARK_WINDOW[1], 'status': 'failed'}},
        {'version': 'best', 'backtest_30d': {'profit_factor': 2.0, 'settlement': S, 'days_ago': BENCHMARK_WINDOW[0], 'holding_days': BENCHMARK_WINDOW[1]}},
        {'version': 'worst_comparable', 'backtest_30d': {'profit_factor': 0.2, 'settlement': S, 'days_ago': BENCHMARK_WINDOW[0], 'holding_days': BENCHMARK_WINDOW[1]}},
    ]

    to_delete, protected = select_for_deletion(history, keep=1)

    assert [h['version'] for h in to_delete] == ['worst_comparable']
    assert {h['version'] for h in protected} == {'pre_fix', 'flawless', 'crashed'}
    # 'no_losing_trades' and 'failed' are both unrankable, but they remain distinguishable -- the
    # defect was that `None` alone meant either one.
    statuses = {h['version']: h['backtest_30d'].get('status') for h in protected if 'status' in h['backtest_30d']}
    assert statuses == {'flawless': 'no_losing_trades', 'crashed': 'failed'}


def test_freshly_trained_model_is_never_selected_even_if_it_ranks_last():
    from core.ai.common import CURRENT_SETTLEMENT, select_for_deletion

    S = CURRENT_SETTLEMENT
    history = [
        {'version': 'v_new', 'backtest_30d': {'profit_factor': 0.01, 'settlement': S, 'days_ago': BENCHMARK_WINDOW[0], 'holding_days': BENCHMARK_WINDOW[1]}},
        {'version': 'v_a', 'backtest_30d': {'profit_factor': 3.0, 'settlement': S, 'days_ago': BENCHMARK_WINDOW[0], 'holding_days': BENCHMARK_WINDOW[1]}},
        {'version': 'v_b', 'backtest_30d': {'profit_factor': 2.0, 'settlement': S, 'days_ago': BENCHMARK_WINDOW[0], 'holding_days': BENCHMARK_WINDOW[1]}},
    ]

    to_delete, _ = select_for_deletion(history, keep=1, protected_versions={'v_new'})

    assert 'v_new' not in {h['version'] for h in to_delete}
    assert {h['version'] for h in to_delete} == {'v_b'}


def test_benchmark_records_that_it_is_in_sample_rather_than_claiming_otherwise(tmp_path, monkeypatch):
    """The rotation benchmark is IN-SAMPLE and no choice of window fixes that.

    An earlier draft of this feature moved days_ago 30 -> 40 with a comment claiming the window
    "must start AFTER the last label the final fit saw". It does not: the final ensemble is refit
    on every row, training rows run to T-PRED_DAYS, and their labels resolve on prices through T --
    so any window ending before T is inside the training data, and raising days_ago buries it
    deeper. The window is back where it was, the entry records the truth, and a genuinely
    out-of-sample rotation score needs an as-of model per window (backlog #3).
    """
    import backend.backtest as bt
    from core.ai import trainer as t
    from core.ai.common import BENCHMARK_WINDOW, FEATURE_COLS

    calls = []

    def fake_run_time_machine(**kwargs):
        calls.append(kwargs)
        return {"summary": {"profit_factor": 1.4, "win_rate": 0.5,
                            "sniper_hit_rate": 0.4, "avg_return": 0.02}}

    monkeypatch.setattr(bt, "run_time_machine", fake_run_time_machine)
    monkeypatch.setattr(t, "MODEL_PATH", str(tmp_path / "m.pkl"))
    monkeypatch.setattr(t, "prepare_features", lambda df: (df[FEATURE_COLS], df["target"]))

    dates = pd.bdate_range("2021-01-01", periods=400)
    panel = pd.DataFrame([
        {**{c: float(i + k) for c in FEATURE_COLS}, "target": k % 3, "date": d}
        for i, d in enumerate(dates) for k in range(12)
    ])

    assert t.train_and_save([panel]) is True
    assert len(calls) == 1

    entry = json.loads((tmp_path / "models_history.json").read_text())[-1]["backtest_30d"]
    # The window is RECORDED, and it is the one the comparability key expects -- so a run with a
    # different PRED_DAYS cannot be ranked against this one.
    assert (entry["days_ago"], entry["holding_days"]) == BENCHMARK_WINDOW
    assert (calls[0]["days_ago"], calls[0]["holding_days"]) == BENCHMARK_WINDOW
    # And the entry says plainly that the score is in-sample.
    assert entry["in_sample"] is True
    assert entry["settlement"] == CURRENT_SETTLEMENT
    assert entry["status"] == "ok"


def test_benchmark_records_failed_when_the_backtest_returns_an_error_dict(tmp_path, monkeypatch):
    """run_time_machine RETURNS error dicts rather than raising for several conditions, and those
    responses carry no summary. Reading a missing profit_factor as "no losing trades" would
    recreate the two-meanings defect inside the field added to fix it."""
    import backend.backtest as bt
    from core.ai import trainer as t
    from core.ai.common import FEATURE_COLS, is_rankable

    monkeypatch.setattr(bt, "run_time_machine",
                        lambda **kw: {"error": "No stocks met requirements"})
    monkeypatch.setattr(t, "MODEL_PATH", str(tmp_path / "m.pkl"))
    monkeypatch.setattr(t, "prepare_features", lambda df: (df[FEATURE_COLS], df["target"]))

    dates = pd.bdate_range("2021-01-01", periods=400)
    panel = pd.DataFrame([
        {**{c: float(i + k) for c in FEATURE_COLS}, "target": k % 3, "date": d}
        for i, d in enumerate(dates) for k in range(12)
    ])

    assert t.train_and_save([panel]) is True

    written = json.loads((tmp_path / "models_history.json").read_text())[-1]
    assert written["backtest_30d"]["status"] == "failed"
    assert written["backtest_30d"]["profit_factor"] is None
    assert "No stocks met requirements" in (written["backtest_30d"].get("error") or "")
    # A failed benchmark is unrankable, so this model can never be auto-deleted on it.
    assert is_rankable(written) is False


def test_a_shared_timestamp_never_takes_a_protected_file_with_it():
    """Timestamps are minute-resolution (`%Y%m%d_%H%M`), so two history entries can name the SAME
    .pkl. Deleting on a rankable entry's behalf must not remove a protected entry's file -- the
    mapping from entries to filenames is where protection leaks if nobody looks."""
    from core.ai.common import BENCHMARK_WINDOW, CURRENT_SETTLEMENT, timestamps_to_delete

    shared = '20260601_1200'
    history = [
        # Pre-2026-09-02: no settlement marker, so protected...
        {'version': 'v4.old', 'timestamp': shared, 'backtest_30d': {'profit_factor': 0.1}},
        # ...but it shares a file with this comparable, worst-ranked entry.
        {'version': 'v4.weak', 'timestamp': shared,
         'backtest_30d': {'profit_factor': 0.2, 'settlement': CURRENT_SETTLEMENT,
                          'days_ago': BENCHMARK_WINDOW[0], 'holding_days': BENCHMARK_WINDOW[1]}},
        {'version': 'v4.good', 'timestamp': '20260602_1200',
         'backtest_30d': {'profit_factor': 3.0, 'settlement': CURRENT_SETTLEMENT,
                          'days_ago': BENCHMARK_WINDOW[0], 'holding_days': BENCHMARK_WINDOW[1]}},
    ]

    stamps = timestamps_to_delete(history, keep=1, fresh_timestamp='20260603_1200')

    assert shared not in stamps, (
        "the shared .pkl backs a protected entry and must survive, even though the other entry "
        "sharing it ranks last"
    )


def test_deletion_is_an_allow_list_not_everything_not_kept():
    """`history` is truncated to the last 50 entries. Under the old glob-and-keep shape a
    protected file eventually fell out of the keep-set and was removed with no comparability
    check and no log line -- the protection expired silently around night 52."""
    from core.ai.common import BENCHMARK_WINDOW, CURRENT_SETTLEMENT, timestamps_to_delete

    def entry(v, pf):
        return {'version': f'v4.{v}', 'timestamp': v,
                'backtest_30d': {'profit_factor': pf, 'settlement': CURRENT_SETTLEMENT,
                                 'days_ago': BENCHMARK_WINDOW[0],
                                 'holding_days': BENCHMARK_WINDOW[1]}}

    history = [entry(f'ts{i}', float(i)) for i in range(10)]
    stamps = timestamps_to_delete(history, keep=5, fresh_timestamp='ts9')

    # Exactly the 5 worst comparable entries, named individually. A file on disk with no history
    # entry at all is NOT in this set, so it cannot be swept up.
    assert stamps == {'ts0', 'ts1', 'ts2', 'ts3', 'ts4'}
    assert 'ts_orphan_on_disk' not in stamps
