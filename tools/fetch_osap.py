"""Index the Open Source Asset Pricing predictors as first-class entries.

The paywall problem has a way around it that is not piracy. Chen and Zimmermann
publish, for 331 published predictors, the claim each paper made, mean return,
t-statistic, sample window, together with a definition precise enough to
implement. The PDF is not needed to run the paper, which is exactly how this
project's first replication was built.

We keep the ones a reader can actually run: predictors OSAP marks as clearly
predictive, built from accounting, price or trading data, all of which Vintage
fetches free. Analyst estimates, options and 13F signals are excluded on the
same data gate the rest of the index uses.

Citations are matched back to OpenAlex on a best-effort basis, so an OSAP entry
can sit in the same ranking as everything else. Where no match is found the
card carries the paper's own t-statistic instead, and says so.

    uv run python tools/fetch_osap.py
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import os
import re
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

import httpx

import fetch_papers as fp

SIGNALDOC = ("https://raw.githubusercontent.com/OpenSourceAP/CrossSection/"
             "master/SignalDoc.csv")
OSAP_HOME = "https://www.openassetpricing.com/"
FREE_DATA = {"Accounting", "Price", "Trading"}      # what Vintage can fetch today

JOURNALS = {
    "JF": "Journal of Finance", "JFE": "Journal of Financial Economics",
    "RFS": "Review of Financial Studies", "AR": "The Accounting Review",
    "JAR": "Journal of Accounting Research", "JAE": "Journal of Accounting and Economics",
    "JPE": "Journal of Political Economy", "MS": "Management Science",
    "RFQA": "Review of Quantitative Finance and Accounting",
    "JFQA": "Journal of Financial and Quantitative Analysis",
    "RAS": "Review of Accounting Studies", "JB": "Journal of Business",
    "FAJ": "Financial Analysts Journal", "JFM": "Journal of Financial Markets",
}


def surname(authors: str) -> str:
    first = re.split(r",| and ", authors or "")[0].strip()
    return first.split()[-1] if first else ""


def match_openalex(row: dict, client: httpx.Client) -> dict | None:
    """Best effort: the signal name is not the paper title, so search on it and
    accept a hit only when the year and first author agree."""
    year, name = (row.get("Year") or "").strip(), surname(row.get("Authors", ""))
    if not year.isdigit() or not name:
        return None
    try:
        page = fp.openalex({
            "search": row.get("LongDescription") or "",
            "filter": f"publication_year:{year}",
            "per-page": 5,
        }, client)
    except Exception:
        return None
    for work in page.get("results", []):
        names = " ".join(a["author"]["display_name"]
                         for a in work.get("authorships", []) if a.get("author"))
        if name.lower() in names.lower():
            return work
    return None


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-match", action="store_true",
                    help="skip the OpenAlex citation match (use when its budget is out)")
    args = ap.parse_args()

    print("fetching SignalDoc")
    text = httpx.get(SIGNALDOC, timeout=120, follow_redirects=True).text
    rows = list(csv.DictReader(io.StringIO(text)))
    keep = [r for r in rows
            if r.get("Cat.Data") in FREE_DATA
            and r.get("Predictability in OP") == "1_clear"]
    print(f"  {len(rows)} predictors, {len(keep)} clear and on free data")

    out: list[dict] = []
    matched = 0
    with httpx.Client(follow_redirects=True) as client:
        for i, r in enumerate(keep, 1):
            work = None if args.no_match else match_openalex(r, client)
            if work:
                matched += 1
            cites = int((work or {}).get("cited_by_count") or 0)
            pct = float(((work or {}).get("citation_normalized_percentile") or {})
                        .get("value") or 0.0)
            year = (r.get("Year") or "1900").strip()
            published = f"{year}-01-01"
            journal = JOURNALS.get((r.get("Journal") or "").strip(),
                                   (r.get("Journal") or "working paper").strip())
            tstat = (r.get("T-Stat") or "").strip()
            sample = f"{r.get('SampleStartYear', '')}, {r.get('SampleEndYear', '')}".strip(", ")
            desc = (r.get("LongDescription") or r.get("Acronym") or "").strip()
            summary = (r.get("Evidence Summary") or "").strip()

            abstract = (
                f"{desc}. {r.get('Authors', '')} ({year}) report t = {tstat or 'n/a'} "
                f"over {sample or 'the paper’s sample'}, using "
                f"{(r.get('Cat.Data') or '').lower()} data. "
                f"{summary} Open Source Asset Pricing publishes the definition, so this "
                f"predictor can be implemented and rerun without the paper's PDF."
            ).strip()

            out.append({
                "openalex_id": (work or {}).get("id", "").rsplit("/", 1)[-1],
                "arxiv_id": None,
                "doi": (work or {}).get("doi"),
                "title": desc,
                "authors": (r.get("Authors") or "").strip(),
                "author_count": len(re.split(r",| and ", r.get("Authors") or "")),
                "abstract": abstract,
                "published": published,
                "primary_category": f"OSAP · {journal}",
                "url": OSAP_HOME,
                "pdf": None,
                "citations": cites,
                "citations_per_month": fp.per_month(cites, published),
                "percentile": round(pct, 4),
                "top_1pct": bool(((work or {}).get("citation_normalized_percentile") or {})
                                 .get("is_in_top_1_percent")),
                "source": "osap",
                "spec": True,
                "tstat": tstat,
                "sample": sample,
                "tags": fp.tags_for(f"{desc} {summary}"),
                "status": "queued",
                "status_note": "definition published by OSAP; runnable on free data",
                "thumb": None,
            })
            if i % 25 == 0:
                print(f"    {i}/{len(keep)}  matched={matched}", flush=True)
            time.sleep(0.0 if args.no_match else 0.35)

    path = os.path.join(fp.ROOT, "data", "papers", "osap.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump({"source": "Open Source Asset Pricing (Chen & Zimmermann)",
                   "url": OSAP_HOME, "predictors": out}, fh, indent=2)
    print(f"matched {matched}/{len(out)} to OpenAlex")
    print(f"wrote {path}")


if __name__ == "__main__":
    main()
