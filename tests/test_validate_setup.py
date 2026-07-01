"""Behavioural tests for validate_setup.py beyond ``--help``.

Covers backend-argument parsing (the multi-backend fan-out front door) and the
per-backend env/package checks that drive the PASS/FAIL exit code — none of
which CI exercised before.
"""
from __future__ import annotations

import argparse

import pytest
import validate_setup
from validate_setup import (
    Result,
    _parse_backends,
    check_jaeger,
    check_langfuse,
    check_langsmith,
    check_opik,
    check_phoenix,
)


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


def test_opik_cloud_missing_key_fails(monkeypatch):
    # Cloud base (comet.com) requires OPIK_API_KEY + OPIK_WORKSPACE -> must fail.
    monkeypatch.setenv("OPIK_URL_OVERRIDE", "https://www.comet.com/opik/api")
    for var in ("OPIK_API_KEY", "OPIK_WORKSPACE"):
        monkeypatch.delenv(var, raising=False)
    r = check_opik(smoke=False)
    assert r.passed is False


def test_jaeger_unreachable_endpoint_fails(monkeypatch):
    # Jaeger needs no auth, but an unreachable OTLP endpoint must fail the probe.
    monkeypatch.setenv("JAEGER_ENDPOINT", "http://127.0.0.1:9/v1/traces")  # closed port
    r = check_jaeger(smoke=False)
    assert r.passed is False


def test_phoenix_single_backend_requires_arize_package(monkeypatch):
    # Single-backend Phoenix uses phoenix.otel.register() -> arize-phoenix is required.
    monkeypatch.setattr(validate_setup, "_is_installed", lambda module: False)
    monkeypatch.setattr(validate_setup, "_probe_tcp", lambda *a, **k: True)
    monkeypatch.delenv("PHOENIX_API_KEY", raising=False)
    r = check_phoenix(smoke=False)
    assert r.passed is False
    assert any("arize-phoenix not installed" in m for m in r.messages)


def test_phoenix_fanout_does_not_require_arize_package(monkeypatch):
    # Multi-backend fan-out builds a manual TracerProvider + OTLPSpanExporter and
    # never imports arize-phoenix -> its absence must not fail the check.
    def fake_installed(module):
        return module == "opentelemetry.exporter.otlp.proto.http"

    monkeypatch.setattr(validate_setup, "_is_installed", fake_installed)
    monkeypatch.setattr(validate_setup, "_probe_tcp", lambda *a, **k: True)
    monkeypatch.delenv("PHOENIX_API_KEY", raising=False)
    r = check_phoenix(smoke=False, fanout=True)
    assert r.passed is True
    assert not any("arize-phoenix not installed (pip install" in m for m in r.messages)


def test_phoenix_fanout_still_requires_otlp_exporter(monkeypatch):
    # In fan-out the OTLP HTTP exporter *is* what the pattern uses; its absence fails.
    monkeypatch.setattr(validate_setup, "_is_installed", lambda module: False)
    monkeypatch.setattr(validate_setup, "_probe_tcp", lambda *a, **k: True)
    monkeypatch.delenv("PHOENIX_API_KEY", raising=False)
    r = check_phoenix(smoke=False, fanout=True)
    assert r.passed is False
    assert any("opentelemetry-exporter-otlp-proto-http not installed" in m for m in r.messages)


def _fake_urlopen_failing_then_ok(fail_times: int):
    """Return a urlopen stand-in that raises URLError `fail_times`, then succeeds."""
    calls = {"n": 0}

    class _Resp:
        status = 200

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

    def _urlopen(req, timeout=None):
        calls["n"] += 1
        if calls["n"] <= fail_times:
            raise validate_setup.urllib.error.URLError("connection refused")
        return _Resp()

    return _urlopen, calls


def test_probe_http_retry_succeeds_after_transient_failures(monkeypatch):
    # Mirrors SigNoz's opamp settle: endpoint refuses a few times, then serves.
    monkeypatch.setattr(validate_setup.time, "sleep", lambda *_: None)  # no real waiting
    fake, calls = _fake_urlopen_failing_then_ok(fail_times=3)
    monkeypatch.setattr(validate_setup.urllib.request, "urlopen", fake)
    r = Result("signoz")
    assert validate_setup._probe_http_retry(r, "http://localhost:4318", attempts=7) is True
    assert calls["n"] == 4  # 3 failures + 1 success
    assert r.passed is True


def test_probe_http_retry_fails_after_exhausting_attempts(monkeypatch):
    monkeypatch.setattr(validate_setup.time, "sleep", lambda *_: None)
    fake, _ = _fake_urlopen_failing_then_ok(fail_times=99)  # never recovers
    monkeypatch.setattr(validate_setup.urllib.request, "urlopen", fake)
    r = Result("signoz")
    assert validate_setup._probe_http_retry(r, "http://localhost:4318", attempts=4) is False
    assert r.passed is False
    assert any("unreachable after 4 attempts" in m for m in r.messages)
