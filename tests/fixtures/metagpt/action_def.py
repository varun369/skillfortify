"""Fixture: MetaGPT Action definitions with external calls.

Used by test_metagpt.py to verify extraction of:
- Multiple Action subclasses
- URLs from _aask / requests calls
- Import dependencies
"""
from metagpt.actions import Action
import requests


class FetchWebPage(Action):
    name: str = "FetchWebPage"

    async def run(self, url: str) -> str:
        resp = requests.get("https://scraper.example.com/api/v2/fetch")
        return resp.text


class SummarizeText(Action):
    name: str = "SummarizeText"

    async def run(self, text: str) -> str:
        result = await self._aask(f"Summarize: {text}")
        return result


class TranslateDocument(Action):
    name: str = "TranslateDocument"

    async def run(self, text: str) -> str:
        resp = requests.post(
            "https://translate.example.com/api/v1/translate",
            json={"text": text, "target": "en"},
        )
        return resp.json()["translated"]
