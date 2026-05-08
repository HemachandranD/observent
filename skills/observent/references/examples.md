# observent Examples

Eight runnable end-to-end examples — one per supported framework, with the three backends rotated to demonstrate all of them. Plus a multi-backend fan-out, a verification checklist, and troubleshooting.

> **Convention notes.** Phoenix-targeted examples (1, 5, 8) emit OpenInference keys — Phoenix's UI is OI-native. Langfuse / SigNoz examples (2, 3, 4, 6, 7) inherit OI keys from the relevant `openinference-instrumentation-*` package and exporters carry them on the OTLP wire; both backends ingest the spans, but for richer convention-aware UI on those backends you can supplement with OTel-GenAI keys (`gen_ai.*` — see `otel_genai.md`) or use the Custom path (the helper bakes in the convention literal at generation time — see Example 8). The Multi-Backend Fan-Out example at the bottom emits both conventions because the resolved set requires it.

---

## 1. LangGraph + Arize Phoenix (local, zero account)

```python
# main.py
import os
from phoenix.otel import register
from openinference.instrumentation.langchain import LangChainInstrumentor
from langchain_anthropic import ChatAnthropic
from langgraph.prebuilt import create_react_agent

# --- Observability: Phoenix local ---
tracer_provider = register(
    project_name=os.getenv("PHOENIX_PROJECT_NAME", "langgraph-demo"),
    endpoint=os.getenv("PHOENIX_COLLECTOR_ENDPOINT", "http://localhost:6006/v1/traces"),
)
LangChainInstrumentor().instrument(tracer_provider=tracer_provider)

# --- Agent ---
llm = ChatAnthropic(model="claude-sonnet-4-6")

def get_weather(city: str) -> str:
    """Get weather for a city."""
    return f"It's 72°F and sunny in {city}."

agent = create_react_agent(llm, tools=[get_weather])

if __name__ == "__main__":
    result = agent.invoke(
        {"messages": [{"role": "user", "content": "What's the weather in Tokyo?"}]},
        config={"configurable": {"session_id": "demo-session-001"}},
    )
    print(result["messages"][-1].content)
    # Open http://localhost:6006 to see the trace
```

```bash
# 1. Start Phoenix UI in another terminal:
python -m phoenix.server.main serve   # or `pip install arize-phoenix && phoenix serve`

# 2. Install dependencies:
pip install 'arize-phoenix>=5.0' 'openinference-instrumentation-langchain>=0.1' \
            'langgraph>=0.2' 'langchain-anthropic>=0.2'

# 3. Set ANTHROPIC_API_KEY and run:
export ANTHROPIC_API_KEY=sk-ant-...
python main.py
```

*Last verified: 2026-05-08 with Python 3.12.*

---

## 2. CrewAI + Langfuse (callback, cost tracking)

```python
# crew_main.py
import os
from langfuse.langchain import CallbackHandler
from crewai import Agent, Task, Crew, Process
from langchain_openai import ChatOpenAI

# --- Observability: Langfuse via LangChain callback ---
langfuse_handler = CallbackHandler()  # reads LANGFUSE_PUBLIC_KEY/SECRET_KEY/HOST from env

llm = ChatOpenAI(model="gpt-4o", callbacks=[langfuse_handler])

researcher = Agent(
    role="Senior Research Analyst",
    goal="Find accurate, source-backed information",
    backstory="You are a meticulous researcher.",
    llm=llm, verbose=True,
)
writer = Agent(
    role="Technical Writer",
    goal="Turn research into clear summaries",
    backstory="You write for a developer audience.",
    llm=llm, verbose=True,
)

research = Task(
    description="Research the latest developments in {topic}",
    expected_output="A structured summary with sources",
    agent=researcher,
)
write = Task(
    description="Write a 3-paragraph summary based on the research",
    expected_output="A polished 3-paragraph summary",
    agent=writer,
)

crew = Crew(
    agents=[researcher, writer],
    tasks=[research, write],
    process=Process.sequential,
    verbose=True,
)

if __name__ == "__main__":
    result = crew.kickoff(inputs={"topic": "multi-agent observability"})
    print(result)
    # langfuse_handler flushes automatically; or:
    from langfuse import get_client
    get_client().flush()
```

