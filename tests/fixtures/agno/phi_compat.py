"""Legacy Phidata import compatibility -- test fixture.

Agno was formerly known as Phidata. Many projects still use the
old ``phi`` import paths. The parser must detect these as well.
"""

from phi.agent import Agent
from phi.tools.duckduckgo import DuckDuckGoTools
from phi.tools.yfinance import YFinanceTools

agent = Agent(
    name="Legacy Phi Agent",
    tools=[DuckDuckGoTools(), YFinanceTools(stock_price=True)],
    instructions=["Show financial data in tables"],
    show_tool_calls=True,
)
