"""Fixture: basic Composio tool usage with Action-based tool retrieval.

Used by test_composio.py to verify extraction of:
- ComposioToolSet instantiation
- Action-based tool retrieval (Action.GITHUB_CREATE_ISSUE, etc.)
- URLs from API calls
- Import dependencies
"""
from composio import ComposioToolSet, Action
import requests


toolset = ComposioToolSet()

tools = toolset.get_tools(actions=[
    Action.GITHUB_CREATE_ISSUE,
    Action.SLACK_SEND_MESSAGE,
])

response = requests.get("https://api.composio.dev/v1/actions")
