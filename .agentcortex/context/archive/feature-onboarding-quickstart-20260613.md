# Work Log: feature/onboarding-quickstart

## Header

- Branch: `feature/onboarding-quickstart`
- Classification: `feature`
- Classified by: `claude-opus-4-8[1m]`
- Frozen: `true`
- Created Date: `2026-06-13`
- Owner: `luvseldom@gmail.com`
- Guardrails Mode: `Full`
- Current Phase: `ship`
- Checkpoint SHA: `03274d1` (feat(onboarding): offline demo seed; base 844f89b)
- Recommended Skills: `verification-before-completion (completion claims), karpathy-principles (coding baseline), test-driven-development (seed verification), production-readiness (idempotent/offline seed)`
- Primary Domain Snapshot: `none`
- SSoT Sequence: `none`

---

## Session Info

- Agent: `claude-opus-4-8[1m]`
- Session: `2026-06-13`
- Platform: `claude-code`
- Guardrails loaded: `§1, §2, §4, §7, §8.1, §10 (core)` + `§5/§12 at implement`.
- Override: `none`

---

## Task Description

- Feature #1 of Optimization Round 2 (P1). Make the repo trivially adoptable: a newcomer sees a populated dashboard within minutes, offline. `storage.db`/model are gitignored → fresh clone is empty. Deliver a committed demo price fixture + idempotent offline `seed_demo.py` (reuses recalculate) + one-command `quickstart.sh`/`.ps1` + README Quickstart, and correct the README labeling description to match the shipped ATR default (honesty). Spec: `docs/specs/onboarding-quickstart.md` (frozen). Stacked on #2 (844f89b).
- Phase chain: `/spec ✅ → /plan → /implement → /review → /test → /handoff → /ship`.

---

## Phase Sequence

| Phase | Status | Entered | Notes |
|---|---|---|---|
| bootstrap | done | 2026-06-13 | feature; tooling+docs+data asset; offline seed |
| plan | done | 2026-06-13 | 6 target files; offline seed; Mode Normal |
| implement | pending | — | — |
| implement | done | 2026-06-13 | 03274d1; 205 pass; no-model fresh-clone proof |
| review | done | 2026-06-13 | inline burden-of-proof; recalc fix adversarially verified |
| test | done | 2026-06-13 | 205 pass; +4 seed tests; offline+no-model paths |
| handoff | done | 2026-06-13 | resume written; closure Open PR (stacked) |
| ship | done | 2026-06-13 | PR #24; SSoT+backlog updated; epic complete |

---

## Phase Summary

