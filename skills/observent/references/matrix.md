# observent Reference

Complete reference for frameworks, backends, integration mechanics, span attributes, and context propagation. `../SKILL.md` references this document during code generation.

---

## Maintainer's sources

Re-verify each section against the upstream artifacts listed under it (per-subsection `**Sources:**` lines) or via the consolidated list below. Bump the per-section `Last verified` date when you re-check.

**Specs & SDK:**
- OpenInference semantic conventions — https://github.com/Arize-ai/openinference/blob/main/spec/semantic_conventions.md
- OTel semantic conventions (GenAI) — https://github.com/open-telemetry/semantic-conventions/tree/main/docs/gen-ai
- OTel Python SDK & instrumentation — https://opentelemetry.io/docs/languages/python/
- W3C Trace Context (Level 1) — https://www.w3.org/TR/trace-context/
- OTel baggage API — https://opentelemetry.io/docs/specs/otel/baggage/api/

**Backends:**
- Arize Phoenix — https://docs.arize.com/phoenix
- Langfuse — https://langfuse.com/docs
- SigNoz — https://signoz.io/docs
- Elastic APM Python agent — https://www.elastic.co/guide/en/apm/agent/python/current/index.html
- LangSmith — https://docs.smith.langchain.com

**Frameworks (also linked in per-framework subsections):**
- LangGraph — https://langchain-ai.github.io/langgraph/
- CrewAI — https://docs.crewai.com
- Microsoft Agent Framework — https://github.com/microsoft/agent-framework
- Anthropic Agents — https://docs.anthropic.com/en/docs/agents
- OpenAI Agents SDK — https://openai.github.io/openai-agents-python/
- smolagents — https://huggingface.co/docs/smolagents
- LlamaIndex — https://docs.llamaindex.ai

**OpenInference instrumentors (PyPI):**
- https://github.com/Arize-ai/openinference/tree/main/python — canonical Python monorepo; each per-instrumentor README has install + usage.

Last reviewed: 2026-05-17.

---

## 8 × 5 Compatibility Matrix

| Framework | Arize Phoenix<br>*OI* | Langfuse<br>*OTel-GenAI* | SigNoz<br>*OTel-GenAI* | Elastic APM<br>*OTel-GenAI* | LangSmith<br>*OTel-GenAI* |
|---|---|---|---|---|---|
| LangGraph | OI: `LangChainInstrumentor` | LangChain callback (`langfuse.langchain.CallbackHandler`) | OTLP + OI: `LangChainInstrumentor` | Native agent + OI: `LangChainInstrumentor` | OTLP + OI: `LangChainInstrumentor` |
| CrewAI | OI: `CrewAIInstrumentor` (+ LangChain) | LangChain callback (CrewAI inherits) | OTLP + OI: `CrewAIInstrumentor` | Native agent + OI: `CrewAIInstrumentor` | OTLP + OI: `CrewAIInstrumentor` |
| Microsoft Agent Framework | OI: `OpenAIInstrumentor` + MAF native OTel | OTLP exporter + MAF native OTel + `OpenAIInstrumentor` | OTLP + MAF native OTel + `OpenAIInstrumentor` | Native agent + MAF native OTel + `OpenAIInstrumentor` | OTLP + MAF native OTel + `OpenAIInstrumentor` |
| Anthropic Agents SDK | OI: `AnthropicInstrumentor` | `langfuse` decorator `@observe` (or `OpenAIInstrumentor`-style for Anthropic) | OTLP + OI: `AnthropicInstrumentor` | Native agent + OI: `AnthropicInstrumentor` | OTLP + OI: `AnthropicInstrumentor` |
| OpenAI Agents SDK | **Native trace processor** (`phoenix.otel.OpenAIAgentsTracingProcessor`) | **Native trace processor** (Langfuse OpenAIAgents processor) | **Native trace processor** with OTLP backend | Native APM agent + OpenAI Agents SDK trace processor (OTel bridge) | **Native trace processor** with OTLP backend |
| smolagents | OI: `SmolagentsInstrumentor` | OI: `SmolagentsInstrumentor` (exporter sends to Langfuse OTLP) | OTLP + OI: `SmolagentsInstrumentor` | Native agent + OI: `SmolagentsInstrumentor` | OTLP + OI: `SmolagentsInstrumentor` |
| LlamaIndex | OI: `LlamaIndexInstrumentor` | `langfuse.llama_index` callback | OTLP + OI: `LlamaIndexInstrumentor` | Native agent + OI: `LlamaIndexInstrumentor` | OTLP + OI: `LlamaIndexInstrumentor` |
| Custom | Manual spans + helper functions | Manual spans + `langfuse` decorator | Manual spans + OTLP exporter | Manual spans + `elasticapm.Client` (OTel bridge) | Manual spans + OTLP exporter |

