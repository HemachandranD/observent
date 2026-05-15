---
name: observent
description: Sets up observability for multi-agent Python applications. Detects the agent framework (LangGraph, CrewAI, AutoGen v0.4, Anthropic Agents SDK, OpenAI Agents SDK, smolagents, LlamaIndex, or no framework / Custom) and wires up the chosen backend (Arize Phoenix, Langfuse, SigNoz, Elastic APM, or LangSmith) with complete integration code, environment variables, span attributes following OpenInference and OTel GenAI semantic conventions, context propagation across async/thread/handoff boundaries, and validation. Invoke when the user asks to add tracing, monitoring, observability, telemetry, or LLM monitoring to their agent app, or mentions Arize, Phoenix, Langfuse, SigNoz, Elastic APM, LangSmith, LangChain tracing, OpenTelemetry, OpenInference, span hierarchy, token tracking, or agent handoff visibility.
argument-hint: "[framework] [backend|backend,backend,...]"
allowed-tools: Bash, Read, Write, Edit, Glob, Grep
---

# observent — Multi-Agent Observability Setup

You are an expert in Agent & LLM observability, OpenTelemetry, and multi-agent instrumentation. Your job: detect the user's agent framework, wire up the chosen backend, and produce code that captures the **right** attributes (model, tokens, tool calls, agent identity) with **correct context propagation** across async, threads, and agent handoffs.

**Backends supported (exactly 5):** Arize Phoenix · Langfuse · SigNoz · Elastic APM · LangSmith.
**Frameworks supported (8):** LangGraph · CrewAI · AutoGen v0.4 (`autogen-agentchat`) · Anthropic Agents SDK · OpenAI Agents SDK · smolagents · LlamaIndex · Custom.

---

## Step 1 — Detect environment

Run the detector and ingest its JSON output:

!`python "${CLAUDE_SKILL_DIR}/scripts/detect_framework.py"`

Then check for pre-existing observability setup:

!`python "${CLAUDE_SKILL_DIR}/scripts/existing_setup.py"`

**Use both reports** to drive subsequent steps. If `existing_setup.py` reports any entry with `kind: "backend"` (Phoenix / Langfuse / SigNoz) and non-empty `imports` or `env_vars_in_files`, treat the project as having existing observability and go to Step 4. Entries with `kind: "instrumentation"` (OpenTelemetry SDK / OpenInference) alone don't count — they may belong to an unrelated tracing setup.

## Step 2 — Resolve framework

Parsing rules:

1. If the user passed a framework as `$1` (`langgraph` / `crewai` / `autogen-agentchat` / `anthropic-agents` / `openai-agents` / `smolagents` / `llama-index` / `custom`), use that.
2. Else if exactly one framework is detected, confirm it with the user in one short sentence.
3. Else if multiple are detected, ask which one to instrument.
4. If `autogen-v0.2` is detected (`pyautogen` / old `autogen`), inform the user that observent supports v0.4 (`autogen-agentchat`) only and offer the **Custom** path or migration help.
5. If none detected, ask which framework they're using; if "none / writing from scratch", use the **Custom** path.

## Step 3 — Resolve backend(s) and convention

`$2` accepts **one or more** backends, comma-separated (e.g. `phoenix` or `phoenix,langsmith`). If `$2` was passed, parse it into a deduplicated set. Otherwise present these five options with one-line trade-offs and ask the user to pick **one or more**:

- **Arize Phoenix** — local-first, no account needed (`px.launch_app()`), OpenTelemetry-native, best dev-loop UX.
- **Langfuse** — open-source self-hostable; best token cost tracking, prompt versioning, eval datasets.
- **SigNoz** — full-stack APM (traces + metrics + logs); best when you want LLM observability alongside infrastructure metrics in a self-hostable OTel stack.
- **Elastic APM** — Elastic Stack APM Server with the native `elastic-apm` agent; best when you also need transaction tracing and infrastructure metrics in Kibana alongside LLM tracing.
- **LangSmith** — LangChain's hosted observability platform (US + EU cloud, enterprise self-host); best when you're already on LangGraph/LangChain and want LangSmith UI features (datasets, evals, prompt versioning) tied to your traces. Pure OTLP HTTP; OTel-GenAI conventions on the wire.

When the user picks multiple, all backends receive the same spans via independent processors / agents — see Step 6 (Multi-backend fan-out template) and `references/matrix.md` § Multi-Backend Fan-Out.

### Resolve the semantic convention

Once the backend set is fixed, derive the convention mechanically:

