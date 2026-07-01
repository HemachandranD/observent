# observent skill — gaps found during real_a2a setup (2026-07-01)

Feedback for the skill maintainer, found while running `/observent` against the
`real_a2a` app (4-process, 3-framework A2A system; backends: Phoenix + SigNoz).

## 1. `references/self_host.md § SigNoz` is stale — upstream deprecated docker-compose

**What the skill says:** SigNoz is provisioned via `method: upstream-clone` —

```bash
git clone --depth 1 -b main https://github.com/SigNoz/signoz.git .observent/vendor/signoz \
  && docker compose -f .observent/vendor/signoz/deploy/docker/docker-compose.yaml up -d --wait
```

**What actually happens:** the compose file no longer exists at that path. Cloning
`SigNoz/signoz` main and checking `deploy/` gets:

```
deploy/
  install.sh      # now a no-op that prints a deprecation notice
  MIGRATION.md
  README.md
```

`deploy/README.md` states plainly:

> **Note:** The `install.sh` script and the `docker-compose` manifests have been
> deprecated. SigNoz now installs and runs through **Foundry**.

So `docker compose -f .observent/vendor/signoz/deploy/docker/docker-compose.yaml up -d --wait`
fails immediately with "path not found" — this is not a flaky/version-skew issue, the
file is just gone from `main`.

## 2. The replacement (Foundry) doesn't fit either `vendored-compose` or `upstream-clone`

SigNoz's new self-host path is a **third provisioning shape** the skill's two
methods (`vendored-compose` / `upstream-clone`) don't model:

1. Install a small vendor-published CLI (`foundryctl`) via a checksum-verified
   GitHub-releases installer script:
   ```bash
   curl -fsSL https://signoz.io/foundry.sh | bash
   ```
   (Reviewed the script — it's a legitimate installer: resolves the latest GitHub
   release tag, downloads a platform-specific tarball, verifies its sha256 against
   a published checksums file, and installs the binary to `~/.local/bin`. No
   arbitrary remote code execution beyond that. It also transparently supports
   Windows/Git-Bash — detects `mingw*/cygwin*/msys*` and maps to `windows` + `.exe`.)

2. Write a `casting.yaml` describing the desired deployment:
   ```yaml
   apiVersion: v1alpha1
   kind: Installation
   metadata:
     name: signoz
   spec:
     deployment:
       flavor: compose
       mode: docker
   ```

3. Either let Foundry manage everything (`foundryctl cast -f casting.yaml`), or —
   the safer option, since it avoids handing an unfamiliar CLI ongoing control —
   generate plain compose files and run them yourself:
   ```bash
   foundryctl forge -f casting.yaml   # writes ./pours/deployment/compose.yaml (+ config)
   docker compose -f pours/deployment/compose.yaml up -d --wait
   ```

Ports stayed the same as the old doc (UI `8080`, OTLP `4317`/`4318`), so
`matrix.md`'s SigNoz endpoint table is still correct — only the *provisioning*
mechanism changed, not the running service's contract.

**Suggested fix:** add a third `method: vendor-cli-generated` (or similar) to
`self_host.md § Provisioning method per backend` and `spec_schema.md § plan.provision[]`,
with steps: install CLI (pinned installer URL + any version pin flag) → write CLI's
own declarative config → `<cli> forge`-equivalent to materialize a plain compose
file → `docker compose up -d --wait` on that generated file, same as
`vendored-compose` from that point on. SigNoz should move from `upstream-clone` to
this new method; worth also re-checking whether Opik/Langfuse's `upstream-clone`
compose paths are still current (I did not re-verify those in this session).

## 3. `references/self_host.md § Image Versions` pins are now disconnected from what's deployed

The pinned tags recorded for SigNoz (`signoz/signoz v0.126.1`,
`signoz-otel-collector v0.144.4`, `clickhouse-server 25.5.6`) were read off the old
`upstream-clone` compose file, which no longer exists. Foundry's generated
`compose.yaml` pins its own image versions internally — the skill has no visibility
into (or control over) those pins anymore unless it also parses the generated
`pours/deployment/compose.yaml` after the fact. Worth deciding whether the skill
should record "pins are whatever Foundry resolves at generation time, not tracked
here" for any backend that moves to `vendor-cli-generated`.

