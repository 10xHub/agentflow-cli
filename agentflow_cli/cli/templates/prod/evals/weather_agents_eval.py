from agentflow.qa.evaluation import EvalConfig, EvalSet, EvalSetBuilder
from agentflow.qa.evaluation.config.presets import EvalPresets


def get_eval_config() -> EvalConfig:
    """Evaluation config for this file.

    EvalPresets provides ready-made criterion bundles.  Pick one that matches
    what your agent does, or call EvalPresets.combine() to mix them.

    Available presets:
        EvalPresets.response_quality()   — LLM judge on response accuracy
        EvalPresets.tool_usage()         — checks tool calls + response quality
        EvalPresets.conversation_flow()  — multi-turn conversation evaluation
        EvalPresets.comprehensive()      — all of the above combined
        EvalPresets.quick_check()        — fast ROUGE-based check, no LLM cost
    """
    return EvalPresets.tool_usage(threshold=0.6)


def get_eval_set() -> EvalSet:
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
