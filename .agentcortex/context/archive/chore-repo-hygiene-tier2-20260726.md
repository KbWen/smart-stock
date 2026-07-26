# Work Log: chore/repo-hygiene-tier2

## Header

- Branch: `chore/repo-hygiene-tier2`
- Classification: `quick-win`
- Classified by: `claude-opus-5`
- Frozen: `true`
- Created Date: `2026-07-26`
- Owner: `KbWen`
- Guardrails Mode: `Quick`
- Current Phase: `ship`
- Diff Base SHA: `2c97e05429c022d4f4233aef95d35222e5538266`
- Checkpoint SHA: `4786a72`
- Recommended Skills: `verification-before-completion (auto), karpathy-principles (auto), systematic-debugging (auto, on-encounter)`
- Primary Domain Snapshot: `none`
- SSoT Sequence: `1`

---

## Session Info

- Agent: `claude-opus-5` · Session: `2026-07-26 11:15 UTC` · Platform: `claude-code`
- Guardrails loaded: AGENTS.md §Core Directives, state_machine.md (Quick mode — `engineering_guardrails.md`
  deliberately NOT read; reading it on a quick-win is a Token Leak violation per `bootstrap.md §0`)
- Override / Downstream-Capabilities / private: absent
- Read receipt: SSoT known from this session (Update Sequence 1, Last Updated 2026-07-26 after the Tier 1
  ship) · Work Log created · Spec Scope: none

---

## Task Description

Tier 2 of the 3-tier repo hygiene cleanup. Tier 1 shipped as PR #56 (`2c97e05`). **Re-scoped from 5 items
to 3 after evidence** — see Drift Log.

1. Delete the orphaned `tools/` directory (4 files). All four have canonical counterparts in
   `.agentcortex/tools/`, which is what `deploy.sh:739 _runtime_tools` maintains and the manifest records.
   `tools/` is absent from the manifest, never deployed, and referenced by nothing — a leftover from the
   2026-06-13 AgentCortex v5.3.0 → agentic-os v1.5.3 migration.
2. Fix root `CONTRIBUTING.md`, currently titled "Contributing to **AgentCortex**" — wrong project.
   Same identity-leak class as the `CITATION.cff` / `README_zh-TW.md` leaks fixed in PR #47.
   `docs/project_meta/CONTRIBUTING.md` holds the correct Smart Stock content.
3. Fix `docs/specs/_product-backlog-honesty-first-2026-06-13.md` frontmatter: `status: living` on a
   historical snapshot. The other two snapshots are correctly `status: archived`.

Classification rationale: `bootstrap.md §0` row 3 (touches `docs/specs/`) sets the floor at `quick-win`.
Nothing here touches installer source-selection, so the Tier 1 provenance escalation does NOT apply.
No application code, no behavior change. Chain: `/plan` → `/implement` → `/ship` (review/test optional
per §10.4 — but validate + full suite will still be run as evidence, given what Tier 1 surfaced).

---

## Phase Sequence

| Phase | Status | Entered | Notes |
|---|---|---|---|
| bootstrap | done | 2026-07-26 | `quick-win`; scope corrected 5 → 3 items |
| plan | done | 2026-07-26 | 3 items, 7 paths; Confidence 93% |
| implement | done | 2026-07-26 | 7 paths, zero divergence, commit `4786a72` |
| review | optional | — | quick-win exempt (§10.4) |
| test | optional | — | quick-win exempt (§10.4) |
| handoff | n/a | — | quick-win exempt |
| ship | done | 2026-07-26 | SSoT Seq 1→2; archived |

---

## Phase Summary

- bootstrap: classified `quick-win` (floor set by the `docs/specs/` row of the §0 table). Branch cut from
  `master@2c97e05`. The headline outcome is a **scope correction**: two of the five items I reported to
  the user after the Tier 1 survey were not duplicates at all. Evidence in Drift Log.
- plan: 3 items → 7 target paths. Two risks pre-cleared before planning (deploy does not overwrite root
  `CONTRIBUTING.md`; nothing references `tools/`). | Confidence: 93% — high.
