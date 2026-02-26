---
name: Agent-Driven Development Issue
about: Structured issue for AI-assisted analysis, design, and implementation
title: "[AREA] Short description"
labels: []
assignees: []
---

## 1. Context / Background

（為什麼需要這個改動？現在的狀態有什麼問題或限制？）

---

## 2. Problem Statement

請具體描述「目前不理想的地方」：

- 錯誤行為 / 不一致行為
- 設計瓶頸
- 可擴充性問題
- 可解釋性不足
- 使用體驗不佳

---

## 3. Desired Outcome

描述「完成後應該長什麼樣子」：

- 行為層面（系統應該做到什麼）
- 品質層面（穩定性、可解釋性、可維護性）
- 不需要給數值績效，重點是**性質**

---

## 4. Constraints / Guardrails

（任何**不可違反**的條件）

- 不允許的做法（例如：黑盒、隱性假設）
- 必須維持的特性（例如：可回溯、可審計）
- 資料 / 時序 / 環境限制

---

## 5. Scope (Optional but Helpful)

- 可能影響的模組或資料夾
- 相關檔案路徑
- 是否允許結構性調整（refactor）

---

## 6. Risk & Impact

- 若實作錯誤，影響層級：
  - Low：顯示 / 文件 / 工具
  - Medium：策略邏輯 / 研究結果
  - High：核心管線 / 資料正確性 / 生產系統

---

## 7. Acceptance Criteria

（如何判斷「這個 Issue 完成了」）

- 可驗證的條件（測試、檢查點、行為描述）
- 不需要是數字，可以是「可解釋 / 可追蹤 / 無 side effect」

---

## 8. Notes for Agent

（給 AI Agent 的提示）

- 是否偏好「最小改動」或「結構優化」
- 是否需要先設計再實作
- 是否允許提出替代方案
