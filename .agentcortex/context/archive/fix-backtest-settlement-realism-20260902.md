# Work Log: fix/backtest-settlement-realism

## Header

- Branch: `fix/backtest-settlement-realism`
- Classification: `hotfix`
- Classified by: `claude-opus-5`
- Frozen: `2026-09-02`
- Created Date: `2026-09-02`
- Owner: `KbWen`
- Guardrails Mode: `Full`
- Current Phase: `ship`
- Diff Base SHA: `b61367d` <!-- immutable: set once on first /implement -->
- Checkpoint SHA: `none` <!-- mutable: refresh each commit -->
- Recommended Skills: `verification-before-completion, red-team-adversarial`
- Primary Domain Snapshot: `backtest`
- SSoT Sequence: `4`

---

## Session Info

> Written by /bootstrap. Update on each new session.

- Agent: `claude-opus-5`
- Session: `2026-09-02`
- Platform: `claude-code`
- Guardrails loaded: `.agent/rules/engineering_guardrails.md` §10, `.agent/workflows/shared-contracts.md`
- Files Read: `9` (optional — running count of file reads across this session for token-budget instrumentation; bootstrap may seed `0`, later phases may increment when material).

---

## Task Description

> 1-3 sentences: what is being done and why.

Honest Metrics epic #1. `run_time_machine` booked a winning trade at the session **high** and a
losing trade at the session **low** — a one-directional error that inflated `avg_net_return`,
`net_win_rate`, `net_profit_factor` and `sharpe_ratio` on the Backtest page and in Strategy Lab.
Settle both barriers at prices an order could actually have received, with a gap exception filling
at the bar's open. Spec: `docs/specs/backtest-settlement-realism.md` (frozen 2026-09-02).

---

## Phase Sequence

> Record each phase entry in order. Update `Current Phase` in the Header on entry.

| Phase | Status | Entered | Notes |
|---|---|---|---|
| bootstrap | done | 2026-09-02 | Spec frozen at intake; classification `hotfix` (escalated from quick-win) |
| plan | done | 2026-09-02 | Two assignments in the forward-walk loop + 5 new / 2 corrected tests |
| implement | done | 2026-09-02 | backend/backtest.py settlement; tests/test_backend/test_backtest.py |
| review | done | 2026-09-02 | Reviewer `Verdict: PASS`; 4 findings fixed in-branch, 2 deferred with measured reasons |
| test | done | 2026-09-02 | 295 passed (was 290); all 7 settlement tests falsified |
| handoff | n/a | — | `hotfix` is exempt from /handoff (§Delivery Gates) |
| ship | done | 2026-09-02 | PR #64; SSoT updated; Work Log archived |

---

## Phase Summary

> One paragraph per completed phase. Delta-oriented: what changed, what was decided.
> End this section with the `⚡ ACX` sentinel at least once — `validate.sh` checks for it here so the runtime marker has a persistent audit trail (chat output is ephemeral).

