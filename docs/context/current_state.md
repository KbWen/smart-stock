# Project Current State (vNext)

- **Project Intent**: Build a self-managed Agent OS for Codex Web / Codex App / Google Antigravity to reduce human procedural burden and continuously lower token costs.
- **Core Guardrails**:
  - Correctness first: No claim of completion without evidence.
  - Small & reversible: Prioritize small, reversible changes; avoid unauthorized refactoring.
  - Document-first: Core logic or structural changes require a Spec/ADR first.
  - Handoff gate: Non-`tiny-fix` tasks must produce a traceable handoff summary.
- **System Map**:
  - Global SSoT: `docs/context/current_state.md`
  - Task Isolation: `docs/context/work/<branch-name>.md`
  - Workflows & Policies: `.agent/workflows/*.md`, `.agent/rules/*.md`
- **ADR Index**:
  - `docs/adr/ADR-001-vnext-self-managed-architecture.md`
- **Spec Index**:
  - `[api-perf] docs/specs/api-refactor-perf.md [Frozen] — ✅ ALL 5 ACs done (batch benchmark test added 2026-03-17)`
  - `[backend] docs/specs/backend-refactor-modular.md [Frozen] — ✅ ALL 8 ACs done (schema parity tests added 2026-03-17)`
  - `[frontend-api] docs/specs/frontend-api-opt.md [Frozen] — ✅ ALL 4 ACs done (E2E real render benchmark added 2026-03-18)`
  - `[frontend-test] docs/specs/frontend-testing.md [Frozen] — ✅ ALL 6 ACs done (82.12% coverage confirmed 2026-03-18)`
  - `[cache] docs/specs/smart-stock-cache.md [Frozen] — ✅ ALL 5 ACs done (GlassCard+Button extracted 2026-03-17)`
  - `[ml-rotation] docs/specs/ml-model-rotation.md [Frozen] — ✅ ALL 4 ACs done (profit_factor rotation + None guard + MAX_SAVED_MODELS + active model protection 2026-03-18)`
  - `[fe-lazy] docs/specs/frontend-lazy-loading.md [Frozen] — ✅ ALL 4 ACs done (already implemented: App.tsx full-page lazy, MarketRisk inner Suspense, recharts in async chunks 2026-03-18)`
  - `[meta-norm] docs/specs/meta-normalization.md [Frozen] — ✅ ALL 3 ACs done (single-pass normalization, route passes requested_pairs to service 2026-03-18)`
  - `[predictor-ts] docs/specs/predictor-thread-safety.md [Frozen] — ✅ ALL 3 ACs done (threading.Lock + OrderedDict LRU cache maxsize=3 2026-03-18)`
  - `[meta-tests] docs/specs/meta-service-tests.md [Frozen] — ✅ ALL 5 ACs done (23 new tests: _to_bool, signals, safe defaults, updated_at fallback 2026-03-18)`
  - `[api-security] docs/specs/api-security-hardening.md [Frozen] — ✅ ALL 12 ACs done (path traversal, info-leak, rate limits, ticker validation, bare excepts, SHA256 integrity 2026-03-19)`
  - When reading specs: only open files tagged with the current task's module.
- **Canonical Commands**:
  - `/bootstrap`: Task initialization & classification freeze.
  - `/plan`: Define target files, steps, risks, and rollback.
  - `/implement`: Execute implementation only when `IMPLEMENTABLE`.
  - `/review`: Check AC alignment & scope creep.
  - `/test`: Report test coverage via Test Skeleton.
  - `/handoff`: Output resumable state summary (mandatory for non-tiny-fix).
  - `/ship`: Consolidate evidence and update/archive state.
  - `ask-openrouter`: [OPTIONAL] External model delegation (natural language or `/or-*` commands). See `.agent/workflows/ask-openrouter.md`.
  - `codex-cli`: [OPTIONAL] Codex CLI delegation. See `.agent/workflows/codex-cli.md`.
- **References**:
  - `AGENTS.md`
  - `.agent/rules/engineering_guardrails.md`
  - `.agent/rules/state_machine.md`
  - `docs/CODEX_PLATFORM_GUIDE.md`
  - `docs/guides/token-governance.md`

> [!NOTE]
> This file is the Single Source of Truth for global project context only.
> Do not store per-task progress here; write progress to `docs/context/work/<branch-name>.md`.

## Global Lessons (AI Error Pattern Registry)
>
> 3-5 high-value patterns max. Reviewed during /bootstrap.

- [Global Memory]: Branch-local lessons are lost after archival. Use Global Lessons Registry for persistence.
- [Format Safety]: Do not copy line numbers from view tools; they break file edits.
- [E2E Perf Testing]: E2E performance tests must run against production build (`vite preview`), not dev server. React StrictMode double-invocation in dev inflates timing 3-6×, masking true render performance.
- [Work Log Lag]: Evidence must be written to Work Log during each phase (implement/review/test), not accumulated for ship. Stale logs block the ship gate and require recovery before proceeding.
- [Rotation Conflict]: When trainer.py uses timestamp-based rotation and manage_models.py uses quality-based pruning independently, a bad new model can displace a good old one before prune runs. Unify via a shared constant and quality-first sort key.

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
