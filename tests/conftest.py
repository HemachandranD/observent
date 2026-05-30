"""Make the plugin's stdlib-only scripts importable by name from the tests.

The scripts live in two trees (``skills/observent/scripts`` and ``scripts``);
both are added to ``sys.path`` so tests can ``import detect_framework`` etc.
without packaging the plugin.
"""
from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
for _p in (_ROOT / "skills" / "observent" / "scripts", _ROOT / "scripts"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))
