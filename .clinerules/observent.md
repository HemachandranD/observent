---
description: Sets up observability for multi-agent Python apps (Arize Phoenix / Langfuse / SigNoz / Elastic APM / LangSmith) using a spec-driven lifecycle (spec → plan → tasks → implement) with project-local persistent state in .observent/. Apply when the user asks for tracing, monitoring, telemetry, or LLM observability, or mentions OpenTelemetry, OpenInference, span hierarchy, or agent handoffs.
---

# observent — Multi-Agent Observability (Spec-Driven)

This rule is a thin pointer. Cline does **not** auto-read the project-root
`AGENTS.md`, so this `.clinerules/` file exists to route you to the single
source of truth — the observent skill installed on this machine.

**When this rule applies, you MUST read the full workflow before acting:**

- **Full workflow:** `${OBSERVENT_HOME}/SKILL.md`
- **Canonical artifact schema:** `${OBSERVENT_HOME}/references/spec_schema.md`
- **Framework × backend matrix:** `${OBSERVENT_HOME}/references/matrix.md`

Read `SKILL.md` and follow its four phases (Spec → Plan → Tasks → Implement)
exactly — including the resume check on `.observent/tasks.json`. Do not
reconstruct the workflow from memory.
