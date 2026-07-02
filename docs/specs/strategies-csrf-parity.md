---
status: frozen
module: strategies-csrf-parity
version: 1.0.0
source: review-finding (Strategy Lab #1 independent review; Honest Research Workbench epic #6)
source_doc: _product-backlog.md
created: 2026-07-02
---

# Strategies CSRF-Header Parity

Honest Research Workbench epic **#6** (review-finding / quick-win). Surfaced by the Strategy Lab (#1) independent review: the mutating `/api/strategies` endpoints did not replicate the `X-Requested-With` CSRF-parity check that `POST /api/smart_scan` already enforces (`backend/routes/stock.py:178`). No active vulnerability (the app has no cookie auth, so there is no ambient credential to ride), but it is an inconsistency with the shipped security baseline (`docs/specs/api-security-hardening.md`). This closes it.

## 1. Goal
- Bring `POST/PUT/DELETE /api/strategies` to parity with the app's existing lightweight CSRF defense: require the `X-Requested-With: XMLHttpRequest` header on mutating requests.

## 2. Acceptance Criteria
1. **[FROM-SOURCE]** `POST`, `PUT`, and `DELETE /api/strategies*` reject requests missing `X-Requested-With: XMLHttpRequest` with **HTTP 403** (message parity with `smart_scan`: "Missing X-Requested-With header"), via a shared `_require_xrw(request)` helper. Read-only `GET /api/strategies` and `GET /api/strategies/compare` are unaffected.
2. **[FROM-SOURCE]** No client regression: the frontend `mutateJson` already sends the header (added in #1), so the Strategy Lab UI keeps working. Backend CRUD tests send the header by default (fixture); a dedicated test asserts the 403 gate when it is absent/wrong.
3. **[FROM-SOURCE]** Tests: a test asserting 403 on header-less POST/PUT/DELETE and 200 on header-less GET; the full strategy suite stays green.

## 3. Non-goals
- No full CSRF token system (unnecessary — no cookie auth). No change to CRUD/compare behavior beyond the header gate. No new endpoint.

## 4. Constraints
- Additive & reversible: one helper + three one-line guards. Rollback removes them.
- Parity, not novelty: reuse the exact `smart_scan` check (same header, same 403).

## 5. File Relationship
EXTENDS `docs/specs/strategy-lab.md` (hardens its endpoints); upholds `docs/specs/api-security-hardening.md` (CSRF-parity baseline).
