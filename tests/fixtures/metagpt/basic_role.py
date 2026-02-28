"""Fixture: basic MetaGPT Role with actions.

Used by test_metagpt.py to verify extraction of:
- Role subclass with name, profile, goal
- Action subclass with name
- Role-to-action mapping
"""
from metagpt.roles import Role
from metagpt.actions import Action


class AnalyzeData(Action):
    name: str = "AnalyzeData"

    async def run(self, instruction: str) -> str:
        return f"Analysis: {instruction}"


class Analyst(Role):
    name: str = "Analyst"
    profile: str = "Data Analyst"
    goal: str = "Analyze datasets and provide insights"
    actions: list = [AnalyzeData]
