"""Enforce the documentation-hygiene invariants that CLAUDE.md currently asks
maintainers to uphold by hand.

These are the cross-file facts that drift silently:
  1. The framework x backend grid is restated in matrix.md AND README.md — the
     two must list the same frameworks and the same backend columns.
  2. Version pins (``pkg==X.Y.Z``) appear in the matrix's Verified Versions
     table AND in per-backend/per-framework install snippets — a package must
     not be pinned to two different versions across matrix.md.
  3. The convention-resolution rule documented in matrix.md must match what
     validate_setup.resolve_convention() actually computes.

Failing here means a PR introduced drift; fix the doc (or the code) so they
agree, per CLAUDE.md § Documentation Hygiene.
"""
from __future__ import annotations

import re
from pathlib import Path

import observent_matrix
import validate_setup

ROOT = Path(__file__).resolve().parent.parent
_REFS = ROOT / "skills" / "observent" / "references"
MATRIX = _REFS / "matrix.md"
OPENINFERENCE = _REFS / "openinference.md"
OTEL_GENAI = _REFS / "otel_genai.md"
EVAL = _REFS / "eval.md"
SKILL = ROOT / "skills" / "observent" / "SKILL.md"
EVAL_COMMAND = ROOT / "commands" / "observent-eval.toml"
README = ROOT / "README.md"

# Derived from the single source of truth (observent_matrix.py). matrix.md and
# README.md are checked against these display names; adding a framework/backend
# there flows here automatically.
FRAMEWORKS = observent_matrix.framework_display_names()
BACKEND_COLUMNS = observent_matrix.backend_display_names()


def _read(p: Path) -> str:
    return p.read_text(encoding="utf-8")


def test_matrix_lists_all_frameworks() -> None:
    text = _read(MATRIX)
    for fw in FRAMEWORKS:
        assert re.search(rf"^\|\s*{re.escape(fw)}\b", text, re.MULTILINE), fw


def test_readme_lists_all_frameworks() -> None:
    text = _read(README)
    for fw in FRAMEWORKS:
        assert re.search(rf"^\|\s*{re.escape(fw)}\b", text, re.MULTILINE), fw


def test_matrix_and_readme_share_backend_columns() -> None:
    matrix, readme = _read(MATRIX), _read(README)
    for backend in BACKEND_COLUMNS:
        assert backend in matrix, f"{backend} missing from matrix.md"
        assert backend in readme, f"{backend} missing from README.md"


def test_version_pins_are_internally_consistent() -> None:
    # No package may be pinned to two different versions within matrix.md.
    text = _read(MATRIX)
    pins: dict[str, set[str]] = {}
    for name, ver in re.findall(r"([A-Za-z0-9_.-]+)==([0-9][0-9A-Za-z.]*)", text):
        pins.setdefault(name, set()).add(ver)
    conflicts = {n: v for n, v in pins.items() if len(v) > 1}
    assert not conflicts, f"conflicting version pins in matrix.md: {conflicts}"


def test_verified_versions_table_pins_are_referenced() -> None:
    # Every package in the Verified Versions table should be pinned to the
    # same version where it's mentioned elsewhere in matrix.md (caught above),
    # and the table itself must be non-empty.
    text = _read(MATRIX)
    table = re.search(r"## Verified Versions(.+?)(?:\n## )", text, re.DOTALL)
    assert table, "Verified Versions section not found in matrix.md"
    rows = re.findall(r"\|\s*([A-Za-z0-9_.-]+)\s*\|\s*==([0-9][0-9A-Za-z.]*)\s*\|", table.group(1))
    assert len(rows) >= 10, f"expected the full pin table, found {len(rows)} rows"


def test_matrix_convention_columns_match_code() -> None:
    # Each product backend's per-backend convention (from the single source) must
    # match what resolve_convention() computes for that backend alone — Phoenix
    # OI, the other four OTel-GenAI.
    for backend, conv in observent_matrix.backend_conventions().items():
        assert validate_setup.resolve_convention([backend]) == conv


def _alias_table_keys() -> list[str]:
    """Backtick-quoted dotted attribute keys in eval.md's alias table rows."""
    text = _read(EVAL)
    section = re.search(r"## Cross-convention alias table(.+?)(?:\n## )", text, re.DOTALL)
    assert section, "Cross-convention alias table section not found in eval.md"
    keys: list[str] = []
    for line in section.group(1).splitlines():
        if not line.lstrip().startswith("|"):
            continue
        for tok in re.findall(r"`([a-z_]+(?:\.[a-z_.]+)+)`", line):
            if tok.split(".")[0] in {"llm", "gen_ai", "openinference", "tool", "tool_call"}:
                keys.append(tok)
    return keys


def test_eval_alias_table_keys_exist_in_canonical_refs() -> None:
    # Each attribute key the eval gate normalizes must be a real key documented in
    # openinference.md (OI / tool / openinference.* keys) or otel_genai.md (gen_ai.*),
    # so the cross-convention alias map can't silently drift from the specs.
    oi_text, otel_text = _read(OPENINFERENCE), _read(OTEL_GENAI)
    keys = _alias_table_keys()
    assert len(keys) >= 12, f"alias table looks too small ({len(keys)} keys parsed)"
    for key in keys:
        ref = otel_text if key.startswith("gen_ai.") else oi_text
        ref_name = "otel_genai.md" if key.startswith("gen_ai.") else "openinference.md"
        assert key in ref, f"eval.md alias key `{key}` not found in {ref_name}"


def test_eval_phase5_cross_references_resolve() -> None:
    # The eval feature's narrative surfaces must point at each other consistently.
    assert EVAL.is_file(), "references/eval.md missing"
    assert EVAL_COMMAND.is_file(), "commands/observent-eval.toml missing"
    skill = _read(SKILL)
    assert "Phase 5 — Evaluate" in skill, "SKILL.md missing Phase 5 section"
    assert "references/eval.md" in skill, "SKILL.md Phase 5 must cross-link references/eval.md"
    assert "eval_gate.py" in _read(EVAL_COMMAND), "observent-eval.toml must invoke eval_gate.py"


def test_matrix_header_convention_labels_match_code() -> None:
    # The 8x7 matrix header tags each backend with an italic convention label,
    # e.g. ``Arize Phoenix<br>*OI*`` / ``Langfuse<br>*OTel-GenAI*``. That label is
    # the canonical source's convention, written for humans — assert it matches.
    text = _read(MATRIX)
    label_to_conv = {"OI": "oi", "OTel-GenAI": "otel-genai"}
    for backend in observent_matrix.BACKENDS:
        m = re.search(rf"{re.escape(backend.display)}<br>\*([\w-]+)\*", text)
        assert m, f"{backend.display}: no convention label in matrix.md 8x7 header"
        label = m.group(1)
        assert label in label_to_conv, f"{backend.display}: unknown convention label *{label}*"
        assert label_to_conv[label] == backend.convention, (
            f"{backend.display}: matrix.md labels it *{label}* "
            f"but observent_matrix says {backend.convention}"
        )