## 4. Minor process note (not a doc bug, just an observation)

Nothing in `SKILL.md` Phase 1 § 1.5 / Phase 3 flags that a self-host provisioning
step might itself require installing a new local CLI tool (as opposed to only ever
running `docker compose`). That's a bigger trust/consent surface than "run docker
compose up" — this session paused and asked the user explicitly before running the
`curl | bash` installer, which felt like the right call, but the skill's `confirm`
task prompt template (`spec_schema.md § tasks.json`) doesn't have a slot for
"this backend's provisioning also installs a local binary, here's what it does and
why it's trustworthy (checksum-verified GitHub release, no arbitrary exec)." Might
be worth a dedicated confirm sub-step for `vendor-cli-generated` provisioning so
this isn't ad-hoc per session.

## 5. Phoenix + SigNoz port collision isn't called out (only Jaeger + SigNoz is)

`self_host.md § Jaeger` has this note:

> **Note:** Jaeger's default `4318`/`4317` OTLP ports collide with a self-hosted
> SigNoz. If you run both, remap one stack's host ports in its compose file.

The same collision exists for **Phoenix + SigNoz**: Phoenix's vendored compose
publishes host `4317` for its OTLP gRPC receiver
(`docker-compose.observent-phoenix.yml`), and SigNoz's ingester also wants host
`4317`/`4318`. When both are selected together (a very likely combo — Phoenix for
dev-loop UX, SigNoz for full-stack APM — this is exactly what this session's user
picked), the second `docker compose up` fails outright:

```
Error response from daemon: failed to set up container networking: driver failed
programming external connectivity on endpoint signoz-ingester-1: Bind for
0.0.0.0:4317 failed: port is already allocated
```

Fix applied here: remapped Phoenix's host port for gRPC from `4317:4317` to
`4327:4317` in the vendored compose file (the app only uses Phoenix's **HTTP**
OTLP endpoint on `6006`, so losing the default host gRPC port is harmless).
**Suggested fix:** generalize the Jaeger note into a proper port-conflict matrix in
`self_host.md § Port-conflict & readiness notes` covering every pairwise overlap
across all 6 self-hostable backends (Phoenix, Jaeger, and SigNoz's ingester all
default to host `4317`/`4318`), and have Phase 1 § 1.5 check for cross-backend port
collisions among the *newly selected* set before writing any compose file, not just
against what's already running.

## 6. SigNoz's OTLP receiver isn't actually ready when `docker compose up --wait` returns

Even after `--wait` reports every container `Healthy`, the ingester's OTLP HTTP
receiver on `4318` refused/dropped real span POSTs for about two more minutes.
`docker logs signoz-ingester-1` shows why: the container starts with a placeholder
pipeline, waits for its real collector config to arrive over **opamp** from the
`signoz` control-plane container, then does an internal `Restarting collector
service` and only *then* logs `Starting HTTP server ... endpoint [::]:4318`. The
container's own healthcheck (hitting the health-check extension on `13133`) goes
green well before that restart, so `--wait` is watching the wrong signal for this
backend. In this session, the skill's `validate_setup.py` ran immediately after
provisioning and reported the endpoint reachable but the smoke-test span export
failed with `RemoteDisconnected` — a plain retry ~2 minutes later succeeded with no
code changes. **Suggested fix:** for SigNoz specifically, either poll the OTLP
endpoint with a real (small) span POST — not just a health check — before
declaring `provision` done, or document the opamp-driven settle delay in
`self_host.md § SigNoz` and give `validate_setup.py` a bounded retry/backoff
instead of a single immediate check.

## 7. `validate_setup.py`'s Phoenix check hard-requires the `arize-phoenix` pip package

