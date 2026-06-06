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

# Write the canonical cross-tool AGENTS.md into the project (substituting
# ${OBSERVENT_HOME}). Idempotent — several providers read AGENTS.md natively,
# so the first one to need it writes it and the rest are no-ops.
AGENTS_WRITTEN=false
write_agents_md() {
  $AGENTS_WRITTEN && { echo "    ↳ AGENTS.md already written this run"; return; }
  # Avoid wrapping the redirect in `run` (the outer shell honors `>` even in dry-run).
  if $DRY_RUN; then
    echo "[dry-run] sed 's|\${OBSERVENT_HOME}|$OBSERVENT_HOME|g' $REPO_DIR/AGENTS.md > $PROJECT_DIR/AGENTS.md"
  else
    sed "s|\${OBSERVENT_HOME}|$OBSERVENT_HOME|g" "$REPO_DIR/AGENTS.md" > "$PROJECT_DIR/AGENTS.md"
  fi
  echo "    ✓ AGENTS.md → $PROJECT_DIR/AGENTS.md"
  AGENTS_WRITTEN=true
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
    # Prefer the marketplace form (self-contained, supports `claude plugin
    # update`, survives deleting this clone). Fall back to the local repo path
    # only if it fails — e.g. offline, or the marketplace isn't reachable.
    if $DRY_RUN; then
      echo "[dry-run] claude plugin install HemachandranD/observent (fallback: claude plugin install $REPO_DIR)"
    elif claude plugin install HemachandranD/observent; then
      echo "    ✓ Claude Code plugin installed (marketplace)"
    else
      echo "    ↳ marketplace install failed — falling back to local path"
      claude plugin install "$REPO_DIR"
      echo "    ✓ Claude Code plugin installed (local path)"
    fi
    INSTALLED+=("Claude Code")
  fi
fi

# ── 4. Google Antigravity (CLI + IDE) ────────────────────────────────────────
if is_installed antigravity; then
  echo "  Detected: Google Antigravity"
  # AGENTS.md in the project is read by both the Antigravity CLI and the
  # desktop IDE.
  write_agents_md
  if command -v antigravity &>/dev/null; then
    run antigravity extensions install "$REPO_DIR"
    echo "    ✓ Antigravity extension installed"
  else
    echo "    ↳ 'antigravity' not on PATH — skipped extension install (AGENTS.md still applies)"
  fi
  INSTALLED+=("Antigravity")
fi

# ── 5. OpenAI Codex (CLI + IDE) ───────────────────────────────────────────────
if is_installed codex; then
  echo "  Detected: OpenAI Codex (CLI + IDE)"
  # Both the Codex CLI (`codex` / ~/.codex) and the IDE extension
  # (openai.chatgpt) read the project-root AGENTS.md natively — no separate
  # extension/context file is needed.
  write_agents_md
  INSTALLED+=("Codex (CLI + IDE)")
fi

# ── 6. Providers that read AGENTS.md natively (Windsurf / GitHub Copilot) ──────
if is_installed windsurf; then
  echo "  Detected: Windsurf"
  # Windsurf/Cascade auto-discovers the project-root AGENTS.md and feeds it into
  # the same rules engine as the legacy .windsurf/rules/.
  write_agents_md
  INSTALLED+=("Windsurf")
fi

# GitHub Copilot agent mode reads the project-root AGENTS.md (IDE + CLI).
if is_installed copilot; then
  echo "  Detected: GitHub Copilot"
  write_agents_md
  INSTALLED+=("GitHub Copilot")
fi

# ── 7. Tools needing their own scoped rule file (Cursor / Cline) ──────────────
# These are thin pointers to ${OBSERVENT_HOME}/SKILL.md, not duplicated bodies:
#   • Cursor — keeps its `globs: **/*.py` auto-attach scoping.
#   • Cline  — does not auto-read project-root AGENTS.md, so it needs a rule file.
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

if is_installed cline; then
  echo "  Detected: Cline"
  _install_rule "Cline" ".clinerules/observent.md" ".clinerules" "observent.md"
fi

# ── 8. Export OBSERVENT_HOME in shell profile ────────────────────────────────────
SHELL_RC="$HOME/.bashrc"
[[ "${SHELL:-}" == */zsh ]] && SHELL_RC="$HOME/.zshrc"
if ! grep -q "OBSERVENT_HOME" "$SHELL_RC" 2>/dev/null; then
  run bash -c "echo '' >> \"$SHELL_RC\""
  run bash -c "echo 'export OBSERVENT_HOME=\"$OBSERVENT_HOME\"  # observent' >> \"$SHELL_RC\""
  echo "  ✓ OBSERVENT_HOME exported in $SHELL_RC (run: source $SHELL_RC)"
fi

# ── 9. Summary ─────────────────────────────────────────────────────────────────
echo ""
if [[ ${#INSTALLED[@]} -gt 0 ]]; then
  echo "observent installed for: ${INSTALLED[*]}"
  echo "  Scripts: $OBSERVENT_HOME/scripts/"
else
  echo "No supported providers were detected."
  echo "Install Claude Code, Antigravity, GitHub Copilot, Codex, Cursor, Windsurf, or Cline, then re-run."
fi
