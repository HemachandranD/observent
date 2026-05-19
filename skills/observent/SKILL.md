---
name: observent
description: Sets up observability for multi-agent Python applications using a spec-driven lifecycle (spec → plan → tasks → implement) with project-local persistent state in .observent/. Detects the agent framework (LangGraph, CrewAI, Microsoft Agent Framework, Anthropic Agents SDK, OpenAI Agents SDK, smolagents, LlamaIndex, or no framework / Custom) and wires up the chosen backend (Arize Phoenix, Langfuse, SigNoz, Elastic APM, or LangSmith) with complete integration code, environment variables, span attributes following OpenInference and OTel GenAI semantic conventions, context propagation across async/thread/handoff boundaries, and validation. The .observent/tasks.json checkpoint makes the workflow resumable across session breaks. Invoke when the user asks to add tracing, monitoring, observability, telemetry, or LLM monitoring to their agent app, or mentions Arize, Phoenix, Langfuse, SigNoz, Elastic APM, LangSmith, LangChain tracing, OpenTelemetry, OpenInference, span hierarchy, token tracking, or agent handoff visibility.
argument-hint: "[framework] [backend|backend,backend,...]"
allowed-tools: Bash, Read, Write, Edit, Glob, Grep
---

# observent — Multi-Agent Observability (Spec-Driven)

You are an expert in Agent & LLM observability, OpenTelemetry, and multi-agent instrumentation. Your job: produce three artifacts under `.observent/` in the user's project, then execute the task list.

**Backends supported (exactly 5):** Arize Phoenix · Langfuse · SigNoz · Elastic APM · LangSmith.
**Frameworks supported (8):** LangGraph · CrewAI · Microsoft Agent Framework (`agent-framework`) · Anthropic Agents SDK · OpenAI Agents SDK · smolagents · LlamaIndex · Custom.

## Lifecycle

```
.observent/spec.md     →    .observent/plan.md     →    .observent/tasks.json     →    user files
   (what & why)              (how, with content)         (checkpoint, mutable)         (executed)
```

Four phases — Spec, Plan, Tasks, Implement — described below. The artifacts are fingerprinted: downstream regenerates when upstream changes. `tasks.json` doubles as the session checkpoint; any task with status `pending` or `failed` means the workflow is incomplete and you should offer to resume.

**Canonical schema reference:** `references/spec_schema.md`. Construct and validate the three artifacts strictly against the shapes documented there. This SKILL.md describes the *workflow*; `spec_schema.md` is the contract.

---

## On every invocation — resume check first

Before doing anything else:

1. Read `.observent/tasks.json` if it exists.
2. If any task has status `pending` or `failed`, prompt the user:
   `Found incomplete observent run. Resume from task <id> (<kind>)? (yes / restart / abort)`
   - `yes` → jump to the Implement phase from the first non-terminal task.
   - `restart` → delete `.observent/{spec.md, plan.md, tasks.json}` and start fresh from the Spec phase.
   - `abort` → exit without changes.
3. If `tasks.json` is absent or all tasks are terminal (`done` / `skipped`), check upstream drift (§ Drift detection) and run the lifecycle from the earliest phase whose artifact is missing or stale.

If invoked with `$1`/`$2` args, capture them as the user's framework/backend preferences and proceed into the Spec phase; they override prior choices and invalidate downstream fingerprints.

---

## Phase 1 — Spec

**Goal:** produce `.observent/spec.md` capturing what to set up and why. Locks once the user confirms the choices.

### Step 1.1 — Detect environment

Run both detectors **in parallel** — they're independent deterministic scripts that emit JSON, so issue them as two Bash tool calls in a **single message**, not sequentially:

- `python "${CLAUDE_SKILL_DIR}/scripts/detect_framework.py"`
- `python "${CLAUDE_SKILL_DIR}/scripts/existing_setup.py"`

Do **not** wrap either script in a subagent — they're already deterministic; an LLM in the middle adds latency and nondeterminism without saving context. The JSON output goes straight into `spec.detection`.