The Phoenix check in `validate_setup.py` fails with
`[FAIL] arize-phoenix not installed (pip install 'arize-phoenix>=5.0')` even when
the generated code deliberately does **not** use `phoenix.otel.register()` (the
single-backend convenience wrapper) and instead follows `matrix.md`'s own
"Multi-Backend Fan-Out" pattern: a manual `TracerProvider` with one
`BatchSpanProcessor(OTLPSpanExporter(...))` per backend. That pattern needs only
`opentelemetry-sdk` + `opentelemetry-exporter-otlp-proto-http` — never the
`arize-phoenix` package itself. Confirmed the pipeline genuinely works by exporting
a real span directly (no exception, span accepted) while the validator still
reported `FAIL` and exit code 1 for the overall run. **Suggested fix:** make the
`arize-phoenix` package check conditional on whether the generated code actually
calls `phoenix.otel.register()` (single-backend path) vs. builds its own
`TracerProvider` (multi-backend fan-out path, `matrix.md`'s own recommended
pattern for exactly this Phoenix+other-backend combination) — in the latter case,
reachability + a real synthetic-span POST (which the script already does for
SigNoz) is the correct and sufficient check, not a pip-package presence check.

## 8. `PHOENIX_PROJECT_NAME` is documented as a no-code-change env var, but only works with `phoenix.otel.register()` — the manual multi-backend `TracerProvider` pattern silently ignores it

`matrix.md § Arize Phoenix` lists `PHOENIX_PROJECT_NAME` under "Optional env vars"
with the description "groups traces into projects," and its only code sample is:

```python
tracer_provider = register(
    project_name=os.getenv("PHOENIX_PROJECT_NAME", "my-agent-app"),
    ...
)
```

But `register()` is the single-backend convenience wrapper. When Phoenix is
combined with another backend (this session's Phoenix+SigNoz case — exactly the
scenario `matrix.md`'s own "Multi-Backend Fan-Out" section recommends a manual
`TracerProvider` for), the generated `observability.py` built a bare
`TracerProvider(resource=Resource.create({"service.name": service_name}))` and
never read `PHOENIX_PROJECT_NAME` at all. Setting it in `.env` had **zero effect**
— every trace silently landed in Phoenix's `default` project with no error or
warning anywhere. This was caught only by manually cross-checking the doc's env
var list against the generated code, not by any validator output.

The actual fix (added by hand, not by the skill) is to fold the value into the
resource as the attribute Phoenix reads for raw-OTLP project routing:

```python
resource_attrs = {"service.name": service_name}
if phoenix_project := os.getenv("PHOENIX_PROJECT_NAME"):
    resource_attrs["openinference.project.name"] = phoenix_project
provider = TracerProvider(resource=Resource.create(resource_attrs))
```

**Suggested fix:** `matrix.md § Arize Phoenix` and the Phase 2 § 2.2 "Required
pieces in every generated file" checklist should give the **manual
`TracerProvider` fan-out path** its own project-routing snippet (the
`openinference.project.name` resource attribute above), not just the
`register(project_name=...)` one — otherwise every multi-backend-with-Phoenix
generation silently drops this documented, user-facing knob.

## 9. `capture.md`'s `exclude_spans` advice assumes FastAPI; `StarletteInstrumentor` (this app's actual web framework) doesn't expose it

`capture.md § Optional HTTP body adapter` says:

> Transport spans (`http receive` / `http send`) from the ASGI instrumentor are
> **left intact** — they are honest transport spans, not observent's to suppress.
> A user who wants them gone can pass `exclude_spans=["receive", "send"]` to the
> **FastAPI instrumentor**.

True for `FastAPIInstrumentor.instrument_app()`, but this app is Starlette (not
FastAPI), and `StarletteInstrumentor.instrument_app()` in the pinned version
(`opentelemetry-instrumentation-starlette==0.63b1`) has **no** `exclude_spans`
parameter at all — its signature only exposes `server_request_hook` /
`client_request_hook` / `client_response_hook` / `meter_provider` /
`tracer_provider`. Checked the source: internally it hardcodes a call to
`app.add_middleware(OpenTelemetryMiddleware, ...)` without forwarding
`exclude_spans`, even though the underlying `OpenTelemetryMiddleware` (from
`opentelemetry-instrumentation-asgi`) supports it just fine.

