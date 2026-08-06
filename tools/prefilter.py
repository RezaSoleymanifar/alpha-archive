"""Cheap abstract screen, so a full PDF read is spent only where it can pay.

A third of the drops in the ledger were never data problems. Eighteen were pure
theory and fifteen were simulation studies with no empirical claim to reproduce
at all, and both usually announce themselves in the abstract. Reading their PDFs
bought nothing.

This screens on the abstract alone and is measured against the 100 papers the
PDF triage already judged, which is the only reason to trust it. The bar is
stated before the run and is deliberately lopsided:

    A paper the PDF read called `keep` must never be screened out.

Recall on keeps is the number that matters. Precision is a bonus, a theory
paper that survives to the PDF stage costs one read, while a keep that is
screened out is a paper lost from the archive with nobody ever noticing. Those
two errors are not worth the same, so the thresholds are not symmetric.

RESULT, measured 2026-08-06 against all 100 labelled papers: it fails.

    keeps preserved     22/24    recall 92%
    PDF reads saved     10/76    13%

It loses "Iterative detection of global factors near the BBP phase transition",
which validates on real returns after its simulations, and "Anchored Geodesic
Analysis for Multivariate Extremes", which proves a theorem and then applies it
to real tail data. Both are exactly the kind of paper the archive wants.

The trade is bad on its own terms. Scaled to the remaining papers it saves
roughly a hundred reads and loses roughly nineteen reproducible papers, and the
keeps are the entire product. Tuning the patterns until they clear the bar on
these same hundred labels would be fitting to the answer key, which is the thing
this repository exists to refuse.

So the screen is kept and not used. `--apply` queues every unjudged paper for a
full read regardless, and this file stands as the record of why that cost is
being paid on purpose rather than through never having checked.

    uv run python tools/prefilter.py --evaluate   # score against the labelled 100
    uv run python tools/prefilter.py --apply      # queue every unjudged paper
"""

from __future__ import annotations

import argparse
import io
import json
import os
import re
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAPERS = os.path.join(ROOT, "data", "papers", "papers.json")
LEDGER = os.path.join(ROOT, "data", "triage", "ledger.json")
QUEUE = os.path.join(ROOT, "data", "triage", "queue.json")

# Marks of a paper with nothing empirical to reproduce. Each is a phrase that
# describes the *contribution*, not merely a technique mentioned in passing.
THEORY = re.compile(r"""
    we \s+ prove | \bproof\s+of\b | \btheorem\b | \blemma\b | \bcorollary\b
  | closed[- ]form \s+ (solution|expression) | existence \s+ and \s+ uniqueness
  | viscosity \s+ solution | Hamilton[- ]Jacobi | \bHJB\b
  | stochastic \s+ control \s+ problem | verification \s+ theorem
  | asymptotic \s+ expansion | we \s+ derive \s+ (a|an|the) \s+ (closed|explicit|analytic)
  | \bwell[- ]posedness\b | martingale \s+ representation
""", re.I | re.X)

SYNTHETIC = re.compile(r"""
    synthetic \s+ (data|market|price|series) | simulated \s+ (data|market|series)
  | Monte \s+ Carlo \s+ (study|experiments?|simulations?)
  | agent[- ]based \s+ (model|simulation) | \bABM\b
  | numerical \s+ (experiments?|illustrations?) \s+ (show|demonstrate|confirm)
  | simulation \s+ study
""", re.I | re.X)

# Marks of real data actually touched. Any one of these overrides the screens
# above, because a theorem proved *and* tested on real prices is reproducible.
EMPIRICAL = re.compile(r"""
    \bbacktest\w* | out[- ]of[- ]sample | \bS&P\s*500\b | \bNASDAQ\b | \bCRSP\b
  | \bDow\s+Jones\b | \bRussell\b | \bSTOXX\b | \bFTSE\b | \bNikkei\b
  | daily \s+ (returns?|closes?|prices?) | historical \s+ (data|prices?|returns?)
  | real[- ]world \s+ data | empirical(ly)? \s+ (test|evaluat|validat|analys|studi|examin)
  | using \s+ data \s+ from | data \s+ (spanning|covering|from) \s+ \d{4}
  | \b(19|20)\d{2}\s*(to|-| none |through)\s*(19|20)\d{2}\b
  | cross[- ]section \s+ of \s+ (stock|equity|asset) | \bWRDS\b
  | Fama[- ]French | \bCompustat\b | Yahoo \s+ Finance | \bETFs?\b
""", re.I | re.X)


