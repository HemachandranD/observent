#!/usr/bin/env python3
"""PostToolUse hook: mirror CI's checks the moment a file is edited.

Two classes of check, matching what CI runs:
  * Python in skills/observent/scripts, scripts, or tests -> ruff + mypy.
  * A docs / single-source file that the docs-consistency suite covers
    (references/*.md, SKILL.md, README.md, observent-eval.toml, and the
    observent_matrix.py source of truth) -> the docs-consistency pytest suite,
    so cross-file drift (matrix <-> README <-> code, image/version pins, the
    known-auto-instrumenting-deps table) surfaces on save, not in CI.

The scripts + references are the load-bearing surface of the plugin (CLAUDE.md >
Tech Stack, > Documentation Hygiene), so a lint nit, type regression, or doc
drift should surface on save. Exits 0 (silent) for files outside scope; exits 2
with the tool output on stderr when a check is unhappy, feeding it back to Claude.
Every check fails **open** (returns 0) when its tool isn't installed locally, so
the hook never blocks an edit just because ruff/mypy/pytest is missing.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys

# Mirrors the CI ruff/mypy invocation targets.
TARGET_RE = re.compile(r"/(skills/observent/scripts|scripts|tests)/[^/]+\.py$")

# Files whose edit can break the docs-consistency suite: the reference docs +
# SKILL.md, README.md, the eval command, and the grid's single source of truth.
DOCS_RE = re.compile(
    r"/(skills/observent/(references/[^/]+\.md|SKILL\.md)"
    r"|README\.md"
    r"|commands/observent-eval\.toml)$"
)
_SOURCE_OF_TRUTH = "/skills/observent/scripts/observent_matrix.py"


def _run(tool: str, file_path: str, root: str) -> str | None:
    """Run `tool check? <file>` and return its output if it reported a problem."""
    if shutil.which(tool) is None:
        return None  # Tool not installed locally; don't block the edit.
    cmd = [tool, "check", file_path] if tool == "ruff" else [tool, file_path]
    proc = subprocess.run(cmd, cwd=root, capture_output=True, text=True)
    if proc.returncode != 0:
        return f"{tool}:\n{proc.stdout}{proc.stderr}"
    return None


def _run_docs_consistency(root: str) -> str | None:
    """Run the docs-consistency suite and return its output if it failed.

    Fails open (returns None) when pytest isn't importable or collects nothing,
    so a missing pytest never blocks a docs edit.
    """
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", "tests/test_docs_consistency.py", "-q"],
        cwd=root,
        capture_output=True,
        text=True,
    )
    if proc.returncode == 0:
        return None
    combined = f"{proc.stdout}{proc.stderr}"
    # returncode 5 = no tests collected; a "No module named ... pytest" import
    # error = pytest not installed in this interpreter. Either way, fail open.
    pytest_missing = "No module named" in combined and "pytest" in combined
    if proc.returncode == 5 or pytest_missing:
        return None
    return f"docs-consistency (pytest tests/test_docs_consistency.py):\n{combined}"


def _affects_docs_consistency(norm: str) -> bool:
    return bool(DOCS_RE.search(norm)) or norm.endswith(_SOURCE_OF_TRUTH)


def main() -> int:
    try:
        event = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return 0

    file_path = (event.get("tool_input") or {}).get("file_path") or ""
    norm = "/" + file_path.replace("\\", "/").lstrip("/")
    root = os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()

    problems: list[str] = []

    # Python scripts/tests: ruff + mypy (same targets CI checks).
    if norm.endswith(".py") and TARGET_RE.search(norm):
        problems += [m for m in (_run("ruff", file_path, root), _run("mypy", file_path, root)) if m]

    # Docs / single-source edits: run the docs-consistency suite so mirror drift
    # (matrix <-> README <-> code) surfaces on save. observent_matrix.py hits both.
    if _affects_docs_consistency(norm):
        msg = _run_docs_consistency(root)
        if msg:
            problems.append(msg)

    if problems:
        sys.stderr.write("Lint / type-check / docs-consistency issues (same checks CI runs):\n\n")
        sys.stderr.write("\n".join(problems))
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
