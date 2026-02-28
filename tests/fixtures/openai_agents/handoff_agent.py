"""Fixture: agent-to-agent handoff pattern.

Used by test_openai_agents.py to verify detection of:
- Multiple Agent(...) definitions
- handoffs=[...] parameter linking agents
- handoff_description keyword
"""
from agents import Agent, function_tool


@function_tool
def lookup_order(order_id: str) -> str:
    """Look up an order by ID."""
    return f"Order {order_id}: shipped"


specialist = Agent(
    name="order_specialist",
    instructions="Handle order-related queries.",
    tools=[lookup_order],
    handoff_description="Handles order tracking and returns.",
)

triage_agent = Agent(
    name="triage_agent",
    instructions="Route customer queries to the right specialist.",
    handoffs=[specialist],
)