def screen(title: str, abstract: str) -> tuple[str, str]:
    """Return (verdict, why). `read` means spend a PDF read on it."""
    text = f"{title}\n{abstract}"

    if EMPIRICAL.search(text):
        return "read", "names real data or an out-of-sample test"

    theory = THEORY.search(text)
    synth = SYNTHETIC.search(text)
    if theory and synth:
        return "skip", f"theory and simulation only ({theory.group(0).strip()[:28]})"
    if theory:
        return "skip", f"analytical contribution only ({theory.group(0).strip()[:28]})"
    if synth:
        return "skip", f"simulation only ({synth.group(0).strip()[:28]})"

    # Says nothing either way. A PDF read is exactly how that gets resolved.
    return "read", "abstract is not explicit, resolve by reading"


def norm(arxiv_id: str | None) -> str:
    """Drop the version suffix.

    The ledger stores `2607.06502` and the index stores `2607.06502v1`. Joining
    on the raw strings matched 9 papers out of 100 and reported a confident 100%
    recall on three of them, which is how a broken join passes for a result.
    """
    return re.sub(r"v\d+$", "", (arxiv_id or "").strip())


def load_papers() -> list[dict]:
    with open(PAPERS, encoding="utf-8") as fh:
        data = json.load(fh)
    return data if isinstance(data, list) else data.get("papers", [])


def load_ledger() -> dict:
    if not os.path.exists(LEDGER):
        return {}
    with open(LEDGER, encoding="utf-8") as fh:
        return json.load(fh).get("papers", {})


def evaluate() -> bool:
    """Score the screen against every paper the PDF read already judged."""
    ledger = load_ledger()
    by_id = {norm(p.get("arxiv_id")): p for p in load_papers()}

    kept_lost, kept_ok, dropped_saved, dropped_cost = [], 0, 0, 0
    unmatched = 0
    for key, judged in ledger.items():
        paper = by_id.get(norm(key))
        if not paper:
            unmatched += 1
            continue
        verdict, why = screen(paper.get("title", ""), paper.get("abstract", ""))
        if judged["verdict"] == "keep":
            if verdict == "skip":
                kept_lost.append((paper.get("title", "")[:66], why))
            else:
                kept_ok += 1
        else:
            dropped_saved += verdict == "skip"
            dropped_cost += verdict == "read"

    total_keeps = kept_ok + len(kept_lost)
    recall = kept_ok / total_keeps if total_keeps else 0.0
    print(f"labelled papers matched : {kept_ok + len(kept_lost) + dropped_saved + dropped_cost}"
          f"  (unmatched {unmatched})")
    print(f"keeps preserved         : {kept_ok}/{total_keeps}   recall {recall:.0%}")
    print(f"drops screened out      : {dropped_saved}/{dropped_saved + dropped_cost}"
          f"   PDF reads saved {dropped_saved}")
    if kept_lost:
        print()
        print("KEEPS THE SCREEN WOULD HAVE LOST. The screen is not safe to apply:")
        for title, why in kept_lost:
            print(f"  - {title}  [{why}]")
    print()
    passed = recall == 1.0
    print("VERDICT:", "safe to apply" if passed else "NOT safe, do not apply")
    return passed


def apply() -> None:
    ledger = load_ledger()
    papers = load_papers()
    judged = {norm(k) for k in ledger}
    pending = [p for p in papers if norm(p.get("arxiv_id")) not in judged]

    queue, skipped = [], []
    for paper in pending:
        _, why = screen(paper.get("title", ""), paper.get("abstract", ""))
        # The screen's verdict is recorded and deliberately not acted on, see
        # the measured result at the top of this file.
        record = {
            "arxiv_id": paper.get("arxiv_id"),
            "title": paper.get("title"),
            "url": paper.get("url"),
            "pdf": paper.get("pdf"),
            "published": paper.get("published"),
            "abstract": paper.get("abstract"),
            "screen_why": why,
        }
        queue.append(record)

    with open(QUEUE, "w", encoding="utf-8", newline="\n") as fh:
        json.dump({"queue": queue, "screened_out": skipped}, fh, indent=1)

    print(f"already judged  : {len(ledger)}")
    print(f"pending         : {len(pending)}")
    print(f"  -> PDF read   : {len(queue)}")
    print(f"  -> screened   : {len(skipped)}")
    print(f"wrote {QUEUE}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--evaluate", action="store_true")
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    if args.evaluate or not args.apply:
        ok = evaluate()
        if not args.apply:
            raise SystemExit(0 if ok else 1)
        if not ok:
            print("Screen failed its bar, so every paper is queued for a read.")
            print()
    apply()


if __name__ == "__main__":
    main()
