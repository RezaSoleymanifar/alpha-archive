"""Redraw the paper's exhibits from our own numbers, in the paper's own layout.

A table of matched values proves the arithmetic. Redrawing the exhibit proves
the exhibit: same rows in the same order, same column groups, same rules, same
series on the same axes, with our numbers in the cells instead of theirs. Put
the two side by side and the reader checks the replication by looking rather
than by trusting a state column.

The layout is not invented here. It is read out of the checklist that
`tools/extract_artifacts.py` harvested off the PDF: the order rows first
appear is the order the page prints them, the column address carries its own
grouping, and the indent structure is in the cell address. So this file draws
what the page says it is, and if the page changes the drawing follows.

On fidelity, plainly: the paper is typeset in LaTeX. matplotlib ships the real
Computer Modern face (`cmr10`), which is the same family, so the type is close
but the engine's kerning and hinting are not TeX's. Parity is therefore
measured rather than asserted -- see `tools/visual_parity.py`.

    uv run python tools/render_exhibits.py 2606.04153
"""

from __future__ import annotations

import glob
import json
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CHECKLISTS = os.path.join(ROOT, "data", "checklists")
ARTIFACTS = os.path.join(ROOT, "data", "artifacts")

# The paper's face. matplotlib carries Computer Modern for mathtext, which is
# the same family the document is set in, so using it here removes the single
# largest source of visual disagreement that is not about content.
SERIF = ["cmr10", "DejaVu Serif"]

DPI = 200
FONT = 9.0
RULE = 1.1          # \toprule and \bottomrule weight
THIN = 0.6          # \cmidrule weight

# How many column groups sit in one stacked block. The paper breaks wide tables
# into halves rather than shrinking the type, and these are the break points it
# chose, read off the crops.
BLOCKS = {
    "T3": 4, "T4": 2, "T5": 2, "T6": 2, "T7": 4, "T8": 4,
    "TA2": 4, "TB1": 2, "TB2": 4, "TB3": 4, "TC1": 2, "TD1": 7,
    "T1": 9, "T2": 9, "TA1": 9,
}


def _checklist(paper: str) -> dict:
    hits = (glob.glob(os.path.join(CHECKLISTS, f"{paper}.json"))
            or glob.glob(os.path.join(CHECKLISTS, f"{paper}v*.json")))
    with open(hits[0], encoding="utf-8") as fh:
        return json.load(fh)


def _observed(paper: str) -> dict[str, float | None]:
    """Our value for every cell address, or None where we did not build it."""
    path = os.path.join(ARTIFACTS, f"{paper}.json")
    if not os.path.exists(path):
        return {}
    with open(path, encoding="utf-8") as fh:
        return {a["cell"]: a["observed"] for a in json.load(fh)["artifacts"]}


def _decimals(raw: str) -> int:
    return len(raw.split(".")[1]) if "." in str(raw) else 0


def table_spec(paper: str, exhibit: str) -> dict | None:
    """Rows, columns and printed formatting for one table, in page order."""
    cells = [c for e in _checklist(paper).get("exhibits", [])
             for c in (e.get("cells") or [])
             if c["id"].split("/")[0] == exhibit]
    if not cells:
        return None

    rows: list[tuple[str, ...]] = []
    cols: list[tuple[str, ...]] = []
    panels: list[str] = []
    by_cell: dict[tuple, dict] = {}

    for c in cells:
        parts = c["id"].split("/")[1:]
        panel = c.get("panel") or ""
        # The column address is whatever the checklist called `col`; everything
        # before it in the id, minus the panel, is the row's own path.
        col = tuple(str(c["col"]).split("/"))
        row = tuple(p for p in parts[:len(parts) - len(col)] if p and p != panel)
        if panel and panel not in panels:
            panels.append(panel)
        key = (panel, row)
        if key not in [(p, r) for p, r in rows]:
            rows.append((panel, row))
        if col not in cols:
            cols.append(col)
        by_cell[(panel, row, col)] = c

    return {"exhibit": exhibit, "rows": rows, "cols": cols,
            "panels": panels or [""], "cells": by_cell,
            "caption": ""}


def _tidy(label: str) -> str:
    """"k =1" back to "k = 1".

    The checklist keeps column headings exactly as the PDF's text layer emitted
    them, spacing artefacts and all. That is right for matching addresses and
    wrong for redrawing the page, which set them with the spaces.
    """
    return label.replace("k =", "k = ").replace("k =  ", "k = ")


def _fmt(value, raw: str) -> str:
    if value is None:
        return ""
    return f"{value:.{_decimals(raw)}f}"


def _wrap(text: str, chars: int) -> list[str]:
    """Greedy wrap, because the notes paragraph is justified prose on the page."""
    words, lines, current = text.split(), [], ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if len(candidate) > chars and current:
            lines.append(current)
            current = word
        else:
            current = candidate
    if current:
        lines.append(current)
    return lines


