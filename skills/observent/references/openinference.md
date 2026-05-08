# OpenInference Semantic Conventions

Canonical attribute reference for the OpenInference (OI) tracing spec — the convention Arize Phoenix consumes natively. observent emits these keys when the resolved convention is `oi` or `both` (see `../SKILL.md` Step 3).

**Source:** https://arize-ai.github.io/openinference/spec/semantic_conventions.html
**Last verified:** 2026-05-08.

---

## Span kinds

Set on every span via `openinference.span.kind`.

| Value | Purpose |
|---|---|
| `LLM` | Large Language Model invocations |
| `EMBEDDING` | Embedding service calls |
| `CHAIN` | Workflow / graph nodes; entry points and links between steps |
| `RETRIEVER` | Data retrieval (RAG) |
| `RERANKER` | Document reranking |
| `TOOL` | External tool / function calls |
| `AGENT` | Reasoning blocks combining LLMs and tools |
| `GUARDRAIL` | Jailbreak protection / response filtering |
| `EVALUATOR` | Output evaluation / assessment |
| `PROMPT` | Prompt template rendering |

---

## LLM spans

### Core

| Attribute | Type | Notes |
|---|---|---|
| `llm.model_name` | string | Resolved model id (e.g. `gpt-4o`, `claude-sonnet-4-6`) |
| `llm.system` | string | Well-known: `anthropic`, `openai`, `vertexai`, `cohere`, `mistralai`, `xai`, `deepseek`, `amazon`, `meta`, `ai21` |
| `llm.provider` | string | Hosting provider (`openai`, `azure`, `google`, `aws`, …) |
| `llm.invocation_parameters` | JSON string | Excludes input messages |
| `llm.finish_reasons` | string[] | `stop`, `length`, `tool_use`, … |

### Messages (chat API)

Flattened with indexed prefixes — e.g. `llm.input_messages.0.message.role`.

| Attribute | Type | Notes |
|---|---|---|
| `llm.input_messages` | list of objects | Flattened per index |
| `llm.output_messages` | list of objects | Flattened per index |
| `…<i>.message.role` | string | `user`, `system`, `assistant`, `tool`, `function` |
| `…<i>.message.content` | string | Text content |
| `…<i>.message.contents` | list of objects | Multimodal content (use `message_content.*` below) |
| `…<i>.message.tool_calls` | list of objects | Function calls from the LLM |
| `…<i>.message.tool_call_id` | string | References `tool_call.id` |

### Multimodal content

Flattened — e.g. `llm.input_messages.0.message.contents.0.message_content.type`.

| Attribute | Type | Notes |
|---|---|---|
| `message_content.type` | string | `text`, `image`, `audio` |
| `message_content.text` | string | When `type=text` |
| `message_content.image` | object | When `type=image` (use `image.url`) |

### Tool calls (function calling)

| Attribute | Type | Notes |
|---|---|---|
| `tool_call.id` | string | Identifier for concurrent calls |
| `tool_call.function.name` | string | Function name being invoked |
| `tool_call.function.arguments` | JSON string | Function arguments |
| `message.function_call_name` | string | Legacy: function name in tool/function role |
| `message.function_call_arguments_json` | JSON string | Legacy: function arguments |
| `llm.function_call` | JSON string | Object with `function_name` and `args` |

### Available tools (advertised to the model)

| Attribute | Type | Notes |
|---|---|---|
| `llm.tools` | list of objects | Flattened |
| `…<i>.tool.name` | string | Tool identifier |
| `…<i>.tool.description` | string | Purpose |
| `…<i>.tool.json_schema` | JSON string | Input schema |
| `…<i>.tool.parameters` | JSON string | Parameter spec |

### Text completions (legacy API)

| Attribute | Type | Notes |
|---|---|---|
| `llm.prompts` | list of objects | `…<i>.prompt.text` |
| `llm.choices` | list of objects | `…<i>.completion.text` |

### Token counts

| Attribute | Type | Notes |
|---|---|---|
| `llm.token_count.prompt` | int | Input tokens |
| `llm.token_count.completion` | int | Output tokens |
| `llm.token_count.total` | int | Sum |
| `llm.token_count.prompt_details.cache_read` | int | Anthropic cache hit |
| `llm.token_count.prompt_details.cache_write` | int | Anthropic cache write |
| `llm.token_count.prompt_details.audio` | int | Audio input tokens |
| `llm.token_count.completion_details.reasoning` | int | Reasoning tokens |
| `llm.token_count.completion_details.audio` | int | Audio output tokens |

### Cost (USD)

| Attribute | Type | Notes |
|---|---|---|
| `llm.cost.prompt` | float | Input cost |
| `llm.cost.completion` | float | Output cost |
| `llm.cost.total` | float | Combined |
| `llm.cost.prompt_details.{input,cache_write,cache_read}` | float | Detail breakdown |
| `llm.cost.completion_details.{output,reasoning,audio}` | float | Detail breakdown |

### Prompt templates

