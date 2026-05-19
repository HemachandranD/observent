# observent — Multi-Agent Observability (Spec-Driven)

**Invoke when** the user asks to add tracing, monitoring, observability, telemetry, or LLM monitoring to their Python agent app; or mentions Arize, Phoenix, Langfuse, SigNoz, Elastic APM, LangSmith, OpenTelemetry, OpenInference, span hierarchy, token tracking, or agent handoff visibility.

**Frameworks (8):** LangGraph · CrewAI · Microsoft Agent Framework (`agent-framework`) · Anthropic Agents SDK · OpenAI Agents SDK · smolagents · LlamaIndex · Custom
**Backends (5):** Arize Phoenix · Langfuse · SigNoz · Elastic APM · LangSmith

---

## Lifecycle

observent runs as a spec-driven lifecycle that persists state in the **user's project** under `.observent/`:

```
.observent/spec.md     →    .observent/plan.md     →    .observent/tasks.json     →    user files
   (what & why)              (how, with content)         (checkpoint, mutable)         (executed)
```

`tasks.json` is the resume checkpoint — any task with status `pending` or `failed` means the workflow is incomplete.

**Canonical schema:** `${OBSERVENT_HOME}/references/spec_schema.md` — the contract for all three artifacts. **Full workflow:** `${OBSERVENT_HOME}/SKILL.md`.

---

## On every invocation — resume check first

1. Read `.observent/tasks.json` if it exists.
2. If any task has status `pending` or `failed`, prompt: `Found incomplete observent run. Resume from task <id> (<kind>)? (yes / restart / abort)`.
3. If absent or all-terminal, run drift checks (project / spec / plan fingerprints — see `${OBSERVENT_HOME}/SKILL.md § Drift detection`) and regenerate stale artifacts before continuing.

---

## Phase 1 — Spec

Produce `.observent/spec.md` (YAML frontmatter + free-form body per `${OBSERVENT_HOME}/references/spec_schema.md § 1`).

