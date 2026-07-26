---
title: "ADR-003: core/data.py Decomposition"
status: proposed
date: 2026-07-19
applies_to:
  - "core/data.py"
---

# ADR-003: `core/data.py` Decomposition

- **Status**: Proposed (2026-07-19)
- **Origin**: 2026-07-19 tech-debt audit (MED: god-module).
- **applies_to**: `core/data.py`, importers across `backend/` + `core/`

## Context

`core/data.py` is the largest file in the codebase (~814 lines, 27 functions) and mixes
several unrelated responsibilities: DB connection + schema init, technical-indicator and
score persistence, stock-universe fetch/cache, global search, and sparkline loading. It is
imported widely across `backend/` and `core/`, so any split is a broad import-graph change.

The design roundtable's minimalist/risk seat and the pre-mortem both concluded this split
is **"not worth the risk now"**: it carries real regression surface (every importer of
`core.data` moves) and **zero honesty payoff** (it doesn't change any user-facing behavior
or fix a 說到做不到). It is recorded here so the debt is tracked, not silently dropped.

## Options

- **A — Big-bang 3-way split**: `db.py` (connection/schema), `persistence.py`
  (indicators/scores), `universe.py` (fetch/cache), updating all importers at once.
  Highest regression risk.
- **B — Incremental extraction (recommended if done)**: extract ONE cohesive seam at a
  time behind a re-export shim (`core/data.py` keeps `from .db import *` etc.) so importers
  don't move until they're migrated deliberately. Each step is independently test-verified.
- **C — Defer.** Legitimate: the module is not on fire; correctness-first + YAGNI favor
  leaving working code alone until a concrete need (a second consumer, a merge-conflict
  hotspot) justifies the churn.

## Decision (recommended)

**Prefer C (defer) unless a concrete trigger appears**; if decomposition is undertaken, use
**B (incremental, shim-backed)** — never A. Do not schedule this purely for aesthetics.

## Consequences / risks

- If pursued: a `git grep -l 'core.data\|from core import data'` census MUST precede any
  move; the re-export shim keeps old import paths valid until each importer is migrated;
  full backend suite green after every step.
- If deferred: the file keeps growing; revisit when it becomes a genuine collaboration or
  test-isolation pain point.

## Rollback

Each incremental extraction is a small branch-revertable step; the re-export shim means a
revert never leaves importers dangling.