```bash
pip install 'crewai>=0.80' 'langfuse>=3.0' 'langchain-openai>=0.2'
export LANGFUSE_PUBLIC_KEY=pk-lf-... LANGFUSE_SECRET_KEY=sk-lf-...
export LANGFUSE_HOST=https://cloud.langfuse.com  # or http://localhost:3000 for self-host
export OPENAI_API_KEY=sk-...
python crew_main.py
# Visit https://cloud.langfuse.com to see Crew → Agent → Task → LLM hierarchy
```

*Last verified: 2026-05-08 with Python 3.12.*

---

## 3. AutoGen v0.4 + SigNoz (OTLP, session_id propagation)

```python
# autogen_signoz.py
import asyncio
import os
from opentelemetry import baggage, context, trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from openinference.instrumentation.openai import OpenAIInstrumentor

from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.teams import RoundRobinGroupChat
from autogen_agentchat.conditions import MaxMessageTermination
from autogen_ext.models.openai import OpenAIChatCompletionClient

# --- Observability: SigNoz via OTLP ---
headers = {}
if key := os.getenv("SIGNOZ_INGESTION_KEY"):
    headers["signoz-access-token"] = key

provider = TracerProvider(
    resource=Resource.create({"service.name": os.getenv("OTEL_SERVICE_NAME", "autogen-demo")}),
)
provider.add_span_processor(
    BatchSpanProcessor(
        OTLPSpanExporter(
            endpoint=os.getenv("SIGNOZ_ENDPOINT", "http://localhost:4318/v1/traces"),
            headers=headers,
        )
    )
)
trace.set_tracer_provider(provider)
OpenAIInstrumentor().instrument(tracer_provider=provider)

# --- Agents ---
async def main(session_id: str):
    # Set session.id baggage so it propagates across all child spans
    ctx = baggage.set_baggage("session.id", session_id)
    ctx = baggage.set_baggage("user.id", "user-42", context=ctx)
    token = context.attach(ctx)
    try:
        model_client = OpenAIChatCompletionClient(model="gpt-4o")
        assistant = AssistantAgent("assistant", model_client=model_client,
                                   system_message="You are a concise expert.")
        critic = AssistantAgent("critic", model_client=model_client,
                                system_message="Critique the assistant's answer in 1 sentence.")
        team = RoundRobinGroupChat([assistant, critic],
                                   termination_condition=MaxMessageTermination(4))
        result = await team.run(task="Explain how LLM caching works.")
        print(result.messages[-1].content)
    finally:
        context.detach(token)
        provider.shutdown()

if __name__ == "__main__":
    asyncio.run(main(session_id="demo-session-002"))
```

```bash
# Start SigNoz self-host first:
git clone https://github.com/SigNoz/signoz.git && cd signoz/deploy
docker compose -f docker/clickhouse-setup/docker-compose.yaml up -d

pip install 'autogen-agentchat>=0.4' 'autogen-ext[openai]' \
            'opentelemetry-sdk>=1.25' 'opentelemetry-exporter-otlp-proto-http>=1.25' \
            'openinference-instrumentation-openai>=0.1'
export OPENAI_API_KEY=sk-... SIGNOZ_ENDPOINT=http://localhost:4318/v1/traces
python autogen_signoz.py
# UI: http://localhost:3301
```

*Last verified: 2026-05-08 with Python 3.12.*

---

## 4. Anthropic Agents SDK + Langfuse (decorator, token usage)

