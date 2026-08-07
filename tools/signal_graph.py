"""Find the signal papers by who they build on, not by what they are called.

The problem this solves. A quant does not want all of finance. They want the
papers that propose or test a tradeable predictor, and that set cannot be
picked out by topic, venue or keyword: "Financial Markets and Investment
Strategies" holds both Fama-French and a survey of ETF fee structures, and no
journal publishes only signals.

The method, in one line: a paper that cites several known signal papers is
almost certainly a signal paper, provided the seeds it cites are ones that few
other papers cite.

    seeds     127 predictors from Chen and Zimmermann's Open Source Asset
              Pricing catalogue, each a published cross-sectional signal with
              its source paper. Somebody else verified these, by hand, and
              published the list.
    corpus    every finance paper harvested by tools/harvest_finance.py.
    edges     `referenced_works` from OpenAlex, which is each paper's outgoing
              citation list.

Why the weighting matters, and it is the whole method. Roughly three thousand
papers in this corpus cite Fama-French (1993), so citing it says nothing at all
about whether a paper is a signal paper. Forty cite Sloan's accruals paper, so
citing that says a great deal. Each seed is therefore weighted by inverse
document frequency -- log(corpus size / how many corpus papers cite it) -- and a
paper's score is the sum of the weights of the seeds it cites. That is the same
arithmetic a search engine uses to decide that "the" is worthless and
"accruals" is not.

Two guards against the obvious failure. A paper must cite at least three
distinct seeds, so one lucky edge cannot admit it. And its score must clear a
threshold, so three of the most common seeds together still will not.

Nothing here reads a paper or asks a model anything. It is citation arithmetic
over a graph somebody else published.

    uv run python tools/signal_graph.py --resolve      # seeds -> OpenAlex ids
    uv run python tools/signal_graph.py --score        # score the corpus
"""

from __future__ import annotations

import argparse
import json
import math
import os
import sys
import time
import urllib.parse
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(ROOT, "data", "corpus.duckdb")
OSAP = os.path.join(ROOT, "data", "papers", "osap.json")
SEEDS = os.path.join(ROOT, "data", "papers", "signal_seeds.json")

API = "https://api.openalex.org/works"
MAILTO = "reza@soleymanifar.com"

# A paper must reach this many distinct seeds before it is considered at all.
# One shared reference is a coincidence; three is a lineage.
MIN_SEEDS = 3

# And its weighted score must clear this. The unit is a seed of average
# rarity, so 1.5 means "three common seeds is not enough, three uncommon ones
# is". Set by looking at where the known signal papers fall, not by taste.
MIN_SCORE = 1.5

# --------------------------------------------------------------- expansion
#
# A paper that clears the bar is itself a signal paper, so papers citing *it*
# are candidates too. Running that round after round is how the set grows past
# what 127 hand-verified predictors can reach on their own.
#
# Two things keep it from drifting into all of finance.
#
# The promotion bar is higher than the inclusion bar. Being in the set is a
# claim about one paper; becoming a seed is a claim about everything that will
# be admitted through it, so it takes more evidence.
PROMOTE_SCORE = 3.0

# And every generation's seeds are worth less than the last. Generation zero is
# Chen and Zimmermann's hand-verified list and is worth full weight; a seed
# promoted three rounds later is worth a fifth of that. Without the decay one
# bad promotion in round one is indistinguishable from a verified predictor by
# round three, and the set walks away from signals into whatever is adjacent.
GENERATION_DECAY = 0.6

# Stop when a round adds almost nothing, or after this many rounds regardless.
MAX_ROUNDS = 6
MIN_NEW_PER_ROUND = 25


def _get(url: str, tries: int = 6) -> dict:
    for attempt in range(tries):
        try:
            req = urllib.request.Request(
                url, headers={"User-Agent": f"alpha-archive ({MAILTO})"})
            with urllib.request.urlopen(req, timeout=60) as fh:
                return json.load(fh)
        except urllib.error.HTTPError as exc:
            if attempt == tries - 1:
                raise
            after = exc.headers.get("Retry-After") if exc.headers else None
            wait = float(after) if after and str(after).isdigit() else 5 * (attempt + 1)
            print(f"  HTTP {exc.code}, waiting {wait:.0f}s", file=sys.stderr, flush=True)
            time.sleep(wait)
        except Exception:                                # noqa: BLE001
            if attempt == tries - 1:
                raise
            time.sleep(2 ** attempt)
    return {}


