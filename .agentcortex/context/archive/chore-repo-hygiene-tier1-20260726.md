# Work Log: chore/repo-hygiene-tier1

## Header

- Branch: `chore/repo-hygiene-tier1`
- Classification: `hotfix`
- Classified by: `claude-opus-5`
- Frozen: `true`
- Created Date: `2026-07-26`
- Owner: `KbWen`
- Guardrails Mode: `Full`
- Current Phase: `ship`
- Diff Base SHA: `5c93b710a003732703de08f82c4905b30946f676`
- Checkpoint SHA: `43a2e40` (test) · impl `ac4b461`
- Recommended Skills: `verification-before-completion (auto), red-team-adversarial (auto, Lite), karpathy-principles (auto), systematic-debugging (auto, on-encounter)`
- Primary Domain Snapshot: `none`
- SSoT Sequence: `0`

---

## Session Info

- Agent: `claude-opus-5` · Session: `2026-07-26 08:17 UTC` · Platform: `claude-code`
- Guardrails loaded: AGENTS.md §Core Directives, state_machine.md, security_guardrails.md, shared-contracts.md
- Override / Downstream-Capabilities / private: absent
- Read receipt: SSoT (Last Verified 2026-07-02, Seq 0) · Work Log created · Spec Scope: none

---

## Task Description

Tier 1 of a 3-tier repo hygiene cleanup (2026-07-26 survey). Tiers 2–3 deferred.

1. Rename 2 mojibake archive filenames → `frontend-testing.md`, `optimize-frontend-api.md`
2. Remove stale root `deploy_brain.{sh,ps1,cmd}` (superseded by `installers/`)
3. Untrack + gitignore `stock_list_cache.json` (`core/config.py:58`), `tw_stocks_analysis_refined.csv` (`fetch_stocks.py:114`)
4. ~~`.gitkeep` / `archive/work/` cleanup~~ — DROPPED at `/plan`

---

## Phase Sequence

| Phase | Status | Entered | Notes |
|---|---|---|---|
| bootstrap | done | 2026-07-26 | `hotfix` via provenance escalation |
| plan | done | 2026-07-26 | item 4 dropped; 8 paths; Confidence 92% |
| implement | done | 2026-07-26 | 8 paths, zero divergence, commit `ac4b461` |
| review | done | 2026-07-26 | PASS — 0 blocking, 3 informational |
| test | done | 2026-07-26 | 288 passed; +5 falsified guards |
| handoff | n/a | — | hotfix exempt (§10.2) |
| ship | done | 2026-07-26 | SSoT Seq 0→1; archived |

---

## Phase Summary

- bootstrap: `hotfix` + 4 skills, branch from `master@5c93b71`. Not urgency — `state_machine.md`
  Supply-Chain/Provenance Escalation forces `hotfix` minimum because item 2 removes files containing
  source-selection and remote-fetch logic.
- plan: 3 of 4 items survived; item 4 dropped as framework-managed. | Confidence: 92% — high.
- implement: 8 paths, zero divergence. Renames woke 2 dormant validators → 2 FAILs, both remediated
  in-branch; a 3rd FAIL was my own oversized log. | Confidence: 95% — high.
- review: PASS. 0 blocking, 0 security findings; Red Team Lite concluded the change *reduces* attack
  surface. Closed an evidence gap implement left open (CI runs with no committed cache).
- test: 288 passed / 1 deselected (+5 new `tests/test_repo_hygiene.py` guards pinning R1/R2/R4). Each
  guard was empirically falsified before acceptance. Lite adversarial = the falsification pass itself.

⚡ ACX

---

## Gate Evidence

- Gate: bootstrap | Verdict: PASS | Classification: hotfix | Timestamp: 2026-07-26T08:17:32Z
- Gate: plan | Verdict: PASS | Classification: hotfix | Timestamp: 2026-07-26T08:31:00Z
- Gate: implement | Verdict: PASS | Classification: hotfix | Timestamp: 2026-07-26T08:52:00Z
- Gate: review | Verdict: PASS | Classification: hotfix | Timestamp: 2026-07-26T09:10:00Z
- Gate: test | Verdict: PASS | Classification: hotfix | Timestamp: 2026-07-26T09:25:00Z
- Gate: ship | Verdict: PASS | Classification: hotfix | Timestamp: 2026-07-26T09:40:00Z

---

## External References

| Type | Path | Notes |
|---|---|---|
| Spec | — | hotfix is Spec-Gate exempt |
| ADR | `docs/adr/` | coverage exit 1; feature/arch-only check, skipped for hotfix |
| Follow-up | Tier 2 | `daily_run.sh` root vs `scripts/` · `CONTRIBUTING.md` root vs `docs/project_meta/` · `codex/` vs `.codex/` · `tools/check_text_integrity.*` vs `.agentcortex/tools/` · 3 `_product-backlog-*` snapshots |
| Follow-up | Tier 3 | 17 drifted docs between `docs/` and `.agentcortex/docs/` + `.gitignore` asymmetry |
| Bug | `validate.sh:2259` | `printf '%b'` mangles Windows paths in broken-link output (pre-existing) |

---

## Known Risk