For `existing_setup.py`: treat entries with `kind: "backend"` (Phoenix / Langfuse / SigNoz) and non-empty `imports` or `env_vars_in_files` as existing observability. Entries with `kind: "instrumentation"` alone don't count — they may belong to an unrelated tracing setup.

### Step 1.2 — Resolve framework

1. If the user passed a framework as `$1` (`langgraph` / `crewai` / `microsoft-agent-framework` / `anthropic-agents` / `openai-agents` / `smolagents` / `llama-index` / `custom`), use it.
2. Else if exactly one framework is detected, confirm it in one short sentence.
3. Else if multiple are detected, ask which one to instrument.
4. If `autogen` / `autogen_agentchat` / `pyautogen` is detected, inform the user that AutoGen has been superseded by **Microsoft Agent Framework** (`microsoft-agent-framework`) — Microsoft's unification of AutoGen and Semantic Kernel — and observent no longer supports AutoGen. Offer MAF, or the **Custom** path if they need to keep their existing AutoGen code.
5. If none detected, ask; "none / writing from scratch" → **Custom** path.

### Step 1.3 — Resolve backend(s) and convention

`$2` accepts one or more backends, comma-separated (e.g. `phoenix` or `phoenix,langsmith`). If `$2` was passed, parse into a deduplicated set. Otherwise present these five with one-line trade-offs and ask the user to pick one or more:

- **Arize Phoenix** — local-first, no account needed (`px.launch_app()`), OpenTelemetry-native, best dev-loop UX.
- **Langfuse** — open-source self-hostable; best token cost tracking, prompt versioning, eval datasets.
- **SigNoz** — full-stack APM (traces + metrics + logs); best when you want LLM observability alongside infra metrics in a self-hostable OTel stack.
- **Elastic APM** — Elastic Stack APM Server with the native `elastic-apm` agent; best when you also need transaction tracing and infra metrics in Kibana alongside LLM tracing.
- **LangSmith** — LangChain's hosted observability platform (US + EU cloud, enterprise self-host); best when you're already on LangGraph/LangChain. Pure OTLP HTTP; OTel-GenAI conventions on the wire.

**Derive the convention mechanically** from the resolved backend set (do not ask the user):

| Backend set | Convention |
|---|---|
| `{phoenix}` | `oi` (OpenInference only — Phoenix-native UI) |
| Any non-empty subset of `{langfuse, signoz, elastic-apm, langsmith}` (no Phoenix) | `otel-genai` |
| Any set containing Phoenix **and** at least one of `{langfuse, signoz, elastic-apm, langsmith}` | `both` |

State the resolved convention in one short sentence (e.g. "Resolved: phoenix,elastic-apm → emitting both OI and OTel-GenAI attributes").

### Step 1.4 — Existing-setup decision

If Step 1.1 found pre-existing observability config, ask explicitly:
- **Extend** — keep their existing setup, add observent attributes/instrumentors on top.
- **Replace** — overwrite with observent's recommended pattern.
- **Abort** — exit without changes.

Never overwrite without asking, even when auto-invoked. Store the choice in `spec.choice.existing_setup_decision`. Once locked it is **not re-prompted on resume**; to change it the user re-runs `/observent-spec`.

### Step 1.5 — Write `.observent/spec.md`

Construct the YAML frontmatter per `references/spec_schema.md § 1`. Compute `detection.project_fingerprint` from `pyproject.toml` + `requirements*.txt` + `poetry.lock` (see schema for exact ordering). Write the file; set `status: locked` once the user has confirmed the choices in Steps 1.2–1.4. Preserve any existing prose body on re-runs.

---

## Phase 2 — Plan

**Goal:** read `spec.md` and produce `.observent/plan.md` with the full generated content embedded in fenced blocks behind anchor comments. Deterministic from spec — no user questions in this phase except the diff-preview confirm in Phase 4.

### Step 2.1 — Decide structure

Using `references/matrix.md` (sections **Per-framework** and **Per-backend**), determine:

- **Files to generate** — typically:
  - `observent_otel.py` (always — backend init + framework instrumentation).
  - `observent_fastapi_payload.py` (only if `spec.choice.fastapi_payload_capture: true`).
  - Edits to the user's entry-point file (e.g., `main.py`) to import `observent_otel` and register middleware.
  - `.env` append with required env var names.
- **Multi-backend processor list** — one `BatchSpanProcessor(OTLPSpanExporter(...))` per OTLP backend in `spec.choice.backends` (Phoenix, Langfuse, SigNoz, LangSmith). Elastic APM in native-agent mode is **not** a processor — set `elastic_apm_native_agent: true` and instantiate `elasticapm.Client(...)` + `elasticapm.instrument()` next to the TracerProvider.
- **OpenAI Agents SDK** — if `spec.choice.framework == openai-agents`, set `openai_agents_native_processors: true` and use the SDK's native `set_trace_processors()` API, not `openinference-instrumentation-openai`. This is non-negotiable.
- **Pinned versions** — copy exact `==X.Y.Z` pins from `references/matrix.md § Verified Versions` into the `pip_install` line.

### Step 2.2 — Required pieces in every generated file

Every `observent_otel.py` template must include:

- **Backend init** — exporter / native client configured from env vars; never hard-code keys.
- **Framework instrumentation** — the right OpenInference instrumentor or native trace processor (see `references/matrix.md`).
- **Multi-agent attributes** on every agent/chain span, keyed by `spec.choice.convention`:
  - `oi`: `openinference.span.kind` (`AGENT` / `CHAIN` / `LLM` / `TOOL` / `RETRIEVER`), `agent.name`, `agent.role`, `agent.framework`.
  - `otel-genai`: `gen_ai.operation.name`, `gen_ai.agent.name`, `gen_ai.provider.name`.
  - `both`: emit the union.
- **Baggage** for `session.id`, `user.id`, `tenant.id`, `app.version` at the entry point.
- **Flush-on-exit** — `provider.shutdown()` or `langfuse.flush()` via `atexit`.
- **OTLP HTTP** (not gRPC) for all OTLP backends.
- **Convention as a generation-time literal** — for the Custom path, write `_CONVENTION = "<oi|otel-genai|both>"` as a literal in `observent_otel.py`. Do **not** make it read an env var; convention is a generation-time decision.

### Step 2.3 — FastAPI payload capture

If `spec.choice.fastapi_payload_capture: true`, generate `observent_fastapi_payload.py` from the canonical template in `references/fastapi_payload.md` and add `app.add_middleware(ObserventPayloadMiddleware)` to the user's FastAPI app. Sensitive keys (auth credentials, session/CSRF, PII) are redacted at the value level; the key stays so the attribute shape is stable. No truncation. The redaction list is a **generation-time literal** in the generated file.

### Step 2.4 — Context propagation rules

observent emits W3C-compliant context. Every template relies on the OTel SDK's default composite propagator (`TraceContextTextMapPropagator` + `W3CBaggagePropagator`).

- **Do not override the global propagator.** Never call `set_global_textmap()` with B3/Jaeger/custom — that breaks `traceparent` interop with every backend in the matrix.
- Use `tracer.start_as_current_span()` (never the raw `start_span`).
- Async: Python 3.11+ inherits context across `asyncio.create_task`. For older versions wrap with `contextvars.copy_context().run(...)`.
- Threads: `attach()`/`detach()` pattern (see `references/matrix.md § Context Propagation`).
- HTTP fan-out: enable `opentelemetry-instrumentation-httpx` and `opentelemetry-instrumentation-requests`.
- Subprocess fan-out: `opentelemetry.propagate.inject(env)` before `subprocess.run(env=env)`; child re-extracts with `extract(os.environ)`. On Windows, env var names are case-insensitive — read the exact case `inject` wrote (`traceparent`) or normalize.

### Step 2.5 — Endpoints

