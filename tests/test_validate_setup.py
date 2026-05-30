"""Behavioural tests for validate_setup.py beyond ``--help``.

Covers backend-argument parsing (the multi-backend fan-out front door) and the
per-backend env/package checks that drive the PASS/FAIL exit code — none of
which CI exercised before.
"""
from __future__ import annotations

import argparse

import pytest
import validate_setup
from validate_setup import Result, _parse_backends, check_langfuse, check_langsmith


def test_parse_single_backend():
    assert _parse_backends("phoenix") == ["phoenix"]


def test_parse_multi_backend_preserves_order():
    assert _parse_backends("langsmith,phoenix") == ["langsmith", "phoenix"]


def test_parse_dedupes():
    assert _parse_backends("phoenix,phoenix,signoz") == ["phoenix", "signoz"]


def test_parse_all_expands_to_every_check():
    assert _parse_backends("all") == list(validate_setup.CHECKS.keys())


def test_parse_rejects_unknown_backend():
    with pytest.raises(argparse.ArgumentTypeError):
        _parse_backends("phoenix,redis")


def test_parse_rejects_empty():
    with pytest.raises(argparse.ArgumentTypeError):
        _parse_backends(" , ")


def test_parse_strips_whitespace():
    assert _parse_backends(" phoenix , signoz ") == ["phoenix", "signoz"]


def test_result_fail_flips_passed():
    r = Result("x")
    assert r.passed is True
    r.fail("boom")
    assert r.passed is False


def test_result_ok_warn_info_keep_passed_true():
    r = Result("x")
    r.ok("a")
    r.warn("b")
    r.info("c")
    assert r.passed is True
    assert len(r.messages) == 3


def test_langfuse_missing_env_fails(monkeypatch):
    # No LANGFUSE_* env vars set -> the check must fail (without network).
    for var in ("LANGFUSE_PUBLIC_KEY", "LANGFUSE_SECRET_KEY", "LANGFUSE_HOST"):
        monkeypatch.delenv(var, raising=False)
    r = check_langfuse(smoke=False)
    assert r.passed is False


def test_langsmith_missing_key_fails(monkeypatch):
    monkeypatch.delenv("LANGSMITH_API_KEY", raising=False)
    monkeypatch.setenv("LANGSMITH_ENDPOINT", "http://127.0.0.1:9")  # closed port
    r = check_langsmith(smoke=False)
    assert r.passed is False
