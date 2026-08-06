"""Build the index from arXiv's own API, with no OpenAlex budget in the loop.

OpenAlex meters its free tier by the day, and paging sixty candidates per
keeper exhausts it. arXiv does not: its API asks only for three seconds between
calls and returns a hundred entries at a time, every one of them with an open
PDF. So the corpus is built here, and citations are attached from Semantic
Scholar, which is also free and keyless.

Same methodology as everywhere else: the three gates from fetch_papers decide
what is indexed, and ranking is by percentile inside a publication year, since
OpenAlex's field-normalised percentile is unavailable while the budget is out.

    uv run python tools/fetch_arxiv_bulk.py --target 1000
    uv run python tools/fetch_arxiv_bulk.py --target 1000 --no-thumbs
"""

from __future__ import annotations

import argparse
import io
import json
import os
import re
import sys
import time
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

import feedparser
import httpx

import fetch_papers as fp

API = "https://export.arxiv.org/api/query"
PAGE = 100          # arXiv's practical maximum per call
PAUSE = 3.1         # what arXiv asks for between calls


def harvest(target: int, client: httpx.Client) -> list[dict]:
    """Walk the q-fin listing newest-first, keeping what passes the gates."""
    kept: list[dict] = []
    seen: set[str] = set()
    start, scanned, empty = 0, 0, 0
    while len(kept) < target and start < 30000 and empty < 3:
        r = client.get(API, params={
            "search_query": "cat:q-fin*", "sortBy": "submittedDate",
            "sortOrder": "descending", "start": start, "max_results": PAGE,
        }, headers=fp.UA, timeout=120)
        feed = feedparser.parse(r.text)
        if not feed.entries:
            empty += 1
            time.sleep(PAUSE * 2)
            start += PAGE
            continue
        empty = 0
        scanned += len(feed.entries)
        for e in feed.entries:
            axid = e.id.rsplit("/abs/", 1)[-1]
            base = re.sub(r"v\d+$", "", axid)
            if base in seen:
                continue
            seen.add(base)
            title = re.sub(r"\s+", " ", e.title).strip()
            summary = re.sub(r"\s+", " ", e.summary).strip()
            names = [a.name for a in getattr(e, "authors", [])]
            rec = {
                "arxiv_id": axid,
                "thumb_key": axid,
                "doi": f"https://doi.org/10.48550/arXiv.{base}",
                "title": title,
                "authors": ", ".join(names[:3]) + (" et al." if len(names) > 3 else ""),
                "author_count": len(names),
                "abstract": summary,
                "published": e.published[:10],
                "primary_category": f"arXiv:{base}",
                "url": f"https://arxiv.org/abs/{axid}",
                "pdf": f"https://arxiv.org/pdf/{axid}",
                "citations": 0,
                "citations_per_month": 0.0,
                "percentile": 0.0,
                "influential": 0,
                "source": "arxiv",
                "tags": fp.tags_for(f"{title} {summary}"),
            }
            ok, _ = fp.practical(rec)
            if ok:
                rec["status"], rec["status_note"] = fp.testability(f"{title} {summary}")
                kept.append(rec)
                if len(kept) >= target:
                    break
        print(f"    scanned {scanned}, kept {len(kept)}", flush=True)
        start += PAGE
        time.sleep(PAUSE)
    return kept


def add_citations(papers: list[dict], client: httpx.Client) -> int:
    """Semantic Scholar gives both counts in one keyless call, 400 ids at a time."""
    index = {f"ARXIV:{re.sub(r'v\\d+$', '', p['arxiv_id'])}": p for p in papers}
    ids, found = list(index), 0
    for i in range(0, len(ids), 400):
        chunk = ids[i:i + 400]
        for attempt in range(5):
            r = client.post("https://api.semanticscholar.org/graph/v1/paper/batch",
                            params={"fields": "citationCount,influentialCitationCount"},
                            json={"ids": chunk}, timeout=120)
            if r.status_code == 200:
                for key, row in zip(chunk, r.json()):
                    if not row:
                        continue
                    p = index[key]
                    p["citations"] = int(row.get("citationCount") or 0)
                    p["influential"] = int(row.get("influentialCitationCount") or 0)
                    p["citations_per_month"] = fp.per_month(p["citations"], p["published"])
                    found += 1
                break
            time.sleep(4.0 * (attempt + 1))
        print(f"    citations {min(i + 400, len(ids))}/{len(ids)}", flush=True)
        time.sleep(1.5)
    return found


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--target", type=int, default=1000)
    ap.add_argument("--no-thumbs", action="store_true")
    args = ap.parse_args()

    with httpx.Client(follow_redirects=True) as client:
        print(f"harvesting arXiv q-fin until {args.target} pass the gates")
        papers = harvest(args.target, client)
        print(f"  kept {len(papers)}")

        print("citations from Semantic Scholar")
        print(f"  matched {add_citations(papers, client)}")

    if not args.no_thumbs:
        print(f"rendering first pages ({len(papers)})", flush=True)
        ok = 0
        for i, p in enumerate(papers, 1):
            p["thumb"] = fp.render_thumb(p)
            ok += bool(p["thumb"])
            if i % 50 == 0:
                print(f"    {i}/{len(papers)}  ok={ok}", flush=True)
            time.sleep(0.45)
        before = len(papers)
        papers = [p for p in papers if p.get("thumb")]
        print(f"  {len(papers)} rendered, dropped {before - len(papers)} unreadable")

    # Percentile inside the publication year, since the field-normalised one
    # needs OpenAlex. Marked local so the page never passes it off as theirs.
    by_year: dict[str, list[dict]] = {}
    for p in papers:
        by_year.setdefault(p["published"][:4], []).append(p)
    for group in by_year.values():
        group.sort(key=lambda p: -p["citations"])
        n = len(group)
        for i, p in enumerate(group):
            p["percentile"] = round(1 - (i + 0.5) / n, 4) if n > 1 else 0.5
            p["percentile_source"] = "local"

    papers.sort(key=lambda p: (-(p.get("percentile") or 0), -p["citations"]))
    stamp = datetime.now(timezone.utc).isoformat(timespec="seconds")

    existing = []
    if os.path.exists(fp.PAPERS_JSON):
        with open(fp.PAPERS_JSON, encoding="utf-8") as fh:
            existing = json.load(fh).get("papers", [])
    have = {(p.get("title") or "").lower()[:90] for p in papers}
    merged = papers + [p for p in existing
                       if (p.get("title") or "").lower()[:90] not in have
                       and p.get("thumb")]

    with open(fp.PAPERS_JSON, "w", encoding="utf-8") as fh:
        json.dump({"fetched_at": stamp, "papers": merged}, fh, indent=2)
    print(f"wrote {fp.PAPERS_JSON} with {len(merged)} papers "
          f"({len(papers)} new from arXiv, {len(merged) - len(papers)} kept)")


if __name__ == "__main__":
    main()
