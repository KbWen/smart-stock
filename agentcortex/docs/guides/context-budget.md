# Context Budget Guard

## Purpose

Define the **maximum read scope** per task classification to prevent agents from blindly reading all framework documents. This is the single biggest source of token waste — an agent reading 8 files when it only needs 2.

> Ref: `engineering_guardrails.md` Reading Mode (Full/Quick/Lite) defines *which sections* to read.
> This guide defines *which files* to read at all.

## Read Budgets by Classification

### tiny-fix

| Priority | File | Sections |
| --- | --- | --- |
| MUST | `AGENTS.md` | §Sentinel, §Intent Routing (tiny-fix fast-path only) |
| MUST | `engineering_guardrails.md` | Lite Mode: §7, §8.1 (if bug), §9.1, §10.3 |
| MUST | Target file(s) | Full read |
| SKIP | `current_state.md`, Work Logs, Specs, ADRs, all guides | — |

**Max file reads: 2-3** (governance + target files)

### quick-win

| Priority | File | Sections |
| --- | --- | --- |
| MUST | `AGENTS.md` | §Core Directives, §Intent Routing |
| MUST | `engineering_guardrails.md` | Quick Mode: §4, §7, §8.1, §9.1 |
| MUST | `current_state.md` | Spec Index only (check existing coverage) |
| MUST | Target file(s) | Full read |
| IF MATCH | Relevant spec from Spec Index | Full read (1 spec max) |
| SHOULD | `docs/context/work/<worklog-key>.md` | `## Resume` block only (if exists) |
| SKIP | ADRs, all guides, archived logs, unrelated specs | — |

**Max file reads: 4-6**

### feature

| Priority | File | Sections |
| --- | --- | --- |
| MUST | `AGENTS.md` | Full |
| MUST | `engineering_guardrails.md` | Full Mode |
| MUST | `current_state.md` | Full |
| MUST | `docs/context/work/<worklog-key>.md` | Full (create if missing) |
| MUST | `state_machine.md` | Full |
| MUST | Relevant spec(s) from Spec Index | Full |
| MAY | 1 guide (if directly relevant) | Full |
| SKIP | Archived logs (unless cross-branch overlap), unrelated specs, platform guides | — |

**Max file reads: 6-9**

### architecture-change

| Priority | File | Sections |
| --- | --- | --- |
| MUST | All files from `feature` budget | Full |
| MUST | Relevant ADR(s) | Full |
| MAY | `migration.md` guide | Full |
| MAY | `token-governance.md` | If token impact expected |
| SKIP | Platform-specific guides (unless platform is the target) | — |

**Max file reads: 8-12**

### hotfix

| Priority | File | Sections |
| --- | --- | --- |
| MUST | `AGENTS.md` | §Core Directives, §Intent Routing |
| MUST | `engineering_guardrails.md` | Full Mode (§8.1 Bug Fix Protocol critical) |
| MUST | `current_state.md` | Spec Index + Ship History (for regression check) |
| MUST | `docs/context/work/<worklog-key>.md` | Full |
| MUST | Target file(s) + related modules | Full |
| SKIP | ADRs, guides, archived logs (unless root cause tracing requires them) | — |

**Max file reads: 5-8**

## Enforcement

### At Bootstrap

After classification, the agent MUST output a **Read Plan** as part of the bootstrap report:

```markdown
## Read Plan
- Classification: [tier]
- Files to read: [list with sections]
- Files explicitly skipped: [list with reason]
- Estimated governance reads: [N files]
```

### During Execution

- If an agent needs a file outside its budget, it MUST justify the read in the Work Log delta:
  `Budget extension: reading [file] because [reason]`
- Unjustified reads outside budget are flagged as **Token Leak** in the Drift Log.

### Integration with Token Governance

This guide operationalizes `token-governance.md` §1 (Task-Level Token Budget) by converting turn-count budgets into concrete file-read budgets. The two are complementary:

- **Token Governance**: How many turns and what format.
- **Context Budget**: How many files and which sections.

## Anti-Patterns

| Anti-Pattern | Correct Behavior |
| --- | --- |
| Reading all `.agent/workflows/*.md` at bootstrap | Read ONLY the workflow for the current phase |
| Reading `engineering_guardrails.md` in Full Mode for a `tiny-fix` | Use Lite Mode (§7, §8.1, §9.1, §10.3) |
| Re-reading `AGENTS.md` every turn | Read once at session start; it's in context |
| Reading archived work logs "just in case" | Read ONLY if cross-branch overlap detected in `current_state.md` |
| Reading all specs from Spec Index | Read ONLY specs tagged as relevant to current task |
| Reading platform guides for non-platform tasks | Skip unless the task targets that platform |
