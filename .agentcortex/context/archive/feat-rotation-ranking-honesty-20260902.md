# Work Log: feat/rotation-ranking-honesty

## Header

- Branch: `feat/rotation-ranking-honesty`
- Classification: `feature`
- Classified by: `claude-opus-5`
- Frozen: `2026-09-02`
- Created Date: `2026-09-02`
- Owner: `KbWen`
- Guardrails Mode: `Full`
- Current Phase: `ship`
- Diff Base SHA: `3732d0e` <!-- immutable: set once on first /implement -->
- Checkpoint SHA: `4dd3ff4` <!-- mutable: refresh each commit -->
- Recommended Skills: `verification-before-completion, red-team-adversarial`
- Primary Domain Snapshot: `ml`
- SSoT Sequence: `8`

---

## Session Info

> Written by /bootstrap. Update on each new session.

- Agent: `claude-opus-5`
- Session: `2026-09-02`
- Platform: `claude-code`
- Guardrails loaded: `.agent/rules/engineering_guardrails.md` §10, `.agent/workflows/shared-contracts.md`
- Files Read: `7` (optional — running count of file reads across this session for token-budget instrumentation; bootstrap may seed `0`, later phases may increment when material).

---

## Task Description

> 1-3 sentences: what is being done and why.

Honest Metrics epic #4, the last P0 and the **only** item in this epic whose failure mode is
irreversible: rotation and `prune` `os.remove` `.pkl` files ranked by a profit factor that is not
comparable across the entries it ranks. Before #1 a winning trade was booked at the session high,
which on the same seed and window moved profit factor 0.74 → 0.80 — so a genuinely better old model
could be deleted for having been measured with a different ruler. Spec:
`docs/specs/model-rotation-ranking-honesty.md`.

---

## Phase Sequence

> Record each phase entry in order. Update `Current Phase` in the Header on entry.

| Phase | Status | Entered | Notes |
|---|---|---|---|
| bootstrap | done | 2026-09-02 | Spec frozen; last P0; the only irreversible failure mode in the epic |
| plan | done | 2026-09-02 | One rule: unrankable means PROTECTED, not last |
| implement | done | 2026-09-02 | select_for_deletion + settlement/status markers + benchmark window |
| review | done | 2026-09-02 | Both NOT READY; the protection expired at ~50 entries |
| test | done | 2026-09-02 | 335 passed (was 330); every guard falsified individually |
| handoff | done | 2026-09-02 | Resume written |
| ship | done | 2026-09-02 | PR opened; SSoT updated; log archived |

---

## Phase Summary

> One paragraph per completed phase. Delta-oriented: what changed, what was decided.
> End this section with the `⚡ ACX` sentinel at least once — `validate.sh` checks for it here so the runtime marker has a persistent audit trail (chat output is ephemeral).

**bootstrap** — Left until last because it depends on #1 (which created the incomparability) and because it is the highest-stakes item: everything else in this epic mis-states a number, this one deletes a file. Reading the code surfaced a **fourth** defect the panel had not named: `profit_factor: None` meant *both* "no losing trades" (a flawless run, from `backend/backtest.py`) and "the benchmark raised" (from the trainer), and the sort key ranked both below a model that lost money on every trade.

**plan** — One rule, stated so it can be checked: *an irreversible action requires a comparable measurement.* Unrankable means **protected**, not last — sorting an unknown to the bottom is a silent decision to delete it.

**implement** — `is_rankable` / `select_for_deletion` in `core/ai/common.py`, used by both deletion entry points. `backtest_30d` records `settlement`, `status`, `days_ago`, `holding_days`. `manage_models list` gained a `Settle` column so a human can see which scores are even comparable.

**review** — Both `NOT READY`. **Three findings invalidated parts of what I had built**, including the core one: the protection **expired silently at ~50 entries**. Details below; the most useful outcome of the whole feature.

**test** — 335 passed. Every guard falsified individually by reverting it. A **third** set of tests was found defending the old rule, using a local copy of the deleted sentinel so they passed regardless of production code.