- **R1 RESOLVED** — root wrappers were unmanaged orphans: `deploy.sh:839-841` deploys only `installers/*`;
  `validate.sh:28` + `:34-36` and `validate.ps1:225-227` resolve `ROOT_DEPLOY_*` there;
  `.agentcortex-manifest:208-210` lists only that trio. `docs/**` refs to a root `./deploy_brain.sh`
  describe the agentic-os **source repo** (Tier 3 drift); `.codex/INSTALL.md:33-35` already correct.
  Now pinned by `test_installer_wrappers_live_only_under_installers`.
- **R2 RESOLVED** — no reader beyond each writer; proven twice on a cache-less tree. Accepted delta: fresh
  clones fetch the universe live rather than read a 2026-06-01 cache, returning **more, current** data
  (2128 vs 1819). Now pinned by `test_runtime_artifacts_are_not_tracked`.
- **R3 INVALIDATED item 4** — the three `.gitkeep.md` are framework-deployed (`deploy.sh:901-905`;
  `validate.ps1:1023-1024`); `archive/work/` is the `/handoff §6` overflow dir, empty so untracked.
- **R4 ACCEPTED** — renaming exposed both files to `*.md` validators for the first time. Two defects fixed;
  `empty Phase Summary` WARN 15→17 accepted (15 peer logs share it). Recurrence pinned by
  `test_archived_worklog_filenames_end_in_md`.

---

## Decisions

none

---

## Conflict Resolution

none — `karpathy-principles` vs `verification-before-completion` is `compatible`; no other pair is listed.

---

## Skill Notes

- **karpathy-principles** (/plan, /implement, /review): §3 "notice unrelated dead code, mention it — don't
  delete it" was binding since this task IS deletion — each removal needed its own evidence. Applied:
  item 4 dropped, Tier 2/3 untouched.
- **systematic-debugging** (/implement, on 2 validate FAILs): Observe → Hypothesize → Verify → Fix.
- **red-team-adversarial** (Lite, hotfix row): /review fix-point + regression vector; /test falsification pass.

---

## Drift Log

- Skip Attempt: NO · Gate Fail Reason: N/A · Token Leak: NO
- SSoT staleness: Last Verified 24 days old (>14) — advisory.
- ADR coverage inert repo-wide: all 4 ADRs lack `applies_to:` frontmatter though `current_state.md §ADR
  Index` documents the values. Out of scope; spawned as a separate task.
- Governance precedence: `bootstrap.md §1` says write SSoT `Last Verified` at bootstrap; `AGENTS.md §vNext
  State Model` limits SSoT writes to `/ship` + an exhaustive exception set excluding `/bootstrap`. Per
  §Skill Safety & Precedence rule 2 (AGENTS.md > workflows), not written.
- Branch created during bootstrap; no content changed there. Lock ensured each phase (all exit 0).
- **Scope reduction at /plan**: item 4 dropped once `deploy.sh:901-905` / `validate.ps1:1023-1024` proved
  the `.gitkeep.md` files are framework-deployed. Reduction, not creep — classification unchanged.
- **Scope addition at /implement (+2 lines, files already in the diff)**: stripped a pre-existing UTF-8 BOM
  from `optimize-frontend-api.md` (rest hash-identical) and de-linked a machine-local `file:///c:/Users/...`
  URL in `frontend-testing.md`, per validate.sh's own guidance.
- **Process miss (mine)**: skipped `implement.md §Work Log Compaction Check`; log hit 283 lines/15KB vs
  max 300/12KB → `[FAIL] work log compaction`. Compacted at implement/review/test; no evidence dropped.
  The repeat had its own cause: my Python writes emitted CRLF on Windows, inflating every line by 1 byte.
- **Prediction accuracy**: at /plan I predicted one rename consequence (Phase Summary WARN 15→17) —
  correct but incomplete; missed the BOM FAIL and broken-link WARN from the same root cause.
- **Evidence gap closed at /review**: implement proved the cache-less path only via a direct
  `get_all_tw_stocks()` call; the real CI scenario (full suite, no cache) was untested. Re-ran — 283 passed.
- Recovered stale Work Log lock on 2026-07-26T10:21:23.331637+00:00; prior_owner=KbWen; prior_session=2026-07-26T08:17:32Z; reason=stale-time; lock=chore-repo-hygiene-tier1.lock.json

---

## Review Feedback

No blocking findings. Informational, deliberately not fixed:

1. **LOW — `.gitignore:20-21` unanchored.** Both match at any depth, but each file is only written to
   `BASE_DIR` (`core/config.py:58`, `fetch_stocks.py:114`) → no real collision. Left unanchored to match
   every neighbouring line in the block (`storage.db`, `market_history.json`).
2. **INFO — collaborator effect.** `git rm --cached` deletes both from the working tree of anyone who
   pulls. The cache self-regenerates; the CSV needs `fetch_stocks.py` re-run. Belongs in the PR body.
3. **INFO — this log ran near the 12KB ceiling** for three phases; the repeat cause was CRLF from my own
   Python writes on Windows. Moot after archival (the compaction check only scans active `work/` logs).