```python
# anthropic_langfuse.py
import os
import anthropic
from langfuse import observe, get_client

langfuse = get_client()
client = anthropic.Anthropic()

TOOLS = [{
    "name": "get_weather",
    "description": "Returns current weather for a city",
    "input_schema": {
        "type": "object",
        "properties": {"city": {"type": "string"}},
        "required": ["city"],
    },
}]

def get_weather(city: str) -> str:
    return f"72°F sunny in {city}"

@observe(name="tool-call")
def execute_tool(name: str, args: dict) -> str:
    if name == "get_weather":
        return get_weather(args["city"])
    return "unknown tool"

@observe(name="agent-run", as_type="generation")
def run_agent(prompt: str, session_id: str = "default") -> str:
    langfuse.update_current_trace(
        session_id=session_id,
        user_id="user-42",
        tags=["weather", "anthropic-agents-sdk"],
    )
    messages = [{"role": "user", "content": prompt}]

    while True:
        resp = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1024,
            tools=TOOLS,
            messages=messages,
        )
        # Surface usage so Langfuse computes cost:
        langfuse.update_current_observation(
            model="claude-sonnet-4-6",
            usage_details={
                "input": resp.usage.input_tokens,
                "output": resp.usage.output_tokens,
                "cache_read_input_tokens": getattr(resp.usage, "cache_read_input_tokens", 0),
                "cache_creation_input_tokens": getattr(resp.usage, "cache_creation_input_tokens", 0),
            },
        )

        if resp.stop_reason == "end_turn":
            return "".join(b.text for b in resp.content if b.type == "text")

        if resp.stop_reason == "tool_use":
            tool_use = next(b for b in resp.content if b.type == "tool_use")
            tool_result = execute_tool(tool_use.name, tool_use.input)
            messages.append({"role": "assistant", "content": resp.content})
            messages.append({
                "role": "user",
                "content": [{
                    "type": "tool_result",
                    "tool_use_id": tool_use.id,
                    "content": tool_result,
                }],
            })

if __name__ == "__main__":
    print(run_agent("What's the weather in Tokyo?", session_id="demo-003"))
    langfuse.flush()
```

```bash
pip install 'anthropic>=0.40' 'langfuse>=3.0'
export ANTHROPIC_API_KEY=sk-ant-...
export LANGFUSE_PUBLIC_KEY=pk-lf-... LANGFUSE_SECRET_KEY=sk-lf-...
python anthropic_langfuse.py
```

*Last verified: 2026-05-08 with Python 3.12.*

---

## 5. OpenAI Agents SDK + Arize Phoenix (native trace processor)

This example uses the **OpenAI Agents SDK's native tracing** wired to Phoenix — it captures handoffs, guardrails, and agent runs as first-class spans. Do **not** use `openinference-instrumentation-openai` here; that only captures raw OpenAI HTTP calls and loses agent structure.

```python
# openai_agents_phoenix.py
import os
from phoenix.otel import register
from openinference.instrumentation.openai_agents import OpenAIAgentsInstrumentor
from agents import Agent, Runner, function_tool

# --- Observability: Phoenix native trace processor for Agents SDK ---
tracer_provider = register(
    project_name=os.getenv("PHOENIX_PROJECT_NAME", "openai-agents-demo"),
    endpoint=os.getenv("PHOENIX_COLLECTOR_ENDPOINT", "http://localhost:6006/v1/traces"),
)
OpenAIAgentsInstrumentor().instrument(tracer_provider=tracer_provider)

# --- Agents with handoff ---
@function_tool
def get_weather(city: str) -> str:
    """Get current weather for a city."""
    return f"72°F sunny in {city}"

weather_agent = Agent(
    name="WeatherAgent",
    instructions="You answer weather questions concisely.",
    tools=[get_weather],
)
triage = Agent(
    name="Triage",
    instructions="Hand off weather questions to WeatherAgent.",
    handoffs=[weather_agent],
)

if __name__ == "__main__":
    result = Runner.run_sync(triage, "What's the weather in Tokyo?")
    print(result.final_output)
    # Open http://localhost:6006 — you should see:
    #   Runner.run -> Triage -> Handoff -> WeatherAgent -> tool: get_weather -> LLM
```

```bash
phoenix serve &  # background Phoenix UI on :6006
pip install 'arize-phoenix>=5.0' 'openinference-instrumentation-openai-agents>=0.1' \
            'openai-agents>=0.0.4'
export OPENAI_API_KEY=sk-...
python openai_agents_phoenix.py
```