This mattered in practice: with the default `StarletteInstrumentor.instrument_app(app)`
generated by the skill, every request produced a `POST / http send` span **per SSE
chunk** (this app streams JSON-RPC responses) — 12+ transport spans for one logical
request, on top of the one real server span. The user asked "why is the trace
polluted with POST/GET" and the fix was to bypass `StarletteInstrumentor` entirely
and call the ASGI middleware directly:

```python
from opentelemetry.instrumentation.asgi import OpenTelemetryMiddleware

app.add_middleware(OpenTelemetryMiddleware, exclude_spans=["receive", "send"])
```

**Suggested fix:** either (a) have `capture.md`'s advice explicitly branch on
web framework — "FastAPI: pass `exclude_spans` to `FastAPIInstrumentor`; Starlette:
`StarletteInstrumentor` doesn't expose it, use `OpenTelemetryMiddleware` directly"
— or (b) since this is clearly a noise problem for **any** streaming ASGI app
regardless of framework, have Phase 2's generated instrumentation default to
`exclude_spans=["receive", "send"]` whenever `capabilities.streaming` (or
equivalent SSE usage) is detected, rather than requiring the user to notice the
noise and hunt down the fix themselves.

## 10. `capture.md`'s "enrich the existing root span" design has no documented option for users who don't want *any* web-framework span as the trace root

Gap #9's `exclude_spans=["receive", "send"]` fix removed the per-message ASGI
noise, but the user came back with a further, reasonable objection: they didn't
want **any** "blunt" framework-level ASGI instrumentation at all — not even the
one remaining `POST /` server span per request — because it still made the trace
feel congested next to the actual business spans (`Crew.kickoff`, `Task
Execution`, etc.). `capture.md`'s entire design (§ "Core principle — enrich in
place, never duplicate the root span") assumes the desired root **is** whatever
the web-framework instrumentor opens, and only documents a fallback root
(`agent.run`) for the case where *nothing* is instrumented (a bare CLI). It has no
documented path for "I have a web framework, but I don't want its instrumentor's
span at all — just give me one clean span per request, and please don't break
cross-service trace linkage while you're at it."

The fix (not in the skill, built by hand this session): drop the ASGI/Starlette
instrumentor entirely and replace it with a minimal custom middleware that does
**only** W3C context extraction — no span:

```python
from opentelemetry import context as otel_context
from opentelemetry.propagate import extract

class TraceContextMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        carrier = {k.decode("latin-1"): v.decode("latin-1") for k, v in scope.get("headers", [])}
        token = otel_context.attach(extract(carrier))
        try:
            await self.app(scope, receive, send)
        finally:
            otel_context.detach(token)
```

Then made `capture.py`'s existing private `_enrich_or_open` fallback (previously
only reachable via the `capture_run`/`capture_run_async` decorators, for the
"nothing instrumented" CLI case) into a public `open_or_enrich_span(inputs)`
context-manager entry point, and used it at the one shared AI-boundary wrap point
(`executor_base.py::SimpleAgentExecutor.execute`) instead of the raw
`enrich_current_span` call that assumed a framework span was already recording.
Net result: zero transport/framework spans of any kind, one clean `agent.run` root
per request that CrewAI/LangGraph/Google ADK's own spans nest under, and
cross-service trace linkage (admin -> child) fully preserved because context is
still extracted — just invisibly, with no span attached to it.

**Suggested fix:** document this as a third, first-class pattern in
`capture.md`/`matrix.md` alongside "framework instrumentor already open" and
"nothing instrumented (CLI)" — call it "framework present but its transport
spans are unwanted": extract-context-only middleware (no span) + the fallback
root becomes the *primary* mechanism, not a rarely-hit edge case. Given gap #9
already showed users reaching for exactly this kind of de-noising, it's likely a
common enough preference (not a CLI-only edge case) to warrant its own generation
option in Phase 1 (e.g. a `spec.choice.http_transport_spans: none | root-only | full`
knob) rather than requiring hand-rolled middleware each time.

## 11. Google ADK's LLM spans hardcode `llm.provider: "google"` / `gen_ai.system: "gcp.vertex.agent"` regardless of the actual model backend

