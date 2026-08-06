# Alpha Archive

> **Every quantitative finance paper, replicated. Open. Verified.**

Alpha Archive is an automated signal-extraction engine. It ingests academic papers from arXiv / SSRN / NBER, uses LLMs to extract the trading signal specification, runs each through a standardized backtest pipeline, and publishes the results.

## Why this exists

- **400+ "factors"** have been published in academic finance journals. Most decay or never worked. Nobody knows which to trust.
- **Replication is manual today**, sites like AlphaArchitect do it by hand, ~50 papers/year.
- **Quantpedia charges $300/yr** for static curated database with no live re-runs.
- **Nothing exists** that's: (1) automated, (2) free, (3) live-updating, (4) standardized methodology, (5) crowdsourced.

LLMs can now read papers, extract signal specifications, and write the implementation code. Alpha Archive is the productized version of that loop.

## What it does

```
arXiv / SSRN / NBER feed   →   LLM triage (is this tradable?)
                           →   LLM extracts spec (formula, data, horizon, claimed Sharpe)
                           →   Auto-generates feature.py implementation
                           →   Runs purged-CV backtest with DSR correction
                           →   Publishes result on alpha-archive.io/papers/{id}
                           →   Tracks alpha decay over time
```

Each paper gets a public landing page with:
- Original paper link + author
- LLM-extracted signal specification
- Generated Python implementation (open, auditable)
- Backtest: IC report card, DSR-adjusted Sharpe, decay curve, regime analysis
- Replication score: gap between paper claims and live result
- Comments / community discussion

## Relationship to Hou-Xue-Zhang 2018 ("Replicating Anomalies")

HXZ 2018 is the gold-standard one-shot replication study: 452 published anomalies, all run through one consistent pipeline, with a multiple-testing-corrected significance bar (t > 2.78). Roughly 64% of the published "discoveries" failed to replicate. It permanently moved the goalposts for credible factor research and is the closest existing analogue to what Alpha Archive aims to be.

Alpha Archive is the **autonomous, perpetually-running version of HXZ**:

| | HXZ 2018 | Alpha Archive |
|---|---|---|
| Scope | 452 finished papers, one-shot | Every new paper as it drops, continuous |
| Pipeline | Manual, single team, single dataset | Automated LLM extraction + standardized backtest |
| Significance bar | Single threshold across the 452 | Cumulative DSR adjustment across all papers ever tested |
| Result lifecycle | Frozen at publication | Live re-runs track alpha decay over time |
| Code / data | Closed source-of-truth | Open code, open results, crowdsourced verification |

The methodology HXZ established (point-in-time data, survivorship-free universe, purged CV, multiple-testing correction) is the methodology spec here. See [docs/methodology.md](./docs/methodology.md). After HXZ, no credible factor paper can skip these checks; Alpha Archive enforces them automatically and at scale.

## Differentiators

| | AlphaArchitect | Quantpedia | Alpha Archive |
|---|---|---|---|
| Cost | Free blog | $300/yr | Free + open |
| Coverage | ~50 papers/yr (manual) | 700+ static | 1000s/yr automated |
| Reproducible code | Sometimes | Some | Always (auto-gen + open) |
| Live re-runs | No | No | Continuously updated |
| Methodology standardized | No | Partial | Yes (purged CV + DSR everywhere) |
| Crowdsourced | No | No | Yes (challenges, alts, votes) |
| Tracks alpha decay | No | No | Yes (live re-run cadence) |

## Vision: Central intelligence for quant finance

Alpha Archive combines three loops into one knowledge base:

1. **Automated replication**, LLM reads paper, extracts spec, writes code, runs backtest
2. **Meta-learning critique**, internal critic agent judges every result; actor self-improves; learn improves the critic
3. **Crowdsourced verification**, community submits challenges, alternatives, annotations; Twitter-Community-Notes-style bipartisan agreement gates merges

The result: one canonical, continuously-updated, executable, community-verified page per quant finance paper.

Like Wikipedia for trading signals, with executable code + live backtests + bipartisan verification.

## Quick start (developer)

```bash
git clone https://github.com/RezaSoleymanifar/alpha-archive
cd alpha-archive
uv sync                                                # Python env
uv run alpha-archive init                              # SQLite schema
uv run alpha-archive install-fixtures                  # 326 ground-truth fixtures from OpenAP
uv run alpha-archive poll arxiv                        # fetch new papers
uv run alpha-archive triage --limit 20                 # LLM triage (free via Claude Code CLI)
uv run alpha-archive replicate <paper_id> <pdf_url>    # end-to-end paper -> verdict
```

## Autonomous self-improvement loop

