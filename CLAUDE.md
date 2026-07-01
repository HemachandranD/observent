# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

**observent** is a Claude Code plugin that wires up observability for multi-agent Python applications. It supports 9 frameworks × 7 backends (Arize Phoenix · Langfuse · SigNoz · Elastic APM · LangSmith · Opik · Jaeger) — a full grid of 63 integration paths.

The repo *is* the plugin: skill files live under `skills/observent/`, plugin manifests under `.claude-plugin/`, and slash commands under `commands/`. Users install it by adding the repo as a marketplace then installing the plugin: `claude plugin marketplace add HemachandranD/observent` followed by `claude plugin install observent@observent`.

## Repository Layout

```
.claude-plugin/
  plugin.json           # Claude Code plugin manifest — name, version, author
  marketplace.json      # Marketplace listing for `claude plugin install`; also
                        # declares skills:["./skills/observent"] for npx skills discovery
commands/
  observent.toml            # /observent [framework] [backend|backend,...] — full SDD lifecycle (spec→plan→tasks→implement) with resume
  observent-spec.toml       # /observent-spec — produce .observent/spec.md only
  observent-plan.toml       # /observent-plan — produce .observent/plan.md from spec.md
  observent-tasks.toml      # /observent-tasks — decompose plan.md into .observent/tasks.json
  observent-implement.toml  # /observent-implement — execute (or resume) tasks.json
  observent-detect.toml     # /observent-detect — run detectors and report
  observent-validate.toml   # /observent-validate <backend|backend,...> [--smoke-test]
  observent-eval.toml       # /observent-eval [--baseline] [--ci] — optional Phase 5 eval gate
skills/observent/
  SKILL.md              # Skill entry point — frontmatter + SDD workflow (Spec / Plan / Tasks / Implement) + optional Phase 5 Evaluate
  references/
    spec_schema.md      # Canonical schema for the three .observent/ artifacts (spec.md, plan.md, tasks.json)
    matrix.md           # 9×7 matrix, per-framework + per-backend reference,
                        # span attribute summary, context propagation, troubleshooting
    openinference.md    # Canonical OpenInference attribute reference (Phoenix path)
    otel_genai.md       # Canonical OTel-GenAI attribute reference (Langfuse / SigNoz / Elastic APM / LangSmith / Opik / Jaeger path)
    examples.md         # 8 runnable examples covering all frameworks + multi-backend fan-out
    capture.md          # transport-agnostic AI-boundary input/output/status capture engine
                        # (observent_capture.py) + optional observent_http.py raw-body adapter
    gateway.md          # gateway-boundary capture for opaque vendor runtimes (Claude Code,
                        # Cursor): litellm-proxy CustomLogger (observent_litellm.py) stamps an
                        # injected correlation id -> calls group by session.id / gen_ai.conversation.id
    self_host.md        # local-provisioning reference: pinned Docker compose / clone commands
                        # per self-hostable backend + image-tag pin table
    eval.md             # optional Phase 5 eval-gate engine: eval.json schema, cross-convention
                        # alias table, generated observent_eval.py collector, PII regexes,
                        # CI snippet, LLM-as-judge delegation contract
  scripts/
    observent_matrix.py # SINGLE SOURCE OF TRUTH for the framework×backend grid —
                        # frameworks/backends (slug, display, detect modules,
                        # convention) + KNOWN_AUTO_INSTRUMENTING_DEPS (deps that ship
                        # their own dormant OTel instrumentation, e.g. a2a-sdk).
                        # detect_framework.py, validate_setup.py and
                        # tests/test_docs_consistency.py all derive their tables here.
    detect_framework.py # JSON report: frameworks/backends/instrumentors detected
    validate_setup.py   # Per-backend env + reachability check; --smoke-test emits a span
    existing_setup.py   # Reports pre-existing observability config in user's project
    eval_gate.py        # Phase 5 deterministic eval gate (stdlib-only): normalizes spans
                        # across conventions, asserts budgets/behavior/redaction/regression
tests/test_workflows/   # Local test bed (NOT shipped in the plugin) — two demo agent
  building_blocks.py    #   apps (CrewAI + LangGraph) exercising every span kind, used to
  mcp_server.py         #   smoke-test that /observent wires up tracing end-to-end.
  llm_service.py        #   See tests/test_workflows/README.md.
  crewai_app.py
  langgraph_app.py
  requirements.txt
  .env.example
.github/workflows/ci.yml
README.md               # Public-facing — install, usage, supported matrix
LICENSE                 # Apache-2.0
NOTICE                  # Apache-2.0 attribution notice
```

