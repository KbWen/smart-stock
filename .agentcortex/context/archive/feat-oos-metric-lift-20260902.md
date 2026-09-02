# Work Log: feat/oos-metric-lift

## Header

- Branch: `feat/oos-metric-lift`
- Classification: `feature`
- Classified by: `claude-opus-5`
- Frozen: `2026-09-02`
- Created Date: `2026-09-02`
- Owner: `KbWen`
- Guardrails Mode: `Full`
- Current Phase: `ship`
- Diff Base SHA: `ad94f48` <!-- immutable: set once on first /implement -->
- Checkpoint SHA: `ec4fe95` <!-- mutable: refresh each commit -->
- Recommended Skills: `verification-before-completion, red-team-adversarial`
- Primary Domain Snapshot: `ml`
- SSoT Sequence: `7`

---

## Session Info

> Written by /bootstrap. Update on each new session.

- Agent: `claude-opus-5`
- Session: `2026-09-02`
- Platform: `claude-code`
- Guardrails loaded: `.agent/rules/engineering_guardrails.md` §10, `.agent/workflows/shared-contracts.md`
- Files Read: `8` (optional — running count of file reads across this session for token-budget instrumentation; bootstrap may seed `0`, later phases may increment when material).

---

## Task Description

> 1-3 sentences: what is being done and why.

Honest Metrics epic #5, escalated to P0 by #2's measurement. Three defects that together let the
product present a model as usable when the numbers say it is not: metrics attributed to a model
that never ships (F8), precision recorded with no base rate while the stored distribution is the
**train** split (F9), and `get_model_health` returning `ok` for anything non-zero, so a model at or
below the base rate passed as healthy (F10). Spec: `docs/specs/oos-metric-attribution-and-lift.md`.

---

## Phase Sequence

> Record each phase entry in order. Update `Current Phase` in the Header on entry.

| Phase | Status | Entered | Notes |
|---|---|---|---|
| bootstrap | done | 2026-09-02 | Spec frozen; `feature` (trainer + predictor + route + frontend + tests) |
| plan | done | 2026-09-02 | Additive keys only; absence of a key stays the contamination marker |
| implement | done | 2026-09-02 | trainer lift/prevalence, predictor 4 degrade rules, payload, LiftRow |
| review | done | 2026-09-02 | Both NOT READY; NaN reached `ok`, chip asserted the wrong cause |
| test | done | 2026-09-02 | 330 passed (was 320); frontend 88; each new rule falsified |
| handoff | done | 2026-09-02 | Resume written |
| ship | done | 2026-09-02 | PR opened; SSoT updated; log archived |

---

## Phase Summary

> One paragraph per completed phase. Delta-oriented: what changed, what was decided.
> End this section with the `⚡ ACX` sentinel at least once — `validate.sh` checks for it here so the runtime marker has a persistent audit trail (chat output is ephemeral).

**bootstrap** — Chosen ahead of #3 and #4 because it is the only one of the three that is *actively* misleading a user right now: the other two are latent hazards, this one is a claim on screen. `feature` — trainer, predictor, route, frontend, tests.

**plan** — Additive keys only. The persisted structure gains `test_class_distribution`, `oos_metrics.lift_*` and `oos_metrics_scope`; nothing is renamed or backfilled, because #2 established that **absence of a key is the contamination marker** and writing values into old entries would destroy the only signal that their metrics are untrustworthy. `class_distribution` deliberately keeps its ambiguous name — renaming would blank a real number in the panel for every existing entry, and the ambiguity is a *display* problem, resolved where it actually misled someone.

**implement** — `class_prevalence` and `lift_over_prevalence` extracted as pure functions so the contract is directly testable. `get_model_health` grew from two verdicts to six, each with its own machine `reason` and its own zh-TW message.

**review** — Both reviewers returned `NOT READY`, and the two highest findings were things I had not considered: **NaN and inf reached `ok`**, and **the chip asserted one cause for every degraded state**. Twenty findings, all fixed; dispositions below.

**test** — 330 backend / 88 frontend. Each new rule falsified by reverting it. Two rounds of my own test theatre caught and replaced (see Evidence).

