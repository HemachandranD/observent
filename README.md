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

| Provider | How observent runs | Install method |
|---|---|---|
| **Claude Code** | Plugin — `/observent`, `/observent-detect`, `/observent-validate` slash commands | `claude plugin install HemachandranD/observent` |
| **Google Antigravity** (CLI + IDE) | Extension + `AGENTS.md` context — read by both the CLI and the desktop IDE | `antigravity extensions install https://github.com/HemachandranD/observent --auto-update` |
| **GitHub Copilot** (CLI + IDE) | Instructions — `.github/copilot-instructions.md`, read by the IDE extension and Copilot CLI | `install.sh` or manual copy |
| **Cursor** | Rule — `.cursor/rules/observent.mdc` auto-attached to `*.py` files | `install.sh` or manual copy |
| **Windsurf** | Rule — `.windsurf/rules/observent.md` | `install.sh` or manual copy |
| **Cline** | Rule — `.clinerules/observent.md` | `install.sh` or manual copy |
| **OpenAI Codex** (CLI + IDE) | Extension — `.codex/context.md` for the CLI; `AGENTS.md` (shared `~/.codex/config.toml`) for the `openai.chatgpt` VS Code extension | `install.sh` or manual copy |

> **Note:** Google replaced **Gemini CLI** with **Antigravity** (May 2026; Gemini CLI's consumer tiers sunset 2026-06-18). observent ships a single cross-tool `AGENTS.md`, which Antigravity reads natively from both the CLI and the IDE.

## Install

### One-liner (all providers)

The installer detects every provider present on your system and wires up each one automatically.

**macOS / Linux:**
```bash
git clone https://github.com/HemachandranD/observent.git /tmp/observent
bash /tmp/observent/install.sh
```

**Windows (PowerShell):**
```powershell
git clone https://github.com/HemachandranD/observent.git $env:TEMP\observent
& "$env:TEMP\observent\install.ps1"
```

Both installers accept `--project-dir <path>` (where project-scoped rules are written, default `$PWD`) and `--dry-run` (preview without writing).

---

### Claude Code (plugin)

```bash
claude plugin install HemachandranD/observent
```

Adds three slash commands: `/observent`, `/observent-detect`, `/observent-validate`.

### Google Antigravity (extension — CLI + IDE)

```bash
antigravity extensions install https://github.com/HemachandranD/observent --auto-update
```

The installer also drops an `AGENTS.md` into your project root, which both the Antigravity CLI and the desktop IDE read automatically.

### OpenAI Codex (extension — CLI + IDE)

The installer wires up both surfaces. To do it manually:

```bash
# CLI: load the context extension from ~/.codex/extensions/
mkdir -p ~/.codex/extensions/observent
cp -r /tmp/observent/.codex/. ~/.codex/extensions/observent/

# IDE (openai.chatgpt VS Code extension): reads AGENTS.md from the project root
cp /tmp/observent/AGENTS.md ./AGENTS.md
```

The CLI loads `.codex/context.md`; the VS Code extension shares `~/.codex/config.toml` with the CLI and reads the project-root `AGENTS.md`. Both surfaces then run the same observent workflow.

### Cursor / Windsurf / Cline / GitHub Copilot (project-scoped rules)

Run the installer from your project root — it copies the rule / instructions file for each detected IDE into the project:

```bash
cd /your/agent/project
bash /tmp/observent/install.sh
```

Or copy manually:

```bash
# Cursor
mkdir -p .cursor/rules
cp /tmp/observent/.cursor/rules/observent.mdc .cursor/rules/

# Windsurf
mkdir -p .windsurf/rules
cp /tmp/observent/.windsurf/rules/observent.md .windsurf/rules/

# Cline
mkdir -p .clinerules
cp /tmp/observent/.clinerules/observent.md .clinerules/

# GitHub Copilot (IDE + CLI)
mkdir -p .github
cp /tmp/observent/.github/copilot-instructions.md .github/
```

Then set `OBSERVENT_HOME` to where the scripts live (default after `install.sh`: `~/.observent`):

```bash
export OBSERVENT_HOME="$HOME/.observent"   # add to ~/.bashrc or ~/.zshrc
```

### Uninstall

```bash
bash /tmp/observent/uninstall.sh          # macOS / Linux
& "$env:TEMP\observent\uninstall.ps1"    # Windows
```

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

The rule / instructions / context file is auto-loaded and tells the agent to run the observent workflow. For Antigravity and GitHub Copilot this works identically from both the CLI and the IDE.

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
  marketplace.json      # Marketplace listing
commands/
  observent.toml          # /observent [framework] [backend|backend,...]
  observent-detect.toml   # /observent-detect
  observent-validate.toml # /observent-validate <backend|backend,...> [--smoke-test]
skills/observent/
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
scripts/
  detect_providers.py        # Detects installed AI coding providers
antigravity-extension.json   # Antigravity extension manifest (ex-Gemini)
AGENTS.md                    # Cross-tool context (Antigravity / Copilot / Codex / Cursor / Claude Code; mirrors SKILL.md workflow)
.github/copilot-instructions.md  # GitHub Copilot instructions (IDE + CLI)
.cursor/rules/               # Cursor rule (auto-attached to *.py)
.windsurf/rules/             # Windsurf rule
.clinerules/                 # Cline rule
.codex/                      # OpenAI Codex CLI context (IDE uses AGENTS.md)
install.sh              # Cross-platform installer (bash)
install.ps1             # Cross-platform installer (PowerShell)
uninstall.sh / .ps1     # Uninstallers
.github/workflows/ci.yml
```

## Contributing

Adding a framework or backend requires updates in five places — see `CLAUDE.md` for the ordered checklist.

Adding a provider requires updates in four places:

1. `scripts/detect_providers.py` — add a `_<provider>()` detector function.
2. `install.sh` + `install.ps1` — add detection + install block.
3. Provider adapter files (rule / context / extension manifest).
4. `README.md` — add a row to the Supported providers table.

CI validates plugin manifests, command TOML files, script imports, SKILL.md frontmatter, lint, and type-check on Ubuntu + Windows for Python 3.10 / 3.11 / 3.12.

## License

Apache-2.0 — see [LICENSE](LICENSE) and [NOTICE](NOTICE).
