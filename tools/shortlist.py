"""The 95 papers worth building, enriched once and shared.

The ledger holds verdicts, papers.json holds titles and thumbnails, and the
taxonomy holds the area and task. Three files, and both the website and the
work queue need the same join of them, so it happens here rather than twice
with two chances to disagree.

Effort is a tier inferred from what the judgement recorded, how many sources a
paper joins, how large its universe is, whether anything has to be trained. It
is not an estimate in hours, because a tier is the most those signals honestly
support.
"""

from __future__ import annotations

import json
import os
import re
import sys
from typing import Any

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from alpha_archive import taxonomy  # noqa: E402

LEDGER = os.path.join(ROOT, "data", "triage", "ledger.json")
PAPERS = os.path.join(ROOT, "data", "papers", "papers.json")
REPLICATIONS = os.path.join(ROOT, "data", "replications")
APPEAL = os.path.join(ROOT, "data", "triage", "appeal.json")

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
BIG_UNIVERSE = re.compile(
    r"\b([1-9]\d{2,})\s+(?:stocks|names|constituents|equities|funds|assets)", re.I)

TIERS = {
    "S": "Closed-form on a small universe. A sitting.",
    "M": "An estimator to fit, or several sources to join.",
    "L": "A model to train. Results move with the seed.",
}


def norm(arxiv_id: str | None) -> str:
    return re.sub(r"v\d+$", "", (arxiv_id or "").strip())


def effort(entry: dict) -> tuple[str, str]:
    text = " ".join([entry.get("method") or "",
                     " ".join(entry.get("data_needed") or [])])
    sources = len(entry.get("data_needed") or [])
    big = BIG_UNIVERSE.search(text)
    universe = int(big.group(1)) if big else 0

    if TRAINED.search(text):
        return "L", "a model has to be trained, so results move with the seed"
    if universe >= 100 or sources >= 4:
        return "M", f"{universe} names" if universe else f"{sources} separate sources"
    if FITTED.search(text):
        return "M", "an estimator has to be fitted and checked"
    return "S", "closed-form on a small universe"


def numeracy(entry: dict) -> int:
    """How checkable the targets are. More digits, less room to argue."""
    return sum(sum(c.isdigit() for c in t)
               for t in entry.get("reproducible_targets") or [])


def built() -> set[str]:
    """Papers with a replication already in the repo."""
    if not os.path.isdir(REPLICATIONS):
        return set()
    out = set()
    for name in os.listdir(REPLICATIONS):
        if name.endswith(".json"):
            try:
                with open(os.path.join(REPLICATIONS, name), encoding="utf-8") as fh:
                    out.add(norm(json.load(fh).get("arxiv_id")))
            except Exception:
                continue
    return {o for o in out if o}


def appeal_scores() -> dict[str, dict[str, Any]]:
    """How much a working quant would want to read each one.

    Reproducibility and worth reading are different questions. A paper can be
    perfectly reproducible and still be the four hundredth GARCH variant, and
    ordering the shortlist by confidence alone put exactly those at the top.
    """
    if not os.path.exists(APPEAL):
        return {}
    with open(APPEAL, encoding="utf-8") as fh:
        return json.load(fh)


def load() -> list[dict[str, Any]]:
    """Every keep, joined, classified and scored, best first."""
    with open(LEDGER, encoding="utf-8") as fh:
        judged = json.load(fh)["papers"]
    with open(PAPERS, encoding="utf-8") as fh:
        index = json.load(fh)
    rows = index if isinstance(index, list) else index.get("papers", [])
    meta = {norm(p.get("arxiv_id")): p for p in rows}
    done = built()
    scored = appeal_scores()

    out = []
    for key, entry in judged.items():
        if entry.get("verdict") != "keep":
            continue
        ident = norm(key)
        paper = meta.get(ident, {})
        text = " ".join([paper.get("title") or "", entry.get("method") or "",
                         paper.get("abstract") or ""])
        area, task = taxonomy.classify(text)
        tier, why = effort(entry)
        out.append({
            "id": ident,
            "title": (paper.get("title") or ident).strip(),
            "abstract": paper.get("abstract") or entry.get("method") or "",
            "authors": paper.get("authors") or "",
            "url": paper.get("url") or f"https://arxiv.org/abs/{ident}",
            "pdf": paper.get("pdf"),
            "thumb": paper.get("thumb"),
            "published": (paper.get("published") or "")[:10],
            "citations": paper.get("citations") or 0,
            "percentile": paper.get("percentile") or 0,
            "influential": paper.get("influential") or 0,
            "source": paper.get("source") or "arxiv",
            "area": area,
            "task": task,
            "tags": taxonomy.tags_for(text),
            "tier": tier,
            "tier_why": why,
            "confidence": entry.get("confidence") or 0,
            "method": entry.get("method") or "",
            "reason": entry.get("reason") or "",
            "data_needed": entry.get("data_needed") or [],
            "targets": entry.get("reproducible_targets") or [],
            "digits": numeracy(entry),
            "state": "replicated" if ident in done else "queued",
            **{k: (scored.get(ident) or {}).get(k, 0)
               for k in ("appeal", "tradeable", "evidence", "interest", "buildability")},
            "one_liner": (scored.get(ident) or {}).get("one_liner", ""),
        })

    # Worth reading first, then how sure we are it reproduces, then how cheap.
    # Effort used to lead, which surfaced trivial papers over interesting ones.
    order = {"S": 0, "M": 1, "L": 2}
    out.sort(key=lambda k: (-k["appeal"], -k["confidence"], order[k["tier"]]))
    return out


def stats(papers: list[dict[str, Any]]) -> dict[str, Any]:
    with open(LEDGER, encoding="utf-8") as fh:
        judged = json.load(fh)["papers"]
    return {
        "shortlisted": len(papers),
        "judged": len(judged),
        "replicated": sum(1 for p in papers if p["state"] == "replicated"),
        "tiers": {t: sum(1 for p in papers if p["tier"] == t) for t in "SML"},
        "targets": sum(len(p["targets"]) for p in papers),
    }
