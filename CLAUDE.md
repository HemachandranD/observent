# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

**observent** is a Claude Code plugin that wires up observability for multi-agent Python applications. It supports 8 frameworks × 5 backends (Arize Phoenix · Langfuse · SigNoz · Elastic APM · LangSmith) — a full grid of 40 integration paths.

The repo *is* the plugin: skill files live under `skills/observent/`, plugin manifests under `.claude-plugin/`, and slash commands under `commands/`. Users install it via `claude plugin install HemachandranD/observent`.

## Repository Layout

```
.claude-plugin/
  plugin.json           # Claude Code plugin manifest — name, version, author
  marketplace.json      # Marketplace listing for `claude plugin install`
commands/
  observent.toml            # /observent [framework] [backend|backend,...] — full SDD lifecycle (spec→plan→tasks→implement) with resume
  observent-spec.toml       # /observent-spec — produce .observent/spec.md only
  observent-plan.toml       # /observent-plan — produce .observent/plan.md from spec.md
  observent-tasks.toml      # /observent-tasks — decompose plan.md into .observent/tasks.json
  observent-implement.toml  # /observent-implement — execute (or resume) tasks.json
  observent-detect.toml     # /observent-detect — run detectors and report
  observent-validate.toml   # /observent-validate <backend|backend,...> [--smoke-test]
skills/observent/
  SKILL.md              # Skill entry point — frontmatter + 4-phase SDD workflow (Spec / Plan / Tasks / Implement)
  references/
    spec_schema.md      # Canonical schema for the three .observent/ artifacts (spec.md, plan.md, tasks.json)
    matrix.md           # 8×5 matrix, per-framework + per-backend reference,
                        # span attribute summary, context propagation, troubleshooting
    openinference.md    # Canonical OpenInference attribute reference (Phoenix path)
    otel_genai.md       # Canonical OTel-GenAI attribute reference (Langfuse / SigNoz / Elastic APM / LangSmith path)
    examples.md         # 8 runnable examples covering all frameworks + multi-backend fan-out
    self_host.md        # local-provisioning reference: pinned Docker compose / clone commands
                        # per self-hostable backend + image-tag pin table
  scripts/
    detect_framework.py # JSON report: frameworks/backends/instrumentors detected
    validate_setup.py   # Per-backend env + reachability check; --smoke-test emits a span
    existing_setup.py   # Reports pre-existing observability config in user's project
.github/workflows/ci.yml
README.md               # Public-facing — install, usage, supported matrix
LICENSE                 # MIT
```

**Note on `.observent/`:** the skill's three persisted artifacts (`spec.md`, `plan.md`, `tasks.json`) live in the **user's project**, not this repo — they are created by `/observent-spec` on first run in whatever project the user is instrumenting. Do not commit a `.observent/` directory into this plugin repo. See `skills/observent/references/spec_schema.md` for the canonical artifact schemas.

## Tech Stack

- **Language:** Python 3.10+ (CI matrix: 3.10 / 3.11 / 3.12 on Ubuntu + Windows).
- **Skill scripts:** zero external dependencies — only stdlib + optional dynamic imports.
- **Lint:** `ruff`.
- **Type check:** `mypy --strict`.

## Commands

```bash
# Detect frameworks/backends installed in the current project
python skills/observent/scripts/detect_framework.py

# Detect pre-existing observability config in the current project
python skills/observent/scripts/existing_setup.py

# Validate one backend's setup (env vars, packages, endpoint reachability)
python skills/observent/scripts/validate_setup.py phoenix
python skills/observent/scripts/validate_setup.py langfuse
python skills/observent/scripts/validate_setup.py signoz
python skills/observent/scripts/validate_setup.py elastic-apm
python skills/observent/scripts/validate_setup.py langsmith
python skills/observent/scripts/validate_setup.py all

# Validate multiple backends (multi-backend fan-out — comma-separated)
python skills/observent/scripts/validate_setup.py phoenix,signoz
python skills/observent/scripts/validate_setup.py phoenix,langsmith
python skills/observent/scripts/validate_setup.py phoenix,langfuse,signoz,elastic-apm,langsmith

# Validate AND emit one synthetic LLM span per backend (using each backend's preferred convention)
python skills/observent/scripts/validate_setup.py phoenix --smoke-test
python skills/observent/scripts/validate_setup.py phoenix,langsmith --smoke-test

# Lint + type-check
ruff check skills/observent/scripts/
mypy --strict skills/observent/scripts/
```

## How to Extend

> **Schema generality:** the spec / plan / tasks artifacts (`skills/observent/references/spec_schema.md`) are generic over framework and backend *strings* — adding a new framework or backend does **not** require schema edits. Only the matrix and detector entries below need updating; the skill picks up the new option via those.

### Adding a new framework

Update in this order:

