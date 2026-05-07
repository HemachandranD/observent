# bigboss

A multi-provider plugin that wires up production-grade observability for multi-agent Python applications. Detects your agent framework, generates the right integration code for your chosen backend, and enforces the span attributes and context propagation patterns that actually make multi-agent traces useful.

Works with Claude Code, Gemini CLI, Cursor, Windsurf, Cline, and OpenAI Codex CLI.

## Why bigboss

Generic LLM tracing isn't enough for multi-agent apps. You need:

- **Span hierarchy** — `Crew → Agent → LLM call`, `Workflow → Step → Tool` — so the trace tree maps to your agent topology.
- **Handoff visibility** — agent-to-agent transfers (OpenAI Agents SDK, AutoGen) as first-class spans.
- **Identity attributes** — `agent.name`, `agent.role`, `agent.framework` on every span for filtering.
- **Session grouping** — multi-turn conversations grouped under one `session.id`.
- **Mandatory attributes** — model, provider, prompt + completion + cache tokens, tool calls, finish reasons — captured per OpenInference and OpenTelemetry GenAI conventions so cost columns aren't $0.
- **Context propagation** — across async, threads, subprocesses, and HTTP boundaries.

bigboss generates code that does all of this correctly the first time.

## Supported frameworks × backends

| Framework | Arize Phoenix | Langfuse | SigNoz |
|---|:---:|:---:|:---:|
| LangGraph | ✓ | ✓ | ✓ |
| CrewAI | ✓ | ✓ | ✓ |
| AutoGen v0.4 (`autogen-agentchat`) | ✓ | ✓ | ✓ |
| Anthropic Agents SDK | ✓ | ✓ | ✓ |
| OpenAI Agents SDK *(native trace processor)* | ✓ | ✓ | ✓ |
| smolagents | ✓ | ✓ | ✓ |
| LlamaIndex | ✓ | ✓ | ✓ |
| Custom (no framework) | ✓ | ✓ | ✓ |

AutoGen v0.2 (`pyautogen`) is not supported — use the Custom path or upgrade to v0.4.

## Supported providers

| Provider | How bigboss runs | Install method |
|---|---|---|
| **Claude Code** | Plugin — `/bigboss`, `/bigboss-detect`, `/bigboss-validate` slash commands | `claude plugin install HemachandranD/bigboss` |
| **Gemini CLI** | Extension — loaded via `GEMINI.md` context file | `gemini extensions install HemachandranD/bigboss` |
| **Cursor** | Rule — `.cursor/rules/bigboss.mdc` auto-attached to `*.py` files | `install.sh` or manual copy |
| **Windsurf** | Rule — `.windsurf/rules/bigboss.md` | `install.sh` or manual copy |
| **Cline** | Rule — `.clinerules/bigboss.md` | `install.sh` or manual copy |
| **OpenAI Codex CLI** | Extension — `.codex/context.md` injected as context | `install.sh` or manual copy |

## Install

### One-liner (all providers)

The installer detects every provider present on your system and wires up each one automatically.

**macOS / Linux:**
```bash
git clone https://github.com/HemachandranD/bigboss.git /tmp/bigboss
bash /tmp/bigboss/install.sh
```

**Windows (PowerShell):**
```powershell
git clone https://github.com/HemachandranD/bigboss.git $env:TEMP\bigboss
& "$env:TEMP\bigboss\install.ps1"
```

Both installers accept `--project-dir <path>` (where project-scoped rules are written, default `$PWD`) and `--dry-run` (preview without writing).

---

### Claude Code (plugin)

```bash
claude plugin install HemachandranD/bigboss
```

Adds three slash commands: `/bigboss`, `/bigboss-detect`, `/bigboss-validate`.

### Gemini CLI (extension)

```bash
gemini extensions install HemachandranD/bigboss
```

### Cursor / Windsurf / Cline (project-scoped rules)

