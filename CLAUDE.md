# Claude Integration Entry

**MANDATORY**: Read and follow `AGENTS.md` before any action. It contains the governance rules, delivery gates, and state model that apply to ALL work in this repository.

This repository uses a documentation-first governance system (`AGENTS.md`, `.agent/`, `docs/context/`). Claude adapts to it via the commands below.

## Startup Behavior

1. Read `AGENTS.md` — obey all directives, gates, and rules referenced there.
2. Read `docs/context/current_state.md` (SSoT) to understand project state.
3. Run /bootstrap to classify your task and load the appropriate work log.

## Command Templates

Use templates in `.claude/commands/`:

- `spec-intake.md`
- `bootstrap.md`
- `plan.md`
- `implement.md`
- `review.md`
- `test.md`
- `test-classify.md`
- `decide.md`
- `handoff.md`
- `ship.md`

## Notes

- No Claude API or CLI is required for this baseline integration.
- Validate structure with `./tools/validate.sh`.