1. `skills/observent/scripts/detect_framework.py` — add an entry to `FRAMEWORKS`.
2. `skills/observent/SKILL.md` — add the framework to the `argument-hint`-eligible list in Phase 1 § Step 1.2 and the description's auto-invocation triggers.
3. `skills/observent/references/matrix.md` — add a "Per-framework reference" subsection and a row to the 8×3 compatibility matrix.
4. `skills/observent/references/examples.md` — add at least one runnable example (rotate which backend it uses) and stamp it with a `*Last verified: YYYY-MM-DD with Python X.Y.*` footer.
5. `skills/observent/references/matrix.md` § Verified Versions — add a row for the new framework + instrumentor packages with the exact installed version (`==X.Y.Z`, sourced from the package's PyPI page or `pip show`), and bump the table's "Last verified" date to today. Mirror the same `==` pin in the per-framework `pip install` snippet you added in step 3.
6. CI passes (frontmatter parse, imports, lint, type-check).

### Adding a new backend

Update in this order:

1. `skills/observent/scripts/validate_setup.py` — add a `check_<backend>()` function and register it in `CHECKS`.
2. `skills/observent/scripts/detect_framework.py` — add an entry to `BACKENDS`.
3. `skills/observent/SKILL.md` — update the description, the backend-options list in Phase 1 § Step 1.3, the convention-derivation table (if applicable), and the endpoints table in Phase 2 § Step 2.5.
4. `skills/observent/references/matrix.md` — add a "Per-backend reference" subsection and a column to the matrix.
5. `skills/observent/references/examples.md` — add at least one example using the new backend, with a `*Last verified: YYYY-MM-DD with Python X.Y.*` footer.
6. `skills/observent/references/matrix.md` § Verified Versions — add a row for the backend's required package(s) with the exact installed version (`==X.Y.Z`, sourced from the package's PyPI page or `pip show`), and bump the table's "Last verified" date to today. Mirror the same `==` pin in the per-backend Install line you added in step 4.
7. **If the backend is self-hostable:** `skills/observent/references/self_host.md` — add a provisioning section (choose `vendored-compose` for a self-contained stack or `upstream-clone` when the stack needs repo-mounted config files), add a row to the § Image Versions table with the exact image tag(s), and bump that table's "Last verified" date. Add the backend to the `{phoenix, langfuse, signoz, elastic-apm}` provisionable set referenced in `SKILL.md` Phase 1 § 1.5. If it has **no** free self-host edition (like LangSmith), instead document it under the "not provisioned" note and leave it out of the provisionable set.

### Adding a new provider

Update in this order:

1. `scripts/detect_providers.py` — add a `_<provider>()` detector function and register it in `DETECTORS`.
2. `install.sh` + `install.ps1` — add a detection block and install logic (copy adapter files, substitute `${OBSERVENT_HOME}`).
3. Provider adapter files:
   - For CLI tools with extension systems: add an extension manifest + context file (e.g., `gemini-extension.json` + `GEMINI.md`).
   - For IDE rules: add a rule file under `.<provider>/rules/` (e.g., `.cursor/rules/observent.mdc`).
   - Rule body must reference `${OBSERVENT_HOME}/scripts/` for script paths (substituted at install time).
4. `README.md` — add a row to the Supported providers table and document the install command.
5. CI passes (detect_providers.py smoke test, lint, type-check).

#### Which path placeholder to use

- **Claude Code plugin** (`commands/*.toml`, `skills/observent/SKILL.md`): use `${CLAUDE_SKILL_DIR}`. Claude Code injects this at runtime; the files are loaded directly from the cloned plugin repo, not from `OBSERVENT_HOME`.
- **All other adapters** (`GEMINI.md`, `.cursor/rules/*.mdc`, `.windsurf/rules/*.md`, `.clinerules/*.md`, `.codex/context.md`): use `${OBSERVENT_HOME}`. The installer literal-substitutes this at copy time so the rule files reference the absolute `~/.observent/scripts/` path on the user's machine.

Don't mix them — `${CLAUDE_SKILL_DIR}` is empty outside Claude Code, and `${OBSERVENT_HOME}` is only resolved by the installer for files it copies.

## Design Constraints

- **Spec-driven lifecycle** — the skill produces three artifacts in the user's project under `.observent/`: `spec.md` (what & why), `plan.md` (how, with generated content in anchored fenced blocks), and `tasks.json` (ordered, mutable checkpoint that doubles as the session file). Downstream artifacts carry a sha256 fingerprint of their upstream's frontmatter so drift forces regeneration. `tasks.json` is the resume point — any task with status `pending` or `failed` means the workflow is incomplete and `/observent` should offer to resume. **No imperative driver script**: each `kind` (`confirm` / `write_file` / `edit_file` / `run_command` / `validate`) maps 1:1 to a Claude Code tool. Canonical schemas: `skills/observent/references/spec_schema.md`.
- **OTLP HTTP, not gRPC** is the default exporter for all three backends. Reasons: works through corporate proxies, smaller dep tree, Phoenix Cloud only supports HTTP.
- **OpenAI Agents SDK uses native `set_trace_processors()`**, not `openinference-instrumentation-openai`. This is non-negotiable — `-openai` loses agent structure (handoffs, runs, guardrails).
- **Per-backend convention** — the convention emitted by generated code is mechanically derived from the chosen backend set, not a free choice:
  - `{phoenix}` → OpenInference only (Phoenix-native UI). Canonical keys: `skills/observent/references/openinference.md`.
  - Any non-empty subset of `{langfuse, signoz, elastic-apm, langsmith}` (no Phoenix) → OTel-GenAI only. Canonical keys: `skills/observent/references/otel_genai.md`.
  - Any set containing Phoenix **and** at least one of `{langfuse, signoz, elastic-apm, langsmith}` → both, so each backend's UI lights up. This is the only case dual-emission is justified.
  No `OBSERVENT_CONVENTION` override — the rule is fixed by the backend set.
