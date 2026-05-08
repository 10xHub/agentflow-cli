from __future__ import annotations

import asyncio

from agentflow.qa import QuickTest
from agentflow.qa.evaluation import CriterionResult, EvalCaseResult, EvalReport, EvalSummary

from evals.weather_agents import (
    EVAL_REPORT_DIR,
    build_weather_agent_eval_config,
    build_weather_agent_eval_set,
    write_weather_agent_eval_reports,
)


def test_weather_agent_eval_set_covers_core_weather_behaviors() -> None:
    eval_set = build_weather_agent_eval_set()

    case_ids = {case.eval_id for case in eval_set.eval_cases}
    case_names = {case.name for case in eval_set.eval_cases}

    assert eval_set.name == "weather-agent-regression"
    assert len(eval_set.eval_cases) == 4
    assert "greeting_response" in case_names
    assert "weather_london" in case_ids
    assert "weather_new_york" in case_ids
    assert "weather_tokyo" in case_ids


def test_weather_agent_eval_config_uses_deterministic_criteria() -> None:
    config = build_weather_agent_eval_config()

    assert config.mock_mode is True
    assert set(config.criteria) == {"response", "tool_usage", "node_order"}
    assert config.criteria["tool_usage"].check_args is False
    assert config.reporter.output_dir == str(EVAL_REPORT_DIR)
    assert config.reporter.json_report is True
    assert config.reporter.html is True
    assert config.reporter.junit_xml is True


def test_write_weather_agent_eval_reports_creates_report_artifacts(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr("evals.weather_agents.EVAL_REPORT_DIR", tmp_path)
    report = EvalReport(
        eval_set_id="weather-agent-regression",
        eval_set_name="weather-agent-regression",
        results=[
            EvalCaseResult(
                eval_id="sample",
                name="sample",
                passed=True,
                actual_response="The weather in London is sunny",
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

    output = write_weather_agent_eval_reports(report)

    assert output.json_path is not None
    assert output.html_path is not None
    assert output.junit_path is not None
    assert "weather-agent-regression" in tmp_path.joinpath(output.json_path).read_text(
        encoding="utf-8"
    )


def test_agentflow_quick_test_smoke_for_expected_weather_greeting() -> None:
    result = QuickTest.single_turn(
        agent_response="Hello! I can help you check the weather anywhere. What location are you interested in?",
        user_message="Hi",
    )

    asyncio.run(result).assert_contains("weather").assert_no_errors()
