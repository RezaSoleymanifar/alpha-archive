"""Claude Code CLI backend, shells out to `claude -p`.

Free if the user has a Max plan. No API key required (CLI is already authed).
Per-call latency similar to API. Supports --model alias and --json-schema.
"""
from __future__ import annotations

import os
import shutil
import subprocess
from typing import Optional

from .base import LLMProvider, LLMResponse


# Model alias map: friendly name -> claude CLI alias
MODEL_ALIASES = {
    "haiku": "haiku",
    "sonnet": "sonnet",
    "opus": "opus",
    # explicit full names also pass through
}


class ClaudeCodeProvider(LLMProvider):
    name = "claude_code"

    def __init__(
        self,
        *,
        binary: Optional[str] = None,
        timeout: int = 180,
        default_model: str = "sonnet",
        max_budget_usd: Optional[float] = None,
    ):
        self.binary = binary or shutil.which("claude") or "claude"
        self.timeout = timeout
        self.default_model = default_model
        self.max_budget_usd = max_budget_usd

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
        # Compose final prompt; claude CLI doesn't accept system separately in -p mode,
        # so prepend system as instruction text if provided.
        full_prompt = prompt
        if system:
            full_prompt = f"{system.strip()}\n\n---\n\n{prompt}"

        # Build CLI args
        m = MODEL_ALIASES.get((model or self.default_model).lower(), model or self.default_model)
        cmd = [
            self.binary,
            "-p", full_prompt,
            "--model", m,
            "--no-session-persistence",
        ]
        if json_schema is not None:
            import json as _json
            cmd.extend(["--json-schema", _json.dumps(json_schema)])
        if self.max_budget_usd is not None:
            cmd.extend(["--max-budget-usd", str(self.max_budget_usd)])

        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.timeout,
                encoding="utf-8",
                errors="replace",
            )
        except subprocess.TimeoutExpired as e:
            raise RuntimeError(f"claude CLI timed out after {self.timeout}s") from e

        if proc.returncode != 0:
            raise RuntimeError(
                f"claude CLI failed (exit {proc.returncode}):\n"
                f"stderr: {proc.stderr[:2000]}"
            )

        text = (proc.stdout or "").strip()
        return LLMResponse(
            text=text,
            model=m,
            provider=self.name,
            cost_usd=0.0,  # routed through Max plan; not metered here
            raw={"stderr": proc.stderr[-500:] if proc.stderr else ""},
        )


if __name__ == "__main__":
    p = ClaudeCodeProvider()
    r = p.complete("Reply with exactly: ok", model="haiku")
    print(f"text:     {r.text!r}")
    print(f"provider: {r.provider}")
    print(f"model:    {r.model}")