**Reading the matrix:** the italic label under each backend's header (e.g. *OI*, *OTel-GenAI*) is the **semantic convention** that backend prefers — Phoenix is OpenInference-native; the other four are OTel-GenAI-native. The convention observent emits at generation time is derived mechanically from the backend set you pick (see SKILL.md § Step 3): single Phoenix → OI only; any Phoenix-less subset → OTel-GenAI only; Phoenix + any other → both.

**OI** = OpenInference instrumentor (`openinference-instrumentation-*`). The OI instrumentor itself emits raw OTel spans regardless of which backend you target — only the exporter destination and the *attribute keys* the backend reads differ. For Elastic APM, the OI instrumentor still emits OTel spans; the `elasticapm.Client` agent picks them up via its OTel bridge (no separate exporter needed) and ingests them alongside auto-instrumented transaction spans.

**Sources:** matrix entries are derived from the per-framework and per-backend reference subsections below — re-verify there when bumping a row or column.

---

## Verified Versions

Last verified: 2026-05-17 against Python 3.12.

| Package | Pinned version |
|---|---|
| arize-phoenix | ==15.10.0 |
| langfuse | ==4.6.1 |
| elastic-apm | ==6.25.0 |
| langsmith | ==0.8.5 |
| opentelemetry-sdk | ==1.41.1 |
| opentelemetry-exporter-otlp-proto-http | ==1.41.1 |
| langgraph | ==1.2.0 |
| crewai | ==1.14.4 |
| agent-framework | ==1.4.0 |
| anthropic | ==0.102.0 |
| openai-agents | ==0.17.2 |
| smolagents | ==1.25.0 |
| llama-index | ==0.14.22 |
| openinference-instrumentation-langchain | ==0.1.65 |
| openinference-instrumentation-crewai | ==1.1.6 |
| openinference-instrumentation-openai | ==0.1.48 |
| openinference-instrumentation-openai-agents | ==1.5.0 |
| openinference-instrumentation-anthropic | ==1.0.4 |
| openinference-instrumentation-llama-index | ==4.4.1 |
| openinference-instrumentation-smolagents | ==0.1.30 |

These are the exact versions `examples.md` and the per-framework install commands below target. When bumping any pin, update this table **and** the matching per-backend Install line, the per-framework `pip install` snippet, and the `*Last verified: …*` footer of any example in `examples.md` that was re-run.

**Sources:** each row's PyPI page at `https://pypi.org/project/<package-name>/` — pins are the exact version the most recent re-verification pass installed.

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
- **Install:** `pip install 'arize-phoenix==15.10.0' 'opentelemetry-sdk==1.41.1' 'opentelemetry-exporter-otlp-proto-http==1.41.1'`
- **Sources:** Phoenix docs — https://docs.arize.com/phoenix · `phoenix.otel.register` — https://docs.arize.com/phoenix/tracing/how-to-tracing/setup-tracing/setup-tracing-python · OpenInference instrumentors — https://github.com/Arize-ai/openinference/tree/main/python

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
- **Install:** `pip install 'langfuse==4.6.1'` (plus framework-specific extras as listed below).
- **Sources:** Langfuse docs — https://langfuse.com/docs · OTel integration — https://langfuse.com/docs/opentelemetry/get-started · LangChain integration — https://langfuse.com/docs/integrations/langchain · `@observe` decorator — https://langfuse.com/docs/sdk/python/decorators

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
- **Install:** `pip install 'opentelemetry-sdk==1.41.1' 'opentelemetry-exporter-otlp-proto-http==1.41.1'` + relevant `openinference-instrumentation-*` packages.
- **Sources:** SigNoz docs — https://signoz.io/docs · OTel Python instrumentation guide — https://signoz.io/docs/instrumentation/opentelemetry-python/ · Cloud ingestion-key header — https://signoz.io/docs/ingestion/signoz-cloud/keys/

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
- **Install:** `pip install 'elastic-apm==6.25.0'` + relevant `openinference-instrumentation-*` packages.
- **Sources:** Elastic APM Python agent — https://www.elastic.co/guide/en/apm/agent/python/current/index.html · OTel bridge — https://www.elastic.co/guide/en/apm/agent/python/current/opentelemetry-bridge.html · APM Server OTLP intake — https://www.elastic.co/guide/en/observability/current/apm-open-telemetry-direct.html

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

