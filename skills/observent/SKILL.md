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

Run both detectors **in parallel** — they're independent deterministic scripts that emit JSON, so issue them as two Bash tool calls in a **single message**, not sequentially. Both scripts ship in this skill's own `scripts/` directory (beside `SKILL.md`); resolve that directory to an absolute path (see note below) and run:

- `python "<skill-dir>/scripts/detect_framework.py"`
- `python "<skill-dir>/scripts/existing_setup.py"`

> **Resolving `<skill-dir>`.** `<skill-dir>` is the folder this `SKILL.md` was loaded from — its `scripts/` and `references/` subfolders ship *inside* the skill, so the path is always relative to the skill, never to the user's project cwd.
> - **In Claude Code**, substitute the built-in `${CLAUDE_SKILL_DIR}` variable — e.g. `python "${CLAUDE_SKILL_DIR}/scripts/detect_framework.py"`. (This is the only place that variable applies; it resolves automatically.)
> - **Every other agent** (Cursor, Copilot, Codex, Cline, Windsurf, …) receives the same self-contained folder via `npx skills` and has **no** `${CLAUDE_SKILL_DIR}` variable. Use the absolute path of the skill folder you loaded `SKILL.md` from — the exact directory varies by agent (project-level `.agents/skills/observent/` for many CLIs; a global dir such as `~/.cursor/skills/observent/`, `~/.codeium/windsurf/skills/observent/`, or `~/.config/<agent>/skills/observent/` when installed with `-g`). Same `scripts/` + `references/` layout either way.

Do **not** wrap either script in a subagent — they're already deterministic; an LLM in the middle adds latency and nondeterminism without saving context. The JSON output goes straight into `spec.detection`. `detect_framework.py` also reports a `docker` block (`{available, compose_available}`) — capture it into `spec.detection.docker_available` / `docker_compose_available` for the provisioning offer in Step 1.6.

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

### Step 1.5 — Local provisioning offer

For each backend whose resolved `endpoints.<backend>.mode == self-host`, probe the endpoint and record reachability in `spec.detection.backends_reachable.<backend>`. When a self-host backend is **unreachable**:

- **Backend ∈ {phoenix, langfuse, signoz, elastic-apm} and Docker available** (`detection.docker_available && detection.docker_compose_available`): ask
  `<backend> isn't reachable at <url>. Provision it locally with Docker? (yes / no, I'll start it myself / skip)`.
  On `yes` set `spec.choice.self_host_provision.<backend> = true`; otherwise `false`.
- **Docker not available**: state that and skip the offer (set `false`). For Phoenix, mention the `px.launch_app()` in-process alternative. The final `validate` will still report the backend as unreachable.
- **Backend == langsmith**: never offer Docker — surface the enterprise-license note from `references/self_host.md § LangSmith` and keep it cloud-first. `self_host_provision` gets no `langsmith` key.

Templates and pinned image tags are **not** decided here — they live in `references/self_host.md` and are materialized in Phase 2. This step only records the decision. Reachable backends and cloud-mode backends get no `self_host_provision` entry.

### Step 1.6 — Write `.observent/spec.md`

Construct the YAML frontmatter per `references/spec_schema.md § 1`. Compute `detection.project_fingerprint` from `pyproject.toml` + `requirements*.txt` + `poetry.lock` (see schema for exact ordering). Write the file; set `status: locked` once the user has confirmed the choices in Steps 1.2–1.5. Preserve any existing prose body on re-runs.

---

## Phase 2 — Plan

**Goal:** read `spec.md` and produce `.observent/plan.md` with the full generated content embedded in fenced blocks behind anchor comments. Deterministic from spec — no user questions in this phase except the diff-preview confirm in Phase 4.

### Step 2.1 — Decide structure

Using `references/matrix.md` (sections **Per-framework** and **Per-backend**), determine:

- **Files to generate** — typically:
  - `observent_otel.py` (always — backend init + framework instrumentation).
  - `observent_capture.py` (always — transport-agnostic input/output/status capture at the AI boundary; see `references/capture.md`).
  - `observent_http.py` (only if `spec.choice.http_body_capture: true` — optional raw HTTP body/header capture; enriches the existing server span, adds no span).
  - Edits to the user's entry-point file (e.g., `main.py`) to import `observent_otel`, wrap the agent invocation with `capture_run`, and (if applicable) register the HTTP middleware.
  - `.env` append with required env var names.
- **Multi-backend processor list** — one `BatchSpanProcessor(OTLPSpanExporter(...))` per OTLP backend in `spec.choice.backends` (Phoenix, Langfuse, SigNoz, LangSmith). Elastic APM in native-agent mode is **not** a processor — set `elastic_apm_native_agent: true` and instantiate `elasticapm.Client(...)` + `elasticapm.instrument()` next to the TracerProvider.
- **OpenAI Agents SDK** — if `spec.choice.framework == openai-agents`, set `openai_agents_native_processors: true` and use the SDK's native `set_trace_processors()` API, not `openinference-instrumentation-openai`. This is non-negotiable.
- **Pinned versions** — copy exact `==X.Y.Z` pins from `references/matrix.md § Verified Versions` into the `pip_install` line.
- **Local provisioning** — for each backend with `spec.choice.self_host_provision.<backend> == true`, materialize the chosen stack from `references/self_host.md` into a `plan.provision[]` entry:
  - `method: vendored-compose` (Phoenix, Elastic APM) → add a `files[]` create entry for `docker-compose.observent-<backend>.yml`, copy the pinned compose template into a `<!-- plan:compose_<backend> -->` anchor, and set `up_command`/`down_command` to the `docker compose -f … up -d --wait` / `down` lines.
  - `method: upstream-clone` (Langfuse, SigNoz) → no compose file; set `up_command` to the pinned `git clone … && docker compose -f … up -d --wait` line from `self_host.md` (no `<!-- plan:compose_* -->` anchor).
  Copy image tags **verbatim** from `references/self_host.md § Image Versions` — never invent versions. When `self_host_provision` is empty, `plan.provision` is `[]`.

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