| Attribute | Type | Notes |
|---|---|---|
| `llm.prompt_template.template` | string | Template with `{variable}` syntax |
| `llm.prompt_template.variables` | JSON string | Key-value substitutions |
| `llm.prompt_template.version` | string | Template version |
| `prompt.vendor` | string | `langchain`, `langsmith`, `portkey`, `arize-phoenix` |
| `prompt.id` | string | Vendor-specific id |
| `prompt.url` | string | Vendor-specific URL |

---

## TOOL spans

| Attribute | Type | Notes |
|---|---|---|
| `tool.name` | string | Tool identifier |
| `tool.description` | string | Documentation |
| `tool.json_schema` | JSON string | Input spec |
| `tool.parameters` | JSON string | Parameter spec |
| `tool.id` | string | Tool call result identifier |

Pair with generic `input.value` / `output.value` for actual call args and return value.

---

## AGENT spans

`openinference.span.kind = "AGENT"` plus:

| Attribute | Type | Notes |
|---|---|---|
| `agent.name` | string | Required — used for UI grouping |
| `agent.role` | string | |
| `agent.framework` | string | `langgraph` / `crewai` / `autogen-agentchat` / `anthropic-agents` / `openai-agents` / `smolagents` / `llama-index` / `custom` |
| `input.value` | string | Triggering task or message |
| `output.value` | string | Final agent output |

---

## CHAIN spans (workflow / graph nodes)

`openinference.span.kind = "CHAIN"` plus generic `input.value`, `output.value`.

---

## EMBEDDING spans

`openinference.span.kind = "EMBEDDING"` plus:

| Attribute | Type | Notes |
|---|---|---|
| `embedding.model_name` | string | e.g. `text-embedding-3-small` |
| `embedding.text` | string | Input text |
| `embedding.vector` | float[] | Output vector |
| `embedding.embeddings` | list of objects | `…<i>.embedding.{text,vector}` for batched calls |
| `embedding.invocation_parameters` | JSON string | Excludes input |

Embedding spans do **not** use `llm.system` or `llm.provider`.

---

## RETRIEVER spans (RAG)

`openinference.span.kind = "RETRIEVER"` plus:

| Attribute | Type | Notes |
|---|---|---|
| `retrieval.documents` | list of objects | Flattened per document |
| `…<i>.document.id` | string / int | Unique identifier |
| `…<i>.document.content` | string | Retrieved text |
| `…<i>.document.score` | float | Relevance |
| `…<i>.document.metadata` | JSON string | Associated metadata |
| `input.value` | string | Query text |

---

## RERANKER spans

| Attribute | Type | Notes |
|---|---|---|
| `reranker.model_name` | string | e.g. `cross-encoder/ms-marco-MiniLM-L-12-v2` |
| `reranker.query` | string | Query text |
| `reranker.input_documents` | list of objects | Pre-rank |
| `reranker.output_documents` | list of objects | Post-rank |
| `reranker.top_k` | int | Number of top results returned |

---

## Generic input / output

Set on most span kinds for at-a-glance inspection in the UI.

| Attribute | Type | Notes |
|---|---|---|
| `input.value` | string | Operation input |
| `input.mime_type` | string | e.g. `application/json` |
| `output.value` | string | Operation output |
| `output.mime_type` | string | e.g. `application/json` |

---

## Audio

| Attribute | Type | Notes |
|---|---|---|
| `audio.url` | string | Cloud storage URL |
| `audio.mime_type` | string | `audio/mpeg`, `audio/wav`, … |
| `audio.transcript` | string | Transcribed text |

---

## Image

| Attribute | Type | Notes |
|---|---|---|
| `image.url` | string | URL or base64-encoded data |

---

## Agent / execution graph

| Attribute | Type | Notes |
|---|---|---|
| `agent.name` | string | |
| `graph.node.id` | string | Execution graph node identifier |
| `graph.node.name` | string | Human-readable node name |
| `graph.node.parent_id` | string | Parent node; empty = root |

---

## Cross-cutting (Baggage)

Set once at the entry point with OTel baggage; promoted to span attributes via `BaggageSpanProcessor`.

| Attribute | Type | Notes |
|---|---|---|
| `session.id` | string | Groups traces per conversation / session |
| `user.id` | string | |
| `tenant.id` | string | |
| `app.version` | string | |
| `metadata` | JSON string | Span-level metadata |
| `tag.tags` | string[] | Categorical tags |

---

## Exception handling

| Attribute | Type | Notes |
|---|---|---|
| `exception.type` | string | Exception class name |
| `exception.message` | string | Detailed error message |
| `exception.stacktrace` | string | Stack trace |
| `exception.escaped` | bool | Scope escape indicator |

---

## Flattening rules

OI uses **indexed-attribute prefixes** for arrays of objects:

```
<prefix>.<index>.<suffix>
```

Examples:
- `llm.input_messages.0.message.role`
- `llm.output_messages.1.message.content`
- `llm.tools.0.tool.json_schema`
- `llm.output_messages.0.message.tool_calls.0.tool_call.id`

Allowed leaf types: `bool`, `str`, `bytes`, `int`, `float`, or `List` variants thereof. Anything richer (objects, mixed lists) must be JSON-stringified before being set.