*Last verified: 2026-05-08 with Python 3.12.*

---

## 6. smolagents + Langfuse (OpenInference instrumentor)

```python
# smolagents_langfuse.py
import base64
import os
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from openinference.instrumentation.smolagents import SmolagentsInstrumentor
from smolagents import CodeAgent, DuckDuckGoSearchTool, LiteLLMModel

# --- Observability: Langfuse via OTLP ---
host = os.environ["LANGFUSE_HOST"].rstrip("/")
auth = base64.b64encode(
    f"{os.environ['LANGFUSE_PUBLIC_KEY']}:{os.environ['LANGFUSE_SECRET_KEY']}".encode()
).decode()

provider = TracerProvider(resource=Resource.create({"service.name": "smolagents-demo"}))
provider.add_span_processor(
    BatchSpanProcessor(
        OTLPSpanExporter(
            endpoint=f"{host}/api/public/otel/v1/traces",
            headers={"Authorization": f"Basic {auth}"},
        )
    )
)
trace.set_tracer_provider(provider)
SmolagentsInstrumentor().instrument(tracer_provider=provider)

# --- Agent ---
model = LiteLLMModel(model_id="anthropic/claude-sonnet-4-6")
agent = CodeAgent(tools=[DuckDuckGoSearchTool()], model=model)

if __name__ == "__main__":
    answer = agent.run("Who won the latest Formula 1 Grand Prix?")
    print(answer)
    provider.shutdown()
```

```bash
pip install 'smolagents>=1.0' 'openinference-instrumentation-smolagents>=0.1' \
            'opentelemetry-sdk>=1.25' 'opentelemetry-exporter-otlp-proto-http>=1.25'
export ANTHROPIC_API_KEY=sk-ant-...
export LANGFUSE_PUBLIC_KEY=pk-lf-... LANGFUSE_SECRET_KEY=sk-lf-... LANGFUSE_HOST=https://cloud.langfuse.com
python smolagents_langfuse.py
```

*Last verified: 2026-05-08 with Python 3.12.*

---

## 7. LlamaIndex + SigNoz (RetrieverQueryEngine with retrieval spans)

```python
# llama_signoz.py
import os
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from openinference.instrumentation.llama_index import LlamaIndexInstrumentor

from llama_index.core import VectorStoreIndex, SimpleDirectoryReader, Settings
from llama_index.llms.anthropic import Anthropic

# --- Observability: SigNoz via OTLP ---
headers = {}
if key := os.getenv("SIGNOZ_INGESTION_KEY"):
    headers["signoz-access-token"] = key

provider = TracerProvider(resource=Resource.create({"service.name": "llamaindex-demo"}))
provider.add_span_processor(
    BatchSpanProcessor(
        OTLPSpanExporter(
            endpoint=os.getenv("SIGNOZ_ENDPOINT", "http://localhost:4318/v1/traces"),
            headers=headers,
        )
    )
)
trace.set_tracer_provider(provider)
LlamaIndexInstrumentor().instrument(tracer_provider=provider)

# --- RAG pipeline ---
Settings.llm = Anthropic(model="claude-sonnet-4-6")
documents = SimpleDirectoryReader("./docs").load_data()
index = VectorStoreIndex.from_documents(documents)
query_engine = index.as_query_engine()

if __name__ == "__main__":
    response = query_engine.query("Summarize the main themes.")
    print(response)
    # In SigNoz: see RETRIEVER spans with retrieval.documents attribute
    provider.shutdown()
```

```bash
pip install 'llama-index>=0.11' 'llama-index-llms-anthropic' \
            'openinference-instrumentation-llama-index>=2.0' \
            'opentelemetry-sdk>=1.25' 'opentelemetry-exporter-otlp-proto-http>=1.25'
mkdir -p docs && echo "Sample document content." > docs/sample.txt
export ANTHROPIC_API_KEY=sk-ant-... SIGNOZ_ENDPOINT=http://localhost:4318/v1/traces
python llama_signoz.py
```

