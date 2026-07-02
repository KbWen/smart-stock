---
status: frozen
module: transparency-panel
version: 1.0.0
source: user-directed (Honest Research Workbench epic #2)
source_doc: _product-backlog.md
created: 2026-07-02
---

# Transparency Panel — "What Does The System Actually Know?"

Honest Research Workbench epic **#2**. A first-class, read-only view that makes the project's differentiator (transparency) visible: how much data the system has, and exactly what the AI model does and does not know — aggregating **existing, already-honest signals** into one place. No new data, no ML change, no persistence.

## 1. Goal
- Give any user (novice or expert) a single honest answer to "how much can I trust what this app shows me?" by surfacing **data sufficiency** and **model quality/state** together.
- Reuse the existing honest primitives — `get_model_health()`, `report_history_coverage()`, `get_history_context()`, model `oos_metrics` — so the panel can never claim more than those already do.

## 2. Progressive Disclosure (epic cross-cutting constraint)
- **Simple default path**: a short honest headline — e.g. "資料涵蓋 N 檔股票（YYYY-MM-DD ~ YYYY-MM-DD）" and a model status chip ("示範模式 · AI 未訓練" / "AI 模型辨識力不足" / "AI 已訓練 vX") keyed off `model_health.status`. A novice sees at a glance whether to trust the AI numbers, no jargon required.
- **Expert depth path**: an expandable section revealing the raw numbers — OOS accuracy / precision_strong / recall_strong / precision_buy / recall_buy, train/test sample sizes, class distribution, and coverage breakdown (tickers meeting predict vs train row thresholds). Hidden by default.

## 3. Acceptance Criteria
1. **[FROM-SOURCE]** New read-only endpoint `GET /api/transparency` aggregates (additive; changes no existing endpoint):
   - `data`: `{ universe_size, tickers_with_history, date_range:{start,end}|null, coverage:{ with_predict_rows, with_train_rows, short_count, min_predict_rows, min_train_rows } }` from `report_history_coverage()` (`core/data.py:482`) + `get_history_context()` (added in strategy-lab). **Counts only** — never return the full `short` ticker list in the payload (keep it small + honest).
   - `model`: `get_model_health()` (`core/ai/predictor.py:159`) → `{ status: 'unavailable'|'degraded'|'ok', version, message }` PLUS, when a model entry exists, `{ trained_at, samples, test_samples, class_distribution, oos_metrics }` read from `models_history.json`. When no model / no metrics, these are `null` and `status` is `unavailable` — **honest N/A, never fabricated**.
2. **[FROM-SOURCE]** Performance guards (the coverage/history scans are heavy on a full-universe DB): the endpoint's aggregate is **server-side cached with a short TTL** (≈60s; recompute only when stale) and **rate-limited** via the shared `backend/limiter.py` limiter (e.g. `10/minute`). One cache miss recomputes; concurrent misses do not each rescan.
3. **[FROM-SOURCE]** Frontend first-class "系統透明度 (System Transparency)" view on a new `/transparency` route with a sidebar nav entry, reusing the existing dark-glass design system + `ModelHealthBanner`/`Tooltip` (no new visual language). Renders the §2 simple headline always; the expert numbers behind an expand toggle. Honest empty/error/loading states (no fabricated numbers on failure).
4. **[FROM-SOURCE]** Honesty guards: every model metric is shown with a plain-language caption (novices won't hover); a `status!=='ok'` state shows the existing honest `model_health.message`; OOS metrics are labeled as **out-of-sample on the training universe, not a forward guarantee** (consistent with `ml-label-oos-evaluation.md`); N/A stays visibly N/A.
5. **[FROM-SOURCE]** Tests: backend — endpoint shape with model present / absent (honest nulls), counts-only (no `short` list leak), cache hit avoids recompute, rate-limit tier present. Frontend — simple headline renders for each `model_health.status`; expert numbers hidden until expanded; honest N/A when model unavailable; no fabricated value on error. Full backend + frontend suites green; production build passes.

## 4. Non-goals
- No new data collection, no ML training/label/feature change, no model retraining.
- No new persistence (read-only aggregation of existing sources).
- No per-ticker coverage drill-down UI (counts only; per-ticker lives elsewhere).
- No changing `get_model_health` / `report_history_coverage` semantics — consume them as-is.

## 5. Constraints
- **Additive & reversible**: one new endpoint + one new page + nav entry; existing endpoints/pages untouched. Rollback = remove them.
- **Runtime**: coverage/history queries are full-ish scans → MUST be cached + rate-limited (AC2); never run per-render uncached.
- **Honesty-first**: the panel can only surface what the underlying honest primitives report; when they say N/A, the panel says N/A.

## 6. API / Data Contract
```
GET /api/transparency   (cached ~60s, rate-limited)
 -> {
   "data": { "universe_size": int, "tickers_with_history": int,
             "date_range": {"start": str, "end": str} | null,
             "coverage": { "with_predict_rows": int, "with_train_rows": int,
                           "short_count": int, "min_predict_rows": int, "min_train_rows": int } },
   "model": { "status": "unavailable"|"degraded"|"ok", "version": str, "message": str,
              "trained_at": str|null, "samples": int|null, "test_samples": int|null,
              "class_distribution": {"hold":num,"buy":num,"strong":num}|null,
              "oos_metrics": {"accuracy":num,"precision_strong":num,"recall_strong":num,
                              "f1_strong":num,"precision_buy":num,"recall_buy":num}|null }
 }
```

## 7. File Relationship
INDEPENDENT (new endpoint + page). Consumes: `core/ai/predictor.py:get_model_health` (relates to `docs/specs/ui-model-state-disclosure.md`), `core/data.py:report_history_coverage` (relates to `docs/specs/listed-otc-data-completeness.md`), `core/data.py:get_history_context` (from `docs/specs/strategy-lab.md`); reuses OOS framing from `docs/specs/ml-label-oos-evaluation.md`.