- bootstrap: classified `feature` (adds data/demo/ asset dir + offline seed capability; §10.1 new-directory). Spec frozen. Honesty: demo runs without a bundled model (AI shows N/A honestly); README labeling description corrected to shipped ATR default.
- plan: 6 target files; offline idempotent seed reusing recalculate. | Confidence: 90% — high.
- implement: data/demo/demo_prices.csv (6 tickers, 3825 rows) + scripts/seed_demo.py (idempotent, offline) + quickstart.sh/.ps1 + README (quickstart + label-honesty fix) + 4 tests. **Scope addition (justified)**: backend/recalculate.py — discovered & fixed a real gating bug (V4 technical scoring required a loadable model → a fresh clone with NO model produced 0 scores = empty dashboard, contradicting the feature's claim). Fixed: technical scores compute regardless of model; AI prob stays NULL (honest). Commit 03274d1. Full suite 205 pass. | Confidence: 95% — high.
- review: inline burden-of-proof (tooling+docs+1-logic-line core fix; lower risk). recalc fix adversarially verified by the no-model fresh-clone proof (score rows=6, ai-not-null=0) + full suite green + existing test_recalculate.py still passing. Honesty audit: README now matches shipped ATR default; demo claim verified true for the real fresh-clone (no-model) path. No overclaim. AC1-AC6 all evidenced.
- test: full suite 205 pass / 0 fail / 1 integration deselected (+4 seed tests). AC→test — AC2→test_seed_demo_populates_offline; AC5→test_seed_demo_populates_offline + test_seed_demo_works_without_model (no-model honest path) + idempotency + missing-fixture; AC6→full suite. Offline guaranteed (network-fetch guard in fixture). | Confidence: 95% — high.
- handoff: stacked on #2 (base 844f89b). Committed 03274d1. Resume written. Closure: Open PR (base = feature/ml-label-redesign). Next: /ship.
- ship: PR #24 (stacked on #23→#22). SSoT Spec Index + Ship History + Active Backlog updated; backlog #1 → Shipped; spec → shipped. Work log archived + INDEX.jsonl. **Optimization Round 2 epic complete** (#3 data + #2 ML-labels + #1 onboarding). Honesty preserved: every claim backed by reproduced evidence; the no-model fresh-clone gap was caught and fixed.

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
| Spec | docs/specs/onboarding-quickstart.md | Frozen — AC source |
| Code | backend/recalculate.py | recalculate_all(incremental=False) — offline scoring reused by seed |
| Code | start.sh / start.bat | existing run scripts (quickstart complements, no shadow) |
| Data | data/demo/demo_prices.csv | committed demo fixture (6 tickers, exported from dev DB) |

---

## Known Risk

- Idempotency: seed_demo MUST NOT clobber a real synced DB — guard with emptiness check + `--force`.
- Offline guarantee: seed path must not call yfinance; recalculate_all(incremental=False) scores from DB only (verified).
- Fixture honesty: static public-price snapshot, documented; AI shows N/A without a model (no bundled .pkl).
- Rollback: delete data/demo/ + scripts/seed_demo.py + quickstart.* + revert README; no app-logic/DB-schema change.

---

## Conflict Resolution

none

---

## Skill Notes

- test-driven-development: tests for seed orchestration; caught the cross-test pollution (test_backtest fakes core.data) and the no-model gating bug via the offline assertion.
- production-readiness: seed is idempotent (emptiness guard + --force) and offline; clear failure exit code; no clobber of real data.
- verification-before-completion: 5-gate — Scope (planned + justified recalc fix), Quality (205 pass), Evidence (no-model proof), Risk (LABEL/seed rollback), Communication (honest N/A for AI without model).
- karpathy-principles: reused existing recalculate instead of duplicating scoring; minimal recalc fix.

---

## Drift Log

- Skip Attempt: NO
- Gate Fail Reason: N/A
- Token Leak: NO
- ADR coverage: tooling/docs/data-asset; no docs/architecture infra (consistent with prior specs) — skip, logged.
- SSoT write: current_state.md Spec Index + Ship History + Active Backlog via direct Edit (guard replace heavy; Stage-1 WARN-only). Logged per Write-Isolation fallback. Heartbeat/§7 knowledge-consolidation: N/A (no Update Sequence field; no docs/architecture infra).
- Scope addition: backend/recalculate.py is_v4 gating fix — beyond the 6 planned files but REQUIRED for the feature's core claim (no-model fresh clone must show scores). User-priority honesty: caught via the no-model proof.
- ship: PR #24 stacked on #23→#22. Round-2 epic (#3+#2+#1) complete.

---

## Design Reference

none (CLI/docs/tooling — no UI rendering code; §4.4 exempt)

---

## Observability

none

---

## Resume

- State: HANDEDOFF (ship pending)
- Completed: spec frozen, bootstrap/plan/implement/review/test(205 pass); commit 03274d1
- Next: /ship — push (base=feature/ml-label-redesign, stacked PR), SSoT Spec Index + Ship History, backlog #1→Shipped (Round-2 epic complete)
- Context: Offline demo seed + quickstart so a fresh clone shows a populated dashboard in minutes. Found+fixed a recalc gating bug (no-model → 0 scores); now technical scores compute without a model, AI = honest N/A.

### Read Map (for next agent)
- docs/specs/onboarding-quickstart.md → full (frozen AC source)
- scripts/seed_demo.py → full (offline seed)
- backend/recalculate.py → is_v4 gating fix (lines ~65-73)

### Skip List
- tests/ — green (205), no changes expected
- core/ — untouched by #1 (only backend/recalculate.py logic fix)

### Context Snapshot (≤ 200 tokens)
storage.db + model_sniper.pkl are gitignored → fresh clone empty. #1 bundles data/demo/demo_prices.csv (6 tickers) + scripts/seed_demo.py (idempotent, offline; loads fixture → recalculate_all(incremental=False) scores DB tickers offline). quickstart.sh/.ps1 wrap install+seed+run. README gained a Quickstart section and its label description was corrected to the shipped ATR default (#2). Critical honesty fix: recalculate gated V4 technical scoring behind a loadable model, so a no-model fresh clone got 0 scores; now technical scores always compute and AI prob stays NULL when no model. Verified: no-model seed → 6 scores, AI NULL. Round-2 epic (#3+#2+#1) complete after this ship.

### Backlog Status
- Active Backlog: docs/specs/_product-backlog.md
- Current Feature: #1 onboarding — shipping now
- Remaining: 0 pending (Round-2 epic complete after #1 ships)
- Next Recommended: epic done — optional /retro

---

## Evidence

- Full suite: `pytest -q -m "not integration"` → `205 passed, 1 deselected` (+4 vs #2 baseline 201).
- Seed tests: `pytest tests/test_scripts_seed_demo.py -q` → `4 passed` (offline populate, no-model path, idempotency, missing-fixture).
- **Honest fresh-clone proof** (no model file, simulated): `seed(force=True)` → `score rows=6, ai-not-null=0` → technical scores populated, AI honestly NULL. This is the real target-user scenario.
- Offline guarantee: tests monkeypatch `fetch_stock_data` to raise on any call; seed + recalculate never trigger it.
- Quickstart syntax: `bash -n quickstart.sh` OK; PowerShell `ParseFile` on quickstart.ps1 OK.
- Idempotency: second `seed(force=False)` returns loaded=0 and prints "Skipping load".
