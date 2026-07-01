#!/usr/bin/env python3
"""Single source of truth for observent's framework x backend grid.

The shipped detector/validator scripts *and* the docs-consistency test all
derive their framework/backend tables from the structures here, so the 9x7
matrix is declared exactly once. The "Adding a new framework / backend" steps in
CLAUDE.md that used to touch ``detect_framework.py``, ``validate_setup.py`` and
``tests/test_docs_consistency.py`` separately now collapse to editing this file;
the prose references (matrix.md, README.md) are then checked against it.

Zero third-party deps (stdlib only) so the skill stays self-contained when it
ships verbatim to other agents via ``npx skills``.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Framework:
    slug: str  # code identifier used on the wire / in args, e.g. "langgraph"
    display: str  # UI / docs label, e.g. "LangGraph"
    modules: tuple[str, ...] = ()  # import names to probe; empty = not auto-detectable (Custom)


@dataclass(frozen=True)
class Backend:
    slug: str
    display: str
    convention: str  # "oi" | "otel-genai" ("" for detection-only extras)
    detect_modules: tuple[str, ...] = ()  # probeable import names; empty = service-only (SigNoz)


# Declaration order here is the order frameworks/backends appear in docs and in
# detector output. Keep it aligned with references/matrix.md and README.md.
FRAMEWORKS: tuple[Framework, ...] = (
    Framework("langgraph", "LangGraph", ("langgraph",)),
    Framework("crewai", "CrewAI", ("crewai",)),
    Framework("microsoft-agent-framework", "Microsoft Agent Framework", ("agent_framework",)),
    Framework("anthropic-agents", "Anthropic Agents SDK", ("anthropic",)),
    Framework("openai-agents", "OpenAI Agents SDK", ("agents",)),
    Framework("smolagents", "smolagents", ("smolagents",)),
    Framework("llama-index", "LlamaIndex", ("llama_index",)),
    # google-adk ships as the namespaced module ``google.adk`` (PyPI ``google-adk``).
    # Two probes: ``google.adk`` matches an installed module via find_spec, and
    # ``google_adk`` normalizes to ``google-adk`` for the declared-deps name match;
    # bare ``google`` is intentionally omitted (it over-matches google-genai etc.).
    Framework("google-adk", "Google ADK", ("google.adk", "google_adk")),
    Framework("custom", "Custom", ()),  # the no-framework path — never auto-detected
)

# The seven product backends — each has a UI column, a convention, and a
# validate_setup check. SigNoz and Jaeger have no detect module: they're backend
# services, not pip packages, so a bare ``opentelemetry`` install (below) is the
# only hint for them.
BACKENDS: tuple[Backend, ...] = (
    Backend("phoenix", "Arize Phoenix", "oi", ("phoenix", "arize_phoenix")),
    Backend("langfuse", "Langfuse", "otel-genai", ("langfuse",)),
    Backend("signoz", "SigNoz", "otel-genai", ()),
    Backend("elastic-apm", "Elastic APM", "otel-genai", ("elasticapm",)),
    Backend("langsmith", "LangSmith", "otel-genai", ("langsmith",)),
    Backend("opik", "Opik", "otel-genai", ("opik",)),
    Backend("jaeger", "Jaeger", "otel-genai", ()),
)

# Detection-only signals that are NOT product backends (no UI column, no
# convention, no validate check): a bare opentelemetry install hints at an
# existing OTel/SigNoz setup worth surfacing.
DETECTION_EXTRA_BACKENDS: tuple[Backend, ...] = (
    Backend("opentelemetry", "OpenTelemetry", "", ("opentelemetry",)),
)


@dataclass(frozen=True)
class AutoInstrumentingDep:
    slug: str  # pip/display slug, e.g. "a2a-sdk"
    display: str  # UI / docs label, e.g. "A2A SDK"
    modules: tuple[str, ...]  # import names to probe (installed / declared / imported)
    env_var: str  # the documented on/off gate for its built-in instrumentation
    enabled_by_default: bool  # value of env_var when unset


# Third-party libraries that ship their OWN OpenTelemetry instrumentation, dormant
# until ``opentelemetry`` becomes importable, then auto-emitting to whatever global
# TracerProvider is registered — with NO code from observent or the user. The
# skill's own ``pip install opentelemetry-sdk`` is exactly what wakes them, flooding
# the trace with library-internal spans. Each is gated by a documented env var so
# the spec phase can offer keep-vs-disable (same confirm discipline as any other
# generation choice). See references/matrix.md § Known auto-instrumenting
# dependencies. Keep this list conservative — only libraries with a *documented*
# on/off env var belong here.
KNOWN_AUTO_INSTRUMENTING_DEPS: tuple[AutoInstrumentingDep, ...] = (
    AutoInstrumentingDep(
        "a2a-sdk",
        "A2A SDK",
        # ``a2a`` matches an installed/imported module; ``a2a_sdk`` normalizes to
        # the ``a2a-sdk`` PyPI name for the declared-deps match (same two-probe
        # trick as google-adk above).
        ("a2a", "a2a_sdk"),
        "OTEL_INSTRUMENTATION_A2A_SDK_ENABLED",
        True,
    ),
)


# --- derived views the scripts / tests consume ---------------------------


def framework_detection_modules() -> dict[str, list[str]]:
    """slug -> probe modules, for auto-detectable frameworks only."""
    return {f.slug: list(f.modules) for f in FRAMEWORKS if f.modules}


def backend_detection_modules() -> dict[str, list[str]]:
    """slug -> probe modules: product backends that ship a package, plus extras."""
    out = {b.slug: list(b.detect_modules) for b in BACKENDS if b.detect_modules}
    out.update({b.slug: list(b.detect_modules) for b in DETECTION_EXTRA_BACKENDS})
    return out


def backend_conventions() -> dict[str, str]:
    """slug -> convention, for the seven product backends."""
    return {b.slug: b.convention for b in BACKENDS}


def auto_instrumenting_deps() -> list[dict[str, object]]:
    """The known dormant-instrumentation deps, as plain dicts for detector output."""
    return [
        {
            "slug": d.slug,
            "display": d.display,
            "modules": list(d.modules),
            "env_var": d.env_var,
            "enabled_by_default": d.enabled_by_default,
        }
        for d in KNOWN_AUTO_INSTRUMENTING_DEPS
    ]


def framework_display_names() -> list[str]:
    return [f.display for f in FRAMEWORKS]


def backend_display_names() -> list[str]:
    return [b.display for b in BACKENDS]