⚡ ACX

---

## Gate Evidence

> Gate receipts written by each phase. Format: `- Gate: <phase> | Verdict: PASS | Classification: <type> | Timestamp: <ISO>`
> **Critical**: `|` pipe separators are mandatory. Receipts placed inside markdown code fences are silently masked and NOT counted by validate.sh — always write receipts as plain list lines.
> Receipt order-of-appearance is authoritative for phase progression; `Timestamp` is provenance metadata only (validators require it to be present and parseable, but do NOT enforce monotonic/chronological ordering).

- Gate: bootstrap | Verdict: PASS | Classification: feature | Timestamp: 2026-09-02T18:00:00Z
- Gate: plan | Verdict: PASS | Classification: feature | Timestamp: 2026-09-02T18:10:00Z
- Gate: implement | Verdict: PASS | Classification: feature | Timestamp: 2026-09-02T19:00:00Z
- Gate: review | Verdict: PASS | Classification: feature | Timestamp: 2026-09-02T20:30:00Z
- Gate: test | Verdict: PASS | Classification: feature | Timestamp: 2026-09-02T20:40:00Z
- Gate: handoff | Verdict: PASS | Classification: feature | Timestamp: 2026-09-02T20:50:00Z
- Gate: ship | Verdict: PASS | Classification: feature | Timestamp: 2026-09-02T21:00:00Z

---

## External References

> Links to specs, ADRs, issues, PRs, or design docs relevant to this task.

| Type | Path / URL | Notes |
|---|---|---|
| Spec | `docs/specs/model-rotation-ranking-honesty.md` | Frozen 2026-09-02; AC5 amended post-review |
| Spec | `docs/specs/backtest-settlement-realism.md` | #1 — created the incomparability this fixes |
| ADR | `docs/adr/ADR-004-model-rotation-sort-key.md` | Annotated: quality-first ranking stands, but only among comparable entries |
| Backlog | `docs/specs/_product-backlog.md` #4 | Honest Metrics epic, last P0 |
| PR | — | filled at ship |

---

## Known Risk

> List risks identified during planning or implementation. Include mitigation.

Root Cause: a persisted metric was treated as a stable ruler. Nothing recorded *how* a profit factor
was measured, so when #1 changed the fill model the stored numbers silently became two incompatible
populations — and the code that ranked them was wired to an `os.remove`.

- **The model store can now grow past `MAX_SAVED_MODELS`.** That is the intended consequence of
  refusing a bad comparison, not a leak. Every pre-2026-09-02 entry and every failed benchmark is
  protected, at ~2.3 MB each. Mitigated by logging it with the manual prune command, and by
  `manage_models list` showing a `Settle` column so a human can see which entries are protected and
  why. Deliberately **not** mitigated by a fallback cap — that would reintroduce
  deletion-on-no-information, which is the defect.
- **`manage_models delete` is now advertised as routine**, which makes its lack of an active-model
  guard a routine footgun: `MODEL_PATH` is a copy, not a symlink, so deleting the active entry
  leaves the running model with no provenance and flips health to
  `metrics_not_for_this_version`. Guarded behind `--force`.
- **The benchmark is in-sample and cannot be made otherwise here.** Recorded as
  `backtest_30d.in_sample: true` rather than claimed away. A real out-of-sample rotation score needs
  an as-of model per window — backlog #3.

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

**Verdict: NOT READY.** The reviewer's Q1 — *can any input delete a file that should have been
protected?* — came back clean, and it verified AC8 holds **by construction**: `rankable ⊆ history`,
so anything the old top-N-of-all kept is necessarily in the new top-N-of-rankable. The new code can
never delete what the old code kept. What it found instead was that two ACs asserted properties the
code did not have.

