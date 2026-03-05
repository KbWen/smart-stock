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
  - [frontend-data] docs/specs/smart-stock-cache.md [Frozen]
  - [api-core] docs/specs/api-refactor-perf.md [Frozen]
  - [frontend-v4] docs/specs/frontend-api-opt.md [Frozen]
  - [frontend-v4] docs/specs/frontend-testing.md [Frozen]
  - [auth] docs/specs/auth/login_flow.md [Frozen]
  - [payment] docs/specs/payment/checkout.md [Draft]
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
- [Ticker Consistency]: Backend lookup should use normalized tickers, but API response should match requested keys to avoid frontend mapping failure.
- [Signal Priority]: Deduplicate signals using a `Set` when merging legacy and new structures to ensure UI cleanliness.
- [Bulk Fetching]: Always prefer consolidated bulk endpoints (e.g., `/api/v4/meta`) over per-item fetches to eliminate network waterfalls.
- [Vitest Partitioning]: Exclude `e2e` directories from Vitest to prevent conflicts with Playwright test runners.
- [HTML Validation]: React Testing Library catches invalid HTML hierarchy (e.g., `div` in `tbody`); ensure test wrappers follow DOM standards.
- [Case Sensitivity]: UI labels should be matched with case-insensitive regex in tests to remain resilient to styling changes (e.g., CSS text-transform).

## Ship History

### Ship-feat/frontend-testing-2026-03-05

- Feature shipped: Established Vitest (Unit) and Playwright (E2E) infrastructure for Frontend V4. Added coverage reporting and initial CandidateRow tests.
- Tests: Pass (Core logic verified)
