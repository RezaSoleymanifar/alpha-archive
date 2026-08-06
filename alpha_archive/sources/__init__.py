"""Paper source pollers, curated-first hierarchy.

PRIMARY (high-signal, low-noise, ship by default):
  - alpha_architect: hand-curated by Wes Gray's team, often pre-replicated
  - aqr:             AQR research insights (Asness, Frazzini, Pedersen)
  - two_sigma:       Two Sigma research blog
  - nber:            NBER finance working papers (peer-academic)

BACKGROUND (volume, heavily LLM-triaged):
  - arxiv:           q-fin categories, ~30-50 papers/day, mostly noise

DEPRIORITIZED (in repo for future, not active):
  - ssrn:            scraping unreliable; better via official partnerships
  - twitter/reddit/substack: dropped: let critics file GitHub issues instead

Each module exposes:
    poll() -> list[dict]   # standardized paper records
"""
from .alpha_architect import poll_alpha_architect
from .aqr import poll_aqr
from .two_sigma import poll_two_sigma
from .nber import poll_nber
from .arxiv import poll_arxiv
from .ssrn import poll_ssrn

__all__ = [
    "poll_alpha_architect", "poll_aqr", "poll_two_sigma", "poll_nber",
    "poll_arxiv", "poll_ssrn",
]
