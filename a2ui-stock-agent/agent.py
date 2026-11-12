import os

import yfinance as yf
from agno.agent import Agent
from agno.models.groq import Groq
from agno.tools.yfinance import YFinanceTools
from dotenv import load_dotenv

from a2ui import quote_card

load_dotenv()

INSTRUCTIONS = """You are a stock assistant.
For any question about the current price of a stock, call show_quote_card with the
ticker symbol and then reply with one short sentence. Do not repeat the numbers in text.
Use the other yfinance tools only for questions the card cannot answer."""


def make_agent(surfaces: list) -> Agent:
    """Build an agent whose render tool appends A2UI messages to `surfaces`."""

    def show_quote_card(ticker: str) -> str:
        """Show a live quote card for a stock ticker (e.g. NVDA, AAPL, TSLA) in the user's UI.

        Args:
            ticker: The stock ticker symbol.
        """
        info = yf.Ticker(ticker.upper()).fast_info
        price = float(info["last_price"])
        prev = float(info["previous_close"])
        change = price - prev
        surfaces.extend(
            quote_card(
                symbol=ticker.upper(),
                name=ticker.upper(),
                price=price,
                change=change,
                change_pct=change / prev * 100,
                currency=info.get("currency", "USD"),
            )
        )
        return f"Quote card for {ticker.upper()} displayed to the user."

    return Agent(
        model=Groq(id=os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")),
        tools=[show_quote_card, YFinanceTools()],
        instructions=INSTRUCTIONS,
        markdown=False,
    )
