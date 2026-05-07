#!/usr/bin/env bash
# observent installer — detects installed providers and wires up each one.
# Usage: bash install.sh [--project-dir <path>] [--dry-run]
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OBSERVENT_HOME="${OBSERVENT_HOME:-$HOME/.observent}"
PROJECT_DIR="${PROJECT_DIR:-$PWD}"
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

echo "observent installer"
echo "  Repo:         $REPO_DIR"
echo "  OBSERVENT_HOME: $OBSERVENT_HOME"
echo "  Project:      $PROJECT_DIR"
$DRY_RUN && echo "  Mode:         dry-run"
echo ""

# ── 1. Copy core skill files to OBSERVENT_HOME ──────────────────────────────────
run mkdir -p "$OBSERVENT_HOME"
run cp -r "$REPO_DIR/skills/observent/." "$OBSERVENT_HOME/"
echo "✓ Skill files → $OBSERVENT_HOME"

# ── 2. Detect providers ────────────────────────────────────────────────────────
PROVIDER_JSON="$(python3 "$REPO_DIR/scripts/detect_providers.py")"

is_installed() {
  echo "$PROVIDER_JSON" | python3 -c "
import json, sys
data = json.load(sys.stdin)
sys.exit(0 if data['providers'].get('$1', {}).get('installed') else 1)
"
}

INSTALLED=()

# ── 3. Claude Code ─────────────────────────────────────────────────────────────
if is_installed claude_code; then
  echo "  Detected: Claude Code"
  if ! command -v claude &>/dev/null; then
    echo "    ↳ ~/.claude found but 'claude' not on PATH — skipping plugin install"
  elif claude plugin list 2>/dev/null | grep -q "observent"; then
    echo "    ↳ already installed — skipping"
    INSTALLED+=("Claude Code")
  else
    run claude plugin install "$REPO_DIR"
    echo "    ✓ Claude Code plugin installed"
    INSTALLED+=("Claude Code")
  fi
fi

# ── 4. Gemini CLI ──────────────────────────────────────────────────────────────
if is_installed gemini; then
  echo "  Detected: Gemini CLI"
  if ! command -v gemini &>/dev/null; then
    echo "    ↳ ~/.gemini found but 'gemini' not on PATH — skipping extension install"
  else
    run gemini extensions install "$REPO_DIR"
    echo "    ✓ Gemini extension installed"
    INSTALLED+=("Gemini CLI")
  fi
fi

# ── 5. OpenAI Codex CLI ───────────────────────────────────────────────────────
if is_installed codex; then
  echo "  Detected: OpenAI Codex CLI"
  CODEX_EXT="$HOME/.codex/extensions/observent"
  run mkdir -p "$CODEX_EXT"
  run cp -r "$REPO_DIR/.codex/." "$CODEX_EXT/"
  echo "    ✓ Codex extension → $CODEX_EXT"
  INSTALLED+=("Codex CLI")
fi

# ── 6. Project-scoped adapters (Cursor / Windsurf / Cline) ────────────────────
_install_rule() {
  local provider="$1" src="$2" dst_dir="$3" dst_file="$4"
  local dst="$PROJECT_DIR/$dst_dir/$dst_file"
  run mkdir -p "$PROJECT_DIR/$dst_dir"
  # Substitute ${OBSERVENT_HOME} with the actual path. Avoid wrapping the
  # redirect in `run` — the outer shell would honor `>` even in dry-run mode
  # and write the dry-run echo text into the destination file.
  if $DRY_RUN; then
    echo "[dry-run] sed 's|\${OBSERVENT_HOME}|$OBSERVENT_HOME|g' $REPO_DIR/$src > $dst"
  else
    sed "s|\${OBSERVENT_HOME}|$OBSERVENT_HOME|g" "$REPO_DIR/$src" > "$dst"
  fi
  echo "    ✓ $provider rule → $dst"
  INSTALLED+=("$provider")
}

if is_installed cursor; then
  echo "  Detected: Cursor"
  _install_rule "Cursor" ".cursor/rules/observent.mdc" ".cursor/rules" "observent.mdc"
fi

if is_installed windsurf; then
  echo "  Detected: Windsurf"
  _install_rule "Windsurf" ".windsurf/rules/observent.md" ".windsurf/rules" "observent.md"
fi

if is_installed cline; then
  echo "  Detected: Cline"
  _install_rule "Cline" ".clinerules/observent.md" ".clinerules" "observent.md"
fi

# ── 7. Export OBSERVENT_HOME in shell profile ────────────────────────────────────
SHELL_RC="$HOME/.bashrc"
[[ "${SHELL:-}" == */zsh ]] && SHELL_RC="$HOME/.zshrc"
if ! grep -q "OBSERVENT_HOME" "$SHELL_RC" 2>/dev/null; then
  run bash -c "echo '' >> \"$SHELL_RC\""
  run bash -c "echo 'export OBSERVENT_HOME=\"$OBSERVENT_HOME\"  # observent' >> \"$SHELL_RC\""
  echo "  ✓ OBSERVENT_HOME exported in $SHELL_RC (run: source $SHELL_RC)"
fi

# ── 8. Summary ─────────────────────────────────────────────────────────────────
echo ""
if [[ ${#INSTALLED[@]} -gt 0 ]]; then
  echo "observent installed for: ${INSTALLED[*]}"
  echo "  Scripts: $OBSERVENT_HOME/scripts/"
else
  echo "No supported providers were detected."
  echo "Install Claude Code, Gemini CLI, Codex CLI, Cursor, Windsurf, or Cline, then re-run."
fi