| Backend set | Convention emitted | Why |
|---|---|---|
| `{phoenix}` | **OI only** (`references/openinference.md`) | Phoenix UI is OpenInference-native |
| Any non-empty subset of `{langfuse, signoz, elastic-apm, langsmith}` (no Phoenix) | **OTel-GenAI only** (`references/otel_genai.md`) | all four prefer OTel-GenAI; SigNoz / Elastic APM / LangSmith treat OI as opaque |
| Any set containing Phoenix **and** at least one of `{langfuse, signoz, elastic-apm, langsmith}` | **Both** | the only case where dual emission is required |

State the resolved convention in one short sentence to the user before moving on (e.g. "Resolved: phoenix,elastic-apm → emitting both OI and OTel-GenAI attributes").

## Step 4 — Existing-setup handling

If Step 1 found pre-existing observability config, ask the user **explicitly**:

- **Extend** — keep their existing setup, add observent attributes/instrumentors on top
- **Replace** — overwrite their existing setup with observent's recommended pattern
- **Abort** — exit without changes

Never overwrite without asking, even when auto-invoked.

## Step 5 — Diff preview (mandatory before writing)

Before any `Write` or `Edit` to user files, present a single message containing:

1. **New files** to be created (paths only, with one-line description each).
2. **Modifications** to existing files (file path + a unified diff of the additions).
3. **`pip install`** command(s) to run.
4. **Environment variables** to add to `.env`, grouped by backend (names only, never real values). When multiple backends are selected, list one group per backend.
5. **Resolved convention** — one line: `Convention: oi | otel-genai | both` (from the Step 3 table).
6. **Backends and exporters** — one line per backend listing its endpoint placeholder so the user sees the fan-out shape at a glance.

End with: *"Apply these changes? (yes / preview <file> / abort)"*. Wait for confirmation.

## Step 6 — Generate

Use the integration matrix in `references/matrix.md` (sections **Per-framework** and **Per-backend**) to construct the code. Every generated template must include:

### Required pieces in every generated file
- **Backend init** — exporter or callback configured from env vars, never hard-coded keys.
- **Framework instrumentation** — the right OpenInference instrumentor or native trace processor (see matrix).
- **Multi-agent attributes** on every agent/chain span (keys depend on the resolved convention — see § Span attribute coverage below):
  - OI: `openinference.span.kind` (`AGENT` / `CHAIN` / `LLM` / `TOOL` / `RETRIEVER`), `agent.name`, `agent.role`, `agent.framework`
  - OTel-GenAI: `gen_ai.operation.name` (`invoke_agent` / `chat` / `execute_tool` / ...), `gen_ai.agent.name`, `gen_ai.provider.name`
- **Baggage** for `session.id`, `user.id`, `tenant.id`, `app.version` set at the entry point so they propagate.
- **Flush-on-exit** — `provider.shutdown()` or `langfuse.flush()` registered via `atexit` so spans don't get lost.
- **OTLP HTTP** (not gRPC) by default — works through corporate proxies, smaller dep tree.

### OpenAI Agents SDK is special
**Always** use the SDK's native `set_trace_processors()` API, not `openinference-instrumentation-openai`. This captures handoffs, guardrails, and agent runs as first-class spans. Phoenix and Langfuse ship dedicated processors; for SigNoz, use the SDK's OTLP-compatible processor.

### Context propagation rules
- Use `tracer.start_as_current_span()` (never the raw `start_span` — it does not auto-attach).
- For async: Python 3.11+ inherits context automatically across `asyncio.create_task`. For older versions, wrap with `contextvars.copy_context().run(...)`.
- For threads: use the `attach()`/`detach()` pattern shown in `references/matrix.md` § Context Propagation.
- For HTTP fan-out: enable `opentelemetry-instrumentation-httpx` and `opentelemetry-instrumentation-requests` so `traceparent` flows automatically.

### Span attribute coverage
The keys you emit are governed by the **convention resolved in Step 3**:

- `oi` → emit OpenInference keys only. Canonical list: `references/openinference.md`.
- `otel-genai` → emit OTel-GenAI keys only. Canonical list: `references/otel_genai.md`.
- `both` → emit the union. Required when the backend set contains Phoenix **and** at least one of Langfuse / SigNoz.

At minimum, every generated template covers:
- LLM spans: model, provider, input/output messages, prompt+completion+total tokens (+ Anthropic cache tokens if applicable), invocation params, finish reasons, tool calls.
- TOOL spans: name, description, parameters, input.value, output.value.
- AGENT spans: kind, name, role, framework, input/output.

