"""Pick the LLM from settings / environment variables, so the agent is provider-agnostic.

    OPENROUTER_API_KEY   -> OpenRouter  (any model, e.g. x-ai/grok-4.1-fast)
    XAI_API_KEY          -> xAI's own Grok API
    GROQ_API_KEY         -> Groq (the inference company, different from xAI's Grok)
    ANTHROPIC_API_KEY    -> Anthropic

Env overrides: LLM_PROVIDER, LLM_MODEL, LLM_BASE_URL. The dashboard can also pass a key
for the current session only (it is never written to disk).
The agent needs a model that supports tool calling.
"""
import os

DEFAULTS = {
    "openrouter": "x-ai/grok-4.1-fast",
    "xai": "grok-4-1-fast-non-reasoning-latest",
    "groq": "openai/gpt-oss-120b",
    "anthropic": "claude-sonnet-5-5",
}
KEYS = {
    "openrouter": "OPENROUTER_API_KEY",
    "xai": "XAI_API_KEY",
    "groq": "GROQ_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
}


def detect_provider(provider: str | None = None, api_key: str | None = None) -> str | None:
    p = (provider or os.getenv("LLM_PROVIDER", "")).lower().strip()
    if p and p != "auto":
        if p not in KEYS:
            raise ValueError(f"provider must be one of {list(KEYS)}")
        return p
    return next((name for name, key in KEYS.items() if os.getenv(key)), None)


def configured_providers() -> list[str]:
    return [n for n, k in KEYS.items() if os.getenv(k)]


def get_model(provider: str | None = None, model_id: str | None = None,
              api_key: str | None = None, base_url: str | None = None):
    provider = detect_provider(provider)
    if not provider:
        raise ValueError("No LLM key found. Enter a key in the sidebar or set one of: " + ", ".join(KEYS.values()))
    key = api_key or os.getenv(KEYS[provider])
    if not key:
        raise ValueError(f"No API key for {provider}. Enter one in the sidebar or set {KEYS[provider]}.")
    model_id = model_id or os.getenv("LLM_MODEL") or DEFAULTS[provider]
    base_url = base_url or os.getenv("LLM_BASE_URL") or None

    if provider == "openrouter":
        from agno.models.openrouter import OpenRouter
        return OpenRouter(id=model_id, api_key=key, **({"base_url": base_url} if base_url else {}))
    if provider == "xai":
        from agno.models.xai import xAI
        return xAI(id=model_id, api_key=key, **({"base_url": base_url} if base_url else {}))
    if provider == "groq":
        from agno.models.groq import Groq
        return Groq(id=model_id, api_key=key)
    from agno.models.anthropic import Claude
    return Claude(id=model_id, api_key=key)
