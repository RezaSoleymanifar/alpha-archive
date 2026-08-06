"""Re-apply the gates and add influential citations to an existing index.

The gates in fetch_papers.py change more often than the universe does, and a
full refetch costs twenty minutes of somebody else's bandwidth. This runs the
current gates over data/papers/papers.json, drops what no longer qualifies,
fills in Semantic Scholar's influential-citation count, and writes it back.

    uv run python tools/refine_universe.py
"""

from __future__ import annotations

import io
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

import httpx

import fetch_papers as fp


def main() -> None:
    data = json.load(open(fp.PAPERS_JSON, encoding="utf-8"))
    papers = data["papers"]

    keep, reasons = [], {}
    for p in papers:
        ok, why = fp.practical(p)
        if ok and not p.get("thumb"):
            ok, why = False, "no open pdf — cannot be read or rerun"
        if ok:
            keep.append(p)
        else:
            key = why.split(" (")[0]
            reasons[key] = reasons.get(key, 0) + 1

    print(f"{len(keep)}/{len(papers)} survive the current gates")
    for why, n in sorted(reasons.items(), key=lambda kv: -kv[1]):
        print(f"  dropped {n:>4}  {why}")

    with httpx.Client(follow_redirects=True) as client:
        print("influential citations from Semantic Scholar")
        got = fp.add_influential(keep, client)
        print(f"  matched {got}/{len(keep)}")

    # OpenAlex does not score a paper until it has a year of citations, which is
    # exactly the cohort the leaderboard cares about. Fill the gap with the
    # paper's percentile inside its own publication year, in our own corpus, and
    # mark it estimated rather than passing it off as theirs.
    by_year: dict[str, list[dict]] = {}
    for p in keep:
        by_year.setdefault((p.get("published") or "0000")[:4], []).append(p)
    filled = 0
    for year, group in by_year.items():
        group.sort(key=lambda p: -p["citations"])
        n = len(group)
        for i, p in enumerate(group):
            if p.get("percentile"):
                p["percentile_source"] = "openalex"
                continue
            p["percentile"] = round(1 - (i + 0.5) / n, 4) if n > 1 else 0.5
            p["percentile_source"] = "local"
            filled += 1
    print(f"  filled {filled} percentiles from the local year cohort")

    keep.sort(key=lambda p: (-(p.get("percentile") or 0), -p["citations"]))
    data["papers"] = keep
    with open(fp.PAPERS_JSON, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2)
    print(f"wrote {fp.PAPERS_JSON}")


if __name__ == "__main__":
    main()
