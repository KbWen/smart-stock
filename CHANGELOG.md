# Changelog

## [Honest Metrics] - 2026-09-02

An epic correcting 說到做不到 gaps found in the **mathematics** layer by a three-auditor quant panel
(ML methodology / backtest realism / data integrity, commissioned independently). In progress.

### Backtest numbers will change — this is a correction, not a regression

`run_time_machine` used to book a winning trade at the session **high** and a losing trade at the
session **low**. The error was one-directional: every win was credited the best print of the day no
order could have captured, every loss charged the worst print the position never actually paid.

Exits now settle where an order could have filled — a target touch at `target_gain`, a stop touch at
`-stop_loss` — with a gap exception on both sides when the bar opens straight through a barrier. **If
you kept a screenshot of a backtest, the same query will now return different figures.** The run is
seeded, so the picks are the same; the settled returns are not. Affected: `avg_return`,
`avg_net_return`, `profit_factor`, `net_profit_factor`, `sharpe_ratio`, `best_return`. Win rates are
unaffected — trade signs do not change. Max drawdown is unaffected — it measures excursion, not
settlement.

On the 92-ticker dev data the headline moved the *flattering* way (`avg_return` −1.23% → −0.72%),
because that sample was stop-heavy: correcting 11 over-punished losses outweighed correcting 3
over-credited wins. On a hit-heavy sample the sign flips. No threshold or default was changed.

`sharpe_ratio` is now `null` (shown as `—`) instead of `0.00` when the standard deviation of net
returns is undefined or exactly zero — a single pick, or every settled trade landing on the same
barrier. The old code fabricated a zero there. On the dev data at shipped settings this is in fact
the *only* number the release moves, because the honestly-weak model admits one candidate that
touches no barrier.

### Your model will turn orange on upgrade. Nothing about it changed.

`get_model_health` used to return `ok` for any model whose metrics were merely non-zero. It now
returns `degraded` — with the banner and the honest message that go with it — in four cases, and
**every existing install hits at least one of them immediately**, because no history entry written
before 2026-09-02 carries the `embargo` key proving its metrics were out-of-sample.

This is a **measurement change, not a model change.** The model you have is the model you had. What
changed is that the app stopped telling you it was fine without checking.

The four causes are reported separately, because they are different facts to act on and the UI used
to assert only one of them:

- `contaminated_metrics` — the entry predates the date-based embargo, so its numbers were never
  out-of-sample. **Retrain to clear this.**
- `below_baseline` — StrongBuy precision is at or below the test-split base rate. A lift of 1.0 is
  exactly "no better than guessing at the class prevalence", and the boundary is inclusive.
- `zero_power` — the model produced no buy signal at all.
- `no_baseline` / `metrics_not_for_this_version` — the entry cannot be evaluated (missing or
  non-finite lift, or no history entry for the loaded version). These fail toward disclosure rather
  than toward `ok`.

The transparency panel now shows **both** class distributions with the split each belongs to, and
reports precision as **lift over the test-split base rate**. The distribution it used to show under
the OOS heading was the *train* split — not the denominator a reader would reasonably assume.
`models_history.json` gains `test_class_distribution`, `oos_metrics.lift_strong` / `lift_buy`, and
`oos_metrics_scope: "split_model"`, which records that the metrics describe the 80/20-split ensemble
rather than the full-data refit that actually ships. `manage_models list` gains a `Lift` column so
the CLI and the UI cannot disagree about whether a model has an edge.

**Breaking, for JSON consumers**: `/api/transparency`'s `model.class_distribution` is replaced by
`train_class_distribution` + `test_class_distribution`. No alias — an absent key is the marker that
an entry predates the measurement.

### 風險等級 is now 多頭廣度 — it never measured risk

The dashboard card and the Market page showed 風險等級 with values like "LOW RISK (BULL)", and a
tooltip claiming an assessment 「根據動量均值與系統風險」. The value is computed **purely** from the
share of tracked tickers whose trend score exceeds 20 — no volatility, no index level, no drawdown,
no correlation. It is a **breadth** reading, so it is now labelled as one.

The API field `risk_level` is renamed **`breadth_level`** and carries a stable machine token
(`BULLISH` / `NEUTRAL` / `BEARISH` / `UNKNOWN`) instead of a display string; labels and colours live
in the frontend. **No compatibility alias is kept** — keeping the misleading name available would
defeat the point. If you script against `/api/market_status`, update the field name.

