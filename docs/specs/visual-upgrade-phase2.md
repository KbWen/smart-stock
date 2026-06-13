---
id: visual-upgrade-phase2
status: frozen
created: 2026-03-28
owner: KbWen
source: natural-language (retroactive)
source_doc: docs/specs/_raw-intake.md
---

# Spec: 視覺衝擊力升級 Phase 2 — Sparkline 迷你走勢圖

## Problem Statement

候選股列表只顯示數字（價格、漲跌幅、評分、AI 機率），
使用者無法一眼判斷近期走勢方向與動量，
需要在每一列嵌入 30 日收盤價迷你走勢圖，提升資訊密度與視覺質感。

## Scope

- **後端**：新增 `GET /api/v4/stock/{ticker}/sparkline` 輕量 endpoint（純收盤價，不跑指標計算）
- **前端**：新增 `SparklineChart` 元件 + `useSparkline` hook；整合至 `CandidateRow`

## Out of Scope

- 不做 K 線圖（只顯示收盤價折線）
- 不顯示信號 dot（信號已在 SniperCard PriceSignalChart 中呈現）
- 不加 X/Y 軸、tooltip、legend（保持最小尺寸）
- 不做批次 endpoint（每列各自 lazy 請求，利用 TTL cache 去重）
- 不修改現有 `/api/v4/stock/{ticker}/history` endpoint

## Acceptance Criteria

- AC1: `GET /api/v4/stock/{ticker}/sparkline` 回傳陣列，每筆含 `{date, close}`，預設 30 筆（最新 30 根 bars）
- AC2: sparkline endpoint 有 in-memory cache，TTL=60s，key=`sparkline:{ticker}`，不重複 DB 讀取
- AC3: sparkline endpoint **不呼叫** `compute_v4_indicators` 或 `calculate_rise_score_v2`（純 DB load + tail）
- AC4: `SparklineChart` 以 `change_percent > 0` → 紅色（台灣漲色）、`< 0` → 綠色（台灣跌色）顯示走勢線；無資料時顯示 placeholder div
- AC5: `useSparkline(ticker)` 透過 `useCachedApi` 取得資料，ttlMs=60s，throttleMs=200ms
- AC6: `CandidateRow` 在 ticker 欄位嵌入 SparklineChart，`CandidateTable.ROW_HEIGHT` 由 76 調整為 92px
- AC7: 後端測試 ≥162 pass，前端測試 ≥43 pass，production build 無 TypeScript 錯誤

## Technical Constraints

- Recharts v3.7.0（現有依賴，不新增 chart library）
- sparkline endpoint cache 獨立於現有 `history:{ticker}` cache（不同 key）
- `CandidateRow` 使用 virtual scroll，sparkline 只在可見列 mount/unmount（不需額外 IntersectionObserver）
- 不引入新的前端 library
- ticker 格式驗證沿用現有 `_TICKER_RE` regex[FROM-SOURCE]

## API / Data Contract

```
GET /api/v4/stock/{ticker}/sparkline
Response: [
  { "date": "2026-01-02", "close": 580.0 },
  ...  // 30 items max, ascending by date
]
Errors:
  422 — invalid ticker format
  404 — ticker not found in DB
```

## File Relationship

EXTENDS `docs/specs/visual-upgrade-phase1.md`
