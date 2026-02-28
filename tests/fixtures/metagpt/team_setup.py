"""Fixture: MetaGPT Team composition with multiple roles.

Used by test_metagpt.py to verify extraction of:
- Team().hire([...]) compositions
- Multiple Role subclasses in one file
- Role-action wiring
- run_project call
"""
from metagpt.roles import Role
from metagpt.actions import Action
from metagpt.team import Team


class WriteCode(Action):
    name: str = "WriteCode"

    async def run(self, instruction: str) -> str:
        code = await self._aask(instruction)
        return code


class ReviewCode(Action):
    name: str = "ReviewCode"

    async def run(self, code: str) -> str:
        review = await self._aask(f"Review this code:\n{code}")
        return review


class Programmer(Role):
    name: str = "Programmer"
    profile: str = "Python Developer"
    goal: str = "Write clean Python code"
    actions: list = [WriteCode]


class Reviewer(Role):
    name: str = "Reviewer"
    profile: str = "Code Reviewer"
    goal: str = "Ensure code quality"
    actions: list = [ReviewCode]


team = Team()
team.hire([Programmer(), Reviewer()])
team.run_project("Build a REST API")
