"""Score a computed grid against the paper's printed one, cell by cell.

A replication module hands over a flat mapping of the paper's own cell addresses
to the values it computed:

    {"T6/CSM approach/Baseline/k =3/TW": 122.33, ...}

This compares each one against what the page prints, applies the tolerance
declared for that kind of number, and writes data/artifacts/<paper>.json. The
builder never decides what counts as a match and never decides the denominator,
which are the two places the last version of this went wrong.

    uv run python tools/score_replication.py 2606.04153 --from results.json

TOLERANCES ARE DECLARED HERE AND FROZEN. They were written before any model in
this repository produced a number for these tables, and they are set at half of
the last printed digit: the bar for "this is the number on the page", not a bar
tuned until the result cleared it. Widening one to rescue a miss is the exact
failure CONTRIBUTING.md was written about. Record the miss instead.
"""

from __future__ import annotations

import argparse
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

CHECKLISTS = os.path.join(ROOT, "data", "checklists")
ARTIFACTS = os.path.join(ROOT, "data", "artifacts")

# Half of the last printed digit, per kind of number. Keyed on the metric name
# that ends the cell address.
TOLERANCE = {
    "TW": 0.005,            # terminal wealth, printed to 2dp
    "AV": 0.005,            # annualised return, percent, 2dp
    "SD": 0.005,            # annualised sd, percent, 2dp
    "SR": 0.005,            # Sharpe ratio, 2dp
    "MDD": 0.005,           # maximum drawdown, 2dp
    "MSE": 0.0005,          # mean squared error, 3dp
    "MCS p-value": 0.0005,  # 3dp
}
DEFAULT_TOLERANCE = 0.0005  # correlations, R2, CER: all printed to 3dp

REPRODUCED, MISSED, NOT_ATTEMPTED = "REPRODUCED", "MISSED", "NOT_ATTEMPTED"

# What produced the numbers being scored. The artifact carries these through to
# the site, so a stale entry here puts the wrong file under "here is the code"
# on a public page, which is the one caption that has to be true.
NOTEBOOKS = {
    "2606.04153": "notebooks/2606.04153_sign_and_magnitude.ipynb",
}
MODULES = {
    "2606.04153": "alpha_archive/replications/decomp2026_eval.py",
}


def tolerance_for(cell_id: str) -> float:
    """The bar this cell has to clear, from the metric its address ends in."""
    tail = cell_id.rsplit("/", 1)[-1]
    return TOLERANCE.get(tail, DEFAULT_TOLERANCE)


def load_checklist(paper: str) -> dict:
    import glob
    hits = (glob.glob(os.path.join(CHECKLISTS, f"{paper}.json"))
            or glob.glob(os.path.join(CHECKLISTS, f"{paper}v*.json")))
    if not hits:
        sys.exit(f"no checklist for {paper}: run tools/extract_artifacts.py first")
    with open(hits[0], encoding="utf-8") as fh:
        return json.load(fh)


def _key(cell_id: str) -> str:
    """An address reduced to what a typesetter cannot change.

    Table 4 heads its columns "k = 1" and Table 6 heads them "k =1". Both come
    off the page verbatim, and neither is worth making a replication track, so
    addresses are matched with the spaces taken out.
    """
    return "".join(cell_id.split()).lower()


def score(paper: str, computed: dict[str, float],
          notes: dict[str, str] | None = None) -> dict:
    checklist = load_checklist(paper)
    cells = {c["id"]: c for e in checklist["exhibits"] for c in e["cells"]}
    by_key = {_key(k): k for k in cells}
    computed = {by_key.get(_key(k), k): v for k, v in computed.items()}
    notes = {by_key.get(_key(k), k): v for k, v in (notes or {}).items()}

    unknown = sorted(k for k in computed if k not in cells)
    if unknown:
        # A computed value with no home on the page is either a typo in the
        # address or a number the paper does not print. Either way it must not
        # be scored, because a match against nothing is not a match.
        print(f"{len(unknown)} computed cells are not printed in the paper:",
              file=sys.stderr)
        for u in unknown[:10]:
            print(f"  {u}", file=sys.stderr)

    artifacts = []
    for cid, cell in cells.items():
        published = cell["value"]
        tol = tolerance_for(cid)
        if cid not in computed or computed[cid] is None:
            artifacts.append({
                "name": cid, "cell": cid, "published": published,
                "observed": None, "tolerance": tol,
                "where": cid.split("/")[0], "gap": None,
                "state": NOT_ATTEMPTED, "note": notes.get(cid, ""), "blocker": "",
            })
            continue
        observed = float(computed[cid])
        gap = abs(observed - published)
        artifacts.append({
            "name": cid, "cell": cid, "published": published,
            "observed": round(observed, 6), "tolerance": tol,
            "where": cid.split("/")[0], "gap": round(gap, 6),
            "state": REPRODUCED if gap <= tol else MISSED,
            "note": notes.get(cid, ""), "blocker": "",
        })

    tally = {s: sum(1 for a in artifacts if a["state"] == s)
             for s in (REPRODUCED, MISSED, NOT_ATTEMPTED, "UNOBTAINABLE")}
    total = len(artifacts)
    checked = tally[REPRODUCED] + tally[MISSED]
    return {
        "paper": paper,
        "title": "A new decomposition approach to modeling financial returns",
        "headline": (f"{tally[REPRODUCED]} of {total:,} printed numbers reproduced, "
                     f"{tally[MISSED]} missed, {tally[NOT_ATTEMPTED]:,} not built"),
        "fully_reproduced": tally[REPRODUCED] == total and total > 0,
        "checked": checked,
        "tally": tally,
        "notebook": NOTEBOOKS.get(paper, ""),
        "code": MODULES.get(paper, ""),
        "artifacts": artifacts,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("paper")
    ap.add_argument("--from", dest="src", required=True,
                    help="JSON file of {cell_id: value}")
    args = ap.parse_args()

    with open(args.src, encoding="utf-8") as fh:
        payload = json.load(fh)
    computed = payload.get("computed", payload)
    notes = payload.get("notes", {})

    result = score(args.paper, computed, notes)
    os.makedirs(ARTIFACTS, exist_ok=True)
    out = os.path.join(ARTIFACTS, f"{args.paper}.json")
    with open(out, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(result, fh, indent=1, ensure_ascii=False)
    print(result["headline"], "->", out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