`google_adk_research`'s LLM calls don't go to Gemini/Vertex at all — `real_a2a/shared/llm.py::adk_model` wraps `google.adk.models.lite_llm.LiteLlm` pointed at OpenRouter (model `openrouter/nvidia/nemotron-3-nano-30b-a3b:free`). Pulled a real `call_llm` span from the `deepresearch` service to confirm what `openinference-instrumentation-google-adk` actually records:

```json
"llm.model_name": "openrouter/nvidia/nemotron-3-nano-30b-a3b:free",
"gen_ai.request.model": "openrouter/nvidia/nemotron-3-nano-30b-a3b:free",
"llm.provider": "google",
"gen_ai.system": "gcp.vertex.agent",
"gcp.vertex.agent.llm_request": "{...}",
"gcp.vertex.agent.llm_response": "{...}"
```

The model name is correctly captured (OpenRouter/nvidia), but `llm.provider` /
`gen_ai.system` are hardcoded to Google's own values — the instrumentor assumes
ADK == Vertex/Gemini and never inspects the actual `LiteLlm` model string to
correct the provider attribution, nor the `gcp.vertex.agent.*` attribute
namespace which is misleading here (nothing touched GCP or Vertex). Anyone
filtering/grouping a trace UI by provider would see this OpenRouter/nvidia call
bucketed under "google."

**Suggested fix:** `matrix.md § Google ADK` should flag this as a **known
instrumentor limitation** when `LiteLlm` targets a non-Google backend (OpenRouter,
Together, Groq, etc. via LiteLLM) — provider/system attribution can't be trusted
for non-Gemini ADK agents, and callers should be warned rather than discovering it
by inspecting raw span JSON. Longer term, worth raising upstream with
`openinference-instrumentation-google-adk` to derive `llm.provider` from the
`LiteLlm` model string's prefix instead of hardcoding it to `google`.

## 12. Outbound HTTP calls (`HTTPXClientInstrumentor`) add noisy, low-value spans — wanted for propagation only, not for spans

