"""Unit tests for the eval gate runner (skills/observent/scripts/eval_gate.py).

Covers: span normalization across both conventions, cross-convention metric
parity, each assertion family (budgets / behavior / redaction / regression /
judge), baseline regression math, exit codes, and JUnit output well-formedness.
"""
from __future__ import annotations

import json
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

import eval_gate


def _llm_oi(prompt: int, completion: int, model: str = "claude-sonnet-4-6") -> dict[str, Any]:
    return {
        "name": "llm",
        "parent_id": "0xroot",
        "start_time": "2026-06-25T10:00:01Z",
        "end_time": "2026-06-25T10:00:03Z",
        "status": {"status_code": "OK"},
        "attributes": {
            "openinference.span.kind": "LLM",
            "llm.model_name": model,
            "llm.token_count.prompt": prompt,
            "llm.token_count.completion": completion,
            "llm.token_count.total": prompt + completion,
        },
    }


def _llm_otel(prompt: int, completion: int, model: str = "claude-sonnet-4-6") -> dict[str, Any]:
    return {
        "name": "chat",
        "parent_id": "0xroot",
        "start_time": "2026-06-25T10:00:01Z",
        "end_time": "2026-06-25T10:00:03Z",
        "status": {"status_code": "OK"},
        "attributes": {
            "gen_ai.operation.name": "chat",
            "gen_ai.request.model": model,
            "gen_ai.usage.input_tokens": prompt,
            "gen_ai.usage.output_tokens": completion,
        },
    }


def _root(kind_attr: dict[str, Any], seconds: float = 18.0, status: str = "OK") -> dict[str, Any]:
    return {
        "name": "agent.run",
        "parent_id": None,
        "start_time": "2026-06-25T10:00:00.000000Z",
        "end_time": f"2026-06-25T10:00:{seconds:09.6f}Z",
        "status": {"status_code": status},
        "attributes": kind_attr,
    }


def _write_spans(path: Path, raw: list[dict[str, Any]]) -> Path:
    path.write_text("\n".join(json.dumps(r) for r in raw), encoding="utf-8")
    return path


def _agent_root(**kw: Any) -> dict[str, Any]:
    return _root({"openinference.span.kind": "AGENT"}, **kw)


# --------------------------------------------------------------------------- #
# Normalization + convention parity
# --------------------------------------------------------------------------- #


def test_normalize_oi_llm_span() -> None:
    span = eval_gate.normalize_span(_llm_oi(2000, 500))
    assert span.kind == "llm"
    assert span.model == "claude-sonnet-4-6"
    assert span.prompt_tokens == 2000
    assert span.completion_tokens == 500
    assert span.total_tokens == 2500


def test_normalize_otel_llm_span() -> None:
    span = eval_gate.normalize_span(_llm_otel(2000, 500))
    assert span.kind == "llm"
    assert span.model == "claude-sonnet-4-6"
    assert span.prompt_tokens == 2000
    assert span.completion_tokens == 500
    # total derived when no explicit total key (OTel-GenAI has none).
    assert span.total_tokens == 2500


def test_convention_parity_identical_metrics() -> None:
    oi = [_root({"openinference.span.kind": "AGENT"}), _llm_oi(2000, 500), _llm_oi(1800, 400)]
    otel = [_root({"gen_ai.operation.name": "invoke_agent"}), _llm_otel(2000, 500), _llm_otel(1800, 400)]
    m_oi = eval_gate.aggregate([eval_gate.normalize_span(s) for s in oi], {})
    m_otel = eval_gate.aggregate([eval_gate.normalize_span(s) for s in otel], {})
    assert m_oi.as_dict() == m_otel.as_dict()
    assert m_oi.total_tokens == 4700
    assert m_oi.llm_calls == 2
    assert m_oi.root_latency_ms == 18000.0


def test_root_latency_from_root_span_only() -> None:
    raw = [_agent_root(seconds=12.0), _llm_oi(10, 10)]
    spans = [eval_gate.normalize_span(s) for s in raw]
    assert eval_gate.aggregate(spans, {}).root_latency_ms == 12000.0


# --------------------------------------------------------------------------- #
# Budgets
# --------------------------------------------------------------------------- #


def test_budget_pass_and_fail() -> None:
    spans = [eval_gate.normalize_span(s) for s in [_agent_root(), _llm_oi(2000, 500)]]
    metrics = eval_gate.aggregate(spans, {})
    ok = eval_gate.check_budgets({"budgets": {"max_total_tokens": 8000}}, spans, metrics)
    assert ok[0].status == eval_gate.PASS
    bad = eval_gate.check_budgets({"budgets": {"max_total_tokens": 1000}}, spans, metrics)
    assert bad[0].status == eval_gate.FAIL


def test_cost_budget_skipped_without_rates() -> None:
    spans = [eval_gate.normalize_span(_llm_oi(2000, 500))]
    metrics = eval_gate.aggregate(spans, {})
    checks = eval_gate.check_budgets({"budgets": {"max_cost_usd": 0.05}}, spans, metrics)
    assert checks[0].status == eval_gate.SKIP


