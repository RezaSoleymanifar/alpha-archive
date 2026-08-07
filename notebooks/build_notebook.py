"""Generate the walkthrough notebook for arXiv 2606.04153.

The notebook is written here rather than by hand so its prose and its code stay
in one file, and so a rerun cannot leave stale output beside edited text.

What it has to do, in order of importance:

Carry every exhibit, not a selection. The paper prints twenty-three of them,
fifteen tables and eight figures, and an earlier version of this notebook showed
four. Four is a highlight reel: the reader cannot tell whether the other
nineteen were skipped because they agreed or because they did not. So every
exhibit gets a cell, including the ones we could not build, and the ones that
disagree are the point rather than an embarrassment.

Put the page beside the rebuild. Each cell shows the exhibit as the paper
printed it on the left, the same cells recomputed on the right, and the function
that produced them underneath. A number without its code is a claim.

Never round toward agreement. Every state on this page was decided by
`tools/score_replication.py` against tolerances frozen before any of these
models produced a value, and this file only displays that verdict.

Dollar signs are written as `\\$` throughout. Jupyter hands `$100 ... $182` to
MathJax and renders `100becomes182`, which turned the headline claim into
gibberish in the previous build.

    uv run python notebooks/build_notebook.py
    uv run python notebooks/build_notebook.py --execute
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "notebooks", "2606.04153_sign_and_magnitude.ipynb")
FIGURES = os.path.join(ROOT, "notebooks", "paper_figures")
ARTIFACT = os.path.join(ROOT, "data", "artifacts", "2606.04153.json")


def md(*lines: str) -> dict:
    return {"cell_type": "markdown", "metadata": {}, "source": "\n".join(lines)}


def code(*lines: str) -> dict:
    return {"cell_type": "code", "metadata": {}, "execution_count": None,
            "outputs": [], "source": "\n".join(lines)}


# What each exhibit is, and which function in the replication produced our side
# of it. An exhibit with no function is one we did not build, and the reason is
# printed in the notebook rather than left as a blank row.
# Which function produced our side of each exhibit. There is deliberately no
# description column here: the caption printed under every heading is read out
# of the PDF by `tools/crop_exhibits.py`. An earlier version of this file
# carried hand-written summaries, six of which described a different exhibit
# than the image beneath them, and those summaries were then used to justify
# not building the exhibit. Never describe an exhibit from memory.
CODE_FOR = {
    "T1": ("decomp2026_eval", "correlations"),
    "T3": ("decomp2026_eval", "r2_oos"),
    "T4": ("decomp2026_eval", "mcs_pvalues"),
    "T5": ("decomp2026_eval", "mcs_pvalues"),
    "T6": ("decomp2026_eval", "switching"),
    "T7": ("decomp2026_eval", "cer_mean_variance"),
    "T8": ("decomp2026_eval", "cer_crra"),
    "TB1": ("decomp2026_eval", "switching"),
    "TB2": ("decomp2026_eval", "cer_mean_variance"),
    "TB3": ("decomp2026_eval", "cer_crra"),
    "TC1": ("decomp2026_eval", "crisis_tables"),
    "TD1": ("decomp2026_eval", "full_set_table"),
}


def exhibits_from_pdf() -> list[dict]:
    """The exhibit list and captions, as the cropper read them off the PDF."""
    path = os.path.join(FIGURES, "index.json")
    if not os.path.exists(path):
        sys.exit("no notebooks/paper_figures/index.json: run tools/crop_exhibits.py")
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)["exhibits"]


# Why an exhibit has no rebuilt column. Silence here would read as an oversight;
# each of these is a decision with a reason that survives being written down.
NOT_BUILT = {
    "T2": "A grid of asterisks marking which predictors each model selected at "
          "each k. Our own selections are printed below it, but the checklist "
          "harvested no numeric cells from the page, so there is nothing to "
          "score against.",
    "TA1": "As Table 2, for MSE-based selection rather than AUC.",
    "TA2": "This prints out-of-sample R-squared by model, loss and k, which is "
           "what Table 3 prints, and the two disagree: the linear model at "
           "k = 1 under squared loss is -0.24 in Table 3 and -0.88 here. "
           "Neither caption says what changed between them, so there is no "
           "way to know which one a replication should be scored against. "
           "Recorded rather than guessed.",
    "F1": "A plot of Table 3's R-squared values against k. Every point in it "
          "is a cell scored above, so the figure carries no number of its own.",
    "F2": "A wealth-growth plot. Its endpoints are Table 6's terminal wealth, "
          "scored above; the path between them is never printed as numbers.",
    "F3": "As Figure 2, across the copula and benchmark strategies.",
    "F4": "A plot of terminal wealth against k. Every point is a cell of "
          "Table 6 or B1, both scored above.",
    "FA1": "As Figure 1, for MSE-based selection.",
    "FC1": "The crisis wealth paths, whose endpoints are Table C1's terminal "
           "wealth.",
    "FC2": "As Figure C1, for the COVID window.",
    "FD1": "The nine-predictor wealth paths, whose endpoints are Table D1's.",
}


HELPERS = [
    "import base64, io, json, os",
    "import pandas as pd",
    "from IPython.display import HTML, display",
    "",
    "ROOT = os.path.dirname(os.getcwd()) if os.path.basename(os.getcwd()) == 'notebooks' else os.getcwd()",
    "FIGURES = os.path.join(ROOT, 'notebooks', 'paper_figures')",
    "",
    "with open(os.path.join(ROOT, 'data', 'artifacts', '2606.04153.json'), encoding='utf-8') as fh:",
    "    ARTIFACT = json.load(fh)",
    "",
    "CELLS = ARTIFACT['artifacts']",
    "print(f\"{len(CELLS):,} scored cells loaded\")",
]

RENDERER = [
    "def _b64(path):",
    "    with open(path, 'rb') as fh:",
    "        return base64.b64encode(fh.read()).decode()",
    "",
    "",
    "def cells_for(exhibit):",
    "    \"\"\"Every scored cell belonging to one exhibit, in page order.\"\"\"",
    "    return [c for c in CELLS if c['cell'].split('/')[0] == exhibit]",
    "",
    "",
    "def rebuilt(exhibit):",
    "    \"\"\"The exhibit as a frame: what the page prints, what we computed.\"\"\"",
    "    rows = []",
    "    for c in cells_for(exhibit):",
    "        addr = c['cell'].split('/')",
    "        rows.append({",
    "            'row': ', '.join(p for p in addr[1:-1] if p),",
    "            'metric': addr[-1],",
    "            'printed': c['published'],",
    "            'ours': c['observed'],",
    "            'gap': c['gap'],",
    "            'state': {'REPRODUCED': 'match', 'MISSED': 'differs'}",
    "                     .get(c['state'], 'not built'),",
    "        })",
    "    return pd.DataFrame(rows)",
    "",
    "",
    "def _style(frame):",
    "    \"\"\"Green where we matched the page, red where we did not.\"\"\"",
    "    def paint(s):",
    "        return ['color:#0a7d3c;font-weight:600' if v == 'match'",
    "                else 'color:#b04040;font-weight:600' if v == 'differs'",
    "                else 'color:#999' for v in s]",
    "    return (frame.style.apply(paint, subset=['state'])",
    "            .format({'printed': '{:g}', 'ours': '{:g}', 'gap': '{:g}'},",
    "                    na_rep='—')",
    "            .hide(axis='index').to_html())",
    "",
    "",
    "def show(exhibit, rows=14, note=''):",
    "    \"\"\"The paper's exhibit and ours, side by side, in one output.\"\"\"",
    "    frame = rebuilt(exhibit)",
    "    attempted = frame[frame['state'] != 'not built'] if len(frame) else frame",
    "    body = attempted if len(attempted) else frame",
    "    table = _style(body.head(rows)) if len(body) else (",
    "        f'<p style=\"color:#777;font-size:12px\">{note or \"not built\"}</p>')",
    "    tail = ''",
    "    if len(body) > rows:",
    "        tail = (f'<p style=\"color:#777;font-size:11px\">showing {rows} of '",
    "                f'{len(body):,} cells; the rest are in the artifact file.</p>')",
    "    if len(frame):",
    "        n_match = int((frame['state'] == 'match').sum())",
    "        n_diff = int((frame['state'] == 'differs').sum())",
    "        tail += (f'<p style=\"color:#777;font-size:11px\">{exhibit}: '",
    "                 f'{n_match:,} matched, {n_diff:,} differ, '",
    "                 f'{len(frame) - n_match - n_diff:,} not built.</p>')",
    "",
    "    path = os.path.join(FIGURES, f'{exhibit}.png')",
    "    left = (f'<img src=\"data:image/png;base64,{_b64(path)}\" '",
    "            f'style=\"width:100%;border:1px solid #e5e7eb;border-radius:4px\">'",
    "            if os.path.exists(path) else '<p>no page image</p>')",
    "    cap = ('font:600 11px/1.5 -apple-system,system-ui,sans-serif;'",
    "           'letter-spacing:.08em;text-transform:uppercase;color:#6b7280;'",
    "           'padding-bottom:6px')",
    "    box = 'flex:1;min-width:0'",
    "    display(HTML(",
    "        f'<div style=\"display:flex;gap:20px;align-items:flex-start;'",
    "        f'max-width:1180px\">'",
    "        f'<div style=\"{box}\"><div style=\"{cap}\">as the paper printed it</div>'",
    "        f'{left}</div>'",
    "        f'<div style=\"{box}\"><div style=\"{cap}\">rebuilt from free data</div>'",
    "        f'<div style=\"overflow-x:auto;font-size:12px\">{table}</div>{tail}</div>'",
    "        f'</div>'))",
    "",
    "",
    "def source(module, symbol):",
    "    \"\"\"The function that produced the right-hand column, as it is on disk.\"\"\"",
    "    import ast",
    "    path = os.path.join(ROOT, 'alpha_archive', 'replications', module + '.py')",
    "    with open(path, encoding='utf-8') as fh:",
    "        text = fh.read()",
    "    for node in ast.parse(text).body:",
    "        if getattr(node, 'name', None) == symbol:",
    "            from IPython.display import Code",
    "            return Code(ast.get_source_segment(text, node), language='python')",
    "    return None",
]


def exhibit_cells() -> list[dict]:
    """One markdown heading and one code cell per exhibit, all twenty-three."""
    out: list[dict] = []
    for entry in exhibits_from_pdf():
        exhibit = entry["exhibit"]
        module, symbol = CODE_FOR.get(exhibit, ("", ""))
        # The heading is the exhibit's number; the lede is the paper's caption,
        # verbatim, so the words above the image always match the image.
        lines = [f"### {entry['label']}", "", f"*{entry['caption']}*"]
        if exhibit in NOT_BUILT:
            lines += ["", f"**No rebuilt column.** {NOT_BUILT[exhibit]}"]
        out.append(md(*lines))
        if module and symbol:
            out.append(code(f"show({exhibit!r})", "",
                            f"source({module!r}, {symbol!r})"))
        else:
            note = NOT_BUILT.get(exhibit, "no printed numbers to reproduce")
            out.append(code(f"show({exhibit!r}, note={note!r})"))
    return out


def tally_cell() -> list[dict]:
    return [
        md("## The count, without a thumb on it",
           "",
           "Every cell above was scored against a tolerance set at half of the "
           "paper's last printed digit, written down before any model here "
           "produced a number. The totals below are that scoring, summed."),
        code("summary = (pd.DataFrame(CELLS)",
             "           .assign(exhibit=lambda d: d['cell'].str.split('/').str[0])",
             "           .pivot_table(index='exhibit', columns='state',",
             "                        values='cell', aggfunc='count', fill_value=0))",
             "summary['checked'] = summary.get('REPRODUCED', 0) + summary.get('MISSED', 0)",
             "# .where keeps the divisor float, so an exhibit we never checked",
             "# becomes NaN rather than pd.NA, which has no __round__.",
             "summary['rate %'] = (100 * summary.get('REPRODUCED', 0)",
             "                     / summary['checked'].where(summary['checked'] > 0)).round(0)",
             "summary.sort_values('checked', ascending=False)"),
        code("t = ARTIFACT['tally']",
             "checked = t['REPRODUCED'] + t['MISSED']",
             "print(f\"printed        {len(CELLS):>6,}\")",
             "print(f\"rebuilt        {checked:>6,}\")",
             "print(f\"matched        {t['REPRODUCED']:>6,}\")",
             "print(f\"missed         {t['MISSED']:>6,}\")",
             "print(f\"not built      {t['NOT_ATTEMPTED']:>6,}\")",
             "print(f\"match rate     {100*t['REPRODUCED']/checked:>5.0f}%  of what we checked\")"),
    ]


def build() -> dict:
    cells = [
        md("# Does the sign of a return tell you more than the return?",
           "",
           "**Paper:** *A new decomposition approach to modeling financial "
           "returns*, arXiv [2606.04153](https://arxiv.org/abs/2606.04153).",
           "",
           "The claim, in one line: forecasting **whether** the S&P 500 goes up "
           "next month, conditioned on **how big** the move is, beats "
           "forecasting the return itself. Over 1981 to 2021, after costs, "
           "\\$100 becomes **\\$182** instead of the **\\$105** you get from "
           "buy-and-hold.",
           "",
           "This notebook carries **every exhibit in the paper**: fifteen "
           "tables and eight figures. Each one appears as the paper printed it, "
           "beside the same cells recomputed from data anyone can download, "
           "with the function that produced them underneath.",
           "",
           "Where we disagree with the page, the cell says so in red. Nothing "
           "here was tuned until it agreed."),

        md("## How to read every cell below",
           "",
           "Left is the exhibit lifted straight out of the paper's PDF. Right "
           "is our rebuild, one row per printed number:",
           "",
           "| column | meaning |",
           "|---|---|",
           "| `printed` | the number on the page |",
           "| `ours` | what the replication computed |",
           "| `gap` | the absolute difference |",
           "| `state` | `match` inside tolerance, `differs` outside it |",
           "",
           "The tolerance is half of the last digit the paper printed, frozen "
           "in `tools/score_replication.py` before any of this ran."),

        code(*HELPERS),
        code(*RENDERER),

        md("## First, prove the pipeline",
           "",
           "The paper splits its sample at 400 observations of 887, counting "
           "from February 1948. If the data does not rebuild to exactly those "
           "counts, nothing downstream is worth reading, so it is checked "
           "before anything is modelled."),
        code("import sys",
             "sys.path.insert(0, ROOT)",
             "from alpha_archive.replications.decomp2026_paper import load, WINDOW",
             "",
             "frame = load()",
             "print(f'{len(frame):,} observations, "
             "{frame.index[0]:%Y-%m} to {frame.index[-1]:%Y-%m}  (paper: 887)')",
             "print(f'in-sample {WINDOW}, out-of-sample {len(frame) - WINDOW}"
             "  (paper: 400 and 487)')"),

        md("## The exhibits",
           "",
           "Twenty-three of them, in the order the paper prints them."),
    ]
    cells += exhibit_cells()
    cells += tally_cell()

    return {
        "cells": cells,
        "metadata": {
            "kernelspec": {"display_name": "Python 3", "language": "python",
                           "name": "python3"},
            "language_info": {"name": "python", "version": "3.11"},
        },
        "nbformat": 4,
        "nbformat_minor": 5,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--execute", action="store_true",
                    help="run the notebook and keep its outputs")
    args = ap.parse_args()

    if not os.path.exists(ARTIFACT):
        sys.exit("no scored artifact: run tools/score_replication.py first")

    nb = build()
    with open(OUT, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(nb, fh, indent=1, ensure_ascii=False)
    n_code = sum(1 for c in nb["cells"] if c["cell_type"] == "code")
    print(f"{len(nb['cells'])} cells ({n_code} code) -> {OUT}")

    if args.execute:
        cmd = [sys.executable, "-m", "jupyter", "nbconvert", "--to", "notebook",
               "--execute", "--inplace", "--ExecutePreprocessor.timeout=1800",
               OUT]
        result = subprocess.run(cmd, cwd=ROOT)
        if result.returncode:
            return result.returncode
        print(f"executed -> {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
