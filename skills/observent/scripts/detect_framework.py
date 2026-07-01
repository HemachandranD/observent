#!/usr/bin/env python3
"""Detect installed agentic frameworks and observability backends.

Detection layers (in order of confidence):
  1. Installed packages via importlib.util.find_spec - works regardless of
     pip/uv/poetry/conda.
  2. Declared dependencies parsed from pyproject.toml, requirements*.txt,
     Pipfile, setup.cfg.
  3. Import statements grepped from *.py files in cwd.

Output: JSON to stdout. Used by SKILL.md dynamic context.
"""
from __future__ import annotations

import importlib.util
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

from observent_matrix import (
    auto_instrumenting_deps,
    backend_detection_modules,
    framework_detection_modules,
)

# Derived from the single source of truth in observent_matrix.py (see CLAUDE.md
# "Adding a new framework / backend"). FRAMEWORKS excludes the non-detectable
# Custom path; BACKENDS adds the detection-only ``opentelemetry`` signal and
# omits SigNoz (a service, not a pip package).
FRAMEWORKS: dict[str, list[str]] = framework_detection_modules()

BACKENDS: dict[str, list[str]] = backend_detection_modules()

# Third-party deps that carry their own dormant OTel instrumentation (gap #15).
AUTO_INSTRUMENTING_DEPS: list[dict[str, object]] = auto_instrumenting_deps()

INSTRUMENTORS: dict[str, str] = {
    "openinference-instrumentation-langchain": "openinference.instrumentation.langchain",
    "openinference-instrumentation-crewai": "openinference.instrumentation.crewai",
    "openinference-instrumentation-openai": "openinference.instrumentation.openai",
    "openinference-instrumentation-anthropic": "openinference.instrumentation.anthropic",
    "openinference-instrumentation-llama-index": "openinference.instrumentation.llama_index",
    "openinference-instrumentation-smolagents": "openinference.instrumentation.smolagents",
    "openinference-instrumentation-google-adk": "openinference.instrumentation.google_adk",
}

WEB_FRAMEWORKS: dict[str, list[str]] = {
    "fastapi": ["fastapi"],
    "starlette": ["starlette"],
    "flask": ["flask"],
    "django": ["django"],
}


def _is_installed(module: str) -> bool:
    try:
        return importlib.util.find_spec(module) is not None
    except (ImportError, ValueError):
        return False


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""


def _parse_pyproject(path: Path) -> set[str]:
    text = _read_text(path)
    if not text:
        return set()
    deps: set[str] = set()
    for match in re.finditer(r'["\']([A-Za-z0-9_.\-]+)(?:[<>=!~][^"\']*)?["\']', text):
        deps.add(match.group(1).lower())
    return deps


def _parse_requirements(path: Path) -> set[str]:
    deps: set[str] = set()
    for line in _read_text(path).splitlines():
        line = line.strip()
        if not line or line.startswith("#") or line.startswith("-"):
            continue
        match = re.match(r"^([A-Za-z0-9_.\-]+)", line)
        if match:
            deps.add(match.group(1).lower())
    return deps


def _gather_declared_deps(root: Path) -> set[str]:
    deps: set[str] = set()
    for name in ("pyproject.toml", "Pipfile", "setup.cfg"):
        path = root / name
        if path.exists():
            deps |= _parse_pyproject(path)
    for req in root.glob("requirements*.txt"):
        deps |= _parse_requirements(req)
    return deps


def _gather_imports(root: Path, max_files: int = 200) -> tuple[set[str], bool]:
    imports: set[str] = set()
    pattern = re.compile(r"^\s*(?:from|import)\s+([A-Za-z_][\w.]*)")
    count = 0
    truncated = False
    for py in root.rglob("*.py"):
        if any(part.startswith(".") or part in {"venv", ".venv", "env", "__pycache__"} for part in py.parts):
            continue
        if count >= max_files:
            truncated = True
            break
        count += 1
        for line in _read_text(py).splitlines():
            match = pattern.match(line)
            if match:
                imports.add(match.group(1).split(".")[0])
    return imports, truncated


