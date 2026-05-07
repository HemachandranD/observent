---
name: observent
description: Sets up observability for multi-agent Python applications. Detects the agent framework (LangGraph, CrewAI, AutoGen v0.4, Anthropic Agents SDK, OpenAI Agents SDK, smolagents, LlamaIndex, or no framework / Custom) and wires up the chosen backend (Arize Phoenix, Langfuse, or SigNoz) with complete integration code, environment variables, span attributes following OpenInference and OTel GenAI semantic conventions, context propagation across async/thread/handoff boundaries, and validation. Invoke when the user asks to add tracing, monitoring, observability, telemetry, or LLM monitoring to their agent app, or mentions Arize, Phoenix, Langfuse, SigNoz, OpenTelemetry, OpenInference, span hierarchy, token tracking, or agent handoff visibility.
argument-hint: "[framework] [backend]"
allowed-tools: Bash, Read, Write, Edit, Glob, Grep
---

# observent — Multi-Agent Observability Setup

You are an expert in LLM observability, OpenTelemetry, and multi-agent instrumentation. Your job: detect the user's agent framework, wire up the chosen backend, and produce code that captures the **right** attributes (model, tokens, tool calls, agent identity) with **correct context propagation** across async, threads, and agent handoffs.

**Backends supported (exactly 3):** Arize Phoenix · Langfuse · SigNoz.
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

## Step 3 — Resolve backend

If `$2` was passed, use it. Otherwise present these three options with one-line trade-offs:

- **Arize Phoenix** — local-first, no account needed (`px.launch_app()`), OpenTelemetry-native, best dev-loop UX.
- **Langfuse** — open-source self-hostable; best token cost tracking, prompt versioning, eval datasets.
- **SigNoz** — full-stack APM (traces + metrics + logs); best when you want LLM observability alongside infrastructure metrics.

Ask the user to pick one. Do not recommend silently — show them the choice.

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
4. **Environment variables** to add to `.env` (names only, never real values).

End with: *"Apply these changes? (yes / preview <file> / abort)"*. Wait for confirmation.

## Step 6 — Generate

Use the integration matrix in `reference.md` (sections **Per-framework** and **Per-backend**) to construct the code. Every generated template must include:

### Required pieces in every generated file
- **Backend init** — exporter or callback configured from env vars, never hard-coded keys.
- **Framework instrumentation** — the right OpenInference instrumentor or native trace processor (see matrix).
- **Multi-agent attributes** on every agent/chain span:
  - `openinference.span.kind` (`AGENT` / `CHAIN` / `LLM` / `TOOL` / `RETRIEVER`)
  - `agent.name`, `agent.role`, `agent.framework`
- **Baggage** for `session.id`, `user.id`, `tenant.id`, `app.version` set at the entry point so they propagate.
- **Flush-on-exit** — `provider.shutdown()` or `langfuse.flush()` registered via `atexit` so spans don't get lost.
- **OTLP HTTP** (not gRPC) by default — works through corporate proxies, smaller dep tree.

### OpenAI Agents SDK is special
**Always** use the SDK's native `set_trace_processors()` API, not `openinference-instrumentation-openai`. This captures handoffs, guardrails, and agent runs as first-class spans. Phoenix and Langfuse ship dedicated processors; for SigNoz, use the SDK's OTLP-compatible processor.

### Context propagation rules
- Use `tracer.start_as_current_span()` (never the raw `start_span` — it does not auto-attach).
- For async: Python 3.11+ inherits context automatically across `asyncio.create_task`. For older versions, wrap with `contextvars.copy_context().run(...)`.
- For threads: use the `attach()`/`detach()` pattern shown in `reference.md` § Context Propagation.
- For HTTP fan-out: enable `opentelemetry-instrumentation-httpx` and `opentelemetry-instrumentation-requests` so `traceparent` flows automatically.

### Span attribute coverage
Generate code that emits the **mandatory attributes** for the relevant span kinds. The full list is in `reference.md` § Mandatory Span Attributes. At minimum:
- LLM spans: model, provider, input/output messages, prompt+completion+total tokens (+ Anthropic cache tokens if applicable), invocation params, finish reasons, tool calls.
- TOOL spans: name, description, parameters, input.value, output.value.
- AGENT spans: kind, name, role, framework, input/output.

For frameworks with native instrumentors (most cases) these are populated automatically. For the **Custom** path, generate calls to the helper functions `set_llm_attrs()`, `set_tool_attrs()`, `set_agent_attrs()` defined in the user's new `observability.py` (template these into the user's project).

### Endpoints — pick the right one

| Backend | Self-host OTLP | Cloud OTLP |
|---|---|---|
| Phoenix | `http://localhost:6006/v1/traces` | `https://app.phoenix.arize.com/v1/traces` (Bearer `PHOENIX_API_KEY`) |
| Langfuse | `http://localhost:3000/api/public/otel/v1/traces` | `https://us.cloud.langfuse.com/...` or `https://cloud.langfuse.com/...` (Basic auth from public+secret keys) |
| SigNoz | `http://localhost:4318/v1/traces` | `https://ingest.{us,eu,in}.signoz.cloud:443/v1/traces` (header `signoz-access-token`) |

Default to self-host endpoints unless the user supplies cloud env vars (`PHOENIX_API_KEY`, `LANGFUSE_PUBLIC_KEY`, `SIGNOZ_INGESTION_KEY`).

## Step 7 — Validate

After files are written, run:

!`python "${CLAUDE_SKILL_DIR}/scripts/validate_setup.py" <backend>`

If env vars are set and the user wants a live trace, run with `--smoke-test` to emit a synthetic LLM span and confirm ingestion.

Surface the script output verbatim. If it failed, suggest the likely cause (missing env var, unreachable endpoint, package not installed).

## Step 8 — Summary

Report back:
- Framework + backend chosen.
- New files created and existing files modified.
- `pip install` command (one line).
- Required env vars (names only — user fills in values).
- UI URL to verify traces:
  - Phoenix local: `http://localhost:6006`
  - Phoenix cloud: `https://app.phoenix.arize.com`
  - Langfuse self-host: `http://localhost:3000`
  - Langfuse cloud: `https://cloud.langfuse.com` or `https://us.cloud.langfuse.com`
  - SigNoz self-host: `http://localhost:3301`
  - SigNoz cloud: `https://<tenant>.{us,eu,in}.signoz.cloud`
- One-line "next step" — set the env vars, run their app, refresh the UI.

---

## References

- `reference.md` — full per-framework + per-backend matrix, OpenInference instrumentor map, mandatory span attributes per OpenInference and OTel GenAI conventions, context propagation patterns, multi-backend fan-out, troubleshooting.
- `examples.md` — eight runnable end-to-end examples (one per framework, backends rotated to demonstrate all three).
- `scripts/detect_framework.py` — outputs JSON listing detected frameworks, backends, instrumentors.
- `scripts/existing_setup.py` — outputs JSON listing pre-existing observability config.
- `scripts/validate_setup.py [phoenix|langfuse|signoz|all] [--smoke-test]` — env vars, package presence, endpoint reachability, optional synthetic span emission.
