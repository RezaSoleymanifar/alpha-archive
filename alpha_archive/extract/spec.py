"""LLM extraction of signal specification from paper text.

Per actor.md §3: uses Sonnet, runs TWICE with different seeds, requires agreement
on `formula` and `horizon` before proceeding (self-consistency check).
"""
from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field
from typing import Optional


SPEC_MODEL = "claude-sonnet-4-6"

EXTRACT_PROMPT = """You are a quantitative finance research engineer. You read academic papers and extract the trading signal specification in a strict JSON schema. Missing or unclear fields should be returned as null, do NOT invent values.

Read the following paper excerpt carefully:

----- PAPER -----
{paper_text}
----- END PAPER -----

Extract the signal specification. Output STRICT JSON only, no prose, no code fences.

Schema:
{{
  "hypothesis": "1-sentence economic hypothesis the paper proposes",
  "formula": "precise English description of the signal computation, e.g., 'rank stocks by past 12-month return excluding the most recent month'",
  "feature_pseudocode": "1-3 lines of pandas-style pseudocode showing how to compute the signal from prices/fundamentals",
  "data_required": {{
    "prices": true | false,
    "fundamentals": ["pe", "pb", "roe", ...] or [],
    "macro": ["vix", "rates", ...] or [],
    "alternative": ["insider", "sentiment", ...] or []
  }},
  "universe": "sp500" | "russell1000" | "russell2000" | "russell3000" | "global_developed" | "us_all" | null,
  "rebalance_freq": "daily" | "weekly" | "monthly" | "quarterly" | null,
  "horizon_days": int or null,
  "expected_sign": "+" | "-" | "both" | null,
  "is_long_short": true | false,
  "is_cross_sectional": true | false,
  "claimed_sharpe": float or null,
  "claimed_period": "e.g., 1965-1989" or null,
  "claimed_alpha_t_stat": float or null,
  "notes": "any caveats, e.g., 'requires fundamental data quarterly lag'"
}}

Confidence guidance:
- If paper does not specify a horizon, set horizon_days = null (don't guess)
- If multiple universes mentioned, pick the primary one tested
- If paper is NOT about a tradable signal, return all-null with notes explaining why
"""


@dataclass
class SignalSpec:
    hypothesis: Optional[str] = None
    formula: Optional[str] = None
    feature_pseudocode: Optional[str] = None
    data_required: dict = field(default_factory=dict)
    universe: Optional[str] = None
    rebalance_freq: Optional[str] = None
    horizon_days: Optional[int] = None
    expected_sign: Optional[str] = None
    is_long_short: Optional[bool] = None
    is_cross_sectional: Optional[bool] = None
    claimed_sharpe: Optional[float] = None
    claimed_period: Optional[str] = None
    claimed_alpha_t_stat: Optional[float] = None
    notes: Optional[str] = None

    def is_complete(self) -> bool:
        """Per actor.md §3: required fields = formula, data_required, universe, horizon_days, expected_sign."""
        return all([
            self.formula is not None,
            self.data_required,
            self.universe is not None,
            self.horizon_days is not None,
            self.expected_sign is not None,
        ])

    @classmethod
    def from_json(cls, d: dict) -> "SignalSpec":
        return cls(**{k: v for k, v in d.items() if k in cls.__annotations__})


def _call_extract(paper_text: str, provider, temperature: float, max_tokens: int = 1500) -> dict:
    return provider.complete_json(
        EXTRACT_PROMPT.format(paper_text=paper_text[:25000]),
        model="sonnet",
        temperature=temperature,
        max_tokens=max_tokens,
    )


def _agreement_score(a: SignalSpec, b: SignalSpec) -> float:
    """Cheap proxy: fraction of key fields that agree across two extractions."""
    keys = ["formula", "horizon_days", "universe", "rebalance_freq", "expected_sign",
            "is_cross_sectional", "is_long_short"]
    matches = 0
    for k in keys:
        va, vb = getattr(a, k), getattr(b, k)
        if va is None and vb is None:
            matches += 1
        elif isinstance(va, str) and isinstance(vb, str):
            # loose string match: lower + substring overlap
            la, lb = va.lower().strip(), vb.lower().strip()
            if la == lb or la in lb or lb in la:
                matches += 1
        elif va == vb:
            matches += 1
    return matches / len(keys)


def extract_spec(
    paper_text: str,
    *,
    require_agreement: float = 0.85,
) -> tuple[SignalSpec, float, dict]:
    """Extract spec twice with different seeds; return (spec, agreement_score, debug).

    Per actor.md: if agreement < `require_agreement`, caller should escalate to human.
    Uses pluggable LLM provider (see alpha_archive.llm.factory.get_provider).
    """
    from ..llm import get_provider
    provider = get_provider()
    a_dict = _call_extract(paper_text, provider, temperature=0.0)
    b_dict = _call_extract(paper_text, provider, temperature=0.4)
    a = SignalSpec.from_json(a_dict)
    b = SignalSpec.from_json(b_dict)
    score = _agreement_score(a, b)
    return a, score, {"variant_a": asdict(a), "variant_b": asdict(b), "agreement": score, "provider": provider.name}


def extract_spec_offline(paper_text: str) -> SignalSpec:
    """Heuristic-only extractor for testing without API key.
    Pulls a few obvious fields via regex; everything else null.
    """
    import re
    spec = SignalSpec()
    m = re.search(r"sharpe(?:\s+ratio)?[:\s]+(\d+\.\d+)", paper_text, re.I)
    if m:
        spec.claimed_sharpe = float(m.group(1))
    if re.search(r"\bs&p\s*500\b|\bsp\s*500\b|\bsp500\b", paper_text, re.I):
        spec.universe = "sp500"
    if re.search(r"\bmonthly\b.*\brebalanc", paper_text, re.I):
        spec.rebalance_freq = "monthly"
        spec.horizon_days = 21
    if re.search(r"\b(cross[- ]?section)\b", paper_text, re.I):
        spec.is_cross_sectional = True
    spec.notes = "extracted offline (regex only); use extract_spec() with API key for full LLM pass"
    return spec
