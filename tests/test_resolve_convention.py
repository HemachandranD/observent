"""The set-level convention rule is a documented, non-trivial invariant
(references/matrix.md § Convention resolution). These tests pin it down so a
regression in the derivation can't slip through CI's import-only smoke test.
"""
from __future__ import annotations

import itertools

import pytest
import validate_setup
from validate_setup import BACKEND_CONVENTION, resolve_convention

OTEL_GENAI = ["langfuse", "signoz", "elastic-apm", "langsmith", "opik"]


def test_phoenix_alone_is_oi():
    assert resolve_convention(["phoenix"]) == "oi"


@pytest.mark.parametrize("backend", OTEL_GENAI)
def test_single_otel_genai_backend(backend):
    assert resolve_convention([backend]) == "otel-genai"


@pytest.mark.parametrize("backend", OTEL_GENAI)
def test_phoenix_plus_one_otel_genai_is_both(backend):
    assert resolve_convention(["phoenix", backend]) == "both"
    # Order must not matter.
    assert resolve_convention([backend, "phoenix"]) == "both"


def test_all_backends_is_both():
    assert resolve_convention(["phoenix", *OTEL_GENAI]) == "both"


def test_otel_genai_subset_never_promotes_to_both():
    # Any non-empty subset of the OTel-GenAI backends (no Phoenix) stays
    # otel-genai, regardless of how many are combined.
    for r in range(1, len(OTEL_GENAI) + 1):
        for combo in itertools.combinations(OTEL_GENAI, r):
            assert resolve_convention(list(combo)) == "otel-genai"


def test_empty_set_raises():
    with pytest.raises(ValueError):
        resolve_convention([])


def test_rule_covers_every_known_backend():
    # Guard against adding a backend to CHECKS/BACKEND_CONVENTION without
    # teaching resolve_convention about it.
    for backend in validate_setup.CHECKS:
        assert backend in BACKEND_CONVENTION
        assert resolve_convention([backend]) in {"oi", "otel-genai"}