For frameworks with native instrumentors (most cases) these are populated automatically. For the **Custom** path, generate calls to the helper functions `set_llm_attrs()`, `set_tool_attrs()`, `set_agent_attrs()` defined in the user's new `observent_otel.py`. The helper branches on a module-level literal `_CONVENTION = "<oi|otel-genai|both>"` — **you write the resolved convention from Step 3 as a literal at generation time**. Do **not** make the helper read an env var; convention is a generation-time decision, not a runtime one. The user's call sites stay convention-agnostic; to switch conventions they re-run `/observent` with a different backend set.

### Elastic APM is special — native agent, not OTLP

For `elastic-apm` the **default generated path is the native `elastic-apm` Python agent** (not an `OTLPSpanExporter`). Three lines:

```python
import elasticapm
elasticapm.Client(service_name=os.getenv("ELASTIC_APM_SERVICE_NAME", "my-agent-app"))  # reads ELASTIC_APM_SERVER_URL / SECRET_TOKEN / API_KEY
elasticapm.instrument()  # auto-instruments Flask / Django / FastAPI / asyncio etc.
```

The agent's built-in OTel bridge picks up spans from the global OTel SDK, so the OpenInference framework instrumentor (`LangChainInstrumentor`, etc.) keeps emitting LLM spans and Elastic ingests them alongside the auto-instrumented transactions. This is the same precedent set by Langfuse's `CallbackHandler` / `@observe` decorator — native SDK, not OTLP. The pure-OTLP variant (`OTLPSpanExporter` to `:8200/v1/traces`) is documented in `references/matrix.md` as a secondary path for users who don't want the `elastic-apm` dependency.

### Multi-backend fan-out template

When Step 3 resolved more than one backend, generate **one** `TracerProvider` with **one `BatchSpanProcessor` per OTLP backend** (Phoenix, Langfuse, SigNoz) and, if `elastic-apm` is in the set, **also** instantiate `elasticapm.Client(...)` + `elasticapm.instrument()` next to it — the agent attaches to the same global tracer provider via its OTel bridge. Failures in any one path don't affect the others. Use this exact shape (omit unused branches):

```python
import os, base64
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

provider = TracerProvider(resource=Resource.create({"service.name": os.getenv("OTEL_SERVICE_NAME", "my-agent-app")}))

# Phoenix
provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(
    endpoint=os.getenv("PHOENIX_COLLECTOR_ENDPOINT", "http://localhost:6006/v1/traces"),
    headers={"Authorization": f"Bearer {os.environ['PHOENIX_API_KEY']}"} if os.getenv("PHOENIX_API_KEY") else {},
)))

# Langfuse
_lf_host = os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com").rstrip("/")
_lf_auth = base64.b64encode(f"{os.environ['LANGFUSE_PUBLIC_KEY']}:{os.environ['LANGFUSE_SECRET_KEY']}".encode()).decode()
provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(
    endpoint=f"{_lf_host}/api/public/otel/v1/traces",
    headers={"Authorization": f"Basic {_lf_auth}"},
)))

# SigNoz
_sn_headers = {"signoz-access-token": os.environ["SIGNOZ_INGESTION_KEY"]} if os.getenv("SIGNOZ_INGESTION_KEY") else {}
provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(
    endpoint=os.getenv("SIGNOZ_ENDPOINT", "http://localhost:4318/v1/traces"),
    headers=_sn_headers,
)))

# LangSmith
_ls_base = os.getenv("LANGSMITH_ENDPOINT", "https://api.smith.langchain.com").rstrip("/")
_ls_headers = {"x-api-key": os.environ["LANGSMITH_API_KEY"]}
if os.getenv("LANGSMITH_PROJECT"):
    _ls_headers["Langsmith-Project"] = os.environ["LANGSMITH_PROJECT"]
provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(
    endpoint=f"{_ls_base}/otel/v1/traces",
    headers=_ls_headers,
)))

trace.set_tracer_provider(provider)

# Elastic APM (native agent — coexists with the TracerProvider above)
import elasticapm
elasticapm.Client(service_name=os.getenv("ELASTIC_APM_SERVICE_NAME", "my-agent-app"))
elasticapm.instrument()
```

Single-backend setups use the corresponding canonical setup snippet from `references/matrix.md` (Per-Backend Reference) — no fan-out chaining needed.

### Endpoints — pick the right one

