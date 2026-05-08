# observent Reference

Complete reference for frameworks, backends, integration mechanics, span attributes, and context propagation. `../SKILL.md` references this document during code generation.

---

## 8 × 4 Compatibility Matrix

| Framework | Arize Phoenix | Langfuse | SigNoz | Elastic APM |
|---|---|---|---|---|
| LangGraph | OI: `LangChainInstrumentor` | LangChain callback (`langfuse.langchain.CallbackHandler`) | OTLP + OI: `LangChainInstrumentor` | Native agent + OI: `LangChainInstrumentor` |
| CrewAI | OI: `CrewAIInstrumentor` (+ LangChain) | LangChain callback (CrewAI inherits) | OTLP + OI: `CrewAIInstrumentor` | Native agent + OI: `CrewAIInstrumentor` |
| AutoGen v0.4 | OI: `OpenAIInstrumentor` + `autogen-ext` OTel | OTLP exporter + `OpenAIInstrumentor` | OTLP + `OpenAIInstrumentor` | Native agent + `OpenAIInstrumentor` |
| Anthropic Agents SDK | OI: `AnthropicInstrumentor` | `langfuse` decorator `@observe` (or `OpenAIInstrumentor`-style for Anthropic) | OTLP + OI: `AnthropicInstrumentor` | Native agent + OI: `AnthropicInstrumentor` |
| OpenAI Agents SDK | **Native trace processor** (`phoenix.otel.OpenAIAgentsTracingProcessor`) | **Native trace processor** (Langfuse OpenAIAgents processor) | **Native trace processor** with OTLP backend | Native APM agent + OpenAI Agents SDK trace processor (OTel bridge) |
| smolagents | OI: `SmolagentsInstrumentor` | OI: `SmolagentsInstrumentor` (exporter sends to Langfuse OTLP) | OTLP + OI: `SmolagentsInstrumentor` | Native agent + OI: `SmolagentsInstrumentor` |
| LlamaIndex | OI: `LlamaIndexInstrumentor` | `langfuse.llama_index` callback | OTLP + OI: `LlamaIndexInstrumentor` | Native agent + OI: `LlamaIndexInstrumentor` |
| Custom | Manual spans + helper functions | Manual spans + `langfuse` decorator | Manual spans + OTLP exporter | Manual spans + `elasticapm.Client` (OTel bridge) |

**OI** = OpenInference instrumentor (`openinference-instrumentation-*`). For Phoenix and SigNoz, the OI instrumentor is the same — only the exporter destination differs. For Elastic APM, the OI instrumentor still emits OTel spans; the `elasticapm.Client` agent picks them up via its OTel bridge (no separate exporter needed) and ingests them alongside auto-instrumented transaction spans.

---

## Verified Versions

Last verified: 2026-05-08 against Python 3.12.

| Package | Minimum version |
|---|---|
| arize-phoenix | >=5.0 |
| langfuse | >=3.0 |
| elastic-apm | >=6.20 |
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

### Elastic APM

- **Type:** Open source (Apache 2.0). APM Server is part of the Elastic Stack. Self-host via Docker / Kubernetes; cloud at `elastic.co` with multi-region deployments.
- **Integration mechanism:** **Native `elastic-apm` Python agent** (the default observent generates). The agent posts to APM Server's intake endpoint and includes a built-in OTel bridge that picks up spans from the global OTel SDK — so OpenInference framework instrumentors keep working unchanged. A pure-OTLP path is also supported and documented as the secondary alternative.
- **Endpoints:**
  - Self-host APM Server: `http://localhost:8200` (agent default; intake at `/intake/v2/events`, OTLP at `/v1/traces`)
  - Self-host Kibana UI: `http://localhost:5601/app/apm`
  - Cloud APM Server: `https://<deployment>.apm.<region>.cloud.es.io:443`
  - Cloud Kibana UI: `https://<deployment>.kb.<region>.cloud.es.io/app/apm`
