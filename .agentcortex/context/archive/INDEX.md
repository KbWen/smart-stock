# Archive Index

Lightweight retrieval index for archived work logs. Updated during `/ship` archival.
Agent reads this file at bootstrap to find relevant past context without scanning all archives.

> **Rule**: Read this index (~few lines per entry). Only open an archived log if its module/pattern matches your current task.

## By Module

<!-- Format: - <file-or-module>: [<archived-log>] <key-decision-or-lesson> -->
- validate.sh: [codex-template-import-cleanup-namespacing-2026-03-07.md] text integrity checks validated against real repo bytes
- deploy_brain.*: [codex-template-import-cleanup-namespacing-2026-03-06.md] wrapper files delegate to agentcortex/bin/
- AGENTS.md: [codex-master-2026-03-06.md] namespace reorganization preserves fixed anchors
- agentcortex/: [codex-template-import-cleanup-namespacing-2026-03-06.md] canonical namespace for framework assets

- e2e/dashboard.spec.ts: [claude-jovial-elion-2026-03-18.md] E2E perf timing fixed: t0=candidates-fire, not mock-handler duration
- playwright.config.ts: [claude-jovial-elion-2026-03-18.md] PLAYWRIGHT_BASE_URL env override; production build required for E2E perf tests
- vite.config.ts: [claude-jovial-elion-2026-03-18.md] import vitest/config to fix TS `test` property type error
- frontend-api-opt.md spec: [claude-jovial-elion-2026-03-18.md] AC#3 closed — real render benchmark < 300ms on prod build

- core/ai/predictor.py: [claude-jovial-elion-audit-2026-03-18.md] Thread-safe version tracking (threading.Lock) + OrderedDict LRU cache capped at 3 entries
- core/ai/trainer.py, common.py: [claude-jovial-elion-audit-2026-03-18.md] Profit_factor-aware rotation; MAX_SAVED_MODELS=5 shared constant; None guard (-1.0) + active-model protection
- backend/manage_models.py: [claude-jovial-elion-audit-2026-03-18.md] Prune uses same profit_factor key + MAX_SAVED_MODELS constant as trainer.py
- backend/services/v4_meta_service.py: [claude-jovial-elion-audit-2026-03-18.md] Removed double normalization; service accepts pre-normalized requested_pairs
- tests/test_backend/test_meta_service.py: [claude-jovial-elion-audit-2026-03-18.md] 23 new unit tests covering _to_bool, signals, unknown ticker, updated_at fallback, dedup
- tests/test_core/test_model_rotation.py: [claude-jovial-elion-audit-2026-03-18.md] 9 new tests covering ML rotation AC1–AC4
- frontend/v4/src/hooks/useStockAnalysis.ts: [claude-jovial-elion-audit-2026-03-18.md] BUY label fix for 50-70% AI probability range

- core/ai/predictor.py: [master-audit-2026-03-22.md] TOCTOU fix — remove os.path.exists guards; EAFP + single byte-read for checksum/HMAC/joblib.load
- backend/manage_models.py: [master-audit-2026-03-22.md] _SIDECAR_EXTS constant; copy/delete .sha256+.sig on activate/delete
- backend/main.py: [master-audit-2026-03-22.md] CORS allow_headers += X-Requested-With (required for smart_scan POST CSRF guard)
- core/ai/trainer.py: [master-audit-2026-03-22.md] backtest failure → profit_factor: None (not 0) for correct quality-sort ranking
- tests/test_core/test_model_rotation.py: [master-audit-2026-03-22.md] 3 sidecar tests (activate-copies, skips-missing, delete-removes)
- tests/test_backend/test_api.py: [master-audit-2026-03-22.md] 5 new tests: XHR header guard, /api/init smoke, /api/search valid+empty
- frontend/v4/src/lib/apiClient.ts: [master-audit-2026-03-22.md] in-flight race fixed — generation counter prevents stale writes after invalidation; invalidationGen deleted on cache write (bounded)
- frontend/v4/src/pages/Indicators.tsx: [master-audit-2026-03-22.md] rewritten from raw useEffect fetch to useCachedApi+useMemo; isPlaceholder loading guard
- frontend/v4/src/components/ErrorBoundary.tsx: [master-audit-2026-03-22.md] new class component — wraps all Suspense blocks in App, Dashboard, Backtest, MarketRisk
- frontend/v4/src/hooks/useDashboardData.ts: [master-audit-2026-03-22.md] refreshCandidates invalidates /api/v4/meta; MarketHistory exported
- frontend/v4/src/hooks/__tests__/useStockAnalysis.test.ts: [master-audit-2026-03-22.md] timezone-safe date helper: toLocaleDateString('en-CA') vs UTC toISOString

