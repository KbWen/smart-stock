# Smart Stock — Frontend V4

台灣股市 AI 分析儀表板的現代化前端，使用 React + TypeScript + Vite + Tailwind CSS 打造。

## Tech Stack

- **React 18** + **TypeScript**
- **Vite** (開發/打包)
- **Tailwind CSS** (玻璃擬態深色主題)
- **Recharts v3.7** (PriceSignalChart — ComposedChart + ReferenceDot)
- **React Router** (頁面路由)
- **Vitest** + **@testing-library/react** (單元測試)

## 主要元件

| 元件 | 說明 |
| :--- | :--- |
| `SniperCard` | 每支股票的主卡片，整合 ScoreBreakdown + PriceSignalChart + AIAnalyst |
| `PriceSignalChart` | 90 天收盤價折線 + 訊號 ReferenceDot（⚡Squeeze / ✦Golden Cross / ▲Vol Spike） |
| `ScoreBreakdown` | Rise Score 細項 + AI Probability count-up 動畫 (useCountUp hook) |
| `ErrorBoundary` | 全站 Suspense 錯誤邊界，防止單一元件爆炸影響整頁 |
| `useCachedApi` | SWR 風格快取 hook，含 generation counter 防競態 |

## 開發

```bash
# 安裝依賴
npm install

# 啟動開發伺服器 (需後端 API 運行在 localhost:8000)
npm run dev

# 執行測試
npm run test

# 測試覆蓋率報告
npm run coverage

# Production 建置 (包含 tsc -b 嚴格型別檢查)
npm run build
```

## 測試

```bash
# 執行所有單元測試
npm run test

# 覆蓋率 (目標 ≥80% statements)
npm run coverage
```

目前覆蓋率：**82.7% stmts**，38 tests pass。

## API 端點

前端透過 `useCachedApi` 消費以下後端端點：

| 端點 | 說明 | 快取 TTL |
| :--- | :--- | :---: |
| `GET /api/v4/sniper/candidates` | 排名候選股票列表 | 30s |
| `GET /api/v4/stock/{ticker}` | 單股詳細分析 | 300s |
| `GET /api/v4/stock/{ticker}/history` | 90 天 OHLC + 訊號陣列 | 60s |
| `GET /api/v4/meta` | 市場元資料 | 60s |
