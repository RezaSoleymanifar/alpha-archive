---
name: brainstorm-features
description: Use when the user asks to brainstorm new features for Alpha Archive aligned with north_star.md. Reads governance + roadmap + current state, then proposes a prioritized feature list mapped to north-star metrics with effort estimates.
---

# Brainstorm features (north-star aligned)

## When to use
- User asks "what should we build next?"
- User asks "brainstorm features"
- User asks "/brainstorm" (Alpha Archive variant)
- After a significant milestone, to plan the next ramp
- Quarterly planning

## Hard rule
**Every proposed feature MUST map to at least one north_star.md quality bar metric.** Features that don't move a north-star metric are out of scope. North-star metrics:
- False-negative rate < 2%
- False-positive rate < 10%
- Verdict accuracy on canonical fixtures ≥ 85%
- IC sign correctness ≥ 90%
- Replication score (measured/claimed Sharpe) on canon: 0.4-0.8
- Reproducibility 100%
- Asymmetric loss `L = 5·FN + 1·FP + 2·|repl_score − 0.6|` trending down

If a feature does not move any of these, do NOT propose it. Cut.

## Process

### Step 1, Load context (read in this order)
1. `meta/north_star.md`, the immutable goal + quality bar
2. `meta/actor.md`, current pipeline policy + calibration
3. `meta/critique.md`, how the system grades itself
4. `meta/community.md`, crowdsourcing layer state
5. `meta/learn.md`, meta-meta-loop policy
6. `docs/roadmap.md`, phased plan + phase markers
7. `data/meta_runs/metrics.jsonl` (if exists), recent platform metrics
8. `data/critique_runs/*.json` (if exist), recent critic findings
9. Top-level repo tree (Glob), what already exists vs. what's referenced

If any of these are missing, note that as a finding (skill assumes they exist).

### Step 2, Diagnose where the system is failing or thin
For each north-star metric, ask:
- What does the system currently do that addresses it?
- Where is the weakest link in the chain?
- Which fixtures (if any recent runs) flag failures here?

Examples of weak-link diagnoses:
- "FN rate unmeasured" → no critic agent → no FN tracking
- "Replication score for fundamentals-heavy anomalies = N/A" → no PIT fundamentals → blocked by data
- "DSR threshold platform-N inflation untracked" → no platform N counter
- "Self-improvement loop silent" → no learn aggregator running

### Step 3, Propose features (5-10 max, ranked)
Each feature gets a row in this template:

```
| # | Feature | Moves which metric | Effort | Prereqs | Risk if skipped |
|---|---------|--------------------|--------|---------|-----------------|
| 1 | Critic agent | FN rate (measurable) + asymmetric loss (computable) | M (3hr) | None | Meta-loop is theater; cannot self-improve |
| 2 | … | … | S/M/L | … | … |
```

Effort key:
- **S** = under 1 day
- **M** = 1-3 days
- **L** = 1-2 weeks
- **XL** = >2 weeks (decompose into smaller items)

Ranking criteria (in order):
1. **Unblocks measurement of north-star metrics** (you can't optimize what you don't measure)
2. **Highest expected reduction in asymmetric loss `L`**
3. **Lowest effort × highest leverage**
4. **Unblocks downstream features**

### Step 4, Sanity gates (apply before presenting)
For each proposed feature, check:
- [ ] Maps to a specific north-star metric (not vague "improves quality")
- [ ] Has a concrete acceptance test (e.g., "fixture set passes after deploy")
- [ ] Doesn't violate `north_star.md` "out of scope" list (no live execution, no proprietary alpha generation, no HFT, no crypto-native, no replacing fund DD)
- [ ] Doesn't require touching `north_star.md` or `learn.md` directly (those are immutable)
- [ ] Effort estimate is honest, not optimistic

Drop any feature that fails a gate. Re-rank.

### Step 5, Present
Output exactly this structure:

```
## Diagnosis
{1-3 paragraphs: what's working, what's not, where the system is blind}

## Proposed features (ranked)
| # | Feature | Moves | Effort | Prereqs | Risk |
|---|---------|-------|--------|---------|------|
{rows}

## Recommended sequence
{numbered list of which order to build, with brief why}

## What I'm NOT proposing (and why)
{optional but useful, list 2-4 features that came up but failed gates, with the gate that killed them}
```

## Anti-patterns to avoid

- **Don't propose UI / web features** unless they unblock a north-star metric (e.g., public landing pages = reproducibility audit trail = OK; pretty charts = NOT OK on their own)
- **Don't propose data-vendor expansions** without the corresponding metric impact (e.g., "add Sharadar" must justify what additional FN/FP rate it reduces, not just "more anomalies")
- **Don't propose ML model swaps** (e.g., "use Opus instead of Sonnet") unless there's a measured replication-quality gap
- **Don't propose growth/marketing features**, those belong in `docs/go-to-market.md`, not here
- **Don't propose anything in `north_star.md`'s out-of-scope list** (live execution, proprietary alpha, HFT, crypto-native, replacing fund DD)

## Output style

Concise. Bullet points + the table above. No marketing prose. The reader is the project owner deciding what to build next; assume they know the system.

If the user wants follow-up detail on a specific feature, they will ask.
