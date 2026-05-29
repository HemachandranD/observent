# test_workflows — observent demo apps

Two tiny agent workflows (CrewAI and LangGraph) that each take a user question
and walk through the same steps. They exist as a **test bed for observent**:
run them, then run `/observent` against this folder to wire up tracing and
confirm every span kind shows up in your backend.

## What each span kind maps to

| Capability | Where it lives | CrewAI app | LangGraph app |
|---|---|---|---|
| **Agent** | framework primitive | `Agent` | `answer` node |
| **Retriever** | `building_blocks.retrieve_context` | `retrieve_context` tool | `retrieve` node |
| **Tool** | `building_blocks.calculator` | `calculator` tool | `calculate` node |
| **MCP** | `mcp_server.py` over stdio | `company_policy` tool | `policy` node |
| **LLM #1 — direct Azure** | `openai.AzureOpenAI` from env | agent's native CrewAI `LLM` | `building_blocks.direct_azure_chat` |
| **LLM #2 — shared service** | `llm_service.py` (separate FastAPI process) | `ask_llm_service` tool | `draft` node |

The **direct** LLM call uses the Azure OpenAI SDK configured straight from env
vars. The **service** LLM is a separate process both apps call over HTTP — so
it appears as a distinct cross-service span.

## Files

```
building_blocks.py   # shared retriever / tool / MCP client / LLM helpers
mcp_server.py        # minimal MCP stdio server (one tool: company_policy)
llm_service.py       # separate FastAPI LLM service wrapping Azure OpenAI
crewai_app.py        # CrewAI workflow (agent + 4 tools)
langgraph_app.py     # LangGraph workflow (5-node linear pipeline)
requirements.txt
.env.example
```

## Run it

```bash
# 1. Install
python -m venv .venv && . .venv/bin/activate    # Windows: .venv\Scripts\Activate.ps1
pip install -r requirements.txt

# 2. Configure Azure OpenAI
cp .env.example .env        # then edit .env with your endpoint, key, deployment

# 3. Start the shared LLM service (separate terminal — both apps call it)
python llm_service.py        # serves http://localhost:8001

# 4. Run a workflow (each prompts for a question; Enter for a default)
python crewai_app.py
python langgraph_app.py
```

The MCP server does **not** need to be started manually — each app spawns
`mcp_server.py` over stdio on demand.

## Then wire up observability

```
/observent crewai phoenix
/observent langgraph phoenix
```

(or any backend / multi-backend set). Re-run the apps and the traces should
contain agent, retriever, tool, MCP, and both LLM spans — including the
cross-service hop into the shared LLM service.
