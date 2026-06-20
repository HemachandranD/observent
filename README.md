<p align="center">
  <img src="assets/logo.svg" alt="observent" width="760">
</p>

<p align="center">
  Detect &rarr; Spec &rarr; Plan &rarr; Tasks &rarr; Implement &rarr; Validate &rarr; more&hellip;
</p>

# observent

A multi-provider plugin that wires up production-grade observability for multi-agent Python applications. Detects your agent framework, generates the right integration code for your chosen backend, and enforces the span attributes and context propagation patterns that actually make multi-agent traces useful.

Works with Claude Code, Google Antigravity (CLI + IDE), GitHub Copilot (CLI + IDE), OpenAI Codex (CLI + IDE), Cursor, Windsurf, and Cline.

## Why observent

Generic LLM tracing isn't enough for multi-agent apps. You need:

- **Span hierarchy** — `Crew → Agent → LLM call`, `Workflow → Step → Tool` — so the trace tree maps to your agent topology.
- **Handoff visibility** — agent-to-agent transfers (OpenAI Agents SDK, Microsoft Agent Framework) as first-class spans.
- **Identity attributes** — `agent.name`, `agent.role`, `agent.framework` on every span for filtering.
- **Session grouping** — multi-turn conversations grouped under one `session.id`.
- **Mandatory attributes** — model, provider, prompt + completion + cache tokens, tool calls, finish reasons — captured per the convention each backend prefers (OpenInference for Phoenix, OpenTelemetry GenAI for Langfuse / SigNoz / Elastic APM / LangSmith; both when fanning out across Phoenix and any of them) so cost columns aren't $0.
- **Context propagation** — across async, threads, subprocesses, and HTTP boundaries.

observent generates code that does all of this correctly the first time.

## Supported frameworks × backends

| Framework | Arize Phoenix | Langfuse | SigNoz | Elastic APM | LangSmith |
|---|:---:|:---:|:---:|:---:|:---:|
| LangGraph | ✓ | ✓ | ✓ | ✓ | ✓ |
| CrewAI | ✓ | ✓ | ✓ | ✓ | ✓ |
| Microsoft Agent Framework (`agent-framework`) | ✓ | ✓ | ✓ | ✓ | ✓ |
| Anthropic Agents SDK | ✓ | ✓ | ✓ | ✓ | ✓ |
| OpenAI Agents SDK *(native trace processor)* | ✓ | ✓ | ✓ | ✓ | ✓ |
| smolagents | ✓ | ✓ | ✓ | ✓ | ✓ |
| LlamaIndex | ✓ | ✓ | ✓ | ✓ | ✓ |
| Custom (no framework) | ✓ | ✓ | ✓ | ✓ | ✓ |

Elastic APM uses the native `elastic-apm` Python agent by default (its OTel bridge picks up the OpenInference instrumentors), giving you transaction tracing and infrastructure metrics in Kibana alongside LLM spans. LangSmith uses pure OTLP HTTP to its OTel ingest endpoint (cloud US/EU or enterprise self-host) with OTel-GenAI conventions on the wire — no `langsmith` SDK code is generated. Microsoft Agent Framework uses its built-in OpenTelemetry support — observent layers `OpenAIInstrumentor` on top for raw model-call spans. observent does not support AutoGen (v0.2 `pyautogen` or v0.4 `autogen-agentchat`) — Microsoft has unified AutoGen and Semantic Kernel into `agent-framework`; migrate to MAF or use the Custom path.

## Supported providers

| Provider | How observent runs | Install |
|---|---|---|
| **Claude Code** | Plugin — `/observent`, `/observent-detect`, `/observent-validate` slash commands. (Or skill-only via npx skills.) | `claude plugin install HemachandranD/observent` |
| **Cursor · Windsurf · Cline · GitHub Copilot · OpenAI Codex · Google Antigravity** (CLI + IDE) | The `observent` skill is loaded from the agent's own skills directory | `npx skills add HemachandranD/observent` |

