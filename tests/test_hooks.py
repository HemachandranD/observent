"""Tests for the three Claude Code plugin hook scripts.

These run on the hottest paths in the plugin — ``session_start_detect`` on every
session start, ``prompt_nudge`` on every prompt, ``posttooluse_validate`` after
every Edit/Write/MultiEdit — and are wired up via ``.claude-plugin/plugin.json``.
Each is fail-safe (any unexpected error exits 0), which is exactly why behaviour
needs a test: a regression would degrade silently rather than error.

The hooks read a JSON payload from stdin, may print a JSON ``hookSpecificOutput``
block to stdout, and signal back to Claude via exit code (0 = pass-through,
2 = surface stderr this turn). Tests drive ``main()`` directly with a stubbed
stdin and assert that contract.
"""
from __future__ import annotations

import io
import json
import re
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

import posttooluse_validate
import prompt_nudge
import pytest
import session_start_detect


def _run(
    module: ModuleType,
    payload: dict[str, Any] | None,
    monkeypatch: pytest.MonkeyPatch,
    *,
    raw: str | None = None,
) -> int:
    """Feed ``payload`` (or ``raw`` text) to a hook's ``main()`` over stdin."""
    text = raw if raw is not None else json.dumps(payload)
    monkeypatch.setattr(sys, "stdin", io.StringIO(text))
    return int(module.main())


# --- posttooluse_validate -------------------------------------------------


def test_posttooluse_passes_valid_observent_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    f = tmp_path / "observent_otel.py"
    f.write_text("x = 1\n")
    rc = _run(posttooluse_validate, {"tool_input": {"file_path": str(f)}}, monkeypatch)
    assert rc == 0
    assert capsys.readouterr().err == ""


def test_posttooluse_flags_syntax_error_in_observent_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    f = tmp_path / "observent_capture.py"
    f.write_text("def broken(:\n")  # invalid syntax
    rc = _run(posttooluse_validate, {"tool_input": {"file_path": str(f)}}, monkeypatch)
    assert rc == 2
    err = capsys.readouterr().err
    assert "observent_capture.py" in err
    assert "syntax error" in err


def test_posttooluse_ignores_non_observent_files(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    # A broken file the user owns is out of scope — never block on it.
    f = tmp_path / "main.py"
    f.write_text("def broken(:\n")
    rc = _run(posttooluse_validate, {"tool_input": {"file_path": str(f)}}, monkeypatch)
    assert rc == 0
    assert capsys.readouterr().err == ""


def test_posttooluse_missing_or_absent_file_is_passthrough(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    assert _run(posttooluse_validate, {"tool_input": {}}, monkeypatch) == 0
    gone = tmp_path / "observent_otel.py"  # never created
    assert _run(posttooluse_validate, {"tool_input": {"file_path": str(gone)}}, monkeypatch) == 0


def test_posttooluse_malformed_stdin_is_passthrough(monkeypatch: pytest.MonkeyPatch) -> None:
    assert _run(posttooluse_validate, None, monkeypatch, raw="not json") == 0


# --- prompt_nudge ---------------------------------------------------------


def _isolate_marker_dir(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr("tempfile.gettempdir", lambda: str(tmp_path))


def test_prompt_nudge_fires_on_intent_once_per_session(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _isolate_marker_dir(monkeypatch, tmp_path)
    payload = {"prompt": "Can you add tracing and telemetry to my agent?", "session_id": "s1"}

    rc = _run(prompt_nudge, payload, monkeypatch)
    assert rc == 0
    first = capsys.readouterr().out
    assert "observent" in first
    out = json.loads(first)
    assert out["hookSpecificOutput"]["hookEventName"] == "UserPromptSubmit"

    # Second prompt in the same session must stay silent (nudge once).
    rc = _run(prompt_nudge, payload, monkeypatch)
    assert rc == 0
    assert capsys.readouterr().out == ""


def test_prompt_nudge_silent_without_intent(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _isolate_marker_dir(monkeypatch, tmp_path)
    rc = _run(prompt_nudge, {"prompt": "refactor this function", "session_id": "s2"}, monkeypatch)
    assert rc == 0
    assert capsys.readouterr().out == ""


def test_prompt_nudge_silent_when_already_observent(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _isolate_marker_dir(monkeypatch, tmp_path)
    rc = _run(
        prompt_nudge, {"prompt": "/observent langgraph phoenix", "session_id": "s3"}, monkeypatch
    )
    assert rc == 0
    assert capsys.readouterr().out == ""


def test_prompt_nudge_empty_prompt_is_passthrough(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _isolate_marker_dir(monkeypatch, tmp_path)
    assert _run(prompt_nudge, {"prompt": "", "session_id": "s4"}, monkeypatch) == 0
    assert capsys.readouterr().out == ""


# --- session_start_detect -------------------------------------------------


class _FakeProc:
    def __init__(self, returncode: int, stdout: str) -> None:
        self.returncode = returncode
        self.stdout = stdout


def test_session_start_emits_summary_when_detected(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    report = {
        "frameworks": [{"name": "langgraph"}],
        "backends": [{"name": "phoenix"}],
        "docker": {"compose_available": True},
    }
    monkeypatch.setattr(
        session_start_detect.subprocess,
        "run",
        lambda *a, **k: _FakeProc(0, json.dumps(report)),
    )
    rc = _run(session_start_detect, {"cwd": "."}, monkeypatch)
    assert rc == 0
    ctx = json.loads(capsys.readouterr().out)["hookSpecificOutput"]["additionalContext"]
    assert "langgraph" in ctx
    assert "phoenix" in ctx
    assert "Docker Compose is available" in ctx
    assert "/observent" in ctx


def test_session_start_silent_when_nothing_detected(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    empty = json.dumps({"frameworks": [], "backends": []})
    monkeypatch.setattr(
        session_start_detect.subprocess, "run", lambda *a, **k: _FakeProc(0, empty)
    )
    rc = _run(session_start_detect, {"cwd": "."}, monkeypatch)
    assert rc == 0
    assert capsys.readouterr().out == ""


def test_session_start_silent_on_detector_failure(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(
        session_start_detect.subprocess, "run", lambda *a, **k: _FakeProc(1, "")
    )
    rc = _run(session_start_detect, {"cwd": "."}, monkeypatch)
    assert rc == 0
    assert capsys.readouterr().out == ""


# --- plugin.json hook wiring (path-drift guard) ---------------------------

_REPO_ROOT = Path(__file__).resolve().parent.parent


def test_plugin_json_hook_commands_point_at_real_scripts() -> None:
    """Every script referenced by a plugin.json hook command must exist.

    The hook commands embed ``${CLAUDE_PLUGIN_ROOT}/...`` path strings; renaming
    or moving a script silently breaks the hook for every installed user with no
    other signal. This asserts each referenced path resolves on disk.
    """
    text = (_REPO_ROOT / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8")
    manifest = json.loads(text)
    commands = [
        hook["command"]
        for groups in manifest.get("hooks", {}).values()
        for group in groups
        for hook in group.get("hooks", [])
        if hook.get("type") == "command"
    ]
    assert commands, "plugin.json declares no hook commands"

    pattern = r"\$\{CLAUDE_PLUGIN_ROOT\}/([^\"']+)"
    referenced = [m.group(1) for cmd in commands for m in re.finditer(pattern, cmd)]
    assert referenced, "no ${CLAUDE_PLUGIN_ROOT}-relative script paths found in hook commands"
    for rel in referenced:
        assert (_REPO_ROOT / rel).is_file(), f"plugin.json hook references missing file: {rel}"
