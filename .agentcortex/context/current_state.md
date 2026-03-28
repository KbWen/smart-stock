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
  - `.agentcortex/adr/ADR-001-vnext-self-managed-architecture.md`
- **Active Backlog**: none
  - When a multi-feature product spec is decomposed, the backlog path is recorded here (e.g., `.agentcortex/specs/_product-backlog.md`). Bootstrap reads this to detect ongoing product work.
- **Spec Index**:
  - `[api-perf] .agentcortex/specs/api-refactor-perf.md [Frozen] — ✅ ALL 5 ACs done (batch benchmark test added 2026-03-17)`
  - `[backend] .agentcortex/specs/backend-refactor-modular.md [Frozen] — ✅ ALL 8 ACs done (schema parity tests added 2026-03-17)`
  - `[frontend-api] .agentcortex/specs/frontend-api-opt.md [Frozen] — ✅ ALL 4 ACs done (E2E real render benchmark added 2026-03-18)`
  - `[frontend-test] .agentcortex/specs/frontend-testing.md [Frozen] — ✅ ALL 6 ACs done (82.7% coverage confirmed 2026-03-22) [Updated: 2026-03-22]`
  - `[cache] .agentcortex/specs/smart-stock-cache.md [Frozen] — ✅ ALL 5 ACs done (GlassCard+Button extracted 2026-03-17)`
  - `[ml-rotation] .agentcortex/specs/ml-model-rotation.md [Frozen] — ✅ ALL 4 ACs done (profit_factor rotation + None guard + MAX_SAVED_MODELS + active model protection 2026-03-18)`
  - `[fe-lazy] .agentcortex/specs/frontend-lazy-loading.md [Frozen] — ✅ ALL 4 ACs done (already implemented: App.tsx full-page lazy, MarketRisk inner Suspense, recharts in async chunks 2026-03-18)`
  - `[meta-norm] .agentcortex/specs/meta-normalization.md [Frozen] — ✅ ALL 3 ACs done (single-pass normalization, route passes requested_pairs to service 2026-03-18)`
  - `[predictor-ts] .agentcortex/specs/predictor-thread-safety.md [Frozen] — ✅ ALL 3 ACs done (threading.Lock + OrderedDict LRU cache maxsize=3 2026-03-18)`
  - `[meta-tests] .agentcortex/specs/meta-service-tests.md [Frozen] — ✅ ALL 5 ACs done (23 new tests: _to_bool, signals, safe defaults, updated_at fallback 2026-03-18)`
  - `[api-security] .agentcortex/specs/api-security-hardening.md [Frozen] — ✅ ALL 12 ACs done (path traversal, info-leak, rate limits, ticker validation, bare excepts, SHA256 integrity 2026-03-19)`
  - `[audit-doc-test] .agentcortex/specs/audit-doc-test-supplement.md [Frozen] — ✅ ALL 9 ACs done (HMAC tests 9/9, model-signing.md, rate-limiting.md 2026-03-21)`
  - `[visual-upgrade-p1] .agentcortex/specs/visual-upgrade-phase1.md [Frozen] — ✅ ALL 6 ACs done (history endpoint + PriceSignalChart + count-up animation 2026-03-27)`
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

### Ship-claude-jovial-elion-2026-03-18
- Feature shipped: Close `[frontend-api]` AC#3 — fix E2E render-time measurement (t0 = candidates-fire → Squeeze-visible); verified < 300ms on production build. Also fixed pre-existing build blockers (`vite.config.ts` import, `globalThis` in test).
- Tests: Pass (33 unit, 4 E2E)

### Ship-claude-fervent-poincare-2026-03-19
- Feature shipped: API security hardening — [api-security] 12 ACs: path traversal via VERSION_RE, SHA256 integrity check on model load, slowapi rate limits on 3 endpoints, ticker regex on all {ticker} routes, CSRF header on POST, param bounds (days/limit), info-leak removed from 500s and health endpoint, all bare excepts fixed, shared utilities (validate_version_string, profit_factor_sort_key, MAX_PREDICTION_CACHE_SIZE) extracted to common.
- Tests: Pass (124/124, 3.38s)

