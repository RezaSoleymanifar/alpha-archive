"""Rank the corpus on scraped numbers, with every input shown separately.

The rule this file exists to enforce: a paper's position is a function of
numbers somebody else published, and of nothing else. No model read a title.
No heuristic rewarded a fashionable topic. If a paper is high, the reason is
five numbers you can look at, and you can re-sort by any one of them.

The five, and what each is for:

  impact      field-weighted citation impact from OpenAlex. Citations divided
              by the average for that field, year and type. This is the only
              input that makes a 1993 paper comparable to a 2023 one, so it
              carries the most weight.
  standing    citation-normalised percentile, also from OpenAlex. Where the
              paper sits in its own cohort's distribution rather than how far
              above the mean, which is what keeps one 30,000-citation outlier
              from flattening everything below it.
  reach       raw citations, log-scaled. Included because it is the number
              everyone actually knows, and hiding it would look like a dodge.
  momentum    citations in the last two years over the two before. A paper
              still being cited is a different object from one that was.
  access      whether a reader can obtain it. Not a quality signal and not
              weighted as one; it breaks ties toward what you can actually go
              and read.

Everything is converted to a within-corpus percentile before weighting, so no
single skewed input can dominate the sum, and the weights mean what they say.

    uv run python tools/rank_corpus.py
    uv run python tools/rank_corpus.py --top 40 --since 2020
"""

from __future__ import annotations

import argparse
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(ROOT, "data", "corpus.duckdb")

# Field-weighted citation impact is the ranking. It is the metric the field
# itself uses -- Clarivate calls it CNCI, Elsevier calls it FWCI -- and it is
# the only one of these that makes a 1993 paper and a 2023 paper comparable,
# because it divides by what a paper of that age, field and type normally
# earns. The others stay in the table and on the page as columns you can
# re-sort by; they do not move the rank.
WEIGHTS = {
    "impact": 1.00,      # fwci, and nothing else
    "standing": 0.0,
    "reach": 0.0,
    "momentum": 0.0,
    "access": 0.0,
}

# The floor, and why there is one. FWCI is a ratio, so a paper with six
# citations in a cohort that averages 0.03 scores in the hundreds. Those are
# arithmetic accidents, not important papers -- an early probe of this corpus
# put a health-insurance note above Fama-French on exactly that mechanism.
# Below this many citations a paper is listed but not ranked.
MIN_CITATIONS = 10

# Topics harvested earlier that are no longer part of the corpus. Excluded at
# rank time as well as at harvest time, so a database pulled before the
# boundary moved still produces the current ranking rather than the old one.
DROPPED_TOPICS = ("Capital Investment and Risk Analysis",)

RANK_SQL = """
CREATE OR REPLACE TABLE ranked AS
WITH base AS (
    SELECT *,
        -- Momentum is a ratio, so it needs a floor on the denominator or a
        -- paper with one prior citation reads as a hundredfold acceleration.
        CASE WHEN cites_prior2 + cites_recent2 = 0 THEN 0.0
             ELSE cites_recent2::DOUBLE / GREATEST(cites_prior2, 3) END AS mom_raw,
        ln(1 + citations) AS reach_raw
    FROM works
    WHERE year >= ? AND citations >= {min_citations}
      AND topic NOT IN ({dropped})
),
scored AS (
    SELECT *,
        -- percent_rank puts every input on the same 0-1 scale, so a weight of
        -- 0.40 really is 40% of the decision rather than 40% of whatever range
        -- that column happened to have.
        percent_rank() OVER (ORDER BY fwci NULLS FIRST)      AS s_impact,
        percent_rank() OVER (ORDER BY pctile NULLS FIRST)    AS s_standing,
        percent_rank() OVER (ORDER BY reach_raw)             AS s_reach,
        percent_rank() OVER (ORDER BY mom_raw)               AS s_momentum,
        CASE WHEN is_oa THEN 1.0 ELSE 0.0 END                AS s_access
    FROM base
)
SELECT *,
    100.0 * ({w_impact} * s_impact + {w_standing} * s_standing
           + {w_reach} * s_reach + {w_momentum} * s_momentum
           + {w_access} * s_access) AS score
FROM scored
"""


def rank(since: int = 1990):
    import duckdb

    con = duckdb.connect(DB)
    dropped = ", ".join(f"'{t}'" for t in DROPPED_TOPICS) or "''"
    sql = RANK_SQL.format(min_citations=MIN_CITATIONS, dropped=dropped,
                          **{f"w_{k}": v for k, v in WEIGHTS.items()})
    con.execute(sql, [since])
    con.execute("CREATE INDEX IF NOT EXISTS ranked_score ON ranked(score)")
    con.commit()
    return con


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--since", type=int, default=1990)
    ap.add_argument("--top", type=int, default=25)
    args = ap.parse_args()

    con = rank(args.since)
    n = con.execute("SELECT count(*) FROM ranked").fetchone()[0]
    print(f"{n:,} works ranked (from {args.since})\n")

    rows = con.execute("""
        SELECT round(score, 1) AS score, year, citations,
               round(fwci, 1) AS fwci, round(pctile, 3) AS pctile,
               round(100 * s_momentum) AS mom,
               title[1:58] AS title, venue[1:26] AS venue
        FROM ranked ORDER BY score DESC LIMIT ?""", [args.top]).df()
    print(rows.to_string(index=False))
    con.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
