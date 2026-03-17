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
  - `[frontend-api] docs/specs/frontend-api-opt.md [Frozen] — 3/4 ACs ✅; AC#3 E2E <300ms mocked only`
  - `[frontend-test] docs/specs/frontend-testing.md [Frozen] — 5/6 ACs ✅; AC#6 coverage % needs runtime verify`
  - `[cache] docs/specs/smart-stock-cache.md [Frozen] — ✅ ALL 5 ACs done (GlassCard+Button extracted 2026-03-17)`
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
