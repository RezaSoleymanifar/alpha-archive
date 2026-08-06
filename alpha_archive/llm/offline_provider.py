"""Offline backend. No LLM calls. Returns templated stubs for testing plumbing.

When called for triage, returns is_tradable=true with low confidence.
When called for spec extract, returns minimal stub.
When called for codegen, returns the momentum reference implementation.
"""
from __future__ import annotations

import json
from typing import Optional

from .base import LLMProvider, LLMResponse


# Trigger-substring -> canned response. Crude but enough for plumbing tests.
CANNED_RESPONSES = {
    "is_tradable": json.dumps({
        "is_tradable": True,
        "confidence": 0.5,
        "signal_type": "cross_sectional_equity",
        "data_required": ["prices"],
        "horizon_days": 21,
        "claimed_sharpe": None,
        "notes": "OFFLINE provider, no real triage performed",
    }),
    "Extract the signal specification": json.dumps({
        "hypothesis": "stub: cross-sectional momentum",
        "formula": "12-1 month return",
        "feature_pseudocode": "(prices.shift(21) / prices.shift(252)) - 1",
        "data_required": {"prices": True, "fundamentals": [], "macro": [], "alternative": []},
        "universe": "sp500",
        "rebalance_freq": "monthly",
        "horizon_days": 21,
        "expected_sign": "+",
        "is_long_short": True,
        "is_cross_sectional": True,
        "claimed_sharpe": None,
        "claimed_period": None,
        "claimed_alpha_t_stat": None,
        "notes": "OFFLINE stub spec",
    }),
    "Python function that implements a trading signal": (
        "import pandas as pd\nimport numpy as np\n\n"
        "LOOKBACK = 252\nSKIP = 21\n\n"
        "def signal(prices: pd.DataFrame) -> pd.DataFrame:\n"
        "    return (prices.shift(SKIP) / prices.shift(LOOKBACK)) - 1\n"
    ),
}


class OfflineProvider(LLMProvider):
    name = "offline"

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
        # Pick canned response by trigger substring
        text = ""
        for trigger, canned in CANNED_RESPONSES.items():
            if trigger in prompt:
                text = canned
                break
        if not text:
            text = json.dumps({"error": "no canned response for this prompt", "prompt_head": prompt[:200]})

        return LLMResponse(
            text=text,
            model=model or "offline-stub",
            provider=self.name,
            cost_usd=0.0,
        )