- **Auth:** Self-host — none unless a secret token is configured. Cloud — `Authorization: Bearer <ELASTIC_APM_SECRET_TOKEN>` or `Authorization: ApiKey <ELASTIC_APM_API_KEY>` (the agent reads either from env vars).
- **Required env vars:** `ELASTIC_APM_SERVER_URL` (defaults to `http://localhost:8200`). Cloud also needs `ELASTIC_APM_SECRET_TOKEN` or `ELASTIC_APM_API_KEY`. Optional: `ELASTIC_APM_SERVICE_NAME`, `ELASTIC_APM_ENVIRONMENT`.
- **Install:** `pip install 'elastic-apm>=6.20'` + relevant `openinference-instrumentation-*` packages.

**Canonical setup (native agent — primary):**
```python
import os
import elasticapm
from openinference.instrumentation.langchain import LangChainInstrumentor

# 1. Native APM agent — picks up env vars and auto-instruments common frameworks.
elasticapm.Client(
    service_name=os.getenv("ELASTIC_APM_SERVICE_NAME", "my-agent-app"),
)
elasticapm.instrument()  # Flask / Django / FastAPI / asyncio / urllib3 / requests / ...

# 2. LLM instrumentor — emits OTel spans; the agent's OTel bridge ingests them.
LangChainInstrumentor().instrument()
```

**Alternative (pure OTLP — secondary):**
```python
import os
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

headers: dict[str, str] = {}
if token := os.getenv("ELASTIC_APM_SECRET_TOKEN"):
    headers["Authorization"] = f"Bearer {token}"
elif api_key := os.getenv("ELASTIC_APM_API_KEY"):
    headers["Authorization"] = f"ApiKey {api_key}"

server = os.getenv("ELASTIC_APM_SERVER_URL", "http://localhost:8200").rstrip("/")
exporter = OTLPSpanExporter(endpoint=f"{server}/v1/traces", headers=headers)

provider = TracerProvider(resource=Resource.create({"service.name": os.getenv("OTEL_SERVICE_NAME", "my-agent-app")}))
provider.add_span_processor(BatchSpanProcessor(exporter))
trace.set_tracer_provider(provider)
```

Use the OTLP path only when you have a strong reason to avoid the `elastic-apm` dependency — the native agent gives you transactions + auto-instrumented infra metrics for free, which is the main reason teams pick Elastic APM in the first place.

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

### Convention resolution

The convention emitted by generated code is fixed by the backend set chosen in `../SKILL.md` Step 3 — **no override**:

| Backend set | Convention | Reference doc |
|---|---|---|
| `{phoenix}` | **OI only** | `openinference.md` |
| Any non-empty subset of `{langfuse, signoz, elastic-apm}` (no Phoenix) | **OTel-GenAI only** | `otel_genai.md` |
| Any set containing Phoenix **and** at least one of `{langfuse, signoz, elastic-apm}` | **Both** | `openinference.md` + `otel_genai.md` |

Rationale: Phoenix is OpenInference-native; Langfuse, SigNoz, and Elastic APM consume OTel-GenAI (SigNoz / Elastic treat OI keys as opaque attributes — no LLM-specific UI affordances on those backends). Dual-emission is reserved for fan-out cases where both communities are present on the same provider.

### Per-kind summary (quick scan)

For complete attribute lists with types and flattening rules, read `openinference.md` (OI) and `otel_genai.md` (OTel-GenAI). The table below gives you the equivalents at a glance — pick the column that matches the resolved convention.

