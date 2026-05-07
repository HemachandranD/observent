#!/usr/bin/env bash
# bigboss uninstaller — removes BIGBOSS_HOME and project-scoped adapter files.
# Usage: bash uninstall.sh [--project-dir <path>] [--dry-run]
set -euo pipefail

PROJECT_DIR="${PROJECT_DIR:-$PWD}"
BIGBOSS_HOME="${BIGBOSS_HOME:-$HOME/.bigboss}"
DRY_RUN=false

while [[ $# -gt 0 ]]; do
  case "$1" in
    --project-dir) PROJECT_DIR="$2"; shift 2 ;;
    --dry-run)     DRY_RUN=true; shift ;;
    *) echo "Unknown option: $1"; exit 1 ;;
  esac
done

run() {
  if $DRY_RUN; then echo "[dry-run] $*"; else "$@"; fi
}

echo "bigboss uninstaller"
$DRY_RUN && echo "  Mode: dry-run"
echo ""

# Remove BIGBOSS_HOME
if [[ -d "$BIGBOSS_HOME" ]]; then
  run rm -rf "$BIGBOSS_HOME"
  echo "✓ Removed $BIGBOSS_HOME"
else
  echo "  $BIGBOSS_HOME not found — skipping"
fi

# Remove project-scoped adapter files
for f in \
  ".cursor/rules/bigboss.mdc" \
  ".windsurf/rules/bigboss.md" \
  ".clinerules/bigboss.md"; do
  target="$PROJECT_DIR/$f"
  if [[ -f "$target" ]]; then
    run rm "$target"
    echo "✓ Removed $target"
  fi
done

# Remove BIGBOSS_HOME export from shell profile
for rc in "$HOME/.bashrc" "$HOME/.zshrc"; do
  if grep -q "BIGBOSS_HOME" "$rc" 2>/dev/null; then
    run sed -i '/BIGBOSS_HOME.*bigboss/d' "$rc"
    run sed -i '/^$/N;/^\n$/d' "$rc"   # remove trailing blank line left behind
    echo "✓ Removed BIGBOSS_HOME from $rc"
  fi
done

echo ""
echo "bigboss uninstalled."
echo "Note: Claude Code plugin and Gemini extension must be removed via their own CLIs:"
echo "  claude plugin remove bigboss"
echo "  gemini extensions uninstall bigboss"
