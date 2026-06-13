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
- **Active Backlog**: `docs/specs/_product-backlog.md` (honesty-first — all 6 features Shipped 2026-06-13)
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

## Ship History

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
