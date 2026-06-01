#!/usr/bin/env python3
"""PostToolUse hook: ruff + mypy a Python file the moment it's edited, mirroring
exactly what CI runs over skills/observent/scripts, scripts, and tests.

The scripts are the load-bearing logic of the plugin (CLAUDE.md > Tech Stack),
so a lint nit or type regression should surface on save, not in CI. Exits 0
(silent) for files outside the checked dirs; exits 2 with the tool output on
stderr when ruff or mypy is unhappy, feeding it back to Claude.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys

# Mirrors the CI invocation targets.
TARGET_RE = re.compile(r"/(skills/observent/scripts|scripts|tests)/[^/]+\.py$")


def _run(tool: str, file_path: str, root: str) -> str | None:
    """Run `tool check? <file>` and return its output if it reported a problem."""
    if shutil.which(tool) is None:
        return None  # Tool not installed locally; don't block the edit.
    cmd = [tool, "check", file_path] if tool == "ruff" else [tool, file_path]
    proc = subprocess.run(cmd, cwd=root, capture_output=True, text=True)
    if proc.returncode != 0:
        return f"{tool}:\n{proc.stdout}{proc.stderr}"
    return None


def main() -> int:
    try:
        event = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return 0

    file_path = (event.get("tool_input") or {}).get("file_path") or ""
    norm = "/" + file_path.replace("\\", "/").lstrip("/")
    if not norm.endswith(".py") or not TARGET_RE.search(norm):
        return 0

    root = os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
    problems = [msg for msg in (_run("ruff", file_path, root), _run("mypy", file_path, root)) if msg]
    if problems:
        sys.stderr.write("Lint / type-check issues (same checks CI runs):\n\n")
        sys.stderr.write("\n".join(problems))
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