### LangSmith

- **Type:** Commercial. Cloud-first (US `https://api.smith.langchain.com`, EU `https://eu.api.smith.langchain.com`). Enterprise self-host is offered for paid tiers — point `LANGSMITH_ENDPOINT` at it.
- **Integration mechanism:** **Pure OTLP HTTP** to LangSmith's OTel ingest endpoint. LangSmith maps OTel-GenAI semantic conventions to its native trace schema, so the same `OTLPSpanExporter` + OpenInference framework instrumentor stack used for SigNoz works unchanged. No `langsmith` SDK code is generated — keeping LangSmith mechanically identical to SigNoz means it composes cleanly into the multi-backend fan-out template.
- **Endpoints:**
  - Cloud US OTLP: `https://api.smith.langchain.com/otel/v1/traces`
  - Cloud EU OTLP: `https://eu.api.smith.langchain.com/otel/v1/traces`
  - Self-host OTLP: `${LANGSMITH_ENDPOINT}/otel/v1/traces`
  - Cloud UI: `https://smith.langchain.com` (US), `https://eu.smith.langchain.com` (EU)
- **Auth:** Header `x-api-key: ${LANGSMITH_API_KEY}`. Project routing via optional header `Langsmith-Project: ${LANGSMITH_PROJECT}` (otherwise traces land in the `default` project).
- **Required env vars:** `LANGSMITH_API_KEY`. Optional: `LANGSMITH_ENDPOINT` (default `https://api.smith.langchain.com`), `LANGSMITH_PROJECT`.
- **Install:** Relevant `openinference-instrumentation-*` packages plus `opentelemetry-exporter-otlp-proto-http==1.41.1`. The `langsmith` PyPI package is **not** required for the OTLP path observent generates — install it only if you also want to use the `langsmith` SDK directly (datasets, evals).
- **Sources:** LangSmith docs — https://docs.smith.langchain.com · OTel ingest endpoint — https://docs.smith.langchain.com/observability/how_to_guides/trace_with_opentelemetry · LangSmith regions & endpoints — https://docs.smith.langchain.com/administration/concepts#data-regions

**Canonical setup (pure OTLP):**
```python
import os
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from openinference.instrumentation.langchain import LangChainInstrumentor

base = os.getenv("LANGSMITH_ENDPOINT", "https://api.smith.langchain.com").rstrip("/")
headers = {"x-api-key": os.environ["LANGSMITH_API_KEY"]}
if project := os.getenv("LANGSMITH_PROJECT"):
    headers["Langsmith-Project"] = project

exporter = OTLPSpanExporter(endpoint=f"{base}/otel/v1/traces", headers=headers)
provider = TracerProvider(resource=Resource.create({"service.name": os.getenv("OTEL_SERVICE_NAME", "my-agent-app")}))
provider.add_span_processor(BatchSpanProcessor(exporter))
trace.set_tracer_provider(provider)

LangChainInstrumentor().instrument(tracer_provider=provider)
```

LangSmith is cloud-first and has no localhost default — `LANGSMITH_API_KEY` must be set or the exporter will receive 401s.

---

## Per-Framework Reference

### LangGraph (`langgraph`)

- **Tracing model:** LangChain callback system + standard OTel via `LangChainInstrumentor`.
- **Key entry points:** `StateGraph.compile()` → `.invoke()`, `.stream()`, `.astream()`.
- **Where to thread `session_id`:** `RunnableConfig.configurable["session_id"]` and as OTel baggage.
- **Phoenix / SigNoz:** `pip install 'openinference-instrumentation-langchain==0.1.65'` then call `LangChainInstrumentor().instrument(tracer_provider=provider)`.
- **Langfuse:** `langfuse.langchain.CallbackHandler` passed via `config={"callbacks": [handler]}`.
- **Sources:** LangGraph docs — https://langchain-ai.github.io/langgraph/ · `openinference-instrumentation-langchain` — https://github.com/Arize-ai/openinference/tree/main/python/instrumentation/openinference-instrumentation-langchain · Langfuse LangChain callback — https://langfuse.com/docs/integrations/langchain

