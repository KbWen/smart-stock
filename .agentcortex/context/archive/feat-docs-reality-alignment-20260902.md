# Work Log: feat/docs-reality-alignment

## Header

- Branch: `feat/docs-reality-alignment`
- Classification: `feature`
- Classified by: `claude-opus-5`
- Frozen: `2026-09-02`
- Created Date: `2026-09-02`
- Owner: `KbWen`
- Guardrails Mode: `Full`
- Current Phase: `ship`
- Diff Base SHA: `aa3123f` <!-- immutable: set once on first /implement -->
- Checkpoint SHA: `6dec803` <!-- mutable: refresh each commit -->
- Recommended Skills: `verification-before-completion, red-team-adversarial`
- Primary Domain Snapshot: `docs`
- SSoT Sequence: `6`

---

## Session Info

> Written by /bootstrap. Update on each new session.

- Agent: `claude-opus-5`
- Session: `2026-09-02`
- Platform: `claude-code`
- Guardrails loaded: `.agent/rules/engineering_guardrails.md` §10, `.agent/workflows/shared-contracts.md`
- Files Read: `10` (optional — running count of file reads across this session for token-budget instrumentation; bootstrap may seed `0`, later phases may increment when material).

---

## Task Description

> 1-3 sentences: what is being done and why.

Honest Metrics epic #6, the item that closes the epic's central charge. `docs/DATA_INTEGRITY.md`
asserted protections the code does not provide — in two cases by presenting the **defective** code
as the mitigation — while `README.md` claimed leakage was 「完全杜絕」 and a pure breadth reading was
labelled 風險等級. Make every claim true of the code as it now stands, and name what is still
unmitigated. Spec: `docs/specs/docs-reality-alignment.md` (frozen 2026-09-02).

---

## Phase Sequence

> Record each phase entry in order. Update `Current Phase` in the Header on entry.

| Phase | Status | Entered | Notes |
|---|---|---|---|
| bootstrap | done | 2026-09-02 | Spec frozen; `feature` (docs + core + frontend + API contract) |
| plan | done | 2026-09-02 | Rewrite 4 claim rows + Verification; machine token + frontend label map for the rename |
| implement | done | 2026-09-02 | DATA_INTEGRITY/README/whitepaper/API_CONTRACT + core/market.py + 4 frontend files |
| review | done | 2026-09-02 | Both NOT READY; 3 of my own claims were wrong, all fixed |
| test | done | 2026-09-02 | Backend 320, frontend 82, build green, tsc clean |
| handoff | done | 2026-09-02 | Resume written |
| ship | done | 2026-09-02 | PR opened; SSoT updated; log archived |

---

## Phase Summary

> One paragraph per completed phase. Delta-oriented: what changed, what was decided.
> End this section with the `⚡ ACX` sentinel at least once — `validate.sh` checks for it here so the runtime marker has a persistent audit trail (chat output is ephemeral).

**bootstrap** — Sequenced last among the epic's P0s on purpose: #1 (settlement realism) and #2 (date-based embargo) had to land first so this spec could describe behaviour that exists rather than being rewritten twice. `feature`, not `quick-win` — it spans docs, `core/market.py`, four frontend files, the API contract and tests.

**plan** — Two decisions shaped the work. (1) Rewrite the integrity rows rather than leave the inline `[SUPERSEDED]` markers #2 added: a marker tells a reader the old text is wrong but still makes them derive what is true. (2) For the rename, emit a **stable machine token** and keep the display label in the frontend, rather than moving a display string through the API — which also removes the `market.risk_level.includes('HIGH')` colour matching, a silent-failure mode where re-wording the UI would have broken colours with no error anywhere.

