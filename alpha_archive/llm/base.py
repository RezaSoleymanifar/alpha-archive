"""LLMProvider interface, every backend implements `complete()`."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class LLMResponse:
    text: str
    model: str
    provider: str
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None
    cost_usd: Optional[float] = None
    raw: Optional[dict] = None


class LLMProvider(ABC):
    """Backend-agnostic LLM client. Implementations:
    - AnthropicProvider (paid API)
    - ClaudeCodeProvider (free via CLI)
    - OfflineProvider (no LLM)
    """
    name: str = "abstract"

    @abstractmethod
    def complete(
        self,
        prompt: str,
        *,
        model: Optional[str] = None,
        system: Optional[str] = None,
        temperature: float = 0.0,
        max_tokens: int = 1500,
        json_schema: Optional[dict] = None,
    ) -> LLMResponse:
        """Run a single completion. Returns LLMResponse with text + metadata.

        Args:
            prompt: user message text
            model: model alias (e.g., "haiku", "sonnet"), provider-specific
            system: optional system prompt
            temperature: 0.0 to 1.0
            max_tokens: cap on output tokens
            json_schema: optional structured-output schema (provider may ignore)
        """
        raise NotImplementedError

    def complete_json(
        self,
        prompt: str,
        *,
        schema: Optional[dict] = None,
        model: Optional[str] = None,
        temperature: float = 0.0,
        max_tokens: int = 1500,
    ) -> dict:
        """Convenience: get parsed JSON object from completion.
        Strips markdown fences if model wraps output.
        """
        import json
        resp = self.complete(
            prompt=prompt,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            json_schema=schema,
        )
        text = resp.text.strip()
        if text.startswith("```"):
            text = text.split("```", 2)[1]
            if text.startswith("json"):
                text = text[4:]
            text = text.strip().rstrip("`").strip()
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass
        # Fallback: extract first balanced {...} from anywhere in the text.
        start = text.find("{")
        if start < 0:
            raise json.JSONDecodeError("no '{' found in LLM output", text, 0)
        depth = 0
        for i in range(start, len(text)):
            c = text[i]
            if c == "{":
                depth += 1
            elif c == "}":
                depth -= 1
                if depth == 0:
                    return json.loads(text[start:i + 1])
        raise json.JSONDecodeError("unbalanced braces in LLM output", text, start)
