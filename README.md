<p align="center">
  <img src="assets/logo.svg" alt="observent" width="760">
</p>

<p align="center">
  <b>Production-grade observability for multi-agent Python apps — in one command.</b>
</p>

<p align="center">
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-Apache--2.0-blue.svg" alt="License: Apache-2.0"></a>
  <img src="https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12%20%7C%203.13%20%7C%203.14-blue.svg" alt="Python 3.10–3.14">
  <a href=".github/workflows/ci.yml"><img src="https://github.com/HemachandranD/observent/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <img src="https://img.shields.io/badge/agents-Claude%20Code%20%2B%2070%2B%20via%20npx%20skills-CC785C.svg" alt="Works in 70+ agents">
</p>

[![skills.sh](https://skills.sh/b/hemachandrand/observent)](https://skills.sh/hemachandrand/observent)

---

**observent** sets up observability for multi-agent Python applications across **8 frameworks x 5 backends**.

It detects your framework, generates integration code for the backend(s) you pick, previews every change before write, and validates ingestion (optionally with a smoke span).

An optional **Evaluate** step then turns that telemetry into a deterministic, offline CI quality gate — assert token / latency / behavior budgets (and catch PII leaks or regressions) straight from captured spans, no backend required.

## Quickstart

### Claude Code plugin (with `/observent*` slash commands)

```bash
claude plugin marketplace add HemachandranD/observent
claude plugin install observent@observent
```

Run:

```text
/observent
```

### All coding agents via `npx skills` (Cursor, Codex, Copilot, Windsurf, Cline, OpenCode, and more)

```bash
npx skills add HemachandranD/observent
```

Then ask your agent:

> "Set up Arize Phoenix tracing for this LangGraph project."

---

## Commands at a glance

### Claude Code

```text
/observent [framework] [backend|backend,...]
/observent-spec
/observent-plan
/observent-tasks
/observent-implement
/observent-detect
/observent-validate <backend|backend,...> [--smoke-test]
/observent-eval [--baseline] [--ci]
```

Examples:

```text
/observent langgraph phoenix
/observent crewai langfuse
/observent microsoft-agent-framework signoz
/observent openai-agents phoenix
/observent anthropic-agents langfuse
/observent llama-index signoz
/observent smolagents langfuse
/observent custom phoenix
/observent langgraph phoenix,signoz
/observent crewai phoenix,langfuse,signoz,elastic-apm,langsmith
```

### `npx skills` install options

| Flag | Effect |
|---|---|
| `--list` | Show detected install targets without installing |
| `-a <agent>` | Target specific agents (`-a cursor -a cline`) |
| `-g` | Install in home directory |
| `-y` | Skip prompts |

Use without install:

```bash
npx skills use HemachandranD/observent | claude
npx skills use HemachandranD/observent --skill observent --agent claude-code
```

---

## Convention resolution (automatic)

The generated convention is derived mechanically from selected backend(s):

| Selected backend set | Convention emitted |
|---|---|
| `phoenix` only | OpenInference |
| Any non-empty subset of `langfuse`, `signoz`, `elastic-apm`, `langsmith` (without Phoenix) | OTel-GenAI |
| `phoenix` + at least one of `langfuse`, `signoz`, `elastic-apm`, `langsmith` | Both |

There is no runtime override flag; to change conventions, re-run with a different backend set.

---

## Supported frameworks x backends

| Framework | Arize Phoenix | Langfuse | SigNoz | Elastic APM | LangSmith |
|---|:---:|:---:|:---:|:---:|:---:|
| LangGraph | ✓ | ✓ | ✓ | ✓ | ✓ |
| CrewAI | ✓ | ✓ | ✓ | ✓ | ✓ |
| Microsoft Agent Framework | ✓ | ✓ | ✓ | ✓ | ✓ |
| Anthropic Agents SDK | ✓ | ✓ | ✓ | ✓ | ✓ |
| OpenAI Agents SDK | ✓ | ✓ | ✓ | ✓ | ✓ |
| smolagents | ✓ | ✓ | ✓ | ✓ | ✓ |
| LlamaIndex | ✓ | ✓ | ✓ | ✓ | ✓ |
| Custom | ✓ | ✓ | ✓ | ✓ | ✓ |

Implementation notes:
- **Elastic APM** defaults to the native `elastic-apm` Python agent (`elasticapm.Client(...)` + `elasticapm.instrument()`), with framework instrumentors layered on top.
- **LangSmith** uses OTLP HTTP ingest with OTel-GenAI conventions; no generated `langsmith` SDK code.
- **OpenAI Agents SDK** integration uses native trace processors (not `openinference-instrumentation-openai`) so agent structure stays intact.
- **Microsoft Agent Framework** uses built-in OpenTelemetry support with `OpenAIInstrumentor` layered for raw model spans.

---

## Works with any model provider

observent instruments the LLM call path, so model vendor choice is orthogonal to the 8x5 matrix.

OpenAI-compatible endpoints work directly with the standard `openai` client:

| Provider | `base_url` | Key |
|---|---|---|
| OpenRouter | `https://openrouter.ai/api/v1` | `OPENROUTER_API_KEY` |
| Ollama (local) | `http://localhost:11434/v1` | none (placeholder) |
| HuggingFace router | `https://router.huggingface.co/v1` | `HF_TOKEN` |

If you use a non-OpenAI-compatible native SDK, use the Custom path to emit spans manually.

---

## Local self-host provisioning

For unreachable self-host backends (**Phoenix, Langfuse, SigNoz, Elastic APM**), observent can offer Docker-based provisioning.

Provisioning is always explicit:
1. opt-in prompt,
2. command/file preview in diff,
3. confirm before run.

LangSmith is not auto-provisioned (no free OSS Docker edition).

---

## Supported providers

| Provider | How observent runs | Install |
|---|---|---|
| Claude Code | Native plugin with `/observent*` slash commands (or skill-only via `npx skills`) | `claude plugin marketplace add HemachandranD/observent` then `claude plugin install observent@observent` |
| Cursor, Windsurf, Cline, GitHub Copilot, OpenAI Codex, Google Antigravity (CLI + IDE) | Skill loaded from each agent's skills directory | `npx skills add HemachandranD/observent` |

`npx skills` supports 70+ agents. See the canonical list in [vercel-labs/skills](https://github.com/vercel-labs/skills#supported-agents).

---

## For agents (scrape-friendly metadata)

```yaml
name: observent
repo: HemachandranD/observent
language: python
python_versions: ["3.10", "3.11", "3.12", "3.13", "3.14"]
frameworks:
  - langgraph
  - crewai
  - microsoft-agent-framework
  - anthropic-agents
  - openai-agents
  - smolagents
  - llama-index
  - custom
backends:
  - phoenix
  - langfuse
  - signoz
  - elastic-apm
  - langsmith
primary_entrypoint: "/observent [framework] [backend|backend,...]"
validate_entrypoint: "/observent-validate <backend|backend,...> [--smoke-test]"
eval_entrypoint: "/observent-eval [--baseline] [--ci]"
convention_rules:
  - "phoenix only => openinference"
  - "langfuse/signoz/elastic-apm/langsmith without phoenix => otel-genai"
  - "phoenix with any non-phoenix backend => both"
docs:
  matrix: "skills/observent/references/matrix.md"
  examples: "skills/observent/references/examples.md"
  self_host: "skills/observent/references/self_host.md"
```

---

## Repository structure

```text
.claude-plugin/
  plugin.json
  marketplace.json
commands/
  observent.toml
  observent-spec.toml
  observent-plan.toml
  observent-tasks.toml
  observent-implement.toml
  observent-detect.toml
  observent-validate.toml
  observent-eval.toml
skills/observent/
  SKILL.md
  references/
    matrix.md
    openinference.md
    otel_genai.md
    examples.md
    self_host.md
    eval.md
  scripts/
    observent_matrix.py
    detect_framework.py
    validate_setup.py
    existing_setup.py
    eval_gate.py
.github/workflows/ci.yml
```

---

## Contributing

Adding a framework or backend uses an ordered checklist in `CLAUDE.md`.

Run locally:

```bash
pytest
ruff check skills/observent/scripts/ tests/
mypy skills/observent/scripts/
```

---

## License

Apache-2.0. See [LICENSE](LICENSE) and [NOTICE](NOTICE).
