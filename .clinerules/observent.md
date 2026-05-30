---
description: Sets up observability for multi-agent Python apps (Arize Phoenix / Langfuse / SigNoz / Elastic APM / LangSmith) using a spec-driven lifecycle (spec → plan → tasks → implement) with project-local persistent state in .observent/. Apply when the user asks for tracing, monitoring, telemetry, or LLM observability, or mentions OpenTelemetry, OpenInference, span hierarchy, or agent handoffs.
---

# observent — Multi-Agent Observability (Spec-Driven)

**Frameworks (8):** LangGraph · CrewAI · Microsoft Agent Framework · Anthropic Agents SDK · OpenAI Agents SDK · smolagents · LlamaIndex · Custom
**Backends (5):** Arize Phoenix · Langfuse · SigNoz · Elastic APM · LangSmith

## Lifecycle

observent persists state in the **user's project** under `.observent/`:

- `spec.md` — what & why (YAML frontmatter + prose).
- `plan.md` — how (YAML frontmatter + generated content in anchored fenced blocks).
- `tasks.json` — ordered, mutable checkpoint. **This is the session.** Any task with status `pending` or `failed` ⇒ workflow incomplete.

**Canonical schema:** `${OBSERVENT_HOME}/references/spec_schema.md`. **Full workflow:** `${OBSERVENT_HOME}/SKILL.md`.

## On every invocation — resume check first

1. Read `.observent/tasks.json` if present. If any task is `pending`/`failed`, prompt: `Found incomplete observent run. Resume from task <id> (<kind>)? (yes / restart / abort)`.
2. Otherwise run drift checks (project / spec / plan fingerprints — `${OBSERVENT_HOME}/SKILL.md § Drift detection`) and regenerate stale artifacts before continuing.

## Phases

1. **Spec** — Run both detectors **in parallel terminal calls** (deterministic JSON producers — do not wrap in a subagent):
   ```bash
   python "${OBSERVENT_HOME}/scripts/detect_framework.py"
   python "${OBSERVENT_HOME}/scripts/existing_setup.py"
   ```
   Resolve framework + backend(s) (1–5 from the list). Convention is **derived mechanically** from the backend set (`{phoenix}` → `oi`; non-Phoenix subset → `otel-genai`; mixed → `both`). Capture the existing-setup decision (extend / replace / abort). Write `.observent/spec.md` with `status: locked`.
2. **Plan** — Read `spec.md`. Using `${OBSERVENT_HOME}/references/matrix.md`, write `.observent/plan.md` with the full generated content of every file in anchored fenced blocks (`<!-- plan:<slug> -->`). Set `spec_fingerprint`.
3. **Tasks** — Decompose `plan.md` into `.observent/tasks.json` per the canonical schema: `confirm` (diff preview) → `write_file`(s) → `edit_file`(s) → `run_command` (pip install) → `validate` (last). Set `plan_fingerprint`. All `status: pending`.
4. **Implement** — Execute tasks in order. **After every task: mutate status / started_at / finished_at / error and rewrite tasks.json to disk** before moving on (that's what makes it resumable). Surface `validate_setup.py` output verbatim; suggest the likely cause on failure. Summarize at the end.

## Generated-code invariants

- Backend init from env vars (never hard-coded keys); framework instrumentor or native trace processor; multi-agent attrs keyed by convention; baggage (`session.id`, `user.id`, `tenant.id`); flush-on-exit via `atexit`; OTLP **HTTP** not gRPC; W3C default propagator (never call `set_global_textmap()`).
- **OpenAI Agents SDK** uses the SDK's native `set_trace_processors()` API (not `openinference-instrumentation-openai`).
- **Elastic APM** uses the native `elasticapm.Client(...)` + `elasticapm.instrument()` (its OTel bridge picks up framework instrumentors), not OTLP.
- **LangSmith** is pure OTLP HTTP to `${LANGSMITH_ENDPOINT}/otel/v1/traces` with `x-api-key: ${LANGSMITH_API_KEY}`.
- **AI-boundary capture** (always) ⇒ generate `observent_capture.py` from `${OBSERVENT_HOME}/references/capture.md`; wrap the agent invocation with `capture_run` so input/output/status are captured on the existing root span for any transport (HTTP, CLI, worker). Optional raw HTTP bodies via `observent_http.py` only when needed.

References: `${OBSERVENT_HOME}/SKILL.md` · `${OBSERVENT_HOME}/references/spec_schema.md` · `${OBSERVENT_HOME}/references/matrix.md` · `${OBSERVENT_HOME}/references/openinference.md` · `${OBSERVENT_HOME}/references/otel_genai.md` · `${OBSERVENT_HOME}/references/examples.md` · `${OBSERVENT_HOME}/references/capture.md`.