| # | Severity | Finding | Disposition |
|---|---|---|---|
| R1 | **HIGH** | **AC4's `status` is a lie on four reachable paths.** `'ok' if pf is not None else 'no_losing_trades'` — but `run_time_machine` **returns error dicts rather than raising** at four sites, and those responses carry no `summary` at all. A run where zero picks cleared the threshold was recorded as a flawless run, alongside `win_rate: 0`. **This is D2 verbatim, relocated into the field added to fix D2.** | **FIXED** — status is derived from the result (`bt_result.get('error')` or a missing `profit_factor` → `failed`), and the error text is recorded. Test added. |
| R2 | **HIGH** | **AC5 does not deliver the property its comment asserts.** With `PRED_DAYS=20`, training drops the last 20 rows so the last trained row is `N-21`; the benchmark entry row `N-40` is inside the training set, and its training label window is *identical* to the scored `df_future` slice. Raising `days_ago` moves **deeper** into trained data; no value satisfies the goal under a full-data refit. The test only asserted `days_ago >= PRED_DAYS + holding`, a restatement of the implementation, so it could not catch this. | **FIXED by removing the claim, not weakening it.** Window back to 30 (moving it changed what `win_rate`/`avg_return` mean against older entries, for nothing); entry records `in_sample: true`; AC5 amended with the derivation. The test now asserts the honest property. |
| R3 | MEDIUM | **A shared timestamp defeats protection.** `timestamp` is minute-resolution, so two entries can name one `.pkl`; deleting on the rankable one's behalf removed the protected one's file. | **FIXED** — protected timestamps are subtracted, in a shared helper both the trainer and the test harness call. |
| R4 | MEDIUM | **`KeyError` mid-prune, after files are already gone.** `select_for_deletion` used `.get('version')` so a version-less entry survived selection and died at `cmd_delete(h['version'])` — the old code raised *before* any deletion. | **FIXED** — a version-less entry is unrankable up front. |
| R5 | MEDIUM | **prune's `[PROTECTED]` output crashes on a malformed `backtest_30d`** — newly reachable *because* `is_rankable` was hardened to tolerate it. | **FIXED** — isinstance guard. |
| R6 | MEDIUM | **Three vacuous tests.** `_pf_key` was a **local copy** of the deleted `-1.0` sentinel; three tests sorted with it and asserted "None ranks worst" — the behaviour the module docstring already marked superseded. They passed regardless of production code. | **FIXED** — removed, with the reason left in place of the section. `profit_factor_sort_key` was imported and never used; that import is gone too. |
| R7 | INFO | `is_rankable` accepts `"1.5"` / `Decimal` as "a finite number"; the closing rule in `list` still measured 95 chars against a 124-char header. | Rule width fixed. String/Decimal coercion left: both old and new rank them, so it is not a regression, and rejecting a coercible value would fail toward *deletion* of the entries around it. |

---

## Red Team Findings

> Written by /review and /test when adversarial testing runs. HIGH findings do not block but MUST record a risk decision here.

The pre-mortem found the defect that mattered most — the one that made the entire feature a
no-op after seven weeks.

