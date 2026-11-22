#!/usr/bin/env bash
# Instala DevForge a nivel de usuario: CLI, skill y agentes para todos los proyectos.
set -euo pipefail

repo="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
claude_dir="${CLAUDE_CONFIG_DIR:-$HOME/.claude}"
skills_dir="$claude_dir/skills"
agents_dir="$claude_dir/agents"

if [ ! -f "$repo/.claude/skills/factory/SKILL.md" ]; then
  echo "No encuentro .claude/skills/factory/SKILL.md en $repo" >&2
  exit 1
fi

mkdir -p "$skills_dir" "$agents_dir"

# La carpeta de skill admite symlink: las actualizaciones del repo se ven al instante.
ln -sfn "$repo/.claude/skills/factory" "$skills_dir/factory"

# Los agentes se copian: Claude Code los descubre en ~/.claude/agents/.
count=0
for agent in "$repo"/.claude/agents/devforge-*.md; do
  [ -e "$agent" ] || continue
  install -m 0644 "$agent" "$agents_dir/$(basename "$agent")"
  count=$((count + 1))
done

if [ "${SKIP_CLI:-0}" != "1" ] && ! command -v devforge >/dev/null 2>&1; then
  if command -v uv >/dev/null 2>&1; then
    uv tool install --editable "$repo"
  elif command -v pipx >/dev/null 2>&1; then
    pipx install --editable "$repo"
  elif python3 -m pip --version >/dev/null 2>&1; then
    python3 -m pip install --user -e "$repo"
  else
    echo "CLI pendiente: instala con 'uv tool install --editable $repo' (o pipx, o python3-pip)." >&2
  fi
fi

if [ -f "$claude_dir/settings.json" ]; then
  echo "Revisa y combina $repo/.claude/settings.json en $claude_dir/settings.json (no se sobrescribe)."
else
  cp "$repo/.claude/settings.json" "$claude_dir/settings.json"
  echo "Settings de referencia copiados a $claude_dir/settings.json."
fi

echo "Skill: $skills_dir/factory -> $repo/.claude/skills/factory"
echo "Agentes instalados: $count en $agents_dir"
echo "En cada proyecto: devforge init y ajusta test_command en .devforge/project.yaml."
