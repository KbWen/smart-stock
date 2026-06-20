---
status: raw
title: Raw Spec Intake — Directly-Usable v1
source: natural-language + in-session 4-expert brainstorm
received: 2026-06-20
---

> Transient intake artifact. Decomposed into `_product-backlog.md` (Directly-Usable v1). To be deleted by `/ship` once all v1 features are Shipped or Cancelled.

## User Request
"檢查+分析專案。我們要提供使用者一個至少可以直接使用的版本。可能讓不同的專家來頭腦風暴或是研究?"

Goal: provide users **at least a directly-usable version** of the Smart Stock (智慧選股) Taiwan-stock AI dashboard.

## Locked User Decisions (in order made)
1. **Scope** = Path A (Honest Demo v1: frictionless + legible first run) **+** Path C (Real-AI first run), done thoroughly.
2. **NO public hosting** — "這是給大家自己拿去安裝使用的" → product is distributed for users to **self-install**, not a hosted service.
3. **Full universe, not a toy subset** — "為啥不全部股票" → the real product targets the full ~1,800-stock TWSE/TPEX universe. The small bundled demo fixture stays small only because of git repo-size limits (full history ≈ 100MB+ committed) and is reframed as an instant offline preview, NOT the real dataset.
4. **Data distribution = accelerated live sync (option C)** — "C 加速現場同步(授權最乾淨)". Keep "each user fetches their own data on-machine" (no redistribution, cleanest licensing) but switch full-universe history backfill from per-stock yfinance to authoritative TWSE/TPEX per-day bulk endpoints to cut the ~15-min first-run wall. (Rejected: A bundled prebuilt-snapshot Release download — faster but raises third-party market-data redistribution/ToS concerns the user chose to avoid.)

## Hard Constraints
- Honesty-first (shipped value): no model bundled (`.pkl` gitignored) → AI = N/A on fresh clone; no mock data; honest loading/error states; `get_model_health`/`ModelHealthBanner` disclose degraded/unavailable. Do NOT bundle a weak/degenerate model. `MODEL_SIGNING_KEY` empty → an unsigned bundled model is rejected by design.
- Small, reversible changes; no unauthorized refactoring; preserve existing behavior (e.g., keep the dev `npm run dev` workflow available).
- Cross-platform: Windows (PowerShell/.bat) + POSIX (.sh) script parity (maintainer is on Windows).
- `LABEL_MODE=atr` stays (shipped default); no further label/model R&D in this epic.

## Confirmed Gaps (grounded in repo, from 4-expert brainstorm)
1. **Docker = empty dashboard**: `Dockerfile` does not COPY `data/demo/` or `scripts/`; `CMD` is bare `python backend/main.py` (no seed); `docker-compose.yml:8` `./data:/app/data` shadows any baked data. No `.dockerignore`. → backlog #6.
2. **Forced two-terminal**: `quickstart` never runs `npm run build`; backend `GET /` (`backend/main.py:86-97`) serves `frontend/v4/dist/index.html` but `dist/` is never built → `:8000` 404s; users stuck on Vite dev `:5173` + backend `:8000`. → backlog #1.
3. **Demo dataset = 6 obscure tickers** (`data/demo/demo_prices.csv`: 1240/1259/1264/1268/1336 + 2330); only 5 trainable (2330 has 180 rows < `MIN_TRAIN_ROWS=260`, `core/config.py:32`). Looks broken; too small to train a non-degenerate model. → backlog #2.
4. **Wall of AI N/A reads as broken, not honest**: no inline framing; scattered English in an otherwise 繁中 UI (`Layout.tsx` nav, `SniperCard.tsx` "No Stock Selected", `StockList.tsx` empty-state, AI Analyst fallback in `backend/services/v4_stock_detail_service.py:204`); the prominent 同步資料庫 button silently triggers the 10–15 min full sync. → backlog #3.
5. **Real-AI first run requires data + train**: keep N/A-by-default; do NOT bundle `.pkl`; opt-in sync (full universe via #4) + `python backend/train_ai.py`. OOS-proven floor ~92 tickers where the degenerate model stops reproducing (`docs/specs/ml-label-oos-evaluation.md`); absolute precision still honestly low (0.12–0.36) → keep AI secondary + `model_health` loud. → backlog #5.
6. **Data acceleration (option C)**: history currently per-stock yfinance (`core/data.py:558`, sleep 0.5–1.5s/stock = the wall). TWSE `STOCK_DAY_ALL` already used for universe list (`core/universe_source.py:30`); per-day all-stocks backfill via a date-parameterized endpoint (e.g. TWSE MI_INDEX) means far fewer calls + authoritative source. → backlog #4.

## Expert Brief Highlights
- **Product/Adoption**: v1 user = developer/technical retail investor evaluating the repo; "directly usable" = one clone + one command → populated dashboard at one URL with real technical scores for recognizable stocks, N/A framed as honest-by-design. Biggest risk = the mandatory two-terminal dev-server launch reads as an unfinished scaffold.
- **ML/Data-Honesty**: lead with technical (Rise Score) scores; AI is a labeled secondary signal, never the hero. Do NOT commit a `.pkl` (a 5–6-ticker model is degenerate and would ship unsigned). "Universe coverage is the larger lever." Minimum non-degenerate first-run data ≈ the OOS-proven ~92+ floor.
- **DevOps/Packaging**: confirmed the Docker self-seed gap + compose volume shadowing; smallest fix = COPY demo+scripts, seed-on-boot entrypoint, add `.dockerignore`. Single-port served frontend collapses two terminals.
- **UX/First-Run**: add a "示範模式" badge, reframe N/A inline ("尚未訓練模型"), 繁中-ize scattered English, guard the sync button. Honesty (showing N/A) is a feature — make it *legible*, not hidden.
