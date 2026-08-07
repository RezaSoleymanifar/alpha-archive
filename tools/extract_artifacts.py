"""Harvest every number a paper prints, so the checklist is the paper's, not ours.

This exists because of a specific failure. The 2606.04153 replication reported
"7 of 12 published numbers reproduced". Twelve was not the paper's count, it was
ours: somebody read two tables and wrote down what they found there. The paper
prints 1,811 numbers across fifteen tables. Seven of 1,811 is a different claim
than seven of twelve, and only one of them is true.

The fix is to stop letting the builder choose the denominator. This script reads
the PDF and emits every number in every exhibit, addressed by where it sits:

    T6/k=3/CSM approach/Baseline/TW  ->  181.68

That address is stable across runs, so a replication can be scored cell by cell,
and coverage is arithmetic rather than a promise.

    uv run python tools/extract_artifacts.py data/cache/pdf/2606.04153v1.pdf
    uv run python tools/extract_artifacts.py --all

Two rules keep it honest:

  never drop silently   a line inside an exhibit that cannot be aligned to the
                        header is recorded in `unparsed`, not discarded. A
                        harvester that quietly skips what it cannot read
                        recreates the exact problem it was built to solve.
  never invent          no value is repaired, rounded or inferred. The raw token
                        is kept beside the parsed number so a disagreement is
                        always traceable to the page.

What this is not: OCR of a figure. Numbers plotted in a chart and never printed
as text are marked UNOBTAINABLE-by-extraction and left for a human, because
guessing a value off an axis is how a replication starts grading its own exam.
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import re
import sys

try:
    import pdfplumber
except ImportError:  # pragma: no cover - environment problem, not a logic one
    sys.exit("pdfplumber is required: uv add pdfplumber")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(ROOT, "data", "checklists")

# A caption opens an exhibit. Appendix exhibits carry a letter (Table B1), main
# text ones do not (Table 6), and both must be caught: the appendix is where
# robustness lives, which is exactly what a replication is tempted to skip.
CAPTION = re.compile(r"^[ \t]*(Table|Figure)\s+([A-Z]?\d+)\s*[:.]\s*(.*)$", re.M)

# A printed result. Requires a decimal point or a percent sign, which is what
# separates a finding from a year, a page number, an equation index or a
# citation. Stars ride along and are stripped into their own field.
CELL = re.compile(r"^\(?(-?)\$?(\d[\d,]*(?:\.\d+)?)\)?(%?)([*†‡]{0,3})$")

# Panel headers group columns: "k =1 k =2" over "TW AV SD SR MDD" twice.
PANEL_HINT = re.compile(r"[=×]|^Panel\b")

# A panel resets the shape of a table. Table 1 holds three of different widths.
PANEL_START = re.compile(r"^\s*(Panel\s+[A-Z][^:]*:.*)$")

# pdfplumber drops LaTeX subscripts onto their own line, so a correlation table
# emits "t t−1 t−1 t−1 ...". That is typography, not a header row, and letting
# it name columns renames every variable to its time index.
SUBSCRIPT_ONLY = re.compile(r"^\s*(t\s*(−|-)?\s*\d*\s*)+$")

# Everything after this is prose about the table, not the table.
NOTES = re.compile(r"^\s*(Notes?|Source)\s*[:.]", re.M)


def _clean(token: str) -> str:
    """Strip the typographic debris pdfplumber leaves on a numeric token."""
    return token.replace("−", "-").replace("–", "-").strip()


def _norm(text: str) -> str:
    """A line reduced to what both of pdfplumber's extractors agree on."""
    return "".join(_clean(text).split())


def parse_cell(token: str) -> dict | None:
    """A token to a value, or None if it is not a printed result.

    Parenthesised numbers are negative by accounting convention in some tables
    and standard errors in others. We record the parentheses rather than
    resolving them, because which one it means is a property of the table and
    the notes under it, not of the token.
    """
    raw = _clean(token)
    m = CELL.match(raw)
    if not m:
        return None
    sign, body, pct, stars = m.groups()
    if "." not in body and not pct:
        return None                       # a bare integer is a count, not a result
    value = float(body.replace(",", ""))
    if sign == "-":
        value = -value
    return {
        "value": value,
        "raw": raw,
        "percent": bool(pct),
        "stars": len(stars),
        "parenthesised": raw.startswith("("),
    }


