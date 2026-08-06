"""What the server serves: ideas, their published numbers, and their status.

Three files feed this and none of them were written for it. The triage ledger
holds every paper read and why it was kept or dropped. osap.json holds the
Chen-Zimmermann predictor definitions, which are specs rather than papers. The
replications directory holds what has actually been run.

They are joined here once, with the same status vocabulary across all of them,
because the single most useful thing this server can say is which of the three
a given idea is: proven, attempted, or only catalogued.
"""

from __future__ import annotations

import json
import os
import re
from typing import Any

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
LEDGER = os.path.join(ROOT, "data", "triage", "ledger.json")
APPEAL = os.path.join(ROOT, "data", "triage", "appeal.json")
PAPERS = os.path.join(ROOT, "data", "papers", "papers.json")
OSAP = os.path.join(ROOT, "data", "papers", "osap.json")
RUNS = os.path.join(ROOT, "data", "replications")
CODE = os.path.join(ROOT, "alpha_archive", "replications")

# The only three things an idea can be. Anything softer than this is how a
# catalogue starts describing itself as a library of proven strategies.
VERIFIED = "VERIFIED"          # rebuilt and it matched the paper's own numbers
ATTEMPTED = "ATTEMPTED"        # rebuilt, and it did not match, or could not be checked
CATALOGUED = "CATALOGUED"      # read and judged reproducible, never run

REPO = "https://github.com/RezaSoleymanifar/alpha-archive"


def norm(ident: str | None) -> str:
    return re.sub(r"v\d+$", "", (ident or "").strip())


def _read(path: str, default: Any) -> Any:
    if not os.path.exists(path):
        return default
    with open(path, encoding="utf-8") as fh:
        try:
            return json.load(fh)
        except json.JSONDecodeError:
            return default


def slug(text: str | None) -> str:
    return re.sub(r"[^a-z0-9]", "", (text or "").lower())


ARXIV_ID = re.compile(r"(\d{4}\.\d{4,5})")


def arxiv_of(text: str | None) -> str:
    """The bare id out of anything that carries one.

    One record stores `arxiv` as a full abs URL. Slugging that gave
    `httpsarxivorgabs260720093`, which matches nothing, and the archive
    reported no replications while two sat on disk.
    """
    found = ARXIV_ID.search(text or "")
    return found.group(1) if found else ""


def runs() -> dict[str, dict[str, Any]]:
    """Replications that have actually executed, under every name they answer to.

    These records were written by different runs over months and do not agree
    on a key. One carries `arxiv`, another `arxiv_id`, a third only a short
    name like Mom12m that matches an OSAP acronym rather than a title. Keying
    on any single field silently found nothing, which showed up as an archive
    reporting zero replications while two sat on disk.
    """
    out: dict[str, dict[str, Any]] = {}
    if not os.path.isdir(RUNS):
        return out

    for name in sorted(os.listdir(RUNS)):
        if not name.endswith(".json"):
            continue
        rec = _read(os.path.join(RUNS, name), None)
        if not isinstance(rec, dict):
            continue
        # A run has to name a paper. Harness self-tests do not.
        if not (rec.get("paper") or rec.get("arxiv") or rec.get("arxiv_id")
                or rec.get("paper_title")):
            continue

        for alias in (rec.get("arxiv_id"), rec.get("arxiv"), rec.get("paper"),
                      rec.get("paper_title"), rec.get("paper_id"), name[:-5]):
            if not alias:
                continue
            out.setdefault(norm(str(alias)), rec)
            out.setdefault(slug(str(alias)), rec)
            if arxiv_of(str(alias)):
                out.setdefault(arxiv_of(str(alias)), rec)
    return out


# Short names the replication records use, against the catalogue entry they
# belong to. Chen-Zimmermann acronyms are not the predictor titles.
ALIASES = {
    "momentum12month": "mom12m",     # OSAP title -> the acronym the run used
    "momentum6month": "mom6m",
}


def find_run(executed: dict[str, dict[str, Any]], *keys: str) -> dict[str, Any] | None:
    for key in keys:
        if not key:
            continue
        for candidate in (norm(key), slug(key), arxiv_of(key),
                          ALIASES.get(slug(key), "")):
            if candidate and candidate in executed:
                return executed[candidate]
    return None


