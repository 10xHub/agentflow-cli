from agentflow.core.graph import StateGraph
from agentflow.core.state.message_context_manager import MessageContextManager
from agentflow.storage.checkpointer import InMemoryCheckpointer
from agentflow.utils.constants import END
from dotenv import load_dotenv
from injectq import InjectQ

from graph.utils.tool_decision import should_use_tools
from graph.validators.manager import callback_manager

from .nodes import agent, tool_node
from .state import WeatherState


load_dotenv()

checkpointer = InMemoryCheckpointer()

container = InjectQ.get_instance()

context_manager = MessageContextManager(
    max_messages=20,
    remove_tool_msgs=True,
)


graph = StateGraph(
    state=WeatherState(),
    container=container,
    context_manager=context_manager,
)
graph.add_node("MAIN", agent)
graph.add_node("TOOL", tool_node)
graph.add_conditional_edges(
    "MAIN",
    should_use_tools,
    {"TOOL": "TOOL", "MAIN": "MAIN", END: END},
)
graph.add_edge("TOOL", "MAIN")
graph.set_entry_point("MAIN")

app = graph.compile(
    checkpointer=checkpointer,
    callback_manager=callback_manager,
)