def _name_match(needle: str, haystack: set[str]) -> bool:
    needle_norm = needle.replace("_", "-").lower()
    for h in haystack:
        if h.replace("_", "-").lower() == needle_norm:
            return True
    return False


def _docker() -> dict[str, bool]:
    """Report whether Docker + Compose are usable for local backend provisioning.

    Side-effect-free: probes the daemon with `docker version` and `docker compose
    version`; never touches containers. Feeds spec.detection.docker_available so the
    skill knows whether it can offer to provision an unreachable self-host backend.
    See references/self_host.md.
    """
    available = False
    compose_available = False
    if shutil.which("docker"):
        try:
            available = (
                subprocess.run(
                    ["docker", "version"],
                    capture_output=True,
                    timeout=10,
                ).returncode
                == 0
            )
        except (OSError, subprocess.SubprocessError):
            available = False
        if available:
            try:
                compose_available = (
                    subprocess.run(
                        ["docker", "compose", "version"],
                        capture_output=True,
                        timeout=10,
                    ).returncode
                    == 0
                )
            except (OSError, subprocess.SubprocessError):
                compose_available = False
    return {"available": available, "compose_available": compose_available}


def detect(root: Path) -> dict[str, Any]:
    declared = _gather_declared_deps(root)
    imports, imports_truncated = _gather_imports(root)

    frameworks_found: list[dict[str, Any]] = []
    for label, modules in FRAMEWORKS.items():
        sources: list[str] = []
        if any(_is_installed(m) for m in modules):
            sources.append("installed")
        if any(_name_match(m, declared) for m in modules):
            sources.append("declared")
        if any(m in imports for m in modules):
            sources.append("imported")
        if sources:
            frameworks_found.append({"name": label, "sources": sources})

    backends_found: list[dict[str, Any]] = []
    for label, modules in BACKENDS.items():
        sources = []
        if any(_is_installed(m) for m in modules):
            sources.append("installed")
        if any(_name_match(m, declared) for m in modules):
            sources.append("declared")
        if sources:
            backends_found.append({"name": label, "sources": sources})

    instrumentors_found = [
        {"package": pkg} for pkg, mod in INSTRUMENTORS.items() if _is_installed(mod)
    ]

    # Deps whose own OTel instrumentation will auto-activate once opentelemetry-sdk
    # is installed. Surfaced so the spec phase can offer keep-vs-disable (env_var).
    auto_instrumenting_found: list[dict[str, Any]] = []
    for dep in AUTO_INSTRUMENTING_DEPS:
        dep_modules = dep["modules"]
        assert isinstance(dep_modules, list)
        sources = []
        if any(_is_installed(m) for m in dep_modules):
            sources.append("installed")
        if any(_name_match(m, declared) for m in dep_modules):
            sources.append("declared")
        if any(m in imports for m in dep_modules):
            sources.append("imported")
        if sources:
            auto_instrumenting_found.append(
                {
                    "name": dep["slug"],
                    "display": dep["display"],
                    "env_var": dep["env_var"],
                    "enabled_by_default": dep["enabled_by_default"],
                    "sources": sources,
                }
            )

    web_frameworks_found: list[dict[str, Any]] = []
    for label, modules in WEB_FRAMEWORKS.items():
        sources = []
        if any(_is_installed(m) for m in modules):
            sources.append("installed")
        if any(_name_match(m, declared) for m in modules):
            sources.append("declared")
        if any(m in imports for m in modules):
            sources.append("imported")
        if sources:
            web_frameworks_found.append({"name": label, "sources": sources})

    return {
        "python": sys.version.split()[0],
        "cwd": str(root),
        "frameworks": frameworks_found,
        "backends": backends_found,
        "instrumentors": instrumentors_found,
        "auto_instrumenting_deps": auto_instrumenting_found,
        "web_frameworks": web_frameworks_found,
        "docker": _docker(),
        "imports_truncated": imports_truncated,
    }


def main() -> int:
    root = Path.cwd()
    report = detect(root)
    json.dump(report, sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
