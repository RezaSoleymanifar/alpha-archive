"""Score a replication against the paper's own count, not against its own.

`extract_artifacts.py` says what the paper printed. `data/artifacts/*.json` says
what we checked. This puts them side by side and reports the fraction, which is
the number a reader needs and the one a builder is least inclined to compute.

    uv run python tools/coverage.py                    # every paper with a checklist
    uv run python tools/coverage.py 2606.04153 --map   # suggest cell ids for unmapped rows

The gate, in order of how much it matters:

  1. A paper claiming `fully_reproduced` while any printed number is unchecked
     is a lie, and fails the build.
  2. An artifact naming a cell that is not in the checklist is scoring something
     the paper does not print, and fails the build.
  3. An artifact whose declared `published` value disagrees with the harvested
     one is a transcription error, and fails the build. This is not theoretical:
     two of six rows transcribed by hand for 2606.04153 were wrong, and one of
     them was a percent read as a fraction.

Low coverage does not fail. Checking 12 numbers out of 1,794 is honest work as
long as it is reported as 12 out of 1,794. What fails is the claim, never the
size of the effort.
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHECKLISTS = os.path.join(ROOT, "data", "checklists")
ARTIFACTS = os.path.join(ROOT, "data", "artifacts")
OUT_DIR = os.path.join(ROOT, "data", "coverage")

# How close a declared `published` value has to be to the harvested one before
# it counts as the same number. Papers print to two decimals; anything further
# apart than half a printed unit is a different number, not a rounding.
TRANSCRIPTION_EPS = 0.005


def load_checklist(paper: str) -> dict | None:
    for path in (os.path.join(CHECKLISTS, f"{paper}.json"),
                 *glob.glob(os.path.join(CHECKLISTS, f"{paper}v*.json"))):
        if os.path.exists(path):
            with open(path, encoding="utf-8") as fh:
                return json.load(fh)
    return None


def load_artifacts(paper: str) -> dict | None:
    path = os.path.join(ARTIFACTS, f"{paper}.json")
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def cells_by_id(checklist: dict) -> dict[str, dict]:
    return {c["id"]: c for e in checklist["exhibits"] for c in e["cells"]}


def suggest(checklist: dict, art: dict) -> list[str]:
    """Cell ids whose printed value matches this artifact's declared one.

    Only ever a suggestion. A value like 0.17 appears in Table 6 eleven times,
    so the exhibit narrows it and a person still has to choose. Guessing here
    would put a verdict on a cell nobody looked at, which is the failure this
    whole file exists to prevent.
    """
    want, where = art.get("published"), (art.get("where") or "").replace(" ", "")
    if want is None:
        return []
    out = []
    for e in checklist["exhibits"]:
        if where and e["exhibit"].replace(" ", "") != where:
            continue
        for c in e["cells"]:
            if abs(c["value"] - float(want)) <= TRANSCRIPTION_EPS:
                out.append(c["id"])
    return out


def score(paper: str, checklist: dict, artifacts: dict | None) -> dict:
    cells = cells_by_id(checklist)
    rows = (artifacts or {}).get("artifacts", [])

    mapped, unmapped, unknown, mistyped = {}, [], [], []
    for art in rows:
        cid = art.get("cell")
        if not cid:
            unmapped.append(art.get("name", "?"))
            continue
        for one in (cid if isinstance(cid, list) else [cid]):
            if one not in cells:
                unknown.append({"name": art.get("name", "?"), "cell": one})
                continue
            printed = cells[one]["value"]
            declared = art.get("published")
            if declared is not None and abs(printed - float(declared)) > TRANSCRIPTION_EPS:
                mistyped.append({"name": art.get("name", "?"), "cell": one,
                                 "declared": declared, "printed": printed})
            mapped[one] = art.get("state", "NOT_ATTEMPTED")

    per_exhibit = []
    for e in checklist["exhibits"]:
        ids = [c["id"] for c in e["cells"]]
        hit = [i for i in ids if i in mapped]
        per_exhibit.append({
            "exhibit": e["exhibit"],
            "page": e["page"],
            "numbers": len(ids),
            "checked": len(hit),
            "reproduced": sum(1 for i in hit if mapped[i] == "REPRODUCED"),
            "needs_human": e.get("needs_human", False),
            "title": e["title"],
        })

    total = sum(x["numbers"] for x in per_exhibit)
    checked = sum(x["checked"] for x in per_exhibit)
    claims_full = bool((artifacts or {}).get("fully_reproduced"))

    failures = []
    if claims_full and checked < total:
        failures.append(f"claims fully_reproduced with {total - checked} numbers unchecked")
    for u in unknown:
        failures.append(f"artifact {u['name']!r} names cell {u['cell']!r}, "
                        f"which the paper does not print")
    for m in mistyped:
        failures.append(f"artifact {m['name']!r} says the paper printed {m['declared']}, "
                        f"the page says {m['printed']} ({m['cell']})")

    return {
        "paper": paper,
        "acceptance": checklist.get("acceptance", {}),
        "numbers": total,
        "checked": checked,
        "reproduced": sum(x["reproduced"] for x in per_exhibit),
        "coverage": round(checked / total, 4) if total else 0.0,
        "exhibits_total": len(per_exhibit),
        "exhibits_touched": sum(1 for x in per_exhibit if x["checked"]),
        "exhibits": per_exhibit,
        "unmapped_artifacts": unmapped,
        "failures": failures,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("paper", nargs="?", help="arXiv id, e.g. 2606.04153")
    ap.add_argument("--map", action="store_true",
                    help="print candidate cell ids for artifacts with no cell")
    args = ap.parse_args()

    papers = [args.paper] if args.paper else sorted(
        os.path.basename(p)[:-5].split("v")[0]
        for p in glob.glob(os.path.join(CHECKLISTS, "*.json")))

    os.makedirs(OUT_DIR, exist_ok=True)
    bad = 0
    for paper in papers:
        checklist = load_checklist(paper)
        if not checklist:
            print(f"{paper}: no checklist. Run tools/extract_artifacts.py first.",
                  file=sys.stderr)
            bad += 1
            continue
        artifacts = load_artifacts(paper)
        result = score(paper, checklist, artifacts)

        with open(os.path.join(OUT_DIR, f"{paper}.json"), "w",
                  encoding="utf-8", newline="\n") as fh:
            json.dump(result, fh, indent=1, ensure_ascii=False)

        acc = result["acceptance"]
        badge = f" [{acc.get('journal') or acc.get('doi')}]" if acc.get("accepted") else ""
        print(f"\n{paper}{badge}")
        print(f"  {result['checked']} of {result['numbers']} printed numbers checked "
              f"({result['coverage']:.1%}), {result['reproduced']} reproduced")
        print(f"  {result['exhibits_touched']} of {result['exhibits_total']} exhibits touched")
        for x in result["exhibits"]:
            if x["numbers"] or x["needs_human"]:
                flag = "  (plotted, needs a person)" if x["needs_human"] else ""
                print(f"    {x['exhibit']:<10} p{x['page']:<4} "
                      f"{x['checked']:>4}/{x['numbers']:<4}{flag}")

        if args.map and artifacts:
            print("  candidates for unmapped artifacts:")
            for art in artifacts.get("artifacts", []):
                if art.get("cell"):
                    continue
                hits = suggest(checklist, art)
                print(f"    {art.get('name','?')[:44]:<46} "
                      f"{'  '.join(hits[:4]) if hits else 'no match on value'}")

        for f in result["failures"]:
            print(f"  FAIL: {f}", file=sys.stderr)
        bad += len(result["failures"])

    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
