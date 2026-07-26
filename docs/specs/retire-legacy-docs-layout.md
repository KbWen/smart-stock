---
status: draft
title: Retire the legacy `docs/` framework-documentation layout
created: 2026-07-26
source: 2026-07-26 repo hygiene survey (Tier 3 of 3)
---

# Retire the legacy `docs/` framework-documentation layout

## Problem

17 files exist under both `docs/` and `.agentcortex/docs/` with the same names and drifted content.
This violates the doc-governance rule "one topic, one canonical file" and leaves a reader unable to tell
which copy is authoritative.

The cause is a layout migration that was never finished. An older AgentCortex version deployed framework
documentation into the downstream project's `docs/` tree. The current agentic-os version deploys it into
`.agentcortex/docs/` instead. The old copies were never removed.

## Evidence that `.agentcortex/docs/` is canonical and `docs/` is stale

| Signal | Finding |
|---|---|
| Deploy target | `deploy.sh:998-1008` writes framework docs to `.agentcortex/docs/` only. No `deploy_file` call targets bare `docs/`. |
| Manifest coverage | 30 entries under `.agentcortex/docs/`; **0** entries under bare `docs/`. |
| Framework's own record | `deploy.sh:1161-1178` lists 14 of the 17 in its `managed[]` **de-registration** list — the framework has already declared these paths no longer managed. |
| Validators | `validate.sh:693,723-724,1112-1121` and `validate.ps1:680,712-713,1070-1081` resolve every framework-doc check to `.agentcortex/docs/`. Nothing requires a bare `docs/` copy. |
| Authorship | All 17 were last touched by a framework-sync or mechanical-hygiene commit (`deefc97`, `0e20372`, `a3f5f1b`, `5804934`). None carries project-authored content. |
| Inbound links | No project-owned file references any of the 17. The only mentions are `CHANGELOG.md:71` (a historical release note) and `.agentcortex/context/archive/work.md` (an archived 2026-02 work log). |

## Secondary defect: a half-applied `.gitignore` rule

`.gitignore:48-52` ignores four English framework docs under `docs/` as "Template-provided Documentation",
but not their `_zh-TW` counterparts. The result is that only the *translations* are under version control
while the English originals are not — the inverse of the repo's "English is canonical for artifacts" rule
in `AGENTS.md §Chat Language Policy`. Deleting the tracked copies removes the asymmetry at its source.

## Acceptance Criteria

- **AC-1** — All 17 stale framework copies are removed from `docs/`, and `git ls-files docs` contains no
  file whose basename also exists under `.agentcortex/docs/`.
- **AC-2** — Every remaining file under `docs/` is project-owned (API contract, architecture, ADRs,
  project guides, specs, screenshots, project_meta).
- **AC-3** — No framework behavior regresses: `validate.sh` PASS/WARN/FAIL counts are unchanged against a
  stash-clean baseline, with any line-level delta individually explained.
- **AC-4** — The full test suite is unchanged (288 passed / 1 deselected); this change touches no code.
- **AC-5** — A regression guard asserts the `docs/` ↔ `.agentcortex/docs/` namespaces stay disjoint, and
  the guard is proven non-vacuous by falsification.
- **AC-6** — The `.gitignore` "Template-provided Documentation" block is reconciled with the new reality
  and its purpose stated, so a future reader is not left wondering why only four files are listed.

## Non-goals

- Re-deploying or upgrading the framework (`.agentcortex/docs/` content is not touched).
- Deleting the four untracked English copies still sitting on local disks. They are gitignored, invisible
  to the repository, and removing untracked local state is not something this change should do silently.
- Fixing the stale comment at `.github/workflows/integrity-check.yml:62-64`, which still describes
  `docs/CODEX_PLATFORM_GUIDE.md` as framework-managed. Real but out of scope; recorded as follow-up.
- Any change to `docs/specs/`, `docs/adr/`, or project-authored documentation.

## Domain Decisions

- **[DECISION]** `.agentcortex/docs/` is the sole canonical location for framework documentation in this
  downstream project; `docs/` is exclusively project-owned. This is not a new choice — it ratifies what
  `deploy.sh`, the manifest, and both validators already implement.
- **[CONSTRAINT]** The 17 removals must be pure deletions. Any perceived content worth keeping would mean
  the file was project-authored, which the authorship evidence rules out; if a counter-example appears
  during implementation, stop and re-scope rather than silently preserving a merge.
- **[TRADEOFF]** The four untracked English copies are left on disk. Removing them would fully retire the
  old layout, but it destroys local state that git cannot restore. The repository-visible outcome is
  identical either way, so the safe option is taken and the residue is documented.
