# AI-Boundary Input/Output Capture

observent's prime directive is **never miss any input or output that crosses the AI-system boundary** — the prompt, the request state, the run config, and the result — regardless of *how* the agent was triggered (HTTP request, CLI invocation, queue/worker job, cron, notebook). This capture is **transport-agnostic**: it attaches to the agent run itself, not to any web framework.

The mechanism is a single generated module, `observent_capture.py`, plus a thin optional HTTP adapter. The same engine powers every entry point, so adding observability to a FastAPI route, a Celery task, and a `python main.py` script all produce the same `input.*` / `output.*` / status attributes on the run's root span.

This page is the canonical reference for that engine. SKILL.md § Step 2.3 links here.

---

## Maintainer's sources

**Specs:**
- OTel trace API — current span & status — https://opentelemetry.io/docs/languages/python/instrumentation/#set-span-status
- OTel `record_exception()` / exception semconv — https://opentelemetry.io/docs/specs/semconv/exceptions/
- OTel baggage API — https://opentelemetry.io/docs/specs/otel/baggage/api/
- W3C Baggage — https://www.w3.org/TR/baggage/

**Instrumentors & processors:**
- `opentelemetry-processor-baggage` (`BaggageSpanProcessor`) — https://github.com/open-telemetry/opentelemetry-python-contrib/tree/main/processor/opentelemetry-processor-baggage
- `opentelemetry-instrumentation-asgi` (`exclude_spans` knob, header capture) — https://opentelemetry-python-contrib.readthedocs.io/en/latest/instrumentation/asgi/asgi.html

**OTel SDK knobs cited under § Truncation:**
- `OTEL_SPAN_ATTRIBUTE_COUNT_LIMIT` / `OTEL_ATTRIBUTE_VALUE_LENGTH_LIMIT` — https://opentelemetry.io/docs/specs/otel/configuration/sdk-environment-variables/

Last reviewed: 2026-05-30.

---

## Core principle — enrich in place, never duplicate the root span

observent does **not** open its own root span for the agent run. The framework instrumentor (LangChain / CrewAI / LlamaIndex / …) — or the transport instrumentor (e.g. `opentelemetry-instrumentation-fastapi`) — has already opened a root span by the time the agent is invoked. observent **enriches that existing span**:

```python
span = trace.get_current_span()
if span.is_recording():
    # Normal path: stamp input/output/status onto the span that's already current.
    enrich_current_span(inputs)
else:
    # Fallback ONLY when nothing is recording (e.g. a bare CLI before any
    # instrumentor opened a span). Prime directive = never miss input, so open a
    # minimal root rather than silently drop it.
    with tracer.start_as_current_span("agent.run") as span:
        ...
```

This is why there is **no second `agent.run` span** behind HTTP or inside a framework run — the attributes land on the existing root. The fallback span appears only in the rare "nothing open" case, and is documented so it is never a surprise.

### Attribute namespacing

Because the attributes ride a span observent did not name, every captured key is namespaced so it can never collide with the host span's own attributes:

| Namespace | Sourced from | Convention mapping |
|---|---|---|
| `input.value` / `input.<path>` | The run's input (prompt, state dict, request body) | OI native key is `input.value`; flattened leaves use `input.<path>` |
| `output.value` / `output.<path>` | The run's result | OI native key is `output.value`; flattened leaves use `output.<path>` |
| `gen_ai.prompt` / `gen_ai.completion` | Same data, OTel-GenAI convention | Emitted when `_CONVENTION` ∈ {`otel-genai`, `both`} |

The flattening rules (dot-notation, lists-of-primitives kept native, lists-of-objects indexed, `None` dropped) are identical to the HTTP adapter below — they share `_flatten`.

---

## Span status (set at the AI boundary)

The engine sets span status on the run's root span itself, so status no longer depends on whether a transport instrumentor happens to be present:

- **Success** → `span.set_status(Status(StatusCode.OK))`.
- **Exception** → `span.record_exception(exc)`, `span.set_status(Status(StatusCode.ERROR, str(exc)))`, and `error.type` = the exception's qualified name, then re-raise. This pairs the OTel `record_exception()` API (see `otel_genai.md § Errors`) with an explicit ERROR status — the exception event *and* the status both land on the span.

---

## Redaction & baggage promotion

Both are **generation-time literals** in the generated file (no env-var override — same rule as `_CONVENTION`). The redaction list (auth credentials, session/CSRF, PII) and the baggage whitelist are unchanged from observent's prior design; sensitive values become `***REDACTED***` (key preserved so the attribute shape is stable), and a configurable whitelist of leaf keys is promoted into OTel baggage so a `BaggageSpanProcessor` stamps them onto every child span (LLM / tool / agent). See § Baggage promotion below.

---

## Canonical engine

Generated as `observent_capture.py` in the user's project root. **Zero web-framework imports** — depends only on `opentelemetry-api`.

```python
# observent_capture.py
"""Transport-agnostic capture of the input/output that crosses the AI-system
boundary, plus run status, as attributes on the agent run's existing root span.

Works identically whether the agent is triggered by HTTP, a CLI, a queue worker,
or a script: enrich_current_span() stamps onto whatever span is current, and
capture_run() wraps any callable. No web framework required.

Generated by observent. Edit _REDACT_KEYS / _PROMOTE_TO_BAGGAGE / _CONVENTION to
customize; no env-var override is read at runtime by design.
"""
from __future__ import annotations

import functools
from typing import Any, Awaitable, Callable, Iterator, TypeVar

from opentelemetry import baggage, context, trace
from opentelemetry.trace import Status, StatusCode
from opentelemetry.util.types import AttributeValue

_CONVENTION = "oi"  # one of: "oi" | "otel-genai" | "both" — generation-time literal

_REDACT_KEYS: frozenset[str] = frozenset({
    "api_key", "apikey", "api-key",
    "authorization", "bearer",
    "token", "access_token", "refresh_token", "id_token",
    "secret", "client_secret",
    "password", "passwd", "pwd",
    "x-api-key", "x_api_key",
    "openai_api_key", "anthropic_api_key", "azure_openai_key",
    "aws_access_key", "aws_access_key_id",
    "aws_secret", "aws_secret_access_key",
    "cookie", "set-cookie",
    "session", "session_id", "sessionid",
    "csrf", "csrf_token", "x-csrf-token", "xsrf-token",
    "email", "e_mail", "email_address",
    "phone", "phone_number", "mobile",
    "ssn", "social_security_number",
    "credit_card", "card_number", "cvv", "cvc",
    "dob", "date_of_birth", "birth_date",
})
_REDACTED = "***REDACTED***"

# Leaf names promoted from the flattened input into OTel baggage, so a
# BaggageSpanProcessor can stamp them onto every child span.
_PROMOTE_TO_BAGGAGE: frozenset[str] = frozenset({
    "tenant_id",
    "user_id",
    "session_id",
    "request_id",
})

# OTel attribute values must be one of these primitives, or a list of them.
_PRIMITIVES = (str, bool, int, float)

_tracer = trace.get_tracer("observent.capture")

F = TypeVar("F", bound=Callable[..., Any])
AF = TypeVar("AF", bound=Callable[..., Awaitable[Any]])


def _is_sensitive(key: str) -> bool:
    k = key.lower()
    return any(needle in k for needle in _REDACT_KEYS)


def _coerce(value: Any) -> AttributeValue:
    if isinstance(value, _PRIMITIVES):
        return value
    if isinstance(value, (list, tuple)) and all(isinstance(v, _PRIMITIVES) for v in value):
        return list(value)
    return str(value)


def _flatten(prefix: str, value: Any) -> Iterator[tuple[str, AttributeValue]]:
    """Yield (attribute_key, attribute_value) pairs from an arbitrary payload.

    - Dicts recurse with `{prefix}.{key}`. A sensitive key short-circuits to ***REDACTED***.
    - Lists of primitives are kept as a single OTel list attribute.
    - Lists of objects flatten with an integer index segment.
    - None is dropped (OTel disallows None attribute values).
    """
    if value is None:
        return
    if isinstance(value, dict):
        for k, v in value.items():
            child_key = f"{prefix}.{k}" if prefix else str(k)
            if _is_sensitive(str(k)):
                yield child_key, _REDACTED
            else:
                yield from _flatten(child_key, v)
        return
    if isinstance(value, (list, tuple)):
        if all(isinstance(v, _PRIMITIVES) or v is None for v in value):
            cleaned = [v for v in value if v is not None]
            if cleaned:
                yield prefix, _coerce(cleaned)
            return
        for i, v in enumerate(value):
            yield from _flatten(f"{prefix}.{i}", v)
        return
    yield prefix, _coerce(value)


def _promote_baggage(attr_key: str, value: AttributeValue, ctx: context.Context) -> context.Context:
    if value == _REDACTED:
        return ctx
    leaf = attr_key.rsplit(".", 1)[-1]
    if leaf not in _PROMOTE_TO_BAGGAGE:
        return ctx
    return baggage.set_baggage(leaf, str(value), context=ctx)


def _write(span: trace.Span, namespace: str, payload: Any) -> None:
    """Flatten `payload` under `namespace` and set each leaf as a span attribute.

    Also sets the OI-native `input.value` / `output.value` and, when the
    convention calls for it, the OTel-GenAI `gen_ai.*` mirror.
    """
    if not span.is_recording():
        return
    ctx = context.get_current()
    for key, val in _flatten(namespace, payload):
        span.set_attribute(key, val)
        ctx = _promote_baggage(key, val, ctx)
    if ctx is not context.get_current():
        context.attach(ctx)  # promote into the active context for child spans

    # Convention-native single-value mirrors (so each backend's UI lights up).
    flat_str = str(payload)
    if _CONVENTION in ("oi", "both"):
        span.set_attribute(f"{namespace}.value", flat_str)
    if _CONVENTION in ("otel-genai", "both"):
        gen_ai_key = "gen_ai.prompt" if namespace == "input" else "gen_ai.completion"
        span.set_attribute(gen_ai_key, flat_str)


def enrich_current_span(inputs: Any) -> trace.Span:
    """Stamp `input.*` attributes (with redaction + baggage promotion) onto the
    span that is currently recording. Returns that span. Safe to call when no
    span is recording (it becomes a no-op and returns the non-recording span)."""
    span = trace.get_current_span()
    _write(span, "input", inputs)
    return span


def capture_output(result: Any, span: trace.Span | None = None) -> Any:
    """Stamp `output.*` attributes onto `span` (or the current span). Returns the
    result unchanged so it can wrap a return value inline."""
    _write(span or trace.get_current_span(), "output", result)
    return result


def set_ok(span: trace.Span | None = None) -> None:
    span = span or trace.get_current_span()
    if span.is_recording():
        span.set_status(Status(StatusCode.OK))


def set_error(exc: BaseException, span: trace.Span | None = None) -> None:
    span = span or trace.get_current_span()
    if span.is_recording():
        span.record_exception(exc)
        span.set_attribute("error.type", type(exc).__qualname__)
        span.set_status(Status(StatusCode.ERROR, str(exc)))


def _enrich_or_open(inputs: Any):
    """Context manager: enrich the current recording span, or open a fallback
    `agent.run` root span when nothing is recording (never-miss-input)."""
    current = trace.get_current_span()
    if current.is_recording():
        from contextlib import nullcontext
        enrich_current_span(inputs)
        return nullcontext(current)
    # set_error() already records the exception and sets ERROR status, so disable
    # the context manager's own exception handling to avoid a duplicate event.
    cm = _tracer.start_as_current_span(
        "agent.run", record_exception=False, set_status_on_exception=False
    )
    span = cm.__enter__()
    enrich_current_span(inputs)
    return _Closing(cm, span)


class _Closing:
    """Adapts start_as_current_span's CM so capture_run can treat both paths alike."""
    def __init__(self, cm: Any, span: trace.Span) -> None:
        self._cm, self.span = cm, span

    def __enter__(self) -> trace.Span:
        return self.span

    def __exit__(self, *exc: Any) -> Any:
        return self._cm.__exit__(*exc)


def capture_run(fn: F) -> F:
    """Decorator: capture the wrapped callable's first argument as `input.*`, its
    return value as `output.*`, and set OK/ERROR status — on the existing root
    span when one is recording, else on a fallback `agent.run` span.

    Works for sync callables. Use `capture_run_async` for coroutines.
    """
    @functools.wraps(fn)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        inputs = args[0] if args else kwargs
        holder = _enrich_or_open(inputs)
        with holder as span:
            try:
                result = fn(*args, **kwargs)
            except BaseException as exc:
                set_error(exc, span)
                raise
            capture_output(result, span)
            set_ok(span)
            return result
    return wrapper  # type: ignore[return-value]


def capture_run_async(fn: AF) -> AF:
    """Async counterpart of capture_run for coroutine entry points."""
    @functools.wraps(fn)
    async def wrapper(*args: Any, **kwargs: Any) -> Any:
        inputs = args[0] if args else kwargs
        holder = _enrich_or_open(inputs)
        with holder as span:
            try:
                result = await fn(*args, **kwargs)
            except BaseException as exc:
                set_error(exc, span)
                raise
            capture_output(result, span)
            set_ok(span)
            return result
    return wrapper  # type: ignore[return-value]
```