| # | Severity | Finding | Risk decision |
|---|---|---|---|
| T1 | **HIGH** | **The protection expired at ~50 entries, silently.** `trainer.py` persists only `history[-50:]`, and the deletion loop **globbed every `.pkl` and removed anything not in a keep-set built from that truncated history**. On roughly night 52 of a nightly retrain the oldest protected file falls out of the keep-set and is deleted — no comparability check, no log line. The store *was* bounded, but bounded by the exact unguarded path this spec exists to close, and the run log's "may exceed MAX_SAVED_MODELS — that is deliberate" was true only up to ~51 entries. | **FIXED, and it changed the shape of the fix.** Deletion is now an **allow-list**: only timestamps explicitly selected are removed. A file with no history entry at all can no longer be swept up either. Recorded as a `[CONSTRAINT]` so no future change reintroduces glob-and-keep. |
| T2 | HIGH | `no_losing_trades` asserted for backtests that failed without raising. | Same as R1 — found independently by both reviewers. |
| T3 | HIGH | **The comparability key omitted the window, and `PRED_DAYS` is env-configurable.** A user setting `PRED_DAYS=10` gets entries marked `achievable_fill` with `days_ago=30` ranked against existing `days_ago=40` entries — same marker, different ruler, irreversible delete. `days_ago` was recorded but nothing read it. | **FIXED** — the key is `(settlement, days_ago, holding_days)`; a missing window is unrankable. |
| T4 | MEDIUM | AC5's claim not delivered by the code. | Same as R2. |
| T5 | MEDIUM | **Comparability restored for PF, recreated in its neighbours**: `win_rate` / `avg_return` / `sniper_hit_rate` would have come from a 40-day window with old entries at 30, and `list` prints `WR(bt)` beside a `Settle` column that speaks only for `PF(bt)`. | **RESOLVED by R2's fix** — reverting the window to 30 removes the mismatch entirely. This is why the honest fix was to drop the claim rather than keep the window change. |
| T6 | MEDIUM | **Six documents contradicted the code**: `ml-model-rotation.md`'s checked AC2, ADR-004, `api-security-hardening.md`'s "None-safe" claim (the key now raises on `None`), `troubleshooting.md`'s incorrect "always protects the active model", README/WORKFLOW's "keep top 5", and the prune help string. No CHANGELOG entry. | **ALL FIXED.** AC2 marked superseded with its original text kept verbatim; ADR-004 annotated (its quality-first choice still stands, the application changed); CHANGELOG explains why the store grows. |
| T7 | MEDIUM | **The advertised escape hatch can orphan the active model.** `cmd_delete` had no active guard, and both the rotation log and prune now point users at it. | **FIXED** — refuses the active version without `--force`, with the reason in the message. |
| T8/T9 | LOW | `list` rule width; `prune --keep 0` deletes everything rankable. | Width fixed. `keep 0` is an explicit caller choice and stays; a **negative** keep now raises, because clamping it to 0 would fail toward deletion. |

**Cleared by the pre-mortem**: no third naive ranking path exists — a repo-wide grep finds
`profit_factor` ranking only at these two call sites. `/api/models` serves `backtest_30d` raw but the
frontend reads only backtest-summary fields, and `transparency.py` never touches it.

**Narration check, from the same brief**: the rotation log and prune's `[PROTECTED]` block both frame
growth as the cost of refusing a comparison and name the remedy — which reads correctly. The two
places it could have read as a feature were README/WORKFLOW's surviving "keep top 5", now corrected.

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

- **State**: implemented, reviewed, fixed, tested; ready to ship. **The epic's last P0.**
- **Completed**: comparability-aware deletion shared by both entry points; `settlement` / `status` /
  window markers on `backtest_30d`; allow-list deletion; active-model guard on `cmd_delete`; six
  contradicting documents corrected.
- **Next**: **#3** is all that remains — backtest temporal guard (`trained_at` vs entry date) and
  calendar-aligned entry, carrying two #1 deferrals (gap-up-through-target precedence,
  `best_stock` tie-break). It also now inherits the *only* honest way to make the rotation benchmark
  out-of-sample: an as-of model per window.
- **Context**: once #3's spec exists, every first-round spec is written and `_raw-intake.md` can be
  deleted — that is the condition #2 recorded, not a date.

### Read Map

- `docs/specs/model-rotation-ranking-honesty.md` — the spec, including the amended AC5 and the
  derivation of why no window can be out-of-sample under a full-data refit.
- `core/ai/common.py` — `is_rankable` / `select_for_deletion` / `timestamps_to_delete`. The last one
  exists because the entry→filename mapping is where protection leaks.
- `tests/test_core/test_model_rotation.py` — note the harness calls the real helper. It previously
  reproduced the logic, which is how it stayed green through #1's settlement change.

### Skip List

- Do **not** reintroduce glob-and-keep. Deletion is an allow-list; a `[CONSTRAINT]` says so.
- Do **not** add a fallback cap when the store grows. That reintroduces deletion-on-no-information,
  which is the defect this spec exists to remove.