**bootstrap** — Spec was frozen during `/spec-intake` ([PR #63](https://github.com/KbWen/smart-stock/pull/63)). Classification `hotfix`, escalated from the `quick-win` the size alone would justify: `quick-win` makes review and test **optional**, and this change rewrites financial numbers users read as achievable. Rationale recorded in `_product-backlog.md §Classification Note`.

**plan** — One edit site: the forward-walk loop in `backend/backtest.py`. Compute `day_open_pct` alongside the existing high/low/close percentages, then replace the two `locked_roi` assignments. Capture a same-seed before/after run first, since AC7 requires the direction of the change to be reported rather than asserted.

**implement** — `day_open_pct` is computed defensively (`row.get('open')` + `pd.notna`), falling back to `None` so a frame without a usable `open` settles exactly at the barrier with no gap adjustment rather than raising. STOP settles at `-stop_loss`, taking the open only when it is *worse*; HIT settles at `target_gain`, taking the open only when it is *better*. Stop-before-target precedence (AC3) and the `max_gain_pct` / `max_drawdown_pct` excursion measures (AC4) are untouched.

**test** — 5 new tests plus 2 pre-existing tests corrected. **The two pre-existing tests were pinning the defect**: `test_run_time_machine_uses_intraday_stop_before_target` asserted `actual_return == -0.1` (the session low) and `test_run_time_machine_custom_strategy_params` asserted `0.08` / `-0.08` (session high / session low). That is why the bug survived — the suite was actively defending it. All 7 were empirically falsified by reverting `backend/backtest.py` and confirming each fails.

**review** — Independent reviewer returned `Verdict: PASS` with all 7 ACs PROVEN, no scope creep, and confirmed the two corrected pre-existing tests were re-derived from their fixtures rather than made-to-pass. Reviewer and tenth-man **independently converged** on the one real defect the change introduced: settlement was no longer bounded by the bar. Three findings fixed in-branch (clamp, silent flattering fallback, an overstated claim in my own spec text); three surfaced as scope decisions because fixing them requires amending a frozen AC or a Constraint.

⚡ ACX

---

## Gate Evidence

> Gate receipts written by each phase. Format: `- Gate: <phase> | Verdict: PASS | Classification: <type> | Timestamp: <ISO>`
> **Critical**: `|` pipe separators are mandatory. Receipts placed inside markdown code fences are silently masked and NOT counted by validate.sh — always write receipts as plain list lines.
> Receipt order-of-appearance is authoritative for phase progression; `Timestamp` is provenance metadata only (validators require it to be present and parseable, but do NOT enforce monotonic/chronological ordering).

- Gate: bootstrap | Verdict: PASS | Classification: hotfix | Timestamp: 2026-09-02T03:00:00Z
- Gate: plan | Verdict: PASS | Classification: hotfix | Timestamp: 2026-09-02T03:10:00Z
- Gate: implement | Verdict: PASS | Classification: hotfix | Timestamp: 2026-09-02T03:30:00Z
- Gate: review | Verdict: PASS | Classification: hotfix | Timestamp: 2026-09-02T05:00:00Z
- Gate: test | Verdict: PASS | Classification: hotfix | Timestamp: 2026-09-02T05:20:00Z
- Gate: ship | Verdict: PASS | Classification: hotfix | Timestamp: 2026-09-02T06:00:00Z

---

## External References

> Links to specs, ADRs, issues, PRs, or design docs relevant to this task.

| Type | Path / URL | Notes |
|---|---|---|
| Spec | `docs/specs/backtest-settlement-realism.md` | Frozen 2026-09-02 |
| Backlog | `docs/specs/_product-backlog.md` #1 | Honest Metrics epic |
| Source | `docs/specs/_raw-intake.md` §F2 | 3/3 independent auditors |
| ADR | — | No architecture decision — a computation fix inside one module |
| PR | https://github.com/KbWen/smart-stock/pull/64 | This fix |
| PR | https://github.com/KbWen/smart-stock/pull/63 | Intake PR that froze the spec |

---

## Known Risk

> List risks identified during planning or implementation. Include mitigation.

Root Cause: the forward-walk loop conflated *"which barrier was touched"* (correctly derived from
the bar's high/low) with *"at what price the position exited"*, and reused the same intraday extreme
for both. Two pre-existing tests then froze that conflation as expected behavior.

- **Published numbers change with no version marker.** Anyone comparing a screenshot from before
  this lands will see different figures for the same query. Accepted deliberately: the old numbers
  were wrong, and the spec's Non-goals exclude UI work. Flagged to the tenth-man to check whether a
  stored/cached figure is now silently mixed with post-fix ones.
- **Model rotation reads this output.** `core/ai/trainer.py` stores `run_time_machine`'s
  `profit_factor` as `backtest_30d`, and `backend/manage_models.py` prunes on it — so rankings
  computed before this fix are not comparable to rankings computed after. This is backlog #4's
  territory; recorded here so #4 does not have to rediscover it.
- **The change is NOT uniformly conservative.** AC2 makes losses smaller. On a stop-heavy sample it
  can move the headline the *flattering* way, contradicting the epic's stated expectation. Mitigated
  by AC7: the direction is measured and reported, never asserted.

---

## Decisions

> Optional (`/decide` §2): record trade-offs/constraints as `### D-N: <title>` with Decision/Reason/Alternatives/Impact lines. At `/ship`, every entry gets one disposition marker: `→ promoted: ADR-<id>` / `→ consolidated: L2 <domain>` / `→ local`.

none

---

## Conflict Resolution

> Record skill conflicts resolved during bootstrap (from skill_conflict_matrix.md). Format: `<skill-A> vs <skill-B>: <chosen approach>`.

none

---

## Skill Notes

> Cache for loaded skills. Written by phase-entry skill loading. Leave as `none` until populated.

none

---

## Drift Log

> Record deviations from the original plan, reclassifications, or unexpected scope changes.

none

---

## Review Feedback

> Written by /review (fix suggestions + NOT READY findings). Read by /implement on resume-after-review — scope is ONLY the UNPROVEN/blocking rows.

**Verdict: PASS** — all 7 ACs PROVEN with file:line evidence; no Non-goal touched; 41 changed lines.

| # | Severity | Finding | Disposition |
|---|---|---|---|
| R1 | MEDIUM | **Settlement is no longer bounded by the bar.** A dirty row with `open < low` settles *below* the session low. The old code was bounded by construction — it *was* the high or low — so introducing the open created a genuinely new unbounded-output path. Reachable: `core/bulk_history.py:74` reads TWSE columns as 5/6/7/8 while `:100` reads TPEX as 4/5/6/2, and `core/data.py:585` does `SELECT *` with no OHLC sanity check. | **FIXED** — clamp `day_open_pct` into `[day_low_pct, day_high_pct]`. Test `test_settlement_never_leaves_the_bar_on_dirty_open` covers both directions and is falsified by removing the clamp. Recorded as a `[CONSTRAINT]` in the spec's Domain Decisions. **Independently raised by the tenth-man as HIGH 2** — two reviewers, disjoint briefs, same defect. |
| R2 | MEDIUM | **Gap-up open through the target on a stop bar books an unachievable loss.** `open=122, high=135, low=80` with `target_gain=0.15`: the stop branch fires first, the open is not `< -0.05`, so it books `STOP` at −5% — but a limit sell at 115 is marketable at the 122 open and fills on the session's first print. | **DEFERRED to backlog #3 on measured grounds**, not asserted ones. The case needs one bar whose open is ≥ `target_gain` above entry while its low is ≤ `-stop_loss` below it — a ≥20% intraday range at the default barriers. Across the **99,287 real bars in `storage.db` only 4 (0.004%)** have a range that wide at all, and that is merely the *necessary* condition; Taiwan's **±10% daily price limit** makes it structurally near-impossible for a limit-abiding security. Not a regression either (the old code booked the session low, which is worse) and it biases conservative. Amending a frozen AC for a 0.004%-ceiling case that errs safe is not a good trade. Recorded as a `[TRADEOFF]` in Domain Decisions and carried on backlog #3. |
| R3 | INFO | `float(raw_open)` introduces a `ZeroDivisionError` path on a zero entry close, where the pre-existing numpy division at `:203` yields `inf`/`nan`. | **FIXED** — added `and entry_price > 0` to the guard. |
| R4 | INFO | The `day_open_pct is None` fallback had no test. | **FIXED** — `test_settlement_falls_back_to_the_barrier_when_open_is_missing`, plus `test_settlement_at_a_bar_that_opens_exactly_on_the_barrier` for the strict-comparison boundary the reviewer noted nothing pinned. |

---

## Red Team Findings

> Written by /review and /test when adversarial testing runs. HIGH findings do not block but MUST record a risk decision here.

Tenth-man pre-mortem. It first established there is exactly **one** persistence surface for these
numbers: `/api/strategies/compare` recomputes live (`backend/routes/strategies.py:214-246`), the
`strategies` table stores params only (`core/data.py:159-167`), and no response cache wraps
`/api/backtest`. The only stored pre-fix figures are in `models_history.json`.

| # | Severity | Finding | Risk decision |
|---|---|---|---|
| T1 | HIGH | **Model rotation `os.remove`s `.pkl` binaries by comparing two incompatible settlement regimes.** `core/ai/trainer.py:472` sorts ALL history by `profit_factor_sort_key` and `:487` deletes everything outside the top 5; `backtest_score` (`:416-421`) carries no settlement marker, so a pre-fix and a post-fix PF are indistinguishable forever. Irreversible, no backup. | **ACCEPTED for this branch, escalated to backlog #4 and raised to P0 there**, whose scope is already "model rotation ranking honesty". Local `models_history.json` holds 1 entry with `profit_factor: None`, so nothing is at risk here; the hazard is for a populated history. Disclosed in the CHANGELOG entry. Fixing it means adding a `settlement` marker to a persisted structure — outside this spec. |
| T2 | HIGH | Unclamped `day_open_pct` (same defect as R1). | **FIXED** — see R1. |
| T3 | HIGH | **The missing-`open` fallback is silent AND directionally flattering.** With no open, the gap branch is skipped, so a stop can never settle worse than `-stop_loss` — the one case where the new model admits a loss beyond the stop is disabled with no log line. On the HIT side the same fallback is conservative, so the failure is one-directional in the *flattering* direction — the exact class of error this spec exists to remove. yfinance returns NaN opens for halted sessions. | **FIXED** — `logger.warning` naming the ticker and bar date whenever a stop settles without a usable open. Chose a log line over a new `summary` field because the spec's Constraints forbid an API-contract change. |
| T4 | MEDIUM | **FIXED as AC8 — and the finding was understated.** **Sharpe now degenerates to a flattering `0.000`.** Settled returns collapse onto two discrete values, so `std == 0` is newly reachable (it was not before, when high/low variance guaranteed spread); `backend/backtest.py:319-320` then returns `0.0`, which `Backtest.tsx:298` renders as "no edge". This is the flattering-sentinel pattern `docs/specs/backtest-metric-label-honesty.md` outlawed. | **FIXED** after the user delegated the scope call back. Research that settled it: **both** frontend surfaces already implement the null contract (`Backtest.tsx:298` renders `!= null ? … : '—'`, `StrategyCompare.tsx:59` returns `'—'` for null/undefined/NaN) and `useStrategies.ts:32` already types it `number \| null` — the UI was written against a contract the backend never honoured. The tenth-man called this newly reachable; it was in fact **already firing at the shipped defaults**, because `std()` of a single pick is NaN and the old guard fabricated `0.0`. Added as AC8 with a narrow amendment to the API-contract Constraint; `docs/API_CONTRACT.md` and the `Backtest.tsx` type updated to stop lying. |
| T5 | MEDIUM | **The closure text overstates what changed**: the spec and backlog claimed the fix removes inflation in `net_win_rate`, which it structurally cannot — a settled HIT is always positive and a settled STOP always negative, so trade signs are invariant. The Work Log's own AC7 table already showed `0.25 → 0.25 unchanged`. | **FIXED** — corrected the spec's opening paragraph and the backlog row, and added an explicit "Win rates are not among them" paragraph. This was the epic's own failure mode appearing in the epic's own prose; catching it is exactly what the tenth-man is for. |
| T6 | MEDIUM | User-visible numbers change with no marker anywhere; `CHANGELOG.md` is maintained and got no entry. | **PARTIALLY FIXED** — added a `[Honest Metrics]` CHANGELOG entry stating plainly that a kept screenshot will no longer match, which metrics move, which do not, and that the measured direction was *flattering* here. The UI footnote is left alone: the spec's Non-goals exclude frontend work. |
| T7 | LOW | `best_stock` (`backend/backtest.py:322` `idxmax`) becomes an arbitrary tie-break now that every no-gap HIT settles at exactly `target_gain`. | **ACCEPTED.** Cosmetic, and any tie-break rule would be equally arbitrary. Noted for #3, which already touches this area. |

---

## Design Reference

> Populated by /plan for UI tasks. If not a UI task, write `none`.
> Format: `Link: <DSoT URL or file path> | Tool: <Stitch | Figma | Pencil | other>`

none

---

## Observability

> Populated by /ship for feature/architecture-change tasks. Document the production error sink used in changed code.
> Format: `Sink: <logger name or API> | Scope: <files> | Verified: <yes/no>`

none

---

## Resume

> Populated by /handoff for feature/architecture-change tasks. Required: `State`, `Completed`, `Next`, `Context` fields; then `### Read Map`, `### Skip List`, `### Context Snapshot`; optionally `### Backlog Status`. validate.sh enforces the three `###` headings. Leave as `none` until /handoff runs.

none

---

## Test Gate Results

> Test-phase gate outcome for `feature`/`architecture-change` logs (required at handoff/ship once an implement receipt exists; ref: `engineering_guardrails.md §12.2`). Record pass/fail counts + the test command. Leave `none` until `/test` runs.

`python -m pytest -q` → **298 passed / 0 failed** (master baseline: 290). +8 tests: 5 settlement
behaviours, 3 hardening cases added after review (dirty-open clamp, missing-open fallback,
open-exactly-on-barrier). Plus 2 pre-existing tests corrected from the buggy values they were pinning.

---

## Evidence

> Reproducible evidence for completed phases. Commands, outputs, versions. "It should work" is NOT evidence.
> **Terse format** (Ref: `engineering_guardrails.md` §5.2b Evidence Truncation Rule): success ≤ 3 lines per claim, failure ≤ 10 lines per claim with the most diagnostic context (root error + bottom of stack), strip passing-test noise. Multiple bullet entries preferred over one long paste.

**Implementation** — `backend/backtest.py` forward-walk loop:
- STOP branch: `locked_roi = -stop_loss`, then `if day_open_pct is not None and day_open_pct < locked_roi: locked_roi = day_open_pct`.
- HIT branch: `locked_roi = target_gain`, then `if day_open_pct is not None and day_open_pct > locked_roi: locked_roi = day_open_pct`.
- `day_open_pct` is `None` when `open` is absent or NaN → settles exactly at the barrier, no raise.

**Tests** — `python -m pytest tests/test_backend/test_backtest.py -q` → **18 passed**. Full suite
`python -m pytest -q` → **295 passed / 0 failed** (was 290 on master; +5 new tests).

**Falsification (AC6)** — reverted `backend/backtest.py` to master, kept the tests, re-ran:
```
7 failed, 11 passed
FAILED test_run_time_machine_uses_intraday_stop_before_target
FAILED test_run_time_machine_custom_strategy_params
FAILED test_hit_settles_at_target_not_session_high
FAILED test_hit_gap_open_above_target_settles_at_open
FAILED test_stop_settles_at_stop_not_session_low
FAILED test_stop_gap_open_below_stop_settles_at_open
FAILED test_net_of_cost_arithmetic_applies_to_settled_roi
```
Every settlement test fails without the fix — none is vacuous. The first two are the pre-existing
tests that had been asserting the buggy values.

**Falsification of the three post-review tests, reported honestly:**
- `test_settlement_never_leaves_the_bar_on_dirty_open` — **falsified**. Replacing the clamp line with
  a `pass` makes it fail; the other 20 still pass, so it isolates exactly the clamp.
- `test_settlement_at_a_bar_that_opens_exactly_on_the_barrier` — **falsified** by the same revert as
  the other settlement tests (it asserts `0.15` / `-0.05`, not the session extremes).
- `test_settlement_falls_back_to_the_barrier_when_open_is_missing` — **NOT falsifiable by a simple
  mutation, and this is stated rather than glossed.** Removing the `pd.notna(raw_open)` guard leaves
  all 21 tests passing, because NaN comparisons already fail closed: `nan < -0.05` is `False`, and
  `min`/`max` short-circuit to the non-NaN operand. It is therefore a **regression guard** — it
  proves settlement does not raise and does use the barrier value — not proof that the guard itself
  is load-bearing today. It becomes load-bearing the moment someone restructures the comparison into
  a form where NaN does not fail closed, which is precisely when it will earn its keep.

**AC7 — same-seed before/after on the real 92-ticker `storage.db`.** `run_time_machine` seeds
`random(42)` internally, so the candidate sample is identical across runs.

*Shipped defaults (`BACKTEST_AI_THRESHOLD=0.35`), `days_ago` 30 and 60*: **every settlement metric unchanged.**
Both runs admit exactly 1 candidate and neither touches a barrier (0 HIT / 0 STOP), so `locked_roi`
never leaves the `PENDING` path. Honest reading: the shipped threshold plus the honestly-weak model
produce too small a sample to show anything.

**AC8 changed exactly one thing at the shipped defaults, and it is the most telling result in this
Work Log.** Both n=1 runs previously reported `sharpe_ratio: 0.0`; they now report `None` → the UI
renders `—`. With a single pick, `pandas.Series.std()` is NaN, so the old `if std_net > 0 else 0.0`
fabricated a zero. That means **at the real product settings, the only number this entire PR moves
is a Sharpe that was invented out of nothing.** The settlement fix itself is invisible here purely
because the honestly-weak model admits one candidate that touches no barrier — which is itself an
honest thing to be able to say.

*Diagnostic (`BACKTEST_AI_THRESHOLD=0.0`, `days_ago=90`)* — threshold relaxed **only** to obtain a
sample that touches the barriers; **no shipped default was changed**. 16 picks, 3 HIT / 11 STOP:

| metric | before | after |
|---|---|---|
| avg_return | −0.012252 | −0.007190 |
| avg_net_return | −0.019987 | −0.014965 |
| profit_factor | 0.74 | 0.80 |
| net_profit_factor | 0.61 | 0.64 |
| sharpe_ratio | −0.207 | −0.187 |
| best_return | 0.196911 | 0.155727 |
| win_rate / net_win_rate | 0.25 | 0.25 (unchanged) |
| worst_drawdown | −9.21 | −9.21 (unchanged — MAE, per AC4) |

AC8 (nullable Sharpe) changes nothing in this diagnostic run: 16 picks with mixed HIT/STOP/PENDING
outcomes have real dispersion, so `sharpe_ratio` stays a number. Re-running the whole evidence
script after AC8 confirmed byte-identical metrics here.

Per-pick, every branch behaved exactly as specified:
```
2105  STOP  -0.0809 -> -0.0500   1605  HIT   0.1969 -> 0.1557 (gap open above target)
1303  STOP  -0.0921 -> -0.0500   4958  HIT   0.1584 -> 0.1500 (no gap, exact target)
2308  STOP  -0.0794 -> -0.0595   6415  HIT   0.1774 -> 0.1509 (gap open above target)
      ^ gap open BELOW the stop — the one case a loss legitimately exceeds -5%
4938/2884 PENDING  unchanged
```
All 11 STOPs moved up to exactly −0.0500 except `2308`, which settles at −0.0595 because its bar
gapped open through the stop. All 3 HITs moved down. All PENDINGs unchanged.

**Honest reading of the direction (AC7).** The headline moved the **flattering** way here, which is
the opposite of the epic's stated expectation. That is not a problem with the fix — it is what
removing a *one-directional* error looks like on a **stop-heavy** sample: correcting 11 over-punished
losses outweighs correcting 3 over-credited wins. On a hit-heavy sample the sign would flip. The
number to trust is not the direction but the per-pick table above: every exit now settles at a price
an order could have received. **No threshold, default, or metric definition was adjusted.**