Same market state, new words: 偏多 (廣度高) / 中性 / 偏空 (廣度低), with unchanged colours. The no-data state is the one exception: it was a yellow `unknown` and is now a muted `—`, so an empty database no longer looks like a neutral market reading.

### The integrity documentation now matches the code

`docs/DATA_INTEGRITY.md` asserted protections the code did not provide — in two cases by presenting
the *defective* code as the mitigation. Every row is rewritten against what the code does today, with
a runnable check where one exists and a History note where the old text was wrong.

The biggest correction: **survivorship bias is now listed as NOT MITIGATED.** The old text claimed
`random.sample()` handled it. Sampling from a universe of survivors is unbiased *within* survivors and
says nothing about the names that left — backtest results are biased upward by an unmeasured amount.

The "Verification" section used to say that consistent profit factors across `days_ago` prove there is
no look-ahead bias. That is a non-sequitur — both runs inherit the same leak. It now describes a real
control (retrain on shuffled labels; a clean pipeline collapses toward a profit factor of ~1) and
lists what is still unprotected, including that **the backtest scores a model trained on the very
window it is scored over**.

`README.md` no longer claims data leakage is 「完全杜絕」, and the whitepaper no longer asserts
`auto_adjust=True` as a system-wide property — false since the bulk-history path shipped.

### The AI's out-of-sample numbers were not out-of-sample

The training embargo was measured in **pooled rows**, not days. On a panel stacking N tickers, one
calendar day is N rows, so removing `PRED_DAYS = 20` rows removed a fraction of a day. Measured on
the real 92-ticker panel, the split separated train from test by **zero trading days** — while every
label looks forward 20 trading days. The model was scored on outcomes it had been trained on.

The embargo is now counted in trading days from the data's own calendar. Retraining will produce
**worse** numbers, which is the correct direction: on the same panel and seed, StrongBuy recall
falls 0.744 → 0.629 and precision 0.352 → 0.345.

**Your existing `oos_metrics` are stale**, in `models_history.json` and on `/transparency`. This
release does not force a retrain and does not silently rewrite them; the contamination is disclosed
in `docs/specs/ml-label-oos-evaluation.md`, whose 2026-06-13 ATR-vs-fixed table is now marked as
superseded and kept verbatim as the record of what was believed at the time.

Training now **aborts with an explicit message** if the data cannot support a clean embargo, rather
than quietly shrinking it, and the abort is visible to callers: `backend/train_ai.py` exits non-zero
and `scripts/setup_real_ai.py` reports `trained: false` and skips the recalc, so a scheduled retrain
can no longer report success with no model written. A published number that cannot be computed
honestly is worse than no model.

The cross-validation printout is diagnostic only, so when the panel is too short for it the fold
count degrades (3 → 2 → skipped with a warning) rather than failing the run — the holdout embargo,
which is the actual guarantee, is untouched either way.

Each new entry in `models_history.json` now carries an `embargo` block. **An entry without that key
predates this change and its `oos_metrics` are contaminated by construction**, which is the marker
the transparency page will need to badge them.

Honest reading of the corrected numbers: StrongBuy precision `0.3454` now sits **below** the
test-split base rate of `0.3512`. That is a move from "no skill" to "negative skill", not a slight
dip — and `get_model_health` will still call such a model `ok`, because its check predates this.
Fixing that check is the next item in this epic.

Note for anyone with a populated `models_history.json`: `backtest_30d.profit_factor` entries written
before this change are **not comparable** to ones written after, and model rotation ranks on that
field.

## [Directly-Usable v1] - 2026-06-20

A 6-feature epic making the project directly usable as a self-install product (no hosting). PRs #28–#33.

