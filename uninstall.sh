#!/usr/bin/env bash
# observent uninstaller — removes OBSERVENT_HOME and project-scoped adapter files.
# Usage: bash uninstall.sh [--project-dir <path>] [--dry-run]
set -euo pipefail

PROJECT_DIR="${PROJECT_DIR:-$PWD}"
OBSERVENT_HOME="${OBSERVENT_HOME:-$HOME/.observent}"
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

echo "observent uninstaller"
$DRY_RUN && echo "  Mode: dry-run"
echo ""

# Remove OBSERVENT_HOME
if [[ -d "$OBSERVENT_HOME" ]]; then
  run rm -rf "$OBSERVENT_HOME"
  echo "✓ Removed $OBSERVENT_HOME"
else
  echo "  $OBSERVENT_HOME not found — skipping"
fi

# Remove project-scoped adapter files
for f in \
  ".cursor/rules/observent.mdc" \
  ".windsurf/rules/observent.md" \
  ".clinerules/observent.md" \
  ".github/copilot-instructions.md" \
  "AGENTS.md"; do
  target="$PROJECT_DIR/$f"
  if [[ -f "$target" ]]; then
    run rm "$target"
    echo "✓ Removed $target"
  fi
done

# Remove OBSERVENT_HOME export from shell profile.
# Use `sed -i.bak` for GNU/BSD portability (macOS BSD sed needs a backup
# extension; GNU sed accepts it too), then drop the .bak file.
for rc in "$HOME/.bashrc" "$HOME/.zshrc"; do
  if grep -q "OBSERVENT_HOME" "$rc" 2>/dev/null; then
    run sed -i.bak '/OBSERVENT_HOME.*observent/d' "$rc"
    run sed -i.bak '/^$/N;/^\n$/d' "$rc"   # remove trailing blank line left behind
    run rm -f "$rc.bak"
    echo "✓ Removed OBSERVENT_HOME from $rc"
  fi
done

echo ""
echo "observent uninstalled."
echo "Note: Claude Code plugin and Antigravity extension must be removed via their own CLIs:"
echo "  claude plugin remove observent"
echo "  antigravity extensions uninstall observent"
