#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PLATFORM_DOC="$ROOT/docs/CODEX_PLATFORM_GUIDE.md"
CLAUDE_PLATFORM_DOC="$ROOT/docs/CLAUDE_PLATFORM_GUIDE.md"
EXAMPLES_DOC="$ROOT/docs/PROJECT_EXAMPLES.md"
PROJECT_AGENTS_FILE="$ROOT/AGENTS.md"
PROJECT_CLAUDE_FILE="$ROOT/CLAUDE.md"
WORKFLOWS_DIR="$ROOT/.agent/workflows"
CLAUDE_COMMANDS_DIR="$ROOT/.claude/commands"
CODEX_INSTALL="$ROOT/.codex/INSTALL.md"
CODEX_RULES="$ROOT/.codex/rules/default.rules"

required_files=(
  "$WORKFLOWS_DIR/hotfix.md"
  "$WORKFLOWS_DIR/worktree-first.md"
  "$WORKFLOWS_DIR/new-feature.md"
  "$WORKFLOWS_DIR/medium-feature.md"
  "$WORKFLOWS_DIR/small-fix.md"
  "$WORKFLOWS_DIR/govern-docs.md"
  "$WORKFLOWS_DIR/handoff.md"
  "$WORKFLOWS_DIR/bootstrap.md"
  "$WORKFLOWS_DIR/plan.md"
  "$WORKFLOWS_DIR/implement.md"
  "$WORKFLOWS_DIR/review.md"
  "$WORKFLOWS_DIR/help.md"
  "$WORKFLOWS_DIR/test-skeleton.md"
  "$WORKFLOWS_DIR/commands.md"
)

claude_required_files=(
  "$CLAUDE_COMMANDS_DIR/bootstrap.md"
  "$CLAUDE_COMMANDS_DIR/plan.md"
  "$CLAUDE_COMMANDS_DIR/implement.md"
  "$CLAUDE_COMMANDS_DIR/review.md"
  "$CLAUDE_COMMANDS_DIR/test.md"
  "$CLAUDE_COMMANDS_DIR/handoff.md"
  "$CLAUDE_COMMANDS_DIR/ship.md"
)

for f in "${required_files[@]}"; do
  [[ -f "$f" ]] || { echo "missing required file: $f"; exit 1; }
done

for f in "${claude_required_files[@]}"; do
  [[ -f "$f" ]] || { echo "missing claude adapter file: $f"; exit 1; }
done

[[ -f "$PLATFORM_DOC" ]] || { echo "missing platform guide: $PLATFORM_DOC"; exit 1; }
[[ -f "$CLAUDE_PLATFORM_DOC" ]] || { echo "missing claude platform guide: $CLAUDE_PLATFORM_DOC"; exit 1; }
[[ -f "$EXAMPLES_DOC" ]] || { echo "missing examples doc: $EXAMPLES_DOC"; exit 1; }
[[ -f "$PROJECT_AGENTS_FILE" ]] || { echo "missing project AGENTS.md: $PROJECT_AGENTS_FILE"; exit 1; }
[[ -f "$PROJECT_CLAUDE_FILE" ]] || { echo "missing project CLAUDE.md: $PROJECT_CLAUDE_FILE"; exit 1; }
[[ -d "$WORKFLOWS_DIR" ]] || { echo "missing workflows dir: $WORKFLOWS_DIR"; exit 1; }
[[ -d "$CLAUDE_COMMANDS_DIR" ]] || { echo "missing claude commands dir: $CLAUDE_COMMANDS_DIR"; exit 1; }

# Skills validation
[[ -d "$ROOT/.agents/skills" ]] || { echo "missing codex skills dir: $ROOT/.agents/skills"; exit 1; }
[[ -d "$ROOT/.agent/skills" ]] || { echo "missing agent skills canonical dir: $ROOT/.agent/skills"; exit 1; }

