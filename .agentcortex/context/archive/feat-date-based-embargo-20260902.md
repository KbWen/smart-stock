# Work Log: feat/date-based-embargo

## Header

- Branch: `feat/date-based-embargo`
- Classification: `feature`
- Classified by: `claude-opus-5`
- Frozen: `2026-09-02`
- Created Date: `2026-09-02`
- Owner: `KbWen`
- Guardrails Mode: `Full`
- Current Phase: `ship`
- Diff Base SHA: `8fc0128` <!-- immutable: set once on first /implement -->
- Checkpoint SHA: `none` <!-- mutable: refresh each commit -->
- Recommended Skills: `verification-before-completion, red-team-adversarial`
- Primary Domain Snapshot: `ml`
- SSoT Sequence: `5`

---

## Session Info

> Written by /bootstrap. Update on each new session.

- Agent: `claude-opus-5`
- Session: `2026-09-02`
- Platform: `claude-code`
- Guardrails loaded: `.agent/rules/engineering_guardrails.md` §10, `.agent/workflows/shared-contracts.md`
- Files Read: `11` (optional — running count of file reads across this session for token-budget instrumentation; bootstrap may seed `0`, later phases may increment when material).

---

## Task Description

> 1-3 sentences: what is being done and why.

Honest Metrics epic #2. The training embargo was measured in **pooled rows** on a
cross-sectionally stacked panel, so it removed almost no time. Measured directly on the real
92-ticker panel, the old split separated train from test by **0 trading days** — worse than the
audit's ≈0.2-day estimate — while every triple-barrier label looks forward 20 trading days.
Replace it with a date-based embargo drawn from the panel's own calendar. Spec:
`docs/specs/date-based-train-test-embargo.md` (frozen 2026-09-02).

---

## Phase Sequence

> Record each phase entry in order. Update `Current Phase` in the Header on entry.

| Phase | Status | Entered | Notes |
|---|---|---|---|
| bootstrap | done | 2026-09-02 | Spec frozen; `feature` per backlog (>1 module: trainer + eval script + tests) |
| plan | done | 2026-09-02 | Extract the split into a pure `chronological_split()` so the invariant is directly testable |
| implement | done | 2026-09-02 | core/ai/trainer.py, scripts/eval_label_modes.py, tests/test_core/test_embargo.py |
| review | done | 2026-09-02 | Reviewer NOT READY → 1 HIGH closed; tenth-man found a real regression, fixed |
| test | done | 2026-09-02 | 313 passed (was 299); 14 embargo tests, falsification stated precisely |
| handoff | pending | — | — |
| ship | pending | — | — |

---

## Phase Summary

> One paragraph per completed phase. Delta-oriented: what changed, what was decided.
> End this section with the `⚡ ACX` sentinel at least once — `validate.sh` checks for it here so the runtime marker has a persistent audit trail (chat output is ephemeral).

**bootstrap** — Spec generated from `_raw-intake.md` §F1 and frozen. `feature`, not `quick-win`: the change spans `core/ai/trainer.py`, `scripts/eval_label_modes.py` and a new test module, and it alters what every published `oos_metrics` number means.

**plan** — Rather than patching the two `iloc` expressions in place, extract the split into a pure `chronological_split(df_all, pred_days)` returning `(train_mask, test_mask, meta)`. Three reasons: AC2's invariant becomes directly testable instead of inferred from a metric; the trainer and the evidence script share one implementation so they cannot drift; and the AC7 before/after harness can call the real function rather than a copy of it.

**implement** — `chronological_split` picks `cut_date` from the row at the 80% position, then walks back `PRED_DAYS` entries in the panel's **sorted unique dates** to get `embargo_date`. Train is `date < embargo_date`, test is `date >= cut_date`. `cv_gap = PRED_DAYS × max_rows_per_date` over the training split — the **max**, not the mean, because it is the only choice that guarantees the sample-counted `TimeSeriesSplit` gap spans at least `PRED_DAYS` distinct dates on an uneven panel. A new `InsufficientPanelHistory` aborts training with a message naming the shortfall instead of shrinking the embargo. `scripts/eval_label_modes.py` calls the same function and now reports `embargo_days` and `cut_date` in its output.

