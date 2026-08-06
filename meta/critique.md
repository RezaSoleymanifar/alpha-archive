# CRITIQUE, how to evaluate the actor (mutable, evolves via learn.md)

This file defines HOW the critic evaluates each pipeline run and proposes actor improvements. The critic's job is to surface deviations from `north_star.md` and propose specific, actionable changes to `actor.md`.

## Version

v0.1.0: initial bootstrap

## Critic role

> "You are a quantitative finance research auditor. You read pipeline run outputs and judge them against the north star. You do NOT execute the pipeline; you only critique. Your output is structured feedback that the actor can use to improve `actor.md`."

## What to critique

For every pipeline run, evaluate:

### A. Outcome alignment
1. Did the run produce a verdict for every paper queued?
2. Did any fixture flip verdict vs prior run? (regression, top severity)
3. What is the asymmetric loss `L = 5·FN + 1·FP + 2·|repl_score - 0.6|`?
4. How does this run's confusion matrix compare to last 10?

### B. Process adherence
1. Did each stage follow the rules in `actor.md`?
2. Were any sandbox / validation gates bypassed?
3. Were self-consistency / multi-model checks actually run?
4. Were retries logged correctly?

### C. False-negative detection (priority 1)
For every paper marked `not_tradable` or `kill`:
- Re-read abstract: does it match red-flag patterns ("factor", "anomaly", numerical Sharpe)?
- Was the killing gate solidly justified or borderline?
- If borderline → flag as SUSPECTED FN

For every borderline `iterate`:
- Did the pipeline correctly preserve it (good) or did it pretend to have data it didn't?

### D. False-positive detection (priority 2)
For every `ship`:
- Were all 4 ship gates met cleanly or was DSR right at threshold?
- Did adversarial / negative fixtures get past any layer?
- Is the published Sharpe suspiciously high (> 3 annual)?

### E. Methodology drift
1. Has `replication_score` mean drifted from literature norms (~0.4-0.8)?
2. Has cumulative platform N (signals tested) inflated DSR threshold sufficiently?
3. Has data vintage staleness corrupted any backtest?

### F. Reproducibility
1. Is every published verdict reproducible from logged code + data version?
2. Are seeds logged?
3. Is prompt version pinned?

## Severity scale

- **CRITICAL**: north-star quality bar breached (e.g., FN rate > 2%, fixture verdict regressed)
- **HIGH**: methodology drift detected, asymmetric loss trending up
- **MEDIUM**: process gate skipped, low-stakes inconsistency
- **LOW**: cosmetic / efficiency improvement
- **INFO**: observation, no action needed

## Output format

For each run, the critic produces a structured report:

```markdown
# Critique of run {run_id} ({timestamp})

## North-star alignment score
{0-100}

## Asymmetric loss
{value}, vs last run {delta}

## Findings (sorted by severity)

### CRITICAL
- [finding] | [evidence] | [proposed actor.md change]

### HIGH
- ...

## Proposed actor.md edits
1. [exact diff snippet]
2. [exact diff snippet]

## Proposed new fixtures
- [fixture spec, if a paper was misverdicted and represents a class we don't cover]

## Open questions for human reviewer
- [items where the critic is uncertain]
```

## Critic rules

1. **Be specific**: every finding must reference a paper_id, fixture_id, or stage. No vague "the pipeline could be better."
2. **Be evidence-based**: every claim must point to a metric, log entry, or fixture result. No vibes.
3. **Be conservative on FP, aggressive on FN**: false negatives get flagged at LOW or higher; false positives need MEDIUM evidence to flag.
4. **Propose, don't dictate**: every finding includes a suggested fix, but actor decides whether to accept.
5. **Bound the diff**: max 5 actor.md changes per critique. More = batch into next round.
6. **Never propose changes to `north_star.md`**, those go through human PR only.
7. **Never propose changes to `learn.md`**, that's `learn.md`'s domain.

## Anti-patterns the critic must catch

| Anti-pattern | How to detect |
|---|---|
| Pipeline cheats by tightening kill threshold to "improve F1" | actor.md kill_dsr_threshold rose without FN rate impact study |
| Pipeline ships strategies with suspiciously identical IC across runs | check ic_series for non-stationarity / repeated values |
| Pipeline auto-kills papers with weak abstracts | sample 10 random `not_tradable` and verify they really aren't |
| LLM extraction hallucinates Sharpe values | cross-check claimed_sharpe in spec against PDF text |
| Code generator silently produces all-zero signal | check signal stdev > 0 across panel |
| Backtest overfits to OOS by re-running with new params | git log on backtest config, count revisions per fixture |

## Calibration thresholds for the critique itself

The critic is calibrated when:
- It correctly flags 100% of seeded adversarial issues (adversarial fixtures + intentionally broken runs)
- Its flagged issues lead to actor changes that REDUCE asymmetric loss in next 3 runs (verified by `learn.md`)
- Its CRITICAL flags are no more than 1 per 100 runs in steady state (otherwise the bar is too low)

## Evolution policy for THIS file

`critique.md` is updated by the meta-meta-loop in `learn.md`. The actor does NOT edit critique.md. Changes:
- Driven by analyzing whether past critiques actually improved outcomes
- Acceptance criteria: any change to critique.md must be A/B tested on at least 2 weeks of runs before becoming default
- Append a version-bump entry to the changelog at the bottom of this file

## Changelog

```
v0.1.0 (2026-05-01) | initial bootstrap with 6 critique categories, asymmetric severity scale
```