| Span kind | OI keys | OTel-GenAI keys |
|---|---|---|
| LLM | `openinference.span.kind="LLM"`, `llm.model_name`, `llm.provider`, `llm.invocation_parameters`, `llm.input_messages.<i>.message.*`, `llm.output_messages.<i>.message.*`, `llm.token_count.{prompt,completion,total,prompt_details.cache_read,prompt_details.cache_write}`, `llm.tools`, `llm.finish_reasons` | `gen_ai.operation.name="chat"`, `gen_ai.request.model`, `gen_ai.provider.name`, `gen_ai.request.{temperature,max_tokens,top_p,stop_sequences}`, `gen_ai.usage.{input_tokens,output_tokens,cache_creation.input_tokens,cache_read.input_tokens}`, `gen_ai.response.{model,finish_reasons,id}`, opt-in: `gen_ai.input.messages`, `gen_ai.output.messages` |
| TOOL | `openinference.span.kind="TOOL"`, `tool.name`, `tool.description`, `tool.parameters` | `gen_ai.operation.name="execute_tool"`, opt-in: `gen_ai.tool.definitions` |
| AGENT | `openinference.span.kind="AGENT"`, `agent.name`, `agent.role`, `agent.framework` | `gen_ai.operation.name="invoke_agent"`, `gen_ai.agent.{id,name,version,description}` |
| CHAIN | `openinference.span.kind="CHAIN"` | `gen_ai.operation.name="invoke_workflow"` |
| RETRIEVER | `openinference.span.kind="RETRIEVER"`, `retrieval.documents.<i>.document.{id,content,score,metadata}` | `gen_ai.operation.name="retrieval"`, `gen_ai.data_source.id`, opt-in: `gen_ai.retrieval.documents`, `gen_ai.retrieval.query.text` |

Generic `input.value` / `input.mime_type` / `output.value` / `output.mime_type` are OI-only and useful on every span kind for at-a-glance UI inspection. OTel-GenAI uses structured opt-in content attributes instead.

### Cross-cutting (Baggage)

`session.id`, `user.id`, `tenant.id`, `app.version` set once at the entry point and promoted to span attributes via `BaggageSpanProcessor`. These keys are convention-neutral.

### Cost computation

Token counts are captured but **dollar cost** is computed at ingestion time by the backends from a model→price table. Verify the model attribute (`llm.model_name` for OI, `gen_ai.request.model` for OTel-GenAI) is set to a name the backend recognizes — otherwise cost columns show `$0` in the UI. Self-hosted Langfuse and SigNoz allow custom model price configs.

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

Send the same spans to multiple backends simultaneously by attaching one `BatchSpanProcessor` per backend to a single `TracerProvider`:

```python
import os, base64
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

provider = TracerProvider(resource=Resource.create({"service.name": "fanout-app"}))

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

trace.set_tracer_provider(provider)

# Elastic APM — native agent. Picks up the same OTel spans via its bridge,
# no BatchSpanProcessor entry needed. Auto-instruments Flask/Django/FastAPI/etc.
import elasticapm
elasticapm.Client(service_name=os.getenv("ELASTIC_APM_SERVICE_NAME", "fanout-app"))
elasticapm.instrument()
```

Each processor / agent exports independently. If one backend is unreachable, the others still receive spans.

**Convention for fan-out:** when the backend set contains Phoenix **and** at least one of Langfuse / SigNoz / Elastic APM, the convention resolves to `both` (see § Mandatory Span Attributes) — every span must carry OI **and** OTel-GenAI keys so each backend's UI lights up. For Phoenix-less fan-out (e.g. `langfuse,signoz` or `signoz,elastic-apm`), `otel-genai` alone is sufficient.

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

All are installable from PyPI. They emit OpenInference attributes natively — Phoenix consumes them directly. For Langfuse / SigNoz exporters, the user-side code (the Custom path or wrapper code) must additionally emit OTel-GenAI keys per the resolution rule (`openinference.md` and `otel_genai.md`).

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
- **Elastic APM:** if your deployment uses an API key, set `ELASTIC_APM_API_KEY` (the agent sends `Authorization: ApiKey ...`); if it uses a secret token, set `ELASTIC_APM_SECRET_TOKEN` (the agent sends `Authorization: Bearer ...`). Don't set both. `ELASTIC_APM_SERVER_URL` should NOT have a trailing slash.

### "Elastic APM agent silent / no transactions in Kibana"

- The native agent only flushes on shutdown by default. Make sure your app calls `client.close()` or relies on `atexit`.
- Confirm the APM Server URL is reachable: `curl $ELASTIC_APM_SERVER_URL` should return a small JSON manifest, not 404.
- If you're using the OTLP path instead of the native agent, the endpoint is `<server>/v1/traces` (not `/intake/v2/events`).

### "OpenAI Agents SDK shows raw HTTP calls instead of agent spans"

You're using `openinference-instrumentation-openai`. Switch to `openinference-instrumentation-openai-agents` and register via `set_trace_processors()`.
