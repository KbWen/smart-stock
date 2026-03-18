---
status: frozen
module: backend-api
---
# Spec: Remove Double Ticker Normalization in /api/v4/meta

## Problem

`backend/routes/stock.py` (the route handler) and `backend/services/v4_meta_service.py` both
perform the same ticker normalization logic independently:

1. **Route** (`stock.py` lines 168–185): splits raw `tickers` string, calls
   `standardize_ticker()` for each, deduplicates into `normalized` list, validates count ≤ 100.
   Then passes the **original raw string** back to `v4_meta_service.get_meta(tickers=tickers)`.

2. **Service** (`V4MetaService.get_meta`): receives the raw string and repeats the exact same
   split → standardize → deduplicate → normalize pipeline.

The route's work is discarded. Any change to normalization logic must be applied in two places,
creating a DRY violation and a maintenance hazard.

## Goal

Single normalization pass. The route owns input validation + normalization; the service receives
pre-processed data and performs only business logic.

## Proposed Changes

### 1. Change `V4MetaService.get_meta()` signature

```python
# Before
def get_meta(self, tickers: str) -> dict[str, dict[str, dict[str, Any]]]:

# After
def get_meta(self, requested_pairs: list[tuple[str, str]]) -> dict[str, dict[str, dict[str, Any]]]:
    """
    requested_pairs: list of (original_ticker, normalized_ticker) tuples.
    Caller is responsible for normalization and deduplication.
    """
```

The service no longer splits or normalizes — it uses `requested_pairs` directly.

### 2. Update `stock.py` route to pass `requested_pairs`

```python
# Before
return v4_meta_service.get_meta(tickers=tickers)

# After
return v4_meta_service.get_meta(requested_pairs=requested_pairs)
```

The route's existing normalization block stays intact (it already builds `requested_pairs`).

## Acceptance Criteria (AC)

- [x] **AC1 – Single normalization**: `V4MetaService.get_meta()` no longer splits or calls `standardize_ticker()`. `standardize_ticker` import removed from service. _(code inspection + grep confirms 2026-03-18)_
- [x] **AC2 – Correct behavior preserved**: `test_duplicate_normalized_ticker_queries_repo_once` asserts dedup + response shape. _(PASS 2026-03-18)_
- [x] **AC3 – No regression**: 124/124 tests pass. _(2026-03-18)_

## Non-goals

- Changing the normalization rules themselves.
- Adding new ticker formats.
