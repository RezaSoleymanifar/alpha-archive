"""Audit the indexed universe: is each paper something a desk could code?

Three questions, asked in order, and a paper has to pass all three:

  1. Does it name a mechanism?      A signal, a portfolio rule, a forecast.
  2. Can we get the data?           Daily equities, factors, macro, crypto and
                                    short volume are free. Options chains,
                                    tick data, analyst estimates and holdings
                                    are not, so those papers cannot be run.
  3. Is it engineering, not proof?  A convergence theorem for a PDE scheme is
                                    codeable and useless to a desk.

Papers that fail are not deleted here, this prints the ledger so the filter in
fetch_papers.py can be argued with. Run it after every fetch.

    uv run python tools/audit_universe.py            # summary + samples
    uv run python tools/audit_universe.py --write    # also writes docs/audit.md
"""

from __future__ import annotations

import argparse
import io
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

import fetch_papers as fp

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def audit(p: dict) -> tuple[bool, str]:
    """The gates live in fetch_papers so the index and the audit cannot drift."""
    return fp.practical(p)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    args = ap.parse_args()

    path = os.path.join(ROOT, "data", "papers", "papers.json")
    papers = json.load(open(path, encoding="utf-8"))["papers"]

    keep, drop = [], []
    for p in papers:
        ok, why = audit(p)
        (keep if ok else drop).append((p, why))

    reasons: dict[str, int] = {}
    for _, why in drop:
        key = why.split(" (")[0]
        reasons[key] = reasons.get(key, 0) + 1

    print(f"{len(keep)}/{len(papers)} papers survive the audit\n")
    print("rejected, by reason:")
    for why, n in sorted(reasons.items(), key=lambda kv: -kv[1]):
        print(f"  {n:>4}  {why}")

    print("\nkeepers, most cited first:")
    for p, _ in sorted(keep, key=lambda kv: -kv[0]["citations"])[:20]:
        print(f"  {p['citations']:>6}  {p['title'][:74]}")

    print("\nrejects, most cited first (these are the judgement calls):")
    for p, why in sorted(drop, key=lambda kv: -kv[0]["citations"])[:15]:
        print(f"  {p['citations']:>6}  {p['title'][:56]}\n          -> {why}")

    if args.write:
        out = os.path.join(ROOT, "docs", "audit.md")
        with open(out, "w", encoding="utf-8", newline="\n") as fh:
            fh.write("# Universe audit\n\n")
            fh.write(f"{len(keep)} of {len(papers)} indexed papers are runnable: "
                     "they name a mechanism, the data is free, and the deliverable "
                     "is a position rather than a proof.\n\n## Rejected, by reason\n\n")
            fh.write("| Papers | Reason |\n|---:|---|\n")
            for why, n in sorted(reasons.items(), key=lambda kv: -kv[1]):
                fh.write(f"| {n} | {why} |\n")
            fh.write("\n## The judgement calls\n\nThe most-cited rejects, so the "
                     "filter can be argued with rather than trusted.\n\n")
            fh.write("| Citations | Paper | Why not |\n|---:|---|---|\n")
            for p, why in sorted(drop, key=lambda kv: -kv[0]["citations"])[:25]:
                title = p["title"].replace("|", "\\|")[:90]
                fh.write(f"| {p['citations']:,} | {title} | {why} |\n")
        print(f"\nwrote {out}")


if __name__ == "__main__":
    main()
