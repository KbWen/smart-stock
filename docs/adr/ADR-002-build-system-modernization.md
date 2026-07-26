---
title: "ADR-002: Build-System Modernization (pyproject + dependency split + lockfile)"
status: proposed
date: 2026-07-19
applies_to:
  - "requirements.txt"
  - "pyproject.toml"
  - "backend/**"
  - "core/**"
  - "quickstart.*"
---

# ADR-002: Build-System Modernization (pyproject + dependency split + lockfile)

- **Status**: Proposed (2026-07-19)
- **Origin**: 2026-07-19 tech-debt audit (HIGH: unpinned deps) + follow-ups.
- **applies_to**: `requirements.txt`, `pyproject.toml`, `backend/`, `core/`, `quickstart.*`

## Context

The audit's top HIGH finding was that `requirements.txt` had **zero version pins**,
undermining the "Reproducible Reference Layer". PR #51 pinned the **runtime** deps as
a first step, but three related problems remain and are entangled:

1. **No `pyproject.toml`** — the project isn't pip-installable and carries no package
   metadata (name/version/description/urls) for distribution or discovery.
2. **6 `sys.path.append`/`insert` hacks** (`backend/main.py:6`, `backtest.py:8`,
   `manage_models.py:4`, `recalculate.py:6`, `train_ai.py:8`, `core/ai/trainer.py:412`)
   exist so `python backend/main.py` resolves `from core.…` **without installing** the
   package. Removing them REQUIRES switching the run-flow to an editable install
   (`pip install -e .`) — otherwise the documented one-command run breaks.
3. **Runtime and test deps are mixed** in one `requirements.txt` (pytest/httpx/
   pytest-mock alongside fastapi/pandas). A naive `pyproject` that reads this file as
   `[project.dependencies]` would ship pytest as a *runtime* dependency; listing deps
   separately in `pyproject` would create a **second dependency source of truth** — the
   exact SSoT violation this remediation epic fights.

These cannot be fixed piecemeal without creating new inconsistency.

## Options

- **A — `pyproject` with `dynamic` deps from `requirements.txt`.** Cheapest, but pulls
  test deps in as runtime. Rejected (mislabels deps).
- **B — Split + optional-deps + lockfile (recommended).** `pyproject.toml` declares
  `[project.dependencies]` (runtime, from a `requirements.txt` that no longer contains
  test tooling) and `[project.optional-dependencies].dev` (pytest/httpx/pytest-mock);
  a lockfile (uv / pip-tools) captures transitive pins. Removes the dep-mixing and gives
  one install spec + one reproducible lock.
- **C — Leave as-is.** Rejected — leaves the HIGH reproducibility gap and the run-flow
  fragility.

## Decision (recommended)

Adopt **B, in two phases** so blast radius stays reviewable:

- **Phase 1 (feature)**: add `pyproject.toml` (setuptools, `packages.find` over
  `backend*`/`core*`, `[tool.pytest.ini_options]` to pin current pytest behavior);
  split `requirements.txt` → runtime + `requirements-dev.txt` (or optional-deps);
  generate a committed lockfile. **Keep the `sys.path` hacks** — zero import-breakage.
- **Phase 2 (architecture-change)**: switch the run-flow to `pip install -e .`
  (update `quickstart.sh`/`.ps1`, README, Dockerfile), then remove the 6 hacks, with a
  full-suite + real `python backend/main.py` boot verification.

## Consequences / risks

- Adding `pyproject.toml` can shift pytest's `rootdir` — Phase 1 MUST re-run the full
  suite (283 backend + vitest) and confirm identical pass counts.
- Phase 2 is the risky part (import resolution across every entry point) — it is a
  separate PR with an explicit boot test, not bundled with Phase 1.
- Coordinate with PR #51: `requirements.txt` becomes runtime-only; the pins move with it.

## Rollback

Both phases are additive/branch-reverted. Phase 2's run-flow change is guarded by the
boot test; if an entry point breaks, revert the hack-removal commit (hacks restored).