def render_table(paper: str, exhibit: str, out_png: str,
                 caption: str = "", notes: str = "",
                 aspect: float = 0.0, layout: dict | None = None) -> bool:
    """Draw one table as the paper lays it out, with our numbers in it."""
    spec = table_spec(paper, exhibit)
    if not spec:
        return False
    observed = _observed(paper)

    cols, rows = spec["cols"], spec["rows"]
    # Column groups: the leading part of the address, when there is one.
    groups: list[str] = []
    for col in cols:
        head = col[0] if len(col) > 1 else ""
        if head not in groups:
            groups.append(head)
    per_block = max(1, BLOCKS.get(exhibit, 4))
    blocks = [groups[i:i + per_block] for i in range(0, len(groups), per_block)]

    # Geometry. The content decides the proportions, then the whole drawing is
    # scaled so its aspect ratio matches the crop it will sit beside. Without
    # that, a correct table drawn half as tall lands every row between the
    # page's rows and scores as though the content were wrong.
    cols_in_block = max(
        sum(1 for c in cols if (c[0] if len(c) > 1 else "") in b) for b in blocks)
    line_h = 0.175

    note_lines = _wrap(notes, max(60, int(7.2 * cols_in_block))) if notes else []

    # Group labels ("Copula-based approach") each take a line of their own and
    # are not rows. Leaving them out of the budget made the canvas too short,
    # and the drawing ran off the bottom edge -- which reads as a table with
    # missing rows and scores as one.
    group_lines = 0
    for panel in spec["panels"]:
        seen = set()
        for row_panel, row in rows:
            if row_panel == panel and len(row) > 1 and row[0] not in seen:
                seen.add(row[0])
                group_lines += 1

    height = 0.0
    for _ in blocks:
        height += line_h * (3.4 + len(rows) + group_lines
                            + 1.4 * len(spec["panels"]))
    height += line_h * 3.0                             # title
    height += line_h * (1.0 + 1.05 * len(note_lines))  # notes

    width = 2.35 + 0.62 * cols_in_block
    if aspect and aspect > 0:
        width = height / aspect

    # Geometry measured off the printed page, when the probe found the same
    # number of columns the checklist says the block has. Placing our numbers
    # on the page's own column centres is the difference between a table that
    # overlays the original and one that lands in its gutters.
    probed = (layout or {}).get("columns") or []
    label_w = width * ((layout or {}).get("label_w") or 0.26)
    if len(probed) == cols_in_block:
        centres = [width * c for c in probed]
        cell_w = (centres[-1] - centres[0]) / max(1, cols_in_block - 1)
    else:
        cell_w = (width - label_w) / max(1, cols_in_block)
        centres = [label_w + cell_w * (i + 0.5) for i in range(cols_in_block)]

    fig = plt.figure(figsize=(width, height), dpi=DPI)
    fig.patch.set_facecolor("white")
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, width)
    ax.set_ylim(0, height)
    ax.axis("off")

    def text(x, y, s, *, size=FONT, ha="left", style="normal", weight="normal"):
        ax.text(x, y, s, fontsize=size, ha=ha, va="baseline",
                family=SERIF, style=style, weight=weight)

    def rule(y, x0, x1, lw=RULE):
        ax.plot([x0, x1], [y, y], lw=lw, color="black", solid_capstyle="butt")

    y = height - line_h * 1.6
    label = exhibit_title(exhibit)
    text(width / 2, y, f"{label}: {caption}" if caption else label,
         ha="center", size=FONT + 0.6)
    y -= line_h * 2.0

    for block in blocks:
        block_cols = [c for c in cols if (c[0] if len(c) > 1 else "") in block]
        xs = {c: (centres[i] if i < len(centres)
                  else label_w + cell_w * (i + 0.5))
              for i, c in enumerate(block_cols)}

        rule(y, 0, width)
        y -= line_h * 1.15

        # Group header, centred over its own columns, with a rule beneath.
        if any(len(c) > 1 for c in block_cols):
            for name in block:
                members = [c for c in block_cols if c[0] == name]
                if not members:
                    continue
                left = xs[members[0]] - cell_w / 2
                right = xs[members[-1]] + cell_w / 2
                text((left + right) / 2, y, _tidy(name), ha="center")
                rule(y - line_h * 0.35, left + 0.05, right - 0.05, lw=THIN)
            y -= line_h * 1.35

        for c in block_cols:
            text(xs[c], y, _tidy(c[-1]), ha="center")
        y -= line_h * 0.5
        rule(y, 0, width)
        y -= line_h * 1.15

        for panel in spec["panels"]:
            if panel:
                text(0.04, y, panel, style="italic")
                y -= line_h * 1.15
            seen_groups: set[str] = set()
            for prow_panel, row in rows:
                if prow_panel != panel:
                    continue
                # A row path of more than one part is an indented member of a
                # group, and the group's own label is printed once above it.
                if len(row) > 1 and row[0] not in seen_groups:
                    seen_groups.add(row[0])
                    text(0.04, y, row[0])
                    y -= line_h
                indent = 0.22 if len(row) > 1 else 0.04
                text(indent, y, row[-1])
                for c in block_cols:
                    cell = spec["cells"].get((panel, row, c))
                    if cell is None:
                        continue
                    text(xs[c], y, _fmt(observed.get(cell["id"]), cell["raw"]),
                         ha="center")
                y -= line_h
            y -= line_h * 0.25
        rule(y + line_h * 0.55, 0, width)
        y -= line_h * 1.1

    # The notes paragraph, which the page sets in smaller italic-led prose and
    # which is a large enough block of ink to move the parity score on its own.
    if note_lines:
        y -= line_h * 0.6
        for i, line in enumerate(note_lines):
            if i == 0:
                text(0.02, y, "Notes:", size=FONT - 1.2, style="italic")
                text(0.02 + 0.42, y, line[len("Notes:"):].strip(),
                     size=FONT - 1.2)
            else:
                text(0.02, y, line, size=FONT - 1.2)
            y -= line_h * 1.05

    os.makedirs(os.path.dirname(out_png), exist_ok=True)
    fig.savefig(out_png, dpi=DPI, facecolor="white")
    plt.close(fig)
    return True


