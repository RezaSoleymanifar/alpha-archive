"""Generate docs/PAPERS_TODO.md, the shortlist, ordered by what to build next.

The ledger says which papers are reproducible. It does not say what any of them
costs to build, and without that the shortlist is a wish rather than a queue.

Effort is estimated from what the judgement already recorded: how many distinct
sources the paper needs, how large its universe is, and whether anything has to
be trained rather than computed. It is a tier, not an estimate in hours, because
a tier is the most these signals can honestly support.

Ranking puts the cheapest well-specified papers first. A paper is worth building
early when its targets are numerous and numeric, those are the ones where a
replication can be declared right or wrong rather than argued about.

    uv run python tools/build_todo.py
"""

from __future__ import annotations

import io
import json
import os
import re
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LEDGER = os.path.join(ROOT, "data", "triage", "ledger.json")
PAPERS = os.path.join(ROOT, "data", "papers", "papers.json")
OUT = os.path.join(ROOT, "docs", "PAPERS_TODO.md")

# Things that cost real time regardless of how clean the data is.
TRAINED = re.compile(
    r"\bLSTM\b|\bGRU\b|transformer|neural|deep|reinforcement|\bRL\b|\bPPO\b|"
    r"\bGCN\b|\bGNN\b|foundation model|fine-?tune|\bLLM\b|agentic",
    re.I,
)
FITTED = re.compile(
    r"\bGARCH\b|\bEGARCH\b|\bMLE\b|Bayesian|\bMCMC\b|\bHMM\b|Markov|"
    r"\bSVM\b|random forest|kernel|copula|GAMLSS|filter",
    re.I,
)
BIG_UNIVERSE = re.compile(r"\b([1-9]\d{2,})\s+(?:stocks|names|constituents|equities|funds|assets)", re.I)


def norm(key: str) -> str:
    return re.sub(r"v\d+$", "", (key or "").strip())


def effort(entry: dict) -> tuple[str, str]:
    """A tier and the reason for it."""
    text = " ".join([entry.get("method") or "", " ".join(entry.get("data_needed") or [])])
    sources = len(entry.get("data_needed") or [])

    big = BIG_UNIVERSE.search(text)
    universe = int(big.group(1)) if big else 0

    if TRAINED.search(text):
        return "L", "a model has to be trained, so results move with the seed"
    if universe >= 100 or sources >= 4:
        return "M", (f"{universe} names" if universe else f"{sources} separate sources")
    if FITTED.search(text):
        return "M", "an estimator has to be fitted and checked"
    return "S", "closed-form on a small universe"


def numeracy(entry: dict) -> int:
    """How checkable the targets are: more digits, less room to argue."""
    return sum(sum(c.isdigit() for c in t) for t in entry.get("reproducible_targets") or [])


def main() -> None:
    with open(LEDGER, encoding="utf-8") as fh:
        papers = json.load(fh)["papers"]
    with open(PAPERS, encoding="utf-8") as fh:
        index = json.load(fh)
    rows = index if isinstance(index, list) else index.get("papers", [])
    meta = {norm(p.get("arxiv_id")): p for p in rows}

    keeps = []
    for key, entry in papers.items():
        if entry.get("verdict") != "keep":
            continue
        tier, why = effort(entry)
        paper = meta.get(norm(key), {})
        keeps.append({
            "id": norm(key),
            "title": (paper.get("title") or "").strip() or norm(key),
            "url": paper.get("url") or f"https://arxiv.org/abs/{norm(key)}",
            "published": paper.get("published") or "",
            "confidence": entry.get("confidence") or 0,
            "tier": tier,
            "why": why,
            "targets": entry.get("reproducible_targets") or [],
            "data": entry.get("data_needed") or [],
            "method": entry.get("method") or "",
            "digits": numeracy(entry),
        })

    order = {"S": 0, "M": 1, "L": 2}
    keeps.sort(key=lambda k: (order[k["tier"]], -k["confidence"], -k["digits"]))

    counts = {t: sum(1 for k in keeps if k["tier"] == t) for t in "SML"}
    judged = len(papers)
    drops = judged - len(keeps)

    nl = chr(10)
    out = [
        "# Papers to build",
        "",
        f"{len(keeps)} of {judged} judged papers are reproducible on free data. "
        f"The other {drops} are not, and [the ledger](../data/triage/ledger.json) "
        "records why for each one.",
        "",
        "Effort is a tier, not an hour count. It is inferred from what the "
        "judgement recorded, how many sources a paper needs, how large its "
        "universe is, and whether anything must be trained, because that is the "
        "most those signals honestly support.",
        "",
        "| Tier | Meaning | Count |",
        "|---|---|---|",
        f"| **S** | Closed-form on a small universe. A sitting. | {counts['S']} |",
        f"| **M** | An estimator to fit, or several sources to join. | {counts['M']} |",
        f"| **L** | A model to train. Results move with the seed. | {counts['L']} |",
        "",
        "Ordered cheapest first, then by confidence, then by how numeric the "
        "published targets are. A paper with many exact numbers can be declared "
        "right or wrong; a paper with prose claims can only be argued about.",
        "",
        "---",
        "",
    ]

    for i, k in enumerate(keeps, 1):
        out += [
            f"## {i}. {k['title']}",
            "",
            f"`{k['id']}` · [arXiv]({k['url']}) · **{k['tier']}**, {k['why']} · "
            f"confidence {k['confidence']:.2f}"
            + (f" · {k['published'][:10]}" if k["published"] else ""),
            "",
            k["method"],
            "",
        ]
        if k["data"]:
            out.append("**Data**")
            out += [f"- {d}" for d in k["data"]]
            out.append("")
        if k["targets"]:
            out.append("**Must land on**")
            out += [f"- {t}" for t in k["targets"]]
            out.append("")

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    body = nl.join(out) + nl
    with open(OUT, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(body)

    print(f"wrote {OUT} ({len(body):,} bytes)")
    print(f"{len(keeps)} keeps  S={counts['S']} M={counts['M']} L={counts['L']}")


if __name__ == "__main__":
    main()
