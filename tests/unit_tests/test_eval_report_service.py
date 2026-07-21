"""Unit tests for EvalReportService, which reads real `agentflow eval` JSON
reports (eval_reports/*.json, written by agentflow.qa.evaluation.reporters.json.JSONReporter)
instead of the dummy in-module data the evals router used to serve."""

import json

import pytest
from fastapi import HTTPException

from agentflow_cli.src.app.routers.evals.services.eval_report_service import (
    EvalReportService,
    _case_conversation,
    _case_input,
    _case_rubric,
    _case_score,
    _case_type,
    _format_ago,
    _format_duration,
)


def _criterion(name, score, threshold=0.8):
    return {
        "criterion": name,
        "score": score,
        "passed": score >= threshold,
        "threshold": threshold,
        "details": {},
        "error": None,
        "token_usage": {
            "input_tokens": 10,
            "output_tokens": 5,
            "cache_read_tokens": 0,
            "cache_creation_tokens": 0,
            "total_tokens": 15,
        },
    }


def _eval_case(eval_id, name, passed, score, duration=1.2):
    return {
        "eval_id": eval_id,
        "name": name,
        "passed": passed,
        "criterion_results": [_criterion("correctness", score)],
        "actual_trajectory": [],
        "actual_tool_calls": [],
        "actual_response": "The refund has been processed.",
        "messages": [{"role": "user", "content": "I want a refund for order #4471."}],
        "node_responses": [],
        "node_visits": [],
        "duration_seconds": duration,
        "error": None,
        "metadata": {},
        "turn_results": [],
        "token_usage": {
            "input_tokens": 100,
            "output_tokens": 50,
            "cache_read_tokens": 0,
            "cache_creation_tokens": 0,
            "total_tokens": 150,
        },
        "agent_token_usage": {
            "input_tokens": 0,
            "output_tokens": 0,
            "cache_read_tokens": 0,
            "cache_creation_tokens": 0,
            "total_tokens": 0,
        },
        "node_details": [],
    }


def _sim_case(eval_id, name, passed, score):
    case = _eval_case(eval_id, name, passed, score, duration=4.3)
    case["metadata"] = {"turns": 3, "goals_achieved": passed, "completed": True}
    case["actual_response"] = (
        "USER: I've been charged three times, fix it.\n"
        "AGENT: I understand, let me look into that.\n"
        "USER: Just get me a person!"
    )
    return case


def _report(eval_set_id, timestamp, cases, eval_set_name=""):
    passed = sum(1 for c in cases if c["passed"])
    total = len(cases)
    return {
        "eval_set_id": eval_set_id,
        "eval_set_name": eval_set_name,
        "results": cases,
        "summary": {
            "total_cases": total,
            "passed_cases": passed,
            "failed_cases": total - passed,
            "error_cases": 0,
            "pass_rate": passed / total if total else 0.0,
            "avg_duration_seconds": 1.5,
            "total_duration_seconds": 1.5 * total,
            "criterion_stats": {},
            "total_token_usage": {
                "input_tokens": 100 * total,
                "output_tokens": 50 * total,
                "cache_read_tokens": 0,
                "cache_creation_tokens": 0,
                "total_tokens": 150 * total,
            },
            "per_case_token_usage": {},
            "avg_tokens_per_case": 150.0,
        },
        "config_used": {"model": "gemini-2.0-flash"},
        "timestamp": timestamp,
        "metadata": {},
    }


class TestPureHelpers:
    def test_format_duration(self):
        assert _format_duration(1.234) == "1.2s"

    def test_format_ago_minutes_hours_days(self):
        now = 1_000_000.0
        assert _format_ago(now - 30, now) == "just now"
        assert _format_ago(now - 5 * 60, now) == "5m ago"
        assert _format_ago(now - 3 * 3600, now) == "3h ago"
        assert _format_ago(now - 2 * 86400, now) == "2d ago"

    def test_case_type_eval_vs_sim(self):
        assert _case_type(_eval_case("c1", "n", True, 0.9)) == "eval"
        assert _case_type(_sim_case("c2", "n", True, 0.9)) == "sim"

    def test_case_score_averages_criteria(self):
        case = _eval_case("c1", "n", True, 0.8)
        case["criterion_results"].append(_criterion("tone", 0.6))
        assert _case_score(case) == pytest.approx(0.7)

    def test_case_score_falls_back_to_passed_when_no_criteria(self):
        case = _eval_case("c1", "n", True, 0.8)
        case["criterion_results"] = []
        assert _case_score(case) == 1.0
        case["passed"] = False
        assert _case_score(case) == 0.0

    def test_case_input_reads_first_user_message(self):
        case = _eval_case("c1", "n", True, 0.8)
        assert _case_input(case) == "I want a refund for order #4471."

    def test_case_input_missing_falls_back(self):
        case = _eval_case("c1", "n", True, 0.8)
        case["messages"] = []
        assert _case_input(case) == "—"

    def test_case_rubric_includes_weighted_score_row(self):
        case = _eval_case("c1", "n", True, 0.8)
        rubric = _case_rubric(case)
        assert rubric[0] == {"key": "correctness", "value": 0.8, "tone": "accent"}
        assert rubric[-1]["key"] == "weighted score"

    def test_case_rubric_none_when_no_criteria(self):
        case = _eval_case("c1", "n", True, 0.8)
        case["criterion_results"] = []
        assert _case_rubric(case) is None

    def test_case_conversation_none_for_eval_case(self):
        assert _case_conversation(_eval_case("c1", "n", True, 0.8)) is None

    def test_case_conversation_parses_sim_transcript(self):
        turns = _case_conversation(_sim_case("c2", "n", False, 0.5))
        assert turns == [
            {"role": "sim", "text": "I've been charged three times, fix it."},
            {"role": "agent", "text": "I understand, let me look into that."},
            {"role": "sim", "text": "Just get me a person!"},
        ]


