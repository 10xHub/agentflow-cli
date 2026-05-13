from __future__ import annotations

import asyncio

from agentflow.qa import QuickTest
from agentflow.qa.evaluation import (
    CriterionResult,
    EvalCaseResult,
    EvalReport,
    EvalSummary,
    ReporterConfig,
    ReporterManager,
)

from evals.weather_agents_eval import get_eval_set


def test_eval_set_covers_core_weather_behaviors() -> None:
    eval_set = get_eval_set()

    case_ids = {case.eval_id for case in eval_set.eval_cases}
    case_names = {case.name for case in eval_set.eval_cases}

    assert eval_set.name == "weather-agent-regression"
    assert len(eval_set.eval_cases) == 4
    assert "greeting_response" in case_names
    assert "weather_london" in case_ids
    assert "weather_new_york" in case_ids
    assert "weather_tokyo" in case_ids


def test_reporter_writes_html_and_json_artifacts(tmp_path) -> None:
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

    output = ReporterManager(
        ReporterConfig(output_dir=str(tmp_path), html=True, json_report=True, console=False)
    ).run_all(report, output_dir=str(tmp_path))

    assert output.json_path is not None
    assert output.html_path is not None
    assert "weather-agent-regression" in tmp_path.joinpath(output.json_path).read_text(
        encoding="utf-8"
    )


def test_agentflow_quick_test_smoke_for_expected_weather_greeting() -> None:
    result = QuickTest.single_turn(
        agent_response="Hello! I can help you check the weather anywhere. What location are you interested in?",
        user_message="Hi",
    )

    asyncio.run(result).assert_contains("weather").assert_no_errors()