**test** — 8 new tests, all asserting **distinct dates**, never row counts: a row-count assertion cannot tell a correct embargo from this bug. Reverting `chronological_split` to the row-based logic fails 4 of the 8, and the 4 that still pass are individually explainable (see Evidence) — one of them is the single-ticker case, whose passing *is* the point.

**review** — Independent reviewer + tenth-man pre-mortem dispatched on disjoint briefs, the pattern that caught #1's only real defect.

⚡ ACX

---

## Gate Evidence

> Gate receipts written by each phase. Format: `- Gate: <phase> | Verdict: PASS | Classification: <type> | Timestamp: <ISO>`
> **Critical**: `|` pipe separators are mandatory. Receipts placed inside markdown code fences are silently masked and NOT counted by validate.sh — always write receipts as plain list lines.
> Receipt order-of-appearance is authoritative for phase progression; `Timestamp` is provenance metadata only (validators require it to be present and parseable, but do NOT enforce monotonic/chronological ordering).

- Gate: bootstrap | Verdict: PASS | Classification: feature | Timestamp: 2026-09-02T07:00:00Z
- Gate: plan | Verdict: PASS | Classification: feature | Timestamp: 2026-09-02T07:10:00Z
- Gate: implement | Verdict: PASS | Classification: feature | Timestamp: 2026-09-02T07:40:00Z
- Gate: review | Verdict: PASS | Classification: feature | Timestamp: 2026-09-02T09:00:00Z
- Gate: test | Verdict: PASS | Classification: feature | Timestamp: 2026-09-02T09:20:00Z
- Gate: handoff | Verdict: PASS | Classification: feature | Timestamp: 2026-09-02T09:30:00Z

---

## External References

> Links to specs, ADRs, issues, PRs, or design docs relevant to this task.

| Type | Path / URL | Notes |
|---|---|---|
| Spec | `docs/specs/date-based-train-test-embargo.md` | Frozen 2026-09-02 |
| Spec | `docs/specs/ml-label-oos-evaluation.md` | Its 2026-06-13 table is superseded here (was not OOS) |
| Backlog | `docs/specs/_product-backlog.md` #2 | Honest Metrics epic |
| Source | `docs/specs/_raw-intake.md` §F1 | 3/3 independent auditors |
| ADR | — | No architecture decision — a correctness fix inside the training split |
| PR | — | filled at ship |

---

## Known Risk

> List risks identified during planning or implementation. Include mitigation.

Root Cause: an embargo is a statement about **time**, but it was implemented as row arithmetic.
On a cross-sectional panel one date contributes N rows, so the two are only equivalent when N=1 —
and N=1 is exactly the shape the code was originally written against, so it was correct when
written and silently wrong the moment a second ticker was added.

- **Every stored `oos_metrics` is now known-contaminated.** `models_history.json` and
  `/transparency` still serve numbers computed under the old split. This spec deliberately does
  **not** force a retrain (Constraints), so the staleness persists until someone retrains. It is
  disclosed here and in `ml-label-oos-evaluation.md` rather than silently corrected. Attributing
  metrics correctly is backlog #5.
- **Training can now abort where it previously proceeded.** A panel with fewer than `PRED_DAYS + 2`
  distinct dates raises `InsufficientPanelHistory` and `train_and_save` returns `False`.
  **CORRECTION — an earlier version of this line said "the demo fixture has 485 dates, well clear"
  and that was the wrong check, measured wrong.** 485 is the fixture's raw date count; after
  `prepare_features` drops indicator warm-up and the terminal `PRED_DAYS`, the labeled panel is
  **216 distinct dates** read straight from the CSV, and only ~164 through the
  `load_from_db(days=730)` path the pre-mortem exercised. More importantly the binding constraint
  was never the 22-date floor at all: it was the **CV feasibility cliff at roughly `4 × PRED_DAYS`
  training dates**, which is **independent of ticker count** because `cv_gap` and the row count
  scale together, so `--min-tickers` gave zero protection. The shipped fixture would have crossed
  that cliff as its rolling window slid forward, silently leaving fresh clones unable to train.
  Resolved by degrading the CV diagnostic instead of aborting (see Red Team T2); the 22-date floor
  remains as the genuine guarantee-level abort.
- **~3% fewer training rows** from the max-based CV gap and the wider embargo. Measured on the real
  panel: 59,611 → 57,719 rows. Disclosed as a deliberate `[TRADEOFF]` in the spec.
