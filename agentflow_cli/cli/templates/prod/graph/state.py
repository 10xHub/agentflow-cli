from agentflow.core import AgentState


class WeatherState(AgentState):
    user_location: str = ""
