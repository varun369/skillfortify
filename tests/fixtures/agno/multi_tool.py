"""Agno agent with multiple built-in tool imports -- test fixture."""

from agno.agent import Agent
from agno.models.openai import OpenAIChat
from agno.tools.duckduckgo import DuckDuckGoTools
from agno.tools.yfinance import YFinanceTools
from agno.tools.newspaper4k import Newspaper4kTools

finance_agent = Agent(
    name="Finance Agent",
    model=OpenAIChat(id="gpt-4o"),
    tools=[
        YFinanceTools(stock_price=True, analyst_recommendations=True),
        DuckDuckGoTools(),
    ],
    instructions=["Use tables to display data", "Always cite sources"],
    show_tool_calls=True,
)

news_agent = Agent(
    name="News Agent",
    model=OpenAIChat(id="gpt-4o-mini"),
    tools=[Newspaper4kTools(), DuckDuckGoTools()],
    instructions=["Summarize articles clearly"],
)
