# Work Log: chore/brain-update-v1.8.25

## Header

- Branch: `chore/brain-update-v1.8.25`
- Classification: `hotfix`
- Classified by: `claude-opus-5`
- Frozen: `2026-09-02`
- Created Date: `2026-09-02`
- Owner: `KbWen`
- Guardrails Mode: `Full`
- Current Phase: `test`
- Diff Base SHA: `5179d9b` <!-- immutable: set once on first /implement -->
- Checkpoint SHA: `none` <!-- mutable: refresh each commit -->
- Recommended Skills: `verification-before-completion`
- Primary Domain Snapshot: `framework-governance`
- SSoT Sequence: `3`

---

## Session Info

> Written by /bootstrap. Update on each new session.

- Agent: `claude-opus-5`
- Session: `2026-09-02`
- Platform: `claude-code`
- Files Read: `14`
- Guardrails loaded: `.agent/rules/engineering_guardrails.md` §10 (classification/escalation), `.agent/workflows/shared-contracts.md`

---

## Task Description

> 1-3 sentences: what is being done and why.

Sync the vendored Agentic OS brain from the deployed `1.8.14` (source commit `77089a6`, deployed 2026-07-18) to the
latest upstream tag `v1.8.25` by running the sanctioned `installers/deploy_brain.sh` deployer against
`https://github.com/KbWen/agentic-os.git`. No application (Python/React) behavior change is in scope — only
framework-managed governance files under `.agent/`, `.agentcortex/`, `codex/`, `installers/`, and the adapter
entry files.

---

## Phase Sequence

> Record each phase entry in order. Update `Current Phase` in the Header on entry.

| Phase | Status | Entered | Notes |
|---|---|---|---|
| bootstrap | done | 2026-09-02 | Classified `hotfix` via Supply-Chain/Provenance Escalation |
| plan | done | 2026-09-02 | Single mechanical step: run the sanctioned deployer, then diff-review governance + provenance files |
| implement | done | 2026-09-02 | `bash installers/deploy_brain.sh` → v1.8.25; 3 sidecars resolved keep-local |
| review | done | 2026-09-02 | Read every governance/provenance diff by hand; no gate relaxed |
| test | done | 2026-09-02 | pytest 290/290; validate 107 PASS / 10 WARN / 0 FAIL |
| handoff | pending | — | — |
| ship | pending | — | — |

---

## Phase Summary

> One paragraph per completed phase. Delta-oriented: what changed, what was decided.
> End this section with the `**implement** — `bash installers/deploy_brain.sh` fetched `93d0542` (tag `v1.8.25`) and reported **200 updated / 3 skipped / 2 new / 0 removed**. Working tree delta: 51 tracked files modified + 2 new (`.agent/rules/repo-gotchas.md`, `.agentcortex/tools/check_audit_chain.py`). **Zero application files** — `core/`, `backend/`, `frontend/`, `scripts/`, `tests/` are untouched. The only `docs/` entries in the diff are the two `.gitkeep.md` placeholders the deployer owns, so the Tier-3 namespace split (framework docs live only under `.agentcortex/docs/`) survived the sync intact. Three files were skipped with `.acx-incoming` sidecars and all three were resolved **keep-local** (see Drift Log).

**review** — Read the full diff of every governance- and provenance-bearing file rather than trusting the deployer summary, because a `hotfix` on framework files can silently change gate semantics for every future task. `AGENTS.md`: no gate relaxed — the old runtime item 10 ("user requests cannot bypass gates") was **merged into** the No Bypass Rule as "even when the user explicitly asks", the Write-Isolation exception list gained `/bootstrap` (Last Verified + stale-Spec-Index repair, guarded), and Skill-vs-Workflow precedence was clarified to *not* outrank `.agent/rules/` (the Constitution). One softening, deliberate upstream: "Skipping this load = Gate FAIL" was dropped from §Shared Phase Contracts, though the MUST remains. `installers/deploy_brain.ps1` — the provenance-logic change that forced this classification — only hardens Windows bash discovery: candidates are now probed with `command -v dirname && command -v mktemp` instead of `bash --version`, so a bare `usrinash.exe` that would die at exit 127 mid-deploy is rejected up front. Source selection, cache origin verification, and the half-delete guard are unchanged. No new remote, no new fetch path.

**test** — Application suite green and validate FAIL-free; the WARN set moved by exactly two entries, both explained (see Evidence).

⚡ ACX` sentinel at least once — `validate.sh` checks for it here so the runtime marker has a persistent audit trail (chat output is ephemeral).

