"""Draw every exhibit we can, then score each drawing against the printed page.

This is the loop the replication is driven by: render, measure, adjust, render
again. The score is written to `data/parity/<paper>.json` so a change that
makes a drawing worse shows up as a fall rather than as an opinion.

    uv run python tools/render_exhibits.py 2606.04153
    uv run python tools/render_exhibits.py 2606.04153 --exhibit T6
"""

from __future__ import annotations

import argparse
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from alpha_archive.replications import decomp2026_exhibits as ex  # noqa: E402
from tools import visual_parity  # noqa: E402

PAPER_FIGS = os.path.join(ROOT, "notebooks", "paper_figures")
OUT = os.path.join(ROOT, "notebooks", "rebuilt_figures")


def index(paper: str) -> dict[str, dict]:
    """Caption, notes and printed proportions, per exhibit, from the cropper."""
    with open(os.path.join(PAPER_FIGS, "index.json"), encoding="utf-8") as fh:
        payload = json.load(fh)
    out = {}
    for e in payload["exhibits"]:
        text = e["caption"]
        out[e["exhibit"]] = {
            # Strip the "Table 6: " the drawing prints for itself.
            "caption": text.split(":", 1)[1].strip() if ":" in text else text,
            "notes": e.get("notes", ""),
            "aspect": float(e.get("aspect") or 0.0),
        }
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("paper")
    ap.add_argument("--exhibit", default="")
    args = ap.parse_args()

    meta = index(args.paper)
    # Geometry measured off the printed pages by tools/layout_probe.py, so the
    # redraw is placed on the page rather than beside it.
    layout_path = os.path.join(PAPER_FIGS, "layout.json")
    layouts = {}
    if os.path.exists(layout_path):
        with open(layout_path, encoding="utf-8") as fh:
            layouts = json.load(fh)
    targets = [args.exhibit] if args.exhibit else sorted(meta)

    drawn = []
    for exhibit in targets:
        out_png = os.path.join(OUT, f"{exhibit}.png")
        spec = meta.get(exhibit, {})
        made = False
        if exhibit.startswith("F"):
            made = ex.render_k_figure(args.paper, exhibit, out_png,
                                      caption=spec.get("caption", ""),
                                      aspect=spec.get("aspect", 0.0))
        else:
            made = ex.render_table(args.paper, exhibit, out_png,
                                   caption=spec.get("caption", ""),
                                   notes=spec.get("notes", ""),
                                   aspect=spec.get("aspect", 0.0),
                                   layout=layouts.get(exhibit))
        if made:
            drawn.append(exhibit)
        elif os.path.exists(out_png):
            os.remove(out_png)

    print(f"drew {len(drawn)} of {len(targets)}: {', '.join(drawn)}")

    results = visual_parity.run(args.paper, args.exhibit)
    scored = {k: v for k, v in results.items() if v.get("score") is not None}
    for exhibit, r in sorted(results.items()):
        if r.get("score") is None:
            print(f"  {exhibit:5}     —   {r['reason']}")
        else:
            print(f"  {exhibit:5} {r['score']:6.2f}   ink {r['ink']:5.1f}  "
                  f"profile {r['profile']:5.1f}")
    if scored:
        mean = sum(r["score"] for r in scored.values()) / len(scored)
        print(f"mean parity over {len(scored)} drawn: {mean:.2f}")

    os.makedirs(os.path.join(ROOT, "data", "parity"), exist_ok=True)
    with open(os.path.join(ROOT, "data", "parity", f"{args.paper}.json"),
              "w", encoding="utf-8", newline="\n") as fh:
        json.dump(results, fh, indent=1)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
