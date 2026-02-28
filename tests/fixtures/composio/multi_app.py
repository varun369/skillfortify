"""Fixture: Composio usage with multiple App-based integrations.

Used by test_composio.py to verify extraction of:
- App-based tool retrieval (App.GITHUB, App.SLACK, App.GMAIL)
- Multiple get_tools calls with different apps
- Implied OAuth capabilities from App integrations
"""
from composio import ComposioToolSet, App


toolset = ComposioToolSet(api_key="env:COMPOSIO_API_KEY")

github_tools = toolset.get_tools(apps=[App.GITHUB])
slack_tools = toolset.get_tools(apps=[App.SLACK, App.GMAIL])
calendar_tools = toolset.get_tools(apps=[App.GOOGLE_CALENDAR])