### CrewAI (`crewai`)

- **Tracing model:** Native CrewAI events + LangChain callbacks for the underlying LLM calls.
- **Key entry points:** `Crew.kickoff()`, `Agent`, `Task` (delegations create child spans).
- **Where to thread `session_id`:** Pass via `inputs` dict and set OTel baggage at the top.
- **Phoenix / SigNoz:** `pip install 'openinference-instrumentation-crewai==1.1.6' 'openinference-instrumentation-langchain==0.1.65'` — captures Crew → Agent → Task → LLM hierarchy.
- **Langfuse:** Use `langfuse.langchain.CallbackHandler` — CrewAI's LLM wrapper inherits LangChain callbacks.
- **Sources:** CrewAI docs — https://docs.crewai.com · `openinference-instrumentation-crewai` — https://github.com/Arize-ai/openinference/tree/main/python/instrumentation/openinference-instrumentation-crewai · `openinference-instrumentation-langchain` (underlying LLM calls) — https://github.com/Arize-ai/openinference/tree/main/python/instrumentation/openinference-instrumentation-langchain

### Microsoft Agent Framework (`agent-framework`)

- **Tracing model:** Native OpenTelemetry emission built into `agent-framework`. The framework's spans land on the global `TracerProvider` automatically — just register the provider before constructing any `Agent`. Underlying model calls captured by `OpenAIInstrumentor` (or `AnthropicInstrumentor` for Anthropic-backed agents).
- **Key entry points:** `Agent.run()`, `agent_framework.openai.OpenAIChatClient`, the workflow primitives (sequential, concurrent, handoff, group collaboration) under `agent_framework.workflows`.
- **Where to thread `session_id`:** OTel baggage at the top — MAF's native context propagation carries it across agents and tool calls.
- **Phoenix / SigNoz / Langfuse / LangSmith via OTLP:** `pip install 'agent-framework==1.4.0' 'openinference-instrumentation-openai==0.1.48'` — MAF emits OTel-GenAI spans natively; the OI instrumentor adds raw model spans.
- **Note:** observent no longer supports AutoGen (v0.2 `pyautogen` or v0.4 `autogen-agentchat`) — Microsoft has unified AutoGen and Semantic Kernel into agent-framework. Migrate AutoGen code to MAF, or use the **Custom** path.
- **Sources:** Microsoft Agent Framework — https://github.com/microsoft/agent-framework · MAF observability guidance — search "Observability" / "OpenTelemetry" in the repo README · `openinference-instrumentation-openai` (raw model spans) — https://github.com/Arize-ai/openinference/tree/main/python/instrumentation/openinference-instrumentation-openai

### Anthropic Agents SDK (`anthropic`)

- **Tracing model:** Wrap entry points with the OpenInference Anthropic instrumentor or with Langfuse `@observe` decorators.
- **Key entry points:** `client.messages.create()`, `client.beta.messages.create()`, agent tool-call loops.
- **Where to thread `session_id`:** Set OTel baggage at the top of each conversation turn.
- **Phoenix / SigNoz:** `pip install 'openinference-instrumentation-anthropic==1.0.4'` — captures `prompt_token_count`, `completion_token_count`, **prompt cache read/write tokens**, tool calls.
- **Langfuse:** `@observe(as_type="generation")` and update via `langfuse_context.update_current_observation(usage={...})`.
- **Sources:** Anthropic agents docs — https://docs.anthropic.com/en/docs/agents · `openinference-instrumentation-anthropic` — https://github.com/Arize-ai/openinference/tree/main/python/instrumentation/openinference-instrumentation-anthropic · Anthropic prompt caching — https://docs.anthropic.com/en/docs/build-with-claude/prompt-caching

### OpenAI Agents SDK (`openai-agents`)

- **Tracing model:** **Native** — the SDK has its own tracing pipeline configurable via `set_trace_processors()`. This captures handoffs, guardrails, and agent runs as first-class spans, not as raw OpenAI API calls.
- **Key entry points:** `Runner.run()`, `Agent`, `handoff()`, `Guardrail`.
- **Where to thread `session_id`:** Pass via `Runner.run(... metadata={"session.id": ...})`; use OTel baggage as fallback.
- **Phoenix:** `pip install 'openinference-instrumentation-openai-agents==1.5.0'` then:
  ```python
  from openinference.instrumentation.openai_agents import OpenAIAgentsInstrumentor
  OpenAIAgentsInstrumentor().instrument(tracer_provider=provider)
  ```