> **Single source of truth:** the full workflow lives in `skills/observent/SKILL.md`, alongside its `references/` and `scripts/`. [`npx skills`](https://github.com/vercel-labs/skills) (vercel-labs/skills) copies that **self-contained** skill folder into each detected agent's skills directory (`.claude/skills/`, `.agents/skills/`, …) — auto-detecting which of 70+ coding agents you have installed. No per-tool rule files, no `AGENTS.md` mirror to keep in sync.
>
> **Claude Code gets a choice:** the native plugin (above) adds the `/observent*` slash commands; `npx skills add HemachandranD/observent -a claude-code` installs the same skill into `.claude/skills/` without the slash commands. Both run the identical workflow.

## Install

### Every agent except Claude Code's plugin — `npx skills`

```bash
npx skills add HemachandranD/observent
```

`npx skills` auto-detects the coding agents installed on your machine and copies the self-contained `observent` skill into each one's skills directory. Useful flags:

```bash
npx skills add HemachandranD/observent --list            # show the skill, don't install
npx skills add HemachandranD/observent -a cursor -a cline # target specific agents
npx skills add HemachandranD/observent -g                 # install to your home dir, not the project
npx skills add HemachandranD/observent -y                 # skip prompts
```

No environment variables to set and nothing to keep in sync — `references/` and `scripts/` travel inside the skill folder. To remove it, use `npx skills` (or delete the skill folder from the agent's skills directory).

### Claude Code (plugin)

```bash
claude plugin install HemachandranD/observent
```

Adds three slash commands: `/observent`, `/observent-detect`, `/observent-validate`. (Prefer the skill-only install? `npx skills add HemachandranD/observent -a claude-code` drops it into `.claude/skills/` instead — same workflow, no slash commands.)

---

## Usage

### Claude Code

```
/observent
/observent langgraph phoenix
/observent crewai langfuse
/observent microsoft-agent-framework signoz
/observent openai-agents phoenix
/observent anthropic-agents langfuse
/observent llama-index signoz
/observent smolagents langfuse
/observent custom phoenix
/observent microsoft-agent-framework elastic-apm
/observent langgraph langsmith

# Multi-backend fan-out — second arg accepts a comma-separated list:
/observent langgraph phoenix,signoz
/observent langgraph phoenix,langsmith
/observent crewai phoenix,langfuse,signoz,elastic-apm,langsmith

/observent-detect                                # run detectors and report what's installed
/observent-validate phoenix [--smoke-test]       # single backend
/observent-validate phoenix,signoz --smoke-test  # multi-backend
```

The convention emitted by generated code is **mechanically resolved from the chosen backend set** — Phoenix → OpenInference; Langfuse / SigNoz / Elastic APM / LangSmith → OpenTelemetry GenAI; mixed (Phoenix + at least one of Langfuse / SigNoz / Elastic APM / LangSmith) → both. There's no runtime override; to switch conventions, re-run `/observent` with a different backend(s).

### Antigravity / GitHub Copilot / Cursor / Windsurf / Cline / Codex

Ask your agent to set up observability. For example:

> "Add LLM tracing to this project with Arize Phoenix"
> "Wire up Langfuse observability for this CrewAI app"
> "Set up SigNoz monitoring for my agent"

The `observent` skill — installed into the agent's skills directory by `npx skills` — is loaded on demand and runs the full workflow from its own `SKILL.md`. This works identically from each tool's CLI and IDE.

---

The workflow observent follows:

1. Detect your framework and any pre-existing observability config.
2. Show a diff preview of the changes it will make.
3. After you approve, generate the integration code, list the `pip install` command, and produce a `.env.example`.
4. Run a validation check (and optionally emit a synthetic span to confirm end-to-end ingestion).

## What it generates

For e.g. `langgraph` + `phoenix`, you get:

- A few lines added to your entry point that initialise Phoenix and register the LangChain instrumentor.
- An `.env.example` with `PHOENIX_PROJECT_NAME` (and `PHOENIX_API_KEY` for cloud).
- A `pip install` command pinned to known-good minimum versions.
- Span attributes following the convention resolved from your backend(s) — OpenInference for Phoenix, OTel-GenAI for Langfuse / SigNoz / Elastic APM / LangSmith, both when fanning out across Phoenix and any of them.

For Elastic APM, you get the 3-line native-agent setup (`elasticapm.Client(...)` + `elasticapm.instrument()`) with the framework instrumentor on top — Kibana's APM UI then shows transaction spans, auto-instrumented infra metrics, and LLM spans together. For LangSmith, you get a pure-OTLP `OTLPSpanExporter` block parameterized by `LANGSMITH_API_KEY` (+ optional `LANGSMITH_ENDPOINT` and `LANGSMITH_PROJECT`) — no `langsmith` SDK code, so it composes cleanly into the multi-backend fan-out. For multi-backend fan-out (e.g. `phoenix,elastic-apm` or `phoenix,langsmith`), you get a single `TracerProvider` with one `BatchSpanProcessor` per OTLP backend plus the `elasticapm.Client` next to it (if Elastic is in the set); each path exports independently.

For `Custom`, it also writes an `observent_otel.py` helper with typed setters: `with_agent_span()`, `set_llm_attrs()`, `set_tool_attrs()`. The resolved convention is written into the helper as a module-level literal (`_CONVENTION = "oi"` / `"otel-genai"` / `"both"`) at generation time — no env var, no runtime override.

### Local backends

If you pick a self-host backend that isn't already running and Docker is available, observent can spin it up locally — Phoenix, Langfuse, SigNoz, and Elastic APM each get a pinned Docker stack (a generated `docker-compose.observent-<backend>.yml` for Phoenix/Elastic, a pinned upstream clone for Langfuse/SigNoz).

**It never builds or starts a container without asking — twice:**

1. **Opt-in offer.** When a chosen self-host backend is detected unreachable, observent asks `Provision it locally with Docker? (yes / no, I'll start it myself / skip)`. Decline and no Docker task is created at all.
2. **Confirm before it runs.** Even after you opt in, the exact `docker compose … up -d --wait` command (and, for Phoenix/Elastic, the full generated compose file) appears in the diff preview, and nothing runs until you approve `Apply these changes?`. For Langfuse/SigNoz the preview shows the pinned `git clone … && docker compose up` command rather than the upstream compose contents.

You also get the matching `docker compose … down` command to tear the stack back down. **LangSmith** has no free OSS/Docker edition (self-host is enterprise-licensed), so observent points you at LangSmith Cloud or your licensed `LANGSMITH_ENDPOINT` instead of provisioning it.

## Repository structure

```
.claude-plugin/
  plugin.json           # Claude Code plugin manifest
  marketplace.json      # Marketplace listing — also declares the npx-skills
                        #   discovery path: plugins[0].skills = ["./skills/observent"]
commands/
  observent.toml          # /observent [framework] [backend|backend,...]
  observent-detect.toml   # /observent-detect
  observent-validate.toml # /observent-validate <backend|backend,...> [--smoke-test]
skills/observent/         # The skill folder npx skills installs into each agent
  SKILL.md              # Skill entry point (8-step workflow)
  references/
    matrix.md           # 8×3 matrix, span attrs, context propagation
    openinference.md    # Canonical OpenInference attribute reference
    otel_genai.md       # Canonical OTel-GenAI attribute reference
    examples.md         # 8 runnable end-to-end examples
    self_host.md        # Local-provisioning Docker stacks + image pins
  scripts/
    detect_framework.py # Detects installed frameworks/backends
    validate_setup.py   # Per-backend config + connectivity check
    existing_setup.py   # Detects pre-existing observability config
.github/workflows/ci.yml
```

## Contributing

Adding a framework or backend requires updates in five places — see `CLAUDE.md` for the ordered checklist.

Adding a new **provider** generally needs no repo change: cross-tool installation is handled by [`npx skills`](https://github.com/vercel-labs/skills), which already maps 70+ coding agents to their skills directories. As long as `skills/observent/SKILL.md` stays self-contained, a newly supported agent picks it up automatically. Add a row to the Supported providers table if you want to call it out explicitly.

CI validates plugin manifests (including the `skills` → `SKILL.md` discovery link), command TOML files, script imports, SKILL.md frontmatter, lint, and type-check on Ubuntu + Windows for Python 3.10 / 3.11 / 3.12.

## License

Apache-2.0 — see [LICENSE](LICENSE) and [NOTICE](NOTICE).