### Ship-claude-jovial-elion-audit-2026-03-18
- Feature shipped: 5 quick-wins from three-area audit — [ml-rotation] profit_factor-aware model rotation + `MAX_SAVED_MODELS` shared constant; [predictor-ts] thread-safe version tracking + LRU cache (OrderedDict, cap=3); [meta-norm] single-pass ticker normalization (route owns, service consumes); [meta-tests] 23 new V4MetaService unit tests + 9 ML rotation tests; [fe-lazy] confirmed + BUY label fix.
- Tests: Pass (124/124, +32 new in 3.71s)

### Ship-master-2026-03-21
- Feature shipped: AgentCortex v5.3.0 installation + path migration (agentcortex/ → .agentcortex/, docs/context/ → .agentcortex/context/). Resolved merge conflicts (HMAC feature in predictor.py merged from stash into upstream, trainer.py _cfg import restored). Code conflicts resolved: stock.py kept Query() bounds validation; predictor.py gained _verify_hmac() function.
- Tests: Pass (132/133; 1 pre-existing flaky live-market integration test)

### Ship-master-audit-doc-test-2026-03-21
- Feature shipped: Audit doc & test supplement — 9 new HMAC tests (test_predictor_hmac.py AC1-AC4, test_trainer_hmac.py AC5-AC6+integration), model-signing.md operational guide, rate-limiting.md configuration + test guide.
- Tests: Pass (132/133; 9 new tests all green)

### Ship-master-audit-2026-03-22
- Feature shipped: Multi-area audit quick-wins — Backend: TOCTOU fix in predictor.py (EAFP + single byte-read for checksum/HMAC/load), sidecar file management in manage_models.py (_SIDECAR_EXTS, copy/delete on activate/delete), CORS X-Requested-With header, backtest profit_factor: None on failure, integration marker + 8 new backend tests. Frontend: apiClient.ts in-flight race fix (generation counter + bounded cleanup), Indicators.tsx raw fetch→useCachedApi rewrite, ErrorBoundary component + integrated into all 4 pages, Dashboard refresh also invalidates /api/v4/meta, MarketStatus/MarketHistory type dedup, useStockAnalysis HOLD badge fix, timezone-safe test date helper.
- Tests: Pass (Backend 140/140, Frontend 34/34, Coverage 82.7%)

### Ship-master-visual-upgrade-2026-03-27
- Feature shipped: 視覺衝擊力升級 Phase 1 — Backend: GET /api/v4/stock/{ticker}/history endpoint (90d OHLC + signals, 60s TTL cache). Frontend: PriceSignalChart component (Recharts ComposedChart + ReferenceDot for squeeze/golden_cross/volume_spike signals), useCountUp animation hook for AI Probability count-up effect, SniperCard integration. Review found and fixed: production build type error (Tooltip formatter undefined), skeleton-forever bug on fetch error (isPlaceholder state machine), cache TTL spec mismatch (300s→60s).
- Tests: Pass (Backend 143/143, Frontend 38/38, Production build ✅)

### Ship-master-eng-audit-2026-03-28
- Feature shipped: Engineering audit round 1 quick-wins (3 fixes) — FIX-01: deleted dead code `backend/state.py` (68 lines, 0 imports, duplicate of sync.py state); FIX-02: optimized `score_repo.py:load_latest_scores_for_tickers` correlated subquery → GROUP BY aggregation JOIN; FIX-03: `useDashboardData.ts:refreshCandidates` also invalidates `/api/market_status`.
- Tests: Pass (Backend 85/85, Frontend 38/38, tsc --noEmit ✅)

