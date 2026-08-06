# Next steps

**Status: none of this is started.** Written 2026-08-05 after Vintage shipped, so the
overlap between the two repos is recorded while it is fresh. Nothing here is scheduled.

---

## 1. The reproducibility hole — do this first

`alpha_archive/data/prices.py` resolves its price panel like this:

```python
candidates = [os.environ.get("GRAIN_DATA"),
              Path.home() / "dev" / "investor-copilot", ...]
```

It reads a parquet dump from a **different, private repo on one laptop**, and falls back to
yfinance when that is missing. `alpha_archive/data/fundamentals.py` has the same shape.

The README promises *"Every quantitative finance paper, replicated. Open. Verified."* and the
comparison table against Hou–Xue–Zhang claims **"Open code, open results, crowdsourced
verification"** where HXZ is **"Closed source-of-truth"**.

Those two things cannot both be true. Today nobody outside this machine can reproduce a single
published result, which is the one claim the whole project rests on. HXZ at least shipped a
paper describing its data. This ships a path to a directory that does not exist for anyone else.

**Fix:** replace the data layer with [Vintage](https://github.com/RezaSoleymanifar/vintage)
(`pip install vintage-mcp`). Anyone can then rerun any paper with no local corpus, and the
figures come from SEC EDGAR and FRED directly rather than a parquet snapshot of unknown vintage.

That is also the honest answer to the obvious reviewer question — *where did your data come
from, and was it point-in-time?* Right now there is no good answer.

## 2. Delete the duplicated engine

Both repos independently grew the same three modules:

| Alpha Archive | Vintage | Keep |
|---|---|---|
| `backtest/dsr.py` (111 lines) | `engine/honesty.py` (138) | Vintage — it carries a session trial ledger |
| `backtest/runner.py` (256) | `engine/backtest.py` (216) | Undecided; see below |
| `data/prices.py` (98) | `sources/yahoo.py` (98) | Vintage |

`runner.py` is the harder call. It has an IC report and a verdict string that Vintage does not,
and Vintage has a `known_at`-indexed panel that `runner.py` does not. The merge is probably
"Vintage supplies the panel and the deflation, Alpha Archive keeps the IC report and the
replication score" rather than either one winning outright.

Do not start this before §1. Deduplicating around a data layer that is about to be replaced is
wasted work.

## 3. Make the DSR cumulative across papers

The README already promises this — *"Cumulative DSR adjustment across all papers ever tested"* —
and it is the single most defensible claim in the project. It is also not implemented: `dsr.py`
takes `n_trials` as an argument, so each paper is deflated against its own trial count rather
than against every specification the archive has ever run.

Once the count is cumulative and persisted, the bar rises for every subsequent paper
automatically, and the archive becomes something no individual replicator can reproduce by
hand. That is the moat. It needs a table, not an algorithm.

## 4. Publish the failures loudly

The interesting artifact is not the replicated papers. It is a public, permanently updating
leaderboard of anomalies that **did not** survive, with the gap between claimed and measured
Sharpe. HXZ got its reputation from reporting that ~64% failed, not from the 36% that worked.

Requires §1 first, or the failures are unverifiable and the claim is worse than not making it.

## 5. Say what the sample cannot cover

SEC XBRL only reaches back to roughly 2009. Price-based anomalies replicate over decades;
accounting-based ones do not. Every published result needs its usable sample window stamped on
it, because a "failed replication" run on 2009–2026 against a paper sampled 1963–2000 is not a
failed replication — it is a different experiment.

---

## Not doing

- **Competing with LEAN or Nautilus Trader on execution realism.** Different problem, already
  solved. Alpha Archive answers "is the signal real", not "would the order have filled".
- **Reselling paid data.** Redistribution licensing kills it before the first user.
