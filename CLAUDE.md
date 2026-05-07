# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

**bigboss** is a Claude Code plugin that wires up observability for multi-agent Python applications. It supports 8 frameworks × 3 backends (Arize Phoenix · Langfuse · SigNoz) — a full grid of 24 integration paths.

The repo *is* the plugin: skill files live under `skills/bigboss/`, plugin manifests under `.claude-plugin/`, and slash commands under `commands/`. Users install it via `claude plugin install HemachandranD/bigboss`.

## Repository Layout

```
.claude-plugin/
  plugin.json           # Claude Code plugin manifest — name, version, author
  marketplace.json      # Marketplace listing for `claude plugin install`
commands/
  bigboss.toml          # /bigboss [framework] [backend] — full setup workflow
  bigboss-detect.toml   # /bigboss-detect — run detectors and report
  bigboss-validate.toml # /bigboss-validate <backend> [--smoke-test]
skills/bigboss/
  SKILL.md              # Skill entry point — frontmatter + 8-step instructions
  reference.md          # 8×3 matrix, per-framework + per-backend reference,
                        # span attributes, context propagation, troubleshooting
  examples.md           # 8 runnable examples covering all frameworks
  scripts/
    detect_framework.py # JSON report: frameworks/backends/instrumentors detected
    validate_setup.py   # Per-backend env + reachability check; --smoke-test emits a span
    existing_setup.py   # Reports pre-existing observability config in user's project
.github/workflows/ci.yml
README.md               # Public-facing — install, usage, supported matrix
LICENSE                 # MIT
```

## Tech Stack

- **Language:** Python 3.10+ (CI matrix: 3.10 / 3.11 / 3.12 on Ubuntu + Windows).
- **Skill scripts:** zero external dependencies — only stdlib + optional dynamic imports.
- **Lint:** `ruff`.
- **Type check:** `mypy --strict`.

## Commands

```bash
# Detect frameworks/backends installed in the current project
python skills/bigboss/scripts/detect_framework.py

# Detect pre-existing observability config in the current project
python skills/bigboss/scripts/existing_setup.py

# Validate one backend's setup (env vars, packages, endpoint reachability)
python skills/bigboss/scripts/validate_setup.py phoenix
python skills/bigboss/scripts/validate_setup.py langfuse
python skills/bigboss/scripts/validate_setup.py signoz
python skills/bigboss/scripts/validate_setup.py all

# Validate AND emit one synthetic LLM span to confirm end-to-end ingestion
python skills/bigboss/scripts/validate_setup.py phoenix --smoke-test

# Lint + type-check
ruff check skills/bigboss/scripts/
mypy --strict skills/bigboss/scripts/
```

## How to Extend

### Adding a new framework

Update in this order:

1. `skills/bigboss/scripts/detect_framework.py` — add an entry to `FRAMEWORKS`.
2. `skills/bigboss/SKILL.md` — add the framework to the `argument-hint`-eligible list and the description's auto-invocation triggers.
3. `skills/bigboss/reference.md` — add a "Per-framework reference" subsection and a row to the 8×3 compatibility matrix.
4. `skills/bigboss/examples.md` — add at least one runnable example (rotate which backend it uses).
5. CI passes (frontmatter parse, imports, lint, type-check).

### Adding a new backend

Update in this order:

1. `skills/bigboss/scripts/validate_setup.py` — add a `check_<backend>()` function and register it in `CHECKS`.
2. `skills/bigboss/scripts/detect_framework.py` — add an entry to `BACKENDS`.
3. `skills/bigboss/SKILL.md` — update the description, the backend-options list, and the endpoints table.
4. `skills/bigboss/reference.md` — add a "Per-backend reference" subsection and a column to the matrix.
5. `skills/bigboss/examples.md` — add at least one example using the new backend.

### Adding a new provider

Update in this order:

1. `scripts/detect_providers.py` — add a `_<provider>()` detector function and register it in `DETECTORS`.
2. `install.sh` + `install.ps1` — add a detection block and install logic (copy adapter files, substitute `${BIGBOSS_HOME}`).
3. Provider adapter files:
   - For CLI tools with extension systems: add an extension manifest + context file (e.g., `gemini-extension.json` + `GEMINI.md`).
   - For IDE rules: add a rule file under `.<provider>/rules/` (e.g., `.cursor/rules/bigboss.mdc`).
   - Rule body must reference `${BIGBOSS_HOME}/scripts/` for script paths (substituted at install time).
4. `README.md` — add a row to the Supported providers table and document the install command.
5. CI passes (detect_providers.py smoke test, lint, type-check).

#### Which path placeholder to use

- **Claude Code plugin** (`commands/*.toml`, `skills/bigboss/SKILL.md`): use `${CLAUDE_SKILL_DIR}`. Claude Code injects this at runtime; the files are loaded directly from the cloned plugin repo, not from `BIGBOSS_HOME`.
- **All other adapters** (`GEMINI.md`, `.cursor/rules/*.mdc`, `.windsurf/rules/*.md`, `.clinerules/*.md`, `.codex/context.md`): use `${BIGBOSS_HOME}`. The installer literal-substitutes this at copy time so the rule files reference the absolute `~/.bigboss/scripts/` path on the user's machine.

Don't mix them — `${CLAUDE_SKILL_DIR}` is empty outside Claude Code, and `${BIGBOSS_HOME}` is only resolved by the installer for files it copies.

## Design Constraints

- **OTLP HTTP, not gRPC** is the default exporter for all three backends. Reasons: works through corporate proxies, smaller dep tree, Phoenix Cloud only supports HTTP.
- **OpenAI Agents SDK uses native `set_trace_processors()`**, not `openinference-instrumentation-openai`. This is non-negotiable — `-openai` loses agent structure (handoffs, runs, guardrails).
- **OpenInference + OTel GenAI both** — emit attributes for both standards where they overlap. Phoenix native consumers prefer OI; SigNoz/Langfuse work with either.
- **Mandatory attributes** — every generated template must populate model, provider, prompt+completion+total tokens, input/output messages, and (for Anthropic) cache tokens. The reference doc lists the full set per span kind.
- **Context propagation** — `start_as_current_span` (never `start_span`), Python ≥ 3.11 inherits async context, `attach()`/`detach()` for threads, `inject()` into env for subprocess, HTTPX/Requests instrumentors for cross-service.
- **Diff preview before write** — even when auto-invoked. The skill never silently modifies user code.

## Documentation Hygiene

The 8×3 matrix in `reference.md` is canonical. If you change a row or column there, mirror the change in:
- `SKILL.md` (Step 6 endpoint table, the matrix-implicit instructions)
- `README.md` (Supported matrix)
- `examples.md` (if a removed combination had an example)
