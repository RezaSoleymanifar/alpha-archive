"""Pull recent q-fin papers from arXiv and render their first page as a thumbnail.

Fills the index with real, recent papers so the site has the shape of a working
registry rather than two entries. Every paper here is queued, not replicated —
nothing claims a result it does not have, and the card says so.

Thumbnails are the paper's actual first page, the same as the reference site.
That is only done for arXiv, where the PDF is openly distributed; a paywalled
publisher PDF is neither fetched nor rendered, and those papers keep a
generated figure instead.

    uv run python tools/fetch_papers.py --limit 28
"""

from __future__ import annotations

import argparse
import io
import json
import os
import re
import time
from datetime import datetime, timezone

import feedparser
import httpx
import pypdfium2 as pdfium

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAPERS_JSON = os.path.join(ROOT, "data", "papers", "arxiv.json")
THUMB_DIR = os.path.join(ROOT, "docs", "thumbs")

UA = {"User-Agent": os.environ.get("VINTAGE_USER_AGENT",
                                   "Alpha Archive reza@soleymanifar.com")}
API = ("https://export.arxiv.org/api/query?search_query=cat:q-fin*"
       "&sortBy=submittedDate&sortOrder=descending&start={start}&max_results=100")

THUMB_W = 320          # rendered wide, displayed smaller, so it stays crisp on retina

# Rough topical routing, so cards carry tags a reader can filter on.
TAG_RULES = [
    ("momentum", r"momentum|trend follow"),
    ("reversal", r"reversal|mean.revers"),
    ("volatility", r"volatilit|garch|realized vol"),
    ("machine-learning", r"machine learning|neural|deep learning|transformer|LLM|reinforcement"),
    ("options", r"option|implied vol|derivative pricing"),
    ("crypto", r"crypto|bitcoin|defi|blockchain|token"),
    ("portfolio", r"portfolio|allocation|optimi[sz]ation|risk parity"),
    ("microstructure", r"microstructur|limit order|high.frequenc|order flow"),
    ("factors", r"factor|cross.section|anomal|asset pricing"),
    ("risk", r"risk management|drawdown|tail risk|var\b|expected shortfall"),
    ("macro", r"macro|inflation|monetary|exchange rate|interest rate"),
    ("sentiment", r"sentiment|news|text|social media"),
]

# What we could actually run today, given free data. Honest, and it drives a filter.
TESTABLE = re.compile(
    r"momentum|reversal|trend|moving average|cross.section|factor|anomal|"
    r"volatilit|portfolio|calendar|seasonal", re.I)
NEEDS_MORE = re.compile(
    r"option|implied|limit order|high.frequenc|microstructur|analyst|"
    r"earnings call|proprietary|intraday|order flow|tick", re.I)


def tags_for(text: str) -> list[str]:
    found = [tag for tag, pattern in TAG_RULES if re.search(pattern, text, re.I)]
    return found[:3] or ["quant-finance"]


def testability(text: str) -> tuple[str, str]:
    if NEEDS_MORE.search(text):
        return "blocked", "needs options, intraday or analyst data we do not have"
    if TESTABLE.search(text):
        return "queued", "runnable with free point-in-time data"
    return "triage", "not yet assessed"


def fetch_listing(limit: int) -> list[dict]:
    entries = []
    for start in range(0, max(limit, 1), 100):
        feed = feedparser.parse(
            httpx.get(API.format(start=start), headers=UA, timeout=120).text)
        entries += feed.entries
        if len(entries) >= limit:
            break
        time.sleep(3.2)                      # arXiv asks for one call every 3s

    out = []
    for e in entries[:limit]:
        arxiv_id = e.id.rsplit("/abs/", 1)[-1]
        summary = re.sub(r"\s+", " ", e.summary).strip()
        title = re.sub(r"\s+", " ", e.title).strip()
        status, why = testability(f"{title} {summary}")
        authors = [a.name for a in getattr(e, "authors", [])]
        out.append({
            "arxiv_id": arxiv_id,
            "title": title,
            "authors": ", ".join(authors[:3]) + (" et al." if len(authors) > 3 else ""),
            "author_count": len(authors),
            "abstract": summary,
            "published": e.published[:10],
            "primary_category": e.tags[0]["term"] if e.tags else "q-fin",
            "url": f"https://arxiv.org/abs/{arxiv_id}",
            "pdf": f"https://arxiv.org/pdf/{arxiv_id}",
            "tags": tags_for(f"{title} {summary}"),
            "status": status,
            "status_note": why,
        })
    return out


def render_thumb(paper: dict) -> str | None:
    """First page as a JPEG. Returns the path relative to docs/, or None."""
    os.makedirs(THUMB_DIR, exist_ok=True)
    safe = paper["arxiv_id"].replace("/", "_")
    rel = f"thumbs/{safe}.jpg"
    dest = os.path.join(THUMB_DIR, f"{safe}.jpg")
    if os.path.exists(dest) and os.path.getsize(dest) > 2000:
        return rel

    try:
        r = httpx.get(paper["pdf"], headers=UA, timeout=180, follow_redirects=True)
        if r.status_code != 200 or not r.content.startswith(b"%PDF"):
            return None
        page = pdfium.PdfDocument(r.content)[0]
        img = page.render(scale=2.0).to_pil().convert("RGB")
        img = img.resize((THUMB_W, round(img.height * THUMB_W / img.width)))
        img.save(dest, "JPEG", quality=72, optimize=True)
        return rel
    except Exception as exc:
        print(f"    thumb failed for {paper['arxiv_id']}: {type(exc).__name__}")
        return None


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=28)
    ap.add_argument("--no-thumbs", action="store_true")
    args = ap.parse_args()

    print(f"fetching {args.limit} recent q-fin papers from arXiv")
    papers = fetch_listing(args.limit)
    print(f"  got {len(papers)}")

    if not args.no_thumbs:
        print("rendering first pages")
        for i, p in enumerate(papers, 1):
            p["thumb"] = render_thumb(p)
            if i % 6 == 0:
                print(f"    {i}/{len(papers)}")
            time.sleep(1.1)                  # be a good citizen with arXiv's CDN
    got = sum(1 for p in papers if p.get("thumb"))
    print(f"  thumbnails: {got}/{len(papers)}")

    counts: dict[str, int] = {}
    for p in papers:
        counts[p["status"]] = counts.get(p["status"], 0) + 1
    print("  by status:", counts)

    os.makedirs(os.path.dirname(PAPERS_JSON), exist_ok=True)
    with open(PAPERS_JSON, "w", encoding="utf-8") as fh:
        json.dump({"fetched_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                   "papers": papers}, fh, indent=2)
    print(f"wrote {PAPERS_JSON}")


if __name__ == "__main__":
    main()