---

## Per-framework wrap points

`capture_run` / `capture_run_async` (or a bare `enrich_current_span(...)` + `capture_output(...)` pair) goes at the **agent invocation**, so it enriches the framework's own root span:

| Framework | Where to wrap |
|---|---|
| **LangGraph** | the function that calls `graph.invoke(state)` / `graph.ainvoke(state)` / iterates `graph.stream(state)` |
| **CrewAI** | the function that calls `crew.kickoff(inputs=...)` |
| **LlamaIndex** | the function that calls `query_engine.query(...)` / `chat_engine.chat(...)` |
| **smolagents** | the function that calls `agent.run(task)` |
| **Anthropic / OpenAI Agents SDK** | the request handler / `Runner.run(...)` call site |
| **Microsoft Agent Framework** | the function that invokes the workflow/agent |
| **Custom** | wherever the manual root span is opened — call `enrich_current_span` right after |

Because capture enriches the *current* span, the framework's instrumentor must run first (it opens the root). If the agent is invoked with **no** instrumentor active (bare script), the fallback `agent.run` span guarantees input is still captured.

---

## Baggage promotion (cross-span correlation)

Span attributes live on one span; child spans (LLM / tool / agent steps) do **not** inherit them. To filter child spans by a request field (`tenant_id`, `user_id`, …), the engine promotes a configurable whitelist of leaf keys from the input into **OTel baggage**, and a `BaggageSpanProcessor` stamps them onto every span as it starts.