**implement** — `DATA_INTEGRITY.md` rows C1–C4 rewritten with a runnable check where one exists and a `**History**` note where the old text was wrong. The survivorship row was **split in two**: deterministic sampling genuinely does remove ordering/market-cap bias, so that keeps a mitigation row, while survivorship gets its own row marked `NOT MITIGATED`. The `## Verification` section lost both the "True Out-of-Sample generalization" attribution and the circular `days_ago` argument, gaining a real falsifiable control and an explicit list of what is still unprotected. `README.md`'s 「完全杜絕」 and the whitepaper's system-wide `auto_adjust` assertion are gone. `risk_level` → `breadth_level` across `core/market.py`, `docs/API_CONTRACT.md`, `frontend/v4/src/lib/breadth.ts` (new), and three frontend consumers, with no compatibility alias.

**test** — Backend 320 passed (+7 parameterised breadth boundary cases pinning the strict comparisons at exactly 30% and 60%, each also asserting `risk_level` is absent). Frontend 82 passed, `tsc --noEmit` clean, production build green.

**review** — Both returned `NOT READY`, and the result is the most useful thing in this feature: **three of the errors were in text I wrote while implementing the spec whose entire purpose is that documentation must be true** — a mis-cited source that conflated two different runs, a sentence about the test suite that the test suite itself falsifies, and a fresh absolute ("the actual guarantee"). The pre-mortem separately found that I had corrected the target lines while leaving the same claims standing in `README.md`, the highest-traffic file in the repo. Twenty-four findings, all fixed; dispositions below.

⚡ ACX

---

## Gate Evidence

> Gate receipts written by each phase. Format: `- Gate: <phase> | Verdict: PASS | Classification: <type> | Timestamp: <ISO>`
> **Critical**: `|` pipe separators are mandatory. Receipts placed inside markdown code fences are silently masked and NOT counted by validate.sh — always write receipts as plain list lines.
> Receipt order-of-appearance is authoritative for phase progression; `Timestamp` is provenance metadata only (validators require it to be present and parseable, but do NOT enforce monotonic/chronological ordering).

- Gate: bootstrap | Verdict: PASS | Classification: feature | Timestamp: 2026-09-02T11:00:00Z
- Gate: plan | Verdict: PASS | Classification: feature | Timestamp: 2026-09-02T11:10:00Z
- Gate: implement | Verdict: PASS | Classification: feature | Timestamp: 2026-09-02T12:00:00Z
- Gate: review | Verdict: PASS | Classification: feature | Timestamp: 2026-09-02T13:30:00Z
- Gate: test | Verdict: PASS | Classification: feature | Timestamp: 2026-09-02T13:40:00Z
- Gate: handoff | Verdict: PASS | Classification: feature | Timestamp: 2026-09-02T13:50:00Z
- Gate: ship | Verdict: PASS | Classification: feature | Timestamp: 2026-09-02T14:00:00Z

---

## External References

> Links to specs, ADRs, issues, PRs, or design docs relevant to this task.

| Type | Path / URL | Notes |
|---|---|---|
| Spec | `docs/specs/docs-reality-alignment.md` | Frozen 2026-09-02 |
| Spec | `docs/specs/backtest-settlement-realism.md` | #1 — the behaviour C4 now describes |
| Spec | `docs/specs/date-based-train-test-embargo.md` | #2 — the behaviour C1/C2 now describe |
| Backlog | `docs/specs/_product-backlog.md` #6 | Honest Metrics epic |
| ADR | — | No architecture decision — documentation truth plus one field rename |
| PR | — | filled at ship |

---

## Known Risk

> List risks identified during planning or implementation. Include mitigation.

Root Cause: the integrity sheet was written as a *claim* sheet and never re-verified against the
code it described. Two of its rows named specific expressions (`iloc[:split_idx - PRED_DAYS]`,
`gap=20`) that were themselves the defect, so the document was actively vouching for the bug.

- **A breaking API change with no alias.** `risk_level` is removed outright. Justified in the spec
  (keeping the misleading name defeats the purpose; backend and frontend ship as one unit), but
  anyone scripting against `/api/market_status` must update. Disclosed in `CHANGELOG.md` and in a
  note on the `docs/API_CONTRACT.md` entry.
