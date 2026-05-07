from __future__ import annotations

from agentflow.qa import QuickTest
from agentflow.qa.evaluation import CriterionResult, EvalCaseResult, EvalReport, EvalSummary

from evals.fashion_agent_eval import (
    EVAL_REPORT_DIR,
    build_fashion_agent_eval_config,
    build_fashion_agent_eval_set,
    write_fashion_agent_eval_reports,
)


def test_fashion_agent_eval_set_covers_core_sales_behaviors() -> None:
    eval_set = build_fashion_agent_eval_set()

    case_ids = {case.eval_id for case in eval_set.eval_cases}
    case_names = {case.name for case in eval_set.eval_cases}

    assert eval_set.name == "fashion-agent-regression"
    assert len(eval_set.eval_cases) == 4
    assert "greeting_mentions_company" in case_names
    assert "catalog_search_maroon_silk_wedding" in case_ids
    assert "preference_capture" in case_ids
    assert "virtual_try_on_photo_required" in case_ids


def test_fashion_agent_eval_config_uses_deterministic_criteria() -> None:
    config = build_fashion_agent_eval_config()

    assert config.mock_mode is True
    assert set(config.criteria) == {"response", "tool_usage", "node_order"}
    assert config.criteria["tool_usage"].check_args is False
    assert config.reporter.output_dir == str(EVAL_REPORT_DIR)
    assert config.reporter.json_report is True
    assert config.reporter.html is True
    assert config.reporter.junit_xml is True


def test_write_fashion_agent_eval_reports_creates_report_artifacts(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr("evals.fashion_agent_eval.EVAL_REPORT_DIR", tmp_path)
    report = EvalReport(
        eval_set_id="fashion-agent-regression",
        eval_set_name="fashion-agent-regression",
        results=[
            EvalCaseResult(
                eval_id="sample",
                name="sample",
                passed=True,
                actual_response="Fashionista Inc.",
                criterion_results=[
                    CriterionResult(
                        criterion="response",
                        score=1.0,
                        passed=True,
                        threshold=0.6,
                    )
                ],
            )
        ],
        summary=EvalSummary(
            total_cases=1,
            passed_cases=1,
            failed_cases=0,
            error_cases=0,
            pass_rate=1.0,
        ),
    )

    output = write_fashion_agent_eval_reports(report)

    assert output.json_path is not None
    assert output.html_path is not None
    assert output.junit_path is not None
    assert "fashion-agent-regression" in tmp_path.joinpath(output.json_path).read_text(
        encoding="utf-8"
    )


def test_agentflow_quick_test_smoke_for_expected_greeting_behavior() -> None:
    result = QuickTest.single_turn(
        agent_response="Welcome to Fashionista Inc. How can I help you find the right look?",
        user_message="Hello",
    )

    import asyncio

    asyncio.run(result).assert_contains("Fashionista Inc.").assert_no_errors()
