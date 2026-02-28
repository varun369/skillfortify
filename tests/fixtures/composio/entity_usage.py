"""Fixture: Composio entity and connection management.

Used by test_composio.py to verify extraction of:
- Entity-based access (get_entity, get_connection)
- App references in connection calls
- Action references in execute_action calls
- Environment variables for authentication
"""
from composio import ComposioToolSet, Action, App
import os


api_key = os.environ["COMPOSIO_API_KEY"]
toolset = ComposioToolSet(api_key=api_key)

entity = toolset.get_entity(id="user123")
connection = entity.get_connection(app=App.GITHUB)

result = entity.execute_action(
    action=Action.GITHUB_CREATE_ISSUE,
    params={"repo": "my-org/my-repo", "title": "Bug report"},
    connected_account_id=connection.id,
)

slack_conn = entity.get_connection(app=App.SLACK)