- **The rewrite could itself overstate.** Every new row cites a `file:line` or a runnable command so
  the next audit can falsify it rather than trust it, and AC8 forbids adding a claim that is not
  checkable. The reviewer's brief is explicitly to fact-check the new sentences.
- **A user sees different words for the same market state** (風險等級 → 多頭廣度). Colours are
  unchanged; the transition is stated in the CHANGELOG.
- **The repo may still contradict itself elsewhere.** Other files could assert what the rewritten
  sheet now denies. The tenth-man's brief includes grepping for the old claims across the repo.
  **Partial answer already in hand**: #1's pre-mortem returned a late addendum confirming that
  `scripts/reproduce_pipeline.py:90-91` returns the live `summary` with no baked expected values,
  and that `docs/REPRODUCE.md:62-66` and `docs/MODULE_GUIDE.md:74` describe the backtest *engine*
  rather than its results — so #1's settlement change left **no documentation debt** for this
  feature to clean up. That narrows #6's contradiction sweep to the integrity/README/whitepaper
  surface it already targets.

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

**Verdict: NOT READY.** The brief for this spec was deliberately unusual — *fact-check every
rewritten sentence against the code* — and it earned its keep. **Three of the errors were in text I
wrote while implementing the feature whose entire purpose is that documentation must be true.**

| # | Severity | Finding | Disposition |
|---|---|---|---|
| R1 | HIGH | **I mis-cited my source and conflated two runs.** The Verification section claimed `ml-label-oos-evaluation.md` §Re-measurement shows StrongBuy precision at or below the base rate. That section says close to the opposite: run B gives `atr` StrongBuy 0.365 against 31.0% prevalence (~1.2× lift) and only *Buy* is below chance. The 0.3454-below-0.3512 figure is run **A**, recorded in `_product-backlog.md:53`. Both are true of their own run; blending them and pointing at the wrong section is not. | **FIXED** — both runs reported separately, each with its own citation. |
| R2 | HIGH | **A factually false sentence**: "`pytest tests/test_core/test_embargo.py`, whose every assertion is about distinct dates". The file also asserts `max_rows_per_date == 92` and `cv_gap == PRED_DAYS * 92` — row and sample counts. A skeptic running the cited command finds the contradiction immediately. Copied from that module's own docstring, which was itself inaccurate. | **FIXED** — narrowed to "whose **gap** assertions are about distinct dates rather than row counts", with the exception stated. |
| R3 | HIGH | **A new absolute I introduced**: "the holdout embargo above is the actual **guarantee**". It bounds train/test dates; it says nothing about overlapping labels across tickers or feature construction. | **FIXED** — "the control that is actually enforced", with what it does not cover spelled out. |
| R4 | HIGH | `frontend/v4/e2e/dashboard.spec.ts:18` still asserted `風險等級`. CI runs only `test:unit` + `build`, so this would have failed silently for whoever next ran it — the one test that would have caught a label regression. | **FIXED**. |
| R5 | MEDIUM | `docs/API_CONTRACT.md` showed `"bull_ratio": 0.62` beside a newly added paragraph defining `BULLISH` as `bull_ratio > 60`; `core/market.py:81` returns `62.0` (a percent). The stale example became a visible self-contradiction the moment `breadth_level` was documented next to it. | **FIXED** in both the response and history examples. |
| R6 | MEDIUM | The settlement citation `backend/backtest.py:219-247` covers the clamp and the stop branch but **not** the target settlement at `:252` — half the sentence's claim sat outside the cited range. | **FIXED** — `:219-259` with each branch's line named. |
| R7 | MEDIUM | AC7's colour-mapping coverage was not actually asserted: the existing test passes `riskColorClass` **in as a prop**, so `BREADTH_COLOR` and `breadthOf`'s fallback were never exercised. | **FIXED** — new `src/lib/__tests__/breadth.test.ts` pins that the old display strings degrade to `UNKNOWN` rather than being half-matched, that every level has a label and a colour, and that no label may contain 風險/RISK. |
| R8 | MEDIUM | `breadthLabel` was exported from `useDashboardData` and read by nobody. | **FIXED** — removed; the label is derived once, at the render site. |
| R9 | INFO | `README.md`'s "0 個交易日" was stated unqualified; the measurement is specific to the 92-ticker panel. | **FIXED** — qualifier added. |
| R10 | INFO | The whitepaper cited `core/data.py` / `core/bulk_history.py` with no line numbers, against this spec's own "cite a checkable location" constraint. | **FIXED** — exact lines from `_raw-intake.md`. |
| R11 | INFO | The label-shuffle control is described but **ships no flag** — `grep -rn "shuffle\|permut" core/ai/ scripts/` returns nothing, so it requires a local edit. | **FIXED** — said plainly, including the grep that proves it, rather than implying a command exists. |
| R12 | INFO | The survivorship row's absolute omitted the `backend/backtest.py:67-73` DB fallback universe. | **FIXED** — named, and noted that it is also survivor-only, so the conclusion is unchanged. |

