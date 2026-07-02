---
status: frozen
module: explainable-screening
version: 1.0.0
source: user-directed (Honest Research Workbench epic #3)
source_doc: _product-backlog.md
created: 2026-07-02
---

# Explainable Screening — Why Did This Stock Score?

Honest Research Workbench epic **#3**. Turns the candidate score panel (`ScoreBreakdown`, shown in `SniperCard`) from bare numbers into an honest explanation: which technical signals fired and what they mean, and — critically — an **AI probability that is qualified by `model_health`** so a user never reads a degraded model's number as reliable. Reuses existing signals; adds NO new ML and no fabricated per-signal win-rate.

## 1. Goal
- Make each candidate's score legible: surface the already-computed `signals` (squeeze / golden_cross / volume_spike) and score composition (trend / momentum / volatility) with plain-language one-liners.
- Close a real honesty gap: `ScoreBreakdown` currently shows the AI probability bare, even when `get_model_health()` reports the active model has zero buy-signal discriminative power. Qualify it inline.

## 2. Progressive Disclosure (epic cross-cutting constraint)
- **Simple default path**: a novice sees plain-language chips for the signals that fired ("MACD/KD 黃金交叉", "爆量", "低波壓縮") and, next to the AI number, an honest one-line status ("示範模式" / "模型辨識力不足，僅供參考" / no caption when healthy).
- **Expert depth path**: the existing numeric score bars (trend/momentum/volatility) remain, now each with a short caption of what the sub-score measures; the raw AI % remains for those who want it.

## 3. Acceptance Criteria
1. **[FROM-SOURCE]** `V4StockDetailService.get_stock_detail()` (`backend/services/v4_stock_detail_service.py`) additively includes `model_health` (from `core.ai.get_model_health()` → `{status, version, message}`) in BOTH code paths (cached-DB path and recompute path). No other field changes; `ai_probability` stays honest-nullable.
2. **[FROM-SOURCE]** `ScoreBreakdown` qualifies the AI number by `model_health`: when `status !== 'ok'`, render the honest `model_health.message` (or a short chip "示範模式 · AI 未訓練" for `unavailable`, "AI 辨識力不足，僅供參考" for `degraded`) adjacent to the probability/N-A. When `ok`, no caption. The number/N-A itself is never fabricated or hidden.
3. **[FROM-SOURCE]** `ScoreBreakdown` surfaces an "explainable signals" section: for each fired flag in `signals` (squeeze / golden_cross / volume_spike) show a plain-language chip; and each of trend/momentum/volatility bars gains a one-line caption of what it measures. Signals that did not fire are simply absent (no fabricated "signal").
4. **[FROM-SOURCE]** Honesty guards: signals are framed as **contributing technical factors, NOT a validated per-signal win-rate** (a short note says so); no 飆股/guaranteed-profit framing; the AI probability is never presented as reliable when `model_health` says otherwise. (Per-signal backtested hit-rate is explicitly out-of-scope — it would need per-combo backtesting; deferred, not faked.)
5. **[FROM-SOURCE]** Tests: backend — detail response includes `model_health` in both paths (present-ok / degraded / unavailable). Frontend — `ScoreBreakdown` renders the health qualifier per status (ok → none; degraded/unavailable → honest caption), renders fired-signal chips + sub-score captions, and never fabricates a value. Full backend + frontend suites green; production build passes.

## 4. Non-goals
- No new ML, no model retraining, no change to score computation.
- No per-signal backtested hit-rate (deferred — not fabricated).
- No new endpoint (model_health rides on the existing detail response).
- No change to `signals` semantics — surfaced as-is.

## 5. Constraints
- **Additive & reversible**: one additive field on the detail response + ScoreBreakdown UI; existing behavior untouched.
- **Honesty-first**: the whole point is to make the score honest and legible; when the model is degraded/unavailable, that MUST be visible at the point the AI number is shown.

## 6. API / Data Contract
```
GET /api/v4/stock/{ticker}  (existing) response gains:
  "model_health": { "status": "unavailable"|"degraded"|"ok", "version": str, "message": str }
```
`ScoreBreakdown` props gain: `signals?: {squeeze,golden_cross,volume_spike}` and `modelHealth?: {status,message}`.

## 7. File Relationship
EXTENDS the candidate/detail surface; relates to `docs/specs/ui-model-state-disclosure.md` (model_health) and `docs/specs/transparency-panel.md` (same honest primitive, different surface). Reuses `core/ai/get_model_health`.
