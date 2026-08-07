"""Harvest the finance corpus from OpenAlex into DuckDB, numbers only.

Every field pulled here is a number somebody else computed and published, or a
date. Nothing in this file reads a paper, judges a paper, or asks a model what
it thinks of a paper. That is the point: a ranking is only defensible if each
input can be pointed at, and "an LLM said it was interesting" cannot be.

Source, and why it: OpenAlex is free, needs no key, has no rate limit worth
worrying about in the polite pool, and publishes two numbers this ranking
otherwise has to invent badly --

    fwci                            field-weighted citation impact. Citations
                                    divided by what a paper of that age, field
                                    and type normally gets. 1.0 is average.
    citation_normalized_percentile  where the paper sits in that distribution.

Both are already age- and field-adjusted, which is what makes a 1994 paper
comparable to a 2024 one at all. Raw citation counts are kept too, because a
ranking whose inputs cannot be inspected separately is a black box.

    uv run python tools/harvest_finance.py --since 1990
    uv run python tools/harvest_finance.py --since 2015 --limit 20000
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.parse
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(ROOT, "data", "corpus.duckdb")

API = "https://api.openalex.org/works"
MAILTO = "reza@soleymanifar.com"        # the polite pool; faster and unmetered
PER_PAGE = 200

# The corpus boundary, drawn once and inspectable. OpenAlex's Finance subfield
# is sixteen topics wide and most of them are not this: it carries healthcare
# reform, housing and neoliberalism, community development and European fiscal
# policy, and those outrank real finance work when sorted by impact. So the
# boundary is the five quantitative topics inside that subfield, named here
# rather than filtered per paper.
#
# This is the only judgement in the pipeline. It is a list of five published
# topic ids, not a score applied to individual papers, and moving a topic in or
# out changes the corpus visibly rather than quietly reweighting a ranking.
TOPICS = {
    "T10047": "Financial Markets and Investment Strategies",
    "T10067": "Stochastic processes and financial applications",
    "T10282": "Financial Risk and Volatility Modeling",
    "T11496": "Credit Risk and Financial Regulations",
}

# Left out, and why, so the omission is a statement.
#
# Capital Investment and Risk Analysis (T11976) was in this list and is not any
# more. It is corporate finance -- capital budgeting, real options, project
# appraisal -- and the audience here is quants, who do not read it. Four
# thousand papers left the corpus with it.
#
# Banking regulation and crisis policy (T10127, T10503, T13074, T14101) are
# finance but not quantitative. Housing, healthcare, community development and
# monetary policy (T11817, T11531, T14464, T14166) are not finance in the sense
# meant here.
#
# Still missing, and known to be: econometrics and machine learning applied to
# markets. OpenAlex files both outside the Finance subfield, so they need their
# own topic ids rather than a wider net here, and adding them is pending.

# Only the fields the ranking or the page actually uses. Asking for fewer
# fields makes each page smaller and the harvest faster.
FIELDS = ",".join([
    "id", "doi", "title", "publication_date", "publication_year", "type",
    "cited_by_count", "fwci", "citation_normalized_percentile",
    "counts_by_year", "referenced_works_count", "open_access",
    "authorships", "primary_location", "primary_topic", "language",
    # The idea, which is half the product. OpenAlex stores abstracts as an
    # inverted index (word -> positions) rather than as text, so it has to be
    # put back together below.
    "abstract_inverted_index",
    # Taxonomy. Every one of these is already computed and published per work,
    # so tagging the corpus costs nothing beyond asking for the field. Leaving
    # them out and inventing tags later would be slower and worse.
    "topics",            # up to three, each with subfield and field
    "keywords",          # phrase-level, scored
    "grants",            # funder, which says who paid for the question
    "type_crossref",
    # The citation graph, as outgoing edges. This is the single most useful
    # field here: it is what lets a paper be placed by what it builds on rather
    # than by what a classifier guessed about its title. It is also the largest
    # field by far, around forty ids per work.
    "referenced_works",
])


def _abstract(index: dict | None) -> str:
    """Rebuild the abstract from OpenAlex's word-position index."""
    if not index:
        return ""
    positions: list[tuple[int, str]] = []
    for word, spots in index.items():
        positions.extend((int(p), word) for p in spots)
    positions.sort()
    return " ".join(word for _, word in positions)


