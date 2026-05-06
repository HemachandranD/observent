#!/usr/bin/env python3
"""Validate bigboss observability backend configuration.

Usage:
  python validate_setup.py phoenix [--smoke-test]
  python validate_setup.py langfuse [--smoke-test]
  python validate_setup.py signoz [--smoke-test]
  python validate_setup.py all

Per backend:
  - Verifies required env vars
  - Verifies required Python packages installed
  - Probes the configured endpoint for reachability
  - With --smoke-test: emits one synthetic LLM span and reports back

Exit code: 0 on pass, 1 on any failure.
"""
from __future__ import annotations

import argparse
import importlib.util
import os
import socket
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Callable
from urllib.parse import urlparse


@dataclass
class Result:
    backend: str
    passed: bool = True
    messages: list[str] = field(default_factory=list)

    def ok(self, msg: str) -> None:
        self.messages.append(f"  [OK]   {msg}")

    def warn(self, msg: str) -> None:
        self.messages.append(f"  [WARN] {msg}")

    def fail(self, msg: str) -> None:
        self.messages.append(f"  [FAIL] {msg}")
        self.passed = False

    def info(self, msg: str) -> None:
        self.messages.append(f"  [INFO] {msg}")


def _is_installed(module: str) -> bool:
    try:
        return importlib.util.find_spec(module) is not None
    except (ImportError, ValueError):
        return False


def _check_env(result: Result, var: str, required: bool = True) -> str | None:
    val = os.environ.get(var)
    if val:
        masked = (val[:6] + "..." + val[-4:]) if len(val) > 12 else "***"
        result.ok(f"{var} = {masked}")
        return val
    if required:
        result.fail(f"{var} is not set")
    else:
        result.info(f"{var} not set (optional)")
    return None


def _probe_tcp(result: Result, host: str, port: int, timeout: float = 3.0) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            result.ok(f"TCP {host}:{port} reachable")
            return True
    except OSError as e:
        result.fail(f"TCP {host}:{port} unreachable: {e}")
        return False


def _probe_http(result: Result, url: str, method: str = "GET", timeout: float = 5.0) -> bool:
    try:
        req = urllib.request.Request(url, method=method)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            result.ok(f"HTTP {method} {url} -> {resp.status}")
            return True
    except urllib.error.HTTPError as e:
        # Some endpoints return 4xx for unauth-but-reachable; treat as reachable.
        if 400 <= e.code < 500:
            result.ok(f"HTTP {method} {url} -> {e.code} (reachable)")
            return True
        result.fail(f"HTTP {method} {url} -> {e.code}")
        return False
    except (urllib.error.URLError, OSError) as e:
        result.fail(f"HTTP {method} {url} unreachable: {e}")
        return False


def check_phoenix(smoke: bool) -> Result:
    r = Result("phoenix")
    if not _is_installed("phoenix"):
        r.fail("arize-phoenix not installed (pip install 'arize-phoenix>=5.0')")
    else:
        r.ok("arize-phoenix installed")

    api_key = os.environ.get("PHOENIX_API_KEY")
    endpoint = os.environ.get("PHOENIX_COLLECTOR_ENDPOINT")

    if api_key:
        r.info("PHOENIX_API_KEY set -> cloud mode")
        endpoint = endpoint or "https://app.phoenix.arize.com"
        _probe_http(r, endpoint, method="GET")
    else:
        r.info("PHOENIX_API_KEY not set -> local mode (px.launch_app() or phoenix-server)")
        endpoint = endpoint or "http://localhost:6006"
        parsed = urlparse(endpoint)
        host = parsed.hostname or "localhost"
        port = parsed.port or 6006
        _probe_tcp(r, host, port)

    if smoke and r.passed:
        _emit_smoke_span(r, endpoint=f"{endpoint.rstrip('/')}/v1/traces", headers=_phoenix_headers(api_key))
    return r


def check_langfuse(smoke: bool) -> Result:
    r = Result("langfuse")
    if not _is_installed("langfuse"):
        r.fail("langfuse not installed (pip install 'langfuse>=3.0')")
    pk = _check_env(r, "LANGFUSE_PUBLIC_KEY")
    sk = _check_env(r, "LANGFUSE_SECRET_KEY")
    host = os.environ.get("LANGFUSE_HOST", "https://cloud.langfuse.com")
    r.info(f"LANGFUSE_HOST = {host}")

    if pk and sk and _is_installed("langfuse"):
        try:
            from langfuse import Langfuse  # type: ignore[import-not-found]

            client = Langfuse(public_key=pk, secret_key=sk, host=host)
            if hasattr(client, "auth_check"):
                ok = client.auth_check()
                if ok:
                    r.ok("Langfuse auth_check() passed")
                else:
                    r.fail("Langfuse auth_check() returned False")
            else:
                _probe_http(r, f"{host.rstrip('/')}/api/public/health", method="GET")
        except Exception as e:  # noqa: BLE001
            r.fail(f"Langfuse client init failed: {e}")

    if smoke and r.passed:
        import base64

        auth = base64.b64encode(f"{pk}:{sk}".encode()).decode()
        _emit_smoke_span(
            r,
            endpoint=f"{host.rstrip('/')}/api/public/otel/v1/traces",
            headers={"Authorization": f"Basic {auth}"},
        )
    return r


