"""Tests for detect_framework.py — the declared-dep and import scanners that
decide which frameworks/backends the skill offers to instrument.

Detection is exercised against synthetic project trees written to ``tmp_path``
so the assertions don't depend on what's pip-installed in CI.
"""
from __future__ import annotations

import detect_framework
from detect_framework import (
    _name_match,
    _parse_pyproject,
    _parse_requirements,
    detect,
)


def _names(found):
    return {entry["name"] for entry in found}


def test_requirements_detects_framework_and_backend(tmp_path):
    (tmp_path / "requirements.txt").write_text(
        "langgraph==1.2.0\nlangfuse>=4.0\n# a comment\n-e .\n"
    )
    report = detect(tmp_path)
    assert "langgraph" in _names(report["frameworks"])
    assert "langfuse" in _names(report["backends"])
    # Declared-only deps are tagged as such.
    lg = next(e for e in report["frameworks"] if e["name"] == "langgraph")
    assert "declared" in lg["sources"]


def test_pyproject_dependencies_detected(tmp_path):
    (tmp_path / "pyproject.toml").write_text(
        '[project]\ndependencies = ["crewai>=1.0", "arize-phoenix==15.10.0"]\n'
    )
    report = detect(tmp_path)
    assert "crewai" in _names(report["frameworks"])
    assert "phoenix" in _names(report["backends"])


def test_imports_detected_from_source(tmp_path):
    (tmp_path / "app.py").write_text(
        "import os\nfrom smolagents import CodeAgent\nimport fastapi\n"
    )
    report = detect(tmp_path)
    assert "smolagents" in _names(report["frameworks"])
    assert "fastapi" in _names(report["web_frameworks"])


def test_empty_project_detects_nothing(tmp_path, monkeypatch):
    # Pin installed-package probing off so the test is deterministic regardless
    # of what happens to be pip-installed in the runner (declared/imported
    # detection is what an empty project should surface — i.e. nothing).
    monkeypatch.setattr(detect_framework, "_is_installed", lambda module: False)
    report = detect(tmp_path)
    assert report["frameworks"] == []
    assert report["backends"] == []
    assert report["python"]  # always reported


def test_auto_instrumenting_dep_detected_with_env_gate(tmp_path):
    # a2a-sdk ships dormant OTel instrumentation that wakes once opentelemetry is
    # importable; the detector must surface it plus its documented env-var gate.
    (tmp_path / "requirements.txt").write_text("a2a-sdk>=0.2\n")
    report = detect(tmp_path)
    found = report["auto_instrumenting_deps"]
    assert "a2a-sdk" in {e["name"] for e in found}
    a2a = next(e for e in found if e["name"] == "a2a-sdk")
    assert a2a["env_var"] == "OTEL_INSTRUMENTATION_A2A_SDK_ENABLED"
    assert a2a["enabled_by_default"] is True
    assert "declared" in a2a["sources"]


def test_no_auto_instrumenting_deps_in_clean_project(tmp_path, monkeypatch):
    monkeypatch.setattr(detect_framework, "_is_installed", lambda module: False)
    report = detect(tmp_path)
    assert report["auto_instrumenting_deps"] == []


def test_name_match_normalizes_separators_and_case():
    assert _name_match("llama_index", {"LLAMA-INDEX"})
    assert _name_match("elastic-apm", {"elastic_apm"})
    assert not _name_match("crewai", {"langgraph"})


def test_parse_requirements_skips_comments_and_flags():
    deps = _parse_requirements_text(
        "langgraph==1.0\n\n# comment\n-r other.txt\nLangFuse>=4\n"
    )
    assert "langgraph" in deps
    assert "langfuse" in deps  # lowercased
    assert not any(d.startswith(("#", "-")) for d in deps)


def test_parse_pyproject_extracts_quoted_names():
    deps = _parse_pyproject_text('dependencies = ["crewai>=1.0", "anthropic==0.1"]')
    assert {"crewai", "anthropic"} <= deps


def test_every_framework_module_is_nonempty():
    # Each FRAMEWORKS/BACKENDS entry must list at least one module to probe.
    for modules in detect_framework.FRAMEWORKS.values():
        assert modules
    for modules in detect_framework.BACKENDS.values():
        assert modules


# --- helpers that write to a temp file so the path-based parsers can run ----


def _parse_requirements_text(text, tmp_path_factory=None):
    import tempfile
    from pathlib import Path

    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / "requirements.txt"
        p.write_text(text)
        return _parse_requirements(p)


def _parse_pyproject_text(text):
    import tempfile
    from pathlib import Path

    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / "pyproject.toml"
        p.write_text(text)
        return _parse_pyproject(p)