**bootstrap** — Read SSoT + `engineering_guardrails.md §10`. Deployed brain is `1.8.14` (manifest `source_commit: 77089a6`, deployed 2026-07-18); upstream `git ls-remote --tags` shows the newest tag is `v1.8.25`, so the sync spans 11 releases. Classified `hotfix`, NOT `quick-win`: the deployer rewrites `installers/deploy_brain.*` and `.agentcortex/bin/deploy.sh`, which is installer/bootstrap **source-selection and provenance logic**, and `engineering_guardrails.md §10.4 Supply-Chain / Provenance Escalation` forces `hotfix` minimum for that file class regardless of patch size. `hotfix` buys the REVIEWED + TESTED gates that a mechanical-sync `quick-win` would have skipped. Captured a pre-deploy `validate.sh` baseline for the post-deploy diff.

**implement** — `bash installers/deploy_brain.sh` fetched `93d0542` (tag `v1.8.25`) and reported **200 updated / 3 skipped / 2 new / 0 removed**. Working tree delta: 51 tracked files modified + 2 new (`.agent/rules/repo-gotchas.md`, `.agentcortex/tools/check_audit_chain.py`). **Zero application files** — `core/`, `backend/`, `frontend/`, `scripts/`, `tests/` are untouched. The only `docs/` entries in the diff are the two `.gitkeep.md` placeholders the deployer owns, so the Tier-3 namespace split (framework docs live only under `.agentcortex/docs/`) survived the sync intact. Three files were skipped with `.acx-incoming` sidecars and all three were resolved **keep-local** (see Drift Log).

**review** — Read the full diff of every governance- and provenance-bearing file rather than trusting the deployer summary, because a `hotfix` on framework files can silently change gate semantics for every future task. `AGENTS.md`: no gate relaxed — the old runtime item 10 ("user requests cannot bypass gates") was **merged into** the No Bypass Rule as "even when the user explicitly asks", the Write-Isolation exception list gained `/bootstrap` (Last Verified + stale-Spec-Index repair, guarded), and Skill-vs-Workflow precedence was clarified to *not* outrank `.agent/rules/` (the Constitution). One softening, deliberate upstream: "Skipping this load = Gate FAIL" was dropped from §Shared Phase Contracts, though the MUST remains. `installers/deploy_brain.ps1` — the provenance-logic change that forced this classification — only hardens Windows bash discovery: candidates are now probed with `command -v dirname && command -v mktemp` instead of `bash --version`, so a bare `usrinash.exe` that would die at exit 127 mid-deploy is rejected up front. Source selection, cache origin verification, and the half-delete guard are unchanged. No new remote, no new fetch path.

**test** — Application suite green and validate FAIL-free; the WARN set moved by exactly two entries, both explained (see Evidence).

⚡ ACX

---

## Gate Evidence

> Gate receipts written by each phase. Format: `- Gate: <phase> | Verdict: PASS | Classification: <type> | Timestamp: <ISO>`
> **Critical**: `|` pipe separators are mandatory. Receipts placed inside markdown code fences are silently masked and NOT counted by validate.sh — always write receipts as plain list lines.
> Receipt order-of-appearance is authoritative for phase progression; `Timestamp` is provenance metadata only (validators require it to be present and parseable, but do NOT enforce monotonic/chronological ordering).

- Gate: bootstrap | Verdict: PASS | Classification: hotfix | Timestamp: 2026-09-02T00:00:00Z
- Gate: plan | Verdict: PASS | Classification: hotfix | Timestamp: 2026-09-02T01:30:00Z
- Gate: implement | Verdict: PASS | Classification: hotfix | Timestamp: 2026-09-02T01:40:00Z
- Gate: review | Verdict: PASS | Classification: hotfix | Timestamp: 2026-09-02T02:05:00Z
- Gate: test | Verdict: PASS | Classification: hotfix | Timestamp: 2026-09-02T02:20:00Z

---

## External References

> Links to specs, ADRs, issues, PRs, or design docs relevant to this task.

