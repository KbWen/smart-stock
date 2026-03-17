---
status: frozen
module: frontend-v4
---
# Spec: Frontend Testing Infrastructure (V4)

## 1. Goal

Establish a robust testing foundation for the Frontend V4 codebase to ensure component reliability, prevent regressions, and validate end-to-end user flows.

## 2. Acceptance Criteria (AC)

- [x] **Unit Testing**: Configure `Vitest` and `React Testing Library`. _(vite.config.ts test block + jsdom env + setupTests.ts)_
- [x] **Component Verification**: At least one core component (e.g., `CandidateRow` or `CandidateTable`) must have unit tests covering rendering and signal logic. _(CandidateRow×3, StatCard×5, MarketStatusHeader×6, StockList×5 tests)_
- [x] **E2E Testing**: Configure `Playwright` for cross-browser testing. _(playwright.config.ts + e2e/dashboard.spec.ts with route mocking + perf assertions)_
- [x] **Data Mocking**: Implement a standard pattern for mocking API calls in tests (using `msw` or internal mocks). _(vi.spyOn(global,'fetch') in apiClient.test.ts; vi.mock useCachedApi pattern in hooks/__tests__ and components/__tests__)_
- [x] **CI Readiness**: Add `test:unit` and `test:e2e` scripts to `package.json`. _(both scripts present in package.json)_
- [ ] **Coverage Reporting**: Generate a visual coverage report demonstrating > 40% initial coverage for V4 components. _(pending: run `npm run test:coverage`; estimated ~35-45% with current 6 test files)_

## 3. Non-goals

- Implementing visual regression testing (pixel-perfect matching).
- Testing legacy V1/V2/V3 codebases.
- Setting up a full CI/CD pipeline (execution of tests in GitHub Actions is out of scope for this specific spec, though config should support it).

## 4. Constraints

- Must stay compatible with **React 19** and **Vite**.
- Unit tests must run without requiring a browser (Node.js environment).
- E2E tests must be capable of running against `localhost:5174`.

## 5. Tooling Selection

- **Runner**: Vitest (Native Vite integration).
- **DOM Logic**: React Testing Library.
- **E2E**: Playwright.
- **Coverage**: `@vitest/coverage-v8`.

## 6. File Relationship

This spec is **INDEPENDENT** but follows the architecture established in `docs/specs/frontend-api-opt.md`.
