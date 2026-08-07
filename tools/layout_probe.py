"""Measure a printed exhibit's geometry so the redraw can be placed on it.

Guessing where the columns go does not work. A table drawn with evenly spaced
columns and no gutters between the k-groups lands its numbers on the page's
whitespace and its whitespace on the page's numbers, which scores as
anti-correlated however right the numbers are. The way out is not to guess
harder: it is to read the positions off the crop and draw to them.

What comes back, all in fractions of the image so the caller can scale freely:

    rules     horizontal rules -- the \\toprule, \\midrule and \\bottomrule
              lines. Nearly every row of a rule is ink, which no line of type
              ever is, so they separate cleanly on coverage alone.
    columns   centres of the numeric columns, found as peaks in the column ink
              profile to the right of the row-label block.
    label_w   where the row labels stop and the first number starts.
    baselines centres of the text rows between the rules.

    uv run python tools/layout_probe.py 2606.04153 --exhibit T6
"""

from __future__ import annotations

import argparse
import json
import os

import numpy as np
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAPER = os.path.join(ROOT, "notebooks", "paper_figures")

INK = 200
RULE_COVERAGE = 0.55    # a row this dark across its width is a rule, not type
GAP = 0.06              # a column gutter must be this quiet to split groups


def _ink(path: str) -> np.ndarray:
    img = Image.open(path).convert("L")
    a = np.asarray(img, dtype=np.float32)
    return np.clip((INK - a) / INK, 0.0, 1.0)


def _runs(mask: np.ndarray) -> list[tuple[int, int]]:
    """Contiguous True spans, as (start, end_exclusive)."""
    out, start = [], None
    for i, on in enumerate(mask):
        if on and start is None:
            start = i
        elif not on and start is not None:
            out.append((start, i))
            start = None
    if start is not None:
        out.append((start, len(mask)))
    return out


def probe(path: str) -> dict:
    a = _ink(path)
    h, w = a.shape

    # Rules: rows whose ink spans most of the width.
    coverage = (a > 0.35).mean(axis=1)
    rules = [((s + e) / 2) / h for s, e in _runs(coverage > RULE_COVERAGE)]

    # Body: between the first and last rule is where the numbers live.
    if len(rules) >= 2:
        top, bottom = int(rules[0] * h) + 2, int(rules[-1] * h) - 2
    else:
        top, bottom = 0, h
    body = a[max(0, top):max(top + 1, bottom)]

    profile = body.sum(axis=0)
    if profile.max() > 0:
        profile = profile / profile.max()

    # The row-label block is the run of ink that starts at the left margin;
    # the first quiet gutter after it is where the numbers begin.
    quiet = profile < GAP
    label_w = 0.0
    for s, e in _runs(quiet):
        if s > 0.04 * w and (e - s) > 0.012 * w:
            label_w = s / w
            break

    # Numeric columns: ink runs to the right of the labels. A number is not one
    # run -- the space between "104" and ".63", or between two digits, breaks it
    # into several. Runs separated by less than a real gutter are therefore
    # merged back together, with the gutter width taken from the gaps actually
    # present rather than from a constant.
    right = quiet.copy()
    right[:int(label_w * w)] = True
    spans = [(s, e) for s, e in _runs(~right) if (e - s) > 0.003 * w]
    if len(spans) > 2:
        gaps = sorted(spans[i + 1][0] - spans[i][1] for i in range(len(spans) - 1))
        # The gutter between columns is wide; the breaks inside a number are
        # narrow. The median gap sits among the narrow ones, so twice it
        # separates the two populations without a magic pixel count.
        threshold = max(2.0, 2.0 * gaps[len(gaps) // 2])
        merged = [list(spans[0])]
        for s, e in spans[1:]:
            if s - merged[-1][1] <= threshold:
                merged[-1][1] = e
            else:
                merged.append([s, e])
        spans = [(s, e) for s, e in merged]
    columns = [((s + e) / 2) / w for s, e in spans]

    # Text baselines: ink runs down the page inside the body, rules excluded.
    rows = body.sum(axis=1)
    rows = rows / max(1e-6, rows.max())
    baselines = [((s + e) / 2 + max(0, top)) / h
                 for s, e in _runs(rows > 0.08) if (e - s) > 0.002 * h]

    return {"rules": [round(r, 5) for r in rules],
            "columns": [round(c, 5) for c in columns],
            "label_w": round(label_w, 5),
            "baselines": [round(b, 5) for b in baselines],
            "aspect": round(h / w, 5)}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("paper")
    ap.add_argument("--exhibit", default="")
    args = ap.parse_args()

    with open(os.path.join(PAPER, "index.json"), encoding="utf-8") as fh:
        exhibits = [e["exhibit"] for e in json.load(fh)["exhibits"]]
    if args.exhibit:
        exhibits = [e for e in exhibits if e == args.exhibit]

    out = {}
    for exhibit in exhibits:
        path = os.path.join(PAPER, f"{exhibit}.png")
        if not os.path.exists(path):
            continue
        out[exhibit] = probe(path)
        print(f"  {exhibit:5} rules {len(out[exhibit]['rules']):2}  "
              f"columns {len(out[exhibit]['columns']):2}  "
              f"rows {len(out[exhibit]['baselines']):3}  "
              f"label_w {out[exhibit]['label_w']:.3f}")

    dest = os.path.join(PAPER, "layout.json")
    with open(dest, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(out, fh, indent=1)
    print(f"{len(out)} probed -> {dest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
