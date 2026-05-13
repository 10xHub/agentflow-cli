from pathlib import Path

from agentflow.qa.evaluation import (
    CriterionConfig,
    EvalConfig,
    EvalSet,
    EvalSetBuilder,
    MatchType,
    QuickEval,
    ReporterConfig,
    ReporterManager,
    ReporterOutput,
    TrajectoryCollector,
)

from graph.agent import app


EVAL_REPORT_DIR = Path("eval_reports")


def build_weather_agent_eval_set() -> EvalSet:
    """Build deterministic behavior checks for the weather agent."""
    return (
        EvalSetBuilder(name="weather-agent-regression")
        .add_case(
            query="Hi",
            expected="assistant",
            expected_node_order=["MAIN"],
            name="greeting_response",
            description="The agent responds to a greeting.",
        )
        .add_tool_test(
            query="What is the weather in London?",
            tool_name="get_weather",
            tool_args={"location": "London"},
            expected_response="London",
            case_id="weather_london",
        )
        .add_tool_test(
            query="Tell me the current weather in New York",
            tool_name="get_weather",
            tool_args={"location": "New York"},
            expected_response="New York",
            case_id="weather_new_york",
        )
        .add_tool_test(
            query="How is the weather in Tokyo today?",
            tool_name="get_weather",
            tool_args={"location": "Tokyo"},
            expected_response="Tokyo",
            case_id="weather_tokyo",
        )
        .build()
    )


def build_weather_agent_eval_config() -> EvalConfig:
    """Configure fast non-judge criteria for regression evaluation."""
    return EvalConfig(
        criteria={
            "response": CriterionConfig(
                threshold=0.6,
                match_type=MatchType.ANY_ORDER,
            ),
            "tool_usage": CriterionConfig(
                threshold=1.0,
                match_type=MatchType.EXACT,
                check_args=False,
            ),
            "node_order": CriterionConfig(
                threshold=0.8,
                match_type=MatchType.IN_ORDER,
            ),
        },
        mock_mode=True,
        verbose=True,
        reporter=ReporterConfig(
            enabled=True,
            output_dir=str(EVAL_REPORT_DIR),
            console=True,
            json_report=True,
            html=True,
            junit_xml=True,
            include_details=True,
            include_trajectory=True,
            include_node_responses=True,
            include_actual_response=True,
            include_tool_call_details=True,
            timestamp_files=True,
        ),
    )


def get_eval_set() -> EvalSet:
    """Return the eval set for CLI discovery (agentflow eval)."""
    return build_weather_agent_eval_set()


def get_eval_config() -> EvalConfig:
    """Return the eval config for CLI discovery (agentflow eval)."""
    return build_weather_agent_eval_config()


def run() -> ReporterOutput:
    """Entry point for agentflow eval CLI discovery.

    Runs the full eval and returns the reporter output (HTML + JSON + JUnit).
    """
    config = build_weather_agent_eval_config()
    collector = TrajectoryCollector(capture_all_events=True)
    report = QuickEval.run_sync(
        graph=app,
        collector=collector,
        eval_set=build_weather_agent_eval_set(),
        config=config,
        print_results=True,
    )
    EVAL_REPORT_DIR.mkdir(parents=True, exist_ok=True)
    return ReporterManager(config.reporter).run_all(report, output_dir=str(EVAL_REPORT_DIR))


if __name__ == "__main__":
    reporter_output = run()
    print(f"JSON report: {reporter_output.json_path}")  # noqa: T201
    print(f"HTML report: {reporter_output.html_path}")  # noqa: T201
    print(f"JUnit report: {reporter_output.junit_path}")  # noqa: T201