- **The corrected numbers are worse, and that is the point.** StrongBuy recall 0.744 → 0.629. No
  threshold, feature, label mode or hyper-parameter was touched to soften it.

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

**Verdict: NOT READY** on the first pass, one blocking item. The reviewer independently re-derived
the AC3 guarantee (proof plus 400 fuzzed uneven panels, minimum per-fold gap 29, never below 20),
confirmed the numpy-bool masks select correctly despite duplicate indices from `pd.concat`, and
traced the abort path to confirm no partial artifact, no rotation, no history mutation.

| # | Severity | Finding | Disposition |
|---|---|---|---|
| R1 | **HIGH (blocking)** | AC6 bullet 2 — "the CV gap spans >= PRED_DAYS distinct dates in **every fold**" — had **no test**. `TimeSeriesSplit` was never instantiated in the test module; both CV tests asserted arithmetic on `meta`. The invariant was true but unproven. | **FIXED** — `test_every_cv_fold_is_separated_by_pred_days_of_dates` and `test_every_cv_fold_holds_on_an_uneven_panel` build real folds and assert the calendar gap per fold. |
| R2 | HIGH | My falsification claim was imprecise: reverting **only** the masks fails 2 of 8, not 4. The 4/8 figure required reverting `cv_gap` too. | **CORRECTED** in Evidence — both numbers are now stated, with why. |
| R3 | MEDIUM | A partially dated panel yields `NaT` after concat. Measured: 500 rows silently vanished from **both** splits while `gap_dates` still reported 21; at ~50% NaT it raised an uncaught `TypeError` that `except InsufficientPanelHistory` does not catch. | **FIXED** — explicit NaT guard raising `InsufficientPanelHistory`; test added. |
| R4 | MEDIUM | The abort was invisible to callers. `train_and_save` returned `None` on both success and refusal, and `train_ai.py` then logged "Training pipeline complete" and exited 0 — a scheduled retrain would report success with no model. | **FIXED** — returns `bool`; `train_ai.py` logs an error and exits non-zero; aborts use `logger.error`, not bare `print`. |
| R5 | LOW | A tz-aware `date` column raised `TypeError`, again escaping this module's exception type. | **FIXED** — normalised to UTC-naive; test added. |
| R6 | INFO | The spec and test file were still untracked at review time. | Already committed in `63ed821`. |

---

## Red Team Findings

> Written by /review and /test when adversarial testing runs. HIGH findings do not block but MUST record a risk decision here.

The pre-mortem found the one thing the reviewer's AC-conformance brief structurally could not: a
**real regression** introduced by this change, invisible to every synthetic test because all of them
used 200–400 dates, comfortably above the cliff.

