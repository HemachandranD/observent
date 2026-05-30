"""Behavioural tests for the canonical capture engine in references/capture.md.

The engine is generated code (it ships as a fenced block in the reference, not
as an importable module in this repo), so these tests extract that block, write
it to a temp module, and exercise it. The OpenTelemetry deps it imports are not
part of CI's minimal tool set, so the whole module skips when they're absent —
but it runs locally and anywhere otel is installed, pinning the redesign:

  - enrich-in-place on the current recording span (no duplicate root span);
  - fallback `agent.run` span only when nothing is recording (never-miss-input);
  - OK status on success, ERROR + single exception event + error.type on failure;
  - secret redaction and baggage promotion to child spans.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

pytest.importorskip("opentelemetry")

from opentelemetry import trace  # noqa: E402
from opentelemetry.sdk.trace import TracerProvider  # noqa: E402
from opentelemetry.sdk.trace.export import SimpleSpanProcessor  # noqa: E402
from opentelemetry.sdk.trace.export.in_memory_span_exporter import (  # noqa: E402
    InMemorySpanExporter,
)

ROOT = Path(__file__).resolve().parent.parent
CAPTURE_MD = ROOT / "skills" / "observent" / "references" / "capture.md"


def _extract(marker: str) -> str:
    blocks = re.findall(r"```python\n(.*?)```", CAPTURE_MD.read_text(), re.DOTALL)
    return next(b for b in blocks if b.lstrip().startswith(marker))


@pytest.fixture(scope="module")
def cap(tmp_path_factory):
    """Materialize observent_capture.py from the reference and import it."""
    import importlib.util
    import sys

    code = _extract("# observent_capture.py")
    mod_dir = tmp_path_factory.mktemp("gen")
    mod_path = mod_dir / "observent_capture.py"
    mod_path.write_text(code)
    sys.path.insert(0, str(mod_dir))
    spec = importlib.util.spec_from_file_location("observent_capture", mod_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules["observent_capture"] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def _exporter():
    # set_tracer_provider() only takes effect once per process, so the provider
    # + exporter are module-scoped; each test clears the exporter via `exporter`.
    exp = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exp))
    try:
        from opentelemetry.processor.baggage import (
            ALLOW_ALL_BAGGAGE_KEYS,
            BaggageSpanProcessor,
        )

        provider.add_span_processor(BaggageSpanProcessor(ALLOW_ALL_BAGGAGE_KEYS))
    except ImportError:
        pass
    trace.set_tracer_provider(provider)
    return exp


@pytest.fixture
def exporter(_exporter):
    _exporter.clear()
    return _exporter


def _named(spans, name):
    return next((s for s in spans if s.name == name), None)


def test_enrich_in_place_no_duplicate_span(cap, exporter):
    tracer = trace.get_tracer("t")
    with tracer.start_as_current_span("framework.root"):
        cap.capture_run(lambda payload: {"reply": "ok"})({"message": "hi"})
    spans = exporter.get_finished_spans()
    names = [s.name for s in spans]
    assert "agent.run" not in names, "must not open a duplicate root span"
    root = _named(spans, "framework.root")
    attrs = dict(root.attributes)
    assert attrs.get("input.message") == "hi"
    assert attrs.get("output.reply") == "ok"
    assert root.status.status_code.name == "OK"


def test_fallback_span_when_nothing_recording(cap, exporter):
    cap.capture_run(lambda payload: {"reply": "ok"})({"message": "cli"})
    root = _named(exporter.get_finished_spans(), "agent.run")
    assert root is not None, "fallback agent.run must capture input when nothing is recording"
    attrs = dict(root.attributes)
    assert attrs.get("input.message") == "cli"
    assert attrs.get("output.reply") == "ok"
    assert root.status.status_code.name == "OK"


def test_error_path_sets_status_once(cap, exporter):
    def boom(payload):
        raise ValueError("kaboom")

    with pytest.raises(ValueError):
        cap.capture_run(boom)({"x": 1})
    root = _named(exporter.get_finished_spans(), "agent.run")
    assert root.status.status_code.name == "ERROR"
    assert dict(root.attributes).get("error.type") == "ValueError"
    # exactly one exception event (no double-record from the fallback CM)
    assert [e.name for e in root.events].count("exception") == 1


def test_secret_redaction(cap, exporter):
    tracer = trace.get_tracer("t")
    with tracer.start_as_current_span("framework.root"):
        cap.enrich_current_span({"password": "p@ss", "user_id": "42"})
    attrs = dict(_named(exporter.get_finished_spans(), "framework.root").attributes)
    assert attrs.get("input.password") == "***REDACTED***"
    assert attrs.get("input.user_id") == "42"


def test_baggage_promoted_to_child(cap, exporter):
    pytest.importorskip("opentelemetry.processor.baggage")
    tracer = trace.get_tracer("t")

    @cap.capture_run
    def run(payload):
        with tracer.start_as_current_span("llm.chat"):
            pass
        return {"ok": True}

    with tracer.start_as_current_span("framework.root"):
        run({"user_id": "42"})
    child = _named(exporter.get_finished_spans(), "llm.chat")
    assert dict(child.attributes).get("user_id") == "42"