class TestEvalReportServiceListRuns:
    def test_empty_directory_returns_no_runs(self, tmp_path):
        service = EvalReportService(reports_dir=tmp_path)
        assert service.list_runs() == []

    def test_missing_directory_returns_no_runs(self, tmp_path):
        service = EvalReportService(reports_dir=tmp_path / "does_not_exist")
        assert service.list_runs() == []

    def test_lists_runs_sorted_newest_first_with_run_numbers(self, tmp_path):
        older = _report("customer_support", 1_000_000.0, [_eval_case("c1", "n", True, 0.9)])
        newer = _report("customer_support", 1_000_500.0, [_eval_case("c1", "n", False, 0.5)])
        (tmp_path / "customer_support_20260101_000000.json").write_text(json.dumps(older))
        (tmp_path / "customer_support_20260101_001000.json").write_text(json.dumps(newer))

        service = EvalReportService(reports_dir=tmp_path)
        runs = service.list_runs(now=1_000_500.0 + 60)

        assert [r["run"] for r in runs] == ["#2", "#1"]
        assert runs[0]["status"] == "fail"
        assert runs[1]["status"] == "pass"
        assert runs[0]["cases"] == 1
        assert runs[0]["rate"] == 0.0
        assert runs[1]["rate"] == 100.0

    def test_run_numbers_are_per_eval_set(self, tmp_path):
        cs = _report("customer_support", 1_000_000.0, [_eval_case("c1", "n", True, 0.9)])
        rs = _report("refund_simulator", 1_000_100.0, [_sim_case("c1", "n", True, 0.9)])
        (tmp_path / "customer_support_1.json").write_text(json.dumps(cs))
        (tmp_path / "refund_simulator_1.json").write_text(json.dumps(rs))

        service = EvalReportService(reports_dir=tmp_path)
        runs = {r["name"]: r for r in service.list_runs(now=1_000_100.0)}

        assert runs["customer_support"]["run"] == "#1"
        assert runs["refund_simulator"]["run"] == "#1"

    def test_skips_unparseable_json_files(self, tmp_path):
        (tmp_path / "broken.json").write_text("{not valid json")
        good = _report("customer_support", 1_000_000.0, [_eval_case("c1", "n", True, 0.9)])
        (tmp_path / "good.json").write_text(json.dumps(good))

        service = EvalReportService(reports_dir=tmp_path)
        runs = service.list_runs(now=1_000_000.0)

        assert len(runs) == 1
        assert runs[0]["name"] == "customer_support"


class TestEvalReportServiceRunDetail:
    def test_unknown_run_id_raises_404(self, tmp_path):
        service = EvalReportService(reports_dir=tmp_path)
        with pytest.raises(HTTPException) as exc:
            service.get_run_detail("nope")
        assert exc.value.status_code == 404

    def test_detail_shape_for_single_run(self, tmp_path):
        report = _report(
            "customer_support",
            1_000_000.0,
            [
                _eval_case("c1", "greets user", True, 0.9),
                _eval_case("c2", "refunds order", False, 0.4),
            ],
            eval_set_name="customer-support",
        )
        (tmp_path / "customer_support_run1.json").write_text(json.dumps(report))

        service = EvalReportService(reports_dir=tmp_path)
        run_id = "customer_support_run1"
        detail = service.get_run_detail(run_id)

        assert detail["title"] == "customer-support · run #1"
        assert detail["status"] == "fail"
        assert detail["rate"] == 50.0
        assert len(detail["cases"]) == 2
        assert detail["cases"][0]["id"] == "c1"
        assert detail["cases"][0]["status"] == "pass"
        assert detail["cases"][1]["status"] == "fail"
        assert detail["regression"] is None
        stat_labels = [s["label"] for s in detail["stats"]]
        assert "cases" in stat_labels
        assert "avg latency" in stat_labels

    def test_detail_includes_regression_against_previous_run_of_same_set(self, tmp_path):
        older = _report(
            "customer_support",
            1_000_000.0,
            [_eval_case("c1", "n", True, 0.9), _eval_case("c2", "n", True, 0.85)],
        )
        newer = _report(
            "customer_support",
            1_000_500.0,
            [_eval_case("c1", "n", True, 0.88), _eval_case("c2", "n", False, 0.4)],
        )
        (tmp_path / "customer_support_a.json").write_text(json.dumps(older))
        (tmp_path / "customer_support_b.json").write_text(json.dumps(newer))

        service = EvalReportService(reports_dir=tmp_path)
        detail = service.get_run_detail("customer_support_b")

        assert detail["regression"] is not None
        assert detail["regression"]["note"]["current"].startswith("run #2")
        assert detail["regression"]["note"]["prev"].startswith("run #1")
        newly_failing = next(
            s for s in detail["regression"]["summary"] if s["label"] == "newly failing"
        )
        assert newly_failing["value"] == "1"
        row_c2 = next(
            r for r in detail["regression"]["rows"] if r["name"] == "n" and r["stay"] is False
        )
        assert row_c2["flip"] == "pass → fail"

        older_detail = service.get_run_detail("customer_support_a")
        assert older_detail["regression"] is None