Per the meta governance in `meta/north_star.md` + `meta/actor.md` + `meta/critique.md` + `meta/learn.md`, the platform runs an end-to-end self-improvement cycle. One iteration:

```
poll -> triage -> replicate-on-tradable -> CRITIC grades reports
                                       -> ACTOR proposes calibration tweaks
                                       -> metrics logged to data/meta_runs/metrics.jsonl
              (weekly)              -> LEARN aggregator analyzes attribution -> proposes critique.md edits
```

**Manual run (any cadence):**
```bash
uv run alpha-archive loop                    # one full iteration; proposals only (no auto-apply)
uv run alpha-archive loop --learn            # also run weekly LEARN aggregator
uv run alpha-archive loop --auto-apply       # apply actor proposals to meta/actor.md (still requires human commit)
```

**Per-stage CLI (for inspection / debugging):**
```bash
uv run alpha-archive critique                # grade all ReplicationReports -> data/critique_runs/
uv run alpha-archive critique --paper-id X   # grade just one
uv run alpha-archive actor-propose           # propose actor.md calibration changes
uv run alpha-archive learn                   # run LEARN attribution -> data/learn_runs/
```

### Deployment options

| Mode | When to use | Cost | LLM provider |
|------|-------------|------|--------------|
| **Local cron / Task Scheduler** | Solo dev, full Claude Code Max plan available | $0 | `claude_code` (CLI Max plan, free) |
| **GitHub Actions** (`.github/workflows/autonomous_loop.yml`) | Hands-off, want public artifact trail | ~$0.04/paper | `anthropic` (requires `ANTHROPIC_API_KEY` secret) |

**GitHub Actions cron is intentionally commented-out by default.** To enable scheduled runs:
1. Add `ANTHROPIC_API_KEY` to repo Settings -> Secrets and variables -> Actions
2. Uncomment the `schedule:` block in `.github/workflows/autonomous_loop.yml`
3. Push the change

Until enabled, the workflow remains manually-triggered via the Actions tab ("Run workflow" button on `autonomous-loop`).