`observability.py`'s `init_tracing()` calls `HTTPXClientInstrumentor().instrument()`
globally, once per process, purely to inject `traceparent`/`tracestate` into the
admin -> child A2A calls (see spec.md's "shared wrap points"). But `instrument()`
does two things at once: header injection **and** span creation for every httpx
request the process makes — there's no way to get one without the other via this
API. Confirmed the fallout directly in a captured trace: a bare `POST` span (no
route, no meaningful attributes beyond URL/status) parented under CrewAI's own
`SQLite SQL Writer._execute_core` task span — this is the outbound OpenRouter LLM
API call that CrewAI's own `LLM` class makes via `litellm`/`httpx` under the hood.
It's pure noise: the *real* LLM call is already fully captured, with correct
attributes, by `CrewAIInstrumentor`/`GoogleADKInstrumentor`/`LangChainInstrumentor`
as a proper `LLM`-kind span — the httpx-level span duplicates it as an
undifferentiated transport call one level up. Same problem again for the A2A
`GET /public_agent_card` card-resolver call and any other incidental httpx traffic.

This is the exact same shape of problem as gap #10 (want context propagation,
don't want the span that comes bundled with it) — just on the *outbound* side
instead of the inbound ASGI side. The fix (not generated by the skill) is a
minimal outbound counterpart to `TraceContextMiddleware`: wrap only header
injection, no span:

```python
import httpx
from opentelemetry.propagate import inject

class _PropagatingTransport(httpx.AsyncHTTPTransport):
    async def handle_async_request(self, request):
        inject(request.headers)  # W3C traceparent/tracestate, no span opened
        return await super().handle_async_request(request)
```

(or equivalently, a lightweight `event_hooks={"request": [...]}` callback on the
shared `httpx.AsyncClient` used by `a2a_client.py::call_agent`) instead of
`HTTPXClientInstrumentor().instrument()`.

**Suggested fix:** `matrix.md § Context Propagation § Cross-service / cross-agent
network calls` currently only shows the "instrument httpx fully" recipe. It
should offer this inject-only alternative as the default (or at least a clearly
signposted option) for exactly the case that mattered here: a multi-agent app
where the *meaningful* LLM/tool spans are already produced by the framework
instrumentor, and the raw HTTP layer underneath is redundant, not additive.

## 13. Agent identity isn't consistently attached to spans — matrix.md's own "mandatory" attribute set was never actually generated

`matrix.md § Mandatory Span Attributes` requires, for every agent/chain span:
`openinference.span.kind` (`AGENT`/`CHAIN`/...), `agent.name`, `agent.role`,
`agent.framework` (OI) or `gen_ai.operation.name="invoke_agent"`,
`gen_ai.agent.{id,name,version,description}` (OTel-GenAI) — and Phase 2 § 2.2 of
`SKILL.md` lists this as a **required piece in every generated file**. In
practice, across this session's generated `observability.py` / `capture.py`, this
was never actually added:

- The fallback `agent.run` span opened by `capture.py`'s `open_or_enrich_span`
  carries `input.*`/`output.*`/status only — no `agent.name`, `agent.role`,
  `agent.framework`, `gen_ai.agent.name`, or `openinference.span.kind: "AGENT"`.
- CrewAI's own spans (`Crew_<uuid>.kickoff`, `Task Execution`, etc.) don't surface
  a stable, human-meaningful agent identity either — see gap #14 below.
- The **one** place agent identity does show up organically is Google ADK's own
  `call_llm` span (`gen_ai.agent.name: "deep_researcher"`), which the ADK
  instrumentor adds natively — not something the skill's generated code added,
  and not present on the equivalent CrewAI/LangGraph spans for the other two
  child services.

Net effect: to figure out *which agent* (admin / text2sql / rag / deepresearch)
produced a given span/trace, the only reliable signal is the `service.name`
resource attribute — which requires opening resource attributes in the UI, not
something visible while scanning a span/trace list.

**Suggested fix:** Phase 2 § 2.2's "Multi-agent attributes on every agent/chain
span" checklist item needs to be enforced, not just documented as a goal --
either the skill should generate the attribute-setting code for the fallback
span (`open_or_enrich_span`/`capture_run` should accept an `agent_name`/`agent_role`
parameter and set it), or Phase 3's `confirm` diff preview should surface "agent
identity attributes: present / missing" as an explicit checklist line so this
kind of silent omission gets caught before `tasks.json` is marked done.

## 14. Span and trace names are not meaningful at a glance

Related to #13 but distinct: even where attributes *are* present, the span
**names** shown in a trace list/waterfall are not descriptive on their own.
Examples pulled directly from this session's traces:

- `agent.run` — the fallback root span name is a generic constant; it doesn't say
  "text2sql" or "deepresearch" or carry the actual query.
- `Crew_3bcaf8ed-4ce9-41ff-b72c-8e0f1620c7c9.kickoff` — CrewAI's own span naming
  embeds the Crew's internal UUID, which is meaningless to a human scanning a
  trace list and different on every single run for what is logically "the same"
  operation.
- `Task Execution`, `Flow Execution`, `Environment Context`, `Crew Created` —
  CrewAI's generic internal step names, identical across every agent/run, giving
  no hint which query or which service they belong to without opening the span
  and reading `input.value`.
- The **trace** itself (as opposed to individual spans) has no name/summary at
  all in either backend's UI beyond its root span's name — so a trace list is a
  wall of `agent.run` / `Crew_<uuid>.kickoff` entries with no way to distinguish
  "the France query" from "the India query" without opening each one.

**Suggested fix:** the skill's fallback span (`open_or_enrich_span`) should accept
an optional human-readable name override (e.g. derived from the calling service's
`service_name` plus a short summary of the input) rather than the hardcoded
`"agent.run"` constant — e.g. `f"{service_name}.run"` at minimum, or
`f"{service_name}: {input_summary[:40]}"` if a short input preview is desired on
the span name itself (mind redaction — never put a redacted field's raw value in
a span *name*, only in attributes). This is squarely in the skill's control
(`capture.py`'s generated fallback), unlike CrewAI's own internal span naming
(`Crew_<uuid>.kickoff`, `Task Execution`, ...) which is upstream CrewAI behavior
the skill doesn't generate and can't rename — worth a note in `matrix.md § CrewAI`
that this is a known readability limitation of CrewAI's native instrumentor, so
users aren't surprised when only the top-level `agent.run`-equivalent span is
nameable and the CrewAI subtree stays generic.

## 15. Third-party SDKs can ship their own built-in OTel instrumentation that silently activates the moment `opentelemetry` becomes importable — the skill's detection phase doesn't check for this

After fixing gaps #9/#10, the trace was *still* full of unexplained spans:
`a2a.server.routes.jsonrpc_dispatcher.JsonRpcDispatcher.handle_requests`,
`a2a.server.request_handlers.default_request_handler_v2.DefaultRequestHandlerV2._setup_active_task`,
`a2a.server.events.event_queue_v2.EventQueueSource._dispatch_loop`, etc. — none of
these came from anything the skill generated, from CrewAI/LangGraph/Google ADK, or
from Starlette. Traced it to the installed `a2a-sdk` package itself:
`a2a/utils/telemetry.py` ships a `@trace_class`/`@trace_function` decorator pair
that the SDK applies directly to its own internal classes —
`JsonRpcDispatcher`, `DefaultRequestHandlerV2`, `DefaultRequestHandler`,
`EventQueueSource` (`event_queue_v2.py`), `event_consumer.py`,
`in_memory_queue_manager.py`, and all three client transports
(`grpc.py`/`jsonrpc.py`/`rest.py`) — with span names built as
`f'{cls.__module__}.{cls.__name__}.{name}'`, exactly matching what showed up.

The mechanism is worth calling out because it's easy to miss: the module does
`try: from opentelemetry import trace ... except ImportError: <use a no-op stub>`
at import time, gated by an env var (`OTEL_INSTRUMENTATION_A2A_SDK_ENABLED`,
default `true`). Before this session installed `opentelemetry-sdk`, the a2a-sdk's
own tracing was a silent no-op; the moment the skill's `pip_install`/`uv add` step
made `opentelemetry` importable, this **pre-existing, third-party, not-generated-
by-the-skill** instrumentation woke up and started emitting to whatever
`TracerProvider` the generated `observability.py` registered globally — with zero
code from either the skill or the user. `detect_framework.py` / `existing_setup.py`
(Phase 1 § 1.1) only look for observability config already wired up by the user's
own code (imports, env files) — they have no way to know that a *dependency*
(here, `a2a-sdk`) carries its own dormant instrumentation that the very act of
installing OpenTelemetry will trigger.

Fixed by setting `OTEL_INSTRUMENTATION_A2A_SDK_ENABLED=false` in `.env` (the SDK's
own documented escape hatch) — confirmed via a before/after trace comparison that
this removes every `a2a.server.*` span with no other side effects, leaving just
`agent.run` -> the framework's own spans (CrewAI/LangGraph/Google ADK).

**Suggested fix (the user's explicit ask):** give the user an explicit
enable/disable choice for exactly this class of thing **during skill execution**,
not just after-the-fact troubleshooting. Concretely:
- Phase 1 (detection) could maintain a small known-list of libraries that ship
  their own auto-activating OTel instrumentation gated by a documented env var
  (a2a-sdk's `OTEL_INSTRUMENTATION_A2A_SDK_ENABLED` is one; there are likely
  others in the ecosystem — gRPC, some ORMs, etc.) and, when one of those
  libraries is detected in the project's dependencies, surface a spec-phase
  question: *"`<package>` ships its own OpenTelemetry instrumentation that will
  activate once you install opentelemetry-sdk. Keep it enabled (adds
  `<package>`-internal spans) or disable it (`<ENV_VAR>=false`) for a
  cleaner trace focused on your agent/LLM spans?"* — same `confirm`-gate
  discipline as every other generation choice, recorded in `spec.choice`.
- At minimum, `matrix.md`/`self_host.md` should carry a short "known
  auto-instrumenting dependencies" appendix so a user who hits this (as happened
  here) has something to grep for instead of reading library source to find the
  responsible decorator.


# 16 Invalid type CrewContext for attribute 'crew_context' value. Expected one of ['bool', 'str', 'bytes', 'int', 'float'] or a sequence of those types
# 17 the flow sequence is not proper always
# 18 the root span should always carry input and output values