- **Langfuse:** Use Langfuse's openai-agents processor (consult Langfuse docs for the current package name) registered via `set_trace_processors([...])`.
- **SigNoz:** Use the same OpenInference instrumentor; the OTLP exporter delivers spans to SigNoz.
- **Do NOT** use plain `openinference-instrumentation-openai` for the Agents SDK — it captures only the underlying HTTP calls and loses agent structure (handoffs, runs, guardrails).
- **Sources:** OpenAI Agents Python — https://openai.github.io/openai-agents-python/ · `set_trace_processors` API — https://openai.github.io/openai-agents-python/tracing/ · `openinference-instrumentation-openai-agents` — https://github.com/Arize-ai/openinference/tree/main/python/instrumentation/openinference-instrumentation-openai-agents

### smolagents (`smolagents`)

- **Tracing model:** `openinference-instrumentation-smolagents` covers `CodeAgent.run()`, `ToolCallingAgent.run()`, tool calls, LLM calls.
- **Phoenix / SigNoz / Langfuse:** Same instrumentor — only the exporter destination changes.
- **Install:** `pip install 'openinference-instrumentation-smolagents==0.1.30'`
- **Sources:** smolagents docs — https://huggingface.co/docs/smolagents · `openinference-instrumentation-smolagents` — https://github.com/Arize-ai/openinference/tree/main/python/instrumentation/openinference-instrumentation-smolagents

### LlamaIndex (`llama_index`)

- **Tracing model:** `openinference-instrumentation-llama-index` (preferred) or LlamaIndex's `set_global_handler()` API.
- **Key entry points:** `Workflow.run()`, `QueryEngine.query()`, `RetrieverQueryEngine.query()`, `AgentWorker.run_step()`.
- **Phoenix / SigNoz:** `pip install 'openinference-instrumentation-llama-index==4.4.1'`
- **Langfuse:** `from langfuse.llama_index import LlamaIndexCallbackHandler` then `Settings.callback_manager = CallbackManager([handler])`.
- **Sources:** LlamaIndex docs — https://docs.llamaindex.ai · `openinference-instrumentation-llama-index` — https://github.com/Arize-ai/openinference/tree/main/python/instrumentation/openinference-instrumentation-llama-index · Langfuse LlamaIndex integration — https://langfuse.com/docs/integrations/llama-index

### Custom (no framework)

- **Tracing model:** Manual OTel spans. The skill writes an `observent_otel.py` helper module into the user's project with typed setters: `set_llm_attrs(span, model, input_messages, output_messages, prompt_tokens, completion_tokens, ...)`, `set_tool_attrs(span, name, parameters, input_value, output_value)`, `set_agent_attrs(span, name, role)`.
- **Pattern:** wrap each agent step in `tracer.start_as_current_span("agent.step", attributes={"openinference.span.kind": "AGENT", ...})`.
- **Sources:** OTel Python SDK — https://opentelemetry.io/docs/languages/python/ · OpenInference span kinds — https://github.com/Arize-ai/openinference/blob/main/spec/semantic_conventions.md · OTel-GenAI operation names — https://github.com/open-telemetry/semantic-conventions/blob/main/docs/gen-ai/gen-ai-spans.md

---

## Mandatory Span Attributes

### Convention resolution

The convention emitted by generated code is fixed by the backend set chosen in `../SKILL.md` Step 3 — **no override**:

| Backend set | Convention | Reference doc |
|---|---|---|
| `{phoenix}` | **OI only** | `openinference.md` |
| Any non-empty subset of `{langfuse, signoz, elastic-apm, langsmith}` (no Phoenix) | **OTel-GenAI only** | `otel_genai.md` |
| Any set containing Phoenix **and** at least one of `{langfuse, signoz, elastic-apm, langsmith}` | **Both** | `openinference.md` + `otel_genai.md` |

Rationale: Phoenix is OpenInference-native; Langfuse, SigNoz, Elastic APM, and LangSmith consume OTel-GenAI (SigNoz / Elastic / LangSmith treat OI keys as opaque attributes — no LLM-specific UI affordances on those backends). Dual-emission is reserved for fan-out cases where both communities are present on the same provider.

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