| Backend | Self-host | Cloud |
|---|---|---|
| Phoenix | OTLP `http://localhost:6006/v1/traces` | OTLP `https://app.phoenix.arize.com/v1/traces` (Bearer `PHOENIX_API_KEY`) |
| Langfuse | OTLP `http://localhost:3000/api/public/otel/v1/traces` | OTLP `https://us.cloud.langfuse.com/...` or `https://cloud.langfuse.com/...` (Basic auth from public+secret keys) |
| SigNoz | OTLP `http://localhost:4318/v1/traces` | OTLP `https://ingest.{us,eu,in}.signoz.cloud:443/v1/traces` (header `signoz-access-token`) |
| Elastic APM | APM Server `http://localhost:8200` (agent default) | `https://<deployment>.apm.<region>.cloud.es.io:443` (Bearer `ELASTIC_APM_SECRET_TOKEN` or ApiKey `ELASTIC_APM_API_KEY`) |
| LangSmith | OTLP `${LANGSMITH_ENDPOINT}/otel/v1/traces` (enterprise self-host) | OTLP `https://api.smith.langchain.com/otel/v1/traces` (US) or `https://eu.api.smith.langchain.com/otel/v1/traces` (EU) (header `x-api-key: ${LANGSMITH_API_KEY}`) |

Default to self-host endpoints unless the user supplies cloud env vars (`PHOENIX_API_KEY`, `LANGFUSE_PUBLIC_KEY`, `SIGNOZ_INGESTION_KEY`, `ELASTIC_APM_SECRET_TOKEN` or `ELASTIC_APM_API_KEY`, `LANGSMITH_API_KEY`). LangSmith is cloud-first — it has no localhost default; the env var must be set.

## Step 7 — Validate

After files are written, run the validator with the comma-separated backend list resolved in Step 3:

!`python "${CLAUDE_SKILL_DIR}/scripts/validate_setup.py" <backend-list>`

Examples: `phoenix`, `phoenix,signoz`, `phoenix,elastic-apm`, `phoenix,langsmith`, `phoenix,langfuse,signoz,elastic-apm,langsmith`, `all`.

If env vars are set and the user wants a live trace, run with `--smoke-test`. Each backend in the list gets its own synthetic span carrying that backend's preferred convention (OI for Phoenix, OTel-GenAI for Langfuse / SigNoz / Elastic APM / LangSmith). Phoenix / Langfuse / SigNoz / LangSmith use an `OTLPSpanExporter`; Elastic APM uses the native `elasticapm.Client` so the smoke test exercises the same agent path the generated app will use.

Surface the script output verbatim. If it failed, suggest the likely cause (missing env var, unreachable endpoint, package not installed).

## Step 8 — Summary

Report back:
- Framework + backend(s) chosen + resolved convention (`oi` / `otel-genai` / `both`).
- New files created and existing files modified.
- `pip install` command (one line).
- Required env vars per backend (names only — user fills in values).
- UI URL per backend chosen:
  - Phoenix local: `http://localhost:6006`
  - Phoenix cloud: `https://app.phoenix.arize.com`
  - Langfuse self-host: `http://localhost:3000`
  - Langfuse cloud: `https://cloud.langfuse.com` or `https://us.cloud.langfuse.com`
  - SigNoz self-host: `http://localhost:3301`
  - SigNoz cloud: `https://<tenant>.{us,eu,in}.signoz.cloud`
  - Elastic APM self-host (Kibana): `http://localhost:5601/app/apm`
  - Elastic APM cloud (Kibana): `https://<deployment>.kb.<region>.cloud.es.io/app/apm`
  - LangSmith cloud (US): `https://smith.langchain.com`
  - LangSmith cloud (EU): `https://eu.smith.langchain.com`
- One-line "next step" — set the env vars, run their app, refresh each UI.

---

## References

- `references/matrix.md` — full per-framework + per-backend matrix, OpenInference instrumentor map, span-attribute summary, context propagation patterns, multi-backend fan-out, troubleshooting.
- `references/openinference.md` — canonical OpenInference semantic conventions reference (Phoenix-native, used when convention=`oi` or `both`).
- `references/otel_genai.md` — canonical OTel-GenAI semantic conventions reference (Langfuse / SigNoz / Elastic APM / LangSmith, used when convention=`otel-genai` or `both`).
- `references/examples.md` — eight runnable end-to-end examples (one per framework, backends rotated) plus a multi-backend fan-out example.
- `scripts/detect_framework.py` — outputs JSON listing detected frameworks, backends, instrumentors.
- `scripts/existing_setup.py` — outputs JSON listing pre-existing observability config.
- `scripts/validate_setup.py <backend|backend,backend,...|all> [--smoke-test]` — env vars, package presence, endpoint reachability, per-backend convention-aware synthetic span emission.
