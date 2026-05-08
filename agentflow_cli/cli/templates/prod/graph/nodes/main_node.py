from datetime import datetime

from agentflow.core.graph.agent import Agent


agent = Agent(
    model="gemini-3-flash-preview",
    provider="google",
    system_prompt=[
        {
            "role": "system",
            "content": """
                You are a helpful assistant.
                Your task is to assist the user in finding information and answering questions.
                User Current Location: {user_location}
                If missing information, ask the user for clarification.
            """,
        },
        {
            "role": "user",
            "content": f"Today Date is {datetime.now().strftime('%Y-%m-%d')}",
        },
    ],
    trim_context=True,
    reasoning_config=True,
    tool_node="TOOL",  # Registered tool node name
)