| Type | Path / URL | Notes |
|---|---|---|
| Spec | — | Framework sync — no project spec |
| ADR | — | No architecture decision; vendored-dependency bump |
| Issue | — | — |
| PR | — | filled at ship |
| Source | https://github.com/KbWen/agentic-os.git @ `93d0542` (tag `v1.8.25`) | 11 releases ahead of the deployed `1.8.14` / `77089a6` |

---

## Known Risk

> List risks identified during planning or implementation. Include mitigation.

- **Provenance escalation** (`engineering_guardrails.md §10.4`): the deployer rewrites installer/bootstrap
  source-selection logic (`installers/deploy_brain.*`, `.agentcortex/bin/deploy.sh`), which crosses a downstream
  trust boundary. This is why the task is classified `hotfix` (buys REVIEWED + TESTED gates) rather than
  `quick-win`, despite being a mechanical sync.
- **Blast radius**: framework-managed files only. Rollback = `git checkout -- . && git clean -fd` on this branch
  (tree was clean at branch creation, SHA recorded above). The deployer's `rm -rf` targets `.agentcortex-src/`,
  a gitignored fetch cache that did not exist before this run.
- **Governance drift**: an upstream change to `AGENTS.md` / `.agent/rules/*` can alter gate semantics for every
  future task. Mitigated by diffing the governance files explicitly during `/review` rather than trusting the
  deployer's summary.
- **Local customization loss**: any project-local edit to a framework-managed file would be overwritten.
  Mitigated by the manifest sha256 check — the deployer reports drifted files instead of silently clobbering.

---

## Decisions

> Optional (`/decide` §2): record trade-offs/constraints as `### D-N: <title>` with Decision/Reason/Alternatives/Impact lines. At `/ship`, every entry gets one disposition marker: `→ promoted: ADR-<id>` / `→ consolidated: L2 <domain>` / `→ local`.

none

---

## Conflict Resolution

> Record skill conflicts resolved during bootstrap (from skill_conflict_matrix.md). Format: `<skill-A> vs <skill-B>: <chosen approach>`.

none

---

## Skill Notes

> Cache for loaded skills. Written by phase-entry skill loading. Leave as `none` until populated.

none

---

## Drift Log

> Record deviations from the original plan, reclassifications, or unexpected scope changes.

- **3 skipped files resolved keep-local, sidecars deleted.**
  - `.agentcortex/context/current_state.md` — the incoming file is the 3.4 KB blank SSoT template (`[Describe your project in one line]`) against our 34 KB of real project state. Adopting it would have destroyed the ADR Index, Spec Index, Ship History and Global Lessons. Skip was correct; sidecar deleted.
  - `.agent/skills/systematic-debugging` and `.agents/skills/systematic-debugging/agents/openai.yaml` — sole delta is `phases`/`phase_scope`: ours is `["implement","review","test","hotfix"]`, upstream's is `["implement","review","test"]`. Kept ours, because the **incoming file's own description** still reads "Also activate during hotfix research", so dropping `hotfix` from the phase list would contradict the skill's stated intent; ours is a strict superset and `load_policy: on-failure` makes the skill reachable either way. Both are `scaffold` in the manifest, which is the tier the deployer treats as project-owned-after-seeding — so this drift is sanctioned, not accidental. Worth reporting upstream as a description/phases inconsistency.
- **SSoT write, guarded**: `current_state.md` was first edited directly, then reverted and re-applied through `guard_context_write.py write --mode replace` with an optimistic-lock snapshot (`cbc85c1a…`), producing receipt `.agentcortex/context/.guard_receipts/337ffd90d88a8b4f.json`. The paired trim of the oldest Ship History entry into `.agentcortex/context/archive/ship-history-2026.md` (10/10 cap held) was written **unguarded** — the guard covers the SSoT only — and is logged here for that reason.
- **Deploy note, no action taken**: the deployer listed 6 local skills as not framework-managed (`executing-plans`, `finishing-a-development-branch`, `receiving-code-review`, `requesting-code-review`, `systematic-debugging.acx-incoming`, `writing-plans`) and suggested renaming them `custom-<name>`. Left as-is — pre-existing, out of scope for this sync. The `.acx-incoming` entry in that list is the deployer mis-scanning its own sidecar and disappeared once the sidecar was removed.

---

## Review Feedback

> Written by /review (fix suggestions + NOT READY findings). Read by /implement on resume-after-review — scope is ONLY the UNPROVEN/blocking rows.

