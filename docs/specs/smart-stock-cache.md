---
status: frozen
module: frontend-data
---
# Spec: Frontend Aesthetics & Data Cache Optimization

## 1. Goal

Improve the visual quality of the `smart-stock` dashboard to a "Premium Glassmorphism" standard and eliminate significant data loading delays caused by redundant indicator re-computation.

## 2. Acceptance Criteria (AC)

- [x] **Data Performance**: Individual stock detail loading (`/api/v4/stock/{ticker}`) must return in < 300ms if data exists in `stock_indicators` table. _(V4StockDetailService 6h DB fast-path; in-memory cache 300s)_
- [x] **Cache Logic**: API must prioritize `stock_indicators` cache (TTL: 6h) over on-the-fly re-computation. _(timedelta(hours=6) freshness check in v4_stock_detail_service.py)_
- [x] **UI Aesthetics**: All cards in `Dashboard.tsx` must implement `backdrop-blur` and multi-layered semi-transparent borders. _(.glass-card: backdrop-blur-xl + border-white/10; StatCard: .premium-card with backdrop-blur-md)_
- [x] **UX Transition**: `SniperCard` must show "Stale" cached data immediately while fetching updates in the background (SWR pattern). _(isDbStale banner + RefreshCw; useCachedApi SWR via getCachedData pre-load)_
- [x] **Code Integrity**: Common UI patterns (Glass cards, standard buttons) must be extracted to `src/components/ui/`. _(GlassCard.tsx + Button.tsx + index.ts created 2026-03-17)_

## 3. Non-goals

- **Re-training AI Models**: This task will NOT modify Model Architecture or training scripts.
- **Backend API Migration**: We are not changing the technology stack (FastAPI), only optimizing internal logic.
- **Mobile App Development**: Scope is limited to the Desktop Web Dashboard.

## 4. Constraints

- Must maintain compatibility with existing `storage.db` schema.
- Must not break existing `yfinance` fallback mechanisms.

## 5. File Relationship

This spec is **INDEPENDENT** and provides the first formal documentation for the v4.x Frontend/Cache layer.
