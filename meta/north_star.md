# NORTH STAR, immutable

This file defines the goal. It does NOT change without an explicit human-approved PR. Every other meta file (`actor.md`, `critique.md`, `learn.md`) ultimately serves this north star.

## Mission

Build the optimal pipeline that ingests quantitative finance papers from the open internet, separates **genuine alpha signals** from noise, and publishes verdicts that practitioners can trust.

## What the optimal pipeline does

```
SOURCES → INGEST → TRIAGE → EXTRACT → IMPLEMENT → BACKTEST → VERDICT → PUBLISH
```

At each step the pipeline must:
- prefer being slow + careful over fast + lossy
- prefer false positives (filterable later) over false negatives (irrecoverable)
- prefer transparent + reproducible decisions over black-box judgments
- prefer multi-evidence consensus over single-model verdicts

## Quality bar (non-negotiable)

| Metric | Target | Reason |
|---|---|---|
| **False-negative rate** (kill a real signal) | < 2% | Missing alpha is irrecoverable. Lost real signals never come back. |
| **False-positive rate** (ship a noise factor) | < 10% | Filterable downstream by human review or ensemble. |
| **Verdict accuracy on canonical fixtures** | ≥ 85% | If we can't replicate Fama-French / Jegadeesh-Titman correctly, we have no credibility. |
| **IC sign correctness** | ≥ 90% | Getting the direction wrong is worse than getting magnitude wrong. |
| **Replication score (measured/claimed Sharpe) on canon** | 0.4, 0.8 | Matches McLean & Pontiff post-pub decay literature. |
| **Reproducibility** | 100% | Every published verdict must be byte-for-byte rerunnable from public code + data version. |

## Asymmetric loss function

```
L = 5 · false_negatives + 1 · false_positives + 2 · |replication_score − 0.6|
```

Minimizing L is the platform's optimization objective. False negatives weighted 5× because losing a real signal is permanent.

## Decision boundaries

| Verdict | Conditions |
|---|---|
| `ship` | DSR > 0.95 AND ICIR > 0.3 AND OOS Sharpe ≥ 0.5 × IS Sharpe AND IC sign correct |
| `iterate` | Default when not all `ship` gates pass AND not multiple `kill` gates triggered |
| `kill` | (DSR < 0.3 AND OOS Sharpe < 0) OR (ICIR < 0.1 AND IC sign wrong), requires ≥2 negative gates |

Bias toward `iterate`. `kill` requires multiple independent negative signals.

## Out of scope

These are explicitly NOT goals:
- live execution / production trading
- proprietary alpha generation (we replicate published; we don't invent)
- HFT / sub-daily strategies (data quality insufficient)
- crypto-native (markets too immature for replication)
- ML benchmarks / prediction games (we test trading signals, not generic time-series)
- becoming a data vendor (we use commodity data)
- replacing fund DD / human judgment (we provide evidence, not recommendations)

## Hard constraints

- All LLM-generated code must run in sandbox (no network, no fs writes outside tmp, time + memory limits)
- All published results must be reproducible, versioned code + data vintage logged
- Every verdict on a public paper must include the original paper link
- Methodology changes require ground-truth fixture validation (see `meta/critique.md`)

## What "the optimal agent" looks like

The actor (defined in `actor.md`) is optimal when:
1. It correctly verdicts ≥ 90% of canonical fixtures
2. It surfaces ≥ 1 novel insight per 100 papers (e.g., "this paper's published Sharpe is unreproducible due to X")
3. Its asymmetric loss `L` trends down month-over-month
4. Its decisions are explainable, every verdict ships with reasoning

## Evolution policy for THIS file

`north_star.md` changes require:
- explicit human approval (PR review)
- justification document showing why goal needs revision
- migration plan for any in-flight work affected

Never edit without these. The whole self-improvement system collapses if the north star is mutable by the agent itself.