- backend/services/, backend/repositories/: [backend-refactor-modular-2026-03-05.md] Layered architecture — Services + Repositories extracted from stock.py
- backend/main.py, routes/*: [optimize-api-arch-2026-03-04.md] V4 API arch optimization — bulk meta endpoint introduced
- frontend/v4/src/hooks/useDashboardData: [optimize-frontend-cache-2026-03-04.md] Bulk meta fetch + useCachedApi TTL cache finalization
- frontend/v4/src/components/StockList.tsx: [claude-mystifying-greider-2026-03-18.md] CI fix + StockList mock fix; coverage >40%
- .github/workflows/, frontend coverage: [nifty-newton-2026-03-17.md] AgentCortex v5.2.0 install + project audit; all 5 specs frozen

## By Pattern

<!-- Format: - [<pattern-tag>]: <archived-log>(s) -->
- [namespace-migration]: codex-template-import-cleanup-namespacing-2026-03-06.md
- [text-integrity]: codex-template-import-cleanup-namespacing-2026-03-07.md
- [windows-compat]: codex-template-import-cleanup-namespacing-2026-03-07.md
- [worklog-normalization]: codex-template-import-cleanup-namespacing-2026-03-06.md
- [cross-platform-validation]: codex-template-import-cleanup-namespacing-2026-03-07.md
- [e2e-perf-testing]: claude-jovial-elion-2026-03-18.md
- [vitest-config]: claude-jovial-elion-2026-03-18.md
- [thread-safety]: claude-jovial-elion-audit-2026-03-18.md
- [lru-cache]: claude-jovial-elion-audit-2026-03-18.md
- [dry-normalization]: claude-jovial-elion-audit-2026-03-18.md
- [quality-based-rotation]: claude-jovial-elion-audit-2026-03-18.md
- [worklog-lag-recovery]: claude-jovial-elion-audit-2026-03-18.md
- [toctou-eafp]: master-audit-2026-03-22.md
- [cache-race-generation-counter]: master-audit-2026-03-22.md
- [error-boundary-suspense]: master-audit-2026-03-22.md
- [timezone-local-date]: master-audit-2026-03-22.md

## By Decision

<!-- Format: - D: "<decision summary>" → <archived-log> -->
- D: "Use grep over rg for portability in validation gates" → codex-template-import-cleanup-namespacing-2026-03-07.md
- D: "Work Log key = filesystem-safe normalization of branch name" → codex-template-import-cleanup-namespacing-2026-03-06.md
- D: "Fixed anchors (AGENTS.md, .agent/, docs/) stay at repo root" → codex-template-import-cleanup-namespacing-2026-03-06.md
- D: "New integrity checks must validate against real repo bytes before baselining" → codex-template-import-cleanup-namespacing-2026-03-07.md
- D: "E2E perf tests must run against `vite preview` (prod build), not `vite dev` — StrictMode inflates timing 3-6×" → claude-jovial-elion-2026-03-18.md
- D: "Use `vitest/config` not `vite` for defineConfig when test block is present in vite.config.ts" → claude-jovial-elion-2026-03-18.md
- D: "Rotation strategy: profit_factor-first (not timestamp-first) ensures quality retention over recency" → claude-jovial-elion-audit-2026-03-18.md
- D: "Route owns normalization, service consumes pre-normalized pairs — DRY and clear ownership boundary" → claude-jovial-elion-audit-2026-03-18.md
- D: "LRU model cache cap=3 limits memory to ~150-300MB peak under concurrent FastAPI thread pool load" → claude-jovial-elion-audit-2026-03-18.md
- D: "TOCTOU in FastAPI server: remove os.path.exists() guards before open(); use try/except FileNotFoundError instead" → master-audit-2026-03-22.md
- D: "apiClient invalidation race: generation counter in .then() prevents in-flight writes after cache clear; delete entry after successful write" → master-audit-2026-03-22.md
- D: "Test date helpers: use toLocaleDateString('en-CA') not toISOString() when hook compares via toDateString() — UTC drift at UTC+8 midnight" → master-audit-2026-03-22.md