**Sources:** OI keys → `openinference.md` (canonical) + https://github.com/Arize-ai/openinference/blob/main/spec/semantic_conventions.md · OTel-GenAI keys → `otel_genai.md` (canonical) + https://github.com/open-telemetry/semantic-conventions/tree/main/docs/gen-ai

**LLM token-tracking gotcha (OpenAI Chat Completions vs Responses).** The two OpenAI text endpoints return usage under different field names — Chat Completions: `usage.{prompt_tokens, completion_tokens, total_tokens}`; Responses API: `usage.{input_tokens, output_tokens, total_tokens}`. The OpenInference instrumentor normalizes both into the OI / OTel-GenAI keys above, but only on versions that support the Responses API — check the changelog if a single agent mixes both endpoints. **Streaming + Chat Completions** silently omits usage unless the request passes `stream_options={"include_usage": True}`; the Responses API includes usage automatically. Without the opt-in, `llm.token_count.*` / `gen_ai.usage.*` will be missing on streaming spans. See `openinference.md` § Token counts and `otel_genai.md` § Token usage for the field-name mapping table.

### Cross-cutting (Baggage)

`session.id`, `user.id`, `tenant.id`, `app.version` set once at the entry point and promoted to span attributes via `BaggageSpanProcessor`. These keys are convention-neutral.

### Cost computation

Token counts are captured but **dollar cost** is computed at ingestion time by the backends from a model→price table. Verify the model attribute (`llm.model_name` for OI, `gen_ai.request.model` for OTel-GenAI) is set to a name the backend recognizes — otherwise cost columns show `$0` in the UI. Self-hosted Langfuse and SigNoz allow custom model price configs.

---

## Context Propagation

Multi-agent traces only work if context flows correctly across every boundary.

