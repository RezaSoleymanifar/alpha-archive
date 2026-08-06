"""Crossref search client.

Crossref (https://crossref.org) is the canonical DOI registry: every
DOI'd paper from every major venue is indexed there with a free,
unauthenticated REST API. We use it as the backend for sources that
publish via DOI (NBER prefix 10.3386, SSRN prefix 10.2139, plus most
peer-reviewed journals).

Polite usage: pass `mailto` query param via the `CROSSREF_MAILTO` env
var to get the polite-pool rate limit.
"""
from __future__ import annotations

import os
from datetime import datetime
from typing import Iterable

import httpx

CROSSREF_WORKS = "https://api.crossref.org/works"

DEFAULT_QUERY = "cross-section stock returns anomaly factor"


def _mailto() -> str:
    return os.environ.get("CROSSREF_MAILTO", "alpha-archive@local")


def _to_record(w: dict, *, source: str) -> dict:
    title = ""
    titles = w.get("title") or []
    if titles:
        title = titles[0].strip()

    abstract = w.get("abstract") or ""
    # Crossref abstracts arrive as JATS XML; cheap strip
    if abstract:
        import re
        abstract = re.sub(r"<[^>]+>", "", abstract).strip()

    authors_list = w.get("author") or []
    authors = ", ".join(
        f"{a.get('given','').strip()} {a.get('family','').strip()}".strip()
        for a in authors_list[:10]
    )

    pub_dt = None
    parts = (w.get("issued") or {}).get("date-parts") or [[None]]
    if parts and parts[0]:
        try:
            y = parts[0][0]
            m = parts[0][1] if len(parts[0]) > 1 else 1
            d = parts[0][2] if len(parts[0]) > 2 else 1
            if y is not None:
                pub_dt = datetime(int(y), int(m), int(d))
        except (TypeError, ValueError):
            pub_dt = None

    venue = (w.get("container-title") or [None])[0] or w.get("publisher") or "?"

    doi = w.get("DOI") or ""
    landing = w.get("URL") or (f"https://doi.org/{doi}" if doi else None)

    pdf_url = None
    for link in w.get("link") or []:
        if (link.get("content-type") or "").lower() == "application/pdf":
            pdf_url = link.get("URL")
            break

    return {
        "source": source,
        "external_id": doi.rsplit("/", 1)[-1] if doi else "",
        "title": title,
        "abstract": abstract or None,
        "authors": authors or None,
        "published_at": pub_dt,
        "pdf_url": pdf_url,
        "landing_url": landing,
        "categories": venue,
        "raw": {"doi": doi},
    }


def search_crossref(
    *,
    source: str,
    filters: Iterable[str],
    query: str = DEFAULT_QUERY,
    rows: int = 50,
    sort: str = "published",
    order: str = "desc",
) -> list[dict]:
    """Run a Crossref search with the given filters and return
    standardized paper records.

    Filters use Crossref's filter syntax, e.g. `prefix:10.3386` or
    `from-pub-date:2024-01-01`.
    """
    params = {
        "query": query,
        "filter": ",".join(filters),
        "rows": str(rows),
        "sort": sort,
        "order": order,
        "mailto": _mailto(),
    }
    try:
        r = httpx.get(CROSSREF_WORKS, params=params, timeout=30)
        r.raise_for_status()
    except Exception as e:
        print(f"[crossref:{source}] fetch failed: {e}")
        return []
    data = r.json().get("message", {})
    return [_to_record(w, source=source) for w in data.get("items", [])]
