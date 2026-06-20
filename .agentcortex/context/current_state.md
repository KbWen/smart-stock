# Project Current State (vNext)

- **Project Intent**: Taiwan stock analysis platform with AI-powered buy signal prediction using ensemble ML (Gradient Boosting + Random Forest + MLP), technical indicators, and V4 sniper scoring system.
- **Core Guardrails**:
  - Correctness first: No claim of completion without evidence.
  - Small & reversible: Prioritize small, reversible changes; avoid unauthorized refactoring.
  - Document-first: Core logic or structural changes require a Spec/ADR first.
  - Handoff gate: Non-`tiny-fix` tasks must produce a traceable handoff summary.
- **System Map**:
  - Global SSoT: `.agentcortex/context/current_state.md`
  - Task Isolation: `.agentcortex/context/work/<worklog-key>.md`
  - Active Work Log Path: derive <worklog-key> from the raw branch name using filesystem-safe normalization before any gate checks.
  - Workflows & Policies: `.agent/workflows/*.md`, `.agent/rules/*.md`
- **ADR Index**:
  - docs/adr/ADR-001-vnext-self-managed-architecture.md: vNext self-managed architecture · applies_to: .agentcortex/
- **Active Backlog**: `docs/specs/_product-backlog.md` (Directly-Usable v1 — #1 one-command launch **Shipped 2026-06-20**; #2–#6 pending. Self-install distribution, full-universe via accelerated live sync, no public hosting. Prior Optimization Round 2 backlog archived to `docs/specs/_product-backlog-optimization-round2-2026-06-13.md`)
  - When a multi-feature product spec is decomposed, the backlog path is recorded here (e.g., `docs/specs/_product-backlog.md`). Bootstrap reads this to detect ongoing product work.
- **Spec Index**:
  - `[api-perf] docs/specs/api-refactor-perf.md [Frozen] — ✅ ALL 5 ACs done (batch benchmark test added 2026-03-17)`
  - `[backend] docs/specs/backend-refactor-modular.md [Frozen] — ✅ ALL 8 ACs done (schema parity tests added 2026-03-17)`
  - `[frontend-api] docs/specs/frontend-api-opt.md [Frozen] — ✅ ALL 4 ACs done (E2E real render benchmark added 2026-03-18)`
  - `[frontend-test] docs/specs/frontend-testing.md [Frozen] — ✅ ALL 6 ACs done (82.7% coverage confirmed 2026-03-22) [Updated: 2026-03-22]`
  - `[cache] docs/specs/smart-stock-cache.md [Frozen] — ✅ ALL 5 ACs done (GlassCard+Button extracted 2026-03-17)`
  - `[ml-rotation] docs/specs/ml-model-rotation.md [Frozen] — ✅ ALL 4 ACs done (profit_factor rotation + None guard + MAX_SAVED_MODELS + active model protection 2026-03-18)`
  - `[fe-lazy] docs/specs/frontend-lazy-loading.md [Frozen] — ✅ ALL 4 ACs done (already implemented: App.tsx full-page lazy, MarketRisk inner Suspense, recharts in async chunks 2026-03-18)`
  - `[meta-norm] docs/specs/meta-normalization.md [Frozen] — ✅ ALL 3 ACs done (single-pass normalization, route passes requested_pairs to service 2026-03-18)`
  - `[predictor-ts] docs/specs/predictor-thread-safety.md [Frozen] — ✅ ALL 3 ACs done (threading.Lock + OrderedDict LRU cache maxsize=3 2026-03-18)`
  - `[meta-tests] docs/specs/meta-service-tests.md [Frozen] — ✅ ALL 5 ACs done (23 new tests: _to_bool, signals, safe defaults, updated_at fallback 2026-03-18)`
  - `[api-security] docs/specs/api-security-hardening.md [Frozen] — ✅ ALL 12 ACs done (path traversal, info-leak, rate limits, ticker validation, bare excepts, SHA256 integrity 2026-03-19)`
  - `[audit-doc-test] docs/specs/audit-doc-test-supplement.md [Frozen] — ✅ ALL 9 ACs done (HMAC tests 9/9, model-signing.md, rate-limiting.md 2026-03-21)`
  - `[visual-upgrade-p1] docs/specs/visual-upgrade-phase1.md [Frozen] — ✅ ALL 6 ACs done (history endpoint + PriceSignalChart + count-up animation 2026-03-27)`
  - `[visual-upgrade-p2] docs/specs/visual-upgrade-phase2.md [Frozen] — ✅ ALL 7 ACs done (sparkline endpoint + SparklineChart + CandidateRow integration 2026-03-28)`
  - `[onboarding] docs/specs/onboarding-optimization.md [Frozen] — ✅ ALL 4 ACs done (dev startup and limit sync optimized 2026-06-01)`
  - `[frontend-ai] docs/specs/frontend-ai-optimization.md [Frozen] — ✅ ALL 4 ACs done (SVG sparklines, animations, glassmorphism, AI verification 2026-06-01)`
  - `[core-ai-opt] docs/specs/ai-pipeline-otc-optimization.md [Frozen] — ✅ ALL 5 ACs done + US/Crypto suffix lookup fix 2026-06-02`
  - `[backtest-perf] docs/specs/backtest-and-performance-opt.md [Frozen] — ✅ ALL 5 ACs done (batch query + transaction cost sliders + sharpe & drawdown metrics + CandidateRow optimization + dynamic strategy parameters + production build 2026-06-02)`
  - `[honest-fe] docs/specs/frontend-honest-data-states.md [Frozen] — ✅ ALL 6 ACs done (removed mockData fallback; nullable useCachedApi; honest loading/no-data/error states 2026-06-13)`
  - `[honest-be] docs/specs/backend-failure-state-honesty.md [Frozen] — ✅ ALL 6 ACs done (predict_prob None on failure; ai_prob NULL not fake 0.0; to_ai_percent; frontend N/A 2026-06-13)`
  - `[model-state] docs/specs/ui-model-state-disclosure.md [Frozen] — ✅ ALL 4 ACs done (get_model_health + market_status.model_health + ModelHealthBanner 2026-06-13)`
  - `[backtest-labels] docs/specs/backtest-metric-label-honesty.md [Frozen] — ✅ ALL 4 ACs done (profit_factor None not 9999; unannualized Sharpe relabel; dynamic tooltips) [EXTENDS backtest-perf] 2026-06-13`
  - `[docs-sync] docs/specs/docs-reality-sync.md [Frozen] — ✅ ALL 6 ACs done (API_CONTRACT/README/ARCHITECTURE/TESTING/db-operations corrected 2026-06-13)`
  - `[fe-ci] docs/specs/frontend-ci.md [Frozen] — ✅ ALL 3 ACs done (Frontend CI: vitest + production build) [EXTENDS frontend-test] 2026-06-13`
  - `[data-universe] docs/specs/listed-otc-data-completeness.md [Frozen] — ✅ ALL 6 ACs done (live TWSE/TPEX universe sourcing + ETF inclusion + market/kind tags + history-coverage report/backfill; twstock demoted to fallback) 2026-06-13`
  - `[ml-labels] docs/specs/ml-label-volatility-scaling.md [Frozen] — ✅ ALL 6 ACs done (ATR volatility-scaled triple-barrier labels fix degenerate-model root cause; LABEL_MODE atr/fixed toggle; label_analysis evidence tool. Validated label rebalancing 91/5/4→59.5/13.7/26.8; full-universe OOS NOT claimed — retrain pending) 2026-06-13`
  - `[onboarding-qs] docs/specs/onboarding-quickstart.md [Frozen] — ✅ ALL 6 ACs done (offline demo fixture data/demo/demo_prices.csv + idempotent scripts/seed_demo.py + quickstart.sh/.ps1 + README; recalc gating fix so no-model fresh clone gets technical scores w/ honest NULL AI) 2026-06-13`
  - `[ml-oos-eval] docs/specs/ml-label-oos-evaluation.md [Reference] — OOS eval of atr vs fixed on 92-ticker expanded data (scripts/eval_label_modes.py). HONEST: degeneracy did NOT reproduce at scale (small-data artifact); atr modestly better on StrongBuy (P .339→.363, R .424→.518); absolute precision still low; ~5% universe, not full. 2026-06-13`
  - `[onboarding-launch] docs/specs/onboarding-single-command-launch.md [Frozen] — ✅ ALL 6 ACs done (quickstart builds UI; backend serves built SPA single-port :8000 + react-router deep-link fallback excl. /api,/assets,/static; .ps1/.bat/.sh parity incl. new start.ps1; README reorder; honesty-first unchanged) [EXTENDS onboarding-quickstart] 2026-06-20`
  - When reading specs: only open files tagged with the current task's module.
- **Canonical Commands**:
  - `/spec-intake`: Import external specs (from other LLMs, documents, or natural language). Handles large product specs via decomposition. Runs before `/bootstrap`.
  - `/bootstrap`: Task initialization & classification freeze.
  - `/plan`: Define target files, steps, risks, and rollback.
  - `/implement`: Execute implementation only when `IMPLEMENTABLE`.
  - `/review`: Check AC alignment & scope creep.
  - `/test`: Report test coverage via Test Skeleton.
  - `/handoff`: Output resumable state summary (mandatory for non-tiny-fix).
  - `/decide`: Record key decisions with reasoning to prevent cross-session re-derivation.
  - `/test-classify`: Auto-select test depth and evidence format based on task classification.
  - `/ship`: Consolidate evidence and update/archive state.
  - `ask-openrouter`: [OPTIONAL] External model delegation (natural language or `/or-*` commands). See `.agent/workflows/ask-openrouter.md`.
  - `codex-cli`: [OPTIONAL] Codex CLI delegation. See `.agent/workflows/codex-cli.md`.
- **References**:
  - `AGENTS.md`
  - `.agent/rules/engineering_guardrails.md`
  - `.agent/rules/state_machine.md`
  - `.agentcortex/docs/CODEX_PLATFORM_GUIDE.md`
  - `.agentcortex/docs/guides/token-governance.md`

> [!NOTE]
> This file is the Single Source of Truth for global project context only.
> Do not store per-task progress here; write progress to `.agentcortex/context/work/<worklog-key>.md`.

## Global Lessons (AI Error Pattern Registry)
>
> 3-5 high-value patterns max. Reviewed during /bootstrap.

- [Build Mode Strictness]: `tsc --noEmit` may pass while `npm run build` (`tsc -b`) fails on stricter generic type constraints (e.g., Recharts Formatter). Always run full production build as final validation before shipping.
- [Format Safety]: Do not copy line numbers from view tools; they break file edits.
- [E2E Perf Testing]: E2E performance tests must run against production build (`vite preview`), not dev server. React StrictMode double-invocation in dev inflates timing 3-6×, masking true render performance.
- [Work Log Lag]: Evidence must be written to Work Log during each phase (implement/review/test), not accumulated for ship. Stale logs block the ship gate and require recovery before proceeding.
- [Rotation Conflict]: When trainer.py uses timestamp-based rotation and manage_models.py uses quality-based pruning independently, a bad new model can displace a good old one before prune runs. Unify via a shared constant and quality-first sort key.
- [Sidecar Parity]: Whenever a `.pkl` model file is deleted (rotation or prune), also delete matching `.sha256`/`.sig` sidecars. trainer.py rotation and manage_models.py:cmd_delete must stay in sync on this.
- [Stacked-PR Merge]: When merging stacked PRs, retarget each dependent PR's base to mainline BEFORE merging+deleting its base branch. `gh pr merge --delete-branch` on the base auto-CLOSES the dependent PR and GitHub will NOT reopen it once the base branch is gone (cost a #23→#25 recreation). Either retarget-first, or omit `--delete-branch` until dependents are retargeted.
- [Claim vs Real Target]: Verify "it works" against the REAL target scenario, not the local dev state. The onboarding "populated dashboard" claim was false for a fresh clone (gitignored storage.db/model) until a recalc model-gating bug was fixed — local dev had a model so it masked the gap.

## Ship History

### Ship-feature-onboarding-single-command-launch-2026-06-20
- Feature shipped: One-command launch + single-port served frontend (#1 of Directly-Usable v1, P0). A fresh clone was forced into a two-terminal, two-port setup (Vite dev :5173 + backend :8000) because `quickstart` never built the frontend, so the backend's existing `frontend/v4/dist` serving path 404'd. Now `quickstart.ps1`/`.sh` run `npm ci && npm run build` (graceful if Node absent); the backend serves the built SPA at a single URL (http://localhost:8000) via the existing `read_index` plus a new `spa_fallback` catch-all (`backend/main.py`) returning index.html for react-router deep links (/backtest, /risk, /indicators) while excluding `/api`, `/assets`, `/static` (bare + prefixed) so it never shadows them. `start.bat`/`start.sh` repurposed to single-port launch; new `start.ps1` for PowerShell parity (maintainer is on PowerShell); README reordered (offline single-URL primary, full yfinance sync demoted to optional/slow); the two-terminal dev workflow (`npm run dev`) is preserved and documented. Independent fresh-agent adversarial review READY (2 LOW findings fixed in-branch: bare reserved-segment 404, start.ps1 parity). Honesty-first unchanged (AI stays N/A; no data/model behavior touched). Out of scope: Docker self-seed (#6), demo-data swap (#2), UX legibility (#3), data-sync acceleration (#4), real-AI first-run (#5).
- Tests: Pass (Backend 211/211, +6 new SPA serving tests; full suite green, 1 integration deselected; frontend `npm run build` ✓; e2e single-port :8000 serving + fallback + API-not-shadowed verified)

### Ship-ml-label-oos-evaluation-2026-06-13
- Shipped: honest follow-up verification of #2 (ATR labels). Expanded storage.db from 6 → 92 liquid TWSE tickers (~99k rows) and ran an OOS comparison (production ensemble, chronological 80/20 split) of `fixed` vs `atr` labels. **Honest findings** (docs/specs/ml-label-oos-evaluation.md + reproducible `scripts/eval_label_modes.py`): the degenerate model (precision=recall=0) did NOT reproduce at 92-ticker scale under EITHER mode — it was largely a small-data/low-volatility artifact of the 6-ticker dev DB; more data is the bigger lever. `atr` is a modest, directional improvement on the high-value StrongBuy class (precision 0.339→0.363, recall 0.424→0.518) and Buy precision (0.082→0.120); Buy recall slightly lower; absolute precision remains low (0.12–0.36). Accuracy (fixed 0.485 > atr 0.351) is not comparable (fixed's 77% Hold inflates it). Caveat: 92 tickers ≈ 5% of universe, large/liquid-cap biased — NOT full-universe. Recommendation: keep LABEL_MODE=atr; the larger future lever is universe coverage. No code-behavior change; no model committed (.pkl gitignored).
- Tests: N/A (evaluation + docs; no app code changed). Full suite unaffected (205 pass).

### Ship-feature-onboarding-quickstart-2026-06-13
- Feature shipped: Frictionless onboarding (#1 of Optimization Round 2, P1 — epic complete) — PR #24 (stacked on #23/#22). A fresh clone was empty (`storage.db` + model gitignored) until a slow yfinance sync. Bundled `data/demo/demo_prices.csv` (6 TWSE/OTC tickers incl. 2330) + idempotent offline `scripts/seed_demo.py` (loads fixture, then `recalculate_all(incremental=False)` scores DB tickers — no network) + `quickstart.sh`/`quickstart.ps1` (install→seed→run) + README "⚡ Quickstart" section. README strategy/label description corrected to the shipped ATR-default labeling (docs match code). **Honesty bug fix** in `backend/recalculate.py`: V4 technical scoring was gated behind a loadable model, so a no-model fresh clone produced 0 scores (empty dashboard) — contradicting the feature's promise; now technical scores compute regardless of model and AI probability stays NULL (honest N/A). Verified real fresh-clone (no model) → 6 score rows, AI NULL. Out of scope: bundling a trained model, production deployment, FE build automation.
- Tests: Pass (Backend 205/205, +4 new; full suite green; 1 integration deselected)

### Ship-feature-ml-label-redesign-2026-06-13
- Feature shipped: ML label redesign (#2 of Optimization Round 2, P0) — PR #23 (stacked on #22). Replaced the fixed-percentage triple-barrier training labels (+15%/+10%/-5% over 20d) — which ignore per-stock volatility and produced the degenerate class distribution (dev data Hold 91.1% / Buy 4.9% / Strong 4.0%, low-vol stocks ~100% Hold) behind the Buy/StrongBuy precision=recall=0 finding — with **ATR volatility-scaled** barriers. `core/config.py` + `core/ai/common.py`: `LABEL_MODE` (default `atr`), `ATR_TARGET_MULT`/`ATR_BUY_MULT`/`ATR_STOP_MULT` (config = SSoT). `core/ai/trainer.py`: extracted `_compute_targets()` branching on mode; `atr` scales barriers by per-row ATR-14 at entry (no look-ahead), `fixed` reproduces legacy labels byte-for-byte (toggle to revert); NaN-ATR warm-up → Hold then dropped. `core/ai/label_analysis.py` (new): reproducible distribution-evidence tool. Independent fresh-agent review READY + honesty audit clean (no overclaim). **HONEST SCOPE**: validates label-distribution rebalancing only (91/5/4 → 59.5/13.7/26.8 via shipped tool); full-universe OOS precision/recall NOT claimed (dev DB = 6 tickers); existing saved models + live predictions unchanged; new labels affect only the next training run. Out of scope: backtest exit rules, model architecture, retrain.
- Tests: Pass (Backend 201/201, +11 new; full suite green; 1 integration deselected)

### Ship-feature-data-universe-completeness-2026-06-13
- Feature shipped: Listed/OTC universe & price-data completeness (#3 of Optimization Round 2) — PR #22. Replaced the stale `twstock` static list as the primary universe source with authoritative live TWSE STOCK_DAY_ALL (上市) + TPEX daily-close (上櫃) endpoints, promoted into a reusable `core/universe_source.py` (de-duplicating `fetch_stocks.py`). ETFs (00-prefixed, 4–6 digits) now included and tagged `kind`; warrants/rights excluded. `get_all_tw_stocks` rewritten as a 5-tier fallback chain (memory→fresh-file→live→twstock→stale) that never blanks a good cache on an empty fetch; entries gain additive `market`/`kind` keys (legacy caches load via `_normalize_loaded`). Added `refresh_stock_universe(force)`, `report_history_coverage()` (predict/train coverage vs MIN_PREDICT_ROWS/MIN_TRAIN_ROWS), `backfill_history()`. Independent fresh-agent adversarial review READY; 2 LOW latent defects found & fixed in-branch (None→"None" phantom ticker guard; TPEX volume column). Out of scope: ML training-set semantics (#2), intraday data, DB schema.
- Tests: Pass (Backend 190/190, +15 new; full suite green; 1 integration deselected)

### Ship-honesty-first-2026-06-13
- Feature shipped: Honesty-first epic (data consistent with claims) — 6 changes merged via PR #20. (1) Frontend: removed `mockData.ts` fallback, nullable `useCachedApi`, honest loading/no-data/connection-error states (MarketRisk dead guard fixed). (2) Backend: `predict_prob` returns None on all failures (incl. exception, was `{"prob":0.0}`); `ai_prob` stored as NULL not fake 0.0; `to_ai_percent` helper; readers emit null; frontend "N/A"/"資料不足". (3) `get_model_health` + `/api/market_status.model_health` + `ModelHealthBanner` warns when active model is degraded (buy/strong precision=recall=0) or unavailable. (4) Backtest `profit_factor`/`net_profit_factor` None not 9999 sentinel; "Sharpe" relabelled unannualized single-period; stop/target tooltips follow sliders. (5) Docs synced (API_CONTRACT `/api/sync` + backtest V4.2 params + model_health, README stock-count/sync/workers, ARCHITECTURE lock, TESTING). (6) Frontend CI workflow (vitest + production build) enforces the frontend gate. Out of scope: model retraining, annualized Sharpe.
- Tests: Pass (Backend 176/176 +12, Frontend 53/53 +9, Production build ✅, PR #20 CI green)

### Ship-backtest-and-performance-opt-2026-06-13
- Feature shipped: Backtest hardening + candidate list performance optimization (merged via PR #7). Backend: Taiwan-standard transaction friction — configurable `commission_rate`/`tax_rate`/`slippage_rate` on `/api/backtest` applied to Net ROI & Net Win Rate; Sharpe Ratio (mean net return / stddev) and Worst Drawdown (worst single-stock MDD) added to backtest summary; Net Profit Factor; configurable strategy parameters (`target_gain`/`stop_loss`/`holding_days`) exposed at API and wired to UI sliders. Frontend: candidate list virtualization + bulk sparkline preload via `/api/v4/meta` (eliminates per-row HTTP waterfall on dashboard render); collapsible transaction-cost panel + expanded metrics on Backtest page; `core/data.py:load_sparklines_from_db` single-query batched sparkline retrieval.
- Tests: Pass (Backend 167/167, Frontend 44/44, Production build `tsc -b && vite build` ✅)

### Ship-gemini-audit-hardening-2026-06-02
- Feature shipped: System hardening based on audit findings. Fixed GET API write side-effect in `GET /api/market_status` by moving history saving to background sync task. Added 0.5s-1.5s random sleep to yfinance download loop to prevent rate-limiting. Fixed US/Crypto stock suffix mapping bug in `get_ticker_suffix`. Integrated background sync trigger and real-time progress bar UI into the frontend dashboard. Added rate-limiting (5/minute) to `POST /api/sync`.
- Tests: Pass (Backend 165/165, Frontend 44/44, Production build ✅)

### Ship-claude-frontend-ai-opt-2026-06-01
- Feature shipped: Enhanced frontend visual aesthetics & scroll performance (SVG Sparklines & smooth transitions), verified AI training pipeline correctness (dynamic labels check), integrated TPEX/OTC stocks with suffix fallback logic, protected model activation via atomic file replacement, and updated system documentation.
- Tests: Pass (Backend 163/163, Frontend 44/44, Production build ✅)

> _Older Ship History entries (2026-03-18 … 2026-03-28) archived to `.agentcortex/context/archive/ship-history-2026.md`._
