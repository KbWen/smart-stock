# Claude Integration Entry

**MANDATORY**: Read and follow `AGENTS.md` before any action. It contains the governance rules, delivery gates, and state model that apply to ALL work in this repository.

This repository uses **AgentCortex** — a governance-first AI agent framework.
All rules live in `AGENTS.md` and `.agent/`. This file is the Claude-specific loader only.

## Startup (REQUIRED — every conversation)

1. **Read `AGENTS.md`** — this is the canonical governance document. Follow it exactly.
2. **Read `docs/context/current_state.md`** — this is the Single Source of Truth (SSoT).
3. **Read `.agent/rules/engineering_guardrails.md`** — constitution for all engineering work.
4. If a Work Log exists at `docs/context/work/<worklog-key>.md`, read it to resume context.

Do NOT invent your own workflow. Do NOT skip gates.
Every response MUST end with `⚡ ACX` (sentinel check per AGENTS.md §11).

## Slash Commands

All `/command` behavior is defined in `.agent/workflows/<command>.md`.
When a command is invoked, read the corresponding `.claude/commands/<command>.md` for dispatch instructions, then execute the canonical workflow from `.agent/workflows/`.

Available commands: `/bootstrap`, `/plan`, `/implement`, `/review`, `/test`, `/test-classify`, `/handoff`, `/ship`, `/decide`, `/spec-intake`

## Skills

Skills are defined in `.agents/skills/*/SKILL.md` (detailed instructions) and `.agent/skills/*` (metadata summaries). During `/bootstrap`, the workflow determines which skills are relevant to the task and writes them to the Work Log header. When a skill is recommended, read its `SKILL.md` and apply its guidance **within the active workflow phase only** — skills never override governance or gates.

## Hard Rules

- **Phase order is mandatory**: Bootstrap → Plan → Implement → Review → Test → Ship. NEVER skip phases even if the user asks.
- **No Evidence = No Completion**: non-tiny-fix tasks require verifiable test logs or terminal output.
- **SSoT protection**: only `/ship` may update `docs/context/current_state.md`. Work Logs are session-scoped.
- **Classification freeze**: task classification set during bootstrap is immutable.
- **Installation**: NEVER manually copy framework files. Use `deploy_brain.sh` or `deploy_brain.ps1`. NEVER overwrite the target repo's existing README.md or .gitignore outside the managed block.

## Validate

Run `./tools/validate.sh` (or `tools/validate.ps1` on Windows) to verify structural integrity.
