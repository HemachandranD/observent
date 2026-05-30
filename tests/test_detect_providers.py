"""Tests for detect_providers.py — the installed-IDE/CLI detector that drives
the installer's per-provider copy logic.
"""
from __future__ import annotations

import detect_providers
from detect_providers import DETECTORS


def test_every_detector_returns_required_keys():
    for pid, fn in DETECTORS.items():
        info = fn()
        assert {"label", "installed", "config_dir", "install_cmd"} <= set(info), pid
        assert isinstance(info["installed"], bool)
        assert info["label"]
        assert info["install_cmd"]


def test_claude_code_detected_via_binary(monkeypatch):
    monkeypatch.setattr(detect_providers, "_has_binary", lambda cmd: cmd == "claude")
    monkeypatch.setattr(detect_providers, "_dir_exists", lambda p: False)
    assert detect_providers._claude_code()["installed"] is True


def test_provider_not_detected_when_absent(monkeypatch):
    monkeypatch.setattr(detect_providers, "_has_binary", lambda cmd: False)
    monkeypatch.setattr(detect_providers, "_dir_exists", lambda p: False)
    monkeypatch.setattr(detect_providers, "_glob_any", lambda d, p: False)
    assert detect_providers._cursor()["installed"] is False
    assert detect_providers._cline()["installed"] is False


def test_known_provider_ids_present():
    # The installer keys off these ids; guard against accidental renames.
    assert {"claude_code", "antigravity", "copilot", "codex", "cursor"} <= set(DETECTORS)