### Step 2.3 — AI-boundary input/output/status capture

observent's prime directive is **never miss any input or output that crosses the AI-system boundary**, regardless of how the agent is triggered (HTTP, CLI, queue worker, cron, notebook). This capture is **transport-agnostic** and is generated for **every** framework — not just web apps.

- **Always** generate `observent_capture.py` from the canonical engine in `references/capture.md` and wrap the agent invocation with `capture_run` / `capture_run_async` (or call `enrich_current_span(...)` + `capture_output(...)` directly). See `references/capture.md § Per-framework wrap points` for where each framework's invoke call sits.
- **Enrich in place, never duplicate the root span.** The engine writes `input.*` / `output.*` / status onto the span that is **already recording** (the framework instrumentor's root span, or the HTTP server span). It opens its own `agent.run` span **only** as a fallback when nothing is recording (e.g. a bare CLI), so input is never lost. Do not add a second observent root span when one already exists.
- **Span status is set at the AI boundary** by the engine: `StatusCode.OK` on success; `record_exception()` + `StatusCode.ERROR` + `error.type` on failure. Status no longer depends on whether a transport instrumentor happens to be present.
- Sensitive keys (auth credentials, session/CSRF, PII) are redacted at the value level (key preserved so the attribute shape is stable); a baggage whitelist promotes correlation keys onto child spans. Both are **generation-time literals** in the generated file — same rule as `_CONVENTION`. No truncation.
- **Optional raw HTTP capture** — only if `spec.choice.http_body_capture: true`, also generate `observent_http.py` (an ASGI middleware that enriches the **existing** server span with `http.request.*` / `http.response.*`; adds no span, does not buffer streaming responses). Generate this only when the agent's logical input — already captured by `capture_run` — is insufficient and the raw wire payload (a header/envelope field) is also needed.

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
   - Any locally provisioned stacks: the compose file (`vendored-compose`) or clone target (`upstream-clone`) and the `docker compose … up` command, one line each, from `plan.provision[]`.
   - Prompt: `Apply these changes? (yes / preview <file> / abort)`.
2. One `write_file` task per `files[].op == create` in `plan.files`, with `content_ref: "plan#<slug>"` (this includes any `vendored-compose` `docker-compose.observent-<backend>.yml`).
3. One `edit_file` task per `files[].op == edit`, with `diff_ref: "plan#<slug>"`.
4. One `run_command` task for `pip_install`.
5. One `run_command` task per `plan.provision[]` entry, with `cmd` set to that entry's `up_command` (`docker compose … up -d --wait`, or the pinned clone+up for `upstream-clone`). These come **after** pip-install and **before** `validate` so the endpoint is live when validation runs.
6. One `validate` task — final — calling `<skill-dir>/scripts/validate_setup.py` (resolve `<skill-dir>` as in Step 1.1) with the comma-separated backend list from `spec.choice.backends`.

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
| `validate` | Run `<skill-dir>/scripts/validate_setup.py <backend-list>` via Bash (resolve `<skill-dir>` as in Step 1.1); surface output verbatim. | `done` if exit 0 | `failed`; suggest the likely cause (missing env var, unreachable endpoint, package not installed) |

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
  - SigNoz self-host: `http://localhost:8080` (recent unified image; older releases `3301`) · Cloud: `https://<tenant>.{us,eu,in}.signoz.cloud`
  - Elastic APM self-host (Kibana): `http://localhost:5601/app/apm` · Cloud: `https://<deployment>.kb.<region>.cloud.es.io/app/apm`
  - LangSmith US: `https://smith.langchain.com` · EU: `https://eu.smith.langchain.com`
- For any locally provisioned stack (from `plan.provision[]`): note that it's now running under Docker and give the matching `down_command` to stop it (e.g. `docker compose -f docker-compose.observent-phoenix.yml down`).
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
- `references/capture.md` — canonical transport-agnostic engine (`observent_capture.py`) that captures AI-boundary input/output + run status by enriching the existing root span, plus the optional `observent_http.py` raw-HTTP-body adapter.
- `references/self_host.md` — canonical local-provisioning reference: pinned Docker compose templates / clone commands per self-hostable backend (Phoenix · Langfuse · SigNoz · Elastic APM), the LangSmith "not provisioned" note, and the image-tag pin table. Consumed by Phase 1 § 1.5 and Phase 2 § 2.1.
- `scripts/detect_framework.py` — outputs JSON listing detected frameworks, backends, instrumentors, and web frameworks.
- `scripts/existing_setup.py` — outputs JSON listing pre-existing observability config.
- `scripts/validate_setup.py <backend|backend,backend,...|all> [--smoke-test]` — env vars, package presence, endpoint reachability, per-backend convention-aware synthetic span emission.