⚡ ACX

---

## Gate Evidence

> Gate receipts written by each phase. Format: `- Gate: <phase> | Verdict: PASS | Classification: <type> | Timestamp: <ISO>`
> **Critical**: `|` pipe separators are mandatory. Receipts placed inside markdown code fences are silently masked and NOT counted by validate.sh — always write receipts as plain list lines.
> Receipt order-of-appearance is authoritative for phase progression; `Timestamp` is provenance metadata only (validators require it to be present and parseable, but do NOT enforce monotonic/chronological ordering).

- Gate: bootstrap | Verdict: PASS | Classification: feature | Timestamp: 2026-09-02T15:00:00Z
- Gate: plan | Verdict: PASS | Classification: feature | Timestamp: 2026-09-02T15:10:00Z
- Gate: implement | Verdict: PASS | Classification: feature | Timestamp: 2026-09-02T15:50:00Z
- Gate: review | Verdict: PASS | Classification: feature | Timestamp: 2026-09-02T17:00:00Z
- Gate: test | Verdict: PASS | Classification: feature | Timestamp: 2026-09-02T17:10:00Z
- Gate: handoff | Verdict: PASS | Classification: feature | Timestamp: 2026-09-02T17:20:00Z
- Gate: ship | Verdict: PASS | Classification: feature | Timestamp: 2026-09-02T17:30:00Z

---

## External References

> Links to specs, ADRs, issues, PRs, or design docs relevant to this task.

| Type | Path / URL | Notes |
|---|---|---|
| Spec | `docs/specs/oos-metric-attribution-and-lift.md` | Frozen 2026-09-02 |
| Spec | `docs/specs/date-based-train-test-embargo.md` | #2 — supplies the `embargo` marker this reads |
| Spec | `docs/specs/ui-model-state-disclosure.md` | Owns `get_model_health` + the banner |
| Backlog | `docs/specs/_product-backlog.md` #5 | Honest Metrics epic |
| ADR | — | No architecture decision — additive keys plus a verdict rule |
| PR | — | filled at ship |

---

## Known Risk

> List risks identified during planning or implementation. Include mitigation.

Root Cause: `get_model_health` was written to catch a *degenerate* model — one with literal zeros —
and that was the only failure mode anyone had seen. It never asked the question that actually
matters for an imbalanced ranking task, which is whether the model beats its own base rate, because
the base rate was never recorded.

- **Every existing install flips to `degraded` on upgrade.** No history entry written before
  2026-09-02 carries the `embargo` key, so all of them hit `contaminated_metrics` immediately. That
  is correct — those metrics were never out-of-sample — but it is a jarring change with no cause
  visible in the app. Mitigated by a CHANGELOG section that leads with it and says plainly that it
  is a measurement change, not a model change.
- **A permanent banner stops being a disclosure.** The tenth-man's point: on this project's own
  data the lift is 0.98, so realistically no model clears `ok`, and an orange banner on three pages
  forever trains users to ignore it. Partly mitigated by giving each cause its own chip text so the
  banner still carries information; not fully solved, and recorded as such.
- **This change makes the product say "no edge" more often.** That is the intended direction and
  must not be narrated as a model improvement. The epic's honesty guard forbids tuning the
  threshold; 1.0 is the base rate by definition, not a tunable.

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

**Verdict: NOT READY.** The reviewer ran an independent probe script against the live
`get_model_health` rather than reasoning about it, which is how the NaN finding surfaced.