**Hard safety per `meta/learn.md`:**
- Actor self-edits emit a markdown PROPOSAL by default; `--auto-apply` is opt-in.
- Critique.md changes (LEARN's domain) ALWAYS go through human-reviewed PRs, no auto-merge ever.
- Loop never modifies `meta/north_star.md` or `meta/learn.md` (immutable per spec).

## Architecture

```
[Paper sources]               [LLM layer]              [Backtest engine]        [Web UI]
arXiv API           ─┐        ┌─ Triage              ┌─ Data: yfinance,        ┌─ Next.js
SSRN via Crossref   ─┤  →     ├─ Spec extractor  →   │  EOD, FRED, grain  →   ├─ Per-paper page
NBER via Crossref   ─┤        └─ Code generator     ├─ IC report card        ├─ Search / filter
OpenAP catalog      ─┤                              ├─ Purged CV + DSR       ├─ Submit paper
AlphaArchitect RSS  ─┘                              ├─ Decay analysis        ├─ Discussion
Manual submission   ─┘                              └─ Regime test           └─ API
```

NBER and SSRN block direct scraping; both routed through Crossref's free
DOI registry (NBER prefix `10.3386`, SSRN prefix `10.2139`). OpenAlex
client also wired as a fallback.

See [docs/architecture.md](./docs/architecture.md) for full layout.

## Data layer

Methodology (purged CV, DSR, replication scores) is independent of any specific data vendor; the same pipeline runs on whatever price + fundamentals panel you point it at. Three tiers of access exist, gated by what the user can subscribe to.

### Access tiers

| Tier | Vendor | Cost | Coverage of HXZ-452 anomalies | Who can buy |
|------|--------|------|-------------------------------|-------------|
| **Institutional** | WRDS bundle (CRSP + Compustat + I/B/E/S + TAQ + OptionMetrics) | $40-80K/yr | ~95% | Universities, hedge funds, asset managers, **not individuals** |
| **Retail** | Sharadar Core US (Nasdaq Data Link) | ~$300/mo | ~70% | Anyone |
| **Free** | OpenAP fixtures + Ken French + HXZ q-factors + FRED + grain prices | $0 | ~25 (price + ADV only) for direct compute; ground-truth scoring on 326 derived returns | Anyone |

**Why CRSP + Compustat are gated:** sold only via institutional contracts (WRDS portal, Wharton). No individual seat exists. Bundled with university affiliation, employer subscription, or a negotiated WRDS Individual Research tier (~$1.5-3K/yr, opaque pricing).

**Sharadar is the indie equivalent**: WRDS-tier methodology (PIT fundamentals + survivorship-free universe + ~150 line items) at 1/100th the cost. History starts 1999 vs CRSP's 1925, and only ~150 of CRSP/Compustat's ~1000 line items, but covers the meat of academic asset pricing.

### Pipeline data sources (current)

| Source | Cost | Role |
|---|---|---|
| **Sharadar Core US Fundamentals** (Nasdaq Data Link) | ~$300/mo | PIT fundamentals + adjusted prices + delisting actions, ~3000 US tickers since 1999. The single biggest unlock, solves survivorship-bias and lookahead-bias blockers in one subscription. **Buy when traction justifies; not required for MVP.** |
| **OpenAP CrossSection** (Chen + Zimmermann) | free | 326 anomaly return series pre-computed against CRSP+Compustat. Used as ground-truth fixtures for replication scoring. You don't need raw CRSP because you have the derived returns. |
| **Ken French data library** | free | Fama-French + Carhart benchmark factor return series since 1926, for alpha computation |
| **HXZ q-factors** (authors' site) | free | q-factor return series for HXZ-style alpha decomposition |
| **FRED** | free | Macro (rates, inflation, VIX, credit spreads) for regime-conditional analysis |
| **grain parquet** (companion repo) | free | Daily prices for ~3000 US tickers since 2011, OHLCV |
| **EODHD** | $79/mo | International universe + intraday, complementary, not core |

### Coverage of the academic qfin universe

Per `scripts/audit_qfin_universe_coverage.py` (re-runnable): **the addressable half of academic qfin is the cross-sectional US equity asset pricing canon plus pure portfolio-construction methodology, about 50% of published research by volume.**

| Bucket | % of academic qfin output | Coverage with current stack |
|--------|--------------------------:|-----------------------------|
| US equity cross-sectional factor research (HXZ / FF / Stambaugh / AQR style) | ~18% | ✅ FULL |
| ML on US equity characteristics (Gu-Kelly-Xiu, Kelly-Pruitt-Su, Bryzgalova-Pelger-Zhu) | ~5% | ✅ FULL |
| Pure methodology (portfolio opt, risk estimation, backtesting frameworks) | ~9% | ✅ FULL |
| Asset pricing / derivatives pricing **theory** (no data needed) | ~5% | ✅ N/A |
| US equity stat arb / pairs | ~2% | ✅ FULL |
| PEAD / sentiment indices / country rotation (partial) | ~7% | 🟡 PARTIAL |
| Multi-asset (Carry, Value+Momentum Everywhere) | ~6% | ❌ blocked, need Bloomberg/Refinitiv |
| FX, commodities, fixed income | ~16% | ❌ blocked, same |
| Equity options + vol arb | ~5% | ❌ blocked, need OptionMetrics |
| Microstructure / HFT | ~3% | ❌ blocked, need TAQ |
| Alt-data / text / NLP (Lazy Prices, ChatGPT factor, Google attention) | ~10% | ❌ blocked, need news corpus / SEC EDGAR scrape |
| Crypto factor / on-chain | ~6% | ❌ blocked, cheap to add (free APIs) |

**Positioning is honest:** Alpha Archive replicates the addressable half of academic quant finance, the US equity asset pricing canon, ML applied to it, and portfolio construction methodology. Frontier research (multi-asset, derivatives, microstructure, alt-data) is gated by data licensing and intentionally out of scope.

### Live paper-discovery sources (post-OpenAP cutoff)

OpenAP is the calibration corpus. Live feeds catch new papers as they drop:

| Source | Backend | Signal density | Free? |
|---|---|---|---|
| **arXiv q-fin** (last 30d) | direct API | ⭐ ~2-5% factor papers | ✅ |
| **NBER working papers** | Crossref (DOI prefix `10.3386`) | ⭐⭐ ~25% factor papers | ✅ |
| **SSRN Electronic Journal** | Crossref (DOI prefix `10.2139`) | ⭐⭐ noisy without keyword filter | ✅ |
| **JF / JFE / RFS / JFQA** | Crossref (journal ISSN filter), wireable | ⭐⭐⭐⭐ peer-reviewed gold | ✅ for metadata, paywalled for PDF |
| **AQR research portal** (Asness/Frazzini/Pedersen) | RSS / scrape, wireable | ⭐⭐⭐⭐ | ✅ |

Triage filters the firehose. Real funnel: ~200 raw papers/month → ~30 candidates after keyword filter → ~10 surviving LLM triage → ~5 backtest-ready specs.

### Reproducibility convention

Every published replication pins its data vendor + version (academic standard since ~2005). Runtime config:

- `ALPHA_ARCHIVE_DATA_VENDOR=sharadar|wrds|grain` selects the source
- Each `ReplicationReport` records the vendor + pull-date + filter set used
- LLM-generated code is forbidden from fetching arbitrary external APIs at runtime, only the configured vendor's local cache is readable

## Companion repo: portfolio-management

Alpha Archive answers "does this signal work?", it produces a catalog of validated signals with replication scores and decay curves. The companion repo [`portfolio-management`](../portfolio-management) answers the next question: "given working signals, how do I build a portfolio from them?"

```
alpha-archive (this repo)              portfolio-management
──────────────────────────             ──────────────────────────
INPUT:  papers (arxiv/SSRN/NBER)       INPUT:  validated signals
OUTPUT: validated signals,             OUTPUT: weight vector w
        replication scores,                    (which stocks, how much $)
        decay curves
JOB:    Does this signal work?         JOB:    Given working signals,
                                               build a portfolio.
```

The optimizer in `portfolio-management` (long-only retail convex QP with sector-balance constraints, six factor presets, plus an HRP alternative) consumes the signals validated here. Together they form an end-to-end pipeline: paper → signal validation → portfolio allocation.

## Methodology

Every paper goes through the same pipeline. No cherry-picking, no parameter tuning per paper. Documented in [docs/methodology.md](./docs/methodology.md).

Key principles:
- **Purged k-fold CV** with embargo (Lopez de Prado 2018)
- **Deflated Sharpe Ratio** (Bailey + Lopez de Prado 2014) corrected for ALL papers tested across the platform
- **Pre-registered OOS window**: last 2 years held out from training
- **Standardized cost model**: 5bps round-trip + impact = σ × √(Q/ADV)
- **Replication score**: published Sharpe vs our Sharpe (after corrections)

## Roadmap

See [docs/roadmap.md](./docs/roadmap.md). Phased:
- **Phase 0** ✅ Repo skeleton, SQLite schema, six source pollers (arXiv, SSRN, NBER, AlphaArchitect, AQR, Two Sigma), Typer CLI
- **Phase 0.5** ✅ **Fixture calibration**, 326 ground-truth fixtures bootstrapped from Open Source Asset Pricing (Chen+Zimmermann), plus 4 hand-coded canonical anomalies (12-1 momentum, low-vol Baker-Haugen, BAB Frazzini-Pedersen, MAX Bali-Cakici-Whitelaw) running end-to-end on grain prices. Live-feed pollers rewired through Crossref (NBER, SSRN), both blocked direct scraping. Meta-loop now F1-meaningful.
- **Phase 1** ✅ LLM triage + spec extraction + code generation, end-to-end demo on real arXiv paper (VP-MACD). Pluggable provider abstraction: `claude_code` (free via Max plan) | `anthropic` (API key) | `offline` (no LLM)
- **Phase 2** 🟡 Backtest engine: purged CV, DSR, IC report, asymmetric verdict assignment shipped. Cost model + regime splits in progress.
- **Phase 2.5** 🟡 **Meta-learning loop**, actor/critic/learn governance scaffolded under `meta/`; community layer (Tier-1 GitHub-issue-based crowdsourcing, Community-Notes-style bipartisan agreement) scaffolded under `alpha_archive/community/`
- **Phase 3** ⏳ Web UI MVP (Streamlit)
- **Phase 4** ⏳ Public launch on alpha-archive.io
- **Phase 5** ⏳ Crowdsourced submissions + bipartisan verification at scale

## Why this could become popular

- **SEO win**: each replicated paper = a landing page with original keywords + Sharpe + chart
- **Quant Twitter**: practitioners constantly debate factor zoo; Alpha Archive provides verdict-in-a-link
- **Educational**: students + retail quants can learn what works
- **Fund DD value**: hedge fund LPs use it to vet manager pitches ("did this actually work post-publication?")
- **Content engine**: weekly newsletter "5 papers replicated this week"
- **Recruiter signal**: every result is reproducible code → portfolio piece for QR jobs

## Status

**Phase 2**: pipeline operational end-to-end on real papers (proof-of-life: see [docs/demo_run.md](./docs/demo_run.md)). 4 hand-coded fixtures running on grain S&P 500 daily prices; momentum survives 2014-2026, low-vol/BAB/MAX correctly killed (regime decay consistent with McLean-Pontiff 2016 + HXZ 2018). Live-feed pollers (arXiv, NBER, SSRN) all returning real recent papers. Meta-learning + community layers scaffolded. Pre-Streamlit. Not production. Not financial advice. Use at your own risk.

## License

MIT (planned). Methodology + extracted code is open. Original papers belong to their authors.

## Author

Reza Soleymanifar · PhD UIUC · ML Engineer · [profile](https://github.com/RezaSoleymanifar)