def split_row(line: str) -> tuple[str, list[str]]:
    """A data row into its label and its numeric tokens.

    The label is everything before the first token that parses as a result.
    Row labels in these papers carry spaces ("Buy and hold", "CSR approach"),
    so splitting on whitespace and taking the first field loses half of them.
    """
    tokens = line.split()
    first = next((i for i, t in enumerate(tokens) if parse_cell(t)), None)
    if first is None:
        return line.strip(), []
    return " ".join(tokens[:first]).strip(), tokens[first:]


def page_geometry(page) -> dict[str, list[dict]]:
    """Every line on the page with the x-span of each word on it.

    Column headers cannot be resolved by counting tokens. "MSE MCS p-value"
    repeated four times is twelve tokens over eight columns, which divides
    into nothing, so a counting parser gives up and falls back to the row
    above, and every p-value ends up filed under the same name as the MSE
    beside it. Where a word sits on the page says which column it heads, and
    that works whether the name is one word or three.
    """
    lines: dict[float, list[dict]] = {}
    for w in page.extract_words(use_text_flow=False, keep_blank_chars=False):
        lines.setdefault(round(w["top"], 1), []).append(w)
    out: dict[str, list[dict]] = {}
    for top in sorted(lines):
        words = sorted(lines[top], key=lambda w: w["x0"])
        # Keyed without whitespace because the two extractors disagree about
        # it: a significance star comes back as "0.19*" from extract_text and
        # as "0.19", "*" from extract_words. Keyed on the raw string, every
        # starred row silently misses its own geometry.
        out.setdefault(_norm("".join(w["text"] for w in words)), words)
    return out


def header_groups(words: list[dict], gap: float = 4.0) -> list[tuple[str, float, float]]:
    """Adjacent header words merged into one name per column.

    "MCS p-value" is two words and one column; "TW AV" is two words and two
    columns. The space between them is what tells them apart, so the split is
    made on the gap rather than on the whitespace.
    """
    groups: list[tuple[str, float, float]] = []
    for w in words:
        if groups and w["x0"] - groups[-1][2] <= gap:
            name, x0, _ = groups[-1]
            groups[-1] = (f"{name} {w['text']}".strip(), x0, w["x1"])
        else:
            groups.append((w["text"], w["x0"], w["x1"]))
    return groups


def name_by_position(header_lines: list[str], centres: list[float],
                     geo: dict[str, list[dict]]) -> list[str] | None:
    """One name per column, chosen by which header sits over it."""
    stacked: list[list[str]] = []
    for text in header_lines:
        words = geo.get(_norm(text))
        if not words:
            return None
        groups = header_groups(words)
        if len(groups) < 2:
            continue
        row = []
        for c in centres:
            # The header over a column either contains its centre or is the
            # nearest one to it; a spanning header like "k = 1" sits over two
            # columns and is nearest to both.
            inside = [g for g in groups if g[1] - 1 <= c <= g[2] + 1]
            best = inside[0] if inside else min(
                groups, key=lambda g: abs((g[1] + g[2]) / 2 - c))
            row.append(best[0])
        stacked.append(row)
    if not stacked:
        return None
    # A spanning header repeated under itself adds nothing to the name.
    return ["/".join(dict.fromkeys(parts)) for parts in zip(*stacked)]


def column_names(header_lines: list[str], width: int) -> list[str]:
    """Build one name per column from however many header rows the table used.

    A table like Table 6 stacks two: a panel row (k =1, k =2) spanning groups,
    and a metric row (TW AV SD SR MDD) repeating inside each. The metric row
    sets the width; a shorter row above it that divides the width evenly is
    treated as a spanning group and repeated across its block. When a header
    cannot be made to fit, the column is named by its index rather than
    guessed at, and the caller can see that it was not resolved.
    """
    rows: list[list[str]] = []
    for line in header_lines:
        toks = re.findall(r"\S+(?:\s*=\s*\S+)?", line.replace("= ", "=")) or line.split()
        toks = [t.strip() for t in toks if t.strip()]
        if toks:
            rows.append(toks)
    if not rows:
        return [f"c{i + 1}" for i in range(width)]

    resolved: list[list[str]] = []
    for toks in rows:
        if len(toks) == width:
            resolved.append(toks)
        elif toks and width % len(toks) == 0:
            span = width // len(toks)
            resolved.append([t for t in toks for _ in range(span)])
        # a header row that fits neither is a caption fragment, not a header
    if not resolved:
        return [f"c{i + 1}" for i in range(width)]
    return ["/".join(parts) for parts in zip(*resolved)]