def test_cost_budget_enforced_with_rates() -> None:
    rates = {"claude-sonnet-4-6": {"input_per_1k": 0.003, "output_per_1k": 0.015}}
    spans = [eval_gate.normalize_span(_llm_oi(2000, 500))]
    metrics = eval_gate.aggregate(spans, rates)
    # 2.0*0.003 + 0.5*0.015 = 0.0135
    assert round(metrics.cost_usd, 4) == 0.0135
    spec = {"budgets": {"max_cost_usd": 0.05}, "cost_rates": rates}
    assert eval_gate.check_budgets(spec, spans, metrics)[0].status == eval_gate.PASS


# --------------------------------------------------------------------------- #
# Behavior
# --------------------------------------------------------------------------- #


def test_behavior_require_span_kinds_and_tools() -> None:
    raw = [
        _root({"openinference.span.kind": "AGENT"}),
        _llm_oi(10, 10),
        {
            "name": "web_search",
            "parent_id": "0xroot",
            "start_time": "2026-06-25T10:00:07Z",
            "end_time": "2026-06-25T10:00:08Z",
            "status": {"status_code": "OK"},
            "attributes": {"openinference.span.kind": "TOOL", "tool.name": "web_search"},
        },
    ]
    spans = [eval_gate.normalize_span(s) for s in raw]
    metrics = eval_gate.aggregate(spans, {})
    spec = {"behavior": {"require_span_kinds": ["agent", "llm", "tool"], "require_tools": ["web_search"]}}
    checks = {c.name: c.status for c in eval_gate.check_behavior(spec, spans, metrics)}
    assert checks["behavior.require_span_kinds"] == eval_gate.PASS
    assert checks["behavior.require_tools"] == eval_gate.PASS

    spec_missing = {"behavior": {"require_tools": ["calculator"], "forbid_tools": ["web_search"]}}
    checks2 = {c.name: c.status for c in eval_gate.check_behavior(spec_missing, spans, metrics)}
    assert checks2["behavior.require_tools"] == eval_gate.FAIL
    assert checks2["behavior.forbid_tools"] == eval_gate.FAIL


def test_otel_tool_name_from_span_name() -> None:
    span = eval_gate.normalize_span(
        {
            "name": "execute_tool web_search",
            "parent_id": "0xroot",
            "start_time": "2026-06-25T10:00:07Z",
            "end_time": "2026-06-25T10:00:08Z",
            "status": {"status_code": "OK"},
            "attributes": {"gen_ai.operation.name": "execute_tool"},
        }
    )
    assert span.kind == "tool"
    assert span.tool_name == "web_search"


def test_behavior_expect_llm_calls_range_and_error_status() -> None:
    raw = [_root({"openinference.span.kind": "AGENT"}, status="ERROR"), _llm_oi(10, 10)]
    spans = [eval_gate.normalize_span(s) for s in raw]
    metrics = eval_gate.aggregate(spans, {})
    spec = {"behavior": {"expect_llm_calls": [1, 3], "no_error_status": True}}
    checks = {c.name: c.status for c in eval_gate.check_behavior(spec, spans, metrics)}
    assert checks["behavior.expect_llm_calls"] == eval_gate.PASS
    assert checks["behavior.no_error_status"] == eval_gate.FAIL


# --------------------------------------------------------------------------- #
# Redaction
# --------------------------------------------------------------------------- #


def test_redaction_detects_planted_leaks() -> None:
    leaky = _root({"openinference.span.kind": "AGENT", "input.email": "jane.doe@example.com"})
    spans = [eval_gate.normalize_span(leaky)]
    checks = eval_gate.check_redaction({"redaction": {"assert_no_leaks": True}}, spans)
    assert checks[0].status == eval_gate.FAIL


def test_redaction_passes_when_redacted() -> None:
    clean = _root({"openinference.span.kind": "AGENT", "input.email": "***REDACTED***"})
    spans = [eval_gate.normalize_span(clean)]
    checks = eval_gate.check_redaction({"redaction": {"assert_no_leaks": True}}, spans)
    assert checks[0].status == eval_gate.PASS


def test_redaction_skipped_when_not_requested() -> None:
    spans = [eval_gate.normalize_span(_root({"openinference.span.kind": "AGENT"}))]
    assert eval_gate.check_redaction({}, spans) == []


# --------------------------------------------------------------------------- #
# Regression
# --------------------------------------------------------------------------- #


def test_regression_math() -> None:
    metrics = eval_gate.Metrics(total_tokens=5500, root_latency_ms=18000.0)
    baseline = {"metrics": {"total_tokens": 5000, "root_latency_ms": 18000.0}}
    spec = {"regression": {"max_increase_pct": 20, "metrics": ["total_tokens"]}}
    assert eval_gate.check_regression(spec, metrics, baseline)[0].status == eval_gate.PASS  # +10%

    spec_tight = {"regression": {"max_increase_pct": 5, "metrics": ["total_tokens"]}}
    assert eval_gate.check_regression(spec_tight, metrics, baseline)[0].status == eval_gate.FAIL  # +10% > 5%


