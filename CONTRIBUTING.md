# Contributing

Alpha Archive rebuilds published quantitative finance papers and checks the
result against the numbers the paper printed.

**Nothing here is proven yet.** As of August 2026: 348 papers read, 95 judged
reproducible on free data, and **zero fully reproduced**. That is the honest
state and it is the reason to contribute rather than a reason not to. The
interesting work is all in front of us.

## What a contribution is

Pick a paper from [the shortlist](https://rezasoleymanifar.github.io/alpha-archive/),
rebuild it, and report what landed and what did not. That is it. A replication
that fails is as valuable as one that succeeds, and considerably more common.

## The one rule

**Write the criterion down before you run anything.**

Every number the paper prints becomes an artifact with a tolerance, declared in
advance, in code, frozen. Then you build. Then you see what happened.

This is not decoration. On the first replication in this repo the bar was set at
0.6 correlation, the result came back 0.74, and it got called validated. Worse,
0.6 had been chosen *after* 0.9 turned out to be unreachable. That is grading
your own exam, and the whole project is worthless if it happens once in public.

So `alpha_archive/artifacts.py` holds frozen dataclasses. If you find yourself
widening a tolerance because the result missed, stop. The implementation changes,
not the bar. Record the miss. A miss is a finding.

## How a replication is scored

Per artifact, not per paper. A paper prints eleven numbers; matching six of them
is "six of eleven", not one adjective that credits neither half.

| State | Means |
|---|---|
| `REPRODUCED` | rebuilt, inside the tolerance you declared first |
| `MISSED` | rebuilt, outside it |
| `NOT_ATTEMPTED` | nobody has built this one yet |
| `UNOBTAINABLE` | the fixture needed to check it cannot be got |

A paper counts as fully reproduced only when every artifact is. That is
deliberately hard and currently true of nothing.

## The worked example

`notebooks/2606.04153_sign_and_magnitude.ipynb`. Read it before starting.

It reproduces the paper's benchmark to within a cent, matches its correlation
table, then builds the actual model and **misses the headline by a third**. All
three outcomes are in the same notebook, which is the shape a replication should
have.

It also contains the two lessons that cost the most time:

**Look at the artifact, do not transcribe it.** The notebook embeds the paper's
own pages rendered from the PDF, beside our output. Two of six transcribed rows
turned out to be wrong, and neither was visible until the page was on screen.
One of them, maximum drawdown, is printed as a fraction rather than a percent,
so a perfect match looked like a hundredfold error.

**Sweep the free parameter.** The paper's headline is $181.68 at k=3. Sweeping k
gives a range from $104 to $158 in our hands. The paper is not hiding this, it
plots the whole curve, but a replication that reports only the point the paper
chose has learned nothing about how stable the result is.

## Building one

```
alpha_archive/criteria/<paper>.py        the frozen artifacts, written first
alpha_archive/replications/<paper>.py    the implementation
notebooks/<paper>.ipynb                  the walkthrough, generated from a .py
data/artifacts/<paper>.json              the scored result
```

Notebooks are generated from a Python file, not hand-edited, so prose and code
cannot drift and a rerun cannot leave stale output beside edited text. See
`notebooks/build_notebook.py`.

Data comes from [Vintage](https://github.com/RezaSoleymanifar/vintage), which
serves eighteen free sources with point-in-time dates. If your paper needs
something Vintage lacks, that is an issue on Vintage, not a reason to scrape.

## Writing the notebook

It is an implementation document, not an essay. The paper's exhibits, rebuilt,
readable straight against the printed ones without translating first.

- Lead with a number the reader can check, not with context. The benchmark match
  is in cell four for a reason.
- Say only what a working quant needs. The paper spends pages on copula families;
  a desk wants the signal, the costs, and the return.
- End with coverage: how many published numbers you landed on, as a percentage,
  and which ones you did not. A notebook that runs cleanly tells nobody how much
  of the paper it accounts for.

## Judging a paper

Triage is the other contribution: reading a PDF and deciding whether its claims
are reproducible on free data. `tools/digest.py` reduces a paper to the sections,
tables and figure pages a verdict turns on. `data/triage/ledger.json` is the
append-only record, drops included, because a drop records what the archive
cannot reach and that is a map worth having.

766 papers are indexed and unjudged.

## The bar

Say what happened. If it missed, it missed, with the observed value written down
beside the published one. The archive is only worth anything if a reader can
trust the failures, because that is the only reason to trust the successes.