**Note on `.observent/`:** the skill's three persisted artifacts (`spec.md`, `plan.md`, `tasks.json`) live in the **user's project**, not this repo — they are created by `/observent-spec` on first run in whatever project the user is instrumenting. Do not commit a `.observent/` directory into this plugin repo. See `skills/observent/references/spec_schema.md` for the canonical artifact schemas.

**Note on `tests/test_workflows/`:** a local test bed only — it is **not** part of the installed plugin, and pytest does **not** collect it (excluded via `--ignore` in `pyproject.toml`); it's for manual runs only. The two demo apps (CrewAI + LangGraph) each take a user question and walk one linear pipeline that hits every span kind (agent · retriever · tool · MCP-over-stdio · two LLM calls: a direct Azure OpenAI call and a shared FastAPI LLM service). Run them, then run `/observent` against the folder to confirm every span kind lands in the backend. Environment gotchas worth remembering:
- **CrewAI ≥ 1.0** routes `LLM(model="azure/<deployment>")` to its *native* `azure.ai.inference` provider (a different API from Azure OpenAI). Pass `is_litellm=True` to force the litellm path we actually want — see `tests/test_workflows/crewai_app.py`. CrewAI 1.x also makes `litellm` an **optional** extra, so it must be installed explicitly.
- **litellm pin:** versions `1.82.7` / `1.82.8` were a March 2026 supply-chain compromise (credential stealer targeting `.env` files) and are yanked from PyPI; `CVE-2026-42208` (SQL injection) affects older releases. Pin a recent clean release (e.g. `litellm==1.86.2`).
- On Windows, litellm ships a pathologically deep nested file that trips the 260-char `MAX_PATH` limit when the venv sits under a long path (e.g. a OneDrive folder). Either enable `LongPathsEnabled` or install litellm into a short-path target dir and link it via a `.pth`.

## Tech Stack

- **Language:** Python 3.10+ (CI matrix: 3.10 / 3.11 / 3.12 on Ubuntu + Windows).
- **Skill scripts:** zero external dependencies — only stdlib + optional dynamic imports.
- **Tooling config:** centralized in `pyproject.toml` (`[tool.ruff]`, `[tool.mypy]`, `[tool.pytest.ini_options]`). CI installs **pinned** `ruff` / `mypy` / `pytest` versions so a floating release can't redden an unrelated PR — bump the pins in `.github/workflows/ci.yml` deliberately.
- **Lint:** `ruff` (rule set in `pyproject.toml`).
- **Type check:** `mypy --strict` (config in `pyproject.toml`).
- **Tests:** `pytest` — unit tests for the three skill scripts + the convention rule, plus a docs-consistency suite that enforces the § Documentation Hygiene invariants (framework×backend grid and version pins agree across files). `tests/` is **not** shipped in the plugin.

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

