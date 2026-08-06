# Alpha Archive roadmap

## Phase 0, Skeleton ✅ shipped

- [x] Repo initialized
- [x] SQLite schema (papers, specs, results)
- [x] Source pollers: arXiv, SSRN, NBER, AlphaArchitect, AQR, Two Sigma (curated-first hierarchy)
- [x] Ingest pipeline + dedup
- [x] LLM triage scaffold (Claude Haiku)
- [x] Typer CLI: `init`, `poll`, `triage`, `stats`, `list`, `replicate`, `install-fixtures`, `evaluate`, `llm-info`
- [x] Docs: README, architecture, methodology, roadmap, demo_run, go-to-market, meta_learning

## Phase 0.5, Fixture calibration ✅ shipped

- [x] OpenAP CrossSection bootstrap loader → 326 ground-truth fixtures with literature labels (165 ship / 47 iterate / 114 kill)
- [x] Hand-coded canonical anomalies (Jegadeesh-Titman 1993 momentum)
- [x] Adversarial random fixtures for FP-rate calibration
- [x] Fixture set total: 332 (was 6 pre-bootstrap) → meta-loop F1 now statistically meaningful

## Phase 1, LLM extraction + first end-to-end ✅ shipped

- [x] PDF downloader + text extractor (pypdf, 30 pages)
- [x] Sonnet-driven spec extractor with self-consistency check (run 2× different temps, agreement ≥ 0.85 gate)
- [x] Sonnet-driven code generator → `Spec.code` populated
- [x] Sandbox executor (restricted-builtins exec, no network, deterministic, time-limited)
- [x] AST-level validation gates: signature, imports, no-lookahead, no-banned-tokens, deterministic
- [x] End-to-end smoke test on real arXiv paper (VP-MACD, see [docs/demo_run.md](./demo_run.md))
- [x] Pluggable LLM provider abstraction: `claude_code` (free via Max plan) | `anthropic` (API key) | `offline`

## Phase 2, Backtest engine 🟡 in progress

- [x] Price loader: grain parquet primary, yfinance fallback
- [x] Universe loader (SP500 from grain snapshot, PIT approximation)
- [x] IC report card (mean, std, ICIR, t-stat)
- [x] Purged + embargoed CV
- [x] DSR implementation (Bailey + Lopez de Prado 2014)
- [x] Strategy stats (Sharpe, drawdown, turnover)
- [x] Asymmetric verdict assignment (ship / iterate / kill, bias toward iterate)
- [ ] Cost model (5bps + sqrt market impact), basic 5bps in place; impact term pending
- [ ] Fundamentals loader (Sharadar Core US, gated on $200/mo subscription decision)
- [ ] FRED macro loader
- [ ] Regime analysis splits (VIX / NBER / rate regime)
- [ ] CPCV (Combinatorial Purged CV)

## Phase 2.5, Meta-learning + community 🟡 scaffolded

- [x] Meta governance files: `north_star.md` (immutable goal), `actor.md` (mutable policy), `critique.md` (mutable, learn-edited), `learn.md` (immutable meta-meta), `community.md` (mutable crowdsourcing)
- [x] Asymmetric loss function: `L = 5·FN + 1·FP + 2·|repl_score − 0.6|` (FN weighted 5× because losing real signal is permanent)
- [x] Calibration metric logger (`alpha_archive/meta/calibration.py`)
- [x] Eval loop runner (`alpha_archive/meta/eval_loop.py`)
- [x] Community layer scaffolded: 7 SQLAlchemy models, 5-gate Community-Notes-style verification, reputation system, faction-bipartisan agreement, GitHub-issue scraper (no social-media trawl)
- [ ] Critic agent that reads ReplicationReport and applies critique.md rubric
- [ ] Weekly cron: actor self-edits + learn-proposed PRs
- [ ] Public landing page per merged community contribution

## Phase 2.7, Public catalog seeding (immediate next; cost = $0)

Demand-validation sequence before paying for any data subscription. Order matters:

- [ ] **Run autonomous loop on 5 fresh polled papers** to validate end-to-end on real data + seed metrics.jsonl with multiple data points (`alpha-archive loop --replicate-limit 5`)
- [ ] **Hand-replicate 10 canonical anomalies** (price-only, free-data-only) so the catalog has a credible day-1 baseline before launch:
  - Jegadeesh-Titman 1993 (12-1 momentum)
  - Frazzini-Pedersen 2014 (BAB)
  - Ang-Hodrick-Xing-Zhang 2006 (low-vol)
  - Bali-Cakici-Whitelaw 2011 (MAX)
  - George-Hwang 2004 (52-week-high)
  - DeBondt-Thaler 1985 (long-term reversal)
  - Lehmann 1990 (short-term reversal)
  - Moreira-Muir 2017 (vol-managed)
  - Novy-Marx 2013 (gross profitability, uses minimal yfinance fundamentals)
  - Asness-Frazzini-Pedersen 2019 (Quality Minus Junk, US slice)
- [ ] **Run critic agent over all 10** → first real attribution chain for LEARN
- [ ] **Document each replication** as an artifact under `data/replications/` with reproducibility-pinned vendor + date

Success criteria: 10 catalog entries with verdicts, all reproducible byte-for-byte. **No paid data subscription required for any of these.**

## Phase 2.8, Data access decision gate

Triggered by traction signal from Phase 3 launch (>2K visitors / 100 GitHub stars within 4 weeks). Until triggered, stay on free stack.

Three paths in priority order:

1. **Free institutional path**, university affiliation (alum library access, visiting researcher status), employer subscription (CapOne / hedge fund), or co-author relationship with WRDS-licensed academic. Cost: $0. Use the WRDS data backend (`ALPHA_ARCHIVE_DATA_VENDOR=wrds`).
2. **Retail paid path**, Sharadar Core US (~$300/mo) when audience evidence justifies. Unlocks ~70% of HXZ-452. Cost: $3,600/yr.
3. **Negotiated WRDS Individual Research tier**, apply directly to wrds-support@wharton.upenn.edu with research credentials. Cost: ~$1.5-3K/yr opaque pricing. Worth pursuing only if #1 fails and Sharadar feels insufficient.

Once any path opens, expand replication catalog from ~25 anomalies (price-only) → ~250 anomalies (full Sharadar) or ~400 (full WRDS).

## Phase 3, Web MVP (Streamlit)

- [ ] Streamlit dashboard
  - paper list with filters (source, status, tradable, sharpe>X)
  - per-paper detail page (spec, code, IC chart, equity curve, regime breakdown)
  - search by title/author/keyword
- [ ] Public deployment on Streamlit Cloud / Render
- [ ] Basic SEO (per-paper canonical URL, OG tags, sitemap)

## Phase 4, Public launch (alpha-archive.io)

- [ ] Domain + DNS + Vercel/Railway deploy
- [ ] Next.js frontend replacing Streamlit
  - landing page with replicated paper count + top-Sharpe leaderboard
  - per-paper landing page (SEO-optimized)
  - search + filter
  - subscribe to RSS / weekly digest
- [ ] FastAPI backend for JSON API
- [ ] Postgres migration from SQLite
- [ ] Worker queue (Dramatiq)
- [ ] Monitoring (Sentry, Plausible analytics)

## Phase 5, Community + crowdsourced

- [ ] User accounts (auth via GitHub OAuth)
- [ ] Submit-a-paper form (with anti-spam)
- [ ] Vote / discuss per paper
- [ ] User-submitted alternate implementations (with version diff)
- [ ] Comments + Q&A per paper
- [ ] Bounty for un-replicated high-impact papers

## Phase 6, Live + alpha decay tracking

- [ ] Re-run all surviving signals weekly / monthly
- [ ] Track Sharpe / IC over time → alpha decay charts
- [ ] Email alerts when previously-shipped signal decays below threshold
- [ ] Compare published Sharpe (paper era) vs current Sharpe
- [ ] Public "factor zoo decay" page

## Phase 7, Monetization (optional)

- [ ] Free tier: see all paper results
- [ ] Pro tier ($X/mo): API access, full backtest artifacts download, custom universe runs
- [ ] Enterprise: white-label methodology, custom data integrations, on-prem deployment for fund DD teams

## Phase 8, Research lab (long-term)

- [ ] Native discovery (not just replication): generate alpha hypotheses via LLM, test them
- [ ] Ensemble: combine top-N signals into composite portfolio
- [ ] Live paper-trading for top signals (via Alpaca / IB)
- [ ] Research papers: Alpha Archive itself publishes findings on factor zoo behavior

## Non-goals (intentionally not building)

- Custom QP solver (use OSQP/CVXPY)
- Proprietary data vendor (use commodity providers + caching)
- Live execution platform (focus is research, not trading)
- Mobile app (web is sufficient)
- Crypto-only (markets too immature for replication)