- **Elastic APM uses the native agent** — `elasticapm.Client(...)` + `elasticapm.instrument()` is the default generated path (not OTLP). The agent's OTel bridge picks up the OpenInference framework instrumentors so LLM spans land in Kibana alongside auto-instrumented transactions. Pure-OTLP via `OTLPSpanExporter` to `:8200/v1/traces` is documented as a secondary path for users avoiding the `elastic-apm` dependency. This mirrors the existing Langfuse precedent (`CallbackHandler` / `@observe`) — native SDKs are allowed; the "OTLP HTTP not gRPC" constraint is only about HTTP-vs-gRPC inside OTLP.
- **LangSmith uses pure OTLP HTTP** — `OTLPSpanExporter` to `${LANGSMITH_ENDPOINT}/otel/v1/traces` (default `https://api.smith.langchain.com`) with header `x-api-key: ${LANGSMITH_API_KEY}`. No `langsmith` SDK code is generated — LangSmith maps OTel-GenAI conventions to its native trace schema on ingest, so the generated stack is mechanically identical to SigNoz. This keeps LangSmith composable in the multi-backend fan-out template.
- **Mandatory attributes** — every generated template must populate model, provider, prompt+completion+total tokens, input/output messages, and (for Anthropic) cache tokens. The reference doc lists the full set per span kind.
- **Context propagation** — `start_as_current_span` (never `start_span`), Python ≥ 3.11 inherits async context, `attach()`/`detach()` for threads, `inject()` into env for subprocess, HTTPX/Requests instrumentors for cross-service.
- **Local self-host provisioning** — when a chosen backend's endpoint is `self-host` and unreachable, and Docker + Compose are available, the skill *offers* to stand it up locally. Covered backends: **Phoenix · Langfuse · SigNoz · Elastic APM**. **LangSmith is excluded** — it has no free OSS/Docker edition (self-host is enterprise-licensed), so it gets an explanatory note instead of an offer. **Two confirmation gates, never automatic:** (1) the Phase 1 §1.5 opt-in prompt (`Provision it locally with Docker?`) — a `no`/`skip` means no Docker task is generated; (2) the Phase 4 `confirm` task, which surfaces the `docker compose … up -d --wait` command (and the full compose file for `vendored-compose` backends) in the diff preview — `docker compose up` only runs after the user approves it. Provisioning stays inside the lifecycle as ordinary tasks — a `write_file` for a vendored compose (Phoenix, Elastic APM) and/or a `run_command` that runs the `up` command (or a pinned upstream `git clone` + up for Langfuse, SigNoz) — placed after `pip install` and before the final `validate`. No imperative Docker driver. Canonical templates + pinned image tags: `skills/observent/references/self_host.md`.
- **Diff preview before write** — even when auto-invoked. The skill never silently modifies user code.

## Documentation Hygiene

The 8×5 matrix in `references/matrix.md` is canonical. If you change a row or column there, mirror the change in:
- `SKILL.md` (Phase 2 § Step 2.5 endpoint table, Phase 1 § Step 1.3 backend-options list)
- `README.md` (Supported matrix)
- `references/examples.md` (if a removed combination had an example)

`references/openinference.md` and `references/otel_genai.md` are the canonical attribute references. `references/matrix.md` § Mandatory Span Attributes only carries a per-kind summary table — full attribute lists live in those two files. When the upstream specs change, update these files (and bump their `Last verified` footers); don't re-inline attributes back into `references/matrix.md`.

The **Image Versions** table in `references/self_host.md` is the canonical record of exact Docker image tags for the local-provisioning stacks (analogous to the matrix's Verified Versions, but for images not pip packages). When you bump an image tag, update that table and its `Last verified` footer; the compose templates in the same file are the only place image tags are written — don't duplicate them elsewhere.

The **Verified Versions** table in `references/matrix.md` is the canonical record of exact dependency pins (`==X.Y.Z`) — not floors. When you bump a pin, update the table **and** the matching per-backend Install line, every per-framework `pip install` snippet that mentions that package, and the `*Last verified: …*` footer of any example in `references/examples.md` that was re-run against the new version. The per-example footers are a different signal: they record when each individual example was last actually re-run end-to-end. Don't conflate them: the table is "what we claim works," the footer is "when we last proved it for this example." `scripts/validate_setup.py` error messages intentionally stay on `>=` form so user-facing hints suggest a minimum that will work, not the maintainer's exact pin.
