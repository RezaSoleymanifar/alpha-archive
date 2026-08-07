"""The side-by-side, assembled from the scored record rather than from a story.

A replication is convincing at the moment a reader sees the paper's own printed
exhibit and our rebuilt version of it in the same frame, with the code that made
ours in reach. That is what this file assembles, one block per exhibit:

    left    the exhibit as the paper printed it, the page image itself
    right   the same cells recomputed, each beside the printed value and its gap
    below   the function that produced them, read out of the module

Nothing here decides what counts as a match. The states come from
`data/artifacts/<paper>.json`, which `tools/score_replication.py` wrote against
tolerances frozen before any of these numbers existed. This file only arranges
what that scoring already concluded, which is why it cannot flatter a result.

    uv run python tools/build_evidence.py 2606.04153
"""

from __future__ import annotations

import argparse
import ast
import json
import os
import re
import shutil
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

ARTIFACTS = os.path.join(ROOT, "data", "artifacts")
EVIDENCE = os.path.join(ROOT, "data", "evidence")
DOCS_EVIDENCE = os.path.join(ROOT, "docs", "evidence")

# Where a paper's printed exhibits were cropped to, and which function in the
# replication rebuilt each one. Both halves are needed: an image without the
# code is a claim, and code without the image is a listing.
FIGURES = os.path.join(ROOT, "notebooks", "paper_figures")

# What each exhibit is, and which function produced our side of it. The images
# and the exhibit list come from `tools/crop_exhibits.py`, which reads them off
# the PDF, so this file only has to say what a reader could not see for
# themselves. An exhibit missing from here still gets a block; it simply has no
# code caption under it.
# NOT descriptions. The caption shown under every block is the one the paper
# printed, read out of the PDF by `tools/crop_exhibits.py`. An earlier version
# of this file carried hand-written summaries and six of them described a
# different exhibit than the image beneath: Table 2 was called "descriptive
# statistics" when it is subset selection, Figure 1 was called an illustration
# when it is a headline result. Those summaries then justified not building
# them. Never describe an exhibit from memory; read its caption.
CODE_FOR = {
    "T1": ("decomp2026_eval.py", "correlations"),
    "T3": ("decomp2026_eval.py", "r2_oos"),
    "T4": ("decomp2026_eval.py", "mcs_pvalues"),
    "T5": ("decomp2026_eval.py", "mcs_pvalues"),
    "T6": ("decomp2026_eval.py", "switching"),
    "T7": ("decomp2026_eval.py", "cer_mean_variance"),
    "T8": ("decomp2026_eval.py", "cer_crra"),
    "TB1": ("decomp2026_eval.py", "switching"),
    "TB2": ("decomp2026_eval.py", "cer_mean_variance"),
    "TB3": ("decomp2026_eval.py", "cer_crra"),
    "TC1": ("decomp2026_eval.py", "crisis_tables"),
    "TD1": ("decomp2026_eval.py", "full_set_table"),
}

MODULE_DIR = "alpha_archive/replications/"

# Why an exhibit has no right-hand column. A blank cell reads as an oversight;
# these are decisions, and each one names what stopped us.
NOT_SCORED = {
    "T2": "A grid of asterisks marking which predictors each model selected at "
          "each k. Our selections are computed and printed in the notebook, but "
          "the checklist harvested no numeric cells from it, so there is "
          "nothing here to score against.",
    "TA1": "As Table 2, for MSE-based selection rather than AUC.",
    "TA2": "This prints out-of-sample R-squared by model, loss and k, which is "
           "what Table 3 prints, and the two disagree: the linear model at "
           "k = 1 under squared loss is -0.24 in Table 3 and -0.88 here. "
           "Neither caption says what changed, so there is no way to know "
           "which one a replication should be scored against.",
    "F1": "A plot of the Table 3 R-squared values against k. Every point in it "
          "is a cell scored above, so the figure carries no number of its own.",
    "F2": "A wealth-growth plot. The endpoints are Table 6's terminal wealth, "
          "scored above; the path between them is not printed as numbers.",
    "F3": "As Figure 2, across the copula and benchmark strategies.",
    "F4": "A plot of terminal wealth against k. Every point is a cell of "
          "Table 6 or B1, both scored above.",
    "FA1": "As Figure 1, for MSE-based selection.",
    "FC1": "The crisis wealth paths, whose endpoints are Table C1's terminal "
           "wealth.",
    "FC2": "As Figure C1, for the COVID window.",
    "FD1": "The nine-predictor wealth paths, whose endpoints are Table D1's.",
}