**Verified correct by the reviewer, no action**: the strict `< 0.30` / `> 0.60` comparisons match the
parametrised boundaries exactly, including the 30%/60% NEUTRAL cases (3/10 and 6/10 are exact
doubles, so no float edge); `breadthOf` safely maps null/undefined/unexpected to `UNKNOWN`; the
survivorship, CV-degradation, whitepaper mixed-basis and `embargo`-key claims all match their cited
code; Non-goals respected.

---

## Red Team Findings

> Written by /review and /test when adversarial testing runs. HIGH findings do not block but MUST record a risk decision here.

The pre-mortem's brief was the repo's **self-consistency**, and it found that I had corrected the
target lines while leaving the same claims standing elsewhere — in the highest-traffic file.

| # | Severity | Finding | Risk decision |
|---|---|---|---|
| T1 | HIGH | **`README.md:253` still asserted the exact `auto_adjust` claim the whitepaper had just retracted**, under a heading presenting it as a system-wide safeguard. The next auditor greps `auto_adjust`, finds the README vouching for what the whitepaper denies, and the epic's central charge survives the spec written to close it. | **FIXED** — rewritten to name both ingest paths with line citations and link the integrity sheet. |
| T2 | HIGH | `README.md:255` claimed 「無前視偏誤」 for the backtest, two lines below T1 — the opposite of what the rewritten sheet now says (`backend/backtest.py:176` scores the deployed model over its own training window). | **FIXED** — qualified to feature-layer only, with the model-level gap and survivorship both named and pointed at #3. |
| T3 | HIGH | **`DATA_INTEGRITY.md`'s own header was never rewritten**: "ensure all performance metrics are statistically genuine" and "**no future data can influence past decisions**" — the first two sentences a reader sees, and the strongest overstatement left in the repo, forty lines above the same file marking survivorship NOT MITIGATED. | **FIXED** — a scope note now states that the document records which safeguards exist *and which do not*, that several biases are unmitigated, and that pre-2026-09-02 metrics are contaminated. |
| T4 | MEDIUM | The whitepaper heading still promised "To prevent overfitting and **survivorship bias**" with no bullet addressing it, and kept the absolute "the model never sees the future". | **FIXED** — heading retitled to what the list actually covers, with survivorship named as unmitigated; the split bullet now describes the trading-day embargo and its history. |
| T5 | MEDIUM | Stale e2e assertion. | Same as R4. |
| T6 | MEDIUM | The rewrite introduced two new absolutes. | Same as R2/R3 — found independently by both reviewers. |
| T7 | MEDIUM | **Only the card was renamed.** The nav entry (`Layout.tsx:17` 「市場風險」), both loading strings and the history chart heading still said 風險, so a user reads 多頭廣度 inside a page labelled 市場風險 — and that chart plots only `bull_ratio` / `market_temp` / `ai_sentiment`. | **FIXED** — nav, both loading strings and the chart heading all moved to breadth wording. |
| T8 | MEDIUM | `API_CONTRACT.md` self-contradiction. | Same as R5. |
| T9 | MEDIUM | `REPRODUCE.md` still said "(no look-ahead)" and "Out-of-sample" for the eval it documents. | **FIXED** — qualified with the trading-day embargo and the fact that anything produced before 2026-09-02 was not out-of-sample. |
| T10 | LOW | `CHANGELOG` said "Colours are unchanged" — true for the three real states, but the no-data state went from a yellow `unknown` to a muted `—`, so an empty DB no longer looks like a neutral reading. | **FIXED** — the exception is stated. |
| T11 | LOW | Dead `breadthLabel` export. | Same as R8. |
| T12 | LOW | The three untouched integrity rows cited no `file:line`, against the sheet's own new `[CONSTRAINT]`. | **FIXED** — all three now cite lines that were individually verified to resolve (`:190`, `:182`/`:184`, `:199`/`:200`, `:538-555`). The Imputation row also gained the known train/serve zero-fill asymmetry it had been silent about. |