### Ship-master-eng-audit-r2-2026-03-28
- Feature shipped: Engineering audit round 2 quick-wins (3 fixes) — FIX-A: `core/data.py:save_score_to_db` wrapped in try/finally to prevent connection leak on exception (called ~1000× per sync); FIX-B: `core/market.py:get_market_status` replaced full-table Pandas scan (~1000 rows) with SQL COUNT/AVG aggregates + aligned model_version selection to `GROUP BY count(*) DESC` (same as candidates), removing market/candidate version skew during partial syncs; FIX-C: `v4_stock_detail_service.py` fast-path analyst_summary enriched with RSI (40-70 bullish zone, >80 overheated) and SMA-based trend direction using stored `sma_20`/`sma_60` values, matching slow-path output quality.
- Tests: Pass (Backend 85/85, Frontend 38/38)

### Ship-master-eng-audit-r7-2026-03-28
- Feature shipped: Remaining plan-eng-review + ISSUE-05 items — FIX-DCL: `predictor.py:get_model_version()` proper double-checked locking (second check inside lock before `_set_model_version()`) prevents two threads from each doing a full `joblib.load` when both see `"unknown"` simultaneously; FIX-FAILED-COUNT: `sync.py` adds `failed_count` field to sync_status dict, incremented on per-ticker exception, reset to 0 on each sync start, exposed via `/api/sync/status`.
- Tests: Pass (Backend 101/101)

### Ship-master-eng-audit-r6-2026-03-28
- Feature shipped: ML pipeline hardening (plan-eng-review findings) — FIX-MODEL-ATOMIC: `trainer.py` versioned sha256/sig sidecar now uses atomic write (mkstemp+os.replace); MODEL_PATH activation order changed to sha256→sig→pkl with copy-to-temp+os.replace pattern, eliminating the window where pkl content ≠ sha256 content; FIX-WARMUP-DROP: `prepare_features` training path now calls `dropna(subset=FEATURE_COLS)` before `fillna(0)`, removing early indicator warmup rows (first ~240 bars where SMA240 is NaN) that were previously being fed to the model as fake-zero features.
- Tests: Pass (Backend 101/101)

### Ship-master-eng-audit-r5-2026-03-28
- Feature shipped: Regression tests (16) + ML pipeline bug fixes (2) — TEST: `test_indicators_regression.py` 16 tests covering all eng-audit-r4 edge cases (KD/BB flat price, MACD/ATR zero close, system_repo connection leak, score_repo tie-breaking); FIX-1: `backend/routes/sync.py:147` ai_prob defaulted to None when predict_prob returned None (checksum fail / model not found) — now stays 0.0; FIX-2: `backend/backtest.py:264` profit_factor=float('inf') when zero losses broke json.dump during training (model saved but history orphaned) — capped to 9999.0.
- Tests: Pass (Backend 101/101)

### Ship-master-eng-audit-r4-2026-03-28
- Feature shipped: Engineering audit round 4 quick-wins (5 fixes) — FIX-A/B: `core/analysis.py` KD stochastic + Bollinger Band `bb_percent` both divided by zero when prices are flat over their window (guard: +1e-9 epsilon); FIX-C: `core/indicators_v2.py` MACD hist and ATR percent normalized by `close` now use `.replace(0, np.nan)` to match trainer.py convention; FIX-D: `backend/repositories/system_repo.py:check_db_health` connection leak fixed with try/finally; FIX-E: `backend/repositories/score_repo.py` deterministic tie-breaking when two rows share same `updated_at` (ORDER BY rowid DESC).
- Tests: Pass (Backend 85/85)

### Ship-master-eng-audit-r3-2026-03-28
- Feature shipped: Engineering audit round 3 quick-wins (3 fixes) — FIX-1: `core/ai/trainer.py` rotation loop now cleans `.sha256`/`.sig` sidecar files alongside `.pkl` deletion (prevents orphan accumulation per training run); FIX-2: Atomic JSON writes via `tempfile.mkstemp` + `os.replace` in `core/market.py:save_market_history`, `core/ai/trainer.py` history write, and `backend/manage_models.py:save_history` (prevents file corruption on process crash); FIX-3: removed dead `y_pred = clf_gb_cv.predict(X_v)` line in trainer.py CV loop + changed `logger.error(f"...")` f-string to `logger.error("...", e)` in market.py.
- Tests: Pass (Backend 85/85)
