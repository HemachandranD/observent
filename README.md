# bigboss

A Claude Code skill that wires up production-grade observability for multi-agent Python applications. Detects your agent framework, generates the right integration code for your chosen backend, and enforces the span attributes and context propagation patterns that actually make multi-agent traces useful.

## Why bigboss

Generic LLM tracing isn't enough for multi-agent apps. You need:

- **Span hierarchy** — `Crew → Agent → LLM call`, `Workflow → Step → Tool` — so the trace tree maps to your agent topology.
- **Handoff visibility** — agent-to-agent transfers (OpenAI Agents SDK, AutoGen) as first-class spans.
- **Identity attributes** — `agent.name`, `agent.role`, `agent.framework` on every span for filtering.
- **Session grouping** — multi-turn conversations grouped under one `session.id`.
- **Mandatory attributes** — model, provider, prompt + completion + cache tokens, tool calls, finish reasons — captured per OpenInference and OpenTelemetry GenAI conventions so cost columns aren't $0.
- **Context propagation** — across async, threads, subprocesses, and HTTP boundaries.

bigboss generates code that does all of this correctly the first time.

## Supported

| Framework | Arize Phoenix | Langfuse | SigNoz |
|---|:---:|:---:|:---:|
| LangGraph | YES | YES | YES |
| CrewAI | YES | YES | YES |
| AutoGen v0.4 (`autogen-agentchat`) | YES | YES | YES |
| Anthropic Agents SDK | YES | YES | YES |
| OpenAI Agents SDK *(native trace processor)* | YES | YES | YES |
| smolagents | YES | YES | YES |
| LlamaIndex | YES | YES | YES |
| Custom (no framework) | YES | YES | YES |

AutoGen v0.2 (`pyautogen`) is not directly supported — use the Custom path, or upgrade to v0.4.

## Install

bigboss is a Claude Code skill. Pick one of two install scopes:

### Option A — User-global (install once, use everywhere)

**macOS / Linux:**
```bash
git clone https://github.com/HemachandranD/bigboss.git /tmp/bigboss
mkdir -p ~/.claude/skills
cp -r /tmp/bigboss/.claude/skills/bigboss ~/.claude/skills/bigboss
```

**Windows (PowerShell):**
```powershell
git clone https://github.com/HemachandranD/bigboss.git $env:TEMP\bigboss
New-Item -ItemType Directory -Force "$env:USERPROFILE\.claude\skills" | Out-Null
Copy-Item -Recurse "$env:TEMP\bigboss\.claude\skills\bigboss" "$env:USERPROFILE\.claude\skills\bigboss"
```

### Option B — Per-project (skill travels with the repo)

**macOS / Linux:**
```bash
git clone https://github.com/HemachandranD/bigboss.git /tmp/bigboss
mkdir -p .claude/skills
cp -r /tmp/bigboss/.claude/skills/bigboss .claude/skills/bigboss
```

**Windows (PowerShell):**
```powershell
git clone https://github.com/HemachandranD/bigboss.git $env:TEMP\bigboss
New-Item -ItemType Directory -Force ".claude\skills" | Out-Null
Copy-Item -Recurse "$env:TEMP\bigboss\.claude\skills\bigboss" ".claude\skills\bigboss"
```

Or as a git submodule:
```bash
git submodule add https://github.com/HemachandranD/bigboss.git .claude/skills/bigboss-src
ln -s ../bigboss-src/.claude/skills/bigboss .claude/skills/bigboss   # macOS/Linux
# Windows: New-Item -ItemType Junction -Path .\.claude\skills\bigboss -Target ...\bigboss-src\.claude\skills\bigboss
```

## Usage

In Claude Code, in your agent project:

```
/bigboss
```

Or pass the framework and backend directly:

```
/bigboss langgraph phoenix
/bigboss crewai langfuse
/bigboss autogen-agentchat signoz
/bigboss openai-agents phoenix
/bigboss anthropic-agents langfuse
/bigboss llama-index signoz
/bigboss smolagents langfuse
/bigboss custom phoenix
```

The skill will:

1. Detect your framework and any pre-existing observability config.
2. Show you a diff preview of the changes it will make.
3. After you approve, generate the integration code, list the `pip install` command, and produce a `.env.example`.
4. Run a validation check.

## What it generates

For e.g. `/bigboss langgraph phoenix`, you get:

- A few lines added to your entry point that initialise Phoenix and register the LangChain instrumentor.
- An `.env.example` with `PHOENIX_PROJECT_NAME` (and `PHOENIX_API_KEY` if you go cloud).
- A `pip install` command pinned to known-good minimum versions.
- Span attributes following OpenInference + OTel GenAI semantic conventions out of the box (no extra config).

For `Custom`, it also writes a `bigboss_otel.py` helper to your repo with typed setters: `with_agent_span()`, `set_llm_attrs()`, `set_tool_attrs()`.

## Repository structure

```
.claude/skills/bigboss/
  SKILL.md              # Skill entry point (Claude Code auto-discovers this)
  reference.md          # Per-framework + per-backend matrix, span attrs, context propagation
  examples.md           # 8 runnable end-to-end examples
  scripts/
    detect_framework.py # JSON report of detected frameworks/backends/instrumentors
    validate_setup.py   # Per-backend config and connectivity check (--smoke-test optional)
    existing_setup.py   # Detects pre-existing observability config in user's project
.github/workflows/ci.yml   # Imports + frontmatter + lint + type-check on Ubuntu/Windows
```

## Contributing

Adding a framework or backend requires updates in five places:

1. **`SKILL.md`** — add to detection table and the integration matrix.
2. **`reference.md`** — add a per-framework section, a row to the 8×3 matrix, and instrumentor map entry.
3. **`examples.md`** — add a runnable example.
4. **`scripts/detect_framework.py`** — add to `FRAMEWORKS` or `BACKENDS` dict.
5. **`scripts/validate_setup.py`** — add a `check_<backend>()` function (backends only).

CI runs imports, lint, type-check, and frontmatter validation on Ubuntu + Windows for Python 3.10 / 3.11 / 3.12.

## License

MIT — see [LICENSE](LICENSE).
