from agentflow_cli import ThreadNameGenerator


class MyNameGenerator(ThreadNameGenerator):
    async def generate_name(self, messages: list[str]) -> str:
        # TODO: Implement logic to generate thread name based on messages
        return "MyCustomThreadName"
