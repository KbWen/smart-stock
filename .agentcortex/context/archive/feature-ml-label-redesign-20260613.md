# Work Log: feature/ml-label-redesign

## Header

- Branch: `feature/ml-label-redesign`
- Classification: `feature`
- Classified by: `claude-opus-4-8[1m]`
- Frozen: `true`
- Created Date: `2026-06-13`
- Owner: `luvseldom@gmail.com`
- Guardrails Mode: `Full`
- Current Phase: `ship`
- Checkpoint SHA: `12c3160` (docstring fix from review; impl 276798c)
- Recommended Skills: `verification-before-completion (completion claims), karpathy-principles (coding baseline), test-driven-development (label logic), production-readiness (config SSoT integrity)`
- Primary Domain Snapshot: `none`
- SSoT Sequence: `none (no Update Sequence field in current_state.md)`

---

## Session Info

- Agent: `claude-opus-4-8[1m]`
- Session: `2026-06-13`
- Platform: `claude-code`
- Guardrails loaded: `§1, §2, §4, §7, §8.1, §10 (core)` + `§3 (data/time — look-ahead), §5/§12 (testing) at implement`.
- Override: `none`

---

## Task Description

- Feature #2 of Optimization Round 2 (P0). Replace fixed-percentage triple-barrier training labels with **ATR (volatility)-scaled** barriers to fix the degenerate-model root cause (Buy/StrongBuy precision=recall=0). Config-driven (`LABEL_MODE`/`ATR_*_MULT`), `fixed` mode preserved & toggleable. Evidence-first: prove class rebalancing on real dev data; honestly scope out full-universe OOS metric claims (dev DB has only 6 tickers). Spec: `docs/specs/ml-label-volatility-scaling.md` (frozen).
- Pre-measured evidence: fixed → Hold91.1/Buy4.9/Strong4.0; ATR(3.0,1.8,1.5) → Hold58.7/Buy14.5/Strong26.7.
- Phase chain: `/spec ✅ → /plan → /implement → /review → /test → /handoff → /ship`.

---

## Phase Sequence