def resolve_seeds() -> list[dict]:
    """Turn the OSAP catalogue into OpenAlex ids, by DOI where there is one.

    OSAP names a source paper per predictor but does not carry an OpenAlex id,
    so each has to be looked up. Title search is a last resort and is recorded
    as such: a seed matched on title is a seed that might be the wrong paper,
    and the file says which are which so a bad match can be found later.
    """
    with open(OSAP, encoding="utf-8") as fh:
        predictors = json.load(fh)["predictors"]

    seeds, seen = [], set()
    for p in predictors:
        doi, title = (p.get("doi") or "").strip(), (p.get("title") or "").strip()
        authors = (p.get("authors") or "").strip()
        if doi and doi.lower() != "none":
            url = (f"{API}/doi:{urllib.parse.quote(doi)}"
                   f"?select=id,title,cited_by_count&mailto={MAILTO}")
            how = "doi"
        else:
            # The predictor's own name is not the paper's title, so the search
            # is the name plus the authors, which is what OSAP records.
            query = urllib.parse.quote(f"{title} {authors}")
            url = (f"{API}?search={query}&per-page=1"
                   f"&select=id,title,cited_by_count&mailto={MAILTO}")
            how = "search"

        try:
            payload = _get(url)
        except Exception as exc:                         # noqa: BLE001
            print(f"  no match for {title!r}: {exc}", file=sys.stderr)
            continue
        work = payload if how == "doi" else (payload.get("results") or [None])[0]
        if not work:
            continue

        oid = str(work.get("id", "")).rsplit("/", 1)[-1]
        if not oid or oid in seen:
            continue
        seen.add(oid)
        seeds.append({"openalex_id": oid, "predictor": title,
                      "matched_title": work.get("title") or "",
                      "matched_by": how,
                      "cited_by_count": int(work.get("cited_by_count") or 0)})
        time.sleep(0.12)

    os.makedirs(os.path.dirname(SEEDS), exist_ok=True)
    with open(SEEDS, "w", encoding="utf-8", newline="\n") as fh:
        json.dump({"source": "Open Source Asset Pricing (Chen & Zimmermann)",
                   "seeds": seeds}, fh, indent=1)
    by_doi = sum(1 for s in seeds if s["matched_by"] == "doi")
    print(f"{len(seeds)} seeds resolved ({by_doi} by DOI, "
          f"{len(seeds) - by_doi} by title search) -> {SEEDS}")
    return seeds


def _round(edges: dict, seed_weight: dict, total: int) -> dict:
    """One pass: score every paper by the rarity-weighted seeds it cites.

    `seed_weight` carries each seed's generation discount, so a verified
    predictor and a seed promoted three rounds ago do not count the same.
    """
    freq: dict[str, int] = {sid: 0 for sid in seed_weight}
    for refs in edges.values():
        for sid in refs & seed_weight.keys():
            freq[sid] += 1

    # Inverse document frequency, floored at one so a seed nobody cites does
    # not divide by zero and does not become infinitely valuable either. The
    # generation discount multiplies through it.
    idf = {sid: math.log(total / max(freq[sid], 1)) * seed_weight[sid]
           for sid in seed_weight}
    mean = sum(idf.values()) / max(1, len(idf))

    scored: dict[str, tuple[int, float]] = {}
    for paper_id, refs in edges.items():
        hits = refs & seed_weight.keys()
        if len(hits) < MIN_SEEDS:
            continue
        value = sum(idf[sid] for sid in hits) / max(mean, 1e-9)
        if value >= MIN_SCORE:
            scored[paper_id] = (len(hits), value)
    return {"scored": scored, "freq": freq, "idf": idf}