**Standard.** All wire-level context propagation in observent uses OTel SDK defaults, which implement **W3C Trace Context Level 1** (`traceparent` + `tracestate` per https://www.w3.org/TR/trace-context/) plus W3C Baggage (`baggage` header). The OI / OTel-GenAI semantic conventions govern *span attributes*; W3C TC governs the *cross-process context wire format* — the two are orthogonal. **Never call `set_global_textmap()`** with a non-W3C propagator (legacy B3, Jaeger `uber-trace-id`, etc.) — observent's exporters and all 5 backends assume W3C `traceparent` / `tracestate` on the wire. If interop with a B3-only service is required, use `CompositePropagator([TraceContextTextMapPropagator(), B3Format(), W3CBaggagePropagator()])` so W3C remains primary.

**Sources:** W3C Trace Context — https://www.w3.org/TR/trace-context/ · OTel context API (Python) — https://opentelemetry.io/docs/languages/python/instrumentation/#context-propagation · `BaggageSpanProcessor` (PyPI `opentelemetry-processor-baggage`) — https://github.com/open-telemetry/opentelemetry-python-contrib/tree/main/processor/opentelemetry-processor-baggage · AI-boundary input/output capture (transport-agnostic) — see `capture.md`

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
inject(env)  # adds traceparent + tracestate (W3C TC §3.2 / §3.3)
subprocess.run([...], env=env)
```

The child process loads it via `from opentelemetry.propagate import extract; extract(os.environ)`.

**Windows note.** Env-var keys are case-insensitive at the Win32 layer but case-sensitive in Python's `os.environ` dict. If the parent inherited `TRACEPARENT` (uppercase) from an upstream caller, `os.environ.copy() + inject(env)` will leave both `TRACEPARENT` and `traceparent` in the dict; on Win32 the OS collapses them and the surviving casing is implementation-defined. To avoid silent loss, normalize before spawning — `env.pop("TRACEPARENT", None); env.pop("TRACESTATE", None)` before `inject(env)`. The W3C HTTP binding (§3) is case-insensitive for headers; that does **not** extend to OS env vars.

### Cross-service / cross-agent network calls

Install `opentelemetry-instrumentation-httpx` and `opentelemetry-instrumentation-requests`. Initialize once:

```python
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor

HTTPXClientInstrumentor().instrument()
RequestsInstrumentor().instrument()
```

Outgoing HTTP requests will carry W3C `traceparent` (TC §3.2) and `tracestate` (TC §3.3) headers automatically, so a downstream agent service can resume the trace. **Do not strip `tracestate`** in any custom outbound wrapper — downstream vendors (LangSmith, Elastic, SigNoz) may add list-member entries to it for vendor-specific routing per W3C TC §3.3.1.3.

**Sampling-flag note.** When an upstream caller sends `traceparent` with the `sampled` bit (TC §3.2.2.5) cleared, OTel's default `ParentBased(ALWAYS_ON)` sampler propagates the bit unchanged downstream. If you replace the global sampler, keep it parent-aware so cross-service trace integrity holds.

### AI-boundary input/output capture (any transport)

observent captures the input/output that crosses the **AI-system boundary** — the prompt, request state, run config, and result — as `input.*` / `output.*` attributes on the agent run's existing root span, and sets the run's status (OK / ERROR). This is **transport-agnostic**: it works identically whether the agent is triggered by HTTP, a CLI, a queue worker, or a script, because it enriches whatever span is already recording (the framework instrumentor's root, or the HTTP server span) rather than opening its own. Sensitive keys are redacted at the value level; a baggage whitelist promotes correlation keys onto child spans.

When the raw HTTP wire payload is *also* needed (a header or envelope field the agent never receives as an argument), an **optional** ASGI adapter enriches the existing server span with `http.request.*` / `http.response.*` — it adds no span and does not buffer streaming responses. See **`references/capture.md`** for the canonical engine, the per-framework wrap points, the redaction key list, and the optional HTTP adapter.

### Agent handoffs

- **OpenAI Agents SDK** — handoffs are first-class trace events when using `set_trace_processors()`. No manual work.
- **Microsoft Agent Framework** — MAF's native OTel integration captures workflow-level agent handoffs and tool dispatch as first-class spans. Register a global `TracerProvider` before any `Agent(...)` construction; the framework attaches to it automatically.
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

**Sources:** `BatchSpanProcessor` configuration — https://opentelemetry.io/docs/languages/python/instrumentation/#configure-the-exporters · per-backend endpoint and auth details — see § Per-Backend Reference above.

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

# Elastic APM — native agent. Picks up the same OTel spans via its bridge,
# no BatchSpanProcessor entry needed. Auto-instruments Flask/Django/FastAPI/etc.
import elasticapm
elasticapm.Client(service_name=os.getenv("ELASTIC_APM_SERVICE_NAME", "fanout-app"))
elasticapm.instrument()
```

Each processor / agent exports independently. If one backend is unreachable, the others still receive spans.

**Convention for fan-out:** when the backend set contains Phoenix **and** at least one of Langfuse / SigNoz / Elastic APM / LangSmith, the convention resolves to `both` (see § Mandatory Span Attributes) — every span must carry OI **and** OTel-GenAI keys so each backend's UI lights up. For Phoenix-less fan-out (e.g. `langfuse,signoz` or `signoz,elastic-apm` or `langsmith,signoz`), `otel-genai` alone is sufficient.

---

## OpenInference Instrumentor Map

| Package | Covers |
|---|---|
| `openinference-instrumentation-langchain` | LangGraph, LangChain, CrewAI underlying LLM calls |
| `openinference-instrumentation-crewai` | CrewAI Crew/Agent/Task structure |
| `openinference-instrumentation-openai` | OpenAI SDK, Microsoft Agent Framework (model client) |
| `openinference-instrumentation-openai-agents` | OpenAI Agents SDK (use this — not plain `-openai`) |
| `openinference-instrumentation-anthropic` | Anthropic SDK incl. prompt caching tokens |
| `openinference-instrumentation-llama-index` | LlamaIndex Workflows, QueryEngines, Retrievers |
| `openinference-instrumentation-smolagents` | smolagents CodeAgent/ToolCallingAgent |
| `openinference-instrumentation-bedrock` | AWS Bedrock |
| `openinference-instrumentation-vertexai` | Google Vertex AI |

All are installable from PyPI. They emit OpenInference attributes natively — Phoenix consumes them directly. For Langfuse / SigNoz / Elastic APM / LangSmith exporters, the user-side code (the Custom path or wrapper code) must additionally emit OTel-GenAI keys per the resolution rule (`openinference.md` and `otel_genai.md`).

**Sources:** OpenInference Python monorepo (canonical) — https://github.com/Arize-ai/openinference/tree/main/python · per-package PyPI pages at `https://pypi.org/project/openinference-instrumentation-<framework>/`.

---

## Troubleshooting

**Sources:** symptoms catalogued here come from observent's own field experience — verify against each backend's official troubleshooting docs (linked in § Per-Backend Reference above) before changing this list.

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
