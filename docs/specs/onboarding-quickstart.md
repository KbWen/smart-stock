---
status: shipped
title: Frictionless Onboarding — Offline Demo Seed + One-Command Quickstart
source: external
source_doc: _product-backlog.md (#1)
created: 2026-06-13
---

# Frictionless Onboarding — Offline Demo Seed + One-Command Quickstart

## Goal
Let someone who clones this repo see a **populated, working dashboard within minutes, fully offline** — instead of an empty app that first requires a slow, rate-limited yfinance sync. Bundle a small demo dataset and a one-command quickstart so the project is trivially adoptable.

## Background (grounded)
- `storage.db` and `model_sniper.pkl` are **gitignored** (`.gitignore:9,13`) → a fresh clone has **no price data and no model** → the dashboard is empty until a full network sync.
- `backend/recalculate.py:recalculate_all(incremental=False)` scopes to `SELECT DISTINCT ticker FROM stock_history` and computes V4 scores **offline** from DB history (verified: 6 tickers scored in seconds, no network).
- The honesty epic already makes a missing model degrade to `ai_prob = N/A` — so a demo with real technical scores but no bundled model is honest, not broken.

## Acceptance Criteria
1. A committed demo price fixture `data/demo/demo_prices.csv` provides offline OHLCV history for ~6 TWSE/OTC tickers (incl. 2330 台積電). Documented as a static public-price demo snapshot.
2. `scripts/seed_demo.py` loads the fixture into `storage.db` and computes V4 scores via the existing `recalculate_all` pipeline — **fully offline, no network**, and **idempotent** (re-running is safe; it does not duplicate or clobber a user's real synced data without `--force`). Prints a clear before/after summary.
3. `quickstart.sh` + `quickstart.ps1`: a single command that installs backend deps (`requirements.txt`), runs `seed_demo.py`, and prints the exact commands to launch backend + frontend. Cross-platform (bash + PowerShell), no new heavyweight dependency.
4. README gains a top **"⚡ Quickstart (offline demo)"** section with copy-paste steps. The existing strategy description is corrected so docs match the **shipped default labeling** (ATR volatility-scaled, configurable via `LABEL_MODE`; the fixed +15/+10/-5% is the legacy/toggle mode) — docs MUST match code (honesty).
5. Verifiable offline: a test seeds a temp DB from the fixture and asserts price rows AND scores are populated, with no network access.
6. No change to app **runtime** behavior — seed/quickstart are additive tooling. No regression in the existing suite.

## Non-goals
- Production deployment / containers beyond the existing Docker assets.
- Bundling a trained model (`.pkl` is gitignored, larger, and signing-sensitive). Demo AI probability shows honest `N/A`; `train_ai.py` enables it.
- Frontend build automation beyond printed instructions; auto-starting servers inside CI.

## Constraints
- Fixture is a static demo snapshot of **public** historical closing prices (a handful of tickers); documented as such. No live/private data, no secrets.
- `seed_demo.py` MUST be idempotent and offline; it MUST NOT overwrite a populated real DB unless `--force` is given.
- No change to `core/` app logic; this feature is tooling + docs + a data asset only.

## API / Data Contract
- `data/demo/demo_prices.csv`: columns `ticker,date,open,high,low,close,volume`.
- `scripts/seed_demo.py [--force]`: returns non-zero on failure; prints rows loaded + tickers scored.

## File Relationship
INDEPENDENT (tooling + docs + data asset). Stacked on #2/#3 branches; the README honesty correction aligns docs with the shipped ATR-label default from #2.
