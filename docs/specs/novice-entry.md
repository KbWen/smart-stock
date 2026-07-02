---
status: frozen
module: novice-entry
version: 1.0.0
source: user-directed (Honest Research Workbench epic #4)
source_doc: _product-backlog.md
created: 2026-07-02
---

# Novice Entry — A Good Starting Destination

Honest Research Workbench epic **#4**. Gives a casual "just want to invest" user an honest, guided starting point on the Dashboard: what this tool is (and is NOT), what the numbers mean, the current honest system state, and where to go next — dismissible so experts aren't slowed. This is the epic's progressive-disclosure constraint made into a concrete entry point. Frontend-only; no backend, no data/ML change.

## 1. Goal
- Orient a novice in plain language before they misread a technical score as a "buy tip": state honestly that this is a **research workbench, not investment advice / not a tipster**, and that the AI may be unavailable/degraded.
- Provide a short guided map to the four areas (candidates, 選股雷達, Strategy Lab/回測, 系統透明度) with a one-line "what you'd do there".
- Surface the current honest state (示範模式 when the model is unavailable) at the entry point.

## 2. Progressive Disclosure (epic cross-cutting constraint)
- **Simple default path**: on first visit the guide is shown; a novice reads plain-language orientation + honest expectations + guided links. No jargon required.
- **Expert depth path**: a one-click **dismiss** hides it and the choice is remembered (`localStorage`), so returning experts land straight in the full dashboard. A small "顯示新手導引" affordance can re-open it.

## 3. Acceptance Criteria
1. **[FROM-SOURCE]** A `GettingStarted` panel renders at the top of the Dashboard containing: (a) a one-line honest positioning ("誠實的台股研究工作台，不是投顧、不提供買賣建議"); (b) an honest expectations note (technical scores are not guarantees; AI probability may be N/A/示範模式 — links to 系統透明度); (c) guided quick-links (via react-router) to the candidate list, 選股雷達 (/indicators), AI 回測 / Strategy Lab (/backtest), 系統透明度 (/transparency), each with a one-line purpose.
2. **[FROM-SOURCE]** Dismissible + remembered: a close control hides the panel and persists the choice in `localStorage` (e.g. key `novice_guide_dismissed`); on next load a dismissed guide stays hidden. A small, unobtrusive "顯示新手導引" toggle re-opens it (clears the flag). Reads of `localStorage` are guarded (no crash in SSR/blocked-storage).
3. **[FROM-SOURCE]** Honest state at entry: when `model_health.status === 'unavailable'`, the panel shows a "示範模式 · AI 未訓練" note (reusing the existing signal) so a novice knows the AI numbers are absent by design, not broken.
4. **[FROM-SOURCE]** Honesty guards: no 飆股/guaranteed-profit/收益 framing; the panel never implies the app tells you what to buy; reuses the existing dark-glass design system (no new visual language).
5. **[FROM-SOURCE]** Tests: the panel renders its honest positioning + guided links; dismiss hides it and sets the flag; a pre-set dismiss flag keeps it hidden (with the re-open toggle present); the 示範模式 note shows only when model unavailable. Frontend suite green; production build passes.

## 4. Non-goals
- No backend change, no new endpoint, no data/ML change.
- No multi-step interactive tour/overlay library (a single static panel, not a coach-marks tour).
- No account/persistence beyond `localStorage`.

## 5. Constraints
- **Additive & reversible**: one component + a Dashboard mount; existing dashboard untouched when dismissed.
- **Honesty-first**: the entry's whole job is to set correct expectations; it must never oversell.
- Storage access guarded (try/catch) so a blocked/absent `localStorage` degrades to "always show", never a crash.

## 6. API / Data Contract
None (frontend-only). Consumes the existing `model_health` already available on the Dashboard via `useDashboardData`.

## 7. File Relationship
INDEPENDENT (new Dashboard component). Relates to `docs/specs/honest-first-run-ux.md` (first-run legibility) and `docs/specs/transparency-panel.md` (links to it for "what the system knows").
