---
status: shipped
title: One-Command Launch + Single-Port Served Frontend
source: external
source_doc: _product-backlog.md (Directly-Usable v1, #1)
created: 2026-06-20
frozen: 2026-06-20
shipped: 2026-06-20
primary_domain: none
secondary_domains: []
---

# One-Command Launch + Single-Port Served Frontend

## Goal
A fresh clone reaches a running, populated dashboard at a SINGLE URL (`http://localhost:8000`) with ONE command — eliminating the current mandatory two-terminal, two-port setup (Vite dev `:5173` + backend `:8000`) that makes the project read as an unfinished developer scaffold.

## Background (current state)
- `quickstart.ps1` / `quickstart.sh` install backend deps and seed the offline demo, then instruct the user to run `cd frontend/v4 && npm run dev` (Vite dev server on `:5173`) in a second terminal alongside `python backend/main.py` (`:8000`).
- The backend `GET /` (`backend/main.py:86-97`) already tries to serve `frontend/v4/dist/index.html`, and `/assets` is mounted from `frontend/v4/dist/assets` (`backend/main.py:80-83`) — but **quickstart never runs `npm run build`**, so `dist/` does not exist on a fresh clone and the single-port `:8000` path returns 404. The two-terminal Vite path is therefore the only working route.

## Acceptance Criteria
1. `quickstart.ps1` and `quickstart.sh` build the frontend (`npm ci && npm run build` in `frontend/v4`) so `frontend/v4/dist/` exists, enabling the backend to serve the built SPA at `http://localhost:8000`.
2. A single launch command starts the backend serving the built frontend on `:8000` with no separate Vite dev server required for normal use (enhance `start.ps1`/`start.bat`/`start.sh`, or add a launch step to quickstart).
3. `.ps1`, `.bat`, and `.sh` script variants stay at functional parity (Windows + POSIX).
4. The backend serves a SPA deep-link fallback: any non-`/api`, non-asset GET path returns the built `index.html` so client-side routes (e.g. react-router `/backtest`) and page refreshes do not 404. The fallback MUST NOT shadow `/api/*` or `/assets/*`.
5. `README.md` quickstart is reordered: the offline single-URL path is primary; the legacy full yfinance sync is demoted under an explicit "optional / slow" heading.
6. The existing two-terminal Vite dev workflow remains available for contributors (additive change; not removed — preserves existing behavior per engineering_guardrails §2.2).

## Non-goals
- Docker packaging (backlog #6), data-sync acceleration (#4), real-AI first-run (#5), demo-data swap (#2), and any UI redesign (#3).
- Production deployment / hosting (explicitly out of scope — product is self-install).
- Changing the demo dataset or AI behavior (AI stays N/A; honesty-first unchanged).

## Constraints
- **Honesty-first**: AI probability remains N/A on a fresh clone (no model bundled). This feature changes launch/serving only — not data or model behavior.
- **Small & reversible**: additive only — must not break the existing dev (`npm run dev`) workflow; rollback = revert the script/serving changes.
- **Cross-platform**: Windows (PowerShell/`.bat`) and POSIX (`.sh`) parity is mandatory; the maintainer is on Windows.
- **Reuse**: build on the existing `backend/main.py` static-serving code path (`GET /` + `/assets` mount) — do not rewrite the server.

## API / Data Contract
- No API endpoint changes. Static-serving behavior only: `GET /` and a new SPA catch-all fallback serve the built `index.html`; `/assets/*` serves built assets; `/api/*` and existing routers (`market`, `stock`, `sync`, `system`) are unaffected. The catch-all fallback MUST be registered so it does not shadow `/api/*` or `/assets/*`.

## File Relationship
EXTENDS docs/specs/onboarding-quickstart.md