| Backend | Self-host | Cloud |
|---|---|---|
| Phoenix | OTLP `http://localhost:6006/v1/traces` | `https://app.phoenix.arize.com/v1/traces` (Bearer `PHOENIX_API_KEY`) |
| Langfuse | OTLP `http://localhost:3000/api/public/otel/v1/traces` | `https://us.cloud.langfuse.com/...` or `https://cloud.langfuse.com/...` (Basic from public+secret keys) |
| SigNoz | OTLP `http://localhost:4318/v1/traces` | `https://ingest.{us,eu,in}.signoz.cloud:443/v1/traces` (header `signoz-access-token`) |
| Elastic APM | APM Server `http://localhost:8200` (agent default) | `https://<deployment>.apm.<region>.cloud.es.io:443` (Bearer `ELASTIC_APM_SECRET_TOKEN` or ApiKey `ELASTIC_APM_API_KEY`) |
| LangSmith | OTLP `${LANGSMITH_ENDPOINT}/otel/v1/traces` (enterprise self-host) | `https://api.smith.langchain.com/otel/v1/traces` (US) or `https://eu.api.smith.langchain.com/otel/v1/traces` (EU) (header `x-api-key`) |

Default to self-host unless the user supplies cloud env vars. LangSmith is cloud-first — it has no localhost default.

### Step 2.6 — Write `.observent/plan.md`

Construct YAML frontmatter + anchored fenced blocks per `references/spec_schema.md § 2`. Set `spec_fingerprint` to sha256 of the live `spec.md` frontmatter. Each generated file's full content lives in exactly one fenced block; `tasks.json` will reference it via `plan#<slug>`.

---

## Phase 3 — Tasks

**Goal:** decompose `plan.md` into the ordered, mutable `.observent/tasks.json` checkpoint. No code generation here — content already lives in `plan.md`; tasks only reference it.

### Step 3.1 — Build the task array

Strict order:

1. `confirm` — render the diff preview from `plan.md`:
   - New files (paths + one-line purpose).
   - Modified files with their unified diffs.
   - `pip install` command.
   - Env vars grouped by backend (names only, never values).
   - Resolved convention.
   - Backends and endpoints (one line each).
   - Prompt: `Apply these changes? (yes / preview <file> / abort)`.
2. One `write_file` task per `files[].op == create` in `plan.files`, with `content_ref: "plan#<slug>"`.
3. One `edit_file` task per `files[].op == edit`, with `diff_ref: "plan#<slug>"`.
4. One `run_command` task for `pip_install`.
5. One `validate` task — final — calling `validate_setup.py` with the comma-separated backend list from `spec.choice.backends`.

### Step 3.2 — Write `.observent/tasks.json`

Set `plan_fingerprint` to sha256 of the live `plan.md` frontmatter. All tasks start `status: pending`, `started_at: null`, `finished_at: null`, `error: null`. See `references/spec_schema.md § 3` for the exact JSON shape.

---

## Phase 4 — Implement

**Goal:** execute the task list, mutating `tasks.json` to disk after each task. This phase is fully resumable — re-entry picks up from the first non-terminal task.

### Step 4.1 — Execute tasks in array order

For each task whose status is not terminal (`done` / `skipped`):

| `kind` | Action | On success | On failure |
|---|---|---|---|
| `confirm` | Show `payload.prompt`; wait for user. | `yes` → `done`; `no`/`abort` → `skipped` (and halt the run on `abort`) | n/a |
| `write_file` | Resolve `content_ref` against `plan.md`; `Write` the file. | `done` | `failed` with short error |
| `edit_file` | Resolve `diff_ref` against `plan.md`; apply via `Edit`. | `done` | `failed` with short error |
| `run_command` | Run via Bash. | `done` if exit 0 | `failed` |
| `validate` | Run `validate_setup.py <backend-list>` via Bash; surface output verbatim. | `done` if exit 0 | `failed`; suggest the likely cause (missing env var, unreachable endpoint, package not installed) |

After mutating any task: rewrite `tasks.json` to disk before moving to the next task. Set `started_at` when work begins, `finished_at` when it ends. On `failed`, the next invocation will offer to retry that task.

