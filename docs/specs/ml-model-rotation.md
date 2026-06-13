---
status: frozen
module: core-ai
---
# Spec: ML Model File Rotation / Prune Strategy Unification

## Problem

Two independent model retention strategies currently operate without awareness of each other:

1. **File rotation in `trainer.py`** (line ~361–366): After training, keeps the **5 most recently trained** `.pkl` files (sorted by filename timestamp). Deletes older files unconditionally.
2. **`manage_models.py prune`**: Keeps the **5 highest profit_factor** models from `models_history.json`.

**Conflict scenario**: If 6 training runs produce increasingly poor models, file rotation deletes the oldest `.pkl` — which may be the best-performing model by profit_factor. The prune command cannot recover a deleted `.pkl` even if the history entry still exists. The file is gone.

**Secondary issue** in `prune`: Models with `backtest_30d.profit_factor = None` (backtest failed during training) are treated as `profit_factor = 0.0`, which may cause them to be ranked above legitimately scored 0.0 models, or below them unpredictably.

## Goal

Ensure that model file retention always preserves the **best-performing** models by profit_factor, not the most recently trained.

## Proposed Changes

### 1. Replace file rotation in `trainer.py` with profit_factor–aware retention

After training completes and history is appended, instead of deleting by filename age, load `models_history.json`, sort by `backtest_30d.profit_factor` descending, identify the `.pkl` files that correspond to the **bottom N** models (beyond keep limit), and delete those instead.

```python
# New logic (pseudo-code replacement for the rotation block):
history = load_history_json(history_path)
keep = 5
if len(history) > keep:
    scored = sorted(history, key=lambda h: float(h.get('backtest_30d', {}).get('profit_factor') or 0), reverse=True)
    to_delete = scored[keep:]
    for entry in to_delete:
        ts = entry['timestamp']
        fpath = os.path.join(base_dir, f"{name_part}_{ts}{ext_part}")
        if os.path.exists(fpath) and fpath != MODEL_PATH:
            os.remove(fpath)
```

### 2. Fix `None` profit_factor handling in `manage_models.py prune`

Change the sort key to explicitly distinguish `None` (backtest failure) from a real `0.0` score, placing `None` entries at the bottom of the keep-ranking:

```python
def _pf_key(h):
    pf = h.get('backtest_30d', {}).get('profit_factor')
    return float(pf) if pf is not None else -1.0  # None = worst

scored = sorted(history, key=_pf_key, reverse=True)
```

### 3. Align keep limit constant

Extract keep limit to a named constant in `core/ai/common.py`:

```python
MAX_SAVED_MODELS = 5
```

Both `trainer.py` and `manage_models.py` import and use `MAX_SAVED_MODELS` instead of hardcoded `5`.

## Acceptance Criteria (AC)

- [x] **AC1 – Rotation respects profit_factor**: After training, file rotation deletes the lowest-performing model (by `backtest_30d.profit_factor`) when model count exceeds `MAX_SAVED_MODELS`, not the oldest by timestamp. _(trainer.py rotation block replaced; test_rotation_keeps_highest_profit_factor PASS 2026-03-18)_
- [x] **AC2 – None profit_factor ranked last**: In both `trainer.py` rotation and `manage_models.py prune`, models where `backtest_30d.profit_factor is None` are ranked below any real numeric score (including 0.0). _(sort key `float(pf) if pf is not None else -1.0`; test_none_profit_factor_ranks_below_zero + test_none_pf_models_deleted_first PASS 2026-03-18)_
- [x] **AC3 – Shared constant**: `MAX_SAVED_MODELS = 5` in `core/ai/common.py`; imported by `trainer.py` and `manage_models.py`. _(test_max_saved_models_constant_exists + import checks PASS 2026-03-18)_
- [x] **AC4 – Active model protected**: Rotation skips any file whose realpath matches MODEL_PATH. _(test_rotation_protects_active_model PASS 2026-03-18)_

## Non-goals

- Changing training hyperparameters or ensemble composition.
- Adding automated retraining schedules (separate backlog item).
- Model drift/degradation monitoring (separate backlog item).