| # | Severity | Finding | Disposition |
|---|---|---|---|
| R1 | **HIGH** | **NaN and inf reach `ok`.** `json.loads` accepts bare `NaN`/`Infinity`, and `nan <= 1.0` is `False` while `nan is None` is also `False` — so a non-finite lift fell through **both** new guards and read as a healthy model. Verified reachable from a hand-edited or externally written history file. Violates the spec's `[CONSTRAINT]` verbatim. | **FIXED** — coerce once, require `math.isfinite`. Probed all of `NaN`/`inf`/`"abc"`/negatives afterwards. |
| R2 | **HIGH** | **The version-mismatch fallback reaches `ok` on another model's data.** `entry = history[-1]` when the active version is absent. Tolerable when the output was a vague status; not now that it is a specific public figure ("lift 0.98×") attributed to a version that never earned it. `backend/routes/transparency.py` mirrored the fallback, so the panel rendered another model's metrics, distributions and embargo under the active version — **recreating the F8 mis-attribution one layer up**. | **FIXED** — `metrics_not_for_this_version`, and the transparency route no longer borrows an entry at all. |
| R3 | MEDIUM | **Check order inverted against AC4.** Zero-power ran before the embargo check, so today's entry (both true) was told 「辨識力不足」 rather than 「並非真正的樣本外結果」. The spec explicitly says these are different facts to act on. | **FIXED** — checks now run strictly worst-first, with a comment stating that the order *is* the semantics. |
| R4 | MEDIUM | **The train/test test did not pin the call site.** It proved the helper discriminates, but rewriting `class_prevalence(y_test)` to `y_train_full` broke nothing. AC6 bullet 1 asked for exactly that proof. | **FIXED** — a real small `train_and_save` run into a temp `MODEL_PATH`, reading back `models_history.json`. Falsified by pointing the call site at the train split. |
| R5 | MEDIUM | **The frontend Transparency test was stale and UI coverage was zero.** The mock still supplied `class_distribution`, a key the component no longer reads, so the distribution block rendered nothing and the test passed anyway. | **FIXED** — fixture matches the real payload; asserts both labelled distributions, both lifts, the no-edge marking and the attribution line, plus a second test for the wrong-cause chip. |
| R6 | MEDIUM | **Docs stale after the rename.** `transparency-panel.md` documented `class_distribution`; `API_CONTRACT.md` never documented `/api/transparency` at all, so the rename was an undocumented breaking change. | **FIXED** — both, including the `reason` token vocabulary and how to read a lift. |
| R7 | MEDIUM | **AC7 was unrecorded** in the Work Log at review time. | **FIXED** — measured verdict before/after is in Evidence. |
| R8 | INFO | `lift_buy` never affects health, so the panel can show a red 買進提升倍數 beside an `ok` chip. | **ACCEPTED, deliberate.** The product acts on StrongBuy; gating health on Buy would disclose a weakness in a class no screen uses. The panel showing it red is the honest surface for it. |
| R9 | INFO | `oos_metrics_scope` was plumbed to the payload and the TS type but never read — the 80/20 prose was unconditional. | **FIXED** — the prose is now gated on the field, so an entry that does not record its scope does not get the claim. |
| R10 | INFO | Unused `import pytest`; prevalence persisted at 3 dp while lift divides the unrounded value. | Import removed. The rounding difference is deliberate and left: the stored distribution is for display, the lift is computed from full precision. |

---

## Red Team Findings

> Written by /review and /test when adversarial testing runs. HIGH findings do not block but MUST record a risk decision here.