- implement: 7 paths, zero scope divergence. One unplanned but necessary edit: moving CONTRIBUTING to the
  repo root broke its two bare `TESTING.md` / `CODE_STYLE.md` links, repointed at `docs/project_meta/`.
  | Confidence: 96% — high.
- ship: PASS. validate 92/9/0 against a stash-clean baseline — single explained delta. 288 tests pass.

⚡ ACX

---

## Gate Evidence

- Gate: bootstrap | Verdict: PASS | Classification: quick-win | Timestamp: 2026-07-26T11:15:00Z
- Gate: plan | Verdict: PASS | Classification: quick-win | Timestamp: 2026-07-26T13:05:00Z
- Gate: implement | Verdict: PASS | Classification: quick-win | Timestamp: 2026-07-26T13:20:00Z
- Gate: ship | Verdict: PASS | Classification: quick-win | Timestamp: 2026-07-26T13:30:00Z

---

## External References

| Type | Path | Notes |
|---|---|---|
| Spec | — | quick-win is Spec-Gate exempt |
| Prior | PR #56 / `2c97e05` | Tier 1, merged 2026-07-26 |
| Follow-up | Tier 3 | 17 drifted docs between `docs/` and `.agentcortex/docs/` + `.gitignore` asymmetry (EN template docs ignored, `_zh-TW` committed). Likely ADR-worthy. |

---

## Known Risk

- **R1 (medium) — deleting `tools/` could break an unseen caller.** Mitigation, already gathered:
  `git grep` finds no reference outside the directory itself; the manifest records only
  `.agentcortex/tools/*`; `validate.sh:40-41` and `validate.ps1:232-233` resolve the text-integrity tools
  to `.agentcortex/tools/`. Plan must re-confirm against CI workflows before deleting.
