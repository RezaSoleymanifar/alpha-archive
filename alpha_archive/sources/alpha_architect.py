"""AlphaArchitect blog RSS poller.
They publish curated replications of academic factor papers, high signal density.
~5 posts per week.
"""
from __future__ import annotations

from datetime import datetime

import feedparser

AA_RSS = "https://alphaarchitect.com/feed/"


def poll_alpha_architect(limit: int = 50) -> list[dict]:
    feed = feedparser.parse(AA_RSS)
    out = []
    for entry in feed.entries[:limit]:
        out.append({
            "source": "alpha_architect",
            "external_id": _slug_from_url(entry.link),
            "title": (entry.title or "").strip(),
            "abstract": (getattr(entry, "summary", "") or "").strip(),
            "authors": getattr(entry, "author", None),
            "published_at": _parse_dt(getattr(entry, "published", None)),
            "pdf_url": None,
            "landing_url": entry.link,
            "categories": "alphaarchitect",
            "raw": {},
        })
    return out


def _slug_from_url(url: str) -> str:
    return url.rstrip("/").rsplit("/", 1)[-1]


def _parse_dt(s: str | None) -> datetime | None:
    if not s:
        return None
    for fmt in ("%a, %d %b %Y %H:%M:%S %z", "%a, %d %b %Y %H:%M:%S %Z"):
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    return None


if __name__ == "__main__":
    rows = poll_alpha_architect(limit=10)
    for r in rows:
        print(f"- [{r['external_id']}] {r['title'][:80]}")
    print(f"\ntotal: {len(rows)}")
