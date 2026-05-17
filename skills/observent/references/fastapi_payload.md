# FastAPI Request Payload Capture

When the user's agent app exposes a **FastAPI** (or any ASGI / Starlette) HTTP surface, observent additionally generates a middleware that attaches the inbound request payload — headers, query, and body — as span attributes on the entry-point span. The capture is **schema-agnostic**: the actual payload dict is flattened into individual `key = value` span attributes (no Pydantic model required, no JSON blob, no upfront schema declaration). If the route happens to bind a Pydantic model, its class name is also recorded for reference — but the attribute shape is derived from the *payload itself*, not the model.

For cross-span correlation (filtering LLM / tool / agent spans downstream by request fields like `tenant_id`), the middleware also promotes a configurable whitelist of leaf keys into **OTel baggage**, which a `BaggageSpanProcessor` stamps onto every child span — see § Baggage promotion.

This page is the canonical reference for that middleware. SKILL.md § Step 6 links here.

---

## Maintainer's sources

**Specs:**
- Starlette `BaseHTTPMiddleware` & ASGI middleware — https://www.starlette.io/middleware/
- W3C Trace Context (Level 1) — https://www.w3.org/TR/trace-context/
- OTel baggage API — https://opentelemetry.io/docs/specs/otel/baggage/api/

**Instrumentors & processors:**
- `opentelemetry-instrumentation-fastapi` (provides the FastAPI server span and extracts incoming `traceparent`) — https://opentelemetry-python-contrib.readthedocs.io/en/latest/instrumentation/fastapi/fastapi.html
- `opentelemetry-processor-baggage` (`BaggageSpanProcessor`) — https://github.com/open-telemetry/opentelemetry-python-contrib/tree/main/processor/opentelemetry-processor-baggage

**OTel SDK knobs cited under § Truncation:**
- `OTEL_SPAN_ATTRIBUTE_COUNT_LIMIT` / `OTEL_ATTRIBUTE_VALUE_LENGTH_LIMIT` — https://opentelemetry.io/docs/specs/otel/configuration/sdk-environment-variables/

Last reviewed: 2026-05-17.

---

## When to generate

Generate this middleware when `scripts/detect_framework.py` reports any of these under `web_frameworks`:

- `fastapi`
- `starlette` (FastAPI inherits from Starlette; the middleware works identically)

For Flask / Django, the same idea applies but the hook is different (Flask `before_request` / Django middleware); not covered here.

---

## Attribute keys

Attributes coexist with the standard OTel HTTP attributes (`http.method`, `http.route`, `http.status_code`, `url.path`, etc.) emitted by `opentelemetry-instrumentation-fastapi` — observent's middleware *adds* payload attributes, it does not replace them.

The middleware flattens the payload into **per-key attributes** using dot-notation. Nothing is JSON-blobbed. Each leaf value is set as its own OTel attribute, so backends can index and filter on individual fields (`http.request.body.user_id = "42"`).

### Flattening rules

| Input shape | Becomes |
|---|---|
| `{"user_id": "42"}` | `http.request.body.user_id = "42"` |
| `{"user": {"id": "42", "name": "alice"}}` | `http.request.body.user.id = "42"`<br>`http.request.body.user.name = "alice"` |
| `{"tags": ["a", "b"]}` | `http.request.body.tags = ["a", "b"]` *(OTel list-of-primitives)* |
| `{"items": [{"sku": "x"}, {"sku": "y"}]}` | `http.request.body.items.0.sku = "x"`<br>`http.request.body.items.1.sku = "y"` |
| `{"foo": None}` | *(skipped — OTel attribute values cannot be None)* |
| `"hello"` (top-level scalar) | `http.request.body = "hello"` |
| Non-JSON / binary body | `http.request.body = <decoded string>` |

Leaf values that aren't OTel-typed (`str` / `bool` / `int` / `float` / list of those) are coerced via `str(value)`. Lists of primitives are kept as native OTel list attributes (no flattening). Lists of objects flatten with an integer index segment.

### Attribute namespaces

| Namespace | Sourced from | Notes |
|---|---|---|
| `http.request.headers.<name>` | Request headers | Header name lowercased; `_` substituted for `-` in OTel-style. |
| `http.request.query.<name>` | Query parameters | One attribute per query key. |
| `http.request.body.<path>` | Request body | Flattened JSON body; non-JSON bodies become a single string under `http.request.body`. |
| `http.request.body.pydantic_model` | FastAPI route info | Fully-qualified class name of the bound Pydantic model, when discoverable. Informational only. |
| `http.response.body.<path>` | Response body | Same flattening; non-JSON responses become a single string under `http.response.body`. |

