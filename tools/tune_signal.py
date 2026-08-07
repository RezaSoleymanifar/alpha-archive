"""Choose the signal-set thresholds by measurement instead of by taste.

Four numbers decide which papers count as signal papers: how many distinct
seeds a paper must cite, how high its weighted score must be, how high it must
score to become a seed itself, and how fast a promoted seed's weight decays.
Picking them by eye is the same as judging the papers by eye, one level up.

So they get picked by a rule that nobody can lean on.

    Bury coins.       Hide a fifth of the verified OSAP predictors before the
                      first round. These are known signal papers, so a good
                      setting finds them again.
    Bury bottle caps. Take papers from the corporate-finance topic the corpus
                      dropped. These are known non-signals, so a good setting
                      leaves them out.
    Score.            recall on the hidden coins, minus the share of bottle
                      caps admitted.

Why the subtraction and not just one side. Maximising recall alone is won by a
setting that admits the entire corpus: every coin found, every cap too.
Minimising false admissions alone is won by a setting that admits nothing.
Only the gap between them rewards a setting that separates the two, which is
the only thing worth having.

Nothing here reads a paper. The coins were labelled by Chen and Zimmermann and
the caps by OpenAlex's own topic assignment, both before this file existed.

    uv run python tools/tune_signal.py
    uv run python tools/tune_signal.py --folds 5
"""

from __future__ import annotations

import argparse
import itertools
import json
import math
import os
import random
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))

DB = os.path.join(ROOT, "data", "corpus.duckdb")
SEEDS = os.path.join(ROOT, "data", "papers", "signal_seeds.json")
OUT = os.path.join(ROOT, "data", "signal_tuning.json")

# The grid. Deliberately coarse: a finer one would fit the holdout rather than
# the problem, and there are only about twenty-five coins to fit to.
GRID = {
    "min_seeds": [2, 3, 4],
    "min_score": [1.0, 1.5, 2.5, 4.0],
    "promote_score": [2.5, 3.0, 4.5, 99.0],   # 99 turns expansion off entirely
    "decay": [0.4, 0.6, 0.8],
}

# The topic whose papers stand in for "definitely not a signal paper". It was
# in the corpus until it was dropped for being corporate finance, which is
# exactly what makes it a fair negative: adjacent enough to be a real test,
# far enough that admitting it is a mistake.
NEGATIVE_TOPIC = "Capital Investment and Risk Analysis"

MAX_ROUNDS = 6


def load():
    """Edges, seeds and the negative set, read once and reused for every run."""
    import duckdb

    with open(SEEDS, encoding="utf-8") as fh:
        catalogue = [s["openalex_id"] for s in json.load(fh)["seeds"]]

    con = duckdb.connect(DB)
    have = {r[0] for r in con.execute("DESCRIBE works").fetchall()}
    if "refs" not in have:
        sys.exit("no citation edges: re-run tools/harvest_finance.py")

    total = con.execute("SELECT count(*) FROM works").fetchone()[0]
    edges = {pid: frozenset(str(refs).split())
             for pid, refs in con.execute(
                 "SELECT id, refs FROM works WHERE refs <> ''").fetchall()}
    negatives = {pid for (pid,) in con.execute(
        "SELECT id FROM works WHERE topic = ? AND refs <> ''",
        [NEGATIVE_TOPIC]).fetchall()}
    con.close()
    return edges, catalogue, negatives, total


def expand(edges, seed_ids, total, *, min_seeds, min_score, promote_score,
           decay) -> set:
    """Run the snowball to convergence and return everything it admitted."""
    seed_weight = {sid: 1.0 for sid in seed_ids}
    found: set = set()

    for rnd in range(1, MAX_ROUNDS + 1):
        freq: dict = {}
        for refs in edges.values():
            for sid in refs & seed_weight.keys():
                freq[sid] = freq.get(sid, 0) + 1

        idf = {sid: math.log(total / max(freq.get(sid, 0), 1)) * w
               for sid, w in seed_weight.items()}
        mean = sum(idf.values()) / max(1, len(idf))
        if mean <= 0:
            break

        promoted, fresh = set(), 0
        for pid, refs in edges.items():
            if pid in found or pid in seed_weight:
                continue
            hits = refs & seed_weight.keys()
            if len(hits) < min_seeds:
                continue
            value = sum(idf[sid] for sid in hits) / mean
            if value >= min_score:
                found.add(pid)
                fresh += 1
                if value >= promote_score:
                    promoted.add(pid)

        if not promoted or fresh < 25:
            break
        for pid in promoted:
            seed_weight[pid] = decay ** rnd
    return found


def cost(found: set, hidden: list, negatives: set) -> dict:
    """The objective: coins found, minus caps admitted.

    Both terms are rates rather than counts, because there are a few dozen
    coins and a few thousand caps and a difference of counts would be decided
    entirely by the caps.
    """
    recall = sum(1 for sid in hidden if sid in found) / max(1, len(hidden))
    leak = len(found & negatives) / max(1, len(negatives))
    return {"recall": recall, "leak": leak, "score": recall - leak,
            "admitted": len(found)}


def sweep(folds: int = 4) -> list[dict]:
    edges, catalogue, negatives, total = load()
    print(f"{len(edges):,} papers with edges, {len(catalogue)} verified seeds, "
          f"{len(negatives):,} negatives\n")

    rng = random.Random(20260807)
    shuffled = catalogue[:]
    rng.shuffle(shuffled)
    # Cross-validation, because a single split of twenty-five coins is noise.
    splits = [shuffled[i::folds] for i in range(folds)]

    results = []
    combos = list(itertools.product(*GRID.values()))
    for i, combo in enumerate(combos, 1):
        params = dict(zip(GRID, combo))
        scores = []
        for hidden in splits:
            visible = [s for s in catalogue if s not in set(hidden)]
            found = expand(edges, visible, total, **params)
            scores.append(cost(found, hidden, negatives))

        mean = {k: sum(s[k] for s in scores) / len(scores) for k in scores[0]}
        results.append({**params, **mean})
        print(f"  [{i:3}/{len(combos)}] {params}  "
              f"recall {mean['recall']:.2f}  leak {mean['leak']:.2f}  "
              f"score {mean['score']:+.3f}  admitted {mean['admitted']:.0f}")

    results.sort(key=lambda r: -r["score"])
    with open(OUT, "w", encoding="utf-8", newline="\n") as fh:
        json.dump({"negative_topic": NEGATIVE_TOPIC, "folds": folds,
                   "results": results}, fh, indent=1)

    best = results[0]
    print(f"\nbest: {best}")
    print(f"\nIt finds {100 * best['recall']:.0f}% of the held-out verified "
          f"predictors and admits {100 * best['leak']:.1f}% of the "
          f"corporate-finance papers, ending with {best['admitted']:.0f} "
          f"papers in the signal set.")
    print(f"full grid -> {OUT}")
    return results


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--folds", type=int, default=4)
    args = ap.parse_args()
    sweep(args.folds)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