def segment(lines: list[str]) -> list[list[str]]:
    """Split a panel wherever it restarts its column headers.

    Table 6 does not print twenty columns across the page, it prints ten, then
    repeats the whole header for k = 3 and k = 7 underneath. Parsed as one
    block, the second half inherits the first half's names: 181.68 is filed
    under k = 1 alongside the real k = 1 value of 123.55, one of them silently
    overwrites the other, and the checklist quietly loses ten numbers while
    reporting the wrong value for ten more.
    """
    width = max((len(split_row(ln)[1]) for ln in lines), default=0)
    need = max(3, width // 2)

    out: list[list[str]] = [[]]
    seen_data = False
    for line in lines:
        _, nums = split_row(line)
        # A header restarts the block; a section label ("Momentum") does not.
        # The two are told apart by how wide they are: a header spans the table,
        # a section label names a group of rows in two or three words.
        header_like = not nums and ("=" in line or len(line.split()) >= need)
        if seen_data and header_like:
            out.append([])
            seen_data = False
        out[-1].append(line)
        seen_data = seen_data or bool(nums)
    return [s for s in out if s]


def column_centres(line: str, geo: dict[str, list[dict]], width: int) -> list[float]:
    """Where each column of a full-width data row actually sits on the page."""
    words = geo.get(_norm(line)) or []
    centres = [(w["x0"] + w["x1"]) / 2 for w in words if parse_cell(w["text"])]
    return centres if len(centres) == width else []


def harvest_panel(prefix: str, panel: str, page: int, lines: list[str],
                  geo: dict[str, list[dict]],
                  inherited: list[str]) -> tuple[list[dict], list[dict], list[str]]:
    """Every number in one block of one panel of one exhibit.

    Panels are parsed separately because they do not share a shape. Table 1
    stacks three: a 9-column row vector, a 10-column pair of rows, and an
    8-column triangular matrix. Measuring one width across all three makes two
    of them look broken and names every column in the third wrongly.
    """
    parsed = [split_row(ln) for ln in lines]
    width = max((len(nums) for _, nums in parsed), default=0)
    if not width:
        return [], [], []

    first_data = next(i for i, (_, n) in enumerate(parsed) if n)
    headers = [ln for ln in lines[:first_data] if not SUBSCRIPT_ONLY.match(ln)]
    # Table 7 prints its column header once, above Panel A, and the panels
    # underneath carry none of their own. Without inheriting it, every panel
    # names its columns after whatever row label happened to precede it.
    headers = (inherited + headers)[-3:]

    cols = []
    centre_line = next((ln for ln, (_, n) in zip(lines, parsed) if len(n) == width), "")
    centres = column_centres(centre_line, geo, width)
    if centres:
        cols = name_by_position(headers, centres, geo) or []
    if len(cols) != width:
        cols = column_names(headers, width)

    # A correlation matrix prints only its lower half, so each row is one token
    # shorter than the last and its first number is the diagonal. Read left to
    # right without noticing, and every value lands under the wrong variable.
    lengths = [len(n) for _, n in parsed if n]
    triangular = (len(lengths) >= 2
                  and all(b == a - 1 for a, b in zip(lengths, lengths[1:]))
                  and all(parse_cell(n[0])["value"] == 1.0 for _, n in parsed if n))

    def indent(line: str) -> float:
        words = geo.get(_norm(line))
        # Unknown indentation must not silently end a section; keep what we
        # know rather than inventing a boundary from a failed lookup.
        return words[0]["x0"] if words else section_x + 2.0

    cells, unparsed, rank = [], [], 0
    section, section_x = "", 0.0
    used_as_header = set(headers)
    for line, (label, nums) in zip(lines, parsed):
        if not nums:
            # A line already spent naming the columns is not also a section
            # label, or Table C1's rows all end up filed under "Global
            # Financial Crisis COVID-19 Crisis".
            if (label and len(label) > 1 and line not in used_as_header
                    and re.search(r"[A-Za-z]{2}", label)
                    and not PANEL_HINT.search(line) and len(label.split()) <= 6):
                section, section_x = label, indent(line)
            continue
        # A section ends where the indenting stops. "Momentum" heads three
        # indented rows and then "Linear model" starts back at the margin;
        # read as text alone there is nothing to say so, and the CSR approach
        # ends up filed as a kind of momentum.
        if section and indent(line) <= section_x + 1:
            section, section_x = "", 0.0
        offset = rank if triangular else 0
        rank += 1
        if not triangular and len(nums) != width:
            # Kept, not dropped. A short row is sometimes a genuine partial row
            # and sometimes a layout the parser misread; either way a human has
            # to see it rather than have it vanish from the denominator.
            unparsed.append({"panel": panel, "line": line.strip(),
                             "found": len(nums), "expected": width})
        for i, tok in enumerate(nums):
            cell = parse_cell(tok)
            if cell is None:
                continue
            j = i + offset
            col = cols[j] if j < len(cols) else f"c{j + 1}"
            addr = "/".join(p for p in (prefix, panel, section, label, col) if p)
            cells.append({"id": addr, "panel": panel, "section": section,
                          "row": label, "col": col, "page": page, **cell})
    return cells, unparsed, cols


def harvest_exhibit(kind: str, number: str, title: str, page: int,
                    block: str, geo: dict[str, list[dict]] | None = None) -> dict:
    """Every number in one exhibit, addressed by panel, row and column."""
    prefix = f"{kind[0]}{number}"
    geo = geo or {}
    body = NOTES.split(block)[0]
    lines = [ln for ln in body.split("\n")[1:] if ln.strip()]
    # A caption that wraps puts its tail on the next line ("...crisis peri-" /
    # "ods"). Left in place it becomes the first header row and names a column
    # "ods". A caption tail is short, lowercase and carries no numbers.
    if lines and not split_row(lines[0])[1] and len(lines[0].split()) <= 2 \
            and lines[0].strip()[:1].islower():
        lines = lines[1:]

    out = {
        "exhibit": f"{kind} {number}",
        "kind": kind.lower(),
        "page": page,
        "title": title.strip(),
        "columns": [],
        "cells": [],
        "unparsed": [],
        "needs_human": False,
        "why": "",
    }

    if kind == "Figure":
        # Axis ticks are not results. Harvesting "2.00 1.50 1.25 1.00" off a
        # wealth chart would pad the denominator with the y-axis, which is the
        # same dishonesty as choosing the denominator by hand. A value that a
        # paper only plots has to be read off the curve by a person, or matched
        # against the series the figure was drawn from.
        out.update(needs_human=True,
                   why="plotted, not printed: compare the rebuilt series to the "
                       "figure rather than reading values off the axis")
        return out

    # Panels reset the header and the shape. Everything before the first panel
    # marker is its own unnamed panel, which is the common single-panel case.
    marks = [i for i, ln in enumerate(lines) if PANEL_START.match(ln)]
    spans = []
    if not marks or marks[0] > 0:
        spans.append(("", lines[:marks[0]] if marks else lines))
    for a, start in enumerate(marks):
        end = marks[a + 1] if a + 1 < len(marks) else len(lines)
        name = PANEL_START.match(lines[start]).group(1).strip().rstrip(":")
        spans.append((name, lines[start + 1:end]))

    # Headers printed above the first panel belong to every panel below it.
    preamble = spans[0][1] if spans and spans[0][0] == "" else []
    shared = [ln for ln in preamble
              if not split_row(ln)[1] and not SUBSCRIPT_ONLY.match(ln)
              and ("=" in ln or len(ln.split()) >= 3)]

    for name, span in spans:
        for block in segment(span):
            cells, unparsed, cols = harvest_panel(
                prefix, name, page, block, geo, shared if name else [])
            out["cells"].extend(cells)
            out["unparsed"].extend(unparsed)
            out["columns"].extend(cols)

    # Two cells cannot share an address. If they do the checklist is scoring one
    # number twice and never scoring another, which is worse than missing them
    # both because the count still looks right.
    seen: dict[str, int] = {}
    for c in out["cells"]:
        seen[c["id"]] = seen.get(c["id"], 0) + 1
    out["collisions"] = sorted(k for k, n in seen.items() if n > 1)

    if not out["cells"]:
        # A table can be real and hold no numbers: Table 2 marks which
        # predictors entered each subset with stars. That is a claim to be
        # checked, so it stays on the list rather than disappearing because it
        # is not numeric.
        out.update(needs_human=True,
                   why="no printed numbers: the claim is the pattern of marks, "
                       "which has to be checked against the selected variables")
    return out


def acceptance(front: str) -> dict:
    """Whether an arXiv posting is actually a peer-reviewed accepted manuscript.

    This is printed on page one and nowhere in the arXiv metadata, so a site
    that reads only the metadata shows a Journal of Banking and Finance paper
    and an unrefereed preprint as the same thing. They are not the same thing,
    and the difference is one regex away.
    """
    out: dict = {"accepted": False, "journal": "", "doi": "", "evidence": ""}
    m = re.search(r"[Aa]ccepted for publication in\s+(?:the\s+)?([^\n.]{3,90})", front)
    if m:
        out.update(accepted=True, journal=m.group(1).strip(),
                   evidence=m.group(0).strip())
    if re.search(r"[Aa]uthor accepted manuscript", front):
        out["accepted"] = True
        out.setdefault("evidence", "Author accepted manuscript")
    d = re.search(r"(10\.\d{4,9}/[^\s)]+)", front)
    if d:
        out["doi"] = d.group(1).rstrip(".")
        out["accepted"] = True
    # A DOI carries the year the publisher assigned, which is how fast the
    # journal moved relative to the preprint.
    y = re.search(r"\.(19|20)(\d{2})\.", out["doi"] or "")
    if y:
        out["journal_year"] = int(y.group(1) + y.group(2))
    return out


def extract(pdf_path: str) -> dict:
    paper = os.path.basename(pdf_path).replace(".pdf", "")
    with pdfplumber.open(pdf_path) as pdf:
        pages = [p.extract_text() or "" for p in pdf.pages]
        geos = [page_geometry(p) for p in pdf.pages]

    exhibits = []
    for i, text in enumerate(pages, 1):
        marks = list(CAPTION.finditer(text))
        for j, m in enumerate(marks):
            end = marks[j + 1].start() if j + 1 < len(marks) else len(text)
            # A caption is only an exhibit if the block under it holds numbers
            # or is a figure. In-text references ("Table 3 reports the R2
            # values") match the same pattern and must not become exhibits.
            block = text[m.start():end]
            kind, number, title = m.group(1), m.group(2), m.group(3)
            ex = harvest_exhibit(kind, number, title, i, block, geos[i - 1])
            # An in-text reference ("Table 3 reports the R2 values") matches the
            # same caption pattern. What separates it from the exhibit is that
            # the exhibit is followed by its own contents: numbers, or a notes
            # block explaining them.
            if ex["cells"] or NOTES.search(block) or kind == "Figure":
                exhibits.append(ex)

    # A paper reprints its captions in the body; the exhibit itself is the
    # occurrence carrying the numbers, so keep the richest one per name.
    best: dict[str, dict] = {}
    for ex in exhibits:
        key = ex["exhibit"]
        if key not in best or len(ex["cells"]) > len(best[key]["cells"]):
            best[key] = ex
    kept = sorted(best.values(), key=lambda e: e["page"])

    total = sum(len(e["cells"]) for e in kept)
    return {
        "paper": paper,
        "pages": len(pages),
        "acceptance": acceptance(pages[0] if pages else ""),
        "exhibits": kept,
        "totals": {
            "exhibits": len(kept),
            "tables": sum(1 for e in kept if e["kind"] == "table"),
            "figures": sum(1 for e in kept if e["kind"] == "figure"),
            "numbers": total,
            "unparsed_lines": sum(len(e["unparsed"]) for e in kept),
        },
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("pdf", nargs="*", help="paper PDFs to harvest")
    ap.add_argument("--all", action="store_true", help="every cached PDF")
    args = ap.parse_args()

    paths = args.pdf or []
    if args.all:
        paths = sorted(glob.glob(os.path.join(ROOT, "data", "cache", "pdf", "*.pdf")))
    if not paths:
        ap.error("give a PDF path or --all")

    os.makedirs(OUT_DIR, exist_ok=True)
    for path in paths:
        result = extract(path)
        out = os.path.join(OUT_DIR, f"{result['paper']}.json")
        with open(out, "w", encoding="utf-8", newline="\n") as fh:
            json.dump(result, fh, indent=1, ensure_ascii=False)
        t = result["totals"]
        acc = result["acceptance"]
        where = f" [{acc['journal'] or acc['doi']}]" if acc["accepted"] else ""
        print(f"{result['paper']}{where}: {t['numbers']} numbers in {t['exhibits']} "
              f"exhibits ({t['tables']} tables, {t['figures']} figures), "
              f"{t['unparsed_lines']} lines needing a human -> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
