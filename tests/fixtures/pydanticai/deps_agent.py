"""PydanticAI agent with typed dependencies and system prompt functions."""

from dataclasses import dataclass

from pydantic_ai import Agent, RunContext


@dataclass
class MyDeps:
    """Dependencies for the agent."""

    user_name: str
    db_url: str


agent = Agent(
    'openai:gpt-4o',
    deps_type=MyDeps,
    system_prompt='You are a database assistant.',
)


@agent.system_prompt
def add_user_context(ctx: RunContext[MyDeps]) -> str:
    """Inject user context into the system prompt."""
    return f"Current user is {ctx.deps.user_name}"


@agent.tool
def query_database(ctx: RunContext[MyDeps], sql: str) -> str:
    """Execute a database query."""
    import os
    os.getenv("DB_PASSWORD")
    return f"Results from {ctx.deps.db_url}"