# Pace between pages. The polite pool allows ten requests a second, but two
# full harvests back to back still earned a 429, so this stays well under and
# costs about two minutes over the whole corpus.
PAUSE = 0.12


def _get(url: str, tries: int = 8) -> dict:
    for attempt in range(tries):
        try:
            req = urllib.request.Request(
                url, headers={"User-Agent": f"alpha-archive ({MAILTO})"})
            with urllib.request.urlopen(req, timeout=90) as fh:
                return json.load(fh)
        except urllib.error.HTTPError as exc:
            if attempt == tries - 1:
                raise
            # A 429 says come back later and often says exactly when. Honour
            # that when it does, and back off hard when it does not: giving up
            # on a throttle loses the whole harvest.
            after = exc.headers.get("Retry-After") if exc.headers else None
            wait = float(after) if after and str(after).isdigit() else 5 * (attempt + 1)
            print(f"  HTTP {exc.code}, waiting {wait:.0f}s "
                  f"(attempt {attempt + 1})", file=sys.stderr, flush=True)
            time.sleep(wait)
        except Exception as exc:                       # noqa: BLE001
            if attempt == tries - 1:
                raise
            wait = 2 ** attempt
            print(f"  retry {attempt + 1} in {wait}s ({exc})", file=sys.stderr)
            time.sleep(wait)
    return {}


def _row(work: dict) -> dict:
    """One work, flattened to the numbers and the few strings a page needs."""
    loc = work.get("primary_location") or {}
    source = (loc.get("source") or {}) if isinstance(loc, dict) else {}
    oa = work.get("open_access") or {}
    topic = work.get("primary_topic") or {}
    authors = work.get("authorships") or []

    # Citation trajectory, as two numbers rather than a blob: what the paper
    # earned in the last two full years, and in the two before that. Their
    # ratio is momentum, and it is computed at rank time rather than here.
    counts = {c["year"]: c["cited_by_count"] for c in (work.get("counts_by_year") or [])}
    years = sorted(counts)
    recent = sum(counts[y] for y in years[-2:]) if years else 0
    prior = sum(counts[y] for y in years[-4:-2]) if len(years) > 2 else 0

    pct = work.get("citation_normalized_percentile") or {}

    return {
        "id": str(work.get("id", "")).rsplit("/", 1)[-1],
        "doi": (work.get("doi") or "").replace("https://doi.org/", ""),
        "title": work.get("title") or "",
        "date": work.get("publication_date") or "",
        "year": int(work.get("publication_year") or 0),
        "type": work.get("type") or "",
        "citations": int(work.get("cited_by_count") or 0),
        "fwci": float(work["fwci"]) if work.get("fwci") is not None else None,
        "pctile": (float(pct["value"]) if isinstance(pct, dict)
                   and pct.get("value") is not None else None),
        "cites_recent2": int(recent),
        "cites_prior2": int(prior),
        "references": int(work.get("referenced_works_count") or 0),
        "n_authors": len(authors),
        "is_oa": bool(oa.get("is_oa")),
        "oa_url": oa.get("oa_url") or "",
        "venue": source.get("display_name") or "",
        "venue_id": str(source.get("id") or "").rsplit("/", 1)[-1],
        "topic": topic.get("display_name") or "",
        "topic_id": str(topic.get("id") or "").rsplit("/", 1)[-1],
        "authors": ", ".join(
            (a.get("author") or {}).get("display_name") or "" for a in authors[:12]),
        "abstract": _abstract(work.get("abstract_inverted_index")),
        # Taxonomy, flattened to pipe-joined strings so one DuckDB column holds
        # them and a substring match is enough to filter on the page.
        "topics": " | ".join(
            (t.get("display_name") or "") for t in (work.get("topics") or [])[:3]),
        "keywords": " | ".join(
            (k.get("display_name") or "") for k in (work.get("keywords") or [])[:6]),
        "institutions": " | ".join(sorted({
            (inst.get("display_name") or "")
            for a in authors for inst in (a.get("institutions") or [])})[:6]),
        "countries": " | ".join(sorted({
            c for a in authors for c in (a.get("countries") or [])})[:6]),
        "funders": " | ".join(sorted({
            (g.get("funder_display_name") or "") for g in (work.get("grants") or [])})[:4]),
        # Outgoing citation edges, bare ids, space separated. A separate edge
        # table would be tidier, but this keeps the harvest to one write and a
        # substring match is enough to ask "does this cite that".
        "refs": " ".join(
            str(w).rsplit("/", 1)[-1] for w in (work.get("referenced_works") or [])),
    }