| # | Severity | Finding | Risk decision |
|---|---|---|---|
| T1 | HIGH | `scripts/setup_real_ai.py:66` discarded `train_fn()`'s result and returned `trained: True` unconditionally, then ran the recalc and exited 0. README sells it as **the** one command for real AI, so a user would be told it worked, see AI stay N/A, and have nothing to go on. | **FIXED** — an explicit `False` short-circuits before the recalc and reports `trained: False, reason: train_aborted`; `main()` already maps that to exit 2. Only `False` counts, since the injected test doubles return `None`. |
| T2 | HIGH | **The real abort cliff was ~`4 × PRED_DAYS` distinct TRAINING dates — the CV gap — not the 22 that `InsufficientPanelHistory` guards, and it is INDEPENDENT of ticker count** because `cv_gap` and the row count scale together. My Work Log's safety claim ("demo fixture has 485 dates, well clear") was the wrong check *and* measured wrong. The shipped fixture would have crossed the cliff as its rolling window slid forward, silently leaving fresh clones unable to train. | **FIXED by changing the design, not the threshold.** The CV loop is **diagnostic only** — each fold's classifier is fit, its accuracy printed, then discarded; it never touches the shipped model or `oos_metrics`. So it now degrades (3 folds → 2 → skipped with a warning) while the holdout embargo, the actual guarantee, still aborts when it cannot be honoured. AC4 amended, with a new `[DECISION]`: *degrade diagnostics, never the guarantee*. Test pins the cliff at both 8 and 60 tickers to prove it is about dates. |
| T3 | HIGH | Nothing machine-readable distinguished a contaminated `oos_metrics` from a clean one, so the spec's own "staleness is disclosed" Constraint was unimplemented — `/transparency` renders the number under an unqualified 「樣本外 (OOS)」 label. | **FIXED** — `history_entry` gains an `embargo` block (`days`, `basis`, `cut_date`, `train_dates`, `test_dates`). Entries **lacking** the key are pre-fix by construction, recorded as a `[CONSTRAINT]` so nobody backfills it. Badging the panel is backlog #5; the marker it needs now exists. |
| T4 | MEDIUM | `docs/specs/ai-pipeline-otc-optimization.md:24-25` (**frozen**) mandates the row-based gap, and `docs/DATA_INTEGRITY.md:42-43` names the exact broken expressions. Deferring both to #6 means an auditor grepping for the documented mitigation finds code that no longer exists. | **FIXED with pointers, not rewrites** — a supersession warning on the frozen AC3 (bullets kept verbatim as the record of what was specified) and inline `[SUPERSEDED 2026-09-02 …]` markers on the two `DATA_INTEGRITY.md` rows. The full correction stays #6's job. |
| T5 | MEDIUM | `docs/REPRODUCE.md:73-79` still asserted the contaminated `atr`-better conclusion, and `docs/guides/troubleshooting.md:133-140` documented an error string that no longer exists and prescribed "run a full sync" — adding tickers, the one action that cannot fix a date-coverage abort. | **FIXED** — REPRODUCE.md drops the conclusion and links the supersession; troubleshooting.md gains the real message and the actual fix (backfill a **longer window**, not more tickers). |
| T6 | MEDIUM | Narration: "precision 0.352 → 0.345" understates the move. It is from ~at-prevalence to **below** test-split prevalence (0.3454 vs 0.3512) — no skill to negative skill — and run A's prevalence was not recorded in the diff. Also `core/ai/predictor.py:195` will call the first genuinely clean model `ok`. | **FIXED in the record** — Evidence now states run A's prevalence and the lift explicitly, and the ship note carries the `get_model_health` point: shipping #2 before #5 makes the health check most wrong exactly when the metrics are most honest. Fixing the check itself is #5. |
| T7 | LOW | The cut is taken at a **row** position, so on a panel whose width changes over time the test window's share of *dates* differs from its share of rows, and nothing recorded it. | **FIXED** — `meta` gains `n_train_dates` / `n_test_dates`, with a test that the distortion is visible. Measured on the real panel it runs the *other* way to the hypothesis: 22.4% of dates vs 20.1% of rows, because recent dates are narrower. Worth having the number rather than assuming a direction. |
| T8 | LOW | Mixed/missing `date` frames. | Same fix as R3. |

