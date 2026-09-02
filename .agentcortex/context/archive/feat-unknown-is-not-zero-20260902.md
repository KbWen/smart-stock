
# Work Log: feat/unknown-is-not-zero

## Header

- Branch: `feat/unknown-is-not-zero`
- Classification: `feature`
- Classified by: `claude-opus-5`
- Frozen: `2026-09-02`
- Created Date: `2026-09-02`
- Owner: `KbWen`
- Guardrails Mode: `Full`
- Current Phase: `test`
- Diff Base SHA: `88e6086` <!-- immutable: set once on first /implement -->
- Checkpoint SHA: `pending` <!-- mutable: refresh each commit -->
- Recommended Skills: `none`
- Primary Domain Snapshot: `ml`
- SSoT Sequence: `10`

---

## Session Info

> Written by /bootstrap. Update on each new session.

- Agent: `claude-opus-5`
- Session: `2026-09-02 12:00 UTC`
- Platform: `claude-code`
- Files Read: `0` (optional — running count of file reads across this session for token-budget instrumentation; bootstrap may seed `0`, later phases may increment when material).

---

## Task Description

Unknown Is Not Zero epic #1 (GH #14). The prediction path fills every uncomputable feature with `0`,
and `0` is a specific claim about the stock, not a blank: measured on 2330's real last trading day,
`dist_sma240` reads `+0.3429` with full history and `0.0` (exactly on the annual mean) with 150 rows.
Prediction must refuse rather than substitute. Spec: `docs/specs/unknown-is-not-zero-ml-features.md`.

---

## Phase Sequence

> Record each phase entry in order. Update `Current Phase` in the Header on entry.

| Phase | Status | Entered | Notes |
|---|---|---|---|
| bootstrap | done | 2026-09-02 | Classified `feature`; spec frozen; band measured at 120<=rows<260 |
| plan | done | 2026-09-02 | Guard follows the features, not a row count |
| implement | done | 2026-09-02 | AC1 widened, AC5/AC7 narrowed; 365 backend / 90 frontend |
| review | done | 2026-09-02 | Both NOT READY; converged on a 250-row cliff meeting a 420-day window |
| test | done | 2026-09-02 | 369 backend / 92 frontend; every review fix falsified |
| handoff | pending | — | — |
| ship | pending | — | — |

---

## Phase Summary

**plan** — The gate follows the **features**, not a row count: a finite check over `FEATURE_COLS`
covers any future feature with any window, while a constant covers only the windows that existed when
it was written. `MIN_FEATURE_ROWS` explains the refusal in the UI and never gates — two mechanisms
that can disagree is how a disclosure field ends up contradicting the behaviour it describes.

**implement** — Two ACs amended, both recorded in the spec with the reason. **AC1 widened** from "no
longer substitutes `0`" to "substitutes nothing", because inventorying for AC9 turned up two more
substitutions on the same path: an `ffill()` carrying yesterday's indicator into today's prediction
row, and — the important one — `df = df.fillna(0)` in `legacy_service` and `recalculate` **before**
`predict_prob`. With `sma_240 = 0`, `dist_sma240` becomes a finite astronomical number rather than
NaN, so the finite check sees nothing wrong: **the feature would have been inert on two of three
request paths while every unit test passed**, because unit tests build raw OHLCV where
`prepare_features` computes the indicators itself and the NaN is real. **AC5/AC7 narrowed** to the
detail payload: the candidate list reads a stored scalar from the `scores` table with nowhere to
carry a reason, and a schema migration is excluded by §Constraints. A pre-existing test was defending
the defect — asserting the invented feature equalled `0.0`, with the docstring calling that the
requirement. Third occurrence of that pattern in this project.

**review** — Both `NOT READY`, **converged independently on the same HIGH** (details in Review
Feedback below). The lesson worth carrying: my CHANGELOG said the shipped data was unaffected because
every ticker holds 729+ rows. **A row count in a table says nothing about the frame a model is
given** — through a 420-day window those same tickers yielded ~225 rows and 91 of 92 refused.

**plan** — The gate follows the **features**, not a row count, so a longer-window feature is covered
without anyone remembering a constant. `MIN_FEATURE_ROWS` explains and never gates.

**implement** — AC1 widened, AC5/AC7 narrowed (spec records each). The widening came from
inventorying for AC9: `legacy_service`/`recalculate` ran `df = df.fillna(0)` **before**
`predict_prob`, and with `sma_240 = 0` the check sees a finite number, not a NaN. **The feature
would have been inert on two of three request paths while every unit test passed** — unit tests
build raw OHLCV, where the NaN is real.