**Cleared by the pre-mortem, recorded so it is not re-derived**: the rename's blast radius is
genuinely small. `save_market_history` persists only `timestamp/bull_ratio/market_temp/ai_sentiment`
(`core/market.py:110-115`), so **no persisted history row carries the old field** — an existing
user's `market_history.json` round-trips unchanged, nothing renders UNKNOWN or crashes. No reference
in `core/alerts.py`, `backend/recalculate.py`, `scripts/*`, `data/demo/`, `Dockerfile`,
`docker-entrypoint.sh`, `daily_run.*`, `models_history.json` or `stock_list_cache.json`. Only two
HTTP surfaces touch market status and neither reads the field. `Label Bleeding`'s
`iloc[:-PRED_DAYS]` is **not** a repeat of the row-vs-day bug, because `prepare_features` runs
per-ticker before `pd.concat`.

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

- **State**: implemented, reviewed, fixed and tested; ready to ship.
- **Completed**: `DATA_INTEGRITY.md` rewritten (4 claim rows + header scope note + Verification),
  `README.md` (3 claims), whitepaper, `REPRODUCE.md`, `API_CONTRACT.md`; `risk_level` →
  `breadth_level` across backend, 5 frontend files and their tests, plus the nav/chart/loading
  strings the first pass missed.
- **Next**: the epic's three remaining items, both P0s carrying findings this batch measured. **#5**
  (OOS attribution + baseline lift) now also owns the `get_model_health` verdict: with a clean
  embargo the health check is most wrong exactly when the metrics are most honest. **#4** (rotation
  ranking) owns the irreversible `.pkl` deletion across settlement regimes. **#3** carries two #1
  deferrals. Deferred **batch D** (price-source consistency) is still recoverable in `_raw-intake.md`.
- **Context**: `_raw-intake.md` may be deleted once specs for #3, #4 and #5 exist — not before, or
  they lose their source material.

### Read Map

- `docs/specs/docs-reality-alignment.md` — this feature's frozen spec, including the C1–C8 table of
  what each claim said versus what the code did.
- `docs/DATA_INTEGRITY.md` — now the canonical statement of what is and is **not** protected. Its
  §Verification is the list a future feature should be shortening.
- `docs/specs/_product-backlog.md` — the epic, its sequencing, and the P0 escalations.
- `frontend/v4/src/lib/breadth.ts` — the machine-token → label/colour boundary.

### Skip List

- Do **not** re-add a `risk_level` alias. Its absence is the point, and the reviewer confirmed
  nothing persisted or scripted still reads it.
- Do **not** treat `DATA_INTEGRITY.md` as marketing copy. Its new `[CONSTRAINT]` requires every row
  to cite the code implementing it, and a row whose implementation is removed becomes a stated
  limitation rather than a quiet deletion.
- Do **not** re-derive the survivorship position. It is unmitigated, the reason is recorded, and
  fixing it needs a point-in-time universe that does not exist yet.
- Do **not** claim the label-shuffle control is runnable as shipped — it needs a local edit, and the
  doc says so.