*Last verified: 2026-05-08 with Python 3.12.*

---

## 8. Custom multi-agent loop + Arize Phoenix (manual span hierarchy)

When you don't use a framework, the skill writes an `observent_otel.py` helper module to your project. The helper is **convention-aware**: the convention resolved in Step 3 (`oi`, `otel-genai`, or `both`) is **baked in as a literal at generation time** — no env var, no runtime override. The example below shows what gets written for Phoenix-only (`oi`); for Langfuse/SigNoz the literal is `"otel-genai"`, and for Phoenix + (Langfuse or SigNoz) fan-out it's `"both"`.

```python
# observent_otel.py — generated helper (kept in your repo)
"""observent-generated OpenTelemetry helpers for multi-agent apps."""
from __future__ import annotations
import json
from contextlib import contextmanager
from typing import Any

from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

# Resolved by the skill in Step 3 from your chosen backend set and written
# here as a literal. To change it, re-run /observent with a different backend(s).
_CONVENTION = "oi"  # "oi" | "otel-genai" | "both"


def init_tracing(*, service_name: str, exporter) -> trace.TracerProvider:
    provider = TracerProvider(resource=Resource.create({"service.name": service_name}))
    provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(provider)
    return provider


def _set(span, key: str, value: Any) -> None:
    if value is None:
        return
    span.set_attribute(key, value if isinstance(value, (str, int, float, bool)) else json.dumps(value))


def _emit_oi() -> bool:
    return _CONVENTION in ("oi", "both")


def _emit_otel() -> bool:
    return _CONVENTION in ("otel-genai", "both")


@contextmanager
def with_agent_span(name: str, role: str = "", framework: str = "custom"):
    tracer = trace.get_tracer("observent")
    with tracer.start_as_current_span(f"agent.{name}") as span:
        if _emit_oi():
            _set(span, "openinference.span.kind", "AGENT")
            _set(span, "agent.name", name)
            _set(span, "agent.role", role)
            _set(span, "agent.framework", framework)
        if _emit_otel():
            _set(span, "gen_ai.operation.name", "invoke_agent")
            _set(span, "gen_ai.agent.name", name)
            _set(span, "gen_ai.agent.description", role)
        yield span


def set_llm_attrs(span, *, model: str, provider: str, input_messages, output_messages,
                  prompt_tokens: int, completion_tokens: int,
                  cache_read_tokens: int = 0, cache_write_tokens: int = 0,
                  invocation_parameters: dict | None = None,
                  finish_reasons: list[str] | None = None) -> None:
    if _emit_oi():
        _set(span, "openinference.span.kind", "LLM")
        _set(span, "llm.model_name", model)
        _set(span, "llm.provider", provider)
        _set(span, "llm.input_messages", input_messages)
        _set(span, "llm.output_messages", output_messages)
        _set(span, "input.value", input_messages)
        _set(span, "input.mime_type", "application/json")
        _set(span, "output.value", output_messages)
        _set(span, "output.mime_type", "application/json")
        _set(span, "llm.token_count.prompt", prompt_tokens)
        _set(span, "llm.token_count.completion", completion_tokens)
        _set(span, "llm.token_count.total", prompt_tokens + completion_tokens)
        if cache_read_tokens:
            _set(span, "llm.token_count.prompt_details.cache_read", cache_read_tokens)
        if cache_write_tokens:
            _set(span, "llm.token_count.prompt_details.cache_write", cache_write_tokens)
        if invocation_parameters:
            _set(span, "llm.invocation_parameters", invocation_parameters)
        if finish_reasons:
            _set(span, "llm.finish_reasons", finish_reasons)
    if _emit_otel():
        _set(span, "gen_ai.operation.name", "chat")
        _set(span, "gen_ai.provider.name", provider)
        _set(span, "gen_ai.request.model", model)
        _set(span, "gen_ai.response.model", model)
        _set(span, "gen_ai.usage.input_tokens", prompt_tokens)
        _set(span, "gen_ai.usage.output_tokens", completion_tokens)
        if cache_read_tokens:
            _set(span, "gen_ai.usage.cache_read.input_tokens", cache_read_tokens)
        if cache_write_tokens:
            _set(span, "gen_ai.usage.cache_creation.input_tokens", cache_write_tokens)
        if invocation_parameters:
            for k, v in invocation_parameters.items():
                _set(span, f"gen_ai.request.{k}", v)
        if finish_reasons:
            _set(span, "gen_ai.response.finish_reasons", finish_reasons)


def set_tool_attrs(span, *, name: str, description: str = "", parameters: dict | None = None,
                   input_value: Any = None, output_value: Any = None) -> None:
    if _emit_oi():
        _set(span, "openinference.span.kind", "TOOL")
        _set(span, "tool.name", name)
        _set(span, "tool.description", description)
        if parameters is not None:
            _set(span, "tool.parameters", parameters)
        if input_value is not None:
            _set(span, "input.value", input_value)
        if output_value is not None:
            _set(span, "output.value", output_value)
    if _emit_otel():
        _set(span, "gen_ai.operation.name", "execute_tool")
        if parameters is not None:
            _set(span, "gen_ai.tool.definitions", {"name": name, "description": description, "parameters": parameters})
```

