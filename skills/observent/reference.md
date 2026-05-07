# observent Reference

Complete reference for frameworks, backends, integration mechanics, span attributes, and context propagation. SKILL.md references this document during code generation.

---

## 8 × 3 Compatibility Matrix

| Framework | Arize Phoenix | Langfuse | SigNoz |
|---|---|---|---|
| LangGraph | OI: `LangChainInstrumentor` | LangChain callback (`langfuse.langchain.CallbackHandler`) | OTLP + OI: `LangChainInstrumentor` |
| CrewAI | OI: `CrewAIInstrumentor` (+ LangChain) | LangChain callback (CrewAI inherits) | OTLP + OI: `CrewAIInstrumentor` |
| AutoGen v0.4 | OI: `OpenAIInstrumentor` + `autogen-ext` OTel | OTLP exporter + `OpenAIInstrumentor` | OTLP + `OpenAIInstrumentor` |
| Anthropic Agents SDK | OI: `AnthropicInstrumentor` | `langfuse` decorator `@observe` (or `OpenAIInstrumentor`-style for Anthropic) | OTLP + OI: `AnthropicInstrumentor` |
| OpenAI Agents SDK | **Native trace processor** (`phoenix.otel.OpenAIAgentsTracingProcessor`) | **Native trace processor** (Langfuse OpenAIAgents processor) | **Native trace processor** with OTLP backend |
| smolagents | OI: `SmolagentsInstrumentor` | OI: `SmolagentsInstrumentor` (Langfuse consumes OTel) | OTLP + OI: `SmolagentsInstrumentor` |
| LlamaIndex | OI: `LlamaIndexInstrumentor` | `langfuse.llama_index` callback | OTLP + OI: `LlamaIndexInstrumentor` |
| Custom | Manual spans + helper functions | Manual spans + `langfuse` decorator | Manual spans + OTLP exporter |

**OI** = OpenInference instrumentor (`openinference-instrumentation-*`). For Phoenix and SigNoz, the OI instrumentor is the same — only the exporter destination differs.

---

## Verified Versions

Last verified: 2026-05-07 against Python 3.12.

| Package | Minimum version |
|---|---|
| arize-phoenix | >=5.0 |
| langfuse | >=3.0 |
| opentelemetry-sdk | >=1.25 |
| opentelemetry-exporter-otlp-proto-http | >=1.25 |
| langgraph | >=0.2 |
| crewai | >=0.80 |
| autogen-agentchat | >=0.4 |
| anthropic | >=0.40 |
| openai-agents | >=0.0.4 |
| smolagents | >=1.0 |
| llama-index | >=0.11 |
| openinference-instrumentation-langchain | >=0.1 |
| openinference-instrumentation-crewai | >=0.1 |
| openinference-instrumentation-openai | >=0.1 |
| openinference-instrumentation-openai-agents | >=0.1 |
| openinference-instrumentation-anthropic | >=0.1 |
| openinference-instrumentation-llama-index | >=2.0 |
| openinference-instrumentation-smolagents | >=0.1 |

These are the floors `examples.md` and the per-framework install commands below target. When bumping any minimum, update this table **and** the per-example "Last verified" footer in `examples.md` to match.

---

## Per-Backend Reference

### Arize Phoenix

- **Type:** Open source (Apache 2.0). Local UI at `http://localhost:6006` via `pip install arize-phoenix`. Cloud at `app.phoenix.arize.com`.
- **Modern setup API:** `phoenix.otel.register(project_name=..., auto_instrument=True)` returns a `TracerProvider` and (with `auto_instrument=True`) auto-loads any installed OpenInference instrumentors.
- **Endpoints:**
  - Local OTLP HTTP: `http://localhost:6006/v1/traces`
  - Local OTLP gRPC: `localhost:4317`
  - Cloud OTLP HTTP: `https://app.phoenix.arize.com/v1/traces`
- **Auth:** None for local. Cloud uses `PHOENIX_API_KEY` as `Authorization: Bearer <key>`.
- **Required env vars:** None local. Cloud: `PHOENIX_API_KEY`, optional `PHOENIX_COLLECTOR_ENDPOINT`.
- **Optional env vars:** `PHOENIX_PROJECT_NAME` (groups traces into projects).
- **Install:** `pip install 'arize-phoenix>=5.0' 'opentelemetry-sdk>=1.25' 'opentelemetry-exporter-otlp-proto-http>=1.25'`

