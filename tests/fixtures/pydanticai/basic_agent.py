"""Basic PydanticAI agent with a single tool."""

from pydantic_ai import Agent

agent = Agent(
    'openai:gpt-4o',
    system_prompt='You are a helpful assistant.',
)


@agent.tool_plain
def get_greeting(name: str) -> str:
    """Return a greeting for the given name."""
    return f"Hello, {name}!"
