---
status: living
title: Product Backlog — Directly-Usable v1 (Self-Install)
source: 2026-06-20 user-directed "directly usable version" epic (4-expert brainstorm)
created: 2026-06-20
last_updated: 2026-06-20
---

# Product Backlog

## Source Summary
After Optimization Round 2 shipped (archived to `_product-backlog-optimization-round2-2026-06-13.md`), the user asked for "a version users can at least directly use," **distributed for users to self-install** (explicitly NOT a hosted service). A 4-expert brainstorm (product/adoption, ML-data-honesty, DevOps/packaging, UX/first-run, all grounded in the repo) found the blocker is **launch friction + first-run legibility, not model quality**. Key user decisions: (1) NO public hosting — self-install distribution; (2) the real product targets the **full ~1,800-stock universe**, not a toy subset; (3) data reaches users via **accelerated live sync** (option C — switch full-universe history backfill from per-stock yfinance to authoritative TWSE/TPEX per-day bulk endpoints; no data redistribution, cleanest licensing). The small bundled demo fixture stays small (repo-size limit) and is reframed as an instant offline preview only. Honesty-first is preserved throughout (AI stays N/A by default; no bundled/weak model committed). Full source detail + expert briefs: `_raw-intake.md`.

## Feature Inventory
| # | Feature | Kind | Labels | Priority | Spec File | Tier | Status | Dependencies |
|---|---|---|---|---|---|---|---|---|
| 1 | One-command launch + single-port served frontend — quickstart builds `dist`, backend serves the SPA at one URL (:8000), collapse the two-terminal dev setup, `.ps1`/`.bat`/`.sh` parity, SPA deep-link fallback | feature | onboarding | P0 | docs/specs/onboarding-single-command-launch.md | feature | Shipped | — |
| 2 | Credible demo dataset — swap the 6 obscure demo tickers for ~12–15 household-name TWSE stocks (2330/2317/2454/2412/2882…) with enough rows; keep the fixture small | quick-win | data | P1 | scripts/gen_demo_fixture.py (gen tool) | quick-win | Shipped | — |
| 3 | Legible honest first-run UX — reframe AI N/A as "示範模式/尚未訓練", demo-mode badge, 繁中-ize scattered English UI, guard the sync button, first-run explainer (⚠️ §4.4 design-gate) | feature | ui, onboarding | P1 | docs/specs/honest-first-run-ux.md | feature | Shipped | #2 (soft) |
| 4 | Accelerated full-universe history sync — switch full-universe backfill from per-stock yfinance to authoritative TWSE/TPEX per-day bulk endpoints (fewer calls, cleaner licensing, no redistribution); keep yfinance as fallback | feature | data | P1 | — | feature | Pending | — |
| 5 | Real-AI first-run — opt-in quickstart step to sync the full universe (via #4) then train, so AI is populated not N/A; N/A stays the no-model default; do NOT bundle a `.pkl` | feature | ml, onboarding, data | P1 | — | feature | Pending | #4, #1 (soft) |
| 6 | Docker self-seed + `.dockerignore` — COPY demo+scripts, entrypoint seeds before serving, handle compose volume shadowing; containerized one-command self-install | feature | onboarding, infra | P1 | — | feature | Pending | #1 (soft) |

## Column Reference
- **Kind**: `feature` (planned) · `quick-win` (small planned) · `review-finding` (surfaced by review/audit) · `hotfix-spawn` (systemic issue from hotfix)
- **Priority**: `P0` (blocking, do now) · `P1` (high value, next batch) · `P2` (nice to have) · `—` (not yet prioritized)

## Status Key
- Pending: not yet started
- In Progress: spec generated, bootstrap running
- Shipped: feature shipped (see Ship History in current_state.md)
- Deferred: explicitly deferred
- Cancelled: explicitly cancelled

## Notes
- **Suggested execution order** (foundation-first, stacked PRs): #1 → #2 → #3 → #4 → #5 → #6. #1 is the P0 launch foundation; #2 makes the demo credible; #3 frames it honestly; #4 unblocks fast full-universe data; #5 is the real-AI payoff; #6 adds the Docker self-install path. #6 is independent and may slot anytime after #1.
- **EXTENDS, not modifies** (per spec-intake §8b — shipped specs are never edited): #1/#2/#5/#6 → `onboarding-quickstart`; #3 → `frontend-honest-data-states` + `ui-model-state-disclosure`; #4/#5 → `listed-otc-data-completeness`.
- **Distribution constraint**: NO hosting. Product is self-install. Real data reaches users via on-machine sync only (never redistributed by the maintainer).
- **Honesty constraint**: AI probability stays N/A until a model is trained on adequate data; no weak/degenerate model is bundled (`.pkl` gitignored; `MODEL_SIGNING_KEY` empty → an unsigned bundled model is rejected by design).
- **#4 feasibility (verified 2026-06-20)**: history is currently fetched per-stock via `yf.Ticker(...).history()` in `core/data.py:558` with a 0.5–1.5s sleep/stock (the ~10–15 min wall). TWSE `STOCK_DAY_ALL` (`core/universe_source.py:30`) is already used for the universe list; per-date all-stocks history backfill needs a date-parameterized endpoint (e.g., TWSE MI_INDEX) — to be designed in #4's spec. Net: far fewer HTTP calls than per-stock, authoritative source.
