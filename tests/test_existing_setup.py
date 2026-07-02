"""Tests for existing_setup.py — the scanner that decides extend-vs-replace by
finding pre-existing observability wiring in a user's project.
"""
from __future__ import annotations

from existing_setup import scan


def _names(detected):
    return {entry["name"] for entry in detected}


def test_detects_langfuse_import(tmp_path):
    (tmp_path / "app.py").write_text("from langfuse import Langfuse\n")
    report = scan(tmp_path)
    assert "langfuse" in _names(report["detected"])


def test_detects_phoenix_env_file(tmp_path):
    (tmp_path / ".env").write_text("PHOENIX_API_KEY=sk-123\n")
    report = scan(tmp_path)
    phoenix = next(e for e in report["detected"] if e["name"] == "phoenix")
    assert phoenix["env_files"]


def test_signoz_requires_high_signal_not_bare_mention(tmp_path):
    # A bare comment mentioning signoz must NOT count as configured.
    (tmp_path / "notes.py").write_text("# we might use signoz someday\n")
    report = scan(tmp_path)
    assert "signoz" not in _names(report["detected"])


def test_signoz_detected_on_access_token(tmp_path):
    (tmp_path / "conf.py").write_text('headers = {"signoz-access-token": "x"}\n')
    report = scan(tmp_path)
    assert "signoz" in _names(report["detected"])


def test_opentelemetry_classified_as_instrumentation(tmp_path):
    (tmp_path / "otel.py").write_text(
        "from opentelemetry.sdk.trace import TracerProvider\nTracerProvider()\n"
    )
    report = scan(tmp_path)
    otel = next(e for e in report["detected"] if e["name"] == "opentelemetry")
    assert otel["kind"] == "instrumentation"


def test_excluded_dirs_are_skipped(tmp_path):
    venv = tmp_path / ".venv" / "lib"
    venv.mkdir(parents=True)
    (venv / "dep.py").write_text("from langfuse import Langfuse\n")
    report = scan(tmp_path)
    assert "langfuse" not in _names(report["detected"])


def test_clean_project_detects_nothing(tmp_path):
    (tmp_path / "main.py").write_text("print('hello')\n")
    report = scan(tmp_path)
    assert report["detected"] == []
    assert report["self_scan_excluded"] is False


def test_scaffold_only_env_without_code(tmp_path):
    # Env-var names from an earlier incomplete attempt, but no instrumentation
    # code anywhere — SKILL.md Step 1.4's "scaffold_only" case.
    (tmp_path / ".env").write_text("PHOENIX_API_KEY=\n")
    report = scan(tmp_path)
    assert report["scaffold_only"] is True
    phoenix = next(e for e in report["detected"] if e["name"] == "phoenix")
    assert phoenix["instrumentation_code_found"] is False


def test_not_scaffold_only_when_code_present(tmp_path):
    (tmp_path / "app.py").write_text("import phoenix\nphoenix.otel.register()\n")
    (tmp_path / ".env").write_text("PHOENIX_API_KEY=sk-123\n")
    report = scan(tmp_path)
    assert report["scaffold_only"] is False
    phoenix = next(e for e in report["detected"] if e["name"] == "phoenix")
    assert phoenix["instrumentation_code_found"] is True


def test_scaffold_only_false_when_nothing_detected(tmp_path):
    (tmp_path / "main.py").write_text("print('hello')\n")
    report = scan(tmp_path)
    assert report["scaffold_only"] is False