```python
# main.py — your custom multi-agent app
import os
import anthropic
from opentelemetry import trace
from phoenix.otel import register
from observent_otel import with_agent_span, set_llm_attrs, set_tool_attrs

tracer_provider = register(
    project_name=os.getenv("PHOENIX_PROJECT_NAME", "custom-agent-demo"),
    endpoint=os.getenv("PHOENIX_COLLECTOR_ENDPOINT", "http://localhost:6006/v1/traces"),
)
tracer = trace.get_tracer("custom-agent")
client = anthropic.Anthropic()


def planner(question: str) -> str:
    with with_agent_span("planner", role="Decompose user questions into steps") as span:
        msgs = [{"role": "user", "content": f"Plan steps to answer: {question}"}]
        with tracer.start_as_current_span("llm.call") as llm_span:
            resp = client.messages.create(model="claude-sonnet-4-6", max_tokens=512, messages=msgs)
            output = resp.content[0].text
            set_llm_attrs(
                llm_span, model="claude-sonnet-4-6", provider="anthropic",
                input_messages=msgs, output_messages=[{"role": "assistant", "content": output}],
                prompt_tokens=resp.usage.input_tokens, completion_tokens=resp.usage.output_tokens,
            )
        span.set_attribute("output.value", output)
        return output


def executor(plan: str, question: str) -> str:
    with with_agent_span("executor", role="Execute the plan") as span:
        with tracer.start_as_current_span("tool.call") as tool_span:
            set_tool_attrs(tool_span, name="lookup", description="Web lookup",
                           parameters={"q": "string"}, input_value={"q": question},
                           output_value={"result": "stub"})
        msgs = [{"role": "user", "content": f"Plan:\n{plan}\n\nAnswer: {question}"}]
        with tracer.start_as_current_span("llm.call") as llm_span:
            resp = client.messages.create(model="claude-sonnet-4-6", max_tokens=512, messages=msgs)
            output = resp.content[0].text
            set_llm_attrs(
                llm_span, model="claude-sonnet-4-6", provider="anthropic",
                input_messages=msgs, output_messages=[{"role": "assistant", "content": output}],
                prompt_tokens=resp.usage.input_tokens, completion_tokens=resp.usage.output_tokens,
            )
        span.set_attribute("output.value", output)
        return output


if __name__ == "__main__":
    q = "What is observability for multi-agent systems?"
    plan = planner(q)
    print(executor(plan, q))
    tracer_provider.shutdown()
```

*Last verified: 2026-05-08 with Python 3.12.*

---

## Multi-Backend Fan-Out (Phoenix + Langfuse + SigNoz)

