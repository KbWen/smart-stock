---
status: frozen
module: onboarding
version: 1.0.0
---

# Onboarding Optimization & Windows Encoding Fix

Ensures that new users downloading the repository can set up, sync, train, and run the project painlessly on all operating systems (specifically resolving Windows CP950 terminal crashes).

## User Review Required

> [!IMPORTANT]
> - Python scripts printing Unicode emojis directly to standard output will crash on Windows terminals when CP950/Big5 or CP437 is the active page encoding.
> - Emojis will be replaced with standard text formatting (e.g. `[WARNING]`, `[SUCCESS]`, `[ERROR]`) in stdout print statements.

## Acceptance Criteria

### AC1: Windows Encoding Crash Fix
- Eliminate terminal encoding crashes on Windows (e.g. `UnicodeEncodeError` with `cp950` or `cp437`) during training, backtesting, and model management.
- Remove all emojis from print statements in the following Python files:
  - `core/ai/trainer.py`
  - `backend/backtest.py`
  - `backend/manage_models.py`
- Replace emojis with clean, bracketed ASCII headers (e.g. `[INFO]`, `[WARNING]`, `[SUCCESS]`, `[ERROR]`, `[DELETED]`, `[CLEANED]`).

### AC2: Root Automation Scripts
- Add `daily_run.bat` and `daily_run.sh` to the repository root directory as described in `README.md`.
- Ensure `daily_run.sh` changes directory to the repository root (e.g. `cd "$(dirname "$0")"` when run from root, or handles directory location correctly) so that relative paths `backend/...` work correctly.
- Ensure `daily_run.bat` runs the same three steps:
  1. Data sync: `python backend/main.py --sync`
  2. Training: `python backend/train_ai.py`
  3. Recalculation: `python backend/recalculate.py`

### AC3: Fast Development Sync Limit
- Add support for a `--limit` flag to `backend/main.py` (when using `--sync`) and to the `/api/sync` endpoint.
- If `--limit N` is specified, only sync the first `N` stocks from `get_all_tw_stocks()` (e.g. TSMC, Foxconn, etc.) instead of all 1000+ stocks.
- This allows developers to bootstrap a fully working database and trained model in under 1 minute for local verification.

### AC4: Test and Build Verification
- Ensure that the entire backend test suite (`pytest -m "not integration"`) passes.
- Ensure that the frontend production build (`npm run build` in `frontend/v4`) runs cleanly.

## Non-goals
- Modifying the core machine learning ensemble model architectures or technical indicator formula logic.
- Restructuring the SQLite database table schemas.

## Constraints
- Must not affect the behavior when no `--limit` is specified (defaults to syncing all active Taiwan stocks).
- Must run correctly without a `.env` file present (using safe default values).

## File Relationships
- This spec is **INDEPENDENT** of other specs.
