---
status: frozen
module: frontend-data
---
# Spec: Frontend Aesthetics & Data Cache Optimization

## 1. Goal

Improve the visual quality of the `smart-stock` dashboard to a "Premium Glassmorphism" standard and eliminate significant data loading delays caused by redundant indicator re-computation.

## 2. Acceptance Criteria (AC)

- [ ] **Data Performance**: Individual stock detail loading (`/api/v4/stock/{ticker}`) must return in < 300ms if data exists in `stock_indicators` table.
- [ ] **Cache Logic**: API must prioritize `stock_indicators` cache (TTL: 6h) over on-the-fly re-computation.
- [ ] **UI Aesthetics**: All cards in `Dashboard.tsx` must implement `backdrop-blur` and multi-layered semi-transparent borders.
- [ ] **UX Transition**: `SniperCard` must show "Stale" cached data immediately while fetching updates in the background (SWR pattern).
- [ ] **Code Integrity**: Common UI patterns (Glass cards, standard buttons) must be extracted to `src/components/ui/`.

## 3. Non-goals

- **Re-training AI Models**: This task will NOT modify Model Architecture or training scripts.
- **Backend API Migration**: We are not changing the technology stack (FastAPI), only optimizing internal logic.
- **Mobile App Development**: Scope is limited to the Desktop Web Dashboard.

## 4. Constraints

- Must maintain compatibility with existing `storage.db` schema.
- Must not break existing `yfinance` fallback mechanisms.

## 5. File Relationship

This spec is **INDEPENDENT** and provides the first formal documentation for the v4.x Frontend/Cache layer.
