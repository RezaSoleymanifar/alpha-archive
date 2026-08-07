"""Score a rebuilt exhibit against the paper's own printed one, pixel by pixel.

A table of matching numbers proves the computation. It does not prove that the
exhibit was rebuilt, because a reader still has to take our word for the layout,
the ordering, the rules, the series and the axes. Redrawing the exhibit in code
and then measuring the redraw against the page closes that gap: the comparison
is arithmetic, not judgement, and it is reported whether or not it flatters us.

What is and is not achievable, said once and honestly. The paper is typeset in
LaTeX with Computer Modern; matplotlib does not have that font file, so a
byte-identical match is impossible and any tool claiming one is measuring
something else. What *is* achievable, and what this file measures, is
structural parity:

    ink        where the page is dark, are we dark, and vice versa. This is
               the layout: same rows in the same places, same column positions,
               same rules, same curve through the same points.
    profile    column and row ink densities, compared as correlations. Catches
               a table that has the right cells in the wrong order, or a chart
               whose series is scaled differently.
    score      the two combined, as a percentage, so a run can be driven up
               and a regression shows as a fall.

Type antialiasing and stroke weight put a ceiling under 100 that no correct
drawing can pass. The score is therefore read as a distance to close, not as a
grade, and the diff image is what says where the remaining distance is.

    uv run python tools/visual_parity.py 2606.04153 --exhibit T6
"""

from __future__ import annotations

import argparse
import json
import os
import sys

import numpy as np
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAPER = os.path.join(ROOT, "notebooks", "paper_figures")
OURS = os.path.join(ROOT, "notebooks", "rebuilt_figures")
DIFFS = os.path.join(ROOT, "data", "parity")

# Everything is compared at one width. The paper's crops come off the PDF at
# 200dpi and ours are drawn to whatever size suits the drawing, so a common
# canvas is the only way the two are comparable at all.
WIDTH = 900
HEIGHT = 1200
INK = 200          # below this grey level counts as ink
BLUR = 4           # boxcar radius, so a one-pixel typesetting shift is not a miss


def _load_raw(path: str) -> tuple[np.ndarray, float]:
    """Ink map on the common canvas, plus the aspect ratio it was drawn at.

    Both exhibits are normalised onto one canvas before anything is compared.
    An earlier version padded instead, which meant a drawing that was correct
    but a different shape had every row land on a blank part of the other and
    scored near zero -- it was measuring the page size, not the content. The
    shape is not thrown away: it comes back as its own term below, so a drawing
    with the wrong proportions is still penalised, just not catastrophically.
    """
    img = Image.open(path).convert("L")
    aspect = img.height / max(1, img.width)
    img = img.resize((WIDTH, HEIGHT), Image.LANCZOS)
    a = np.asarray(img, dtype=np.float32)
    return np.clip((INK - a) / INK, 0.0, 1.0), aspect


def _blur(a: np.ndarray, radius: int = BLUR) -> np.ndarray:
    """A cheap boxcar, so sub-pixel differences in glyph placement do not count."""
    if radius < 1:
        return a
    pad = np.pad(a, radius, mode="constant")
    cumulative = pad.cumsum(0).cumsum(1)
    cumulative = np.pad(cumulative, ((1, 0), (1, 0)), mode="constant")
    size = 2 * radius + 1
    h, w = a.shape
    total = (cumulative[size:size + h, size:size + w]
             - cumulative[0:h, size:size + w]
             - cumulative[size:size + h, 0:w]
             + cumulative[0:h, 0:w])
    return total / (size * size)


def _corr(x: np.ndarray, y: np.ndarray) -> float:
    if x.std() < 1e-9 or y.std() < 1e-9:
        return 0.0
    return float(np.clip(np.corrcoef(x, y)[0, 1], 0.0, 1.0))


def compare(paper_png: str, ours_png: str, out_png: str = "") -> dict:
    """The two exhibits, measured against each other."""
    a, aspect_a = _load_raw(paper_png)
    b, aspect_b = _load_raw(ours_png)
    fa, fb = _blur(a), _blur(b)

    # Ink agreement, as intersection over union on the softened maps. Union of
    # nothing is a perfect score for two blank pages, so it is guarded.
    inter = float(np.minimum(fa, fb).sum())
    union = float(np.maximum(fa, fb).sum())
    ink = inter / union if union > 1e-6 else 0.0

    # Where the ink sits, column by column and row by row.
    profile = 0.5 * (_corr(fa.sum(0), fb.sum(0)) + _corr(fa.sum(1), fb.sum(1)))

    # And the shape it was drawn at, so normalising onto one canvas above does
    # not quietly forgive a table twice as tall as the page's.
    shape = min(aspect_a, aspect_b) / max(aspect_a, aspect_b)

    score = 100.0 * (0.45 * ink + 0.4 * profile + 0.15 * shape)

    if out_png:
        os.makedirs(os.path.dirname(out_png), exist_ok=True)
        # Paper in red, ours in green, agreement in grey. Anything coloured is
        # a difference, and the colour says which side it came from.
        h, w = a.shape
        rgb = np.full((h, w, 3), 255, dtype=np.uint8)
        both = np.minimum(a, b)
        rgb[..., 0] = 255 - (255 * np.clip(b + both, 0, 1)).astype(np.uint8)
        rgb[..., 1] = 255 - (255 * np.clip(a + both, 0, 1)).astype(np.uint8)
        rgb[..., 2] = 255 - (255 * np.clip(both, 0, 1)).astype(np.uint8)
        Image.fromarray(rgb).save(out_png)

    return {"score": round(score, 2), "ink": round(100 * ink, 2),
            "profile": round(100 * profile, 2), "shape": round(100 * shape, 2),
            "diff": out_png}


def run(paper: str, only: str = "") -> dict:
    index = os.path.join(PAPER, "index.json")
    with open(index, encoding="utf-8") as fh:
        exhibits = [e["exhibit"] for e in json.load(fh)["exhibits"]]
    if only:
        exhibits = [e for e in exhibits if e == only]
        if not exhibits:
            sys.exit(f"{only} is not an exhibit of {paper}")

    results = {}
    for exhibit in exhibits:
        left = os.path.join(PAPER, f"{exhibit}.png")
        right = os.path.join(OURS, f"{exhibit}.png")
        if not os.path.exists(right):
            results[exhibit] = {"score": None, "reason": "not drawn yet"}
            continue
        results[exhibit] = compare(
            left, right, os.path.join(DIFFS, paper, f"{exhibit}.png"))
    return results


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("paper")
    ap.add_argument("--exhibit", default="", help="score just this one")
    args = ap.parse_args()

    results = run(args.paper, args.exhibit)
    drawn = {k: v for k, v in results.items() if v.get("score") is not None}
    for exhibit, r in results.items():
        if r.get("score") is None:
            print(f"  {exhibit:5}     —   {r['reason']}")
        else:
            print(f"  {exhibit:5} {r['score']:6.2f}   ink {r['ink']:5.1f}  "
                  f"profile {r['profile']:5.1f}")
    if drawn:
        mean = sum(r["score"] for r in drawn.values()) / len(drawn)
        print(f"{len(drawn)} of {len(results)} drawn, mean parity {mean:.2f}")

    out = os.path.join(DIFFS, f"{args.paper}.json")
    os.makedirs(DIFFS, exist_ok=True)
    with open(out, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(results, fh, indent=1)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
