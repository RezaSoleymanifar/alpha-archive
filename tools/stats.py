"""Print the index's headline statistics. Run after any fetch or build."""

from __future__ import annotations

import collections
import io
import json
import os
import sys
from datetime import datetime, timedelta, timezone

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load(name: str, key: str) -> list[dict]:
    path = os.path.join(ROOT, "data", "papers", name)
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as fh:
        return json.load(fh).get(key, [])


def main() -> None:
    papers = load("papers.json", "papers")
    specs = load("osap.json", "predictors")
    now = datetime.now(timezone.utc)

    print(f"papers indexed        {len(papers):>6}")
    print(f"  with a real first page{sum(1 for p in papers if p.get('thumb')):>4}"
          f"  ({100 * sum(1 for p in papers if p.get('thumb')) // max(len(papers), 1)}%)")
    print(f"osap predictors       {len(specs):>6}")
    print(f"total cards           {len(papers) + len(specs):>6}")

    print("\nby window")
    for label, days in (("30 days", 30), ("12 months", 365), ("5 years", 1826),
                        ("10 years", 3653)):
        cut = (now - timedelta(days=days)).strftime("%Y-%m-%d")
        n = sum(1 for p in papers if (p.get("published") or "") >= cut)
        print(f"  {label:<10} {n:>6}")

    years = [int((p.get('published') or '1900')[:4]) for p in papers if p.get("published")]
    if years:
        print(f"\noldest paper          {min(years)}")
        print(f"newest paper          {max(years)}")

    print("\nby source")
    for k, n in collections.Counter(p.get("source") for p in papers).most_common():
        print(f"  {str(k):<10} {n:>6}")

    print("\nby venue (top 8)")
    for k, n in collections.Counter(
            (p.get("primary_category") or "?").split(":")[0] for p in papers
    ).most_common(8):
        print(f"  {k[:34]:<34} {n:>4}")

    cites = sorted((p["citations"] for p in papers), reverse=True)
    if cites:
        print(f"\ncitations: max {cites[0]:,}  median {cites[len(cites) // 2]:,}  "
              f"total {sum(cites):,}")
    infl = [p.get("influential") or 0 for p in papers]
    print(f"influential counts matched {sum(1 for x in infl if x):>5}")
    oa = sum(1 for p in papers if p.get("percentile_source") == "openalex")
    print(f"percentiles: {oa} from OpenAlex, {len(papers) - oa} from the local year cohort")

    print("\ntop 10 by impact")
    for p in sorted(papers, key=lambda p: -(p.get("percentile") or 0))[:10]:
        print(f"  {p['citations']:>6} cites  {p['published'][:7]}  {p['title'][:58]}")


if __name__ == "__main__":
    main()