### Step 4.2 — Optional smoke test

If env vars are set and the user wants a live trace, offer to re-run `validate_setup.py` with `--smoke-test`. Each backend in the list gets its own synthetic span carrying that backend's preferred convention (OI for Phoenix, OTel-GenAI for Langfuse / SigNoz / Elastic APM / LangSmith). Phoenix / Langfuse / SigNoz / LangSmith use an `OTLPSpanExporter`; Elastic APM uses the native `elasticapm.Client` so the smoke test exercises the same agent path the generated app uses.

### Step 4.3 — Summary

Once all tasks are terminal, report back:

- Framework + backend(s) + resolved convention (`oi` / `otel-genai` / `both`).
- New files created and existing files modified (read from `plan.files`).
- `pip install` command (one line).
- Required env vars per backend (names only — user fills in values).
- UI URL per backend:
  - Phoenix local: `http://localhost:6006` · Cloud: `https://app.phoenix.arize.com`
  - Langfuse self-host: `http://localhost:3000` · Cloud: `https://cloud.langfuse.com` or `https://us.cloud.langfuse.com`
  - SigNoz self-host: `http://localhost:3301` · Cloud: `https://<tenant>.{us,eu,in}.signoz.cloud`
  - Elastic APM self-host (Kibana): `http://localhost:5601/app/apm` · Cloud: `https://<deployment>.kb.<region>.cloud.es.io/app/apm`
  - LangSmith US: `https://smith.langchain.com` · EU: `https://eu.smith.langchain.com`
- One-line next step — set the env vars, run the app, refresh each UI.

---

## Drift detection

Run these checks at the start of any phase (after the resume prompt):

| Compare | Stored in | Live source | Action on mismatch |
|---|---|---|---|
| Project deps | `spec.detection.project_fingerprint` | sha256 of `pyproject.toml` + `requirements*.txt` + `poetry.lock` (see `references/spec_schema.md § 1`) | Prompt: `Project deps changed since spec was written. Re-run /observent-spec? (yes / continue anyway / abort)` |
| Spec → Plan | `plan.spec_fingerprint` | sha256 of live `spec.md` frontmatter | Regenerate `plan.md` (forces tasks regeneration too) |
| Plan → Tasks | `tasks.plan_fingerprint` | sha256 of live `plan.md` frontmatter | Regenerate `tasks.json`, **but preserve** `status` for tasks whose `id` + `payload` are byte-identical to the prior version — so a re-plan does not re-execute completed work |

Only the **frontmatter** is fingerprinted; edits to prose body or fenced-block bodies don't trigger regeneration. Structural changes do.

---

## References

- `references/spec_schema.md` — **canonical schema** for `.observent/spec.md`, `plan.md`, `tasks.json`. The contract; this SKILL.md describes the workflow.
- `references/matrix.md` — full per-framework + per-backend matrix, OpenInference instrumentor map, span-attribute summary, context propagation patterns, multi-backend fan-out, troubleshooting, verified version pins.
- `references/openinference.md` — canonical OpenInference semantic conventions reference (Phoenix-native; used when convention=`oi` or `both`).
- `references/otel_genai.md` — canonical OTel-GenAI semantic conventions reference (Langfuse / SigNoz / Elastic APM / LangSmith; used when convention=`otel-genai` or `both`).
- `references/examples.md` — eight runnable end-to-end examples (one per framework, backends rotated) plus a multi-backend fan-out example.
- `references/fastapi_payload.md` — canonical FastAPI / Starlette middleware that captures inbound request + outbound response payloads as redacted span attributes.
- `scripts/detect_framework.py` — outputs JSON listing detected frameworks, backends, instrumentors, and web frameworks.
- `scripts/existing_setup.py` — outputs JSON listing pre-existing observability config.
- `scripts/validate_setup.py <backend|backend,backend,...|all> [--smoke-test]` — env vars, package presence, endpoint reachability, per-backend convention-aware synthetic span emission.