**Canonical setup snippet:**

```python
import os
from phoenix.otel import register

tracer_provider = register(
    project_name=os.getenv("PHOENIX_PROJECT_NAME", "my-agent-app"),
    endpoint=os.getenv("PHOENIX_COLLECTOR_ENDPOINT", "http://localhost:6006/v1/traces"),
    auto_instrument=True,  # picks up installed openinference-instrumentation-* packages
)
```

For local development with no Phoenix server running, start one inline:

```python
import phoenix as px
session = px.launch_app()  # UI on http://localhost:6006
```

### Langfuse

- **Type:** Open source (MIT). Self-hostable via Docker. Cloud at `cloud.langfuse.com` (EU) and `us.cloud.langfuse.com` (US).
- **Integration mechanisms:**
  - **LangChain callback** (LangGraph, CrewAI) — `from langfuse.langchain import CallbackHandler`
  - **Decorator** (Custom, Anthropic SDK) — `from langfuse import observe`
  - **OpenAI wrapper** (raw OpenAI SDK use) — `from langfuse.openai import openai`
  - **OTLP** (any OTel pipeline) — POST to `<host>/api/public/otel/v1/traces` with Basic auth
- **Endpoints (OTLP path):**
  - Self-host: `http://localhost:3000/api/public/otel/v1/traces`
  - Cloud US: `https://us.cloud.langfuse.com/api/public/otel/v1/traces`
  - Cloud EU: `https://cloud.langfuse.com/api/public/otel/v1/traces`
- **Auth:** HTTP Basic — `Authorization: Basic base64(public_key:secret_key)`.
- **Required env vars:** `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`. Optional `LANGFUSE_HOST` (defaults to `https://cloud.langfuse.com`).
- **Install:** `pip install 'langfuse>=3.0'` (plus framework-specific extras as listed below).

**Canonical setup snippets:**

LangChain callback (LangGraph, CrewAI):
```python
import os
from langfuse.langchain import CallbackHandler

langfuse_handler = CallbackHandler()  # reads env vars LANGFUSE_PUBLIC_KEY/SECRET_KEY/HOST
```

Decorator (Custom, Anthropic SDK):
```python
from langfuse import observe, get_client

langfuse = get_client()

@observe()
def run_agent(user_input: str) -> str:
    ...
    return result
```

OTLP (when you already have a `TracerProvider`):
```python
import base64, os
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter

host = os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com").rstrip("/")
auth = base64.b64encode(
    f"{os.environ['LANGFUSE_PUBLIC_KEY']}:{os.environ['LANGFUSE_SECRET_KEY']}".encode()
).decode()

exporter = OTLPSpanExporter(
    endpoint=f"{host}/api/public/otel/v1/traces",
    headers={"Authorization": f"Basic {auth}"},
)
```

### SigNoz

- **Type:** Open source. Self-host via Docker Compose. Cloud at `signoz.cloud` with US/EU/IN regions.
- **Integration mechanism:** Pure OTLP — works with any OpenTelemetry-instrumented code. Pair with `openinference-instrumentation-*` for LLM-specific attributes.
- **Endpoints:**
  - Self-host OTLP HTTP: `http://localhost:4318/v1/traces`
  - Self-host OTLP gRPC: `localhost:4317`
  - Self-host UI: `http://localhost:3301`
  - Cloud OTLP: `https://ingest.{us,eu,in}.signoz.cloud:443/v1/traces`
  - Cloud UI: `https://<tenant>.{us,eu,in}.signoz.cloud`
- **Auth:** None for self-host. Cloud requires header `signoz-access-token: <token>`. (Verify against current SigNoz docs — header name has changed historically.)
- **Required env vars:** `SIGNOZ_ENDPOINT` (full OTLP traces URL). Cloud also requires `SIGNOZ_INGESTION_KEY`.
- **Install:** `pip install 'opentelemetry-sdk>=1.25' 'opentelemetry-exporter-otlp-proto-http>=1.25'` + relevant `openinference-instrumentation-*` packages.

**Self-host quickstart:**
```bash
git clone -b main https://github.com/SigNoz/signoz.git && cd signoz/deploy
docker compose -f docker/clickhouse-setup/docker-compose.yaml up -d
# UI at http://localhost:3301
# OTLP receiver at http://localhost:4318
```

