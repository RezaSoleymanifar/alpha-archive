"""NBER (National Bureau of Economic Research) working papers poller.

NBER's own site blocks direct scraping (403). The reliable free path is
the Crossref DOI registry, where every NBER WP is indexed under the
DOI prefix 10.3386.
"""
from __future__ import annotations

from .crossref import search_crossref, DEFAULT_QUERY

NBER_DOI_PREFIX = "10.3386"


def poll_nber(
    limit: int = 50,
    *,
    query: str = DEFAULT_QUERY,
    since_date: str | None = "2024-01-01",
) -> list[dict]:
    filters = [f"prefix:{NBER_DOI_PREFIX}"]
    if since_date:
        filters.append(f"from-pub-date:{since_date}")
    return search_crossref(
        source="nber",
        filters=filters,
        query=query,
        rows=min(limit, 1000),
    )[:limit]


if __name__ == "__main__":
    rows = poll_nber(limit=10)
    print(f"fetched {len(rows)} NBER working papers")
    for r in rows:
        pub = str(r["published_at"])[:10] if r["published_at"] else "?"
        print(f"  [{r['external_id']}] {pub} {r['title'][:80]}")