none

---

## Red Team Findings

> Written by /review and /test when adversarial testing runs. HIGH findings do not block but MUST record a risk decision here.

none

---

## Design Reference

> Populated by /plan for UI tasks. If not a UI task, write `none`.
> Format: `Link: <DSoT URL or file path> | Tool: <Stitch | Figma | Pencil | other>`

none

---

## Observability

> Populated by /ship for feature/architecture-change tasks. Document the production error sink used in changed code.
> Format: `Sink: <logger name or API> | Scope: <files> | Verified: <yes/no>`

none

---

## Resume

> Populated by /handoff for feature/architecture-change tasks. Required: `State`, `Completed`, `Next`, `Context` fields; then `### Read Map`, `### Skip List`, `### Context Snapshot`; optionally `### Backlog Status`. validate.sh enforces the three `###` headings. Leave as `none` until /handoff runs.

none

---

## Test Gate Results

> Test-phase gate outcome for `feature`/`architecture-change` logs (required at handoff/ship once an implement receipt exists; ref: `engineering_guardrails.md §12.2`). Record pass/fail counts + the test command. Leave `none` until `/test` runs.

none

---

## Evidence

> Reproducible evidence for completed phases. Commands, outputs, versions. "It should work" is NOT evidence.
> **Terse format** (Ref: `engineering_guardrails.md` §5.2b Evidence Truncation Rule): success ≤ 3 lines per claim, failure ≤ 10 lines per claim with the most diagnostic context (root error + bottom of stack), strip passing-test noise. Multiple bullet entries preferred over one long paste.

- **Deployed version (pre)**: `.agentcortex-manifest` → `version: 1.8.14`, `source_commit: 77089a6`, `deployed_at: 2026-07-18T16:05:28Z`; `.agentcortex/bin/deploy.sh:29` → `ACX_VERSION="1.8.14"`.
- **Upstream latest**: `git ls-remote --tags https://github.com/KbWen/agentic-os.git` → newest tag `v1.8.25`.
- **Pre-deploy validate baseline**: `bash .agentcortex/bin/validate.sh` (exit 0) → **89 PASS / 10 WARN / 1 FAIL**. The single FAIL was `work logs missing gate evidence receipts: 1` — this Work Log itself, created empty moments earlier.
- **Deploy result**: `Agentic OS v1.8.25 (93d0542) deployed successfully! Summary: 200 updated / 3 skipped / 2 new / 0 removed`.
- **Version after**: `.agentcortex-manifest` → `version: 1.8.25`, `source_commit: 93d0542`, `deployed_at: 2026-09-02T01:39:40Z`; `.agentcortex/bin/deploy.sh:29` → `ACX_VERSION="1.8.25"`.
- **Blast-radius proof**: `git status --short | awk '{print $NF}' | grep -E '^(core|backend|frontend|scripts|tests)/' | wc -l` → **0**. 51 tracked modified + 2 new, all framework-managed.
- **Application tests**: `python -m pytest -q` → **290 passed**, 0 failed (the normally-deselected live-yfinance integration test also ran and passed — network was available).
- **Post-deploy validate**: `bash .agentcortex/bin/validate.sh` (exit 0) → **107 PASS / 10 WARN / 0 FAIL** (from 89/10/1).
  - `FAIL 1 → 0`: the pre-deploy FAIL was this Work Log's missing gate receipt, cleared by the bootstrap receipt. **No FAIL was introduced or masked by the sync.**
  - `PASS 89 → 107`: `validate.sh` itself gained +273 lines in this release, so the +18 are **newly added checks that pass**, not old checks that started passing.
  - `WARN 10 → 10`, a two-entry swap, both explained:
    - **cleared**: `current-branch work log missing 'Guardrails loaded:' receipt` — added at bootstrap.
    - **new**: `security scanning workflow absent — .github/workflows/security.yml not found` — a **new check in v1.8.25**. Partly a filename-convention false negative (`.github/workflows/pytest.yml:33-34` already runs `pip-audit -r requirements.txt`), partly a real gap: the repo has **no SAST and no secret-detection** job. Recorded as a follow-up and deliberately NOT fixed here — adding CI jobs is outside a framework sync's scope.
  - The other 9 WARNs are byte-identical to baseline (pre-existing work-log hygiene advisories).