**Canonical setup snippet:**
```python
import os
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

headers = {}
if key := os.getenv("SIGNOZ_INGESTION_KEY"):
    headers["signoz-access-token"] = key

exporter = OTLPSpanExporter(
    endpoint=os.getenv("SIGNOZ_ENDPOINT", "http://localhost:4318/v1/traces"),
    headers=headers,
)

provider = TracerProvider(
    resource=Resource.create({
        "service.name": os.getenv("OTEL_SERVICE_NAME", "my-agent-app"),
    }),
)
provider.add_span_processor(BatchSpanProcessor(exporter))
trace.set_tracer_provider(provider)
```

---

## Per-Framework Reference

### LangGraph (`langgraph`)

- **Tracing model:** LangChain callback system + standard OTel via `LangChainInstrumentor`.
- **Key entry points:** `StateGraph.compile()` → `.invoke()`, `.stream()`, `.astream()`.
- **Where to thread `session_id`:** `RunnableConfig.configurable["session_id"]` and as OTel baggage.
- **Phoenix / SigNoz:** `pip install openinference-instrumentation-langchain` then call `LangChainInstrumentor().instrument(tracer_provider=provider)`.
- **Langfuse:** `langfuse.langchain.CallbackHandler` passed via `config={"callbacks": [handler]}`.
- **Docs:** https://langchain-ai.github.io/langgraph/

### CrewAI (`crewai`)

- **Tracing model:** Native CrewAI events + LangChain callbacks for the underlying LLM calls.
- **Key entry points:** `Crew.kickoff()`, `Agent`, `Task` (delegations create child spans).
- **Where to thread `session_id`:** Pass via `inputs` dict and set OTel baggage at the top.
- **Phoenix / SigNoz:** `pip install openinference-instrumentation-crewai openinference-instrumentation-langchain` — captures Crew → Agent → Task → LLM hierarchy.
- **Langfuse:** Use `langfuse.langchain.CallbackHandler` — CrewAI's LLM wrapper inherits LangChain callbacks.
- **Docs:** https://docs.crewai.com

### AutoGen v0.4 (`autogen-agentchat`)

- **Tracing model:** OpenTelemetry-native via `autogen-ext`. Underlying model calls captured by `OpenAIInstrumentor`.
- **Key entry points:** `RoundRobinGroupChat.run()`, `AssistantAgent`, `Selector`/`Swarm`/`MagenticOne` teams.
- **Where to thread `session_id`:** OTel baggage at the top — `autogen-ext` propagates context across the team.
- **Phoenix / SigNoz / Langfuse via OTLP:** `pip install openinference-instrumentation-openai` + the autogen-ext OTel hooks.
- **Note:** v0.2 (`pyautogen`) is **not** supported here — use the Custom path or migrate.
- **Docs:** https://microsoft.github.io/autogen/

### Anthropic Agents SDK (`anthropic`)

- **Tracing model:** Wrap entry points with the OpenInference Anthropic instrumentor or with Langfuse `@observe` decorators.
- **Key entry points:** `client.messages.create()`, `client.beta.messages.create()`, agent tool-call loops.
- **Where to thread `session_id`:** Set OTel baggage at the top of each conversation turn.
- **Phoenix / SigNoz:** `pip install openinference-instrumentation-anthropic` — captures `prompt_token_count`, `completion_token_count`, **prompt cache read/write tokens**, tool calls.
- **Langfuse:** `@observe(as_type="generation")` and update via `langfuse_context.update_current_observation(usage={...})`.
- **Docs:** https://docs.anthropic.com/en/docs/agents

### OpenAI Agents SDK (`openai-agents`)

- **Tracing model:** **Native** — the SDK has its own tracing pipeline configurable via `set_trace_processors()`. This captures handoffs, guardrails, and agent runs as first-class spans, not as raw OpenAI API calls.
- **Key entry points:** `Runner.run()`, `Agent`, `handoff()`, `Guardrail`.
- **Where to thread `session_id`:** Pass via `Runner.run(... metadata={"session.id": ...})`; use OTel baggage as fallback.
- **Phoenix:** `pip install openinference-instrumentation-openai-agents` then:
  ```python
  from openinference.instrumentation.openai_agents import OpenAIAgentsInstrumentor
  OpenAIAgentsInstrumentor().instrument(tracer_provider=provider)
  ```
