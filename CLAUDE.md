# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

**bigboss** is a Claude Code skill that wires up observability for multi-agent Python applications. It supports 8 frameworks × 3 backends (Arize Phoenix · Langfuse · SigNoz) — a full grid of 24 integration paths.

The repo *is* the skill: the skill files live under `.claude/skills/bigboss/` and users install them into their own project's `.claude/skills/` (or `~/.claude/skills/`).

## Repository Layout

```
.claude/skills/bigboss/
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
python .claude/skills/bigboss/scripts/detect_framework.py

# Detect pre-existing observability config in the current project
python .claude/skills/bigboss/scripts/existing_setup.py

# Validate one backend's setup (env vars, packages, endpoint reachability)
python .claude/skills/bigboss/scripts/validate_setup.py phoenix
python .claude/skills/bigboss/scripts/validate_setup.py langfuse
python .claude/skills/bigboss/scripts/validate_setup.py signoz
python .claude/skills/bigboss/scripts/validate_setup.py all

# Validate AND emit one synthetic LLM span to confirm end-to-end ingestion
python .claude/skills/bigboss/scripts/validate_setup.py phoenix --smoke-test

# Lint + type-check
ruff check .claude/skills/bigboss/scripts/
mypy --strict .claude/skills/bigboss/scripts/
```

## How to Extend

### Adding a new framework

Update in this order:

1. `.claude/skills/bigboss/scripts/detect_framework.py` — add an entry to `FRAMEWORKS`.
2. `.claude/skills/bigboss/SKILL.md` — add the framework to the `argument-hint`-eligible list and the description's auto-invocation triggers.
3. `.claude/skills/bigboss/reference.md` — add a "Per-framework reference" subsection and a row to the 8×3 compatibility matrix.
4. `.claude/skills/bigboss/examples.md` — add at least one runnable example (rotate which backend it uses).
5. CI passes (frontmatter parse, imports, lint, type-check).

### Adding a new backend

Update in this order:

1. `.claude/skills/bigboss/scripts/validate_setup.py` — add a `check_<backend>()` function and register it in `CHECKS`.
2. `.claude/skills/bigboss/scripts/detect_framework.py` — add an entry to `BACKENDS`.
3. `.claude/skills/bigboss/SKILL.md` — update the description, the backend-options list, and the endpoints table.
4. `.claude/skills/bigboss/reference.md` — add a "Per-backend reference" subsection and a column to the matrix.
5. `.claude/skills/bigboss/examples.md` — add at least one example using the new backend.

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
