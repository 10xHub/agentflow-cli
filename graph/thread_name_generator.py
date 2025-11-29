from agentflow_cli import ThreadNameGenerator


class MyNameGenerator(ThreadNameGenerator):
    async def generate_name(self, messages: list[str]) -> str:
        return "MyCustomThreadName"