- **Langfuse:** Use Langfuse's openai-agents processor (consult Langfuse docs for the current package name) registered via `set_trace_processors([...])`.
- **SigNoz:** Use the same OpenInference instrumentor; the OTLP exporter delivers spans to SigNoz.
- **Do NOT** use plain `openinference-instrumentation-openai` for the Agents SDK — it captures only the underlying HTTP calls and loses agent structure (handoffs, runs, guardrails).
- **Docs:** https://openai.github.io/openai-agents-python/

### smolagents (`smolagents`)

- **Tracing model:** `openinference-instrumentation-smolagents` covers `CodeAgent.run()`, `ToolCallingAgent.run()`, tool calls, LLM calls.
- **Phoenix / SigNoz / Langfuse:** Same instrumentor — only the exporter destination changes.
- **Install:** `pip install openinference-instrumentation-smolagents`
- **Docs:** https://huggingface.co/docs/smolagents

### LlamaIndex (`llama_index`)

- **Tracing model:** `openinference-instrumentation-llama-index` (preferred) or LlamaIndex's `set_global_handler()` API.
- **Key entry points:** `Workflow.run()`, `QueryEngine.query()`, `RetrieverQueryEngine.query()`, `AgentWorker.run_step()`.
- **Phoenix / SigNoz:** `pip install openinference-instrumentation-llama-index`
- **Langfuse:** `from langfuse.llama_index import LlamaIndexCallbackHandler` then `Settings.callback_manager = CallbackManager([handler])`.
- **Docs:** https://docs.llamaindex.ai

### Custom (no framework)

- **Tracing model:** Manual OTel spans. The skill writes an `observent_otel.py` helper module into the user's project with typed setters: `set_llm_attrs(span, model, input_messages, output_messages, prompt_tokens, completion_tokens, ...)`, `set_tool_attrs(span, name, parameters, input_value, output_value)`, `set_agent_attrs(span, name, role)`.
- **Pattern:** wrap each agent step in `tracer.start_as_current_span("agent.step", attributes={"openinference.span.kind": "AGENT", ...})`.

---

## Mandatory Span Attributes

The skill emits attributes following both **OpenInference** semantic conventions (Phoenix-native, also consumed by Langfuse) and the newer **OpenTelemetry GenAI** semantic conventions (consumed by all three backends). For maximum compatibility, both are emitted where they overlap.

### LLM spans

| Attribute (OpenInference) | Attribute (OTel GenAI) | Notes |
|---|---|---|
| `openinference.span.kind = "LLM"` | — | OI span kind |
| `llm.model_name` | `gen_ai.request.model` | Resolved model id |
| `llm.provider` | `gen_ai.system` | `openai` / `anthropic` / etc. |
| `llm.invocation_parameters` (JSON) | `gen_ai.request.temperature`, `.max_tokens`, ... | temp, max_tokens, top_p, stop |
| `llm.input_messages` (array) | `gen_ai.prompt` | Each message: `role`, `content`, optional `tool_calls` |
| `llm.output_messages` (array) | `gen_ai.completion` | Each message: `role`, `content` |
| `input.value` (JSON string) | — | At-a-glance input |
| `output.value` (JSON string) | — | At-a-glance output |
| `input.mime_type = "application/json"` | — | |
| `output.mime_type = "application/json"` | — | |
| `llm.token_count.prompt` | `gen_ai.usage.input_tokens` | int |
| `llm.token_count.completion` | `gen_ai.usage.output_tokens` | int |
| `llm.token_count.total` | — | sum |
| `llm.token_count.prompt_details.cache_read` | — | Anthropic prompt caching |
| `llm.token_count.prompt_details.cache_write` | — | Anthropic prompt caching |
| `llm.tools` (array of tool schemas) | — | When tools are passed in the request |
| `llm.function_call` / `message.tool_calls` | `gen_ai.response.tool_calls` | Tool the model chose |
| `llm.finish_reasons` (array) | `gen_ai.response.finish_reasons` | `stop`, `tool_use`, `length`, etc. |

### TOOL spans