def status_of(rec: dict[str, Any] | None) -> tuple[str, str]:
    """Proven, attempted, or catalogued, and the sentence that justifies it.

    A run that exists is not a pass. The first replication in this repo ran
    fine and still cannot be verified, because the fixture it would have to be
    checked against is not obtainable.
    """
    if rec is None:
        return CATALOGUED, ("Read and judged reproducible on free data. "
                            "Never run, so nothing here is proven.")

    verdict = (rec.get("verification") or {}).get("status")
    if verdict == "VERIFIED":
        return VERIFIED, "Rebuilt, and it matched the numbers the paper published."
    if verdict:
        return ATTEMPTED, (
            f"Rebuilt. Verification came back {verdict}: "
            + ((rec.get("verification") or {}).get("reason") or "no reason recorded.")
        )

    families = rec.get("families")
    if families:
        ok = sum(1 for f in families
                 if f.get("sharpe_gate") == f.get("paper_sharpe_gate")
                 and f.get("cagr_gate") == f.get("paper_cagr_gate"))
        if ok == len(families):
            return VERIFIED, (
                f"Rebuilt. All {len(families)} of the paper's gates reproduced.")
        return ATTEMPTED, (
            f"Rebuilt. {ok} of {len(families)} of the paper's gates reproduced; "
            "the rest differ.")
    return ATTEMPTED, "Rebuilt, with no verification criterion recorded against it."


# Which module implements which idea. Guessing this from the filename matched
# "Momentum (12 month)" against nothing, because the module is named for the
# paper's authors rather than the predictor. An explicit map is three lines and
# cannot silently report that working code does not exist.
IMPLEMENTATIONS = {
    "momentum12month": "jt1993.py",
    "260720093": "darmanin2026.py",
    "260706117": "rgrr2026_data.py",
}


def implementation(key: str) -> str | None:
    """The module that implements an idea, if one exists."""
    if not os.path.isdir(CODE):
        return None
    for candidate in (slug(key), arxiv_of(key).replace(".", "")):
        name = IMPLEMENTATIONS.get(candidate)
        if name and os.path.exists(os.path.join(CODE, name)):
            return os.path.join(CODE, name)
    return None


def load() -> list[dict[str, Any]]:
    """Every idea the server knows, papers and specs alike."""
    ledger = (_read(LEDGER, {}) or {}).get("papers", {})
    appeal = _read(APPEAL, {}) or {}
    index = _read(PAPERS, [])
    rows = index if isinstance(index, list) else index.get("papers", [])
    meta = {norm(p.get("arxiv_id")): p for p in rows}
    executed = runs()

    out: list[dict[str, Any]] = []

    for key, entry in ledger.items():
        if entry.get("verdict") != "keep":
            continue
        ident = norm(key)
        paper = meta.get(ident, {})
        rec = find_run(executed, ident, paper.get("title") or "")
        state, why = status_of(rec)
        scored = appeal.get(ident) or {}
        out.append({
            "id": ident,
            "kind": "paper",
            "title": (paper.get("title") or ident).strip(),
            "authors": paper.get("authors") or "",
            "published": (paper.get("published") or "")[:10],
            "url": paper.get("url") or f"https://arxiv.org/abs/{ident}",
            "method": entry.get("method") or "",
            "finding": scored.get("one_liner") or "",
            "appeal": scored.get("appeal") or 0,
            "data_needed": entry.get("data_needed") or [],
            "published_numbers": entry.get("reproducible_targets") or [],
            "status": state,
            "status_note": why,
            "implementation": implementation(ident),
        })

    for spec in (_read(OSAP, {}) or {}).get("predictors", []):
        name = (spec.get("title") or "").strip()
        rec = find_run(executed, name, spec.get("acronym") or "")
        state, why = status_of(rec)
        out.append({
            "id": name,
            "kind": "spec",
            "title": name,
            "authors": spec.get("authors") or "",
            "published": (spec.get("published") or "")[:10],
            "url": spec.get("url") or "https://www.openassetpricing.com/",
            "method": spec.get("abstract") or "",
            "finding": "",
            "appeal": 0,
            "data_needed": [],
            "published_numbers": (
                [f"t-statistic {spec['tstat']} over {spec.get('sample') or 'the paper sample'}"]
                if spec.get("tstat") else []),
            "status": state,
            "status_note": why,
            "implementation": implementation(name),
        })

    out.sort(key=lambda i: ({VERIFIED: 0, ATTEMPTED: 1, CATALOGUED: 2}[i["status"]],
                            -i["appeal"]))
    return out


def tally(items: list[dict[str, Any]]) -> dict[str, int]:
    counts = {VERIFIED: 0, ATTEMPTED: 0, CATALOGUED: 0}
    for item in items:
        counts[item["status"]] += 1
    return counts