- **One-command launch + single-port served frontend** (#28): quickstart builds the UI; the backend serves the built SPA at a single URL (`http://localhost:8000`) with a react-router deep-link fallback; `start.ps1` added; the two-terminal dev workflow is preserved.
- **Credible demo dataset** (#29): 15 recognizable large-cap TWSE tickers (real prices) via a reproducible `scripts/gen_demo_fixture.py`.
- **Legible honest first-run UX** (#30): Traditional-Chinese nav/states, a "示範模式" demo badge from `model_health`, AI N/A reframed with tooltips, sync-button confirm.
- **Accelerated full-universe sync** (#31): `core/bulk_history.py` + `scripts/fast_backfill.py` backfill the whole universe from official TWSE/TPEX per-day bulk endpoints (raw prices); yfinance per-stock remains the fallback.
- **Opt-in real-AI first-run** (#32): `scripts/setup_real_ai.py` chains backfill → gate → train → recalc; honest gating skips a degenerate train (AI stays N/A); weak models are disclosed by `model_health`.
- **Docker self-seed** (#33): the image bundles the demo + seed script and seeds before serving (`docker-entrypoint.sh`); new `.dockerignore`; no model/dev-DB baked (AI stays N/A in-container).
- **Honesty-first preserved throughout**: no bundled model, real data only; backend 227 tests passing.

## [Unreleased] - 2026-03-27

### ✨ 視覺衝擊力升級 Phase 1 — 買入信號視覺化 + AI 計數動畫

- **PriceSignalChart**: 每張 SniperCard 新增 90 天收盤價折線圖，Recharts ComposedChart + ReferenceDot 標注三種 AI 訊號（⚡Squeeze 黃、✦Golden Cross 藍、▲Volume Spike 紫）
- **AI Probability count-up**: ScoreBreakdown 的 AI 勝率數字加入 requestAnimationFrame 計數動畫（ease-out cubic，~1 秒），強化 AI 計算感
- **History Endpoint**: 新增 `GET /api/v4/stock/{ticker}/history`，回傳 90 天 OHLC + 訊號陣列，獨立 60s in-memory cache
- **Race condition 保護**: PriceSignalChart 走 `useCachedApi (enabled flag)` 模式，快速切換 ticker 不殘留舊資料
- **Tests**: Backend 143/143 ✅ Frontend 38/38 ✅ Production build ✅

## [5.0.0] - 2026-03-05

### 🛡️ Runtime v5 Anti-Drift & Concurrency Release

- **Gate Engine & Handshake**: Implemented a hard-path enforcement overlay for `plan`, `ship`, and `implement` workflows. High-risk tasks now require explicit `PROCEED-<STAGE>:<branch>` contextual handshakes to continue.
- **Skill Safety Guardrails**: Established strict precedence (`AGENTS.md` > `workflows` > `skills`) to prevent Antigravity semantic skills from hijacking execution loops.
- **Multi-Session Concurrency**: Added `Owner` and `Session` metadata requirements to Work Logs. `/bootstrap` now checks for concurrent edits to prevent collisions.
- **Legacy Migration Safety**: Introduced the `/audit` workflow for read-only system mapping of non-AgentCortex repos.
- **SSoT Append-only History**: Changed `current_state.md` to use an append-only `## Ship History` for safer archival.
- **Sentinel Token**: Injected `SENTINEL: ACX-READ-OK` to combat context truncation.

## [3.5.4] - 2026-03-04

### 🔌 External Tool Integration (Natural Language Driven)

- **ask-openrouter workflow**: New `[OPTIONAL MODULE]` workflow (`.agent/workflows/ask-openrouter.md`) enabling natural language delegation to OpenRouter models. Features 3-layer architecture: Intent Router, Pre/Post-Flight, and Dynamic Parameter Assembly.
- **codex-cli alignment**: Updated `codex-cli.md` with `[OPTIONAL MODULE]` tag, silent availability check, and `§8.2` reference for consistency.
- **§8.2 External Tool Delegation Protocol**: New section in `engineering_guardrails.md` defining shared rules for all external CLI tools — silent availability check, cost-tier confirmation, and mandatory Pre/Post-Flight.
- **Graceful degradation**: Users without external tools experience zero disruption — AI silently falls back to native execution.
- **Deploy script**: Bumped to v3.5.4. Added `.openrouter/` to gitignore template.
- **SSoT update**: Registered both tools as `[OPTIONAL]` in `current_state.md` Canonical Commands.

## [3.5.2] - 2026-02-27

### ⚖️ Governance Refinement & Directory Polish

- **指令語義優化**: 修正 `/test-skeleton` 的啟動狀態門檻為 `IMPLEMENTABLE`；為 `/implement` 與 `/execute-plan` 加入硬性進入條件提示（state machine 對齊）。
- **平台技能隔離**: 更新 `AGENTS.md` 與 `README.md`，明確區分 `.agent/skills` 與 `.agents/skills` 為平台獨立目錄，取消自動符號連結以增加配置彈性。
- **Token 反思機制**: 在 `/handoff` 工作流加入 `Token & Efficiency Reflection` 區塊，落實自我管理哲學。
- **清理修復**: 移除了已棄用的 `.agent/workflows/` 冗餘檔案（`update-docs.md`, `docs-update.md`）。

## [3.5.1] - 2026-02-27

### 🛠️ Directory Structure & Multi-Platform Support

- **部署升級**: `deploy_brain.sh` 升級為 v3.5.1，全面支援 vNext 目錄結構。
- **文件策略修復**: 修正 `AGENTS.md` 中的「盲目掃描」反模式，改為基於 `current_state.md` 的精準讀取。
- **Token 極致壓縮**: `rules.md` 與 `AGENTS.md` 完成大幅度內縮優化，節省每回合啟動開銷。

## [3.5.0] - 2026-02-27

### 🚀 vNext Self-Managed Architecture Release

- **SSoT 狀態模型**: 導入 `docs/context/current_state.md` 作為唯一真實來源，任務隔離於 `docs/context/work/` 目錄。
- **工作流全面遷移**: 所有 superpowers 遷移至 `.agent/workflows/`，對齊 Google Antigravity 原生指令。
- **任務分類凍結**: `/bootstrap` 現在強制執行任務分類並凍結，防止開發路徑偏離。
- **遷移工具**: 新增 `docs/guides/migration.md`，支援從舊版 v3.0 無縫升級。

## [3.4.0] - 2026-02-23

### 🚀 Release v3.4.0 (Version Sync + Practical Examples)

- **版本同步**: `README.md`、`.agent/AGENT.md`、`deploy_brain.sh` 全面升級為 v3.4.0。
- **實戰範例**: 新增 `docs/PROJECT_EXAMPLES.md`，提供 Node.js（Express + Vitest）與 Python（FastAPI + pytest）導入流程。
- **部署擴充**: `deploy_brain.sh` 現在會部署 `docs/PROJECT_EXAMPLES.md`。
- **驗證強化**: `validate.sh` 新增 `PROJECT_EXAMPLES.md` 存在檢查，並驗證 README 已連結範例文件。

## [3.3.1] - 2026-02-23

### 🔧 Superpowers Features Completion & README Clarity

- **功能補齊**: 新增 `.agent/superpowers/features/` 模組，包含 `brainstorm`, `research`, `spec`, `execute`, `review`, `retro` 六種能力檔案。
- **指令擴充**: `.agent/superpowers/commands.md` 新增 `/brainstorm`, `/research`, `/spec`, `/retro` 指令模板。
- **工作流深化**: `.agent/superpowers/workflows.md` 納入探索型開發節奏（Idea → Spec → Plan → Implement → Review/Test）。
- **操作文件強化**: `README.md` 補上「原始操作流程」與「如何呼叫各功能檔案」的完整範例。
- **部署修正**: `deploy_brain.sh` 支援部署 `.agent/superpowers/features/*.md`。
- **可用性驗證**: 新增 `/.agent/superpowers/validate.sh`，可一鍵檢查指令、功能檔與 README 對應是否一致。
- **命名一致性**: 新增 `features/implement.md` 並將 `execute.md` 改為相容別名，避免 `/implement` 指令對不上檔名。
- **能力補齊**: 新增 `features/bootstrap.md`（任務啟動）與 `features/handoff.md`（跨回合交接）。
- **Codex 平台相容**: 新增 `docs/CODEX_PLATFORM_GUIDE.md`，提供 Web 與 App 兩端一致操作建議。
- **參考來源標註**: README 新增 Superpowers 原始專案連結，明確標示設計參考來源。
- **規範稽核強化**: `validate.sh` 新增平台文件與 AGENT 引用檢查，並驗證 README 含參考來源。
- **流程強制化**: 新增 `policies/methodology.md` 與 `policies/state_machine.md`，導入 workflow gate 與完成條件。
- **Codex 入口**: 新增 `.codex/INSTALL.md`，支援一句話「Fetch and follow instructions ...」載入流程。
- **指令別名**: 新增 `/write-plan`、`/execute-plan` 對齊 Superpowers 常見命名。

## [3.3.0] - 2026-02-23

### 🧩 Superpowers Alignment for Google Antigravity

- **流程升級**: `README.md` 改版為 Antigravity Superpowers Edition，加入 Plan → Implement → Review → Test 的標準節奏。
- **Agent 強化**: `.agent/AGENT.md` 新增 Superpowers 導向執行模式，明確化可重複操作流程。
- **Prompt 工具箱**: 新增 `.agent/superpowers/commands.md`，提供可直接貼用的高訊噪比指令模板。
- **工作流卡片**: 新增 `.agent/superpowers/workflows.md`，涵蓋小修補、中型功能、Hotfix 與文件治理場景。
- **部署腳本更新**: `deploy_brain.sh` 支援部署 `.agent/superpowers/` 內容與 v3.3 版本訊息。

## [3.2.0] - 2026-02-14

### 🧪 Zero-Token Enhancements (零成本工作流強化)

- **品質閘門**: 新增 `.github/PULL_REQUEST_TEMPLATE.md`，標準化 AI 的產出總結與自檢項目。
- **測試規範**: 新增 `docs/TESTING_PROTOCOL.md`，提供邊際情況與錯誤處理的測試標準，採 Opt-in (手動呼叫) 模式以節省 Token。
- **部署擴充**: `deploy_brain.sh` 現在完整支援所有 v3.2 文檔與模板。

## [3.1.0] - 2026-02-14

### ⚖️ Agent-First Constitution (憲法級架構)

- **憲法層級**: 新增 `.agent/rules/engineering_guardrails.md`，定義 Agent 不可違背的工程準則。
- **協作介面**: 新增 `.github/ISSUE_TEMPLATE/agent_issue.md`，將任務描述結構化。
- **角色 manifest**: 新增 `docs/AGENT_PHILOSOPHY.md`，定義 AI 與人類的協作邊界。
- **腳本優化**: `deploy_brain.sh` 支援部署隱藏資料夾（.github）與文檔。

## [3.0.0] - 2026-02-14

### 🪶 Pragmatic Lean (務實精小版)

- **Radical Simplification**: 將 40+ 個檔案整理為 1 個核心 Prompt (`AGENT.md`)，系統提示開銷降低 94%。
- **Antigravity-Native**: 專位 Google Antigravity 打造，利用 IDE 自動讀取 `.agent/` 目錄的特點，減少手動配置。
- **Human-Centric Guidance**: 移除無效的自動路由，改由 `AGENT_MODEL_GUIDE.md` 指引用戶手動切換模型，確保正確使用 Flash/Pro/Advanced 模型。
- **Audit Implementation**: 合併精華版 PII 掩碼、Secrets 偵測與編碼規範。

## [2.6.5] - 2026-02-13

### 🚀 Flash-First Strategy (重大策略轉變)

- **架構反轉**: 核心邏輯改為以 Flash 為主體，處理 80% 低成本任務。
- **升級請求 (Escalation)**: 當背景超出 Flash 負荷時，模型會主動停止並提示切換至 Pro，確保 100% 節省 Pro Token。
- **新版 README**: 強調操作流程的改變，降低 Token 誤用風險。

## [2.5.1] - 2026-02-13

### 🛡️ Security & Language

- **強制語言**: 全局強制使用繁體中文 (台灣) 進行對話。
- **隱私加固**: `08_compliance` 加入 PII 掩碼規則。
- **漏洞掃描**: `08_code_review` 加入 OWASP Top 10 與 Secrets 掃描指南。

## [2.5.0] - 2026-02-13

### ✨ Added

- **重大升級**: 正式進入工業級架構 (Industrial-Grade)。
- **元數據驅動**: 全檔案加入 YAML frontmatter 支援元數據解析。
- **精細化 Thresholds**: 支援各工作流自定義 Token 閾值，極大化節省成本。
- **新增 4 大工作流**: 工程開發 (`01`)、內容創作 (`10`)、數據報表 (`11`)、環境自檢 (`12`)。
- **新增 3 大規則**: 安全合規 (`08`)、格式標准 (`09`)、指令設計 (`10`)。
- **新增 3 大技能**: 質量審查、圖表建議、架構設計。

### 🚀 Optimized

- **Meta Router**: 升級動態信心調節與多階執行邏輯。
- **README**: 全面繁體中文優化，新增「擴充指南」範例。
- **Deployment**: `deploy_brain.sh` 支援更精確的模組複寫。
