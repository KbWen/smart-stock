---
status: frozen
title: Docs-vs-Reality Alignment
source: external
source_doc: _product-backlog.md #6 (quant-expert panel audit, finding F3 — 3/3 independent auditors)
created: 2026-09-02
updated: 2026-09-02
frozen: 2026-09-02
primary_domain: docs
secondary_domains: [market, transparency]
---

# Docs-vs-Reality Alignment

Honest Metrics epic **#6** (review-finding, P0), and the one that closes the epic's central charge.
The project's stated differentiator is transparency, yet its own integrity documentation asserts
protections the code does not provide — in two cases by presenting the *defective* code as the
mitigation.

Sequenced deliberately **last among the P0s**: #1 (settlement realism) and #2 (date-based embargo)
have now shipped, so this spec can describe behaviour that actually exists rather than being
rewritten twice.

## The false claims, each verified against the code

| # | Location | Claim | Reality |
|---|---|---|---|
| C1 | `docs/DATA_INTEGRITY.md:42` | "Chronological Leakage" is mitigated by `iloc[:split_idx - PRED_DAYS]` | That expression embargoed **rows**, not days. Measured on the real 92-ticker panel it separated train from test by **0 trading days**. Fixed by #2; the row now carries only an inline `[SUPERSEDED]` marker. |
| C2 | `docs/DATA_INTEGRITY.md:43` | "Cross-Validation Bias" is mitigated by `gap=20` | `TimeSeriesSplit`'s `gap` counts **samples**. On a stacked panel that spanned a fraction of one day. Fixed by #2; also only marked so far. |
| C3 | `docs/DATA_INTEGRITY.md:51` | "Selection Bias (backtesting only stocks that survived)" is mitigated by `random.seed(42)` + `random.sample()` | Random sampling **from a survivor-only universe** does not remove survivorship bias; it makes the sample unbiased *within* survivors. `backend/backtest.py:66` draws from `get_all_tw_stocks()` — today's listed set — and no listing/delisting dates are stored anywhere. **Still unmitigated.** |
| C4 | `docs/DATA_INTEGRITY.md:53` | "Outcome Peeking" is mitigated by forward-walk evaluation | The forward walk was correct, but the *price booked* was the session high on a win and the session low on a loss. Fixed by #1. |
| C5 | `docs/DATA_INTEGRITY.md:66-70` | Good backtest numbers come from "True Out-of-Sample generalization", and "consistent profit factors validate the lack of look-ahead bias" | A non-sequitur — consistency across `days_ago` is not a leakage test — and it contradicts the project's own recorded finding that the model is weak. `backend/backtest.py:176` also scores the **production** model, which was trained on the window being scored. |
| C6 | `README.md:237` | The 80/20 split 「完全杜絕」 data leakage | An absolute claim that was false when written and is still too strong now: the embargo is fixed, but the backtest still scores a model trained on its own window (#3), and survivorship is unmitigated. |
| C7 | `docs/project_meta/whitepaper.md:89` | Market data "is fetched with `auto_adjust=True`" as a system-wide property | False since the bulk-history path shipped: `core/bulk_history.py` writes **raw** TWSE/TPEX closes. A single ticker's series can mix both bases (deferred batch D). |
| C8 | `core/market.py:68-72` + `frontend/v4/src/pages/MarketRisk.tsx` | `risk_level` renders as 風險等級 with values "LOW RISK (BULL)" / "HIGH RISK (BEAR)", tooltip 「根據動量均值與**系統風險**評估」 | The value is computed **purely** from the share of tickers with `trend_score > 20`. No volatility, no index, no drawdown, no correlation. It is a market **breadth** reading presented as a risk assessment. |

## Goal

Make every integrity claim in the repo true of the code as it now stands, name what is still
unmitigated instead of implying coverage, and stop presenting a breadth reading as a risk level.

## Acceptance Criteria

1. `docs/DATA_INTEGRITY.md` rows C1–C4 are **rewritten**, not merely marked: each
   states what the code does today after #1 and #2. C3 is reclassified as a **known, unmitigated
   limitation** with the reason (a survivor-only universe and no point-in-time listing dates), not a
   mitigation.

2. The `## Verification` section (C5) drops both the "True Out-of-Sample
   generalization" attribution and the circular `days_ago` argument. It is replaced with a
   **falsifiable** control the reader can actually run — retrain on shuffled labels and observe the
   profit factor collapse toward 1 — and states plainly that the backtest still scores a model
   trained on the window it is scored over (backlog #3).

3. `README.md:237` no longer claims 「完全杜絕」. It states what the split now does
   (a date-based embargo of `PRED_DAYS` trading days) and links to `DATA_INTEGRITY.md` for the
   limitations that remain.

4. `docs/project_meta/whitepaper.md:89` no longer asserts `auto_adjust=True` as a
   system-wide property. It describes both ingest paths and names the mixed-basis hazard as a known
   open issue (deferred batch D).

5. `risk_level` becomes `breadth_level`, carrying a **stable machine value**
   (`BULLISH` / `NEUTRAL` / `BEARISH`) rather than a display string. The frontend maps that value to
   a Chinese label and a colour. This kills two problems at once: the false risk claim, and the
   fragile `market.risk_level.includes('HIGH')` colour matching in
   `frontend/v4/src/hooks/useDashboardData.ts:82-83` and `frontend/v4/src/pages/MarketRisk.tsx:18-21`,
   which would have failed **silently** on any wording change. The UI label becomes 多頭廣度 and the
   tooltip states the actual basis: the share of tracked tickers whose trend score exceeds 20.

6. The rename is complete, with **no compatibility alias**. `risk_level` is removed
   from `core/market.py`, `docs/API_CONTRACT.md`, both frontend consumers and their tests. Keeping a
   deprecated alias would preserve the misleading name in the surface this spec exists to correct.
   The app ships backend and frontend as one unit, so there is no split-version window.

7. Tests: a backend test asserting `breadth_level` takes each of the three machine
   values at the documented `bull_ratio` boundaries and that `risk_level` is **absent**; frontend
   tests updated to the new field and asserting the label/colour mapping. Existing market tests stay
   green.

8. No claim added by this spec may itself overstate. Every rewritten row names the
   file and line the reader can check, and anything still unmitigated is listed as such — including
   the ones this epic has not reached (#3 backtest temporal guard, #4 rotation, #5 metric
   attribution, deferred batch D).

## Non-goals

- **No new mitigations.** This spec changes documentation and one misleading label. It does not add
  survivorship handling, point-in-time universe data, or a temporal guard — those are #3 and batch D.
- **No change to how `bull_ratio` or `market_temp` are computed.** Only what the derived level is
  called and what the tooltip claims about it.
- **No rewrite of `docs/specs/ml-label-oos-evaluation.md`** — #2 already added its supersession
  warning and re-measurement.
- No change to the backtest, the trainer, or any metric.

## Constraints

- **Truth over tidiness**: where a protection does not exist, say so. A shorter honest table beats a
  complete-looking one.
- **Every claim must cite a checkable location** (`file:line` or a runnable command), so the next
  audit can falsify it rather than trust it.
- **Honesty guard** (epic-wide): nothing here may be softened to make the project look better than
  the code is.

## Domain Decisions

- **[DECISION]** A machine value plus a presentation-layer label, rather than a display string in the
  API. String matching on user-facing wording is a silent-failure mode: change the words and the
  colour logic stops working with no error anywhere.
- **[DECISION]** No compatibility alias for `risk_level`. The point of this spec is to remove a
  misleading name from the surface; keeping it available would defeat that, and the app has no
  split-version deployment window.
- **[CONSTRAINT]** `DATA_INTEGRITY.md` is an integrity claim sheet, not marketing. Any future row
  added to it must cite the code that implements it, and a row whose implementation is removed must
  become a stated limitation rather than being deleted quietly.
- **[TRADEOFF]** C6's replacement text is longer than 「完全杜絕」 and less flattering. That is the
  intended direction: the shorter claim was false.

## File Relationship

EXTENDS `docs/specs/docs-reality-sync.md` (the 2026-06-13 pass that corrected API_CONTRACT / README /
ARCHITECTURE / TESTING against the code — this is the same exercise applied to the integrity claims
the quant panel found). Depends on `docs/specs/backtest-settlement-realism.md` (#1) and
`docs/specs/date-based-train-test-embargo.md` (#2), both shipped, for the behaviour it describes.
