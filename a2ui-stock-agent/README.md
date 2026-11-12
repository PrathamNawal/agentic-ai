# A2UI Stock Agent

Smallest end-to-end example: an Agno agent (Groq model) uses yfinance and answers with a
quote **card** instead of text. A tiny browser renderer draws the card from A2UI-style JSON.

```
browser ── POST /chat ──> FastAPI ──> Agno Agent (Groq)
   ▲                                    ├─ YFinanceTools
   └── {text, a2ui:[…]} ◄───────────────└─ show_quote_card → yfinance → A2UI messages
```

Numbers are fetched and placed in the data model on the server in Python, so the model
only chooses the ticker; it never has to emit the figures.

## Run
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # add your GROQ_API_KEY
uvicorn server:app --reload
```
Open http://localhost:8000 and ask "What's NVDA trading at?"

## Notes
- The message format is a simplified A2UI-style shape, not validated against the official
  `a2ui-agent-sdk`. Check https://a2ui.org/specification/ before relying on field names.
- Agno talks to browsers via AG-UI normally; this demo uses a plain HTTP endpoint to stay minimal.
- yfinance scrapes Yahoo and can be rate-limited; fine for a demo.