| Phase | Status | Entered | Notes |
|---|---|---|---|
| bootstrap | done | 2026-06-13 | feature; ATR-label scope; honesty gate AC4 |
| plan | done | 2026-06-13 | 5 steps; fixed-mode golden back-compat; Mode Normal |
| implement | done | 2026-06-13 | 276798c; 201 pass (+11); AC4 evidence captured |
| review | done | 2026-06-13 | fresh acx-reviewer READY; honesty audit clean; 1 LOW doc fixed |
| test | done | 2026-06-13 | 201 pass; 6/6 AC mapped; barrier adversarial cases |
| handoff | done | 2026-06-13 | resume written; closure = Open PR (stacked on #3) |
| ship | done | 2026-06-13 | PR #23 (stacked); SSoT+backlog updated; spec shipped |

---

## Phase Summary

- bootstrap: classified `feature` (alters default training label data-flow; adds config + module; flagged & reversible). Spec frozen with measured fixed-vs-ATR distribution evidence. Honesty constraint front-and-center (AC4): claim only the rebalancing that real data demonstrates; dev DB = 6 tickers → no full-universe OOS quality claim.
- plan: 5 steps, 5 target files (label_analysis.py + test_label_redesign.py new). Extract _compute_targets() branching on LABEL_MODE; fixed = byte-for-byte current logic (golden back-compat test), atr = per-row entry-ATR barriers. Stacked on #3 (base 7634d72). | Confidence: 92% — high (ATR label logic pre-validated on real dev data: 91/5/4 → 59/15/27).
- implement: config+common constants; trainer._compute_targets() pure helper (atr/fixed branch, no look-ahead, NaN-ATR→Hold); label_analysis.py evidence tool; 11 new tests + 1 existing fixed-golden pinned to LABEL_MODE=fixed. Commit 276798c. Full suite 201 pass. AC4 evidence reproduced by shipped tool. Scope: 6 code/test files + spec + backlog (test_ai.py regression-pin required by the default flip — in-scope). Secret scan clean. | Confidence: 95% — high.
- review: fresh independent acx-reviewer (no implement-context). Verdict READY — all 6 ACs ✅PROVEN. Honesty audit CLEAN: grep core/ai for precision/recall/accuracy = 0 hits (no overclaim); reviewer re-ran label_analysis on dev DB → 59.5/13.7/26.8 matches commit exactly; OOS scope disclaimed in spec+docstring+commit. Look-ahead clean (entry price/ATR at entry, only future H/L for touch). Fixed-mode byte-identical to 7634d72. Default-flip does NOT alter saved-model live predictions (predictor discards target). 1 LOW (stale prepare_features docstring) FIXED → commit 12c3160.
- test: full suite 201 pass / 0 fail / 1 integration deselected. AC→test map — AC1→test_config_constants_wired; AC2→test_compute_targets_atr_{strong,buy,stop,none}/_nan_atr_is_hold; AC3→test_compute_targets_fixed_matches_legacy/_ignores_atr; AC4→test_label_distribution_atr_rebalances_vs_fixed (+ shipped label_analysis evidence) ; AC5→backtest untouched (diff); AC6→full suite + test_prepare_features_runs_both_modes. Adversarial barrier cases implemented as tests. | Confidence: 96% — high.
- handoff: stacked on #3 (base 7634d72). Committed 276798c + 12c3160. Resume + Read Map written. Closure: Open PR (base = feature/data-universe-completeness). Next: /ship.
- ship: PR #23 (stacked on #22). SSoT Spec Index + Ship History + Active Backlog updated; backlog #2 → Shipped; spec status → shipped. Work log archived + INDEX.jsonl chain. Honesty preserved end-to-end (rebalancing-only claim).

---

## Gate Evidence

- Gate: bootstrap | Verdict: PASS | Classification: feature | Timestamp: 2026-06-13
- Gate: plan | Verdict: PASS | Classification: feature | Timestamp: 2026-06-13
- Gate: implement | Verdict: PASS | Classification: feature | Timestamp: 2026-06-13
- Gate: review | Verdict: PASS | Classification: feature | Timestamp: 2026-06-13
- Gate: test | Verdict: PASS | Classification: feature | Timestamp: 2026-06-13
- Gate: handoff | Verdict: PASS | Classification: feature | Timestamp: 2026-06-13
- Gate: ship | Verdict: PASS | Classification: feature | Timestamp: 2026-06-13

---

## External References

| Type | Path / URL | Notes |
|---|---|---|
| Spec | docs/specs/ml-label-volatility-scaling.md | Frozen — AC source |
| Code | core/ai/trainer.py | prepare_features SNIPER TARGET block (lines ~103-138) |
| Code | core/config.py / core/ai/common.py | strategy-param SSoT to extend |
| Data | storage.db | dev DB: 6 tickers × ~729 rows (2023-05..2026-06) — label-balance evidence source |

---

## Known Risk

- Honesty risk (PRIMARY): must NOT claim model-quality/precision improvement — only label-distribution rebalancing is validatable at dev-data scale (6 tickers). Ship claim scoped accordingly.
- Default flip to LABEL_MODE=atr changes the NEXT training's labels; existing saved models untouched; ModelHealthBanner still discloses un-retrained/degraded state → no false "improved" surfaced to UI.
- Look-ahead (§3): ATR + entry price at entry row only; future highs/lows only for barrier touch.
- Rollback: set `LABEL_MODE=fixed` (env/config) reverts labeling instantly; revert branch commits otherwise. No DB/model migration.

---

## Conflict Resolution

none

---

## Skill Notes

- test-driven-development: red (missing helper/module/constants) → green per behavior; pure `_compute_targets` helper enables exact barrier-logic unit tests without the indicator pipeline.
- production-readiness: config is single source of truth (no magic numbers); mode togglable for instant rollback; analysis tool restores LABEL_MODE in finally (no global leak).
- verification-before-completion: 5-gate — Scope (planned files + required regression pin), Quality (201 pass), Evidence (label_analysis numbers reproduced), Risk (LABEL_MODE=fixed rollback), Communication (honest scope: rebalancing only).
- karpathy-principles: smallest reversible change; default flip only affects next training; existing models/UI honesty untouched.

---

## Drift Log

- Skip Attempt: NO
- Gate Fail Reason: N/A
- Token Leak: NO
- ADR coverage: data-layer/ML label extension; decision captured in frozen spec; no docs/architecture infra in project (consistent with prior specs) — skip, logged.
- SSoT write: current_state.md Spec Index + Ship History + Active Backlog updated via direct Edit (guard replace-mode mid-file insert is heavy; Stage-1 WARN-only). Logged per Write-Isolation fallback.
- SSoT heartbeat (§8): no Update Sequence field in current_state.md — skipped (consistent with prior ships).
- Knowledge Consolidation (§7): no docs/architecture infra; primary_domain not declared on spec — N/A.
- ship: spec docstring note — final spec status set to shipped; PR #23 stacked on PR #22 (base feature/data-universe-completeness).

---

## Design Reference

none (backend/ML task — no UI surface; §4.4 exempt)

---

## Observability

none

---

## Resume

- State: HANDEDOFF (ship pending)
- Completed: spec frozen, bootstrap/plan/implement/review(READY, honesty-clean)/test(201 pass); commits 276798c + 12c3160
- Next: /ship — push branch (base=feature/data-universe-completeness, stacked PR), SSoT Spec Index + Ship History, backlog #2→Shipped
- Context: ATR-scaled triple-barrier labels replace fixed-% (default LABEL_MODE=atr; fixed preserved & toggleable). Fixes degenerate-model ROOT CAUSE (class imbalance). Honest scope: label rebalancing validated (91/5/4→59.5/13.7/26.8), full-universe OOS NOT claimed (6-ticker dev DB).

### Read Map (for next agent)
- docs/specs/ml-label-volatility-scaling.md → full (frozen AC source; AC4 honesty gate)
- core/ai/trainer.py → _compute_targets + prepare_features target block
- core/ai/label_analysis.py → evidence tool (compare_modes)
- core/config.py → LABEL_MODE + ATR_*_MULT

### Skip List
- tests/ — green (201), no changes expected
- core/ai/predictor.py — unaffected (discards target; verified by reviewer)
- backend/* — unaffected (no signature/contract change)

### Context Snapshot (≤ 200 tokens)
Label mode is config-driven (`common.LABEL_MODE`, read dynamically). `_compute_targets(closes,highs,lows,atr,mode)` is the pure barrier helper: atr mode scales by per-row ATR-14 at entry (no look-ahead), fixed mode is byte-identical to pre-change. Default flipped to 'atr' → only the NEXT training run relabels; saved models + live predictions unchanged; ModelHealthBanner still discloses un-retrained state. To actually realize the fix in production a retrain on full-universe data is required (out of scope here, data-limited). Rollback = set LABEL_MODE=fixed. Next feature: #1 onboarding (P1).

### Backlog Status
- Active Backlog: docs/specs/_product-backlog.md
- Current Feature: #2 ML label redesign — shipping now
- Remaining: 1 pending (#1 onboarding P1)
- Next Recommended: #1 frictionless onboarding

---

## Evidence

- Full suite: `pytest -q -m "not integration"` → `201 passed, 1 deselected` (+11 vs #3 baseline 190).
- Feature tests: `pytest tests/test_core/test_label_redesign.py -q` → `11 passed`.
- AC4 reproducible evidence (via shipped `core/ai/label_analysis.compare_modes` on dev DB, 6 tickers, n=2300): fixed → Hold 91.1% / Buy 4.9% / Strong 4.0% (degenerate); atr → Hold 59.5% / Buy 13.7% / Strong 26.8% (balanced). Matches frozen spec Background.
- Backward-compat: `LABEL_MODE=fixed` golden test (test_ai.py) pins legacy labels → unchanged.
- HONEST SCOPE: label-distribution rebalancing is validated; full-universe OOS precision/recall is NOT claimed (dev DB = 6 tickers). Existing saved models untouched.