def declared_exhibits(paper: str) -> dict[str, dict]:
    """Every exhibit the cropper found in the PDF, in the order it found them."""
    index = os.path.join(FIGURES, "index.json")
    if not os.path.exists(index):
        sys.exit("no notebooks/paper_figures/index.json: run tools/crop_exhibits.py")
    with open(index, encoding="utf-8") as fh:
        payload = json.load(fh)
    if payload.get("paper") != paper:
        sys.exit(f"paper_figures/index.json holds {payload.get('paper')}, not {paper}")

    out: dict[str, dict] = {}
    for entry in payload["exhibits"]:
        key = entry["exhibit"]
        module, symbol = CODE_FOR.get(key, ("", ""))
        out[key] = {
            # "Table 6" heads the block; the paper's own caption is the lede.
            "label": entry.get("label") or key,
            "image": entry["image"],
            "caption": entry["caption"],
            "module": (MODULE_DIR + module) if module else "",
            "symbol": symbol,
        }
    return out

# How many rows one block shows before it stops. A block is an argument, not a
# data dump; the full grid is in the artifact file and is linked from the page.
MAX_ROWS = 16


def load_artifact(paper: str) -> dict:
    path = os.path.join(ARTIFACTS, f"{paper}.json")
    if not os.path.exists(path):
        sys.exit(f"no scored artifact for {paper}: run tools/score_replication.py")
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def read_symbol(module_rel: str, symbol: str) -> str:
    """The source of one function, lifted from the module by parsing it.

    Line numbers in a comment go stale the first time somebody edits above
    them; the AST does not, so the page can never show the wrong function
    under the right name.
    """
    path = os.path.join(ROOT, module_rel)
    try:
        with open(path, encoding="utf-8") as fh:
            source = fh.read()
    except OSError:
        return ""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return ""
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) \
                and node.name == symbol:
            return ast.get_source_segment(source, node) or ""
    return ""


def _row_and_metric(cell_id: str) -> tuple[str, str]:
    """Split a cell address into something a reader can scan.

    "T6/Buy and hold/k =1/TW" -> ("Buy and hold, k =1", "TW"). The exhibit
    prefix is already the block's title, so it is dropped rather than repeated
    on every line.
    """
    parts = cell_id.split("/")
    if len(parts) < 2:
        return cell_id, ""
    metric = parts[-1]
    middle = [p for p in parts[1:-1] if p]
    return ", ".join(middle) or parts[0], metric


def _fmt(value: float | None, published: float) -> str:
    """Print an observed number to the same precision the paper printed."""
    if value is None:
        return "—"
    text = f"{published!r}"
    decimals = len(text.split(".")[1]) if "." in text else 0
    return f"{value:.{decimals}f}"


def block_for(exhibit: str, spec: dict, artifact: dict, paper: str) -> dict | None:
    cells = [a for a in artifact["artifacts"]
             if a["cell"].split("/")[0] == exhibit]

    # Attempted cells first: a block whose visible rows are all "not built" is
    # a picture of an empty promise. Within each group the page order is kept.
    attempted = [c for c in cells if c["observed"] is not None]
    shown = (attempted or cells)[:MAX_ROWS]

    rows = []
    for c in shown:
        label, metric = _row_and_metric(c["cell"])
        rows.append({
            "row": label,
            "metric": metric,
            "printed": c["published"],
            "ours": _fmt(c["observed"], c["published"]),
            "gap": ("—" if c["gap"] is None else _fmt(c["gap"], c["published"])),
            "state": c["state"],
        })

    tally = {}
    for c in cells:
        tally[c["state"]] = tally.get(c["state"], 0) + 1

    image = ""
    src = os.path.join(FIGURES, spec["image"])
    if os.path.exists(src):
        os.makedirs(os.path.join(DOCS_EVIDENCE, paper), exist_ok=True)
        shutil.copyfile(src, os.path.join(DOCS_EVIDENCE, paper, spec["image"]))
        image = f"evidence/{paper}/{spec['image']}"

    return {
        "exhibit": exhibit,
        "label": spec["label"],
        "caption": spec["caption"],
        "image": image,
        "module": spec["module"],
        "symbol": spec["symbol"],
        "code": read_symbol(spec["module"], spec["symbol"]),
        "columns": ["row", "metric", "printed", "ours", "gap"],
        "rows": rows,
        "no_numbers": NOT_SCORED.get(exhibit, "") if not rows else "",
        "cells": len(cells),
        "shown": len(shown),
        "tally": tally,
    }


def build(paper: str) -> dict:
    artifact = load_artifact(paper)
    blocks = []
    for exhibit, spec in declared_exhibits(paper).items():
        block = block_for(exhibit, spec, artifact, paper)
        if block:
            blocks.append(block)
    return {"paper": paper, "blocks": blocks}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("paper", nargs="?", help="paper id; omitted builds every declared one")
    args = ap.parse_args()

    papers = [args.paper] if args.paper else ["2606.04153"]
    os.makedirs(EVIDENCE, exist_ok=True)
    for paper in papers:
        payload = build(paper)
        out = os.path.join(EVIDENCE, f"{paper}.json")
        with open(out, "w", encoding="utf-8", newline="\n") as fh:
            json.dump(payload, fh, indent=1, ensure_ascii=False)
        rows = sum(len(b["rows"]) for b in payload["blocks"])
        print(f"{paper}: {len(payload['blocks'])} blocks, {rows} rows -> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