---

## Redaction defaults

The middleware redacts values whose key (case-insensitive, substring match) appears in `_REDACT_KEYS`. The value is replaced with the literal string `***REDACTED***`; the key itself stays in the payload so the attribute shape is preserved.

```python
_REDACT_KEYS: frozenset[str] = frozenset({
    # --- Auth credentials ---
    "api_key", "apikey", "api-key",
    "authorization", "bearer",
    "token", "access_token", "refresh_token", "id_token",
    "secret", "client_secret",
    "password", "passwd", "pwd",
    "x-api-key", "x_api_key",
    "openai_api_key", "anthropic_api_key", "azure_openai_key",
    "aws_access_key", "aws_access_key_id",
    "aws_secret", "aws_secret_access_key",
    # --- Session / CSRF ---
    "cookie", "set-cookie",
    "session", "session_id", "sessionid",
    "csrf", "csrf_token", "x-csrf-token", "xsrf-token",
    # --- PII ---
    "email", "e_mail", "email_address",
    "phone", "phone_number", "mobile",
    "ssn", "social_security_number",
    "credit_card", "card_number", "cvv", "cvc",
    "dob", "date_of_birth", "birth_date",
})
```

Matching is **case-insensitive substring** against the key name, so `Authorization`, `X-Authorization`, and `proxy-authorization` all match `authorization`. Nested dicts and lists are walked recursively. Bytes are decoded with `errors="replace"` before checking.

To customize the list, edit `_REDACT_KEYS` in the generated middleware module. There is no env var override — the list is a generation-time literal, matching the same rule observent applies to `_CONVENTION`.

---

## Baggage promotion (cross-span correlation)

Span attributes live on a single span — child spans (LLM calls, tool calls, agent steps created downstream of the route handler) do **not** inherit them. If you want to filter or aggregate child spans by a request field (e.g. *"all LLM spans where `tenant_id = acme`"* or *"tool spans grouped by `session_id`"*), the OTel-native answer is **baggage**: values you set as baggage propagate automatically through the trace context, and a `BaggageSpanProcessor` stamps them onto every span as it starts.

The middleware promotes a configurable whitelist of leaf keys from the request payload into baggage. Matching is **exact, case-sensitive on the last dot-segment** of the flattened attribute key — so `http.request.body.user.tenant_id` matches `tenant_id` in the whitelist, and `http.request.headers.x_tenant_id` matches `x_tenant_id`. Redacted values are never promoted. The baggage value is `str(value)` (baggage entries are strings per the OTel spec).

```python
_PROMOTE_TO_BAGGAGE: frozenset[str] = frozenset({
    "tenant_id",
    "user_id",
    "session_id",
    "request_id",
})
```

This is a **generation-time literal**, same rule as `_REDACT_KEYS` and `_CONVENTION` — no env var override. Edit it in the generated file to add or remove keys.

**Baggage vs `tracestate` — disambiguation.** OTel baggage rides its own `baggage` HTTP header (W3C Baggage candidate spec), **not** W3C `tracestate` (TC §3.3). The two are independent: `tracestate` carries vendor-specific routing entries (max 32, 512-byte total — TC §3.3.1.2), while `baggage` carries user-defined cross-cutting attributes. Promoted keys here go into `baggage` and never touch `tracestate`. The 32-entry / 512-byte `tracestate` cap therefore does not apply to your whitelist size — but you do want to keep the whitelist small for the same reason `BaggageSpanProcessor` stamps everything: per-span attribute cardinality and ingest cost.

### Registering the BaggageSpanProcessor

For the promoted baggage to land on child spans, register `BaggageSpanProcessor` on your `TracerProvider`:

```python
from opentelemetry.processor.baggage import BaggageSpanProcessor, ALLOW_ALL_BAGGAGE_KEYS

# Option A — copy every baggage key onto every span (simplest, matches _PROMOTE_TO_BAGGAGE by construction).
provider.add_span_processor(BaggageSpanProcessor(ALLOW_ALL_BAGGAGE_KEYS))

# Option B — restrict to a specific whitelist (defence in depth if other code also sets baggage).
provider.add_span_processor(BaggageSpanProcessor(
    lambda key: key in {"tenant_id", "user_id", "session_id", "request_id"}
))
```

Install: `pip install opentelemetry-processor-baggage`.

