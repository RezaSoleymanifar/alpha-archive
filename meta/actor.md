# ACTOR, current agent policy (mutable, evolves)

This file defines HOW the agent currently operates the pipeline. It MUST stay aligned with `meta/north_star.md`. The agent updates this file in response to critique (see `meta/critique.md`). All edits go through git so evolution is auditable.

## Version

v0.1.0: initial bootstrap

## Stage policies

### 1. Ingest (`alpha_archive.ingest`)

- Poll all sources daily at 06:00 UTC
- Dedupe by `(source, external_id)`, never re-ingest a paper
- Set `triage_status="pending"` on insert
- On source failure (HTTP 4xx/5xx, parse error): log, retry next cycle, do NOT crash
- Cap per-poll at 1000 papers per source to bound LLM cost

### 2. Triage (`alpha_archive.triage`)

**Goal**: filter "is this a tradable signal?" with low FN rate.

Current rules:
- Use Claude Haiku (`claude-haiku-4-5-20251001`) for cost
- Asymmetric voting: if Haiku says `tradable` → trust. If Haiku says `not_tradable` → second-opinion with Sonnet before discarding.
- Confidence threshold: only mark `not_tradable` if Haiku confidence ≥ 0.7. Below that → escalate to Sonnet.
- Output structured JSON only (refer to `alpha_archive/triage.py:TRIAGE_PROMPT`)
- Log every decision + score for the calibration loop

False-negative red flags (escalate immediately):
- Title mentions "factor" / "anomaly" / "predictability" / "alpha"
- Abstract has numerical results (Sharpe, t-stat, return)
- Author affiliation is academic finance department or known quant firm

### 3. Extract (`alpha_archive.extract`, to build)

**Goal**: convert PDF → structured signal spec with high fidelity.

Current rules (initial):
- Use Claude Sonnet for extraction (richer reasoning needed)
- Force structured-output JSON schema (no free text)
- Run TWICE with different temperature seeds; if specs disagree on `formula` or `horizon` → flag for human review queue, do NOT proceed
- Cache PDF text under `data/papers/{paper_id}.pdf.txt` for replay
- Hard requirement: spec must include `formula`, `data_required`, `universe`, `horizon_days`, `expected_sign`. Missing any → mark spec incomplete.

### 4. Implement (`alpha_archive.codegen`, to build)

**Goal**: convert spec → working Python `signal(prices)` function with no leakage.

Current rules (initial):
- Use Claude Sonnet
- Generated code must be a single function with signature `signal(prices: pd.DataFrame) -> pd.DataFrame`
- MUST pass static validation gates BEFORE backtest:
  - No `.shift(-N)` for negative N (lookahead) outside designated forward-return helpers
  - No `import urllib`, `import socket`, `open(... "w")`, `subprocess`, `os.system`
  - Returns DataFrame matching prices.shape (universe alignment)
  - Deterministic given seed
  - Runtime ≤ 60s on 5yr SP500 panel
- Run in Docker sandbox (no network, ephemeral fs, 1 CPU, 2GB mem)
- If validation fails: feed the error back to Sonnet (max 3 self-correction attempts), then escalate

### 5. Backtest (`alpha_archive.backtest.runner.run_signal_backtest`)

**Goal**: standardized backtest, no per-paper tuning.

Locked parameters (per `north_star.md`):
- Cost: 5 bps round-trip + sqrt market impact
- CV: purged + embargoed walk-forward
- DSR: corrected for cumulative platform N (every paper tested counts toward N)
- OOS holdout: last 24 months frozen
- Universe: per spec, default sp500
- Rebalance: monthly unless spec specifies
- Long-only OR long-short: per spec; default long-short for cross-sectional, long-only for time-series
- Top quintile (20%) for discrete rank strategies; continuous-weight for regression-output strategies

### 6. Verdict (`alpha_archive.backtest.runner.assign_verdict`)

Per `north_star.md` decision boundaries. Asymmetric:
- `ship` requires ALL 4 gates pass
- `iterate` is default when in-between (preserves the signal)
- `kill` requires ≥ 2 independent negative gates

Never auto-`kill` on a single negative metric.

### 7. Publish

Every result → public landing page at `alpha-archive.io/papers/{paper_id}`:
- Original paper link + abstract
- Extracted spec (versioned)
- Generated code (versioned, public)
- IC report card with decay + sector splits
- Equity curve + drawdown plot
- DSR + replication score + verdict + reasoning
- Comments / discussion (Phase 5+)

## Cross-cutting principles

1. **Be explainable**: every verdict ships with `verdict_reasoning` list of pass/fail gates
2. **Be reproducible**: log seed, data vintage, model version, prompt version with each result
3. **Be conservative**: when uncertain → escalate to human review, don't auto-kill
4. **Fail loudly**: if any gate fails its preconditions, raise, don't silently proceed
5. **Learn from history**: every false-positive / false-negative becomes a fixture or test case

## Calibration parameters (mutable, tracked here for transparency)

```yaml
triage:
  haiku_confidence_threshold_for_kill: 0.70
  escalate_to_sonnet_below: 0.70
extract:
  self_consistency_min_agreement: 0.85
  max_extraction_retries: 3
codegen:
  max_self_correction_attempts: 3
  sandbox_timeout_seconds: 60
verdict:
  ship_dsr_threshold: 0.95
  ship_icir_threshold: 0.30
  ship_oos_ratio: 0.50
  kill_dsr_threshold: 0.30
  kill_icir_threshold: 0.10
  kill_min_negative_gates: 2
backtest:
  cost_bps: 5.0
  rebalance_freq: "monthly"
  oos_split_date: "2024-01-01"
  top_quintile_pct: 0.20
```

## Lessons learned (append-only journal)

Format: `YYYY-MM-DD | <fixture_id or run_id> | <observation> | <action taken in actor.md>`

```
2026-05-01 | momentum_jt1993 | Full-window Sharpe 0.07 vs claimed 0.7, clear post-pub decay. Pipeline correctly avoided FN by verdict=iterate. Validates asymmetric verdict rules. | No actor changes; reaffirms ship_oos_ratio guardrail.
2026-05-01 | bootstrap        | Imported 326 fixtures from Open Source Asset Pricing (Chen+Zimmermann). 165 ship / 47 iterate / 114 kill labels. Fixture set grew 6 -> 332. | No actor changes; meta-loop F1 now statistically meaningful.
```

## Evolution policy for THIS file

The actor MAY edit this file in response to critique IF:
1. The change moves toward `north_star.md` measurable goals
2. The change is supported by data (regression on fixture set or new fixture)
3. The commit message explains: WHAT changed, WHY (which critique drove it), WHICH north-star metric is targeted
4. Fixtures still pass after the change (or new fixtures are added to cover the case)

The actor MUST NOT:
- Edit `north_star.md`
- Edit `learn.md`
- Loosen verdict thresholds without showing FN rate is preserved
- Add cost-cutting shortcuts that bypass validation gates