- `openinference.span.kind = "TOOL"`
- `tool.name`
- `tool.description`
- `tool.parameters` (JSON schema)
- `input.value` (JSON of actual call args)
- `output.value` (JSON of return value)

### AGENT spans

- `openinference.span.kind = "AGENT"`
- `agent.name` *(required — used for UI grouping)*
- `agent.role`
- `agent.framework` — `langgraph` | `crewai` | `autogen-agentchat` | `anthropic-agents` | `openai-agents` | `smolagents` | `llama-index` | `custom`
- `input.value` — task or message that triggered the agent
- `output.value` — final agent output

### CHAIN spans (workflow / graph nodes)

- `openinference.span.kind = "CHAIN"`
- `input.value`, `output.value`

### RETRIEVER spans (RAG)

- `openinference.span.kind = "RETRIEVER"`
- `retrieval.documents` — array of `{document.id, document.content, document.score, document.metadata}`
- `input.value` — query text
- `embedding.model_name` (when embeddings are used)

### Cross-cutting (every span via Baggage)

- `session.id` — groups traces in the UI per conversation/user session
- `user.id`
- `tenant.id`
- `app.version`

### Cost computation

Token counts are captured but **dollar cost** is computed at ingestion time by the backends from a model→price table. Verify `llm.model_name` (or `gen_ai.request.model`) is set to a model the backend recognizes — otherwise cost columns show `$0` in the UI. Self-hosted Langfuse and SigNoz allow custom model price configs.

---

## Context Propagation

Multi-agent traces only work if context flows correctly across every boundary.

### Sync execution

`tracer.start_as_current_span()` uses `contextvars.ContextVar` under the hood — context is automatic. **Never** use the lower-level `start_span()` unless you also call `trace.use_span(span, end_on_exit=True)`.

### Async execution

Python 3.11+ inherits `Context` automatically across `asyncio.create_task` (PEP 654 / contextvars). For **older Python** (< 3.11), wrap manually:

```python
import contextvars

def _spawn_with_context(coro):
    ctx = contextvars.copy_context()
    return asyncio.create_task(coro, context=ctx)
```

### Threads / subprocesses

For `concurrent.futures.ThreadPoolExecutor`:

```python
from opentelemetry import context as otel_context

def worker(ctx, payload):
    token = otel_context.attach(ctx)
    try:
        return do_work(payload)
    finally:
        otel_context.detach(token)

ctx = otel_context.get_current()
executor.submit(worker, ctx, payload)
```

For subprocesses, propagate the W3C `traceparent` via env var:

```python
from opentelemetry.propagate import inject

env = os.environ.copy()
inject(env)  # adds traceparent + tracestate
subprocess.run([...], env=env)
```

The child process loads it via `from opentelemetry.propagate import extract; extract(os.environ)`.

### Cross-service / cross-agent network calls

Install `opentelemetry-instrumentation-httpx` and `opentelemetry-instrumentation-requests`. Initialize once:

```python
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor

HTTPXClientInstrumentor().instrument()
RequestsInstrumentor().instrument()
```

Outgoing HTTP requests will carry `traceparent` and `tracestate` headers automatically, so a downstream agent service can resume the trace.

### Agent handoffs

- **OpenAI Agents SDK** — handoffs are first-class trace events when using `set_trace_processors()`. No manual work.
- **AutoGen v0.4** — `autogen-ext`'s OTel integration captures team-to-team and agent-to-agent message passing. Enable explicitly per its docs.
- **CrewAI** — Task delegation creates parent/child spans automatically via `openinference-instrumentation-crewai`.
- **LangGraph** — Each node transition becomes a span automatically via `LangChainInstrumentor`.
- **Custom** — Use a `with_agent_context` helper to attach agent identity:

```python
from contextlib import contextmanager
from opentelemetry import trace, baggage

@contextmanager
def with_agent_context(name: str, role: str = "", framework: str = "custom"):
    tracer = trace.get_tracer(__name__)
    with tracer.start_as_current_span(f"agent.{name}") as span:
        span.set_attribute("openinference.span.kind", "AGENT")
        span.set_attribute("agent.name", name)
        span.set_attribute("agent.role", role)
        span.set_attribute("agent.framework", framework)
        yield span
```

### Baggage (cross-cutting attributes)

Set once at the entry point; flows through async/thread/subprocess/HTTP boundaries automatically:

```python
from opentelemetry import baggage, context

ctx = baggage.set_baggage("session.id", session_id)
ctx = baggage.set_baggage("user.id", user_id, context=ctx)
ctx = baggage.set_baggage("app.version", "1.4.2", context=ctx)
token = context.attach(ctx)
try:
    run_agent(user_input)
finally:
    context.detach(token)
```

To turn baggage into span attributes (so they appear in the UI), add `BaggageSpanProcessor`:

```python
from opentelemetry.processor.baggage import BaggageSpanProcessor, ALLOW_ALL_BAGGAGE_KEYS
provider.add_span_processor(BaggageSpanProcessor(ALLOW_ALL_BAGGAGE_KEYS))
```

---

## Multi-Backend Fan-Out

Send the same spans to multiple backends simultaneously:

```python
provider = TracerProvider()
provider.add_span_processor(BatchSpanProcessor(phoenix_exporter))
provider.add_span_processor(BatchSpanProcessor(signoz_exporter))
trace.set_tracer_provider(provider)
```

Each processor exports independently. If one backend is unreachable, the others still receive spans.

---

## OpenInference Instrumentor Map

| Package | Covers |
|---|---|
| `openinference-instrumentation-langchain` | LangGraph, LangChain, CrewAI underlying LLM calls |
| `openinference-instrumentation-crewai` | CrewAI Crew/Agent/Task structure |
| `openinference-instrumentation-openai` | OpenAI SDK, AutoGen v0.4 (model client) |
| `openinference-instrumentation-openai-agents` | OpenAI Agents SDK (use this — not plain `-openai`) |
| `openinference-instrumentation-anthropic` | Anthropic SDK incl. prompt caching tokens |
| `openinference-instrumentation-llama-index` | LlamaIndex Workflows, QueryEngines, Retrievers |
| `openinference-instrumentation-smolagents` | smolagents CodeAgent/ToolCallingAgent |
| `openinference-instrumentation-bedrock` | AWS Bedrock |
| `openinference-instrumentation-vertexai` | Google Vertex AI |

All are installable from PyPI. They emit standard OpenInference + OTel GenAI attributes — the exporter (Phoenix / SigNoz / Langfuse OTLP) determines the destination.

---

## Troubleshooting

### "No traces appearing"

1. Verify env vars actually loaded — print them at startup.
2. Force flush before exit: `provider.shutdown()` (OTel) or `langfuse.flush()` (Langfuse client). Add as `atexit` handler.
3. For Phoenix local — confirm UI is at `http://localhost:6006` and `px.launch_app()` was called.
4. For SigNoz self-host — confirm `docker compose ps` shows `signoz-otel-collector` healthy on port 4318.
5. Corporate proxy? OTLP HTTP works through proxies; gRPC often does not.

### "Traces appear but token counts are missing"

Token counts come from the LLM response. The instrumentor extracts them from the API response. If using a custom LLM wrapper, verify it surfaces `usage.input_tokens` / `usage.output_tokens`. For manual span emission (Custom path), set them explicitly using the helper functions in `observent_otel.py`.

### "Cost shows $0"

Backends compute cost from `llm.model_name` lookups in their internal price table. If your model name is non-standard (e.g. an Azure deployment alias), set the canonical model name on the span and use `llm.invocation_parameters` for the deployment id.

### "Trace tree is broken / orphan spans"

Context propagation issue. Check:
- Async — using Python ≥ 3.11 or wrapping `create_task` with `copy_context`.
- Threads — using the `attach()`/`detach()` pattern.
- HTTP — `RequestsInstrumentor` / `HTTPXClientInstrumentor` enabled.
- Manual spans — using `start_as_current_span`, not `start_span`.

### "401 / authentication error"

- **Phoenix Cloud:** `PHOENIX_API_KEY` set.
- **Langfuse:** Public/secret keys not swapped; `LANGFUSE_HOST` matches the workspace where the keys were issued.
- **SigNoz Cloud:** `SIGNOZ_INGESTION_KEY` set; header name (`signoz-access-token`) matches current docs.

### "OpenAI Agents SDK shows raw HTTP calls instead of agent spans"

You're using `openinference-instrumentation-openai`. Switch to `openinference-instrumentation-openai-agents` and register via `set_trace_processors()`.
