---
status: frozen
module: backtest-perf
version: 1.0.0
---

# Backtest Financial Metrics Expansion & CandidateTable Virtualization Spec

This specification details the mathematical formulas and parameter additions for the backtest simulator (`backend/backtest.py`), as well as the implementation details for virtual list rendering in the frontend candidate table.

## 1. Goal (目標)
- Enhance backtest fidelity by introducing Sharpe Ratio, Max Drawdown (MDD), and realistic Taiwan stock transaction friction (commission, tax, slippage).
- Boost frontend scroll performance under heavy data loads by introducing virtual list rendering in the CandidateTable.

---

## 2. Acceptance Criteria (AC)

### AC1: Backtest Transaction Friction Formula
- Implement buy/sell transaction cost adjustments on individual trade returns.
- Buy cost: `buy_cost = commission_rate + slippage_rate`
- Sell cost: `sell_cost = commission_rate + tax_rate + slippage_rate`
- Formula for net return:
  $$Net\_ROI = \frac{(1 + Raw\_ROI) \times (1 - Sell\_Cost)}{1 + Buy\_Cost} - 1$$
- Default parameters:
  - `commission_rate` = `0.001425` (0.1425% Taiwan standard)
  - `tax_rate` = `0.003` (0.3% Taiwan stock transaction tax)
  - `slippage_rate` = `0.001` (0.1% slippage)
- These parameters should be configurable via function arguments in `run_time_machine` and exposed via API Query Parameters: `commission_rate`, `tax_rate`, `slippage_rate`.

### AC2: Portfolio Performance Metrics
- **Sharpe Ratio**: Calculate the Sharpe Ratio of the Top Picks.
  - Formula:
    $$Sharpe\_Ratio = \frac{\mu_{net}}{\sigma_{net}}$$
    (where $\mu_{net}$ is the average net return of top picks, and $\sigma_{net}$ is the standard deviation. If standard deviation is 0, Sharpe ratio defaults to 0).
- **Max Drawdown (MDD)**:
  - **Individual MDD**: Average maximum drawdown of selected picks (already exists).
  - **Worst Drawdown**: The worst single-stock drawdown among all selected picks: `min(max_drawdowns)`.

### AC3: Backend API Integration
- Expose the new backtest metrics in the API response `/api/backtest`:
  - New summary fields: `sharpe_ratio`, `worst_drawdown`, `avg_net_return`, `net_win_rate`, `net_profit_factor`.
  - Individual picks should include both `actual_return` (raw) and `net_return` (after fees).

### AC4: Frontend CandidateTable Virtualization
- Implement virtual list rendering in `CandidateTable.tsx` so that only rows visible in the viewport are rendered in the DOM.
- Support smooth scrolling and ensure that Recharts Sparkline mini-charts do not trigger layout shifts or lag during scrolling.
- Avoid third-party dependency installation bloat (like installing heavy external windowing libraries if possible, or use simple virtualization logic or React standard pagination/dynamic rendering if it achieves the same visual excellence and performance).
- Ensure TypeScript compiling passes with no warnings.

---

## 3. Non-goals (非目標)
- Modifying ML model training labels or features.
- Developing portfolio weight optimization models (e.g. Markowitz Mean-Variance).

---

## 4. API & Data Contract (API 數據契約)

### GET /api/backtest
Query parameters:
- `commission_rate` (float, default: 0.001425)
- `tax_rate` (float, default: 0.003)
- `slippage_rate` (float, default: 0.001)

Response schema additions:
```json
{
  "top_picks": [
    {
      "ticker": "2330",
      "actual_return": 0.15,
      "net_return": 0.1412,
      "max_drawdown": -0.02
    }
  ],
  "summary": {
    "avg_return": 0.08,
    "avg_net_return": 0.0715,
    "win_rate": 0.70,
    "net_win_rate": 0.65,
    "sharpe_ratio": 1.45,
    "avg_max_drawdown": -2.3,
    "worst_drawdown": -5.0
  }
}
```

### AC5: Custom Strategy Parameters (自訂策略參數)
- **Parameters**:
  - `target_gain` (float, default: 0.15) — Stop profit target.
  - `stop_loss` (float, default: 0.05) — Stop loss target.
  - `holding_days` (int, default: 20) — Maximum investment horizon window.
- **Backend API Integration**:
  - Expose as query parameters in `GET /api/backtest`: `target_gain` (ge=0.01, le=0.50), `stop_loss` (ge=0.01, le=0.50), `holding_days` (ge=1, le=90).
  - Pass them to `run_time_machine()` to override standard Sniper rules.
- **Frontend Configuration**:
  - Add interactive sliders in the backtest settings panel to adjust these parameters, updating the equity chart and result metrics reactively upon SWR trigger.

---

## 5. File Relationships (文件關係)
- This specification is **INDEPENDENT** from existing specs. It governs backtest metrics and rendering virtualization.
