"""Keep the paper's own charts for the papers we intend to replicate.

A replication is judged by whether its curve lands on top of the author's, so
the author's figure has to survive somewhere durable. The render cache does not
count. It is gitignored and rebuilt from PDFs that may move or be withdrawn.

Only keeps are promoted. Rendering every page of all 1,014 papers at review
resolution is roughly a gigabyte, and the drops are dropped precisely because
nothing in them will ever be compared against.

    uv run python tools/keep_figures.py
"""

from __future__ import annotations

import io
import json
import os
import re
import shutil
import sys

from PIL import Image

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE = os.path.join(ROOT, "data", "cache", "figures")
KEPT = os.path.join(ROOT, "data", "figures")
LEDGER = os.path.join(ROOT, "data", "triage", "ledger.json")

QUALITY = 82
MAX_WIDTH = 1300


def norm(arxiv_id: str) -> str:
    return re.sub(r"v\d+$", "", (arxiv_id or "").strip())


def main() -> None:
    with open(LEDGER, encoding="utf-8") as fh:
        papers = json.load(fh)["papers"]
    keeps = {norm(k) for k, v in papers.items() if v.get("verdict") == "keep"}

    os.makedirs(KEPT, exist_ok=True)
    moved = skipped = 0
    before = after = 0

    for name in sorted(os.listdir(CACHE)) if os.path.isdir(CACHE) else []:
        if not name.lower().endswith(".png"):
            continue
        stem = name.rsplit("_p", 1)[0]
        if norm(stem) not in keeps:
            skipped += 1
            continue

        source = os.path.join(CACHE, name)
        target = os.path.join(KEPT, name.rsplit(".", 1)[0] + ".jpg")
        before += os.path.getsize(source)
        try:
            image = Image.open(source).convert("RGB")
            if image.width > MAX_WIDTH:
                height = round(image.height * MAX_WIDTH / image.width)
                image = image.resize((MAX_WIDTH, height), Image.LANCZOS)
            image.save(target, "JPEG", quality=QUALITY, optimize=True)
        except Exception:
            shutil.copy2(source, target)
        after += os.path.getsize(target)
        moved += 1

    print(f"keeps in ledger : {len(keeps)}")
    print(f"figures kept    : {moved}   ({before / 1e6:.1f} MB -> {after / 1e6:.1f} MB)")
    print(f"figures skipped : {skipped}  (belong to drops)")
    print(f"in {KEPT}")


if __name__ == "__main__":
    main()