def harvest(since: int, limit: int = 0, kind: str = "article") -> list[dict]:
    filters = [f"primary_topic.id:{'|'.join(TOPICS)}",
               f"from_publication_date:{since}-01-01"]
    if kind:
        filters.append(f"type:{kind}")

    cursor, rows, pages = "*", [], 0
    while cursor:
        query = urllib.parse.urlencode({
            "filter": ",".join(filters),
            "select": FIELDS,
            "per-page": PER_PAGE,
            "cursor": cursor,
            "mailto": MAILTO,
        })
        payload = _get(f"{API}?{query}")
        time.sleep(PAUSE)
        results = payload.get("results") or []
        rows.extend(_row(w) for w in results)
        pages += 1
        cursor = (payload.get("meta") or {}).get("next_cursor")

        if pages == 1:
            total = (payload.get("meta") or {}).get("count", 0)
            print(f"{total:,} works match; paging {PER_PAGE} at a time")
        if pages % 10 == 0:
            print(f"  {len(rows):,} rows", flush=True)
        if limit and len(rows) >= limit:
            break
        if not results:
            break
    return rows


def write(rows: list[dict]) -> None:
    import duckdb

    con = duckdb.connect(DB)
    con.execute("DROP TABLE IF EXISTS works")
    con.execute("""
        CREATE TABLE works (
            id TEXT PRIMARY KEY, doi TEXT, title TEXT, date TEXT, year INTEGER,
            type TEXT, citations INTEGER, fwci DOUBLE, pctile DOUBLE,
            cites_recent2 INTEGER, cites_prior2 INTEGER, references_ INTEGER,
            n_authors INTEGER, is_oa BOOLEAN, oa_url TEXT, venue TEXT,
            venue_id TEXT, topic TEXT, topic_id TEXT, authors TEXT,
            abstract TEXT, topics TEXT, keywords TEXT, institutions TEXT,
            countries TEXT, funders TEXT, refs TEXT
        )""")
    con.executemany(
        "INSERT OR REPLACE INTO works VALUES ("
        + ",".join("?" * 27) + ")",
        [[r["id"], r["doi"], r["title"], r["date"], r["year"], r["type"],
          r["citations"], r["fwci"], r["pctile"], r["cites_recent2"],
          r["cites_prior2"], r["references"], r["n_authors"], r["is_oa"],
          r["oa_url"], r["venue"], r["venue_id"], r["topic"], r["topic_id"],
          r["authors"], r["abstract"], r["topics"], r["keywords"],
          r["institutions"], r["countries"], r["funders"], r["refs"]]
         for r in rows])
    con.commit()
    n = con.execute("SELECT count(*) FROM works").fetchone()[0]
    con.close()
    print(f"{n:,} works -> {DB}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--since", type=int, default=1990)
    ap.add_argument("--limit", type=int, default=0, help="stop early, for a probe")
    ap.add_argument("--type", default="article", help="'' for every work type")
    args = ap.parse_args()

    started = time.time()
    rows = harvest(args.since, args.limit, args.type)
    print(f"{len(rows):,} rows in {time.time() - started:.0f}s")
    write(rows)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