def check_signoz(smoke: bool) -> Result:
    r = Result("signoz")
    if not _is_installed("opentelemetry.exporter.otlp.proto.http"):
        r.fail(
            "opentelemetry-exporter-otlp-proto-http not installed "
            "(pip install 'opentelemetry-exporter-otlp-proto-http>=1.25')"
        )
    endpoint = os.environ.get("SIGNOZ_ENDPOINT", "http://localhost:4318/v1/traces")
    r.info(f"SIGNOZ_ENDPOINT = {endpoint}")

    parsed = urlparse(endpoint)
    is_cloud = parsed.hostname and parsed.hostname.endswith("signoz.cloud")
    if is_cloud:
        _check_env(r, "SIGNOZ_INGESTION_KEY")
    else:
        r.info("Self-hosted SigNoz (no ingestion key required)")

    # Probe the OTLP endpoint root
    root = f"{parsed.scheme}://{parsed.netloc}"
    _probe_http(r, root, method="GET")

    if smoke and r.passed:
        headers = {}
        key = os.environ.get("SIGNOZ_INGESTION_KEY")
        if key:
            headers["signoz-access-token"] = key
        _emit_smoke_span(r, endpoint=endpoint, headers=headers)
    return r


def _phoenix_headers(api_key: str | None) -> dict[str, str]:
    if api_key:
        return {"Authorization": f"Bearer {api_key}"}
    return {}


def _emit_smoke_span(r: Result, *, endpoint: str, headers: dict[str, str]) -> None:
    """Emit one synthetic LLM span via OTLP HTTP and report ingestion."""
    if not _is_installed("opentelemetry.exporter.otlp.proto.http"):
        r.warn("Skipping smoke test: opentelemetry-exporter-otlp-proto-http not installed")
        return
    try:
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import (
            OTLPSpanExporter,
        )
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import (
            BatchSpanProcessor,
        )
    except ImportError as e:
        r.warn(f"Skipping smoke test: {e}")
        return

    provider = TracerProvider(resource=Resource.create({"service.name": "bigboss-smoke-test"}))
    exporter = OTLPSpanExporter(endpoint=endpoint, headers=headers)
    provider.add_span_processor(BatchSpanProcessor(exporter))
    tracer = provider.get_tracer("bigboss.smoke_test")

    with tracer.start_as_current_span("smoke-test-llm-call") as span:
        span.set_attribute("openinference.span.kind", "LLM")
        span.set_attribute("llm.model_name", "claude-sonnet-4-6")
        span.set_attribute("llm.provider", "anthropic")
        span.set_attribute("gen_ai.system", "anthropic")
        span.set_attribute("gen_ai.request.model", "claude-sonnet-4-6")
        span.set_attribute("input.value", '{"prompt": "smoke test"}')
        span.set_attribute("input.mime_type", "application/json")
        span.set_attribute("output.value", '{"completion": "ok"}')
        span.set_attribute("output.mime_type", "application/json")
        span.set_attribute("llm.token_count.prompt", 4)
        span.set_attribute("llm.token_count.completion", 2)
        span.set_attribute("llm.token_count.total", 6)
        span.set_attribute("gen_ai.usage.input_tokens", 4)
        span.set_attribute("gen_ai.usage.output_tokens", 2)

    provider.shutdown()
    r.ok(f"Synthetic LLM span exported to {endpoint}")
    r.info("Verify the span appears in your backend UI within ~10s.")


CHECKS: dict[str, Callable[[bool], Result]] = {
    "phoenix": check_phoenix,
    "langfuse": check_langfuse,
    "signoz": check_signoz,
}


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate bigboss observability setup.")
    parser.add_argument("backend", choices=[*CHECKS.keys(), "all"])
    parser.add_argument("--smoke-test", action="store_true", help="Emit a synthetic LLM span")
    args = parser.parse_args()

    backends = list(CHECKS.keys()) if args.backend == "all" else [args.backend]
    overall_pass = True
    for backend in backends:
        print(f"\n=== {backend} ===")
        result = CHECKS[backend](args.smoke_test)
        for msg in result.messages:
            print(msg)
        if not result.passed:
            overall_pass = False

    print("\n=== Summary ===")
    print(f"  {'PASS' if overall_pass else 'FAIL'}")
    return 0 if overall_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
