---
status: frozen
title: Frontend Tests into CI
source: external
source_doc: _product-backlog.md (#6)
created: 2026-06-13
---

# Frontend Tests into CI

# Goal
Make the "Frontend 44/44" quality gate real by running the frontend unit tests and the production build in CI — previously only backend pytest ran, so the frontend gate was never enforced.

## Acceptance Criteria
1. A GitHub Actions workflow runs on push (master, claude/**, feature/**) and PRs to master that: installs frontend deps via `npm ci`, runs `vitest run`, and runs the production build (`npm run build`).
2. The job fails if any vitest test fails or the production build (`tsc -b && vite build`) fails.
3. Node 20 with npm cache keyed on `frontend/v4/package-lock.json`.

## Non-goals
- Playwright e2e in CI (separate, heavier; out of scope this stage).
- Coverage thresholds / gating on coverage.

## File Relationship
EXTENDS .agentcortex/specs/frontend-testing.md