# Phase 5 eval gate — assert budgets/behavior over a captured run (offline, no backend)
#   first collect spans:  OBSERVENT_EVAL=1 python your_app.py "question"
python skills/observent/scripts/eval_gate.py --spec .observent/eval.json --spans .observent/eval/spans.jsonl
python skills/observent/scripts/eval_gate.py --spec .observent/eval.json --spans .observent/eval/spans.jsonl --baseline .observent/eval/baseline.json --update-baseline
python skills/observent/scripts/eval_gate.py --spec .observent/eval.json --spans .observent/eval/spans.jsonl --format junit
#   shareable, self-contained HTML report (ASCII-safe; open in any browser):
python skills/observent/scripts/eval_gate.py --spec .observent/eval.json --spans .observent/eval/spans.jsonl --format html > .observent/eval/report.html

# Run the test suite (unit tests + docs-consistency checks)
pytest

# Lint + type-check (config lives in pyproject.toml)
ruff check skills/observent/scripts/ tests/
mypy skills/observent/scripts/
```

## How to Extend

> **Schema generality:** the spec / plan / tasks artifacts (`skills/observent/references/spec_schema.md`) are generic over framework and backend *strings* — adding a new framework or backend does **not** require schema edits. Only the matrix and detector entries below need updating; the skill picks up the new option via those.

### Adding a new framework

Update in this order:

1. `skills/observent/scripts/observent_matrix.py` — add a `Framework(slug, display, modules)` entry to `FRAMEWORKS` (the single source of truth). `detect_framework.py`'s `FRAMEWORKS` table and `tests/test_docs_consistency.py`'s framework list both derive from this automatically — no edits needed in either.
2. `skills/observent/SKILL.md` — add the framework to the `argument-hint`-eligible list in Phase 1 § Step 1.2 and the description's auto-invocation triggers.
3. `skills/observent/references/matrix.md` — add a "Per-framework reference" subsection and a row to the 9×7 compatibility matrix.
4. `skills/observent/references/examples.md` — add at least one runnable example (rotate which backend it uses) and stamp it with a `*Last verified: YYYY-MM-DD with Python X.Y.*` footer.
5. `skills/observent/references/matrix.md` § Verified Versions — add a row for the new framework + instrumentor packages with the exact installed version (`==X.Y.Z`, sourced from the package's PyPI page or `pip show`), and bump the table's "Last verified" date to today. Mirror the same `==` pin in the per-framework `pip install` snippet you added in step 3.
6. CI passes (frontmatter parse, imports, lint, type-check).

### Adding a new backend

Update in this order:

1. `skills/observent/scripts/observent_matrix.py` — add a `Backend(slug, display, convention, detect_modules)` entry to `BACKENDS` (`convention` is `oi` for an OpenInference-native backend, `otel-genai` otherwise; `detect_modules` is the probeable pip import name(s), or `()` for a service-only backend like SigNoz). `validate_setup.BACKEND_CONVENTION`, `detect_framework.BACKENDS`, and the docs-consistency backend list all derive from this. *(A detection-only signal that isn't a product backend — e.g. a bare `opentelemetry` install — goes in `DETECTION_EXTRA_BACKENDS` instead.)*
2. `skills/observent/scripts/validate_setup.py` — add a `check_<backend>()` function and register it in `CHECKS` so `resolve_convention()` and its tests pick it up. (The convention itself now comes from step 1.)
3. `skills/observent/SKILL.md` — update the description, the backend-options list in Phase 1 § Step 1.3, the convention-derivation table (if applicable), and the endpoints table in Phase 2 § Step 2.5.
4. `skills/observent/references/matrix.md` — add a "Per-backend reference" subsection and a column to the matrix.
5. `skills/observent/references/examples.md` — add at least one example using the new backend, with a `*Last verified: YYYY-MM-DD with Python X.Y.*` footer.
6. `skills/observent/references/matrix.md` § Verified Versions — add a row for the backend's required package(s) with the exact installed version (`==X.Y.Z`, sourced from the package's PyPI page or `pip show`), and bump the table's "Last verified" date to today. Mirror the same `==` pin in the per-backend Install line you added in step 4.
7. **If the backend is self-hostable:** `skills/observent/references/self_host.md` — add a provisioning section (choose `vendored-compose` for a self-contained stack, `upstream-clone` when the stack needs repo-mounted config files, or `vendor-cli-generated` when self-host flows through a vendor CLI that *generates* a compose file, e.g. SigNoz/Foundry — this method has no Image-Versions rows since the CLI resolves image tags at generation time; pin the CLI/installer instead). Add a row to the § Image Versions table with the exact image tag(s) (skip for `vendor-cli-generated`), and bump that table's "Last verified" date. Add the backend to the `{phoenix, langfuse, signoz, elastic-apm, opik, jaeger}` provisionable set referenced in `SKILL.md` Phase 1 § 1.5. If it has **no** free self-host edition (like LangSmith), instead document it under the "not provisioned" note and leave it out of the provisionable set.
8. `tests/` — no edits needed for the grid: `test_docs_consistency.py` derives its framework/backend lists from `observent_matrix.py` (step 1), so the new option is covered automatically. Just run `pytest` to confirm the matrix/README/code stay in sync.

### Adding a known auto-instrumenting dependency

Some third-party libraries ship their own OpenTelemetry instrumentation that is dormant until `opentelemetry` is importable, then auto-emits library-internal spans once the skill installs `opentelemetry-sdk` (e.g. `a2a-sdk`'s `a2a.server.*` spans, gated by `OTEL_INSTRUMENTATION_A2A_SDK_ENABLED`). To register one so the skill can offer keep-vs-disable:

1. `skills/observent/scripts/observent_matrix.py` — append an `AutoInstrumentingDep(slug, display, modules, env_var, enabled_by_default)` to `KNOWN_AUTO_INSTRUMENTING_DEPS`. `detect_framework.py` derives its detection loop + the `auto_instrumenting_deps` JSON field from this automatically. Use two probe modules if the import name differs from the PyPI name (the `("a2a", "a2a_sdk")` trick, mirroring google-adk). Only list deps with a **documented** on/off env var.
2. `skills/observent/references/matrix.md § Known auto-instrumenting dependencies` — add a row (dependency · what it instruments · gate env var · default).
3. `skills/observent/SKILL.md § 1.4b` already handles the spec-phase keep/disable question generically — no edit needed unless the interaction changes.
4. `tests/test_detect_framework.py` — add a detection test for the new dep.

### Cross-tool distribution (read this first)

`skills/observent/SKILL.md` (with its `references/` and `scripts/`) is the **single content surface** for every tool. There is no condensed `AGENTS.md` mirror and no per-tool rule files to keep in sync — that multi-copy machinery (`install.sh`/`install.ps1`, `AGENTS.md`, `.cursor/rules/`, `.clinerules/`, `scripts/detect_providers.py`, the Antigravity extension manifest) was retired in favour of `npx skills`.

- **Claude Code** loads the skill directly as a plugin (`claude plugin marketplace add HemachandranD/observent` then `claude plugin install observent@observent`), with the `commands/*.toml` slash commands on top.
- **Every other agent** receives the same **self-contained** skill folder via [`npx skills`](https://github.com/vercel-labs/skills) (vercel-labs/skills): `npx skills add HemachandranD/observent` copies `skills/observent/` into the agent's skills directory (`.claude/skills/`, `.agents/skills/`, …). Discovery works two ways — the flat `skills/observent/SKILL.md` layout, **and** the `"skills": ["./skills/observent"]` array in `.claude-plugin/marketplace.json` (CI asserts that array resolves to a real `SKILL.md`).

Keep the skill **self-contained and relative** so it runs wherever it lands: `references/*` are referenced by plain relative path; scripts are invoked via the agent-agnostic `<skill-dir>/scripts/…` placeholder, with the SKILL.md § Step 1.1 portability note telling each agent how to resolve `<skill-dir>` (Claude Code's `${CLAUDE_SKILL_DIR}`, or the skill's own folder for everyone else). Never reintroduce `${OBSERVENT_HOME}`, an `AGENTS.md` workflow mirror, or per-tool pointer files.

### Adding a new eval check (Phase 5)

The eval gate is **grid-agnostic** — it touches none of `observent_matrix.py`, the detectors, or the 9×7 matrix. To add a new assertion:

1. `skills/observent/scripts/eval_gate.py` — add the check to the relevant family function (`check_budgets` / `check_behavior` / `check_redaction` / `check_regression`) or add a new family and call it from `run_checks`. Emit a `Check(name, status, message)`; keep it stdlib-only and `mypy --strict` clean.
2. `skills/observent/references/eval.md` — document the new `eval.json` key under § eval.json schema. **If it reads a span attribute**, add the canonical field to the cross-convention alias table using only keys that exist in `references/openinference.md` / `otel_genai.md` (the docs-consistency test asserts this).
3. `skills/observent/references/spec_schema.md § 4` — only if the `eval.json` top-level shape changes (a new family). Individual keys within an existing family don't need a schema edit.
4. `tests/test_eval_gate.py` — add a pass/fail unit test for the new check (feed both OI and OTel-GenAI spans if it normalizes an attribute, to prove convention parity).
5. `pytest` — `test_docs_consistency.py` re-checks the alias table against the canonical refs automatically.

### Adding a new provider

Usually **nothing to do in this repo** — `npx skills` already maps 70+ coding agents to their skills directories, so a newly supported agent picks up `skills/observent/` automatically as long as the skill stays self-contained. Optionally add a row to the README § Supported providers table to call it out. (Only an agent with a bespoke install mechanism — the way Claude Code's plugin works — would need its own handling; document that separately if it ever arises.)

#### Which path placeholder to use

- **Script paths in `skills/observent/SKILL.md`**: use the agent-agnostic `<skill-dir>/scripts/…` placeholder, with the § Step 1.1 note explaining that Claude Code substitutes its built-in `${CLAUDE_SKILL_DIR}` while other agents use the absolute path of the skill folder they loaded `SKILL.md` from. Don't hard-code `${CLAUDE_SKILL_DIR}` as the only form in `SKILL.md` — it resolves only in Claude Code, but `npx skills` ships the same `SKILL.md` to every agent.
- **Script paths in `commands/*.toml`**: use literal `${CLAUDE_SKILL_DIR}/scripts/…` — those TOMLs load **only** under the Claude Code plugin, where the variable always resolves.
- **`references/*`** are referenced by plain relative path (no placeholder).
- **Never use `${OBSERVENT_HOME}`** — it was resolved only by the retired installer and means nothing under `npx skills`.

## Design Constraints

- **Spec-driven lifecycle** — the skill produces three artifacts in the user's project under `.observent/`: `spec.md` (what & why), `plan.md` (how, with generated content in anchored fenced blocks), and `tasks.json` (ordered, mutable checkpoint that doubles as the session file). Downstream artifacts carry a sha256 fingerprint of their upstream's frontmatter so drift forces regeneration. `tasks.json` is the resume point — any task with status `pending` or `failed` means the workflow is incomplete and `/observent` should offer to resume. **No imperative driver script**: each `kind` (`confirm` / `write_file` / `edit_file` / `run_command` / `validate`) maps 1:1 to a Claude Code tool. Canonical schemas: `skills/observent/references/spec_schema.md`.
- **OTLP HTTP, not gRPC** is the default exporter for all three backends. Reasons: works through corporate proxies, smaller dep tree, Phoenix Cloud only supports HTTP.
- **OpenAI Agents SDK uses native `set_trace_processors()`**, not `openinference-instrumentation-openai`. This is non-negotiable — `-openai` loses agent structure (handoffs, runs, guardrails).
- **Per-backend convention** — the convention emitted by generated code is mechanically derived from the chosen backend set, not a free choice:
  - `{phoenix}` → OpenInference only (Phoenix-native UI). Canonical keys: `skills/observent/references/openinference.md`.
  - Any non-empty subset of `{langfuse, signoz, elastic-apm, langsmith, opik, jaeger}` (no Phoenix) → OTel-GenAI only. Canonical keys: `skills/observent/references/otel_genai.md`.
  - Any set containing Phoenix **and** at least one of `{langfuse, signoz, elastic-apm, langsmith, opik, jaeger}` → both, so each backend's UI lights up. This is the only case dual-emission is justified.
  No `OBSERVENT_CONVENTION` override — the rule is fixed by the backend set.
- **Elastic APM uses the native agent** — `elasticapm.Client(...)` + `elasticapm.instrument()` is the default generated path (not OTLP). The agent's OTel bridge picks up the OpenInference framework instrumentors so LLM spans land in Kibana alongside auto-instrumented transactions. Pure-OTLP via `OTLPSpanExporter` to `:8200/v1/traces` is documented as a secondary path for users avoiding the `elastic-apm` dependency. This mirrors the existing Langfuse precedent (`CallbackHandler` / `@observe`) — native SDKs are allowed; the "OTLP HTTP not gRPC" constraint is only about HTTP-vs-gRPC inside OTLP.
- **LangSmith uses pure OTLP HTTP** — `OTLPSpanExporter` to `${LANGSMITH_ENDPOINT}/otel/v1/traces` (default `https://api.smith.langchain.com`) with header `x-api-key: ${LANGSMITH_API_KEY}`. No `langsmith` SDK code is generated — LangSmith maps OTel-GenAI conventions to its native trace schema on ingest, so the generated stack is mechanically identical to SigNoz. This keeps LangSmith composable in the multi-backend fan-out template.
- **Mandatory attributes** — every generated template must populate model, provider, prompt+completion+total tokens, input/output messages, and (for Anthropic) cache tokens. The reference doc lists the full set per span kind.
- **Context propagation** — `start_as_current_span` (never `start_span`), Python ≥ 3.11 inherits async context, `attach()`/`detach()` for threads, `inject()` into env for subprocess, HTTPX/Requests instrumentors for cross-service.
- **Local self-host provisioning** — when a chosen backend's endpoint is `self-host` and unreachable, and Docker + Compose are available, the skill *offers* to stand it up locally. Covered backends: **Phoenix · Langfuse · SigNoz · Elastic APM · Opik · Jaeger**. **LangSmith is excluded** — it has no free OSS/Docker edition (self-host is enterprise-licensed), so it gets an explanatory note instead of an offer. Three provisioning methods (`skills/observent/references/self_host.md § Provisioning method per backend`): `vendored-compose` (Phoenix, Elastic APM, Jaeger — a written compose file), `upstream-clone` (Langfuse, Opik — pinned `git clone` + up), and `vendor-cli-generated` (**SigNoz** — installs the Foundry CLI, writes its `casting.yaml`, runs `foundryctl forge` to *generate* a compose file, then `docker compose up` on it; SigNoz deprecated its own `docker-compose` manifests in 2026). **Confirmation gates, never automatic:** (1) the Phase 1 §1.5 opt-in prompt (`Provision it locally with Docker?`) — a `no`/`skip` means no Docker task is generated; (2) the Phase 4 `confirm` task, which surfaces the `docker compose … up -d --wait` command (and the full compose file for `vendored-compose` backends) in the diff preview — `docker compose up` only runs after the user approves it; (3) for `vendor-cli-generated`, an additional `installs_cli` `confirm` because it installs a local binary (a larger consent surface than `docker compose up`) — surfaces the package, installer URL, and trust basis. Provisioning stays inside the lifecycle as ordinary tasks — a `write_file` for a vendored compose (Phoenix, Elastic APM, Jaeger) and/or `run_command`s for the `up` command (a pinned upstream `git clone` + up for Langfuse, Opik; a CLI install → config write → `forge` → up for SigNoz) — placed after `pip install` and before the final `validate`. No imperative Docker driver. Canonical templates + pinned image tags: `skills/observent/references/self_host.md`.
- **Diff preview before write** — even when auto-invoked. The skill never silently modifies user code.
- **Optional MCP enrichment — progressive enhancement, never a dependency** — the bundled zero-dependency scripts (`detect_framework.py`, `existing_setup.py`, `validate_setup.py`) are the floor; the skill must run end-to-end with only `Bash`. When the host agent *also* exposes a useful MCP, Phase 4 may use it to *add* confidence, but the script/Bash path stays canonical for a task's `done`/`failed` status and a missing or failing MCP must never block a task. Recommended set (each with a documented fallback): an **IDE / language-server MCP** (verify generated `observent_otel.py` / `observent_capture.py` imports + type-checks before marking a `write_file`/`edit_file` task `done`), an **observability-backend MCP** (Phoenix / Langfuse / SigNoz / Datadog / Grafana — confirm the smoke-test span actually landed with the expected attributes, past mere endpoint reachability), and a **container / Docker MCP** (inspect provisioned-stack health + logs instead of trusting the `docker compose … up --wait` exit code). MCP use carries the same diff-preview/confirm gate as a file write (never exfiltrate user code/traces silently, never pass secret values). **Context7 is explicitly excluded** — it's a maintainer/authoring aid for refreshing the `references/` files, not an implementation-phase tool. Because the skill ships verbatim to 70+ agents via `npx skills`, MCPs are framed agent-agnostically and `allowed-tools` is **not** widened with volatile MCP tool names — Claude Code users add the relevant ones themselves. Canonical description: `skills/observent/SKILL.md` § Optional MCP enrichment.

## Documentation Hygiene

The 9×7 matrix in `references/matrix.md` is canonical. If you change a row or column there, mirror the change in:
- `SKILL.md` (Phase 2 § Step 2.5 endpoint table, Phase 1 § Step 1.3 backend-options list)
- `README.md` (Supported matrix)
- `references/examples.md` (if a removed combination had an example)

**`skills/observent/SKILL.md` is the single source of truth — there is no cross-tool mirror to keep in sync.** `npx skills` distributes the skill folder verbatim to every agent, so the old condensed `AGENTS.md` copy (and the per-tool pointer files) were removed. When you change the lifecycle, phases, convention rules, generated-code invariants, or provisioning flow, edit `SKILL.md` directly — no second copy needs updating. Do **not** reintroduce an `AGENTS.md` workflow mirror or per-tool rule files.

`references/openinference.md` and `references/otel_genai.md` are the canonical attribute references. `references/matrix.md` § Mandatory Span Attributes only carries a per-kind summary table — full attribute lists live in those two files. When the upstream specs change, update these files (and bump their `Last verified` footers); don't re-inline attributes back into `references/matrix.md`.

The **Image Versions** table in `references/self_host.md` is the canonical record of exact Docker image tags for the local-provisioning stacks (analogous to the matrix's Verified Versions, but for images not pip packages). When you bump an image tag, update that table and its `Last verified` footer; the compose templates in the same file are the only place image tags are written — don't duplicate them elsewhere.

The **Verified Versions** table in `references/matrix.md` is the canonical record of exact dependency pins (`==X.Y.Z`) — not floors. When you bump a pin, update the table **and** the matching per-backend Install line, every per-framework `pip install` snippet that mentions that package, and the `*Last verified: …*` footer of any example in `references/examples.md` that was re-run against the new version. The per-example footers are a different signal: they record when each individual example was last actually re-run end-to-end. Don't conflate them: the table is "what we claim works," the footer is "when we last proved it for this example." `scripts/validate_setup.py` error messages intentionally stay on `>=` form so user-facing hints suggest a minimum that will work, not the maintainer's exact pin.
