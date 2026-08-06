"""OpenAlex search client.

OpenAlex is a free, comprehensive academic index (https://openalex.org)
with a REST API. We use it as the data backend for sources that block
direct scraping (NBER, SSRN). The same client also surfaces papers from
top finance journals (JF, JFE, RFS, JFQA) which would otherwise require
publisher API access.

Polite-pool requires a `mailto` query param; pass user email via
`OPENALEX_MAILTO` env var or hardcode at the call site.
"""
from __future__ import annotations

import os
from datetime import datetime
from typing import Iterable

import httpx

OPENALEX_WORKS = "https://api.openalex.org/works"

# Default search query — favors anomaly / factor / cross-section papers.
DEFAULT_QUERY = "cross-section stock returns anomaly factor"


def _mailto() -> str:
    return os.environ.get("OPENALEX_MAILTO", "alpha-archive@local")


def _to_record(w: dict, *, source: str) -> dict:
    primary = w.get("primary_location") or {}
    src = primary.get("source") or {}
    venue_name = src.get("display_name") or "?"

    pdf_url = None
    best_oa = w.get("best_oa_location") or {}
    pdf_url = best_oa.get("pdf_url") or primary.get("pdf_url")

    landing = primary.get("landing_page_url") or w.get("doi")

    authors = ", ".join(
        (a.get("author") or {}).get("display_name") or "?"
        for a in (w.get("authorships") or [])[:10]
    )

    abstract = _reconstruct_abstract(w.get("abstract_inverted_index"))

    pub = w.get("publication_date")
    pub_dt = None
    if pub:
        try:
            pub_dt = datetime.fromisoformat(pub)
        except ValueError:
            pub_dt = None

    return {
        "source": source,
        "external_id": w.get("id", "").rsplit("/", 1)[-1],
        "title": (w.get("title") or "").strip(),
        "abstract": abstract,
        "authors": authors,
        "published_at": pub_dt,
        "pdf_url": pdf_url,
        "landing_url": landing,
        "categories": venue_name,
        "raw": {"doi": w.get("doi"), "openalex_id": w.get("id")},
    }


def _reconstruct_abstract(inv: dict | None) -> str | None:
    """OpenAlex stores abstracts as inverted index. Reconstruct text."""
    if not inv:
        return None
    positions: list[tuple[int, str]] = []
    for word, idxs in inv.items():
        for i in idxs:
            positions.append((i, word))
    positions.sort()
    return " ".join(w for _, w in positions)


def search_openalex(
    *,
    source: str,
    filters: Iterable[str],
    query: str = DEFAULT_QUERY,
    per_page: int = 50,
    page: int = 1,
) -> list[dict]:
    """Run an OpenAlex search with the given filters and return
    standardized paper records."""
    params = {
        "search": query,
        "filter": ",".join(filters),
        "per_page": str(per_page),
        "page": str(page),
        "mailto": _mailto(),
    }
    try:
        r = httpx.get(OPENALEX_WORKS, params=params, timeout=30)
        r.raise_for_status()
    except Exception as e:
        print(f"[openalex:{source}] fetch failed: {e}")
        return []
    data = r.json()
    return [_to_record(w, source=source) for w in data.get("results", [])]
