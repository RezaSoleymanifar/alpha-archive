# Why the published anomalies are not the target

Written 2026-08-07, after four attempts and one honest pass.

The obvious plan was to replicate the canon. Open Source Asset Pricing publishes
331 predictors with each paper's claimed return, t-statistic and sample window,
plus a definition precise enough to code from, which means the classics are
reachable without opening a paywalled PDF. That plan is now closed, and this
records why so nobody reopens it by accident.

## What was tried

Four price-only predictors were implemented and calibrated: run on the paper's
own sample years and checked against the paper's own numbers.

| Predictor | Published t | Reproduced t | Outcome |
|---|---|---|---|
| IdioVol3F | 3.10 | -2.96 | opposite sign |
| MaxRet | 2.83 | -3.21 | opposite sign |
| VolSD | 3.56 | -2.83 | wrong signal entirely, it is volume variance |
| Mom12m | 3.74 | see below | direction reproduced, size did not |

The first three looked like bugs and one was: `VolSD` is Volume Variance, and
what had been written was the volatility of returns. The sign was also being
hardcoded per function rather than read from SignalDoc's own `Sign` column,
which had `Beta` inverted.

## The measurement that settled it

Chen and Zimmermann publish their actual monthly long-short return series, not
only the summary numbers. That is the right thing to calibrate against: a single
t-statistic recomputed on a different universe cannot separate a coding error
from a sample difference, while a series of a thousand months can.

Momentum, against their own series:

| | |
|---|---|
| Overlapping months | 420, January 1990 to December 2024 |
| Correlation | **0.590** |
| Their mean monthly return | +0.767% |
| Our mean monthly return | +0.120% |

The direction reproduces. Our portfolio moves when theirs moves, month after
month, for thirty-five years. The size does not: we earn roughly a sixth of what
they earn.

## Why that gap does not close

These anomalies were measured on the full CRSP cross-section. Momentum, low
volatility, maximum return and idiosyncratic volatility all concentrate in small
and micro-cap names. Our universe is a large-cap panel, because that is what
free daily price history covers.

The missing return is the missing stocks. No amount of care in the
implementation recovers it, and CRSP costs money. A correlation of 0.59 with a
sixth of the return is the best this approach can do, permanently.

## What that would have meant for the site

Publishing it would have produced a scoreboard of near-misses: every classic
listed, every one marked "direction yes, size no". That is a page about our data
budget rather than about the papers, and it teaches a reader nothing they can
use.

## What replaced it

arXiv q-fin papers. Much of that work already runs on free data, often the same
sources this project can reach, which means an exact match is possible rather
than approachable. An exact match is the only result worth a tick, and a failure
against a paper that used free data is a real finding rather than an artefact of
what we could not afford.

The OSAP claim table stays in Vintage as `openap:`, and their return series as
`openapret:`, because both are useful for checking any implementation. They are
simply no longer what the archive is trying to replicate.
