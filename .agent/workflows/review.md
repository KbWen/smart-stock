---
description: Workflow for review
---
# /review

Conduct strict review of current changes.

Minimum Checks:

- Logic correctness
- Compatibility risks
- Violation of `.agent/rules/engineering_guardrails.md`
- Scope enforcement: MUST skip any file with `status: frozen` or `Finalized` metadata. Review scope is limited to current task's changed files only.

## Security Scan (MANDATORY — Auto-Enforced)

Execute `.agent/rules/security_guardrails.md` §1–§4 against all changed files:

1. **Always-On Checks** (every review): Broken Access Control (A01), Cryptographic Failures (A02), Injection (A03), Secret Detection (§3).
2. **Context Checks** (when relevant code touched): A04–A10 per trigger rules in security_guardrails.md §2.
3. **Dependency Check** (§4): If any dependency manifest changed, flag new dependencies.

### Security Verdict

- Any **CRITICAL/HIGH** finding → Review verdict = **Not Ready**. MUST fix before proceeding.
- **MEDIUM** findings → Flag in review output. Proceed allowed with user acknowledgment.
- **LOW** findings → Informational only.
- Output findings using format defined in security_guardrails.md §5.

## Self-Check Protocol (Auto — Before Presenting Results)

AI MUST verify its own review before outputting:

1. **Scope check**: List every file changed. Any file NOT in the original plan? Flag it.
2. **Regression check**: For each changed function/export, state: "Callers: [list]. Breaking change: yes/no."
3. **Evidence check**: Every claim MUST have a `file:line` reference. No narrative-only assertions.

## Output Format

- Issues found (with severity)
- Security findings (per §5 format above)
- Fix suggestions
- Ready to commit? (Yes/No — blocked if unresolved CRITICAL/HIGH security findings)

## Spec Compliance Check (MANDATORY for feature / architecture-change)

- Cross-reference implementation against EVERY AC in the referenced `docs/specs/<feature>.md`.
- For each AC, mark: ✅ Met / ⚠️ Partially Met (explain) / ❌ Not Met.
- If any AC is ❌: STOP. Cannot proceed to `/test` until resolved.
- `tiny-fix`, `quick-win`, and `hotfix` are EXEMPT from this check.
