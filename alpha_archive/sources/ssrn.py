"""SSRN poller via Crossref.

SSRN itself blocks direct scraping (403/cloudflare). Crossref indexes
all DOI-registered SSRN papers under the prefix 10.2139.
"""
from __future__ import annotations

from .crossref import search_crossref, DEFAULT_QUERY

SSRN_DOI_PREFIX = "10.2139"


def poll_ssrn(
    limit: int = 50,
    *,
    query: str = DEFAULT_QUERY,
    since_date: str | None = "2024-01-01",
) -> list[dict]:
    filters = [f"prefix:{SSRN_DOI_PREFIX}"]
    if since_date:
        filters.append(f"from-pub-date:{since_date}")
    return search_crossref(
        source="ssrn",
        filters=filters,
        query=query,
        rows=min(limit, 1000),
    )[:limit]


if __name__ == "__main__":
    rows = poll_ssrn(limit=10)
    print(f"fetched {len(rows)} SSRN papers")
    for r in rows:
        pub = str(r["published_at"])[:10] if r["published_at"] else "?"
        print(f"  [{r['external_id']}] {pub} {r['title'][:80]}")
