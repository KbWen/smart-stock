---
status: frozen
module: reproducible-reference
version: 1.0.0
source: user-directed (Honest Research Workbench epic #5)
source_doc: _product-backlog.md
created: 2026-07-02
---

# Reproducible Reference Layer — the Honest Pipeline in One Command

Honest Research Workbench epic **#5** (final feature). Packages the end-to-end
`data → label → train → backtest → eval` flow into a one-command map + a
walkthrough doc, so the secondary audience (developers / quant learners) can
**read AND reproduce** the mechanism. Reuses existing tools; adds no runtime
behavior to the app and changes no ML/data.

## 1. Goal
- Give a developer a single entry point that documents the whole honest pipeline, maps each stage to its real code, and can run the offline-demo stages that genuinely work — with the honesty caveat (small data → degenerate model) at every stage.
- Provide a readable walkthrough (`docs/REPRODUCE.md`) that a learner can follow.

## 2. Progressive Disclosure (epic cross-cutting constraint)
- **Simple default path**: `python scripts/reproduce_pipeline.py` prints the pipeline **map** (5 stages, what each does, the real code, the run command) with zero side effects and zero heavy imports — a novice-developer can read the whole shape at a glance.
- **Expert depth path**: `--run` executes the fast/robust stages in-process (data seed + net-of-cost backtest on demo data) and reports the heavier opt-in stages (label/train/eval) with their commands; the doc gives the full detail for running the real full-universe pipeline.

## 3. Acceptance Criteria
1. **[FROM-SOURCE]** `scripts/reproduce_pipeline.py` exposes `reproduce_pipeline(run=False, stage_fns=None)` — pure orchestration with **injectable** stages — plus a `main()`/CLI. Default (`run=False`) prints the map and returns `{ran:False, stages:[...canonical order...], caveat}` with **no side effects and no heavy imports**.
2. **[FROM-SOURCE]** `--run` executes stages IN canonical order (`data, label, train, backtest, eval`) via `stage_fns`; the default wiring auto-runs only the robust stages (data seed → `get_history_context`; `run_time_machine` backtest) and marks label/train/eval as honestly-not-auto-run (`auto_ran:False` + the manual command) rather than faking them. A failing stage is recorded (`{error:...}`) and the run continues (honest, not raised).
3. **[FROM-SOURCE]** The honesty **caveat** (small data → degenerate model; ~1000+ rows/ticker and ~92+ ticker OOS floor; model_health discloses weak models) is present in the map output, the `--run` output, and the returned summary.
4. **[FROM-SOURCE]** `docs/REPRODUCE.md` walks through all five stages, each pointing at the REAL code + the one command, with the honesty contract up front and links to `ml-label-oos-evaluation.md`, `DATA_INTEGRITY.md`, and `/transparency`.
5. **[FROM-SOURCE]** Tests: canonical stage order; map-only default has no side effects and returns the caveat; injected stages run in order; a stage failure is reported honestly and the run continues. Full backend + scripts suites green.

## 4. Non-goals
- No new app runtime behavior, no endpoint, no ML/label/data change.
- The default does NOT auto-train (train is heavy + degenerate on demo) — it is reported honestly with its command, not executed silently.
- No CI job that runs the full real pipeline (documented as manual/opt-in).

## 5. Constraints
- **Additive & reversible**: one script + one doc + tests. Rollback removes them.
- **Honesty-first**: never present demo/small-data results as production quality; the caveat is mandatory at every surface; failures are reported, never hidden.
- Default path must have zero heavy imports / side effects (safe to run anywhere).

## 6. API / Data Contract
None (a script + doc). `reproduce_pipeline(run, stage_fns)` returns
`{ran: bool, stages: list|dict, caveat: str}`.

## 7. File Relationship
INDEPENDENT (new script + doc). Reuses `scripts/seed_demo.py`, `scripts/fast_backfill.py`, `backend/train_ai.py`, `backend/backtest.py:run_time_machine`, `scripts/eval_label_modes.py`, `core/ai/label_analysis.py`. Relates to `docs/specs/ml-label-oos-evaluation.md` (OOS honesty) and `docs/specs/transparency-panel.md` (what the running system knows).