for skill_file in "$ROOT"/.agent/skills/*; do
  [[ -f "$skill_file" ]] || continue
  skill_name="$(basename "$skill_file")"
  [[ "$skill_name" == ".gitkeep" ]] && continue
  codex_skill_path="$ROOT/.agents/skills/$skill_name"

  # Verify .agent/skills/<name> is a non-empty metadata file
  [[ -s "$skill_file" ]] || { echo "empty skill metadata: $skill_file"; exit 1; }

  # Verify corresponding .agents/skills/<name>/ directory exists with SKILL.md
  [[ -d "$codex_skill_path" ]] || { echo "missing codex skill dir: $codex_skill_path"; exit 1; }
  [[ -f "$codex_skill_path/SKILL.md" ]] || { echo "missing skill definition: $codex_skill_path/SKILL.md"; exit 1; }
done

[[ -f "$ROOT/.antigravity/rules.md" ]] || { echo "missing antigravity rules: $ROOT/.antigravity/rules.md"; exit 1; }
[[ -f "$ROOT/.agent/rules/rules.md" ]] || { echo "missing legacy rules copy: $ROOT/.agent/rules/rules.md"; exit 1; }
[[ -f "$CODEX_INSTALL" ]] || { echo "missing codex install doc: $CODEX_INSTALL"; exit 1; }

# Handoff workflow format gate (portable minimal kit follow-up)
required_handoff_patterns=(
  "# /handoff"
  "## 3. Required Output Blocks"
  "Layer 1 (Handoff TL;DR, <= 10 lines)"
  "- Goal"
  "- Current State"
  "- Next Action"
  "- Blocker"
  "- Owner"
  "- Last Verified Command"
  "Layer 2 (Traceability)"
  "- Done"
  "- In Progress"
  "- Risks"
  "- References"
  "## Resume"
  "- State:"
  "- Completed:"
  "- Next:"
  "- Context:"
  "## 4. Minimum References (HARD GATE)"
  "At least 1 docs/ file path"
  "At least 1 code file path"
  "Work Log path"
)

for pattern in "${required_handoff_patterns[@]}"; do
  rg -F -q -- "$pattern" "$WORKFLOWS_DIR/handoff.md" || {
    echo "handoff format gate failed: missing pattern [$pattern] in $WORKFLOWS_DIR/handoff.md"
    exit 1
  }
done

# Legacy rules redirect checks
rg -q "\.antigravity/rules\.md" "$ROOT/.agent/rules/rules.md" || {
  echo "legacy rules missing canonical redirect: $ROOT/.agent/rules/rules.md"
  exit 1
}
rg -q "legacy compatibility" "$ROOT/.agent/rules/rules.md" || {
  echo "legacy rules missing compatibility marker: $ROOT/.agent/rules/rules.md"
  exit 1
}

# Canonical rules safety keyword checks
CANONICAL_RULES="$ROOT/.antigravity/rules.md"
rg -q "docker system prune -a" "$CANONICAL_RULES" || { echo "rules missing dangerous command: docker system prune -a in $CANONICAL_RULES"; exit 1; }
rg -q "chown -R" "$CANONICAL_RULES" || { echo "rules missing dangerous command: chown -R in $CANONICAL_RULES"; exit 1; }
rg -q "rollback" "$CANONICAL_RULES" || { echo "rules missing rollback reminder in $CANONICAL_RULES"; exit 1; }

# Codex prefix_rule syntax and required high-risk command coverage
ACTIVE_CODEX_RULES="$ROOT/codex/rules/default.rules"
[[ -f "$ACTIVE_CODEX_RULES" ]] || ACTIVE_CODEX_RULES="$CODEX_RULES"
if [[ -f "$ACTIVE_CODEX_RULES" ]]; then
  rg -q '^prefix_rule\("' "$ACTIVE_CODEX_RULES" || { echo "codex rules missing prefix_rule(): $ACTIVE_CODEX_RULES"; exit 1; }
  rg -q "docker system prune -a" "$ACTIVE_CODEX_RULES" || { echo "codex rules missing dangerous command: docker system prune -a"; exit 1; }
  rg -q "chown -R" "$ACTIVE_CODEX_RULES" || { echo "codex rules missing dangerous command: chown -R"; exit 1; }
fi

echo "AgentCortex integrity check passed"