# The figures the paper draws over k, and which cells they plot. Both read
# their series straight out of the scored artifact, so a figure cannot drift
# away from the table it summarises: they are the same numbers.
K_FIGURES = {
    "F1": {
        "source": "T3",
        "panels": [("(a) Squared errors", "Squared"),
                   ("(b) Absolute errors", "Absolute")],
        "ylabel": "",
    },
    "F4": {
        "source": ("T6", "TB1"),
        "panels": [("", "TW")],
        "ylabel": "",
    },
}

# The paper's own series, with its line styles. Read off the legends in the
# crops rather than chosen: matching the drawing means matching these.
SERIES_STYLE = {
    "CSM approach/Baseline": ("CSM (Baseline)", "#1a1af5", "-", "*"),
    "Copula-based approach/Clayton": ("Clayton", "#e60000", ":", "o"),
    "GARCH-M model": ("GARCH-M", "#c86464", ":", "D"),
    "CSR approach": ("CSR", "#0a8a0a", "-.", "^"),
    "Linear model": ("Linear", "#000000", "-.", "s"),
    "Copula-based approach/Gaussian": ("Gaussian", "#8a3ffc", "--", "v"),
    "Copula-based approach/FGM": ("FGM", "#d17b00", "--", "P"),
    "CSM approach/Poly": ("Poly", "#00a0a0", "-", "X"),
}


def _series_over_k(observed: dict, sources, row: str, metric: str
                   ) -> tuple[list[int], list[float]]:
    """One model's value at each k, taken from whichever table prints that k."""
    sources = (sources,) if isinstance(sources, str) else sources
    ks, values = [], []
    for k in range(1, 9):
        for table in sources:
            for spacing in (f"k = {k}", f"k ={k}"):
                key = f"{table}/{row}/{spacing}/{metric}"
                if key in observed and observed[key] is not None:
                    ks.append(k)
                    values.append(float(observed[key]))
                    break
            else:
                continue
            break
    return ks, values


def render_k_figure(paper: str, exhibit: str, out_png: str,
                    caption: str = "", aspect: float = 0.0) -> bool:
    """A figure the paper plots against k, redrawn from our own cells."""
    spec = K_FIGURES.get(exhibit)
    if not spec:
        return False
    observed = _observed(paper)

    panels = spec["panels"]
    width = 6.4
    height = width * (aspect if aspect else 0.72)
    fig, axes = plt.subplots(1, len(panels), figsize=(width, height), dpi=DPI,
                             squeeze=False)
    fig.patch.set_facecolor("white")

    drew_any = False
    for ax, (title, metric) in zip(axes[0], panels):
        for row, (label, colour, style, marker) in SERIES_STYLE.items():
            ks, values = _series_over_k(observed, spec["source"], row, metric)
            if len(ks) < 2:
                continue
            drew_any = True
            ax.plot(ks, values, color=colour, linestyle=style, marker=marker,
                    markersize=3.4, linewidth=1.0, label=label)
        ax.set_xlabel("Number of predictors (k)", fontsize=7, family=SERIF)
        if title:
            ax.set_title(title, fontsize=8, family=SERIF)
        ax.tick_params(labelsize=6.5)
        for tick in ax.get_xticklabels() + ax.get_yticklabels():
            tick.set_fontfamily(SERIF)
        ax.grid(True, color="#dddddd", linewidth=0.5)
        ax.set_facecolor("white")
        for spine in ax.spines.values():
            spine.set_linewidth(0.6)
        ax.legend(fontsize=5.6, frameon=False, loc="best",
                  prop={"family": SERIF, "size": 5.6})

    if not drew_any:
        plt.close(fig)
        return False

    fig.suptitle(f"{exhibit_title(exhibit)}: {caption}" if caption
                 else exhibit_title(exhibit),
                 fontsize=8.5, family=SERIF, y=0.99)
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    os.makedirs(os.path.dirname(out_png), exist_ok=True)
    fig.savefig(out_png, dpi=DPI, facecolor="white")
    plt.close(fig)
    return True


def exhibit_title(exhibit: str) -> str:
    kind = "Figure" if exhibit.startswith("F") else "Table"
    body = exhibit[1:]
    return f"{kind} {body}"
