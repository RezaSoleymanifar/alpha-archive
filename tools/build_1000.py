"""Grow the index to a target size, open access only, gates applied.

Sorting by citations and paging until the quota fills, one pass per window so
the 30-day tab is not empty while the all-time tab overflows. `is_oa:true` is
asked of OpenAlex directly, so every paper here has a PDF a reader can open.
Which is also what makes a real first-page thumbnail possible.

    uv run python tools/build_1000.py --target 1000
    uv run python tools/build_1000.py --target 1000 --no-thumbs
"""

from __future__ import annotations

import argparse
import io
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

import httpx

import fetch_papers as fp

# How the target is split across publication-date cohorts. Recent windows get a
# smaller share because less exists, not because it matters less.
QUOTAS = [("30d", 30, 0.06), ("12m", 365, 0.16), ("5y", 1826, 0.26),
          ("10y", 3653, 0.26), ("all", None, 0.26)]


def collect(filter_str: str, want: int, source: str, client: httpx.Client,
            seen: set[str]) -> list[dict]:
    out: list[dict] = []
    cursor, scanned = "*", 0
    while len(out) < want and cursor and scanned < want * 60:
        try:
            page = fp.openalex({"filter": filter_str, "sort": "cited_by_count:desc",
                                "per-page": 200, "cursor": cursor}, client)
        except Exception as exc:
            print(f"    stopped: {type(exc).__name__}")
            break
        results = page.get("results", [])
        scanned += len(results)
        for work in results:
            rec = fp.to_record(work, source)
            key = rec["title"].lower()[:90]
            if not rec["title"] or key in seen:
                continue
            ok, _ = fp.practical(rec)
            if ok:
                seen.add(key)
                out.append(rec)
                if len(out) >= want:
                    break
        cursor = (page.get("meta") or {}).get("next_cursor")
        if not results:
            break
        time.sleep(0.3)
    print(f"    kept {len(out)} of {scanned} scanned")
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--target", type=int, default=1000)
    ap.add_argument("--no-thumbs", action="store_true")
    args = ap.parse_args()

    topics = "primary_topic.id:" + "|".join(fp.QUANT_TOPICS)
    arxiv = (f"primary_location.source.id:{fp.ARXIV_SOURCE},"
             f"primary_topic.subfield.id:{fp.FINANCE_SUBFIELD},is_oa:true")
    openpub = f"{topics},is_oa:true"

    seen: set[str] = set()
    papers: list[dict] = []
    with httpx.Client(follow_redirects=True) as client:
        for key, days, share in QUOTAS:
            want = max(int(args.target * share), 10)
            since = fp.window_filter(days)
            print(f"{key}: want {want}")
            got = collect(arxiv + since, want // 2, "arxiv", client, seen)
            got += collect(openpub + since, want - len(got), "journal", client, seen)
            papers += got

        print(f"\ncollected {len(papers)} papers")
        print("influential citations from Semantic Scholar")
        print(f"  matched {fp.add_influential(papers, client)}")

    if not args.no_thumbs:
        print(f"rendering first pages ({len(papers)})", flush=True)
        ok = 0
        for i, p in enumerate(papers, 1):
            p["thumb"] = fp.render_thumb(p)
            ok += bool(p["thumb"])
            if i % 50 == 0:
                print(f"    {i}/{len(papers)}  ok={ok}", flush=True)
            time.sleep(0.5)
        before = len(papers)
        papers = [p for p in papers if p.get("thumb")]
        print(f"  {len(papers)} rendered, dropped {before - len(papers)} unreadable")

    # Percentile fallback for anything OpenAlex has not scored yet.
    by_year: dict[str, list[dict]] = {}
    for p in papers:
        by_year.setdefault((p.get("published") or "0000")[:4], []).append(p)
    for group in by_year.values():
        group.sort(key=lambda p: -p["citations"])
        n = len(group)
        for i, p in enumerate(group):
            if not p.get("percentile"):
                p["percentile"] = round(1 - (i + 0.5) / n, 4) if n > 1 else 0.5
                p["percentile_source"] = "local"
            else:
                p["percentile_source"] = "openalex"

    papers.sort(key=lambda p: (-(p.get("percentile") or 0), -p["citations"]))
    from datetime import datetime, timezone
    stamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
    with open(fp.PAPERS_JSON, "w", encoding="utf-8") as fh:
        json.dump({"fetched_at": stamp, "papers": papers}, fh, indent=2)
    print(f"wrote {fp.PAPERS_JSON} with {len(papers)} papers")


if __name__ == "__main__":
    main()