**Checked and cleared by the pre-mortem** (recorded so #4/#5 need not re-derive): a vanishing class 2
is guarded by the `win_rate_* > 0 else 1` fallbacks; an extra key in RF's `class_weight` is ignored by
sklearn 1.8; all three folds on the real demo panel carry all three classes; duplicate dates per
ticker only widen `max_rows_per_date`, which is the conservative direction; and **no CI job trains**,
so CI neither catches nor breaks on any of this.

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

- **State**: implemented, tested and reviewed; ready to ship.
- **Completed**: date-based embargo in `core/ai/trainer.py` via a new pure `chronological_split()`;
  the same function wired into `scripts/eval_label_modes.py`; 8 date-invariant tests; a controlled
  before/after measurement; `ml-label-oos-evaluation.md` corrected with a supersession warning.
- **Next**: backlog #6 (docs-vs-reality) is now unblocked — it depends on #1 and #2, both landed. It
  must correct `docs/DATA_INTEGRITY.md:42` (which presents the *broken* embargo as the mitigation for
  chronological leakage), `:51` (survivorship), `:53` (outcome peeking, now fixed by #1), `:66-70`
  (the circular "consistent profit factors validate the lack of look-ahead" claim), `README.md:237`
  (「完全杜絕」), `docs/project_meta/whitepaper.md:89` (`auto_adjust` as a system-wide property), and
  the `risk_level` naming plus its tooltip.
- **Context**: the epic honesty guard forbids compensating for worse numbers. #2's corrected figures
  are worse for StrongBuy, as expected.

### Read Map

- `docs/specs/date-based-train-test-embargo.md` — this feature's frozen spec.
- `docs/specs/_product-backlog.md` — Honest Metrics inventory, sequencing, and the deferrals #1 and
  #2 pushed onto #3 and #4.
- `docs/specs/_raw-intake.md` — the three audit reports; **keep it until all six specs exist**.
- `core/ai/trainer.py::chronological_split` — the split, its `meta`, and `InsufficientPanelHistory`.
- `tests/test_core/test_embargo.py` — the date-invariant contract any future splitter must satisfy.

### Skip List

- Do **not** re-derive the defect: it is measured, not estimated. The old embargo was **0 trading
  days** on the real panel, recorded in `## Evidence`.
- Do **not** re-open atr-vs-fixed. On lift over prevalence the ranking inverts, but that decision
  belongs to backlog #5 and is deliberately untouched here.
- Do **not** force a retrain. The shipped model's `oos_metrics` stay stale-and-disclosed until
  someone retrains; correcting attribution is #5.
- Do **not** add uniqueness/overlap sample weighting — real, but a separate modelling change.

### Context Snapshot

`storage.db` holds 92 tickers / ~99k price rows spanning 2021-11-26 → 2026-07-24, which yields a
74,539-row labeled panel over 859 distinct dates under `LABEL_MODE=atr`. That is ~5% of the ~1,800
listed+OTC universe and large/liquid-cap biased, so every OOS number in this epic is indicative, not
a full-universe validation. `models_history.json` holds a single entry whose `profit_factor` is
`None` and whose `oos_metrics` were computed under the **old contaminated split**.

### Backlog Status

#1 Shipped (PR #64) · **#2 this branch** · #3 Pending (carries two #1 deferrals) · #4 Pending,
**raised to P0** by #1's review · #5 Pending, now carrying the measured below-prevalence precision
finding from #2 · #6 Pending, unblocked by #1 + #2.

---

## Test Gate Results

> Test-phase gate outcome for `feature`/`architecture-change` logs (required at handoff/ship once an implement receipt exists; ref: `engineering_guardrails.md §12.2`). Record pass/fail counts + the test command. Leave `none` until `/test` runs.

`python -m pytest -q` → **313 passed / 0 failed** (master baseline: 299). 14 tests in the new
`tests/test_core/test_embargo.py` (8 initially, 6 added after review), every assertion about
distinct dates rather than row counts.
Falsification detail — including why 4 of the 8 still pass under the reverted implementation — is in
`## Evidence`.

---

## Evidence

> Reproducible evidence for completed phases. Commands, outputs, versions. "It should work" is NOT evidence.
> **Terse format** (Ref: `engineering_guardrails.md` §5.2b Evidence Truncation Rule): success ≤ 3 lines per claim, failure ≤ 10 lines per claim with the most diagnostic context (root error + bottom of stack), strip passing-test noise. Multiple bullet entries preferred over one long paste.

**The defect, measured rather than assumed.** The audit estimated the old embargo at ≈0.2 trading
days. Measured directly on the real 92-ticker panel (74,539 labeled rows over 859 distinct dates),
the row-based split separated train from test by **0 trading days** — the two sides shared a
boundary date. Every training row within 20 trading days of the cut had its label outcome resolved
inside the test window.

**Implementation** — `core/ai/trainer.py`:
- `chronological_split(df_all, pred_days, test_fraction=0.2)` → `(train_mask, test_mask, meta)`.
  `cut_date` is the date of the row at the 80% position; `embargo_date` is `pred_days` entries back
  in the panel's **sorted unique dates**; train is `date < embargo_date`, test is `date >= cut_date`.
- `cv_gap = pred_days × max_rows_per_date` over the training split. The **max**, not the mean — the
  only choice that guarantees a sample-counted `TimeSeriesSplit` gap spans ≥ `pred_days` distinct
  dates on an uneven panel.
- `InsufficientPanelHistory` aborts training with a message naming the shortfall. No fallback to a
  smaller embargo, a row-based split, or an unsplit fit.
- `scripts/eval_label_modes.py` calls the same function, so the evidence tool and production cannot
  drift; it now reports `embargo_days` and `cut_date` in its output.

**Tests** — `python -m pytest -q` → **313 passed / 0 failed** (master baseline: 299; +8 initially, +6 more after review). Every
assertion is about **distinct dates**, never row counts, because a row-count assertion cannot
distinguish a correct embargo from this bug.

**Falsification (AC6), reported honestly.** The mutation reverts the **whole** old behaviour — both
the masks and `cv_gap` back to `PRED_DAYS`. **Precision the reviewer rightly demanded**: reverting
only the masks and leaving the scaled `cv_gap` in place fails just **2 of 8**, because the two
original CV tests asserted arithmetic on `meta` rather than fold boundaries. That gap is now closed
by the two post-review fold tests, which instantiate a real `TimeSeriesSplit`. Reverting the full
old behaviour fails **4 of the original 8**:
```
FAILED test_embargo_spans_pred_days_of_trading_days_on_a_wide_panel
FAILED test_cv_gap_is_scaled_to_span_pred_days_of_dates
FAILED test_cv_gap_uses_the_widest_date_so_an_uneven_panel_is_still_covered
FAILED test_embargo_holds_when_tickers_do_not_all_trade_every_day
4 failed, 4 passed
```
The 4 that still pass do so for stated reasons, not weakness:
- `test_old_row_based_embargo_fails_the_same_invariant` exercises the **old** logic directly, so the
  mutation cannot affect it — it is the test that *demonstrates* the defect.
- `test_single_ticker_panel_still_splits_correctly` passes under both, and **that is the point**:
  rows and dates coincide when N=1, which is exactly why the bug survived. Its passing is the
  spec's Domain Decision reproduced as an executable fact.
- `test_too_few_dates_aborts_instead_of_shrinking_the_embargo` and
  `test_panel_without_a_date_column_aborts` cover guards the mutation deliberately preserved.

**AC7 — the measured effect, one process, one panel, one seed, both splits.** Nothing differs
between the two rows except how the split was computed:

| split | embargo (trading days) | n_train | StrongBuy P / R | Buy P / R | accuracy |
|---|---|---|---|---|---|
| row-based (old) | **0** | 59,611 | 0.3516 / 0.7443 | 0.1503 / 0.1272 | 0.3526 |
| date-based (new) | **21** | 57,719 | 0.3454 / **0.6290** | 0.1410 / 0.1345 | 0.3552 |

StrongBuy recall falls **15% relative** — the largest movement, and the expected direction: the
contaminated split was letting the model recall outcomes it had trained on. Precision drops on both
classes. Accuracy ticks up trivially, which is noise on a 51% Hold base rate. Training rows fall
59,611 → 57,719 (−3.2%), the disclosed cost of the wider embargo.

**A finding this evidence surfaces but does NOT act on** — and the pre-mortem was right that the
first draft of this paragraph understated it. Calling the precision move "0.352 → 0.345, slight" is
the wrong frame. With a clean split, StrongBuy precision **0.3454 sits below the test-split
prevalence of 0.3512** — a lift of **0.98×**. The model went from *at* the base rate to *below* it:
no skill to negative skill. Buy is 0.1410 against 0.1385, a lift of 1.02×, which is nothing.
Both runs' test prevalences are now recorded in the harness output so the lift is checkable from the
evidence rather than taken on trust.

**Consequence worth stating in the ship note**: `core/ai/predictor.py:195` marks a model `degraded`
only when `p_buy + r_buy + p_strong + r_strong <= 0`, so it will call this first genuinely clean
model `ok`. Shipping #2 before #5 makes the health check **most wrong exactly when the metrics are
most honest**. Fixing the check is #5's job (F10); the situation is disclosed here rather than
quietly shipped. Recording prevalence and
reporting precision as lift is backlog **#5**; this Work Log records the number so #5 does not have
to rediscover it. No threshold, feature, label mode or hyper-parameter was touched here.

**AC5 — `scripts/eval_label_modes.py` re-run** (`embargo_days: 21`, cut 2026-01-07):
```
fixed: dist 76.1/9.4/14.5  StrongBuy 0.321/0.377  Buy 0.095/0.194  acc 0.511
atr:   dist 53.4/15.6/31.0 StrongBuy 0.365/0.607  Buy 0.131/0.104  acc 0.373
```
`docs/specs/ml-label-oos-evaluation.md` now carries a `> [!WARNING]` marking its 2026-06-13 table as
**not out-of-sample**, keeps that table verbatim as the record of what was believed, and adds a
§Re-measurement with both runs above. It explicitly does **not** re-decide `LABEL_MODE`: on lift
over prevalence the ranking inverts (`fixed` ≈2.2× vs `atr` ≈1.2× on StrongBuy), but that is #5's
call, and this run is not a controlled comparison against the June table because `storage.db` has
also grown since.
