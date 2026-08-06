"""Anthropic SDK backend, direct API calls.

Activates when ALPHA_ARCHIVE_LLM_PROVIDER=anthropic and ANTHROPIC_API_KEY is set.
"""
from __future__ import annotations

import os
from typing import Optional

from .base import LLMProvider, LLMResponse


# Friendly alias -> full model id
MODEL_MAP = {
    "haiku": "claude-haiku-4-5-20251001",
    "sonnet": "claude-sonnet-4-6",
    "opus": "claude-opus-4-7",
}

# Approximate $ / 1M tokens (input, output), Anthropic published pricing snapshot
PRICING_PER_MTOK = {
    "claude-haiku-4-5-20251001": (1.0, 5.0),
    "claude-sonnet-4-6":          (3.0, 15.0),
    "claude-opus-4-7":            (15.0, 75.0),
}


class AnthropicProvider(LLMProvider):
    name = "anthropic"

    def __init__(self, *, api_key: Optional[str] = None, default_model: str = "sonnet"):
        try:
            from anthropic import Anthropic
        except ImportError as e:
            raise RuntimeError("install with: uv add anthropic") from e
        key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        if not key:
            raise RuntimeError("ANTHROPIC_API_KEY not set")
        self._client = Anthropic(api_key=key)
        self.default_model = default_model

    def complete(
        self,
        prompt: str,
        *,
        model: Optional[str] = None,
        system: Optional[str] = None,
        temperature: float = 0.0,
        max_tokens: int = 1500,
        json_schema: Optional[dict] = None,  # Anthropic doesn't natively enforce schemas; ignored
    ) -> LLMResponse:
        m_alias = (model or self.default_model).lower()
        m = MODEL_MAP.get(m_alias, model or self.default_model)
        kwargs = {
            "model": m,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": [{"role": "user", "content": prompt}],
        }
        if system:
            kwargs["system"] = system
        msg = self._client.messages.create(**kwargs)

        # Cost
        in_t = getattr(msg.usage, "input_tokens", None)
        out_t = getattr(msg.usage, "output_tokens", None)
        cost = None
        prices = PRICING_PER_MTOK.get(m)
        if prices and in_t is not None and out_t is not None:
            cost = (in_t / 1_000_000) * prices[0] + (out_t / 1_000_000) * prices[1]

        return LLMResponse(
            text=msg.content[0].text,
            model=m,
            provider=self.name,
            input_tokens=in_t,
            output_tokens=out_t,
            cost_usd=cost,
            raw={"id": msg.id, "stop_reason": msg.stop_reason},
        )
