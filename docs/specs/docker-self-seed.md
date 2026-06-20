---
status: frozen
title: Docker Self-Seed + .dockerignore
source: external
source_doc: _product-backlog.md (Directly-Usable v1, #6)
created: 2026-06-20
frozen: 2026-06-20
shipped: 2026-06-20
---

# Docker Self-Seed + .dockerignore

## Goal
`docker compose up` (or `docker run`) yields a **populated** dashboard, not an empty one. Today the image lacks the demo fixture + seed script and the CMD only serves — so a container starts with an empty DB and a blank dashboard until a slow network sync. Self-install via Docker should "just work".

## Background (verified 2026-06-20)
- `Dockerfile` COPYs `core/`, `backend/`, `fetch_stocks.py`, built `dist` — but NOT `data/demo/` or `scripts/`; `CMD ["python","backend/main.py"]` has no seed step.
- No `.dockerignore` → the build context ships `node_modules`, `.git`, `.agentcortex`, a dev `storage.db`, models, etc.

## Acceptance Criteria
1. `Dockerfile` COPYs `scripts/` and `data/demo/` into the image so the offline demo fixture + `seed_demo.py` are present (covers `docker run` with no bind mount; `docker compose up` also gets the demo from the host repo via the `./data` mount).
2. A `docker-entrypoint.sh` seeds the offline demo (idempotent; `seed_demo` skips if the demo tickers already exist) BEFORE serving, then `exec`s `python backend/main.py`; the `Dockerfile` uses it as `ENTRYPOINT` (CR-stripped + executable). Seed failure is non-fatal (still serves).
3. A `.dockerignore` excludes the local `storage.db*`, model files (`*.pkl`/`.sha256`/`.sig`), `node_modules`, built `dist`, `.git`, governance/dev dirs and caches — while KEEPING `data/demo/` copyable.
4. Honesty preserved: no model is bundled (`*.pkl` excluded) → AI stays N/A in the container; the demo data is real (from #2). No data/model behavior change.
5. A regression-guard test asserts the `Dockerfile` COPYs the seed script + demo and uses the seed-then-serve entrypoint, and that `.dockerignore` excludes the local DB/models but not the demo.

## Non-goals
- Building/publishing an image in CI; hosted deployment (out of scope — self-install only); changing the app, ports, or the bind-mount model in `docker-compose.yml`.

## Constraints
- Honesty-first: never bake a model or a dev DB into the image. Small & reversible; app code untouched (Dockerfile / entrypoint / .dockerignore only). **Docker is NOT available in this environment**, so the image is verified by inspection + the offline `seed_demo` test + a Dockerfile/entrypoint guard test — not a live build.

## File Relationship
EXTENDS docs/specs/onboarding-quickstart.md
