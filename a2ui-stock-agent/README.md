# A2UI Stock Agent

An Agno agent (Groq model) uses yfinance and answers with a quote **card** rendered by the
official A2UI Lit renderer, instead of a wall of text.

```
browser (Vite + @a2ui/lit) ── POST /api/chat + X-Groq-Api-Key ──> FastAPI ──> Agno Agent (Groq)
        ▲                                                            ├─ YFinanceTools
        └──────── {text, a2ui:[v0.9 messages]} ◄─────────────────── └─ show_quote_card → yfinance → a2ui-agent-sdk
```

- **Server side:** `quote_ui.py` builds the surface with the official `a2ui-agent-sdk` builder
  (Card → Column → Text/Divider, bound to a data model). The model only picks the ticker;
  the numbers go into the data model in Python and never pass through the model.
- **Client side:** `web/` feeds the messages to `MessageProcessor` (`@a2ui/web_core`) and renders
  with `<a2ui-surface>` (`@a2ui/lit`).
- **Bring your own key:** the Groq key is typed into the page, kept in `sessionStorage`, sent in
  the `X-Groq-Api-Key` header per request, and never stored or logged by the server.

## Protocol version
Uses A2UI **v0.9**. The Python SDK and `@a2ui/web_core` also contain v1.0, but the published
renderers (`@a2ui/lit`, `@a2ui/react`, `@a2ui/angular` 0.15) only ship v0.8/v0.9 renderers, so
v0.9 is what can be rendered today.

## Run locally
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
(cd web && npm install && npm run build)
uvicorn server:app --reload      # open http://localhost:8000, paste your Groq key
```

## Deploy
`render.yaml` describes a Render web service (build installs Python deps and builds the web client).

## Notes
- yfinance scrapes Yahoo; cloud IPs are sometimes rate-limited, so quotes can fail intermittently.
- The endpoint has no auth or rate limiting; anyone with the URL and their own Groq key can use it.
