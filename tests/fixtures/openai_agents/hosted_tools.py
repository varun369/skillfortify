"""Fixture: agent using hosted tools (WebSearch, FileSearch, CodeInterpreter).

Used by test_openai_agents.py to verify detection of:
- WebSearchTool, FileSearchTool, CodeInterpreterTool imports
- Agent instantiation referencing hosted tools
"""
from agents import Agent
from agents.tools import WebSearchTool, FileSearchTool, CodeInterpreterTool


search_tool = WebSearchTool()
file_tool = FileSearchTool()
code_tool = CodeInterpreterTool()

agent = Agent(
    name="research_agent",
    instructions="You research topics using web search and analyze files.",
    tools=[search_tool, file_tool, code_tool],
    model="gpt-4o",
)
