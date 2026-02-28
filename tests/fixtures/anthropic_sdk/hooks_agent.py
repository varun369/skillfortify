"""Fixture: Anthropic Agent SDK agent using Hook lifecycle callbacks.

Used by test_anthropic_sdk.py to verify extraction of:
- Hook subclass definitions with before/after_tool_call methods
- Agent construction with hooks
"""
from claude_agent_sdk import Agent
from claude_agent_sdk.hooks import Hook
from claude_agent_sdk.tools import tool
import logging

log = logging.getLogger(__name__)


class AuditHook(Hook):
    """Logs every tool call for compliance auditing."""

    def before_tool_call(self, tool_name, args):
        log.info(f"Calling {tool_name} with {args}")

    def after_tool_call(self, tool_name, result):
        log.info(f"Tool {tool_name} returned {result}")


class RateLimitHook(Hook):
    """Enforces rate limiting on tool invocations."""

    def before_tool_call(self, tool_name, args):
        pass


@tool
def get_account(account_id: str) -> str:
    """Get account details by ID."""
    return f"Account {account_id}"


agent = Agent(
    name="audited_agent",
    model="claude-sonnet-4-20250514",
    tools=[get_account],
    hooks=[AuditHook(), RateLimitHook()],
    instructions="You are an audited agent with lifecycle hooks.",
)