def test_regression_skips_without_baseline() -> None:
    spec = {"regression": {"max_increase_pct": 20}}
    checks = eval_gate.check_regression(spec, eval_gate.Metrics(), None)
    assert checks[0].status == eval_gate.SKIP


# --------------------------------------------------------------------------- #
# Judge + exit codes
# --------------------------------------------------------------------------- #


def test_judge_criteria_are_needs_agent() -> None:
    spec = {"judge": {"criteria": [{"id": "relevant", "prompt": "Relevant?"}]}}
    checks = eval_gate.collect_judge(spec)
    assert checks[0].name == "judge.relevant"
    assert checks[0].status == eval_gate.NEEDS_AGENT


def test_is_passing_treats_needs_agent_as_skip_by_default() -> None:
    checks = [eval_gate.Check("a", eval_gate.PASS), eval_gate.Check("j", eval_gate.NEEDS_AGENT)]
    assert eval_gate.is_passing(checks, fail_on_unjudged=False) is True
    assert eval_gate.is_passing(checks, fail_on_unjudged=True) is False
    checks.append(eval_gate.Check("b", eval_gate.FAIL))
    assert eval_gate.is_passing(checks, fail_on_unjudged=False) is False


def test_main_exit_codes(tmp_path: Path) -> None:
    spans = _write_spans(
        tmp_path / "spans.jsonl",
        [_root({"openinference.span.kind": "AGENT"}), _llm_oi(2000, 500)],
    )
    spec = tmp_path / "eval.json"
    spec.write_text(json.dumps({"budgets": {"max_total_tokens": 8000}}), encoding="utf-8")
    assert eval_gate.main(["--spec", str(spec), "--spans", str(spans)]) == 0

    spec.write_text(json.dumps({"budgets": {"max_total_tokens": 100}}), encoding="utf-8")
    assert eval_gate.main(["--spec", str(spec), "--spans", str(spans)]) == 1


def test_update_baseline_writes_file(tmp_path: Path) -> None:
    spans = _write_spans(tmp_path / "spans.jsonl", [_agent_root(), _llm_oi(2000, 500)])
    spec = tmp_path / "eval.json"
    spec.write_text(json.dumps({"regression": {"max_increase_pct": 20}}), encoding="utf-8")
    baseline = tmp_path / "baseline.json"
    argv = ["--spec", str(spec), "--spans", str(spans), "--baseline", str(baseline), "--update-baseline"]
    rc = eval_gate.main(argv)
    assert rc == 0
    written = json.loads(baseline.read_text(encoding="utf-8"))
    assert written["metrics"]["total_tokens"] == 2500


def test_html_report_is_self_contained() -> None:
    checks = [
        eval_gate.Check("budget.total_tokens", eval_gate.PASS, "209 <= 4000 tokens"),
        eval_gate.Check("regression.total_tokens", eval_gate.FAIL, "+43% vs baseline"),
        eval_gate.Check("judge.relevant", eval_gate.NEEDS_AGENT, "Relevant?"),
    ]
    metrics = eval_gate.Metrics(total_tokens=300, llm_calls=2)
    html = eval_gate.render_html(checks, metrics, ok=False)
    assert html.startswith("<!doctype html>")
    assert "eval gate: FAIL" in html
    html.encode("ascii")  # must be ASCII-safe: stdout redirect uses the platform locale
    assert "http://" not in html and "https://" not in html  # no external assets
    assert "budget.total_tokens" in html and "regression.total_tokens" in html
    assert 'class="badge fail"' in html and 'class="badge needs-agent"' in html
    assert "300" in html  # metrics card rendered


def test_main_html_format(tmp_path: Path, capsys: Any) -> None:
    spans = _write_spans(tmp_path / "spans.jsonl", [_agent_root(), _llm_oi(2000, 500)])
    spec = tmp_path / "eval.json"
    spec.write_text(json.dumps({"budgets": {"max_total_tokens": 8000}}), encoding="utf-8")
    rc = eval_gate.main(["--spec", str(spec), "--spans", str(spans), "--format", "html"])
    out = capsys.readouterr().out
    assert rc == 0
    assert out.startswith("<!doctype html>")
    assert "eval gate: PASS" in out


def test_junit_output_is_well_formed() -> None:
    checks = [
        eval_gate.Check("budget.total_tokens", eval_gate.PASS, "ok"),
        eval_gate.Check("budget.cost_usd", eval_gate.FAIL, "too high"),
        eval_gate.Check("judge.relevant", eval_gate.NEEDS_AGENT, "Relevant?"),
    ]
    xml = eval_gate.render_junit(checks, ok=False)
    root = ET.fromstring(xml)
    assert root.tag == "testsuite"
    assert root.attrib["failures"] == "1"
    assert root.attrib["skipped"] == "1"
    assert len(root.findall("testcase")) == 3