```python
from opentelemetry.processor.baggage import BaggageSpanProcessor, ALLOW_ALL_BAGGAGE_KEYS

provider.add_span_processor(BaggageSpanProcessor(ALLOW_ALL_BAGGAGE_KEYS))
```

Install: `pip install opentelemetry-processor-baggage`. Place it on the same `TracerProvider` that carries the OTLP exporters; Elastic APM picks up the same spans via its OTel bridge. Matching is exact, case-sensitive on the leaf segment; redacted values are never promoted. Keep the whitelist small for per-span cardinality / ingest cost — full-payload duplication onto every child span is intentionally avoided (N spans × full payload, brittle under sampling).

---

## Optional HTTP body adapter

`capture_run` already captures the agent's logical input/output for **any** transport. The HTTP adapter is needed **only when you additionally want the raw HTTP request/response bodies and headers** (e.g. a header or envelope field the agent never receives as an argument). Generate it **only if** `spec.choice.http_body_capture: true`.

It is a thin Starlette/ASGI middleware that **enriches the existing server span** with `http.request.*` / `http.response.*` attributes via the same `_flatten` engine. Key differences from the engine:

- **No new span** — it writes onto the server span the FastAPI instrumentor already opened.
- **No response re-buffering** — it reads the request body (re-injecting it so the route still sees it) and, for the response, captures headers/status without collapsing a `StreamingResponse`. Streaming endpoints keep streaming.
- Transport spans (`http receive` / `http send`) from the ASGI instrumentor are **left intact** — they are honest transport spans, not observent's to suppress. A user who wants them gone can pass `exclude_spans=["receive", "send"]` to the FastAPI instrumentor.

