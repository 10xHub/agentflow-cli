from agentflow.core.graph import ToolNode

from graph.tools.weather_tool import get_weather


tool_node = ToolNode(
    [
        get_weather,
    ]
)
