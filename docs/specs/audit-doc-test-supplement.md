---
id: audit-doc-test-supplement
status: frozen
source: internal-audit
created: 2026-03-21
module: core/ai, backend/routes, docs/guides
---

# Spec: Audit Doc & Test Supplement

## Background

PR#4 (fervent-poincare) merged HMAC model signing and rate limiting. The merge also resolved
stash conflicts, adding `_verify_hmac()` to `core/ai/predictor.py` and restoring `_cfg` import
in `core/ai/trainer.py`. These features currently have zero test coverage. Two operational
guides are also missing.

## Acceptance Criteria

| # | Criteria | File |
|---|----------|------|
| AC1 | `_verify_hmac()` — valid key + valid sig → returns True | tests/test_core/test_predictor_hmac.py |
| AC2 | `_verify_hmac()` — valid key + wrong sig → returns False + logs warning | tests/test_core/test_predictor_hmac.py |
| AC3 | `_verify_hmac()` — no signing key configured → returns True (opt-out) | tests/test_core/test_predictor_hmac.py |
| AC4 | `_verify_hmac()` — no .sig sidecar → returns True (legacy model) | tests/test_core/test_predictor_hmac.py |
| AC5 | trainer HMAC sidecar: MODEL_SIGNING_KEY set → .sig file written on save | tests/test_core/test_trainer_hmac.py |
| AC6 | trainer HMAC sidecar: no MODEL_SIGNING_KEY → no .sig file written | tests/test_core/test_trainer_hmac.py |
| AC7 | `docs/guides/model-signing.md` covers: env var, key generation, verify flow | docs/guides/model-signing.md |
| AC8 | `docs/guides/rate-limiting.md` covers: 3 endpoints, tiers, test instructions | docs/guides/rate-limiting.md |
| AC9 | All pre-existing pytest tests pass (pytest tests/ -q) | CI |

## Scope

**New files:**
- `tests/test_core/test_predictor_hmac.py`
- `tests/test_core/test_trainer_hmac.py`
- `docs/guides/model-signing.md`
- `docs/guides/rate-limiting.md`

**Modified files:**
- `.agentcortex/context/work/master.md` (plan + evidence updates)
- `.agentcortex/context/current_state.md` (ship record, on /ship only)

## Non-Goals

- Do NOT modify predictor.py, trainer.py, or stock.py logic
- Do NOT add new rate limit values or change existing limits
- Do NOT implement logger.py TODO hook
