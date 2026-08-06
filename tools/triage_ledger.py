"""Fold agent triage verdicts into a permanent ledger, keeps and drops alike.

A drop costs a full PDF read. Forgetting it means paying that cost again every
time the paper resurfaces in a harvest, so the ledger is append-only and the
harvester consults it before spending a token.

The drops are also the more interesting half. They record *why* a paper is out
of reach — RavenPack, Binance order books, a proprietary ALM engine, tables the
authors themselves labelled illustrative — which is a map of what the archive
would need to reach further.

    uv run python tools/triage_ledger.py            # fold in data/triage/result_*.json
    uv run python tools/triage_ledger.py --report   # summary of the ledger
"""

from __future__ import annotations

import argparse
import glob
import io
import json
import os
import re
import sys
from collections import Counter
from datetime import datetime, timezone

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LEDGER = os.path.join(ROOT, "data", "triage", "ledger.json")

# Why a paper is out of reach, grouped so the ledger reads as a map of gaps.
GAPS = [
    ("intraday / order book", r"order book|tick|intraday|high[- ]frequency|level-?1|LOB"),
    ("options surface", r"option (chain|surface)|implied vol|OptionMetrics|SPX|VIX"),
    ("vendor data", r"bloomberg|ravenpack|compustat|CRSP|WRDS|refinitiv|thetadata|"
                    r"dukascopy|cryptocompare|coin metrics|silicon data|proprietary"),
    ("crypto derivatives", r"binance|perpetual|funding rate|liquidation|on-chain|uniswap"),
    ("non-US market", r"chinese|shenzhen|A-share|warsaw|iranian|nifty|german power|IMF"),
    ("pure theory", r"pure theor|no empirical|theorem|proof|axiomat|no data"),
    ("synthetic only", r"synthetic|simulat|monte carlo|illustrative"),
    ("spec withheld", r"withheld|not (released|published|disclosed)|undisclosed"),
]


def classify(reason: str) -> str:
    for label, pattern in GAPS:
        if re.search(pattern, reason, re.I):
            return label
    return "other"


def load_ledger() -> dict:
    if os.path.exists(LEDGER):
        with open(LEDGER, encoding="utf-8") as fh:
            return json.load(fh)
    return {"updated_at": None, "papers": {}}


def base_id(arxiv_id: str) -> str:
    return re.sub(r"v\d+$", "", (arxiv_id or "").strip())


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--report", action="store_true")
    args = ap.parse_args()

    ledger = load_ledger()
    papers = ledger["papers"]

    if not args.report:
        added = updated = 0
        for path in sorted(glob.glob(os.path.join(ROOT, "data", "triage", "result_*.json"))):
            with open(path, encoding="utf-8") as fh:
                try:
                    rows = json.load(fh)
                except json.JSONDecodeError:
                    print(f"  skipped unreadable {os.path.basename(path)}")
                    continue
            for r in rows if isinstance(rows, list) else []:
                key = base_id(r.get("arxiv_id"))
                if not key:
                    continue
                entry = {
                    "verdict": r.get("verdict"),
                    "confidence": r.get("confidence"),
                    "method": r.get("method"),
                    "reason": r.get("reason"),
                    # The judgement states its own gap. Re-deriving one from the
                    # prose overwrote it, and collapsed every reason the regex
                    # had no pattern for — "out of scope", "live protocol" —
                    # into "other". classify() is only the fallback now, for the
                    # first ten batches which predate the field.
                    "gap": (r.get("gap") or classify(r.get("reason", "")))
                    if r.get("verdict") == "drop" else "",
                    "data_needed": r.get("data_needed", []),
                    "reproducible_targets": r.get("reproducible_targets", []),
                    "judged_at": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
                    "batch": os.path.basename(path),
                }
                if key in papers:
                    updated += 1
                else:
                    added += 1
                papers[key] = entry

        ledger["updated_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
        os.makedirs(os.path.dirname(LEDGER), exist_ok=True)
        with open(LEDGER, "w", encoding="utf-8") as fh:
            json.dump(ledger, fh, indent=1, sort_keys=True)
        print(f"ledger: {added} new, {updated} re-judged, {len(papers)} total")

    keeps = [k for k, v in papers.items() if v["verdict"] == "keep"]
    drops = [k for k, v in papers.items() if v["verdict"] == "drop"]
    print(f"\n{len(keeps)} keeps, {len(drops)} drops, {len(papers)} judged\n")

    print("why papers are out of reach:")
    for gap, n in Counter(papers[k]["gap"] for k in drops).most_common():
        print(f"  {n:>4}  {gap}")

    if args.report:
        print("\nkeeps, most confident first:")
        for k in sorted(keeps, key=lambda k: -(papers[k].get("confidence") or 0)):
            v = papers[k]
            print(f"  {v['confidence']:.2f}  {k}  {(v['method'] or '')[:64]}")


if __name__ == "__main__":
    main()
