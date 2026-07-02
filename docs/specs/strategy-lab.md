---
status: frozen
module: strategy-lab
version: 1.1.0
source: user-directed (2026-07-02 natural-language)
source_doc: _product-backlog.md (Honest Research Workbench epic, #1)
created: 2026-07-02
amended: 2026-07-02 (v1.1.0 — folded in 3-agent review panel: correctness contracts, security enforcement, novice-honesty UX)
---

# Strategy Lab — Saveable & Comparable Backtest Workbench

Flagship feature of the Honest Research Workbench epic. Adds a **persistence + comparison layer** on TOP of the already-shipped backtest engine (`backend/backtest.py:run_time_machine`, `GET /api/backtest`), without changing backtest math or ML. Users name/save/compare "strategies" (bundles of existing backtest params) side-by-side with honest net-of-cost metrics. Value comes from the user's own strategy — needs no model improvement.

## 1. Goal
- Let a user save a named **strategy** = a complete, reproducible bundle of the existing backtest parameters (`target_gain`, `stop_loss`, `holding_days`, `commission_rate`, `tax_rate`, `slippage_rate`, **and `days_ago`** — the back-test-as-of window, which materially changes results) and re-run it any time without re-entering sliders.
- Let a user **compare** up to 4 saved strategies side-by-side (equity curve + honest net-of-cost summary) to reason about trade-offs — WITHOUT the UI implying a "winner to buy."
- Satisfy the epic's **progressive-disclosure constraint** (§2).

## 2. Progressive Disclosure (epic cross-cutting constraint)
- **Simple default path**: on first open (no saved strategies) the Lab shows 2–3 seeded **preset** strategies and **auto-highlights one as "Balanced (建議起點 / suggested starting point)"** so a novice has a single next action, not a 3-way judgment call (preset names describe the rule's width, never a return promise). Each summary metric is shown with a **one-line plain-language interpretation rendered inline** (NOT hover-only — a novice won't know to hover), e.g. Sharpe → "報酬相對波動的穩定度（越高越穩，非獲利保證）".
- **Expert depth path**: this feature adds **no new expert parameter surface** — it reuses the existing sliders already gated behind the `/backtest` "展開變更" toggle. The new expert value is purely **save / name / manage** many strategies. State this plainly (no over-claimed new depth).

## 3. Acceptance Criteria
1. **Persistence (local-only).** New SQLite table registered in `core/data.py:init_db()` alongside the existing `CREATE TABLE IF NOT EXISTS` statements (NOT lazily in the CRUD module): `strategies(id INTEGER PK, name TEXT NOT NULL UNIQUE, params TEXT/JSON, notes TEXT NULL, created_at, updated_at)`. Uniqueness is a **DB constraint** (`NOT NULL UNIQUE`), not read-then-write. `storage.db` only — never written off-device. Verified-and-guarded: `seed_demo` / `recalculate_all` touch only `stock_*` tables and MUST NOT clear `strategies`; no `DROP TABLE strategies` anywhere. A guard test asserts this.
2. **CRUD API with real validation (additive, does not alter `/api/backtest`).**
   - `GET /api/strategies` → list.
   - `POST /api/strategies` / `PUT /api/strategies/{id:int}` → a **Pydantic `StrategyParams` model** validates the JSON `params` with the **exact same numeric bounds as `GET /api/backtest`** (`target_gain`/`stop_loss` `ge=0.01,le=0.50`; `holding_days` `int, ge=1,le=90`; `commission_rate`/`tax_rate`/`slippage_rate` `ge=0.0,le=0.05`; `days_ago` `int, ge=1`). Reject NaN/Infinity, missing keys, wrong types, and unknown extra keys with a structured 4xx — **no silent coercion**. PUT is partial (`name?`/`params?`/`notes?`) but MUST validate the **merged** record, not only the changed field.
   - `DELETE /api/strategies/{id:int}`.
   - Unique-name collisions surface via caught `sqlite3.IntegrityError` → 409, generic message. **No `str(exc)` in any response** (must not regress `api-security-hardening.md` AC3/AC11). `{id}` typed `int` (free 422 + safe parameterization); all SQL uses `?` placeholders (never f-string interpolation).
3. **Compare API (bounded, throttled, honest).** `GET /api/strategies/compare?ids=<comma-list>`:
   - Server-side validation **before any DB/backtest work** (mirror `get_v4_meta` pattern): reject non-integer tokens, empty `ids=`, and `len(ids) > 4` with 422; dedupe ids (comparing a strategy to itself is rejected as redundant).
   - Rate-limited via the existing `backend/limiter.py` `Limiter` with a **stricter tier than backtest** (`_RATE_COMPARE = "5/minute"`, vs backtest's `20/minute`, since each call is up to 4× the cost).
   - Runs the **existing** `run_time_machine()` once per id (unchanged), each with a **per-id timeout**; a timed-out or failing id returns an honest error slot with a **fixed generic message** (e.g. "backtest failed for this strategy") — never a fabricated result and never raw exception text.
   - Returns **`summary` only** (net-of-cost metrics) per strategy — `top_picks` is dropped from compare (or capped ≤5) to avoid over-returning a payload the side-by-side view doesn't render.
   - Response also carries the **data-sufficiency context** used (see AC6): sample size + date range.
4. **Honest preset seeding.** First run seeds 2–3 presets (e.g. "Tight / Balanced / Wide" — describe rule width, never an outcome), idempotent and **keyed on the unique `name`** so re-running on every app start never duplicates or errors.
5. **Frontend Strategy Lab on `/backtest`.** Simple path (auto-highlighted suggested preset → run → side-by-side compare of ≤4 strategies' equity + summary with inline plain-language metric interpretations) AND expert path (existing sliders → "Save as…" named strategy → manage rename/delete). Reuses the existing dark-glass design system + chart components (no new visual language). Progressive-disclosure AC (§2) demonstrably satisfied.
6. **Honesty guards (compare must not imply a winner).**
   - Every metric carries the already-shipped net-of-cost honesty labels (`backtest-metric-label-honesty.md`).
   - The compare view MUST show, inline near the table, a disclaimer: **過去回測表現不代表未來；小幅差異可能落在雜訊內** ("past backtested performance is not a promise of future results; small differences may be within noise").
   - The compare view MUST surface **data-sufficiency context**: sample size (tickers / rows) and the date range the backtest is based on — so a user sees whether there is even enough data to compare meaningfully (pulls the critical sliver of epic #2 Transparency into #1).
   - **No comparative green/red color-coding ACROSS strategy columns** (which would visually crown a winner); color-code only within a single strategy's own thresholds, if at all.
   - No 飆股/guaranteed-profit framing; no ML probability presented as a prediction in this rules-based surface; strategies never leave the device. A light client-side warning (non-blocking) if a user-entered strategy name contains guarantee/hot-stock keywords.
7. **Tests.** Backend — CRUD happy/invalid/duplicate, `StrategyParams` range + NaN/Inf/missing/extra-key rejection, PUT-merged validation, compare (multi-id, dedupe, >4 → 422, non-int → 422, per-id error slot with no leak), rate-limit tier present, idempotent seed, and the seed/recalc-untouched guard (AC1). Frontend — save-as + compare interaction, suggested-preset highlight, inline metric interpretation present, no cross-column winner coloring. Full backend + frontend suites green; production build (`tsc -b && vite build`) passes.

## 4. Non-goals
- No change to backtest mathematics, sniper rules, ML labels/features/training, or `run_time_machine`'s existing behavior/signature.
- No portfolio-weight optimization (Markowitz etc.).
- No live trading, order execution, or money movement.
- No cloud sync, sharing, multi-user accounts, or any off-device transmission of strategies (local-only).
- No new heavy frontend windowing/dependency bloat.

## 5. Constraints
- **Additive & reversible**: new table + new endpoints + extended `/backtest` page; existing endpoints and math untouched. Rollback = remove new files + router registration; the `strategies` table is inert if unused.
- **Local-only persistence**: `storage.db` (gitignored). A fresh clone / Docker start has no user strategies until saved; presets seed on first run. Full DB wipe loses user strategies (acceptable for a local tool; documented).
- **Reproducibility (honest scope)**: `run_time_machine` uses `random.seed(42)`, but its candidate pool is sampled from `get_all_tw_stocks()` whose ORDER varies by source (live TWSE / twstock fallback / file cache) and cache expiry — so compare is **reproducible only within a stable universe-cache window**, not guaranteed across restarts. Do NOT claim absolute determinism.
- **Honesty-first**: consistent with the epic guards and prior honesty specs; no fabricated numbers.

## 6. API / Data Contract
```
GET    /api/strategies                       -> [{id,name,params,notes,created_at,updated_at}]
POST   /api/strategies      body {name,params,notes?}   -> {id,...} | 4xx {error}
PUT    /api/strategies/{id:int} body {name?,params?,notes?} -> {id,...} | 4xx {error}
DELETE /api/strategies/{id:int}              -> {ok:true}
GET    /api/strategies/compare?ids=1,2,3  (≤4, deduped, throttled 5/min)
        -> {context:{sample_size, date_range}, results:[{id,name,summary} | {id,error:"<generic>"}]}
```
`params` schema = `{target_gain, stop_loss, holding_days, commission_rate, tax_rate, slippage_rate, days_ago}` (same ranges/defaults as `GET /api/backtest`; `days_ago` = backtest as-of window). `summary` schema = existing backtest summary (`avg_net_return`, `net_win_rate`, `sharpe_ratio`, `worst_drawdown`, `net_profit_factor`, …) unchanged. Compare returns `summary` only (no `top_picks`).

## 7. File Relationship
EXTENDS `docs/specs/backtest-and-performance-opt.md` (reuses `run_time_machine` + `/api/backtest` params/summary unchanged); relates to `docs/specs/backtest-metric-label-honesty.md` (net-of-cost honesty labels) and `docs/specs/api-security-hardening.md` (no-leak + rate-limit baseline the new endpoints must uphold); pulls a minimal transparency sliver (sample size + date range in compare) ahead of epic #2 Transparency Panel.