Place this processor on the same `TracerProvider` that carries the OTLP exporters (Phoenix / Langfuse / SigNoz / LangSmith) — Elastic APM picks up the same spans through its OTel bridge, so promoted baggage lands in Kibana too.

### What you can query after this

Every child span (LLM, tool, agent, retriever) carries the promoted keys as plain span attributes — `tenant_id`, `user_id`, etc. — so queries like *"LLM spans in tenant=acme"* or *"tool spans grouped by session"* work in Phoenix / Langfuse / SigNoz / Elastic APM / LangSmith without needing to traverse up to the server span.

### Why not duplicate the whole payload onto every span?

Full payload duplication (every `http.request.body.*` attribute stamped onto every child span) is exhaustive but expensive — N spans × full payload, plus brittleness under sampling. Most users only need a handful of correlation keys at the child level; baggage promotion gives you that at a fraction of the per-attribute cost. Reach for full duplication only when child spans genuinely need to be self-describing in isolation.

---

## Truncation and attribute limits

**No middleware-level truncation.** Full payloads are flattened into per-key attributes regardless of size. Two OTel-level caps still apply, and you should be aware of them:

- **`OTEL_SPAN_ATTRIBUTE_COUNT_LIMIT`** (default `128`) — caps attributes *per span*. A payload with > 128 leaf fields will have its tail silently dropped. Raise it (e.g., `OTEL_SPAN_ATTRIBUTE_COUNT_LIMIT=1024`) if you regularly carry large payloads, or tighten the route's input schema.
- **`OTEL_ATTRIBUTE_VALUE_LENGTH_LIMIT`** — caps each *value*'s length. Default is unset (unlimited); set it explicitly if your backend rejects long strings (e.g., a single 2 MB blob from a non-JSON body).

These are SDK-level knobs — the middleware itself never truncates, so the attributes you see are always the real values (just possibly fewer of them when the count cap kicks in).

---

## Canonical middleware

Generated as `observent_fastapi_payload.py` in the user's project root and registered in the FastAPI app entry point with `app.add_middleware(ObserventPayloadMiddleware)`.

```python
# observent_fastapi_payload.py
"""FastAPI ASGI middleware that captures inbound request + outbound response
payloads as per-key span attributes, with sensitive-key redaction.

Each leaf value in the payload is set as its own OTel attribute under a
dot-notation namespace (`http.request.body.<path>`), so backends can index
and filter on individual fields. No JSON blob, no schema declaration.

Generated by observent. Edit _REDACT_KEYS to customize redaction; no env-var
override is read at runtime by design.
"""
from __future__ import annotations

import json
from typing import Any, Iterable, Iterator

from opentelemetry import baggage, context, trace
from opentelemetry.util.types import AttributeValue
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

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

# OTel attribute values must be one of these primitives, or a list of one
# of these primitives. Anything else is coerced via str().
_PRIMITIVES = (str, bool, int, float)

# Leaf names promoted from the flattened request payload into OTel baggage,
# so a BaggageSpanProcessor can stamp them onto every child span.
_PROMOTE_TO_BAGGAGE: frozenset[str] = frozenset({
    "tenant_id",
    "user_id",
    "session_id",
    "request_id",
})


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
            # Strip Nones for OTel list-of-primitives.
            cleaned = [v for v in value if v is not None]
            if cleaned:
                yield prefix, _coerce(cleaned)
            return
        for i, v in enumerate(value):
            yield from _flatten(f"{prefix}.{i}", v)
        return
    yield prefix, _coerce(value)


def _redact_headers(headers: Iterable[tuple[str, str]]) -> Iterator[tuple[str, str]]:
    for k, v in headers:
        otel_key = f"http.request.headers.{k.lower().replace('-', '_')}"
        yield otel_key, (_REDACTED if _is_sensitive(k) else v)


def _maybe_promote(attr_key: str, value: AttributeValue, ctx: context.Context) -> context.Context:
    """If the leaf segment of attr_key is in _PROMOTE_TO_BAGGAGE and the value
    isn't redacted, attach it to baggage. Returns the (possibly updated) context."""
    if value == _REDACTED:
        return ctx
    leaf = attr_key.rsplit(".", 1)[-1]
    if leaf not in _PROMOTE_TO_BAGGAGE:
        return ctx
    return baggage.set_baggage(leaf, str(value), context=ctx)


class ObserventPayloadMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Any) -> Response:
        span = trace.get_current_span()
        ctx = context.get_current()

        if span.is_recording():
            for k, v in _redact_headers(request.headers.items()):
                span.set_attribute(k, v)
                ctx = _maybe_promote(k, v, ctx)
            for k, v in _flatten("http.request.query", dict(request.query_params)):
                span.set_attribute(k, v)
                ctx = _maybe_promote(k, v, ctx)

        # Body — read once and re-inject so the route handler still sees it.
        # Starlette caches the body on `request._body`; setting it here avoids
        # the "stream consumed" error on downstream `await request.json()`.
        body_bytes = await request.body()
        if body_bytes:
            try:
                parsed = json.loads(body_bytes.decode("utf-8", errors="replace"))
                if span.is_recording():
                    if isinstance(parsed, (dict, list)):
                        for k, v in _flatten("http.request.body", parsed):
                            span.set_attribute(k, v)
                            ctx = _maybe_promote(k, v, ctx)
                    else:
                        span.set_attribute("http.request.body", _coerce(parsed))
            except (UnicodeDecodeError, json.JSONDecodeError):
                if span.is_recording():
                    span.set_attribute(
                        "http.request.body",
                        body_bytes.decode("utf-8", errors="replace"),
                    )

        # Informational: surface the Pydantic model name when FastAPI has resolved the route.
        route = request.scope.get("route")
        if span.is_recording() and route is not None:
            body_field = getattr(route, "body_field", None)
            model = getattr(body_field, "type_", None) if body_field is not None else None
            if model is not None:
                span.set_attribute(
                    "http.request.body.pydantic_model",
                    f"{model.__module__}.{model.__qualname__}",
                )

        # Attach promoted baggage so it propagates to all child spans during call_next.
        token = context.attach(ctx)
        try:
            response = await call_next(request)
        finally:
            context.detach(token)

        # Buffer the response body so we can attach it AND still send it downstream.
        chunks: list[bytes] = []
        async for chunk in response.body_iterator:
            chunks.append(chunk)
        body = b"".join(chunks)

        if span.is_recording() and body:
            try:
                parsed = json.loads(body.decode("utf-8", errors="replace"))
                if isinstance(parsed, (dict, list)):
                    for k, v in _flatten("http.response.body", parsed):
                        span.set_attribute(k, v)
                else:
                    span.set_attribute("http.response.body", _coerce(parsed))
            except (UnicodeDecodeError, json.JSONDecodeError):
                span.set_attribute(
                    "http.response.body",
                    body.decode("utf-8", errors="replace"),
                )

        return Response(
            content=body,
            status_code=response.status_code,
            headers=dict(response.headers),
            media_type=response.media_type,
        )
```

