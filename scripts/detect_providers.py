#!/usr/bin/env python3
"""Detect which AI coding providers/IDEs are installed on this system.

Outputs JSON to stdout:
  {"providers": {provider_id: {label, installed, config_dir, install_cmd}}}

Exit code is always 0 — the caller reads JSON to determine presence.
"""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path
from typing import Callable


def _has_binary(cmd: str) -> bool:
    return shutil.which(cmd) is not None


def _dir_exists(path: str) -> bool:
    return Path(path).expanduser().is_dir()


def _glob_any(directory: str, pattern: str) -> bool:
    d = Path(directory).expanduser()
    return d.is_dir() and any(True for _ in d.glob(pattern))


ProviderInfo = dict[str, object]


def _claude_code() -> ProviderInfo:
    return {
        "label": "Claude Code",
        "installed": _has_binary("claude") or _dir_exists("~/.claude"),
        "config_dir": str(Path("~/.claude").expanduser()),
        "install_cmd": "claude plugin install HemachandranD/observent",
    }


def _antigravity() -> ProviderInfo:
    # Antigravity replaced Gemini CLI (Google, May 2026). The CLI and the
    # desktop IDE share infrastructure and both read AGENTS.md;
    # Antigravity still uses the ~/.gemini home for global config + skills.
    return {
        "label": "Google Antigravity",
        "installed": (
            _has_binary("antigravity")
            or _dir_exists("~/.antigravity")
            or _dir_exists("~/.gemini/antigravity-cli")
        ),
        "config_dir": str(Path("~/.antigravity").expanduser()),
        "install_cmd": "antigravity extensions install https://github.com/HemachandranD/observent --auto-update",
    }


def _copilot() -> ProviderInfo:
    # GitHub Copilot reads the same instruction files from both the CLI
    # (`copilot` / `gh copilot`) and the IDE extension (VS Code / JetBrains).
    ext_dirs = ("~/.vscode/extensions", "~/.vscode-insiders/extensions")
    has_ide = any(_glob_any(d, "github.copilot-*") for d in ext_dirs)
    return {
        "label": "GitHub Copilot",
        "installed": _has_binary("copilot") or _has_binary("gh") or has_ide,
        "config_dir": str(Path("~/.config/github-copilot").expanduser()),
        "install_cmd": "copy .github/copilot-instructions.md into <project>/.github/",
    }


def _codex() -> ProviderInfo:
    return {
        "label": "OpenAI Codex CLI",
        "installed": _has_binary("codex") or _dir_exists("~/.codex"),
        "config_dir": str(Path("~/.codex").expanduser()),
        "install_cmd": "copy .codex/ into ~/.codex/extensions/observent/",
    }


def _cursor() -> ProviderInfo:
    return {
        "label": "Cursor",
        "installed": _has_binary("cursor") or _dir_exists("~/.cursor"),
        "config_dir": str(Path("~/.cursor").expanduser()),
        "install_cmd": "copy .cursor/rules/observent.mdc into <project>/.cursor/rules/",
    }


def _windsurf() -> ProviderInfo:
    return {
        "label": "Windsurf",
        "installed": _has_binary("windsurf") or _dir_exists("~/.codeium/windsurf"),
        "config_dir": str(Path("~/.codeium/windsurf").expanduser()),
        "install_cmd": "copy .windsurf/rules/observent.md into <project>/.windsurf/rules/",
    }


def _cline() -> ProviderInfo:
    ext_dirs = ("~/.vscode/extensions", "~/.vscode-insiders/extensions")
    installed = any(_glob_any(d, "saoudrizwan.claude-dev-*") for d in ext_dirs)
    config_dir = next(
        (str(Path(d).expanduser()) for d in ext_dirs if _dir_exists(d)),
        str(Path(ext_dirs[0]).expanduser()),
    )
    return {
        "label": "Cline (VS Code extension)",
        "installed": installed,
        "config_dir": config_dir,
        "install_cmd": "copy .clinerules/observent.md into <project>/.clinerules/",
    }


DETECTORS: dict[str, Callable[[], ProviderInfo]] = {
    "claude_code": _claude_code,
    "antigravity": _antigravity,
    "copilot": _copilot,
    "codex": _codex,
    "cursor": _cursor,
    "windsurf": _windsurf,
    "cline": _cline,
}


def main() -> None:
    results: dict[str, ProviderInfo] = {pid: fn() for pid, fn in DETECTORS.items()}
    json.dump({"providers": results}, sys.stdout, indent=2)
    print()


if __name__ == "__main__":
    main()
