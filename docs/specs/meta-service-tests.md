---
status: frozen
module: backend-api
---
# Spec: V4MetaService Unit Test Coverage

## Problem

`backend/services/v4_meta_service.py` has non-trivial business logic with zero dedicated unit
tests:

- `_to_bool()`: accepts `None`, `int`, `float`, `str`, `bool` — 6 distinct type branches
- `volume_spike` threshold: `rel_vol > 1.5` hardcoded
- `macd_diff` calculation: `macd - macd_signal` from indicator map
- Unknown ticker fallback: missing keys should produce safe zero/False defaults
- `updated_at` resolution: prefers score's timestamp, falls back to indicators'

Bugs in any of these branches are silent (no crash, wrong data in the UI).

## Goal

Add unit tests for `V4MetaService` covering all non-trivial paths.

## Proposed Tests

File: `tests/test_backend/test_meta_service.py`

### Group 1: `_to_bool()` conversion
- `None` → `False`
- `0` → `False`, `1` → `True`, `-1` → `True`
- `0.0` → `False`, `0.5` → `True`
- `"true"`, `"1"`, `"yes"`, `"y"` (case-insensitive) → `True`
- `"false"`, `"0"`, `""` → `False`
- `True` → `True`, `False` → `False`

### Group 2: `get_meta()` core logic (mock repos)
- Correct score fields mapped to response (`total_score`, `trend_score`, etc.)
- `macd_diff` = `macd - macd_signal` (not just `macd`)
- `volume_spike` = `True` only when `rel_vol > 1.5`; `False` when `rel_vol <= 1.5`
- Unknown ticker (no score, no indicators) returns safe zeros and `False` signals
- `updated_at` picks score's timestamp when available, falls back to indicators'
- Deduplication: `"2330.TW"` and `"2330"` both in request → single repo call, two response keys

## Acceptance Criteria (AC)

- [x] **AC1 – `_to_bool` coverage**: 9 test cases covering None/int/float/str/bool. _(PASS 2026-03-18)_
- [x] **AC2 – Core response shape**: `test_macd_diff_is_macd_minus_signal`, `test_volume_spike_*`, `test_score_fields_mapped_correctly`. _(PASS 2026-03-18)_
- [x] **AC3 – Unknown ticker safe defaults**: `test_unknown_ticker_returns_zeros_no_exception`. _(PASS 2026-03-18)_
- [x] **AC4 – `updated_at` fallback**: `test_fallback_to_indicator_updated_at`. _(PASS 2026-03-18)_
- [x] **AC5 – No regression**: 124/124 tests pass (was 101, +23 new). _(2026-03-18)_

## Non-goals

- Integration tests hitting a real SQLite DB.
- Testing `StockRepository.get_stock_name()` (separate responsibility).
