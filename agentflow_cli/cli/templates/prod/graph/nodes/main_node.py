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
            """,
        },
        {
            "role": "user",
            "content": f"Today Date is {datetime.now().strftime('%Y-%m-%d')}",
        },  # Inject current date into system prompt
    ],
    trim_context=True,
    reasoning_config=True,
    tool_node="TOOL",  # Registered tool node name
)