def score(holdout: float = 0.0) -> None:
    """Grow the signal set from the verified seeds, round after round.

    With `holdout`, that fraction of the verified seeds is hidden before the
    first round and the expansion is measured on how many of them it finds
    again. That is the only honest test available here: the hidden seeds are
    known signal papers, so rediscovering them is evidence the method works and
    failing to is evidence it does not.
    """
    import duckdb
    import random

    with open(SEEDS, encoding="utf-8") as fh:
        catalogue = {s["openalex_id"]: s["predictor"] for s in json.load(fh)["seeds"]}
    if not catalogue:
        sys.exit("no seeds: run --resolve first")

    hidden: set[str] = set()
    if holdout > 0:
        ids = sorted(catalogue)
        random.Random(20260807).shuffle(ids)
        hidden = set(ids[:int(len(ids) * holdout)])
        print(f"holding back {len(hidden)} of {len(catalogue)} verified seeds\n")

    con = duckdb.connect(DB)
    have = {r[0] for r in con.execute("DESCRIBE works").fetchall()}
    if "refs" not in have:
        sys.exit("no citation edges in the corpus: re-run tools/harvest_finance.py")

    total = con.execute("SELECT count(*) FROM works").fetchone()[0]
    edges = {pid: set(str(refs).split())
             for pid, refs in con.execute(
                 "SELECT id, refs FROM works WHERE refs <> ''").fetchall()}

    seed_weight = {sid: 1.0 for sid in catalogue if sid not in hidden}
    generation = {sid: 0 for sid in seed_weight}
    found: dict[str, tuple[int, float, int]] = {}

    for rnd in range(1, MAX_ROUNDS + 1):
        result = _round(edges, seed_weight, total)
        fresh = {pid: v for pid, v in result["scored"].items()
                 if pid not in found and pid not in seed_weight}
        for pid, (hits, value) in fresh.items():
            found[pid] = (hits, value, rnd)

        promoted = {pid for pid, (_, value) in fresh.items()
                    if value >= PROMOTE_SCORE}
        print(f"round {rnd}: {len(fresh):,} new papers, "
              f"{len(promoted):,} promoted to seeds "
              f"(seed set now {len(seed_weight) + len(promoted):,})")

        if not promoted or len(fresh) < MIN_NEW_PER_ROUND:
            break
        for pid in promoted:
            seed_weight[pid] = GENERATION_DECAY ** rnd
            generation[pid] = rnd

    if hidden:
        # The test. A hidden seed counts as recovered if the expansion admitted
        # it on the strength of the seeds that were left visible.
        recovered = sum(1 for sid in hidden if sid in found)
        print(f"\nrecovered {recovered} of {len(hidden)} held-out verified "
              f"seeds ({100.0 * recovered / max(1, len(hidden)):.0f}%)")

    con.execute("DROP TABLE IF EXISTS signal_score")
    con.execute("CREATE TABLE signal_score (id TEXT PRIMARY KEY, "
                "seeds_hit INTEGER, signal DOUBLE, round INTEGER)")
    con.executemany("INSERT INTO signal_score VALUES (?, ?, ?, ?)",
                    [(pid, h, round(v, 4), r) for pid, (h, v, r) in found.items()])
    con.commit()

    print(f"\n{len(found):,} signal papers from a corpus of {total:,} "
          f"({100.0 * len(found) / max(1, total):.1f}%)")

    top = con.execute("""
        SELECT s.signal, s.seeds_hit, s.round, w.citations, w.year,
               w.title[1:56] AS title
        FROM signal_score s JOIN works w USING (id)
        ORDER BY s.signal DESC LIMIT 15""").df()
    print("\nhighest-scoring:")
    print(top.to_string(index=False))
    con.close()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--resolve", action="store_true", help="seeds -> OpenAlex ids")
    ap.add_argument("--score", action="store_true", help="score the corpus")
    ap.add_argument("--holdout", type=float, default=0.0,
                    help="hide this fraction of verified seeds and measure "
                         "how many the expansion finds again")
    args = ap.parse_args()

    if args.resolve:
        resolve_seeds()
    if args.score or not args.resolve:
        score(args.holdout)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
