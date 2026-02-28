"""Fixture: agent with input/output guardrails.

Used by test_openai_agents.py to verify detection of:
- InputGuardrail / OutputGuardrail imports and usage
- Guardrail functions referenced in agent definition
"""
from agents import Agent, InputGuardrail, OutputGuardrail, function_tool
from pydantic import BaseModel


class SafetyCheck(BaseModel):
    is_safe: bool
    reason: str


@function_tool
def search_docs(query: str) -> str:
    """Search internal documentation."""
    return f"Results for: {query}"


async def check_input(ctx, agent, input_text):
    """Validate that input is safe."""
    return SafetyCheck(is_safe=True, reason="Input is clean")


async def check_output(ctx, agent, output_text):
    """Validate that output is safe."""
    return SafetyCheck(is_safe=True, reason="Output is clean")


agent = Agent(
    name="guarded_agent",
    instructions="You answer questions safely.",
    tools=[search_docs],
    input_guardrails=[InputGuardrail(guardrail_function=check_input)],
    output_guardrails=[OutputGuardrail(guardrail_function=check_output)],
)