Registration — **ordering matters**:

```python
# main.py
from fastapi import FastAPI
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from observent_fastapi_payload import ObserventPayloadMiddleware

app = FastAPI()

# 1. MUST run BEFORE add_middleware — creates the FastAPI server span from the
#    incoming W3C `traceparent` (RFC W3C-TC §3.2) so our middleware writes
#    payload attributes onto that span. Reverse the order and `dispatch()` will
#    call `trace.get_current_span()` on an INVALID_SPAN — silent loss of
#    upstream trace continuity, attributes go nowhere.
FastAPIInstrumentor.instrument_app(app)

app.add_middleware(ObserventPayloadMiddleware)
```

`opentelemetry-instrumentation-fastapi` (which observent already installs for cross-service propagation) extracts the incoming W3C `traceparent` / `tracestate` headers via OTel's default `TraceContextTextMapPropagator` and creates the FastAPI server span. Per W3C TC §3.2.2.2, a malformed `traceparent` is silently dropped and a new trace is started — that behavior is mandated by the spec; do **not** add custom parsing that rejects the request on a bad header. The middleware above then runs *inside* that server span, so every payload attribute lands on the same span that carries `http.method` / `http.route` / `http.status_code`. Phoenix / Langfuse / SigNoz / Elastic APM / LangSmith all surface the payload on the request row.

If you want the promoted baggage keys (see § Baggage promotion) to also land on every child LLM / tool / agent span, register `BaggageSpanProcessor` on the same `TracerProvider`.

---

## Convention compatibility

The `http.request.*` / `http.response.*` namespace is OTel-standard and works for all five backends without convention switching — Phoenix renders them under the request span's attributes panel, Langfuse / SigNoz / LangSmith expose them via the OTel-GenAI compatible UI, Elastic APM ingests them through the OTel bridge. The OI vs OTel-GenAI distinction (which governs LLM span keys) does not apply here.

---

*Last verified: 2026-05-17 with Python 3.12, FastAPI 0.115, Starlette 0.40, OpenTelemetry SDK 1.25.*
