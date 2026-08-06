# Selection and ranking methodology

What gets indexed, what gets rejected, and what puts a paper at the top. Written
down because a filter nobody can argue with is a prejudice, not a method.

Everything here is executable: `tools/fetch_papers.py` applies it, and
`tools/audit_universe.py` re-runs it over whatever is currently indexed and
prints the ledger, including the rejects it was closest to keeping.

---

## 1. The universe

Two halves, deliberately equal in size, drawn per time window so every window is
populated rather than only the oldest one.

| Half | Where | How |
|---|---|---|
| Preprints | arXiv q-fin | OpenAlex source `S4306400194`, restricted to the Finance subfield |
| Published | SSRN, NBER, and 19 journals from JF/JFE/RFS down to the Journal of Fixed Income | OpenAlex by ISSN, plus NBER's source id |

Both halves are restricted to seven OpenAlex topics, Financial Markets and
Investment Strategies, Market Dynamics and Volatility, Stochastic Processes and
Financial Applications, Financial Risk and Volatility Modeling, Complex Systems
and Time Series, Economic Theories and Models, Credit Risk. Without that
restriction a citation ranking over finance journals returns development
economics and tax policy, which is true and useless.

Windows: 30 days, 12 months, 5 years, 10 years, all time. A paper found in the
30-day cohort is also in the 12-month one; the page assigns windows from each
card's date, so the index stores one row per paper.

Sources are catalogued in [sources.md](sources.md), including the ones we
cannot reach and why.

## 2. The three gates

A paper is indexed only if it passes all three, in order. The gate that rejected
it is recorded, so the reject list is reviewable.

### Gate 1, does it name a mechanism?

The title, or an abstract of at least 260 characters, must name a signal, a
portfolio rule, or a forecast: cross-sections of returns, predictability,
momentum, reversal, carry, volatility modelling, hedging, option pricing,
execution, liquidity, machine learning applied to any of them.

Rejected here: governance, agency theory, disclosure, executive pay, auditing,
litigation, tax policy, bank regulation, microfinance, financial literacy,
household finance, surveys, climate and ESG, monetary transmission, inequality,
labour, housing, pandemics. Those are finance. They are not a position.

### Gate 2, can a reader get the data?

The archive's promise is that a stranger can rerun the result. Free and
fetchable today: daily OHLCV, SEC filings and XBRL, FRED and ALFRED macro with
first releases, Ken French factors, FINRA short volume, Coinbase crypto.

Rejected here: tick and intraday data, limit order books, TAQ, option chains and
implied-volatility surfaces, OptionMetrics, analyst estimates and I/B/E/S, 13F
and institutional holdings, securities lending, TRACE, fund flows, hedge fund
databases, earnings call transcripts, satellite and card-panel alternative data.

This gate is about *our* data, not the paper's quality. It is the honest reason
a good microstructure paper is absent.

### Gate 3, is the deliverable a position or a proof?

Codeable is not the same as useful. A convergence theorem for a finite
difference scheme can be implemented and gives a desk nothing.

Rejected here: existence and uniqueness, viscosity solutions, mean field games,
abstract stochastic control, utility maximisation as an axiom system, numerical
convergence analysis, discretisation error, general equilibrium existence.

Roughly four papers in five fail one of these three. That ratio is the point:
the citation leaderboard for finance is dominated by work a quant cannot use.

## 3. Ranking

Four orderings ship in the page; switching is a DOM reorder, not a request.

### Impact, the default

OpenAlex `citation_normalized_percentile`: a paper's citation count expressed
as a percentile **against papers of the same field and year**. Jegadeesh and
Titman (1993) score 0.9947 and carry `is_in_top_1_percent`; a strong 2026 paper
can match that inside its own cohort while holding twenty citations.

This is the metric that fixes the flaw in raw counts. Sorting by lifetime
citations is sorting by age, it guarantees an index of pre-2015 papers and
buries everything published while you were reading.

### Most cited

Raw `cited_by_count`. Kept because it is the number people quote, and because
within a fixed window it is a fair comparison.

### Trending

Citations per month since publication: `cited_by_count / max(months, 1)`. A
crude velocity, but it is the one metric that lets a 2024 paper beat a 1993 one
without normalisation tables.

### Newest

Publication date, descending. Present because for the 30-day window every other
ordering degenerates. Nothing published last month has been cited, and the page
says so instead of presenting zeros as a ranking.

### Tie-break and second signal

Semantic Scholar's `influentialCitationCount`, citations where the citing paper
actually builds on the work, rather than name-checking it. Jegadeesh and Titman:
1,017 influential of 11,228 total. Free, no key, and fetched in batches of 500.

### What we do not use

- **Downloads.** arXiv does not publish per-paper counts. SSRN shows them on the
  page and blocks clients that ask, and taking them would mean scraping.
- **Journal impact factor.** Ranks the venue, not the paper.
- **GitHub stars.** What Papers With Code used, but almost no finance paper has
  a repository, so the signal is missing exactly where the index needs it.
- **Altmetric.** Not free at this volume.

## 4. Replication status

Separate from ranking, and never mixed into it. A card shows a result only where
we have actually run the paper: what it claimed, what we measured, and whether
the gap survives the paper's own thresholds. Method for that lives in
[methodology.md](methodology.md), point-in-time panels, costs charged on
turnover, DSR against the specs tried, PBO via CSCV where the design supports it.

Everything else links out and says nothing more. A citation is attention. A
replication is evidence. The index is careful not to spend one as the other.

## 5. Auditing the filter

```bash
uv run python tools/audit_universe.py --write
```

Prints the survival rate, the rejects grouped by gate, and the twenty
most-cited rejections: the judgement calls, the place to look first when the
filter is wrong. `--write` records the same table in [audit.md](audit.md).
