#!/usr/bin/env python3
"""Detect pre-existing observability configuration in the user's project.

Greps for imports, env var references, and OTel TracerProvider setup.
Reports which backend(s) appear to be already configured so SKILL.md can
offer extend-vs-replace instead of blindly overwriting.

Output: JSON to stdout.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

IMPORT_PATTERNS: dict[str, list[re.Pattern[str]]] = {
    "phoenix": [
        re.compile(r"^\s*(?:from|import)\s+phoenix\b"),
        re.compile(r"^\s*(?:from|import)\s+arize_phoenix\b"),
        re.compile(r"\bphoenix\.otel\.register\b"),
        re.compile(r"\bpx\.launch_app\b"),
    ],
    "langfuse": [
        re.compile(r"^\s*(?:from|import)\s+langfuse\b"),
        re.compile(r"\blangfuse\.langchain\b"),
        re.compile(r"\blangfuse\.decorators\b"),
        re.compile(r"\bCallbackHandler\b.*langfuse"),
    ],
    "signoz": [
        re.compile(r"\bsignoz\b", re.IGNORECASE),
        re.compile(r"signoz-access-token", re.IGNORECASE),
    ],
    "opentelemetry": [
        re.compile(r"^\s*(?:from|import)\s+opentelemetry\b"),
        re.compile(r"\bTracerProvider\(\)"),
        re.compile(r"\bBatchSpanProcessor\("),
        re.compile(r"\bOTLPSpanExporter\("),
    ],
    "openinference": [
        re.compile(r"^\s*(?:from|import)\s+openinference\b"),
    ],
}

ENV_VAR_PATTERNS: dict[str, re.Pattern[str]] = {
    "phoenix": re.compile(r"\bPHOENIX_(?:API_KEY|COLLECTOR_ENDPOINT|PROJECT_NAME)\b"),
    "langfuse": re.compile(r"\bLANGFUSE_(?:PUBLIC_KEY|SECRET_KEY|HOST)\b"),
    "signoz": re.compile(r"\bSIGNOZ_(?:ENDPOINT|INGESTION_KEY)\b"),
    "opentelemetry": re.compile(r"\bOTEL_(?:EXPORTER_OTLP_ENDPOINT|SERVICE_NAME|RESOURCE_ATTRIBUTES)\b"),
}

EXCLUDE_PARTS = {".git", ".venv", "venv", "env", "__pycache__", "node_modules", ".tox", ".mypy_cache", ".ruff_cache", ".claude"}
SCAN_SUFFIXES = {".py", ".env", ".sh", ".yaml", ".yml", ".toml", ".cfg", ".ini"}


def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""


def _scan_file(path: Path, hits: dict[str, dict[str, list[str]]]) -> None:
    text = _read(path)
    if not text:
        return
    for backend, patterns in IMPORT_PATTERNS.items():
        for pat in patterns:
            if pat.search(text):
                hits[backend]["imports"].append(str(path))
                break
    for backend, pat in ENV_VAR_PATTERNS.items():
        if pat.search(text):
            hits[backend]["env_vars"].append(str(path))
    # Look for env files specifically
    if path.name.startswith(".env") or path.suffix == ".env":
        for backend, pat in ENV_VAR_PATTERNS.items():
            if pat.search(text):
                hits[backend]["env_files"].append(str(path))


def scan(root: Path, max_files: int = 500) -> dict[str, Any]:
    hits: dict[str, dict[str, list[str]]] = {
        backend: {"imports": [], "env_vars": [], "env_files": []}
        for backend in IMPORT_PATTERNS.keys()
    }
    count = 0
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if any(part in EXCLUDE_PARTS for part in path.parts):
            continue
        if path.suffix not in SCAN_SUFFIXES and not path.name.startswith(".env"):
            continue
        if count >= max_files:
            break
        count += 1
        _scan_file(path, hits)

    detected = []
    for backend, found in hits.items():
        if any(found.values()):
            detected.append({
                "backend": backend,
                "imports": sorted(set(found["imports"]))[:10],
                "env_vars_in_files": sorted(set(found["env_vars"]))[:10],
                "env_files": sorted(set(found["env_files"]))[:10],
            })

    return {
        "cwd": str(root),
        "files_scanned": count,
        "detected": detected,
    }


def main() -> int:
    report = scan(Path.cwd())
    json.dump(report, sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
