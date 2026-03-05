#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PLATFORM_DOC="$ROOT/docs/CODEX_PLATFORM_GUIDE.md"
EXAMPLES_DOC="$ROOT/docs/PROJECT_EXAMPLES.md"
PROJECT_AGENTS_FILE="$ROOT/AGENTS.md"
WORKFLOWS_DIR="$ROOT/.agent/workflows"
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

for f in "${required_files[@]}"; do
  [[ -f "$f" ]] || { echo "missing required file: $f"; exit 1; }
done

[[ -f "$PLATFORM_DOC" ]] || { echo "missing platform guide: $PLATFORM_DOC"; exit 1; }
[[ -f "$EXAMPLES_DOC" ]] || { echo "missing examples doc: $EXAMPLES_DOC"; exit 1; }
[[ -f "$PROJECT_AGENTS_FILE" ]] || { echo "missing project AGENTS.md: $PROJECT_AGENTS_FILE"; exit 1; }
[[ -d "$WORKFLOWS_DIR" ]] || { echo "missing workflows dir: $WORKFLOWS_DIR"; exit 1; }

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

# Rules safety keyword checks
for rules_file in "$ROOT/.agent/rules/rules.md" "$ROOT/.antigravity/rules.md"; do
  rg -q "docker system prune -a" "$rules_file" || { echo "rules missing dangerous command: docker system prune -a in $rules_file"; exit 1; }
  rg -q "chown -R" "$rules_file" || { echo "rules missing dangerous command: chown -R in $rules_file"; exit 1; }
  rg -q "rollback" "$rules_file" || { echo "rules missing rollback reminder in $rules_file"; exit 1; }
done

# Codex prefix_rule syntax and required high-risk command coverage
ACTIVE_CODEX_RULES="$ROOT/codex/rules/default.rules"
[[ -f "$ACTIVE_CODEX_RULES" ]] || ACTIVE_CODEX_RULES="$CODEX_RULES"
if [[ -f "$ACTIVE_CODEX_RULES" ]]; then
  rg -q '^prefix_rule\("' "$ACTIVE_CODEX_RULES" || { echo "codex rules missing prefix_rule(): $ACTIVE_CODEX_RULES"; exit 1; }
  rg -q "docker system prune -a" "$ACTIVE_CODEX_RULES" || { echo "codex rules missing dangerous command: docker system prune -a"; exit 1; }
  rg -q "chown -R" "$ACTIVE_CODEX_RULES" || { echo "codex rules missing dangerous command: chown -R"; exit 1; }
fi

echo "AgentCortex integrity check passed"
