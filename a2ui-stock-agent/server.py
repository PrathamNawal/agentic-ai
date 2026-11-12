import os
from pathlib import Path

from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from agent import DEFAULT_MODEL, make_agent

app = FastAPI()
DIST = Path(__file__).parent / "web" / "dist"


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=500)
    model: str | None = Field(default=None, max_length=100)


@app.get("/api/health")
def health():
    return {"ok": True, "default_model": DEFAULT_MODEL}


@app.post("/api/chat")
def chat(req: ChatRequest, x_groq_api_key: str | None = Header(default=None)):
    # Bring-your-own-key: the key arrives per request over HTTPS, is passed to Groq,
    # and is never stored or logged by this server.
    if not x_groq_api_key:
        raise HTTPException(401, "Add your Groq API key first.")
    surfaces: list = []
    try:
        result = make_agent(x_groq_api_key, req.model or DEFAULT_MODEL, surfaces).run(req.message)
    except Exception as e:  # surface a short, key-free error to the UI
        msg = str(e)
        if "401" in msg or "invalid_api_key" in msg.lower():
            raise HTTPException(401, "Groq rejected that API key.")
        raise HTTPException(502, f"Agent error: {msg[:300].replace(x_groq_api_key, '***')}")
    return {"text": result.content or "", "a2ui": surfaces}


if DIST.exists():
    app.mount("/assets", StaticFiles(directory=DIST / "assets"), name="assets")

    @app.get("/")
    def index():
        return FileResponse(DIST / "index.html")