**bootstrap** — `feature`. Two corrections before the spec was written: training is **not** affected
(`trainer.py` drops warm-up rows before the fill; GH #14 carries the correction), and the band is
**120 <= rows < 250**, not `< 240`.

⚡ ACX

---

## Gate Evidence

- Gate: bootstrap | Verdict: PASS | Classification: feature | Timestamp: 2026-09-02T12:00:00Z
- Gate: plan | Verdict: PASS | Classification: feature | Timestamp: 2026-09-02T12:20:00Z
- Gate: implement | Verdict: PASS | Classification: feature | Timestamp: 2026-09-02T13:30:00Z
- Gate: review | Verdict: PASS | Classification: feature | Timestamp: 2026-09-02T15:10:00Z
- Gate: test | Verdict: PASS | Classification: feature | Timestamp: 2026-09-02T15:20:00Z

---

## External References

| Type | Path / URL | Notes |
|---|---|---|
| Spec | `docs/specs/unknown-is-not-zero-ml-features.md` | Frozen 2026-09-02 |
| Spec | `docs/specs/backend-failure-state-honesty.md` | EXTENDS — the `ai_prob = NULL` precedent |
| Backlog | `docs/specs/_product-backlog.md` #1 | Unknown Is Not Zero epic, first item |
| Issue | https://github.com/KbWen/smart-stock/issues/14 | Source; carries the triage correction |
| ADR | — | No architecture decision — a correctness fix plus a disclosure field |
| PR | — | filled at ship |

---

## Known Risk

Root Cause: a guard that existed on one path was never extended to the other. `trainer.py` drops
warm-up rows for training with a comment naming this exact hazard; inference reached the `fillna(0)`
on the next line with no equivalent.

- **Coverage falls on young databases.** Intended, but a real regression for a fresh install; the
  user is told why rather than shown a bare N/A.
- **Measure per caller window, not per table.** 92 tickers holding 729+ rows each still produced 91
  refusals through a 420-day window. This is what review caught.
- **`MIN_FEATURE_ROWS` must not become a second gate.** It exists for the message only; if a future
  edit lets it decide whether to predict, it can disagree with the finite check.
- **Four of the 27 `FEATURE_COLS` are finite by construction** (`rise_score_v2` fills its outputs),
  so `uncomputable_features` can never flag them. Not reachable on this data — their raw inputs are
  themselves features and are caught first — but structural, and named in `DATA_INTEGRITY.md`.

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

- **AC1 widened, AC5 narrowed, AC7 retargeted during implement.** Each amendment is recorded in
  `docs/specs/unknown-is-not-zero-ml-features.md` at the AC it changes, with the measurement or
  constraint that forced it. Summary: AC1 covers every substitution on the prediction path, not only
  `0`; AC5 lands on the detail payload only (the candidate list reads a stored scalar with nowhere
  to carry a reason, and §Constraints excludes a schema migration) and drops the
  `uncomputable_features` token; AC7 follows AC5 to `ScoreBreakdown.tsx`.
- **Spec §Scope corrected after review.** Its coverage measurement was falsified — see Review
  Feedback H1.
- **`docs/specs/_raw-intake.md` recreated** — the previous epic deleted its own at close, by design.
  Deleted again once all three first-round specs exist.
- **Backlog rotated at spec-intake** — Honest Metrics archived to
  `_product-backlog-honest-metrics-2026-09-02.md`. That move broke a citation in
  `docs/DATA_INTEGRITY.md`, resolved against the archived file rather than left stale.

## Review Feedback

All resolved, each pinned by a test that fails when the fix is reverted. Two reviewers on disjoint
briefs; they converged on H1 and H2 independently. Full narrative in the PR body and the ship note.

| # | Finding | Resolution |
|---|---|---|
| H1 | `RECALC_LOOKBACK_DAYS = 420` calendar days = ~225 trading rows < 250 -> **91/92 refuse**; `INSERT OR REPLACE` then writes those NULLs over the 730-day sync path's good values | 730; measured **0/92**; pinned against `MIN_FEATURE_ROWS` |
| H2 | `backtest.py` `... or 0.0` books a refusal as a strategy rejection | `excluded_unscorable`; counts survive the no-picks branch |
| H3 | AC4 unimplemented — no ticker in the refusal log | `_ticker_of(df)` + caplog tests |
| M1 | Tooltip blames the model while `model_health: ok`, in the majority branch | Names no cause it cannot prove |
| M2 | Predictor warnings never reached `logs/app.log` under the server | `setup_logger` |
| M3 | False `DATA_INTEGRITY` claim (inf->0 is a no-op) | Replaced with the real structural hole |
| M4 | Spec AC5 said 260; shipped is 250 | Corrected with the derivation |
| M5 | Route test satisfied by a missing `.pkl` (CI) | Fake model + call-count assertion |
| M6 | `v4_candidates_service` coverage change undisclosed | Documented in `API_CONTRACT.md` |
| L1 | Warm-up test satisfied by the `PRED_DAYS` truncation alone | Asserted at the warm-up boundary |
| L2 | Stale `file:line`, several moved by this diff | Resolved from the files |

## Red Team Findings

> Written by /review and /test when adversarial testing runs. HIGH findings do not block but MUST record a risk decision here.

none

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

- `python -m pytest -q` -> **369 passed / 0 failed** (master: 344)
- `npx vitest run` -> **92 passed / 0 failed** (master: 88)
- `npx tsc --noEmit` clean; `npm run build` green; `validate.sh` pass=106 warn=14 **fail=0**

---

## Evidence

- **The defect, on real data.** Ticker 2330, same final trading day, varying only supplied history:
  at 120 rows `dist_sma240` `+0.3429` -> `0.0`, `sma120_slope` `+0.0277` -> `0.0`, `sma240_slope`
  `+0.0312` -> `0.0`; 150-239 rows two of those; 240 one; 250 none.
- **The requirement is 250** = `sma_240` + `pct_change(10)`. Swept 120-275: first fully computable
  count is 250; at 249 the sole offender is `sma240_slope`.
- **The window fix, measured per caller.** `lookback=420` -> rows median 225, **refused 91/92**;
  `lookback=730` -> rows median 429, **refused 0/92**.
- **Nine guards, each falsified by restoring the defect it prevents**: prediction `fillna(0)`,
  prediction `ffill().bfill()`, `reindex(fill_value=0)`, the training `dropna`, `df_for_model` in
  `legacy_service` and in `recalculate`, `RECALC_LOOKBACK_DAYS` back to 420, backtest `or 0.0`, and
  the ticker dropped from the log.
- **A pre-existing test was defending the defect**: it asserted the invented feature equalled `0.0`,
  and its docstring called that the requirement.
