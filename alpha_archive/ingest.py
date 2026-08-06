"""Ingest pipeline: poll all sources, dedupe, write to SQLite."""
from __future__ import annotations

from datetime import datetime
from typing import Callable

from sqlalchemy import select

from .db import Paper, Session, init_db
from .sources import (
    poll_arxiv, poll_ssrn, poll_nber, poll_alpha_architect,
    poll_aqr, poll_two_sigma,
)

# Curated-first ordering. Defaults to high-signal sources only.
SOURCES_PRIMARY: dict[str, Callable] = {
    "alpha_architect": poll_alpha_architect,   # ~5/wk, hand-curated, often pre-replicated
    "aqr": poll_aqr,                           # AQR research insights
    "two_sigma": poll_two_sigma,               # Two Sigma research blog
    "nber": poll_nber,                         # NBER finance working papers
}

# Background discovery, high volume, requires aggressive LLM triage
SOURCES_BACKGROUND: dict[str, Callable] = {
    "arxiv": poll_arxiv,                       # q-fin RSS, mostly noise
    "ssrn": poll_ssrn,                         # scrape flaky, deprioritized
}

# Default = primary only. Use 'all' to include background.
SOURCES = SOURCES_PRIMARY


def ingest(source: str = "primary", limit: int | None = None) -> dict:
    """Poll source(s) and insert new papers. Idempotent (UNIQUE on source+external_id).

    `source` accepts:
      - 'primary'    : curated high-signal sources only (default)
      - 'background' : arxiv + ssrn (high volume, noisy)
      - 'all'        : both primary and background
      - <name>       : single named source
    """
    init_db()

    if source == "primary":
        registry = SOURCES_PRIMARY
        targets = list(registry.keys())
    elif source == "background":
        registry = SOURCES_BACKGROUND
        targets = list(registry.keys())
    elif source == "all":
        registry = {**SOURCES_PRIMARY, **SOURCES_BACKGROUND}
        targets = list(registry.keys())
    else:
        registry = {**SOURCES_PRIMARY, **SOURCES_BACKGROUND}
        targets = [source]

    summary = {}

    with Session() as s:
        for src in targets:
            try:
                rows = registry[src](limit) if limit else registry[src]()
            except TypeError:
                # source doesn't accept limit
                rows = registry[src]()

            n_new = n_dup = 0
            for r in rows:
                existing = s.scalar(
                    select(Paper).where(
                        Paper.source == r["source"],
                        Paper.external_id == r["external_id"],
                    )
                )
                if existing:
                    n_dup += 1
                    continue
                s.add(Paper(**{
                    "source": r["source"],
                    "external_id": r["external_id"],
                    "title": r["title"],
                    "abstract": r.get("abstract"),
                    "authors": r.get("authors"),
                    "published_at": r.get("published_at"),
                    "pdf_url": r.get("pdf_url"),
                    "landing_url": r.get("landing_url"),
                    "categories": r.get("categories"),
                    "raw": r.get("raw"),
                }))
                n_new += 1
            s.commit()
            summary[src] = {"new": n_new, "duplicate": n_dup, "total_polled": len(rows)}

    return summary


if __name__ == "__main__":
    import json
    print(json.dumps(ingest(source="all"), indent=2))
