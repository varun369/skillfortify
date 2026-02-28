"""Agno agent with a custom Toolkit subclass -- test fixture."""

import requests

from agno.agent import Agent
from agno.tools import Function, Toolkit


class MyToolkit(Toolkit):
    def __init__(self):
        super().__init__(name="my_tools")
        self.register(Function(name="search", description="Search the web"))
        self.register(Function(name="summarize", description="Summarize text"))

    def search(self, query: str) -> str:
        return requests.get(f"https://api.search.com/v1?q={query}").text

    def summarize(self, text: str) -> str:
        return text[:100]


agent = Agent(
    name="Toolkit Agent",
    tools=[MyToolkit()],
    instructions=["Be helpful"],
)
