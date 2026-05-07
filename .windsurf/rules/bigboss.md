# bigboss — Multi-Agent Observability Setup

**Invoke when** the user asks to add tracing, monitoring, observability, telemetry, or LLM monitoring to their Python agent app; or mentions Arize, Phoenix, Langfuse, SigNoz, OpenTelemetry, OpenInference, span hierarchy, token tracking, or agent handoff visibility.

**Frameworks:** LangGraph · CrewAI · AutoGen v0.4 · Anthropic Agents SDK · OpenAI Agents SDK · smolagents · LlamaIndex · Custom
**Backends:** Arize Phoenix · Langfuse · SigNoz

## How to run

Scripts are in `${BIGBOSS_HOME}/scripts/` (default: `~/.bigboss/scripts/`).

1. Run in the terminal:
   ```bash
   python "${BIGBOSS_HOME}/scripts/detect_framework.py"
   python "${BIGBOSS_HOME}/scripts/existing_setup.py"
   ```
2. Resolve framework and backend — confirm with the user if ambiguous.
3. **Always show a diff preview** of all changes before writing any files.
4. Generate code using the integration matrix in `${BIGBOSS_HOME}/reference.md`.
5. After writing, validate:
   ```bash
   python "${BIGBOSS_HOME}/scripts/validate_setup.py" <backend>
   ```

Full workflow: `${BIGBOSS_HOME}/SKILL.md` — Integration matrix + span attributes: `${BIGBOSS_HOME}/reference.md`
