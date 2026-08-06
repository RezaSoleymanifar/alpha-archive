"""Reduce a paper to the part a triage decision actually turns on.

The verdict needs three things: what the method is, what data it touched, and
which numbers it reports. A 40-page PDF carries all three inside maybe two
pages of text, and the rest (related work, proofs, appendices) never changes
the answer. Pulling the relevant sections keeps a batch of papers small enough
to judge in one pass instead of one paper at a time.

The sections are found by heading, and when no heading matches, the fallback is
the paragraphs that mention a data source or a sample window. A paper whose text
will not extract at all is recorded as such rather than guessed at.

    uv run python tools/digest.py --limit 25          # next 25 unjudged papers
    uv run python tools/digest.py --limit 25 --out data/triage/digest_00.json
"""

from __future__ import annotations

import argparse
import io
import json
import os
import re
import sys
import time

import httpx
import pypdfium2 as pdfium

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
QUEUE = os.path.join(ROOT, "data", "triage", "queue.json")
LEDGER = os.path.join(ROOT, "data", "triage", "ledger.json")
CACHE = os.path.join(ROOT, "data", "cache", "pdf")
FIGURES = os.path.join(ROOT, "data", "cache", "figures")

UA = {"User-Agent": "alpha-archive (reza@soleymanifar.com)"}
MAX_PAGES = 40
THROTTLE = 3.0   # seconds between downloads, per process

# Headings that introduce the sections a verdict turns on.
WANTED = re.compile(
    r"^\s*(?:\d+(?:\.\d+)*\s*\.?\s*)?"
    r"(data(?:\s+and\s+\w+)?|dataset[s]?|sample|empirical\s+\w+|"
    r"method(?:s|ology)?|experimental\s+setup|results?|"
    r"implementation|backtest\w*|simulation\s+setup)\s*$",
    re.I,
)
STOP = re.compile(
    r"^\s*(?:\d+(?:\.\d+)*\s*\.?\s*)?"
    r"(references|bibliography|acknowledg\w+|appendix|conclusion[s]?)\s*$",
    re.I,
)

# Figure and table captions. These are not decoration, the verdicts already in
# the ledger name their reproducible targets as "Figure 6 panel (a)" and "Table
# 3", so a digest that drops captions drops the very thing being reproduced.
CAPTION = re.compile(
    r"^\s*(fig(?:ure)?\.?\s*\d+[a-z]?|table\s+[IVX\d]+[a-z]?)\s*[.:, -]?\s+(.{20,})",
    re.I,
)

# When no heading matches, keep paragraphs that name data or a window.
DATA_HINT = re.compile(
    r"CRSP|Compustat|WRDS|Bloomberg|Refinitiv|RavenPack|OptionMetrics|Yahoo|"
    r"Binance|Coinbase|Kaggle|Fama[- ]French|open\s?source\s?asset|arXiv|"
    r"S&P|NASDAQ|NYSE|Russell|STOXX|FTSE|Nikkei|CSI\s?300|"
    r"daily (?:returns?|prices?|closes?)|tick data|order book|"
    r"(?:19|20)\d{2}\s*(?:to|-| none |through)\s*(?:19|20)\d{2}|"
    r"we (?:use|collect|obtain|download|construct|simulate)",
    re.I,
)


def fetch(paper: dict) -> bytes | None:
    os.makedirs(CACHE, exist_ok=True)
    path = os.path.join(CACHE, f"{paper['arxiv_id']}.pdf")
    if os.path.exists(path) and os.path.getsize(path) > 2000:
        with open(path, "rb") as fh:
            return fh.read()
    url = paper.get("pdf")
    if not url:
        return None
    # Several of these run at once during a bulk pass. arXiv asks for roughly
    # one request every three seconds, and a cache hit above costs nothing, so
    # the wait is only ever paid on a genuine download.
    time.sleep(THROTTLE)
    try:
        response = httpx.get(url, headers=UA, timeout=120, follow_redirects=True)
        response.raise_for_status()
    except Exception:
        return None
    if not response.content.startswith(b"%PDF"):
        return None
    with open(path, "wb") as fh:
        fh.write(response.content)
    return response.content


def pages_of(raw: bytes) -> list[str]:
    doc = pdfium.PdfDocument(raw)
    out = []
    for i in range(min(len(doc), MAX_PAGES)):
        try:
            out.append(doc[i].get_textpage().get_text_range())
        except Exception:
            out.append("")
    return out


# A row of a results table: a label followed by two or more numbers. These are
# the numbers a replication has to land on, and unlike a caption they state the
# value rather than describing it.
NUMERIC_ROW = re.compile(
    r"^\s*\S.{0,60}?\s"                      # a short row label
    r"(?:[-−(]?\d[\d,]*\.?\d*\*{0,3}\)?%?\s+){2,}"  # two or more numbers
    r"[-−(]?\d[\d,]*\.?\d*\*{0,3}\)?%?\s*$"
)