| # | Severity | Finding | Risk decision |
|---|---|---|---|
| T1 | HIGH | **A permanent banner is not a disclosure.** On this project's measured data the lift is 0.98, so realistically no model reaches `ok`; an orange alert would sit on Dashboard, Backtest and Indicators forever and users habituate — costing the project the exact surface it uses for real disclosure. Separately, every existing install flips `ok`→`degraded` on upgrade with nothing explaining it. | **PARTLY FIXED, and the remainder is recorded rather than papered over.** Each cause now has its own chip text, so the banner still carries information instead of one undifferentiated warning, and the CHANGELOG leads with "your model will turn orange; it is a measurement change, not a model change". The deeper point — that a permanently-on warning decays — is real and unsolved; the honest answer is that the model genuinely has no edge, and hiding that to preserve banner salience would invert the epic. |
| T2 | HIGH | **The chip asserted a fact the panel beneath it contradicted.** `Transparency.tsx` hardcoded 「AI 辨識力不足」 for every degraded cause, so an upgrading user read "the AI cannot discriminate" directly above precision 0.55 and lift 2.2. The red contamination box was gated behind `expanded`, so the *always-visible* claim was the wrong one. | **FIXED** — `get_model_health` returns a machine `reason`; the chip and `ScoreBreakdown`'s fallback both follow it. Independently the highest-value finding of the two reviews, because it was a defect I introduced by changing behaviour without touching the display layer. |
| T3 | MEDIUM | The frontend Transparency fixture had drifted from the real payload — same class of failure #2's pre-mortem caught with the real-schema-pin test. | Same as R5. |
| T4 | MEDIUM | **`setup_real_ai.py`'s 92-ticker floor now contradicts the health verdict.** It warns "may be weak" only *below* the floor; at or above it prints "Done. Start the app" with no caveat — and the 0.98 lift was measured **at** 92 tickers. | **FIXED** — it now prints the actual health status, reason and message at the end, whatever the ticker count. |
| T5 | MEDIUM | **`manage_models list` says the model is fine while the UI says no edge** — Acc / P(SB) with no lift, prevalence or health. | **FIXED** — a `Lift` column, with `-` for entries that predate the measurement. |
| T6 | MEDIUM | The `history[-1]` fallback attaches a precise numeric claim to a version that never earned it. | Same as R2 — found independently by both reviewers. |
| T7 | MEDIUM | **Train-without-recalc mismatch**: `core/market.py` picks the version by row count in `stock_scores` while health reads the loaded `.pkl`, so `train_ai.py` alone can show a lift-specific banner about a model that produced none of the on-screen probabilities. | **ACCEPTED, out of scope.** Pre-existing and orthogonal to this spec — it is a version-selection inconsistency, not a metrics one. Recorded here so #3 or a follow-up can pick it up deliberately rather than rediscover it. |
| T8 | MEDIUM | `docs/DATA_INTEGRITY.md` still listed this as an open item under "what is still not protected". | **FIXED** — reworded to record that the attribution is now disclosed via `oos_metrics_scope`, while being explicit that the *measurement* is unchanged. |
| T9 | MEDIUM | `ScoreBreakdown.tsx`'s empty-message fallback asserted the same single wrong cause. | Same as T2. |
| T10 | LOW | `API_CONTRACT.md` did not document `/api/transparency`, making the rename an undocumented breaking change. | Same as R6. |
| T11 | LOW | `LiftRow` rendered `—` for old entries while still printing 「低於 1.0 代表比亂猜還差」 — a threat beside a blank. | **FIXED** — an explanatory line for entries that predate the measurement. |

**Cleared by the pre-mortem, recorded so it is not re-derived**: a fresh install is **not** worse
off. No model → `unavailable` → 示範模式 badge, unchanged; the bundled demo trains a degenerate
model, so the pre-existing zero-power rule fires first with an unchanged message; `GettingStarted`
and `Dashboard` key on `unavailable` only, so the demo badge is untouched.

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

- **State**: implemented, reviewed, fixed, tested; ready to ship.
- **Completed**: test-split prevalence + lift recorded and surfaced; `oos_metrics_scope` attribution;
  `get_model_health` rebuilt as six worst-first verdicts each with a machine `reason`; payload,
  panel, CLI and setup script all aligned to the same verdict.
- **Next**: **#4** (rotation ranks profit factors from different settlement regimes and then
  irreversibly `os.remove`s the losers) and **#3** (backtest temporal guard, carrying two #1
  deferrals). #4 is the last P0.
- **Context**: `_raw-intake.md` may be deleted once specs for #3 and #4 exist — not before.

### Read Map

- `docs/specs/oos-metric-attribution-and-lift.md` — this spec, including the F8/F9/F10 breakdown.
- `core/ai/predictor.py::get_model_health` — the six verdicts. The comment there states that the
  **order is the semantics**; do not reorder without re-reading it.
- `frontend/v4/src/pages/Transparency.tsx` — `DEGRADED_CHIP` maps `reason` → label. A new backend
  `reason` needs an entry here or it falls back to the neutral 「模型狀態：需注意」.
- `docs/DATA_INTEGRITY.md` §Verification — the running list of what is still unprotected.

### Skip List

