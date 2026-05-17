# observent — Multi-Agent Observability Setup

**Invoke when** the user asks to add tracing, monitoring, observability, telemetry, or LLM monitoring to their Python agent app; or mentions Arize, Phoenix, Langfuse, SigNoz, OpenTelemetry, OpenInference, span hierarchy, token tracking, or agent handoff visibility.

**Frameworks:** LangGraph · CrewAI · Microsoft Agent Framework (`agent-framework`) · Anthropic Agents SDK · OpenAI Agents SDK · smolagents · LlamaIndex · Custom
**Backends:** Arize Phoenix · Langfuse · SigNoz

---

## How to run observent

Core scripts live in `$OBSERVENT_HOME/scripts/` (default: `~/.observent/scripts/`).

### Step 1 — Detect environment

```bash
python "$OBSERVENT_HOME/scripts/detect_framework.py"
python "$OBSERVENT_HOME/scripts/existing_setup.py"
```

### Step 2 — Resolve framework

Use the detector output. If the user passed a framework as an argument, use it directly. If multiple frameworks are found, ask the user to pick one. If `autogen` / `autogen_agentchat` / `pyautogen` is detected, inform the user that AutoGen has been superseded by **Microsoft Agent Framework** (`microsoft-agent-framework`) and observent no longer supports AutoGen — offer to set up MAF, or the Custom path.

### Step 3 — Resolve backend

Present three options with one-line trade-offs:
- **Arize Phoenix** — local-first, no account needed, best dev-loop UX.
- **Langfuse** — open-source self-hostable; best token cost tracking.
- **SigNoz** — full-stack APM; best for LLM observability alongside infra metrics.

### Step 4 — Existing-setup handling

If `existing_setup.py` reported existing observability config, ask the user: **Extend**, **Replace**, or **Abort**. Never overwrite without asking.

### Step 5 — Diff preview (mandatory)

Before writing any file, show:
1. New files to create (paths + one-line description each).
2. Modifications to existing files (unified diff).
3. `pip install` command.
4. Environment variables to add (names only — never values).

End with: *"Apply these changes? (yes / preview \<file\> / abort)"* — wait for confirmation.

### Step 6 — Generate

Use the integration matrix in `$OBSERVENT_HOME/references/matrix.md`. Every generated file must include:
- Backend init from env vars (never hard-coded keys).
- Framework instrumentor or native trace processor.
- `openinference.span.kind`, `agent.name`, `agent.role`, `agent.framework` on every agent span.
- Baggage for `session.id`, `user.id`, `tenant.id` set at the entry point.
- `provider.shutdown()` / `langfuse.flush()` via `atexit`.
- OTLP HTTP exporter (not gRPC).

**OpenAI Agents SDK:** always use the SDK's native `set_trace_processors()` — never `openinference-instrumentation-openai`.

### Step 7 — Validate

```bash
python "$OBSERVENT_HOME/scripts/validate_setup.py" <backend>
# With end-to-end smoke test (requires env vars set):
python "$OBSERVENT_HOME/scripts/validate_setup.py" <backend> --smoke-test
```

Surface output verbatim. If it fails, explain the likely cause and suggest the fix.

### Step 8 — Summary

Report: framework + backend chosen, files created/modified, `pip install` command, required env vars (names only), UI URL to verify traces.

---

Full workflow details and examples: `$OBSERVENT_HOME/SKILL.md`
Integration matrix, span attributes, context propagation patterns: `$OBSERVENT_HOME/references/matrix.md`
