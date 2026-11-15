"""Pick the LLM from environment variables, so the agent is provider-agnostic.

    LLM_PROVIDER   openrouter | xai | groq | anthropic   (auto-detected from whichever key is set)
    LLM_MODEL      model id for that provider (optional; sensible default per provider)

    OPENROUTER_API_KEY   -> OpenRouter  (use any model, e.g. LLM_MODEL=x-ai/grok-4.1-fast)
    XAI_API_KEY          -> xAI's own Grok API
    GROQ_API_KEY         -> Groq (the inference company, different from xAI's Grok)
    ANTHROPIC_API_KEY    -> Anthropic

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


def detect_provider() -> str | None:
    p = os.getenv("LLM_PROVIDER", "").lower().strip()
    if p:
        if p not in KEYS:
            raise SystemExit(f"LLM_PROVIDER must be one of {list(KEYS)}")
        return p
    return next((name for name, key in KEYS.items() if os.getenv(key)), None)


def get_model():
    provider = detect_provider()
    if not provider:
        raise SystemExit("No LLM key found. Set one of: " + ", ".join(KEYS.values()))
    if not os.getenv(KEYS[provider]):
        raise SystemExit(f"LLM_PROVIDER={provider} but {KEYS[provider]} is not set.")
    model_id = os.getenv("LLM_MODEL", DEFAULTS[provider])

    if provider == "openrouter":
        from agno.models.openrouter import OpenRouter
        return OpenRouter(id=model_id)
    if provider == "xai":
        from agno.models.xai import xAI
        return xAI(id=model_id)
    if provider == "groq":
        from agno.models.groq import Groq
        return Groq(id=model_id)
    from agno.models.anthropic import Claude
    return Claude(id=model_id)
