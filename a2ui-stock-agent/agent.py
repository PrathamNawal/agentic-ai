import uuid

import yfinance as yf
from agno.agent import Agent
from agno.models.groq import Groq
from agno.tools.yfinance import YFinanceTools

from quote_ui import quote_card

DEFAULT_MODEL = "llama-3.3-70b-versatile"

INSTRUCTIONS = """You are a stock assistant.
For any question about the current price of a stock, call show_quote_card with the
ticker symbol and then reply with one short sentence. Do not repeat the numbers in text.
Use the other yfinance tools only for questions the card cannot answer."""


def make_agent(api_key: str, model: str, surfaces: list) -> Agent:
    """Build an agent for one request. The Groq key is used only for this request."""

    def show_quote_card(ticker: str) -> str:
        """Show a live quote card for a stock ticker (e.g. NVDA, AAPL, TSLA) in the user's UI.

        Args:
            ticker: The stock ticker symbol.
        """
        symbol = ticker.strip().upper()
        info = yf.Ticker(symbol).fast_info
        price = float(info["last_price"])
        prev = float(info["previous_close"])
        surfaces.extend(
            quote_card(
                surface_id=f"quote-{uuid.uuid4().hex[:8]}",
                symbol=symbol,
                price=price,
                change=price - prev,
                change_pct=(price - prev) / prev * 100,
                currency=info["currency"] or "USD",
            )
        )
        return f"Quote card for {symbol} displayed to the user."

    return Agent(
        model=Groq(id=model or DEFAULT_MODEL, api_key=api_key),
        tools=[show_quote_card, YFinanceTools()],
        instructions=INSTRUCTIONS,
        markdown=False,
    )
