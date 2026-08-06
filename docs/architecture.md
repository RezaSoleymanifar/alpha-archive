# Alpha Archive architecture

## Overview

Alpha Archive is a 5-layer **pipeline** with two orthogonal **governance layers** sitting alongside (meta + community). The pipeline produces verdicts; governance keeps the pipeline honest and improving over time.

```
┌─────────────────────────────────────────────────────────────┐
│  Layer 1: SOURCES                                            │
│  arXiv RSS · SSRN scraper · NBER RSS · AlphaArchitect RSS   │
│  · manual submission                                         │
└────────────────────┬────────────────────────────────────────┘
                     ▼
┌─────────────────────────────────────────────────────────────┐
│  Layer 2: INGEST                                             │
│  Dedupe by (source, external_id) → SQLite `papers` table     │
└────────────────────┬────────────────────────────────────────┘
                     ▼
┌─────────────────────────────────────────────────────────────┐
│  Layer 3: LLM TRIAGE + EXTRACTION                            │
│  Haiku triage abstract → Sonnet extracts spec + writes code  │
│  → SQLite `specs` table                                      │
└────────────────────┬────────────────────────────────────────┘
                     ▼
┌─────────────────────────────────────────────────────────────┐
│  Layer 4: BACKTEST ENGINE                                    │
│  Loads price/fundamentals data → runs feature code →         │
│  IC report card → DSR-corrected Sharpe → SQLite `results`    │
└────────────────────┬────────────────────────────────────────┘
                     ▼
┌─────────────────────────────────────────────────────────────┐
│  Layer 5: WEB API + UI                                       │
│  FastAPI REST endpoints + Next.js (or Streamlit MVP)         │
│  Public per-paper landing pages                              │
└─────────────────────────────────────────────────────────────┘
```

### Orthogonal governance layers

```
┌──────────────────────────────────┐  ┌──────────────────────────────────┐
│  META layer (alpha_archive/meta/) │  │  COMMUNITY layer                  │
│  actor / critique / learn loop    │  │  (alpha_archive/community/)       │
│  · enforces north_star.md         │  │  · GitHub-issue ingest            │
│  · weekly self-improvement PRs    │  │  · 5-gate verification            │
│  · 332 fixtures as ground truth   │  │  · Community-Notes bipartisan     │
└──────────────────────────────────┘  │  · reputation + factions          │
                                      └──────────────────────────────────┘
       ↑ both feed evidence to learn.md → proposed critique.md updates
```

See [meta/README.md](../meta/README.md) for the meta-loop.

## Data flow

1. **Cron** (or manual) triggers `alpha-archive poll <source>`.
2. Source poller returns standardized paper dicts. Sources are tiered (`SOURCES_PRIMARY` curated-first; opt-in to `--tier background` for high-volume noise sources).
3. Ingest dedupes against existing `papers` table; new rows get `triage_status=pending`.
4. **Triage worker** picks pending papers, calls Haiku with abstract → updates `triage_status` + `triage_score` + structured `triage_notes` JSON (signal_type, data_required, horizon_days, claimed_sharpe).
5. **Extract worker** picks `tradable` papers, downloads PDF, calls Sonnet 2× with different temps for self-consistency → if agreement ≥ 0.85 inserts `specs` row, else flags for human review.
6. **Codegen worker** generates `signal(prices: pd.DataFrame) -> pd.DataFrame` Python; passes 5 AST-level gates (signature, imports, no-lookahead, no-banned-tokens, deterministic) before sandbox exec.
7. **Backtest worker** loads price/fundamentals panel, executes signal code in restricted-builtins sandbox, computes IC report + DSR + replication score → inserts `results` row.
8. **Verdict worker** applies asymmetric thresholds (ship requires all 4 gates; kill requires ≥ 2 negative gates; iterate is the default for ambiguous).
9. **API** serves results to frontend; per-paper landing page renders.

## Storage

- **SQLite** for metadata (papers, specs, results), sufficient until 100K+ papers
- **Parquet** for backtest artifacts (IC time series, equity curves, plots), under `data/parquet/`
- **PDFs** cached under `data/papers/{paper_id}.pdf`
- Migration to **Postgres** when multi-tenant or write-heavy

## Compute

- MVP: single machine, sequential workers
- Phase 3+: Celery / Dramatiq queue, multiple workers
- Phase 5+: distributed backtest grid (Ray) for parameter sweeps

## Data sources for backtests

- **Prices**: yfinance (free, MVP) → EOD Historical Data ($20/mo) → Polygon ($99/mo)
- **Fundamentals**: yfinance + EOD → grain repo's `eodhd-fundamentals-cache.json`
- **Macro**: FRED (free) via `fredapi`
- **Alt data**: hooks for Form 4 insider trades, options activity, news sentiment

## LLM usage

Pluggable provider via `ALPHA_ARCHIVE_LLM_PROVIDER` env var:
- `claude_code` (default), routes through Claude Code CLI on Max plan. **Cost: $0.**
- `anthropic`, direct Anthropic API. Requires `ANTHROPIC_API_KEY`.
- `offline`. No LLM; for tests / dry runs.

Per-paper LLM workload (5 calls total):
- **Triage**: Haiku, ~200 tokens in / 100 out
- **Spec extraction**: Sonnet × 2 (self-consistency), ~5K in / 2K out each
- **Code generation**: Sonnet, ~3K in / 1K out (+ retries on validation failure)

Equivalent Anthropic API cost: ~$0.04 / paper. At 80K papers/yr that's ~$3,200/yr API cost; via Claude Code Max plan it's $0.

## Web stack

- **Frontend**: Next.js 14+ (App Router) + Tailwind + Recharts/visx
- **Backend**: FastAPI for JSON API; static page generation for SEO
- **Hosting**:
  - API: Fly.io / Railway / Render
  - Frontend: Vercel
  - Database: Supabase or PlanetScale (Postgres) when migrating off SQLite
  - Workers: Modal or Railway

## Scaling milestones

| Stage | Papers | DB | Compute | Hosting cost/mo |
|---|---|---|---|---|
| MVP | <1K | SQLite | Single laptop | $0 |
| Public launch | 1K-10K | SQLite | Single VM | $20 |
| Growth | 10K-100K | Postgres | Multi-worker | $200 |
| Scale | 100K+ | Postgres + S3 parquet | Distributed | $1K-5K |

## Security / abuse

- Rate-limit API (per IP)
- Auth required for: paper submission, comments
- LLM-generated code runs in sandbox (Docker, no network, ephemeral filesystem)
- All extracted code is human-reviewable before backtest execution (configurable gate)

## Observability

- Structured logging (loguru → JSON)
- Per-paper run timeline (ingest → triage → extract → backtest → publish)
- Public dashboard: papers/day, triage hit rate, replication success rate
