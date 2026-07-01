#!/usr/bin/env python3
"""PostToolUse hook: run the docs-consistency suite whenever an 9x7 grid file is
edited, so matrix/pin drift is caught in-loop instead of minutes later in CI.

Reads the Claude Code hook JSON event on stdin. Exits 0 (silent) for files that
aren't part of the grid; exits 2 with the pytest output on stderr when the
consistency suite fails, which feeds the failure back to Claude.

See CLAUDE.md "Documentation Hygiene" — matrix.md is canonical and its grid +
version pins are mirrored across SKILL.md, README.md, and examples.md.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys

# The files whose edits can introduce grid / pin drift.
GRID_RE = re.compile(r"/(matrix|SKILL|README|examples)\.md$", re.IGNORECASE)


def main() -> int:
    try:
        event = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return 0  # Not a well-formed event; never block on hook plumbing.

    file_path = (event.get("tool_input") or {}).get("file_path") or ""
    norm = "/" + file_path.replace("\\", "/").lstrip("/")
    if not GRID_RE.search(norm):
        return 0

    root = os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
    test = os.path.join(root, "tests", "test_docs_consistency.py")
    if not os.path.exists(test):
        return 0

    proc = subprocess.run(
        [sys.executable, "-m", "pytest", test, "-q"],
        cwd=root,
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        sys.stderr.write(
            "Docs-consistency check FAILED after editing a grid file "
            f"({file_path}).\n"
            "Fix the doc or code so the framework x backend grid and version "
            "pins agree across matrix.md / README.md / SKILL.md / examples.md "
            "(see CLAUDE.md > Documentation Hygiene):\n\n"
        )
        sys.stderr.write(proc.stdout + proc.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