def tables(pages: list[str], budget: int = 3000) -> list[str]:
    """The body of each results table, not just its caption.

    A caption says a table compares Sharpe ratios; the rows say which Sharpe.
    Only the second one can be checked against a replication, so the numeric
    rows following each table heading are carried through.
    """
    kept: list[str] = []
    for page in pages:
        lines = page.splitlines()
        for i, line in enumerate(lines):
            match = CAPTION.match(line)
            if not match or not match.group(1).lower().startswith("tab"):
                continue
            rows = [f"[{match.group(1).strip()}]"]
            for follow in lines[i + 1:i + 26]:
                flat = " ".join(follow.split())
                if NUMERIC_ROW.match(follow) and len(flat) > 8:
                    rows.append(flat[:170])
            if len(rows) > 1:
                kept.append("\n".join(rows))
            if sum(len(k) for k in kept) > budget:
                return kept
    return kept


def captions(pages: list[str], budget: int = 2600) -> tuple[list[str], list[int]]:
    """Every figure and table caption, and which pages they sit on.

    The page numbers matter as much as the text: a caption says what a chart
    claims, and the chart itself is what a replication has to match, so those
    pages are the ones worth rendering.
    """
    found: list[str] = []
    where: set[int] = set()
    for index, page in enumerate(pages):
        for line in page.splitlines():
            match = CAPTION.match(line)
            if not match:
                continue
            label, body = match.group(1), " ".join(match.group(2).split())
            found.append(f"{label.strip()}: {body[:260]}")
            where.add(index)
            if sum(len(f) for f in found) > budget:
                return found, sorted(where)
    return found, sorted(where)


def render(raw: bytes, page_numbers: list[int], arxiv_id: str,
           limit: int = 4) -> list[str]:
    """Rasterise the pages carrying figures, so the charts can be looked at.

    Captions describe a result; the plot is where the number actually is. A
    triage that only ever reads prose cannot tell a convincing out-of-sample
    equity curve from an in-sample one.
    """
    if not page_numbers:
        return []
    os.makedirs(FIGURES, exist_ok=True)
    doc = pdfium.PdfDocument(raw)
    written = []
    for index in page_numbers[:limit]:
        if index >= len(doc):
            continue
        path = os.path.join(FIGURES, f"{arxiv_id}_p{index + 1}.png")
        try:
            doc[index].render(scale=1.6).to_pil().save(path, optimize=True)
        except Exception:
            continue
        written.append(path)
    return written


def sections(text: str, budget: int = 5200) -> str:
    """Keep the wanted sections, in order, up to a character budget."""
    lines = [ln.rstrip() for ln in text.splitlines()]
    kept: list[str] = []
    taking = False

    for line in lines:
        if STOP.match(line):
            taking = False
            continue
        if WANTED.match(line):
            taking = True
            kept.append(f"\n## {line.strip()}")
            continue
        if taking and line.strip():
            kept.append(line)
        if sum(len(k) for k in kept) > budget:
            break

    if sum(len(k) for k in kept) < 600:
        # No usable headings. Fall back to paragraphs that name data.
        kept = []
        for para in re.split(r"\n\s*\n", text):
            flat = " ".join(para.split())
            if len(flat) > 90 and DATA_HINT.search(flat):
                kept.append(flat)
            if sum(len(k) for k in kept) > budget:
                break

    body = "\n".join(kept)[:budget]
    return re.sub(r"[ \t]+", " ", body).strip()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=25)
    ap.add_argument("--offset", type=int, default=0)
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    with open(QUEUE, encoding="utf-8") as fh:
        queue = json.load(fh)["queue"]

    judged: set[str] = set()
    if os.path.exists(LEDGER):
        with open(LEDGER, encoding="utf-8") as fh:
            judged = {re.sub(r"v\d+$", "", k) for k in json.load(fh).get("papers", {})}

    # The nine journal papers carry a doi and no arxiv_id.
    pending = [p for p in queue
               if p.get("arxiv_id")
               and re.sub(r"v\d+$", "", p["arxiv_id"]) not in judged]
    batch = pending[args.offset:args.offset + args.limit]

    out, failed = [], 0
    for i, paper in enumerate(batch, 1):
        raw = fetch(paper)
        body, caps, figs, tabs = "", [], [], []
        if raw:
            try:
                pages = pages_of(raw)
                body = sections(chr(10).join(pages))
                caps, on_pages = captions(pages)
                tabs = tables(pages)
                figs = render(raw, on_pages, paper["arxiv_id"])
            except Exception:
                body = ""
        if not body and not caps:
            failed += 1
        out.append({
            "arxiv_id": paper["arxiv_id"],
            "title": paper["title"],
            "published": paper.get("published"),
            "abstract": (paper.get("abstract") or "")[:1200],
            "extract": body or "[pdf text could not be extracted]",
            "captions": caps,
            "tables": tabs,
            "figure_pages": figs,
        })
        print(f"  {i:>3}/{len(batch)}  {paper['arxiv_id']:<14} "
              f"{len(body):>5} chars  {len(caps):>2} caps  {len(figs)} png  "
              f"{paper['title'][:44]}")

    path = args.out or os.path.join(ROOT, "data", "triage", "digest.json")
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(out, fh, indent=1)
    print(f"\n{len(out)} digested, {failed} without extractable text")
    print(f"wrote {path}  ({os.path.getsize(path) / 1024:.0f} KB)")
    print(f"{len(pending) - len(batch)} still pending after this batch")


if __name__ == "__main__":
    main()