```python
# observent_http.py
"""Optional: enrich the existing HTTP server span with raw request/response
headers + bodies. Use ONLY when the agent's logical input (captured by
observent_capture.capture_run) is not enough and you need the wire payload.

Adds NO span and does NOT buffer streaming responses.
"""
from __future__ import annotations

import json
from typing import Any

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response, StreamingResponse

from observent_capture import _coerce, _flatten, _is_sensitive, _REDACTED


class ObserventHTTPMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Any) -> Response:
        from opentelemetry import trace

        span = trace.get_current_span()  # the FastAPI server span — enrich it
        if span.is_recording():
            for k, v in request.headers.items():
                key = f"http.request.headers.{k.lower().replace('-', '_')}"
                span.set_attribute(key, _REDACTED if _is_sensitive(k) else v)
            for k, v in _flatten("http.request.query", dict(request.query_params)):
                span.set_attribute(k, v)

        body = await request.body()  # cached on request; route still reads it
        if span.is_recording() and body:
            try:
                parsed = json.loads(body.decode("utf-8", errors="replace"))
                if isinstance(parsed, (dict, list)):
                    for k, v in _flatten("http.request.body", parsed):
                        span.set_attribute(k, v)
                else:
                    span.set_attribute("http.request.body", _coerce(parsed))
            except (UnicodeDecodeError, json.JSONDecodeError):
                span.set_attribute("http.request.body", body.decode("utf-8", errors="replace"))

        response = await call_next(request)

        # Streaming responses are passed through untouched — never collapse them.
        if span.is_recording() and not isinstance(response, StreamingResponse):
            span.set_attribute("http.response.status_code", response.status_code)
        return response
```

Registration — instrument **before** adding the middleware so the server span exists first:

```python
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from observent_http import ObserventHTTPMiddleware

FastAPIInstrumentor.instrument_app(app)   # opens the server span (+ keeps transport spans)
app.add_middleware(ObserventHTTPMiddleware)
```

---

## Truncation and attribute limits

**No engine-level truncation** — full input/output is flattened into per-key attributes. Two OTel SDK caps still apply:

- **`OTEL_SPAN_ATTRIBUTE_COUNT_LIMIT`** (default `128`) — caps attributes per span; a payload with > 128 leaf fields has its tail dropped. Raise it (e.g. `1024`) for large payloads.
- **`OTEL_ATTRIBUTE_VALUE_LENGTH_LIMIT`** — caps each value's length (unset/unlimited by default).

---

## Convention compatibility

`input.*` / `output.*` are the OI-native single-value keys; `gen_ai.prompt` / `gen_ai.completion` mirror them for OTel-GenAI backends. The flattened per-leaf attributes (`input.user_id`, `http.request.body.*`) are plain OTel attributes that work for all five backends without convention switching. `_CONVENTION` (generation-time literal, derived from the backend set — see `matrix.md § Convention resolution`) decides which single-value mirror(s) are emitted.

---

*Last verified: 2026-05-30 with Python 3.12, OpenTelemetry API/SDK 1.41, Starlette 0.40.*
