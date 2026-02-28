"""LlamaIndex ReActAgent configuration — test fixture."""

from llama_index.core.agent import ReActAgent
from llama_index.core.tools import FunctionTool
from llama_index.llms.openai import OpenAI


def lookup(query: str) -> str:
    """Look up information."""
    return query


lookup_tool = FunctionTool.from_defaults(fn=lookup)

agent = ReActAgent.from_tools(
    [lookup_tool],
    llm=OpenAI(model="gpt-4"),
    verbose=True,
)
