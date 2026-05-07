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
        "install_cmd": "claude plugin install HemachandranD/bigboss",
    }


def _gemini() -> ProviderInfo:
    return {
        "label": "Gemini CLI",
        "installed": _has_binary("gemini") or _dir_exists("~/.gemini"),
        "config_dir": str(Path("~/.gemini").expanduser()),
        "install_cmd": "gemini extensions install HemachandranD/bigboss",
    }


def _codex() -> ProviderInfo:
    return {
        "label": "OpenAI Codex CLI",
        "installed": _has_binary("codex") or _dir_exists("~/.codex"),
        "config_dir": str(Path("~/.codex").expanduser()),
        "install_cmd": "copy .codex/ into ~/.codex/extensions/bigboss/",
    }


def _cursor() -> ProviderInfo:
    return {
        "label": "Cursor",
        "installed": _has_binary("cursor") or _dir_exists("~/.cursor"),
        "config_dir": str(Path("~/.cursor").expanduser()),
        "install_cmd": "copy .cursor/rules/bigboss.mdc into <project>/.cursor/rules/",
    }


def _windsurf() -> ProviderInfo:
    return {
        "label": "Windsurf",
        "installed": _has_binary("windsurf") or _dir_exists("~/.codeium/windsurf"),
        "config_dir": str(Path("~/.codeium/windsurf").expanduser()),
        "install_cmd": "copy .windsurf/rules/bigboss.md into <project>/.windsurf/rules/",
    }


def _cline() -> ProviderInfo:
    return {
        "label": "Cline (VS Code extension)",
        "installed": _glob_any("~/.vscode/extensions", "saoudrizwan.claude-dev-*"),
        "config_dir": str(Path("~/.vscode/extensions").expanduser()),
        "install_cmd": "copy .clinerules/bigboss.md into <project>/.clinerules/",
    }


DETECTORS: dict[str, Callable[[], ProviderInfo]] = {
    "claude_code": _claude_code,
    "gemini": _gemini,
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