- Do **not** backfill the new keys onto old entries. Their absence is the contamination marker.
- Do **not** tune the `1.0` lift threshold. It is the base rate by definition, not a parameter.
- Do **not** gate health on `lift_buy` — the product acts on StrongBuy; the panel shows Buy in red,
  which is the right surface for it.
- Do **not** re-derive whether a fresh install regressed. It did not; the pre-mortem checked.

### Context Snapshot

Six PRs merged this session before this one: #62 (brain v1.8.25), #63 (epic intake), #64, #65, #66.
Backend 330 tests, frontend 88. The single entry in `models_history.json` (`v4.20260601_2031`) has
all-zero metrics and no `embargo` key, so it reports `degraded` for the **contamination** reason
after this change rather than the zero-power one — a better message for the same verdict.

### Backlog Status

#1 Shipped (#64) · #2 Shipped (#65) · #6 Shipped (#66) · **#5 this branch** · #4 Pending **P0** ·
#3 Pending.

---

## Test Gate Results

> Test-phase gate outcome for `feature`/`architecture-change` logs (required at handoff/ship once an implement receipt exists; ref: `engineering_guardrails.md §12.2`). Record pass/fail counts + the test command. Leave `none` until `/test` runs.

`python -m pytest -q` → **330 passed / 0 failed** (master baseline: 320). `npx vitest run` → **88
passed** (was 82). `npx tsc --noEmit` clean, production build green.

---

## Evidence

> Reproducible evidence for completed phases. Commands, outputs, versions. "It should work" is NOT evidence.
> **Terse format** (Ref: `engineering_guardrails.md` §5.2b Evidence Truncation Rule): success ≤ 3 lines per claim, failure ≤ 10 lines per claim with the most diagnostic context (root error + bottom of stack), strip passing-test noise. Multiple bullet entries preferred over one long paste.

**AC7 — measured, not asserted.** The real entry `v4.20260601_2031` (no `embargo`, all-zero
metrics) before and after:

| | status | reason | message |
|---|---|---|---|
| before | `degraded` | *(field did not exist)* | 「AI 模型對買訊的辨識力不足」 |
| after | `degraded` | `contaminated_metrics` | 「此模型的評估指標是在舊的切分方式下產生的…並非真正的樣本外結果」 |

**The status does not silently improve** — that is the AC6 regression guard. What changed is the
*reason*, and it changed for the better: both facts were true of this entry, and the reviewer was
right that the contamination one is the more actionable, so the reordered checks now surface it.

**Adversarial probe of the verdict** (run after the finiteness fix):
```
lift=nan   -> degraded / no_baseline        lift=2.5 -> ok       / ok
lift=inf   -> degraded / no_baseline        lift=1.0 -> degraded / below_baseline
lift='abc' -> degraded / below_baseline     borrowed -> degraded / metrics_not_for_this_version
```
`json.loads('{"lift_strong": NaN}')` parses successfully, `nan <= 1.0` is `False` and
`nan is None` is `False` — which is exactly why NaN escaped both guards before.

**Tests** — backend **330 passed** (baseline 320), frontend **88 passed** (baseline 82), `tsc
--noEmit` clean, production build green.

**Falsification.** Each new rule fails when reverted: removing the embargo+lift branches fails 2 of
the health tests; restoring `float(precision)/(prevalence or 1.0)` fails the zero-prevalence test;
pointing the trainer's call site at `y_train_full` fails the integration test.

**Two rounds of my own test theatre, caught and replaced.** Worth recording because the same
mistake took two forms:
1. The first draft asserted `status in {"ok", "degraded"}` — trivially true. I caught this one
   myself while writing the reviewer's brief, and fixed the *code* so a real assertion existed to
   make (a post-embargo entry missing its lift is now `degraded`).
2. Its replacement monkeypatched `class_prevalence` and then called it directly, proving nothing
   about the trainer's call site. The reviewer caught it. Replaced with a real small
   `train_and_save` run reading back `models_history.json`.
3. That integration test then broke suite isolation by deleting `core/*` from `sys.modules`
   mid-run, causing 4 unrelated failures. It patches the module constant instead.

The pattern: a test that cannot fail is worse than no test, because it reports coverage that does
not exist.
