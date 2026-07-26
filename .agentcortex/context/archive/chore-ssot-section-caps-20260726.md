# Work Log: chore/ssot-section-caps

## Header

- Branch: `chore/ssot-section-caps`
- Classification: `quick-win`
- Classified by: `claude-opus-5`
- Frozen: `true`
- Created Date: `2026-07-26`
- Owner: `KbWen`
- Guardrails Mode: `Quick`
- Current Phase: `ship`
- Diff Base SHA: `ea05663`
- Checkpoint SHA: `pending`
- Recommended Skills: `verification-before-completion (auto), karpathy-principles (auto)`
- Primary Domain Snapshot: `none`
- SSoT Sequence: `3`

---

## Session Info

- Agent: `claude-opus-5` · Session: `2026-07-26 16:00 UTC` · Platform: `claude-code`
- Guardrails loaded: AGENTS.md §Core Directives, state_machine.md (Quick mode)
- Override / Downstream-Capabilities / private: absent
- Read receipt: SSoT known this session · Work Log created · Spec Scope: none

---

## Task Description

Bring the two `current_state.md` sections back under their configured caps. Both were already over the
limit before this session began and were deliberately left alone across PRs #56/#57/#58 rather than
folded into unrelated batches.

1. **Ship History** 23 entries vs cap 10 (`.agent/config.yaml: ship_history_max_entries`) → rotate the
   oldest 13 into `.agentcortex/context/archive/ship-history-2026.md` per `ship.md §State Update`.
2. **Spec Index** 41 counted entries vs cap 30 (`spec_index_max_entries`) → collapse the oldest 11 into a
   `## Spec Index Archive` section at the bottom of `current_state.md` per `ship.md:184`.

Pure relocation. No entry is edited, reordered within its group, or deleted.

---

## Phase Sequence

| Phase | Status | Entered | Notes |
|---|---|---|---|
| bootstrap | done | 2026-07-26 | `quick-win` — 2 files, relocation only |
| plan | done | 2026-07-26 | boundaries computed from the validators' own counting rules |
| implement | done | 2026-07-26 | 13 ship + 11 spec entries relocated |
| review | optional | — | quick-win exempt (§10.4) |
| test | optional | — | quick-win exempt (§10.4) |
| ship | done | 2026-07-26 | — |

---

## Phase Summary

- bootstrap/plan: classified `quick-win`. The counting rule matters: `check_ssot_caps.py:86-105` counts
  every indented bullet under `- **Spec Index**`, which includes the trailing "When reading specs"
  guidance line — hence 41 counted for 40 real entries, and hence 11 (not 10) entries to move.
- implement/ship: 13 ship entries + 11 spec entries relocated. `check_ssot_caps.py` now reports
  "ssot caps OK — ship history 10/10, spec index 30/30". Zero content lost, verified by set-difference.

⚡ ACX

---

## Gate Evidence

- Gate: bootstrap | Verdict: PASS | Classification: quick-win | Timestamp: 2026-07-26T16:00:00Z
- Gate: plan | Verdict: PASS | Classification: quick-win | Timestamp: 2026-07-26T16:05:00Z
- Gate: implement | Verdict: PASS | Classification: quick-win | Timestamp: 2026-07-26T16:15:00Z
- Gate: ship | Verdict: PASS | Classification: quick-win | Timestamp: 2026-07-26T16:20:00Z

---

## External References

| Type | Path | Notes |
|---|---|---|
| Rule | `.agent/workflows/ship.md:184` + §State Update | defines both rotation targets |
| Rule | `.agent/config.yaml:146,152` | `spec_index_max_entries: 30`, `ship_history_max_entries: 10` |

---

## Known Risk

- **R1 — losing a history entry would be unrecoverable from the SSoT alone.** Mitigated by a
  set-difference check across both files before and after: ship entries 23 → 39 across
  `current_state.md` + archive with `lost=[]`; spec entries 40 → 40 with `lost=[]`.
- **R2 — breaking newest-first ordering.** The 13 moved ship entries were inserted as a contiguous block
  immediately after the archive's header, so the archive descends 2026-06-20 → 2026-06-01 → 2026-03-18
  continuously. Verified by reading the boundary.
- **Rollback**: single commit; `git revert` restores both files exactly.

---

## Decisions

none

---

## Conflict Resolution

none

---

## Skill Notes

- **karpathy-principles** §3: relocation only — no entry text was rewritten, including ones with
  awkward wording, because that would be an unrequested edit to historical records.

---

## Drift Log

- Skip Attempt: NO · Gate Fail Reason: N/A · Token Leak: NO
- **Direct SSoT write, not via `guard_context_write.py`.** Here `current_state.md` is the *deliverable*
  being edited, not a side-effect state update at the end of an unrelated task, and the edit is a
  whole-file restructure rather than an anchored insert. Integrity was established by the loss-check
  above instead of by optimistic locking. Recorded per AGENTS.md §Write Isolation.
- These two cap violations pre-date this session. They were deliberately NOT folded into PRs #56/#57/#58
  — an SSoT rewrite inside a hygiene batch would have been exactly the unscoped change those batches
  refused elsewhere.

---

## Review Feedback

none

---

## Red Team Findings

n/a — `red-team-adversarial` does not trigger for `quick-win`.

---

## Design Reference

none

---

## Observability

none

---

## Resume

none

---

## Test Gate Results

- `python -m pytest tests -m "not integration" -q` → 289 passed, 1 deselected (unchanged; no code touched).

---

## Evidence

- `check_ssot_caps.py --root .` → **"ssot caps OK — ship history 10/10, spec index 30/30"** (was
  23/10 and 41/30).
- Loss check: ship entries before=23, after across `current_state.md`+archive=39, `lost=[]`; spec entries
  before=40, after=40, `lost=[]`.
- Live Ship History = 10 entries, ending at `Ship-feature-docker-self-seed-2026-06-20`; archive = 29
  entries, newest-first, continuous across the join.
- `validate.sh` → 92 PASS / 9 WARN / 0 FAIL; `[WARN]`-level lines byte-identical to the pre-change run,
  with the two indented cap `WARN:` sub-lines now absent.
- Both files written LF-only.