### Context Snapshot

Four PRs merged this session before this one: #62 (brain v1.8.25), #63 (epic intake), #64 (#1
settlement realism), #65 (#2 date-based embargo). Backend 320 tests, frontend 87, `validate.sh`
0 FAIL. `storage.db` holds 92 tickers over 2021-11-26 → 2026-07-24 — roughly 5% of the listed+OTC
universe and large-cap biased, so every OOS number in this epic is indicative rather than a
full-universe validation. `models_history.json` holds one entry whose `oos_metrics` predate the
embargo fix and whose contamination is now marked by the **absence** of an `embargo` key.

### Backlog Status

#1 Shipped (PR #64) · #2 Shipped (PR #65) · **#6 this branch** · #3 Pending (carries two #1
deferrals) · #4 Pending **P0** · #5 Pending **P0**.

---

## Test Gate Results

> Test-phase gate outcome for `feature`/`architecture-change` logs (required at handoff/ship once an implement receipt exists; ref: `engineering_guardrails.md §12.2`). Record pass/fail counts + the test command. Leave `none` until `/test` runs.

`python -m pytest -q` → **320 passed / 0 failed** (master baseline: 313; +7 parameterised breadth
boundary cases). `npx vitest run` → **87 passed** (was 82; +5 in the new
`src/lib/__tests__/breadth.test.ts` added after review). `npx tsc --noEmit` clean, production build
green.

---

## Evidence

> Reproducible evidence for completed phases. Commands, outputs, versions. "It should work" is NOT evidence.
> **Terse format** (Ref: `engineering_guardrails.md` §5.2b Evidence Truncation Rule): success ≤ 3 lines per claim, failure ≤ 10 lines per claim with the most diagnostic context (root error + bottom of stack), strip passing-test noise. Multiple bullet entries preferred over one long paste.

**The eight false claims, each verified against the code before rewriting** — the C1–C8 table in
the spec. Two of them (C1, C2) named the *defective* expressions as the mitigation, so the document
was actively vouching for the bug.

**What changed**
- `docs/DATA_INTEGRITY.md`: rows C1–C4 rewritten with a runnable check where one exists and a
  `**History**` note where the old text was wrong. The survivorship row was **split in two** —
  deterministic sampling genuinely removes ordering/market-cap bias so that keeps a mitigation row,
  while survivorship gets its own row marked `NOT MITIGATED`. Header gained a scope note. The
  `## Verification` section lost the "True Out-of-Sample generalization" attribution and the circular
  `days_ago` argument, gaining a falsifiable control and an explicit list of what is unprotected.
- `README.md`: 「完全杜絕」 removed, plus the two further claims the pre-mortem found (`auto_adjust`
  as a system safeguard; 無前視偏誤 for the backtest).
- `docs/project_meta/whitepaper.md`: no longer asserts `auto_adjust=True` system-wide; heading no
  longer promises survivorship protection it does not provide.
- `risk_level` → `breadth_level` with a stable machine token and a frontend label map, removing the
  `.includes('HIGH')` colour matching — a silent-failure mode where re-wording the UI would have
  broken colours with no error anywhere.

**Tests** — backend **320 passed** (baseline 313), frontend **87 passed** (baseline 82), `tsc
--noEmit` clean, production build green.

**Citation verification.** Because this spec's own `[CONSTRAINT]` requires every claim to cite a
checkable location, each line number added to the three previously uncited rows was resolved
individually against `core/ai/trainer.py` rather than estimated: `:190` (terminal truncation), `:182`
vs `:184` (ffill/bfill asymmetry), `:199`/`:200` (dropna vs zero-fill), `:538-555` (atomic swap). An
earlier draft had them off by three lines.

**The finding worth carrying forward.** The fact-check brief — *verify every rewritten sentence
against the code* — caught three errors in text written **during this feature**, including a
sentence that the very test file it cited would falsify. Writing a truthfulness spec does not make
one's own prose true; it has to be checked the same way.