4. **INFO — Ship History is over cap (20→21 vs 10).** `ship.md §State Update` says rotate the oldest into
   `archive/ship-history-YYYY.md`. Pre-existing at baseline; deliberately NOT done here — an 11-entry SSoT
   rewrite inside a hotfix is exactly the unscoped change this task refused elsewhere. Follow-up candidate.

---

## Red Team Findings

Lite mode (hotfix). 2 findings, neither blocking — both conclude the change *reduces* risk.

- **Fix-point vector → IMPROVEMENT.** The deleted root `deploy_brain.sh` pulled and `exec`d a cached
  framework source with **no origin verification** (old `:39-45`), so a `.agentcortex-src` cloned from a
  different or pre-migration repo would be silently updated and executed. The surviving
  `installers/deploy_brain.sh:85-104` compares the cache's `remote get-url origin` against the resolved
  source and re-clones on mismatch. Deleting the weaker path removes a real code-execution surface.
- **Regression attack → none.** A stale cache left by the old flow can't be exploited afterwards: the
  surviving wrapper's origin check (`:89`) forces a re-clone via `remove_cache_or_die` (`:74-83`), which
  refuses to continue on a partial delete.
- **Lite adversarial (/test)** — rather than invent synthetic attack cases for a change with no runtime
  surface, the adversarial budget went into falsifying the new guards themselves: each was broken on
  purpose and observed to fail (see Test Gate Results). A guard that cannot fail is worse than none.

---

## Design Reference

none — no user-visible UI in this change (Design Gate exempt).

---

## Observability

none — no error-handling code in the diff (§5.2a covers application/service code).

---

## Resume

none

---

## Test Gate Results

- Command: `python -m pytest tests -m "not integration" -q`
- Result: **288 passed, 1 deselected** (was 283 before this phase; +5 new guards)
- Test Files: `tests/test_repo_hygiene.py` (new, 5 tests)
- Falsification: each guard was empirically broken and observed to FAIL — re-tracking the cache,
  removing the `.gitignore` entries, resurrecting a root `deploy_brain.sh`, and re-creating a mojibake
  archive filename each produced the expected failure. The guards are not vacuous.

---

## Evidence

- **Renames** — sha256 identical before/after; `git ls-files | grep '"'` → empty (was 2).
- **Wrapper removal** — `bash -n installers/deploy_brain.sh` OK, `.ps1` parses clean. Manifest: `.sh`
  matches raw sha256; `.ps1`/`.cmd` match **after CRLF→LF**, as `.gitattributes` designs (`eol=crlf`,
  manifest stores LF hashes) — all three wrappers byte-identical to the manifest record.
- **Untrack** — both still on disk; `git ls-files` no longer lists them; `git check-ignore -v
  stock_list_cache.json` → `.gitignore:20`.
- **Regression** — `pytest -m "not integration"` → **283 passed** both with the cache present (25.3s) and
  absent (16.0s = the CI scenario); **288 passed** after adding the guards. Cache-less
  `get_all_tw_stocks()` → **2128 tickers** live vs 1819 committed; `test_scripts_seed_demo.py` → 5 passed.
  Local side effect: the now-ignored cache refreshed 1819→2128; gitignored, `git status` unaffected.
- **Validate** — baseline `master@5c93b71`: exit 1 · **92 PASS / 9 WARN / 0 FAIL**. Final: **92 / 9 / 0 —
  counts identical**. Two line-level deltas, both explained: governed-write lint 149→147 files scanned
  (deleted files) and Phase Summary WARN 15→17 (R4). The three `deploy_brain` PASS lines and `[PASS] text
  integrity check` are green at head. *(An earlier revision recorded the baseline as "26 lines / 1 WARN" —
  that was a `tail -25`, not the run.)*
- **Scope** — exactly the **8 planned paths, zero divergence**; both remediation edits landed in files
  already in the diff. Staged diff: 1 line per archive file + 2 in `.gitignore`. `frontend-testing.md`
  normalized CRLF→LF to match the blob `.gitattributes` already produces; no line-ending churn in the diff.
- **CI impact (/review)** — `integrity-check.yml` critical-files list is README/AGENTS/current_state/
  engineering_guardrails only → no deletion breaks it; its UTF-8 walk now covers both renamed `.md` files,
  each decoding cleanly; "Run Repository Validation" is `continue-on-error: true` → the accepted WARN delta
  cannot fail CI. No workflow references any changed path.
- **FAIL triage (/implement)** — all four symptoms traced to one root cause (renaming into the `*.md`
  glob): utf8-bom → stripped; broken `file:///…` link at `frontend-testing.md:9` → plain text; Phase
  Summary 15→17 → accepted (R4). The fourth, work-log compaction, was mine. Detail in Drift Log.
- **Security** (§1 A01–A03 + §3) — A01/A03 N/A: no executable code paths. A02/§3: no credentials, keys,
  tokens or connection strings; `git rm --cached` doesn't purge history, but both files hold public market
  data. §4: no manifest changed. **Findings: none.**
- **Lesson candidate (/retro)** — renaming a file into a validated glob (`*.md`) is not a no-op: it
  activates every content check that was silently skipping it.
