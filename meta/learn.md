# LEARN, meta-meta loop that improves the critique itself (mutable, slow-moving)

This file defines HOW the system learns to critique better over time. It analyzes the git history of `critique.md` and `actor.md` against actual platform-quality outcomes (asymmetric loss trend, fixture pass rate). Its job is to propose updates to `critique.md` so future critiques produce more north-star-aligned actor changes.

## Version

v0.1.0: initial bootstrap

## What learn does

1. Periodically (weekly cron in production) read:
   - `git log meta/actor.md`, every actor change + its commit message
   - `git log meta/critique.md`, every critique-rule change + its commit message
   - `data/meta_runs/metrics.jsonl`, platform metrics time series
   - `data/critique_runs/*.json`, every critique report (planned)
2. Compute "did each critique actually help?" by attributing actor changes to upstream critiques and measuring downstream metric impact
3. Identify critique rules that are:
   - **Effective** (lead to changes that improve `L`)
   - **Ineffective** (lead to changes that don't move `L`)
   - **Counterproductive** (lead to changes that worsen `L`)
4. Propose updates to `critique.md` to amplify effective rules and prune counterproductive ones

## Causal attribution model

For each actor commit `c_a`:
- Find the most recent critique commit `c_c` that PRECEDED `c_a` and was REFERENCED in `c_a`'s commit message (e.g., "addresses critique #42")
- Find the next 3 platform metric snapshots after `c_a`
- Attribute the delta `Δ L` (loss change) to `c_c`'s suggestion

Aggregate per critique rule:
```
attribution[rule_X] = mean(Δ L) for all actor commits caused by critiques citing rule_X
```

Rules with `attribution < 0` (loss decreased = good) get amplified.
Rules with `attribution > 0` (loss increased = bad) get pruned or refined.

## Decision policy for critique updates

| Attribution evidence | Action |
|---|---|
| Rule fired ≥ 5 times AND attribution < -2 (improves L) | promote: make rule more prominent / strict |
| Rule fired ≥ 5 times AND attribution > +2 (degrades L) | demote: weaken or remove rule |
| Rule fired ≥ 5 times AND |attribution| < 1 (no signal) | keep but flag as low-impact |
| Rule fired < 5 times | needs more data, no change yet |

Minimum cooldown: any rule change must persist ≥ 2 weeks before another change. Prevents thrashing.

## Anti-Goodhart safeguards

The biggest risk: critique optimizes for a measurable proxy that diverges from the north star.

Defenses:
1. **Frozen reference fixtures**: a held-out subset of fixtures (≥ 30% of total) is NEVER used in attribution. Used purely as ground-truth check that learn isn't gaming the metric.
2. **Periodic human audit**: every 90 days, human reviewer samples 10 random critique-driven actor commits and grades whether they were genuine improvements
3. **Proposal-only**: learn produces PR drafts to critique.md; humans must approve. Auto-merge is never enabled for critique changes.
4. **Multi-metric**: learn tracks 5+ metrics (asymmetric loss, FN count, FP count, replication score variance, fixture verdict accuracy). Critique change requires ≥ 3 to improve.

## Operational loop

```
WEEKLY at SUN 00:00 UTC:
1. snapshot current platform metrics + fixture pass rates
2. read git log of actor.md + critique.md since last snapshot
3. attribute each actor change to its upstream critique (by commit message reference)
4. compute attribution[rule] aggregate
5. identify candidate critique.md edits
6. open GitHub PR titled "learn: propose critique.md updates {date}"
7. PR body includes:
   - attribution table
   - proposed diff
   - 5 example past runs where the change would have produced different feedback
   - safeguard checks (held-out fixtures still pass, multi-metric improvement evidence)
8. human reviewer approves or rejects
```

## Inputs learn must read

- `git log --follow meta/actor.md` (use `git log -p` for diffs)
- `git log --follow meta/critique.md`
- `data/meta_runs/metrics.jsonl` (per-run platform metrics)
- `data/critique_runs/*.json` (per-run critique reports, planned)
- `data/fixture_runs/*.json` (per-fixture historical results)

## Outputs learn produces

- `data/learn_runs/{date}_attribution.json` (rule-level attribution)
- `data/learn_runs/{date}_proposal.md` (proposed critique.md diff + rationale)
- GitHub PR draft with the proposal

## Bootstrap problem

Until enough actor commits accumulate (~20+), attribution is noisy. Bootstrap policy:
1. First 4 weeks: learn ONLY observes; produces attribution reports without proposing changes
2. Weeks 5-8: learn proposes "low-risk" changes only (clarifications, severity tweaks). No new rules.
3. After week 9: full operation including new-rule proposals

## Hard constraints

- Learn MUST NOT edit `north_star.md`
- Learn MUST NOT directly edit `actor.md` (only critique can suggest, actor decides)
- Learn MUST NOT auto-merge any of its own proposals
- Learn MUST log every analysis run to `data/learn_runs/`
- Learn MUST preserve the held-out fixture set (rotate quarterly with human approval)

## Failure modes learn must guard against

| Failure | Mitigation |
|---|---|
| Optimizes critique for short-term loss reduction at long-term quality cost | held-out fixture set; quarterly human audit |
| Removes critique rules that catch rare-but-critical issues | severity gate: never auto-prune CRITICAL-tagged rules |
| Causes actor to thrash on conflicting critiques | cooldown period; max 1 critique change per fortnight |
| Misattributes actor improvements to wrong critique | require explicit critique-id reference in actor commit message; reject auto-merge if attribution chain broken |
| Becomes more permissive over time (rule-pruning bias) | track total rule count + severity distribution; alert if drift |

## Health metrics for learn itself

- Time from problem detection → actor change: target < 14 days
- % of proposed critique changes accepted by human: target 50-80% (too high = rubberstamp; too low = bad proposals)
- Held-out fixture pass rate: should not degrade over 90 days
- Asymmetric loss trend: should be flat or down over 90 days

## Evolution policy for THIS file

`learn.md` itself is meta-meta and changes only by human PR. Self-modification of learn.md is explicitly forbidden. This is the bedrock, if learn could rewrite its own rules, the whole self-improvement system has no anchor.

## Changelog

```
v0.1.0 (2026-05-01) | initial bootstrap with attribution model + anti-Goodhart safeguards
```