- Do **not** try to make the rotation benchmark out-of-sample by moving the window. It is provably
  impossible under a full-data refit; the entry records `in_sample: true`.
- Do **not** backfill `settlement` onto old entries — absence is what protects them.

### Context Snapshot

Seven PRs merged this session: #62–#67 plus this one pending. Backend 335 tests, frontend 88.
`models_history.json` holds one entry, `v4.20260601_2031`, with no settlement marker — so
`manage_models list` shows it as `(pre-2026-09-02)` and rotation will never auto-delete it. Model
files are ~2.3 MB each; `daily_run.sh` retrains nightly, so the growth trade-off is real and is
disclosed rather than capped.

### Backlog Status

#1 Shipped (#64) · #2 Shipped (#65) · #5 Shipped (#67) · #6 Shipped (#66) · **#4 this branch** ·
#3 Pending — the only item left.

---

## Test Gate Results

> Test-phase gate outcome for `feature`/`architecture-change` logs (required at handoff/ship once an implement receipt exists; ref: `engineering_guardrails.md §12.2`). Record pass/fail counts + the test command. Leave `none` until `/test` runs.

`python -m pytest -q` → **335 passed / 0 failed** (master baseline: 330). Net +5 after removing
three vacuous tests and adding eight real ones.

---

## Evidence

> Reproducible evidence for completed phases. Commands, outputs, versions. "It should work" is NOT evidence.
> **Terse format** (Ref: `engineering_guardrails.md` §5.2b Evidence Truncation Rule): success ≤ 3 lines per claim, failure ≤ 10 lines per claim with the most diagnostic context (root error + bottom of stack), strip passing-test noise. Multiple bullet entries preferred over one long paste.

**The four defects, each verified in the code before writing the spec.** D1 cross-regime ranking
feeding `os.remove`; D2 `profit_factor: None` meaning both "no losing trades" and "the benchmark
raised", with the sort key putting both below a model that lost money on every trade; D3 the
benchmark scoring a window the model was just fit on. D2 was **not named by the quant panel** — it
surfaced from reading `backend/backtest.py:324` against `core/ai/trainer.py`'s exception handler.

**The rule, implemented once and used twice**: `select_for_deletion` in `core/ai/common.py`, called
by the trainer's rotation and by `manage_models prune`. An entry is rankable only if its
`(settlement, days_ago, holding_days)` matches the current benchmark and its profit factor is a
finite number. Everything else is protected.

**Tests** — `python -m pytest -q` → **335 passed / 0 failed** (baseline 330).

**Falsification, per guard:**
- remove the `settlement` check → 3 tests fail;
- treat `None` as rankable → 3 tests fail;
- remove the window from the key → 1 test fails;
- remove the shared-timestamp subtraction → 1 test fails.

**Live check on the real store**: `python backend/manage_models.py list` now prints the single
existing entry with `Settle = (pre-2026-09-02)` and `PF(bt) = None`, i.e. visibly unrankable and
therefore protected. That is the correct verdict — its profit factor was measured under the old
settlement rule.

**A third set of tests was defending the old rule.** After #1's (two tests pinning session-extreme
settlement) and #4's own `test_rotation_none_pf_models_deleted_first`, the reviewer found three more
using a **local copy** of the deleted `-1.0` sentinel — so they asserted the superseded behaviour and
passed regardless of what production did. Three separate instances in one epic is a pattern, not
bad luck: **a test that duplicates the logic it tests can only ever confirm the duplicate.** The
rotation harness had the same shape and is now wired to the real helper.

**What the reviews changed about the fix itself**, recorded because the first implementation looked
complete and was not:
1. Deletion was glob-and-keep, so the protection **expired at ~50 entries** — the feature would have
   silently reverted after seven weeks of nightly retraining. Now an allow-list.
2. AC5 asserted a property no window can deliver under a full-data refit. Removed, with the
   derivation, rather than reworded into something that sounds delivered.
3. `status` was derived from `pf is None`, which recreated D2 inside the field added to fix D2.