Single `TracerProvider`, one `BatchSpanProcessor` per backend. Because the set contains Phoenix **and** (Langfuse, SigNoz), the convention rule resolves to **`both`** — every span must carry OpenInference and OTel-GenAI keys so each backend's UI lights up. See `openinference.md` and `otel_genai.md` for canonical key lists.

```python
# fanout.py
import os
import base64
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

provider = TracerProvider(resource=Resource.create({"service.name": "fanout-demo"}))

# Phoenix
provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(
    endpoint=os.getenv("PHOENIX_COLLECTOR_ENDPOINT", "http://localhost:6006/v1/traces"),
    headers={"Authorization": f"Bearer {os.environ['PHOENIX_API_KEY']}"} if os.getenv("PHOENIX_API_KEY") else {},
)))

# Langfuse
_lf_host = os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com").rstrip("/")
_lf_auth = base64.b64encode(
    f"{os.environ['LANGFUSE_PUBLIC_KEY']}:{os.environ['LANGFUSE_SECRET_KEY']}".encode()
).decode()
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
tracer = trace.get_tracer("fanout-demo")

# Every span must carry BOTH conventions when fanning out across Phoenix + (Langfuse|SigNoz).
with tracer.start_as_current_span("smoke-llm") as span:
    # OpenInference
    span.set_attribute("openinference.span.kind", "LLM")
    span.set_attribute("llm.model_name", "claude-sonnet-4-6")
    span.set_attribute("llm.provider", "anthropic")
    span.set_attribute("llm.token_count.prompt", 12)
    span.set_attribute("llm.token_count.completion", 8)
    span.set_attribute("llm.token_count.total", 20)
    # OTel-GenAI
    span.set_attribute("gen_ai.operation.name", "chat")
    span.set_attribute("gen_ai.provider.name", "anthropic")
    span.set_attribute("gen_ai.request.model", "claude-sonnet-4-6")
    span.set_attribute("gen_ai.usage.input_tokens", 12)
    span.set_attribute("gen_ai.usage.output_tokens", 8)

provider.shutdown()
# Spans now in all three backends. Failure in one doesn't affect the others.
```

For Phoenix-less fan-out (`langfuse,signoz`), drop the OI block — `otel-genai` alone is sufficient.

*Last verified: 2026-05-08 with Python 3.12.*

---

## Verification Checklist

```
[ ] Required packages installed (pip list | grep <backend>)
[ ] Required env vars set (use validate_setup.py to check)
[ ] App runs without import errors
[ ] Trace appears in backend UI within 10s of running the app
[ ] LLM spans show non-zero token counts
[ ] LLM spans show recognised model name (cost is non-zero in UI)
[ ] Span tree shows correct hierarchy (Crew → Agent → LLM, or Workflow → Step → LLM)
[ ] Multi-turn conversations group under one session.id
[ ] No credentials hardcoded; .env is in .gitignore
```

Or just run:

```bash
# single backend
python "${CLAUDE_SKILL_DIR}/scripts/validate_setup.py" <backend> --smoke-test
# multi-backend fan-out (comma-separated)
python "${CLAUDE_SKILL_DIR}/scripts/validate_setup.py" phoenix,signoz --smoke-test
```

---

## Common Issues

- **No traces appear** → check env vars loaded, force-flush before exit (`provider.shutdown()` or `langfuse.flush()`).
- **Token counts missing** → instrumentor mismatch or custom LLM wrapper not surfacing `usage`. For Custom path, set explicitly via `set_llm_attrs()`.
- **Cost shows $0** → backend can't recognise the model name; verify `llm.model_name` matches the backend's price table.
- **Orphan spans / broken trace tree** → context propagation. Check Python ≥ 3.11 (or use `copy_context().run`); use `start_as_current_span`; enable HTTPX/Requests instrumentors for cross-service.
- **OpenAI Agents SDK shows raw HTTP not handoffs** → switch from `openinference-instrumentation-openai` to `openinference-instrumentation-openai-agents` and register via `set_trace_processors()`.
- **SigNoz Cloud 401** → header name is `signoz-access-token` (not `signoz-ingestion-key`); verify against current docs.
