#!/usr/bin/env bash
set -euo pipefail

echo "=== AI Path Audit: $(pwd) ==="
echo

# ---------- Codex ----------
echo "== [Codex] Check repo root AGENTS.md =="
if [ -f "AGENTS.md" ]; then
  echo "✅ OK: ./AGENTS.md"
else
  echo "❌ MISSING: ./AGENTS.md  (Create one at repo root)"
fi
echo

echo "== [Codex] Check SKILL.md location (must be under .agents/skills/) =="
all_skill=$(find . -type f -name "SKILL.md" 2>/dev/null || true)
if [ -z "$all_skill" ]; then
  echo "ℹ️ No SKILL.md found (ok if you don't use Codex skills yet)"
else
  bad_skill=$(echo "$all_skill" | grep -vE '(^|/)\.agents/skills/' || true)
  if [ -n "$bad_skill" ]; then
    echo "❌ SKILL.md found outside .agents/skills/:"
    echo "$bad_skill" | sed 's/^/  - /'
  else
    echo "✅ OK: all SKILL.md under .agents/skills/"
  fi
fi
echo

echo "== [Codex+Antigravity] Check dual-path compatibility (.agent/skills <-> .agents/skills) =="
if [ ! -d ".agents/skills" ]; then
  echo "❌ Missing .agents/skills/"
elif [ ! -d ".agent/skills" ]; then
  echo "❌ Missing .agent/skills/"
else
  missing_agent_link=0
  missing_codex_entry=0

  for codex_skill in .agents/skills/*; do
    [ -e "$codex_skill" ] || continue
    skill_name="$(basename "$codex_skill")"
    if [ ! -e ".agent/skills/$skill_name" ]; then
      echo "❌ Missing .agent/skills/$skill_name (for Antigravity compatibility)"
      missing_agent_link=1
    fi
  done

  for agent_skill in .agent/skills/*; do
    [ -e "$agent_skill" ] || continue
    skill_name="$(basename "$agent_skill")"
    if [ ! -e ".agents/skills/$skill_name" ]; then
      echo "❌ Missing .agents/skills/$skill_name (for Codex compatibility)"
      missing_codex_entry=1
    fi
  done

  if [ "$missing_agent_link" -eq 0 ] && [ "$missing_codex_entry" -eq 0 ]; then
    echo "✅ OK: .agent/skills and .agents/skills entries are aligned"
  fi
fi
echo

# ---------- Antigravity ----------
echo "== [Antigravity] Check workspace rules/workflows (.agent/*) =="
if [ -d ".agent/rules" ]; then
  echo "✅ OK: ./.agent/rules/"
else
  echo "❌ MISSING: ./.agent/rules/"
fi
if [ -d ".agent/workflows" ]; then
  echo "✅ OK: ./.agent/workflows/"
else
  echo "❌ MISSING: ./.agent/workflows/"
fi
echo

echo "== [Antigravity] Suspicious: .agents/rules or .agents/workflows (likely wrong for Antigravity) =="
if [ -d ".agents/rules" ] || [ -d ".agents/workflows" ]; then
  echo "❌ Found Antigravity-like folders under .agents/:"
  [ -d ".agents/rules" ] && echo "  - .agents/rules"
  [ -d ".agents/workflows" ] && echo "  - .agents/workflows"
else
  echo "✅ OK: no .agents/rules or .agents/workflows"
fi
echo

echo "== [Antigravity] Check unrelated folders directly under .agent/ =="
echo "   Allowed: rules/, workflows/, skills/"
if [ -d ".agent" ]; then
  unrelated=$(find .agent -mindepth 1 -maxdepth 1 -type d \
    ! -name "rules" ! -name "workflows" ! -name "skills" 2>/dev/null || true)
  if [ -n "$unrelated" ]; then
    echo "❌ Unrelated folders under .agent/ (should be reviewed):"
    echo "$unrelated" | sed 's/^/  - /'
  else
    echo "✅ OK: .agent/ folders are within allowed set"
  fi
else
  echo "ℹ️ .agent/ does not exist"
fi
echo

echo "== Suggested fixes (dry suggestions) =="
[ ! -d ".agent/skills" ] && [ -d ".agents/skills" ] && echo "mkdir -p .agent && ln -s ../.agents/skills .agent/skills"
[ ! -d ".agents/skills" ] && [ -d ".agent/skills" ] && echo "mkdir -p .agents && ln -s ../.agent/skills .agents/skills"
[ -d ".agents/rules" ] && echo "git mv .agents/rules .agent/rules"
[ -d ".agents/workflows" ] && echo "git mv .agents/workflows .agent/workflows"
echo
echo "Done."