1. **Detect environment — run both detectors in parallel** (issue both as two terminal calls in a single turn; do not wrap in a subagent — they're deterministic JSON producers):

   ```bash
   python "${OBSERVENT_HOME}/scripts/detect_framework.py"
   python "${OBSERVENT_HOME}/scripts/existing_setup.py"
   ```

   Embed the JSON into `spec.detection`. Compute `project_fingerprint` = sha256 of `pyproject.toml` + `requirements*.txt` + `poetry.lock` (in that fixed order).

2. **Resolve framework.** Use the argument the user passed; else auto-confirm the detected one; else ask. If AutoGen is detected, redirect to **Microsoft Agent Framework** (observent no longer supports AutoGen) or the **Custom** path.

3. **Resolve backend(s)** (one or more from the 5). Then **mechanically derive the convention** — do not ask the user:

   | Backend set | Convention |
   |---|---|
   | `{phoenix}` | `oi` |
   | Any non-empty subset of `{langfuse, signoz, elastic-apm, langsmith}` (no Phoenix) | `otel-genai` |
   | Any set with Phoenix **and** at least one of `{langfuse, signoz, elastic-apm, langsmith}` | `both` |

4. **Existing-setup decision.** If existing observability is found, ask: **Extend** / **Replace** / **Abort**. Locked once chosen; not re-prompted on resume.

5. Write `spec.md` with `status: locked`.

## Phase 2 — Plan

Read `spec.md`. Using `${OBSERVENT_HOME}/references/matrix.md` (Per-framework + Per-backend), produce `.observent/plan.md` per `${OBSERVENT_HOME}/references/spec_schema.md § 2`: YAML frontmatter listing files / pip install / env vars / processors, plus the **full generated content** of every file embedded in anchored fenced blocks (`<!-- plan:<slug> -->` followed by one fenced block). Set `spec_fingerprint`. Required pieces in every `observent_otel.py` template:

- Backend init from env vars (never hard-coded keys).
- Framework instrumentor or native trace processor.
- Multi-agent attributes keyed by convention (`oi` / `otel-genai` / `both` — see `${OBSERVENT_HOME}/references/openinference.md` and `${OBSERVENT_HOME}/references/otel_genai.md`).
- Baggage (`session.id`, `user.id`, `tenant.id`, `app.version`) at the entry point.
- Flush-on-exit via `atexit`.
- OTLP **HTTP** (not gRPC).
- W3C default propagator — do not call `set_global_textmap()`.

**OpenAI Agents SDK:** always use the SDK's native `set_trace_processors()` API, never `openinference-instrumentation-openai`. **Elastic APM:** use the native `elasticapm.Client(...)` + `elasticapm.instrument()` (not OTLP); its OTel bridge picks up the framework instrumentors. **LangSmith:** pure OTLP HTTP to `${LANGSMITH_ENDPOINT}/otel/v1/traces` with `x-api-key: ${LANGSMITH_API_KEY}`. **FastAPI:** if detected, generate `observent_fastapi_payload.py` from `${OBSERVENT_HOME}/references/fastapi_payload.md`.

## Phase 3 — Tasks

Decompose `plan.md` into `.observent/tasks.json` per `${OBSERVENT_HOME}/references/spec_schema.md § 3`. Strict order:

1. `confirm` — render the diff preview (file list + diffs + pip command + env var groups + convention + endpoints); prompt: `Apply these changes? (yes / preview <file> / abort)`.
2. One `write_file` per `files[].op == create`.
3. One `edit_file` per `files[].op == edit`.
4. One `run_command` for `pip_install`.
5. One `validate` — final — calling `validate_setup.py` with the resolved backend list.

Set `plan_fingerprint`. All tasks start `status: pending`.

## Phase 4 — Implement

Execute tasks in array order. After **every** task, mutate `status` / `started_at` / `finished_at` / `error` and rewrite `tasks.json` to disk before moving on — this is the checkpoint. `kind` → action:

- `confirm` → user prompt.
- `write_file` → resolve `content_ref` against `plan.md`, create the file.
- `edit_file` → resolve `diff_ref` against `plan.md`, apply diff.
- `run_command` → run in terminal.
- `validate` → `python "${OBSERVENT_HOME}/scripts/validate_setup.py" <backend-list>`; surface output verbatim; if it fails, suggest the likely cause.

When all tasks are terminal, summarize: framework + backends + convention + files + pip install + env vars (names only) + UI URL per backend + one-line next step.

---

## Endpoints

| Backend | Self-host | Cloud |
|---|---|---|
| Phoenix | OTLP `http://localhost:6006/v1/traces` | `https://app.phoenix.arize.com/v1/traces` (Bearer `PHOENIX_API_KEY`) |
| Langfuse | OTLP `http://localhost:3000/api/public/otel/v1/traces` | `https://{us,eu}.cloud.langfuse.com/api/public/otel/v1/traces` (Basic from public+secret keys) |
| SigNoz | OTLP `http://localhost:4318/v1/traces` | `https://ingest.{us,eu,in}.signoz.cloud:443/v1/traces` (header `signoz-access-token`) |
| Elastic APM | APM Server `http://localhost:8200` (agent default) | `https://<deployment>.apm.<region>.cloud.es.io:443` (Bearer `ELASTIC_APM_SECRET_TOKEN` or ApiKey) |
| LangSmith | OTLP `${LANGSMITH_ENDPOINT}/otel/v1/traces` (enterprise self-host) | `https://api.smith.langchain.com/otel/v1/traces` (US) / `https://eu.api.smith.langchain.com/otel/v1/traces` (EU) (`x-api-key`) |

---

References:

- `${OBSERVENT_HOME}/SKILL.md` — full workflow, drift detection, phase-by-phase detail.
- `${OBSERVENT_HOME}/references/spec_schema.md` — canonical schema for `.observent/{spec.md, plan.md, tasks.json}`.
- `${OBSERVENT_HOME}/references/matrix.md` — integration matrix, span attributes, context propagation, verified version pins.
- `${OBSERVENT_HOME}/references/openinference.md` / `otel_genai.md` — canonical attribute references.
- `${OBSERVENT_HOME}/references/examples.md` — runnable end-to-end examples.
- `${OBSERVENT_HOME}/references/fastapi_payload.md` — FastAPI/Starlette payload middleware template.
