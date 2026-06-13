---
id: visual-upgrade-phase1
status: frozen
created: 2026-03-27
owner: KbWen
source: internal
---

# Spec: 視覺衝擊力升級 Phase 1

## Problem Statement

現有 SniperCard 只顯示最新快照（分數 + 文字信號 badge），
缺乏歷史視覺化，朋友看不到「AI 在做什麼」。
需要讓 AI 預測感和前端質感同時提升。

## Scope

- **後端**：新增 `GET /api/v4/stock/{ticker}/history` endpoint
- **前端**：新增 `PriceSignalChart` 元件；`ScoreBreakdown` 加 AI Probability 計數動畫

## Out of Scope

- 不做 K 線圖（Candlestick）
- 不對每個歷史日期跑 `predict_prob`
- 不加 WebSocket 即時資料
- 不修改 `/api/v4/stock/{ticker}` 現有 endpoint

## Acceptance Criteria

- AC1: `GET /api/v4/stock/{ticker}/history` 回傳陣列，每筆含 `{date, close, is_squeeze, golden_cross, volume_spike}`，預設 90 天
- AC2: history endpoint 有 in-memory cache，TTL=60s，key=`history:{ticker}`，不重算已快取的 df
- AC3: `PriceSignalChart` 顯示收盤價折線 + 信號 `ReferenceDot`（squeeze=黃、golden_cross=藍、volume_spike=紫）
- AC4: AI Probability 數字有計數動畫（0 → 實際值，~1 秒）
- AC5: 快速切換 ticker 不造成舊資料殘留（history fetch 走 `useCachedApi`）
- AC6: 後端測試 ≥140 pass，前端測試 ≥34 pass，覆蓋率維持 ≥80%

## Technical Constraints

- Recharts v3.7.0（現有依賴，不新增 chart library）
- `compute_v4_indicators` + `calculate_rise_score_v2` 結果只走 df 路徑（不走 DB cache 路徑）
- history endpoint cache 獨立於現有 `/api/v4/stock/{ticker}` cache
- 前端動畫純 CSS / React state，不引入新動畫 library
