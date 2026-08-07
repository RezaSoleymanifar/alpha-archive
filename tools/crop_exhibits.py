"""Cut every exhibit out of the paper's own PDF, one image per table.

The side-by-side is only an argument if the left half is the exhibit. Handing it
a whole page and calling it Table 1 shows the reader a column of prose next to
our numbers, which is worse than showing nothing: it looks like evidence and is
not. So each image here is located by its caption and trimmed to its own ink.

    page      the checklist recorded which page every cell was read off
    caption   "Table 6" is searched for on that page, and its position is the
              top edge of the crop
    bottom    the next caption if the page holds two exhibits, otherwise the
              page's bottom margin
    trim      whitespace is cut back to the actual ink, so the image is the
              table rather than the page it sat on

Nothing is guessed. If the caption is not on the page the checklist named, this
raises instead of cropping something and hoping.

    uv run python tools/crop_exhibits.py 2606.04153
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import re
import sys

import fitz
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHECKLISTS = os.path.join(ROOT, "data", "checklists")
PDFS = os.path.join(ROOT, "data", "cache", "pdf")
OUT = os.path.join(ROOT, "notebooks", "paper_figures")

DPI = 200
ZOOM = DPI / 72.0

# Ink darker than this counts as content when trimming. Scanned-looking JPEG
# fringe around a table sits well above it, so the trim does not eat rules.
INK = 245


def exhibit_caption(exhibit: str) -> str:
    """"TB1" -> "Table B1", the string the caption line actually starts with."""
    m = re.match(r"^([A-Z])([A-Z]?)(\d+)$", exhibit)
    if not m:
        return exhibit
    kind = {"T": "Table", "F": "Figure"}.get(m.group(1), m.group(1))
    return f"{kind} {m.group(2)}{m.group(3)}"


def find_pdf(paper: str) -> str:
    hits = sorted(glob.glob(os.path.join(PDFS, f"{paper}*.pdf")))
    if not hits:
        sys.exit(f"no PDF cached for {paper} under data/cache/pdf")
    return hits[0]


def load_checklist(paper: str) -> dict:
    hits = (glob.glob(os.path.join(CHECKLISTS, f"{paper}.json"))
            or glob.glob(os.path.join(CHECKLISTS, f"{paper}v*.json")))
    if not hits:
        sys.exit(f"no checklist for {paper}")
    with open(hits[0], encoding="utf-8") as fh:
        return json.load(fh)


def checklist_pages(paper: str) -> dict[str, int]:
    """Exhibit -> the page its cells were read off, as the checklist recorded."""
    pages: dict[str, list[int]] = {}
    for e in load_checklist(paper).get("exhibits", []):
        for c in e.get("cells") or []:
            key = c["id"].split("/")[0]
            pages.setdefault(key, []).append(int(c["page"]))
    # A table that spills over a page break is filed under both; the caption is
    # on the first, so that is the one to search.
    return {k: min(v) for k, v in pages.items() if v}


# A caption line, as the paper writes them: "Table 6:", "Table B1.", "Figure 4".
# The colon or period is what separates a caption from a cross-reference in the
# body text, which is the difference between finding the exhibit and finding a
# sentence that mentions it.
CAPTION = re.compile(r"^(Table|Figure)\s+([A-Z]?)(\d+)\s*[:.]")


def blocks_in_display_space(page) -> list[tuple[fitz.Rect, str]]:
    """Text blocks with their rectangles as the page is actually shown.

    `get_text` reports coordinates in the PDF's own unrotated space, while
    `get_pixmap(clip=...)` reads them in the displayed space. On the four
    landscape pages in this paper those two disagree by a quarter turn, and
    cropping with the mismatch produced an uncaptioned slice of the middle of
    each wide table. Multiplying through `rotation_matrix` puts both on the
    same axes.
    """
    matrix = page.rotation_matrix
    out = []
    for block in page.get_text("blocks"):
        rect = fitz.Rect(block[:4]) * matrix
        rect.normalize()
        out.append((rect, " ".join(str(block[4]).split())))
    return out


def discover(doc) -> dict[str, dict]:
    """Every exhibit in the PDF, found by reading its captions.

    The checklist only knows about exhibits that print numbers, so it cannot
    see a single figure. Scanning the document finds both, finds them where
    they actually are, and keeps the caption the paper wrote rather than a
    description invented later.
    """
    found: dict[str, dict] = {}
    for index in range(doc.page_count):
        for rect, text in blocks_in_display_space(doc[index]):
            m = CAPTION.match(text)
            if not m:
                continue
            kind, letter, number = m.group(1), m.group(2), m.group(3)
            key = f"{kind[0]}{letter}{number}"
            # First caption wins: a later page repeating "Table 6" is the
            # continuation of a table, not a second one.
            if key not in found:
                found[key] = {"page": index, "top": float(rect.y0),
                              "caption": text}
    return found


def trim(path: str) -> tuple[int, int]:
    """Cut the crop back to its own ink, and report what is left."""
    img = Image.open(path).convert("RGB")
    grey = img.convert("L")
    mask = grey.point(lambda p: 255 if p < INK else 0)
    box = mask.getbbox()
    if box:
        pad = 12
        box = (max(0, box[0] - pad), max(0, box[1] - pad),
               min(img.width, box[2] + pad), min(img.height, box[3] + pad))
        img = img.crop(box)
    img.save(path)
    return img.size


def crop(exhibit: str, entry: dict, others: dict, doc) -> dict | None:
    """One exhibit, from its caption down to whatever ends it."""
    index, top = entry["page"], entry["top"]
    page = doc[index]
    blocks = blocks_in_display_space(page)

    start = max(0.0, top - 14)
    # Clear of the folio. The page number is ink, so a trim that stops at the
    # bottom margin keeps it and every crop ends in a stray "44".
    bottom = page.rect.height - 76

    # Each of these tables closes with its own "Notes:" paragraph, and the page
    # then carries on in running prose. Ending at that paragraph is what keeps
    # half a page of unrelated body text out of the image. The text is kept as
    # well: the redrawn exhibit has to reproduce it, and it is a large enough
    # block of ink that leaving it out shows up in the parity score.
    notes = ""
    for rect, text in blocks:
        if rect.y0 >= start and text.startswith("Notes:"):
            bottom = min(bottom, rect.y1 + 12)
            notes = text
            break

    # And stop above a second exhibit when the page carries one.
    for key, other in others.items():
        if key == exhibit or other["page"] != index:
            continue
        if other["top"] > start + 30:
            bottom = min(bottom, other["top"] - 14)

    rect = fitz.Rect(26, start, page.rect.width - 26, bottom)
    if rect.height < 50:
        return None
    pix = page.get_pixmap(matrix=fitz.Matrix(ZOOM, ZOOM), clip=rect)
    os.makedirs(OUT, exist_ok=True)
    path = os.path.join(OUT, f"{exhibit}.png")
    pix.save(path)
    w, h = trim(path)
    print(f"  {exhibit:5} p{index + 1:<3} {w:>5}x{h:<5} {entry['caption'][:62]}")
    return {"exhibit": exhibit, "page": index + 1, "width": w, "height": h,
            "aspect": round(h / max(1, w), 4),
            "image": f"{exhibit}.png", "label": exhibit_caption(exhibit),
            "caption": entry["caption"], "notes": notes}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("paper")
    args = ap.parse_args()

    doc = fitz.open(find_pdf(args.paper))
    found = discover(doc)
    tables = sum(1 for k in found if k.startswith("T"))
    print(f"{args.paper}: {len(found)} exhibits in {doc.page_count} pages "
          f"({tables} tables, {len(found) - tables} figures)")

    made = []
    for exhibit, entry in sorted(found.items()):
        block = crop(exhibit, entry, found, doc)
        if block:
            made.append(block)

    # What the checklist expected and the PDF did not yield, said out loud.
    missing = sorted(set(checklist_pages(args.paper)) - {b["exhibit"] for b in made})
    if missing:
        print(f"checklist exhibits with no caption found: {', '.join(missing)}",
              file=sys.stderr)

    index_path = os.path.join(OUT, "index.json")
    with open(index_path, "w", encoding="utf-8", newline="\n") as fh:
        json.dump({"paper": args.paper, "exhibits": made}, fh, indent=1)
    print(f"{len(made)} cropped -> notebooks/paper_figures/ (index.json written)")
    return 0 if not missing else 1


if __name__ == "__main__":
    raise SystemExit(main())