Run the installer from your project root — it copies the rule file for each detected IDE into the project:

```bash
cd /your/agent/project
bash /tmp/bigboss/install.sh
```

Or copy manually:

```bash
# Cursor
mkdir -p .cursor/rules
cp /tmp/bigboss/.cursor/rules/bigboss.mdc .cursor/rules/

# Windsurf
mkdir -p .windsurf/rules
cp /tmp/bigboss/.windsurf/rules/bigboss.md .windsurf/rules/

# Cline
mkdir -p .clinerules
cp /tmp/bigboss/.clinerules/bigboss.md .clinerules/
```

Then set `BIGBOSS_HOME` to where the scripts live (default after `install.sh`: `~/.bigboss`):

```bash
export BIGBOSS_HOME="$HOME/.bigboss"   # add to ~/.bashrc or ~/.zshrc
```

### Uninstall

```bash
bash /tmp/bigboss/uninstall.sh          # macOS / Linux
& "$env:TEMP\bigboss\uninstall.ps1"    # Windows
```

---

## Usage

### Claude Code

```
/bigboss
/bigboss langgraph phoenix
/bigboss crewai langfuse
/bigboss autogen-agentchat signoz
/bigboss openai-agents phoenix
/bigboss anthropic-agents langfuse
/bigboss llama-index signoz
/bigboss smolagents langfuse
/bigboss custom phoenix

/bigboss-detect          # run detectors and report what's installed
/bigboss-validate phoenix [--smoke-test]
```

### Gemini CLI / Cursor / Windsurf / Cline / Codex

Ask your agent to set up observability. For example:

> "Add LLM tracing to this project with Arize Phoenix"
> "Wire up Langfuse observability for this CrewAI app"
> "Set up SigNoz monitoring for my agent"

The rule / context file is auto-loaded and tells the agent to run the bigboss workflow.

---

The workflow bigboss follows:

1. Detect your framework and any pre-existing observability config.
2. Show a diff preview of the changes it will make.
3. After you approve, generate the integration code, list the `pip install` command, and produce a `.env.example`.
4. Run a validation check (and optionally emit a synthetic span to confirm end-to-end ingestion).

## What it generates

For e.g. `langgraph` + `phoenix`, you get:

- A few lines added to your entry point that initialise Phoenix and register the LangChain instrumentor.
- An `.env.example` with `PHOENIX_PROJECT_NAME` (and `PHOENIX_API_KEY` for cloud).
- A `pip install` command pinned to known-good minimum versions.
- Span attributes following OpenInference + OTel GenAI semantic conventions out of the box.

For `Custom`, it also writes a `bigboss_otel.py` helper with typed setters: `with_agent_span()`, `set_llm_attrs()`, `set_tool_attrs()`.

## Repository structure

```
.claude-plugin/
  plugin.json           # Claude Code plugin manifest
  marketplace.json      # Marketplace listing
commands/
  bigboss.toml          # /bigboss [framework] [backend]
  bigboss-detect.toml   # /bigboss-detect
  bigboss-validate.toml # /bigboss-validate <backend> [--smoke-test]
skills/bigboss/
  SKILL.md              # Skill entry point (8-step workflow)
  reference.md          # 8×3 matrix, span attrs, context propagation
  examples.md           # 8 runnable end-to-end examples
  scripts/
    detect_framework.py # Detects installed frameworks/backends
    validate_setup.py   # Per-backend config + connectivity check
    existing_setup.py   # Detects pre-existing observability config
scripts/
  detect_providers.py   # Detects installed AI coding providers
gemini-extension.json   # Gemini CLI extension manifest
GEMINI.md               # Gemini context file (mirrors SKILL.md workflow)
.cursor/rules/          # Cursor rule (auto-attached to *.py)
.windsurf/rules/        # Windsurf rule
.clinerules/            # Cline rule
.codex/                 # OpenAI Codex CLI context
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

MIT — see [LICENSE](LICENSE).