- **R2 (medium) — editing root `CONTRIBUTING.md` could be undone by the next deploy.** This is the exact
  trap that invalidated Tier 1's item 4. **Checked before classifying**: `deploy.sh:1159` lists
  `managed["CONTRIBUTING.md"]`, but that awk block is a *de-registration* list (it also contains the
  pre-vNext `docs/context/...` paths and the `CITATION.cff` / `README_zh-TW.md` entries already corrected
  in #47). There is **no `deploy_file` call** for it and it is **not in the manifest** → deploy will not
  overwrite it. Safe to edit.
- **R3 (low) — changing `status: living` → `archived` may alter validator behavior.** Some checks
  (`check_lifecycle_frontmatter.py`, `check_ssot_caps.py`) key off lifecycle status. Plan must capture a
  validate baseline first, exactly as Tier 1 did, and explain any delta.
- **Rollback**: every item is a single squashable commit on a dedicated branch; `git revert <sha>` restores
  all three. No untracked or gitignored state is touched, so a git-level revert is complete.

---

## Decisions

none

---

## Conflict Resolution

none — `karpathy-principles` vs `verification-before-completion` is `compatible` (matrix read during the
Tier 1 bootstrap this session; not re-read).

---

## Skill Notes

- **karpathy-principles**: §1 surface assumptions rather than resolving them silently; §3 touch only what
  you must. Directly responsible for the 5 → 3 scope correction below.
- **verification-before-completion**: 5-gate sequence at implement/ship.
- **systematic-debugging**: on encounter only.

---

## Drift Log

- Skip Attempt: NO · Gate Fail Reason: N/A · Token Leak: NO
- **Scope correction at bootstrap (5 → 3 items)**. After the Tier 1 ship I reported five "diverged
  duplicate pairs" to the user. Verifying each before classifying showed two were not duplicates:
  - `daily_run.sh` root vs `scripts/daily_run.sh` — `scripts/` is a deliberate 4-line backward-compat
    wrapper that `cd`s up and delegates to the root script. Both intentional. **Dropped.**
  - `codex/rules/` vs `.codex/rules/` — both framework-managed with different roles.
    `codex/rules/default.rules` is deployed (`deploy.sh:845`), manifest-recorded (`:207`) and is
    validate's `ACTIVE_CODEX_RULES` (`validate.sh:644`); `.codex/INSTALL.md` is deployed at
    `deploy.sh:1035`. **Dropped.**
  Conversely `tools/` turned out to be *larger* than reported — not just the two
  `check_text_integrity.*` files but all four, the whole directory being a migration orphan.
- Repeat of the Tier 1 lesson: a survey-level "looks like a duplicate" judgement does not survive contact
  with `deploy.sh` / manifest / validator evidence. Verify each candidate against who *manages* it before
  putting it in a plan.
- ADR coverage: `docs/adr/` non-empty → no new-project prompt; the `no_covering_adr` check is
  feature/architecture-change only and is skipped for `quick-win` per `bootstrap.md §0a`.
- Work Log size discipline (Tier 1 lesson): this log starts compact and all writes use LF. Tier 1's log
  tripped `[FAIL] work log compaction` three times, partly because Python writes emitted CRLF on Windows.
- **Measurement error, mine**: the first Tier 2 "baseline" (94 PASS / 9 WARN) was invalid. A backgrounded
  validate run and a foreground re-run wrote to the SAME output file concurrently, interleaving their
  output and duplicating lines. Detected by a mangled `cklog consistency:` fragment in the tail. Re-measured
  properly via `git stash push --include-untracked` → validate → `stash pop`, giving the true clean baseline
  of 92/9/0. Lesson: never let two runs share one capture file, and treat a truncated/garbled tail as
  evidence of a corrupt measurement rather than a real regression.
- Unplanned edit accepted at implement: repointing the two relative links inside CONTRIBUTING.md. Not scope
  creep — moving the file to the root would otherwise have left two broken references.

---

## Review Feedback

none

---

## Red Team Findings

n/a — `red-team-adversarial` does not trigger for `quick-win` (auto-trigger matrix).

---

## Design Reference

none — no user-visible UI.

---

## Observability

none — no error-handling code in scope.

---

## Resume

none

---

## Test Gate Results

- Command: `python -m pytest tests -m "not integration" -q` → **288 passed, 1 deselected** (unchanged from
  master; this batch adds no tests and touches no code). Tier 1's `tests/test_repo_hygiene.py` guards still
  pass 5/5 — relevant because they assert the `.agentcortex/tools/` side of the pair this batch deleted from.

---

## Evidence

- **validate**: stash-clean baseline **92 PASS / 9 WARN / 0 FAIL** → after **92 / 9 / 0**. Only one line
  differs: `governed-write lint: 148 → 145 file(s) scanned`, matching the deleted files. No FAIL, no WARN delta.
- **tests**: 288 passed / 1 deselected; `tests/test_repo_hygiene.py` 5/5.
- **tools/ deletion safe**: `.agentcortex/tools/` counterparts all present; `check_text_integrity.py` still
  runs clean; no reference in `.github/workflows/`, Dockerfile, docker-compose, entrypoint, quickstart,
  start, or daily_run scripts.
- **CONTRIBUTING**: root now titled "Contributing to Smart Stock Selector"; both outbound links verified to
  resolve from repo root (`docs/project_meta/TESTING.md`, `docs/project_meta/CODE_STYLE.md`). Normalized
  CRLF→LF before commit so text-integrity does not see mixed-eol (Tier 1 lesson).
- **backlog**: all three historical snapshots now `status: archived`; `_product-backlog.md` remains `living`.
- Scoping evidence gathered pre-classification:
  - `deploy.sh:739` `_runtime_tools` lists `check_text_integrity.py/.ps1`, `text_integrity_baseline.txt`,
    `sync_skills.sh` — all under `.agentcortex/tools/`; `git grep` finds no reference to `tools/*`
  - `validate.sh:40-41`, `validate.ps1:232-233` → text-integrity tools resolve to `.agentcortex/tools/`
  - root `CONTRIBUTING.md:1` = "# Contributing to AgentCortex"; `docs/project_meta/CONTRIBUTING.md:1` =
    "# Contributing to Smart Stock Selector"
  - `_product-backlog-honesty-first-2026-06-13.md` → `status: living`; the other two snapshots →
    `status: archived`
