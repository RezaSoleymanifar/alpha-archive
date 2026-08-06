# COMMUNITY, crowdsourcing layer (mutable, governs human-in-the-loop)

This file defines HOW community contributions interact with the AI pipeline. The community layer is a **third evidence source** alongside (1) automated backtests against fixtures and (2) LLM-driven critique. It exists to catch what AI misses: domain-expert nuance, paper-author corrections, methodology subtleties.

## Version

v0.1.0: initial bootstrap

## Position in the meta system

```
                   ┌───────────────┐
                   │  north_star   │  immutable
                   └───────┬───────┘
                           │
    ┌──────────────┬───────┴───────┬──────────────┐
    │              │               │              │
    ▼              ▼               ▼              ▼
┌────────┐   ┌─────────┐    ┌──────────┐  ┌───────────┐
│ actor  │   │critique │    │community │  │  fixtures │
│        │   │         │    │  notes   │  │           │
└────────┘   └─────────┘    └──────────┘  └───────────┘
   │              │               │              │
   └────────────┬─┴───────────────┴──────────────┘
                ▼
          ┌──────────┐
          │  learn   │  weekly aggregator (immutable)
          └──────────┘
```

Community sits **alongside** critique, not above it. Both feed evidence to learn; learn arbitrates.

## What a community contribution is

A structured submission attached to a `Result` row. Three kinds:

### 1. Challenge

> "Alpha Archive's replication of [paper X] is wrong because [evidence]."

Required fields:
- `paper_id` (which Alpha Archive result is being challenged)
- `claim` (what's wrong, ≤ 500 chars)
- `evidence_type`: `text_quote_from_paper` | `alternative_code` | `external_replication` | `published_critique`
- `evidence_payload` (the quote, code, link, or DOI)
- `proposed_remediation`: `change_spec` | `change_code` | `change_universe` | `change_horizon` | `flag_unreproducible`

### 2. Alternative implementation

> "Here's a different implementation that produces a different verdict."

Required:
- `paper_id`
- `signal_code` (Python, must pass same validation gates as AI-generated)
- `rationale` (why this is better)
- `expected_delta` (predicted change in Sharpe / verdict)

### 3. Annotation

> "This paper has [important context] that doesn't change the verdict but readers should know."

Required:
- `paper_id`
- `annotation_text`
- `category`: `historical_context` | `regulatory_change` | `data_caveat` | `replication_attempt_elsewhere`

## Verification process (Community Notes-style)

Every contribution goes through these gates:

### Gate 1, automated screening

LLM judges:
- Is it on-topic? (matches paper)
- Is it specific? (not vague "could be better")
- Does evidence support claim? (LLM cross-checks payload)
- Is it likely spam / low effort?

Pass → enters voting queue.
Fail → rejected with reason; submitter can appeal.

### Gate 2, automated backtest verification (for code submissions only)

For `alternative_implementation` and code-changing `challenges`:
- Run proposed code through standard backtest pipeline
- Compute delta in: Sharpe, IC, replication score, verdict
- Attach measured impact to the submission for voters to see

### Gate 3, community voting

Each submission collects votes:
- `agree` / `disagree` / `not_qualified_to_judge`
- Voter must have rep ≥ 50 (basic threshold)
- Voter cannot vote on own submission
- Vote weight = sqrt(reputation), capped at 10×

### Gate 4, bipartisan-agreement check (the Community Notes mechanic)

Compute agreement across reviewer **factions**. Factions are inferred from past voting patterns:
- "AI-trusters": consistently vote against challenges
- "AI-skeptics": consistently vote for challenges
- "Neutral": balanced history

A submission requires **agreement from ≥ 2 factions** to merge. Same-faction-only consensus = NOT enough. Prevents both unconditional rubber-stamping and unconditional contrarianism.

### Gate 5, governance tier

| Tier | Definition | Merge rule |
|---|---|---|
| **T1** | Annotation only, no verdict change | Auto-merge after 24h if Gate 1-4 pass |
| **T2** | Code or spec change, no verdict flip | Single human moderator approval after Gate 4 |
| **T3** | Verdict flip (ship→kill or vice versa) | Two-moderator approval + 7-day public comment window |

Moderators are appointed by humans with ≥ 1000 reputation OR explicit appointment by repo owner.

## Reputation system

| Action | Δ rep |
|---|---|
| Submission accepted (T1) | +5 |
| Submission accepted (T2) | +20 |
| Submission accepted (T3) | +100 |
| Submission rejected (Gate 1 spam) | −10 |
| Submission rejected (failed Gate 4 vote) | 0 |
| Vote with eventual majority | +1 |
| Vote against eventual majority | −1 (but capped, can't go negative for Gate-5-overridden cases) |
| Comment marked helpful (≥ 5 upvotes) | +3 |
| Comment marked spam | −5 |

Starting rep: 10 (just enough to vote)
Voting threshold: 50
Submission threshold: 0 (anyone can submit, gates filter)
Moderator threshold: 1000

## Anti-abuse

1. **Auth required**: GitHub OAuth or verified email
2. **Rate limits**: 5 submissions / day, 50 votes / day
3. **Sybil detection**: account creation date, GitHub activity, IP rotation flags
4. **No paid voting**: rep cannot be bought; staking optional in long-term roadmap (Numerai-style)
5. **Authorial disclosure**: if submitter claims to be paper author, must sign w/ email matching paper, flagged as `author_submission`
6. **Cooldowns**: same paper can't have > 5 simultaneous challenges (forces consolidation)

## AI-driven scraping (minimal scope, signal over noise)

We DO NOT scrape Twitter/X, Reddit, or Substack. Those channels are 99% noise; mining them costs more in spam-filtering than the signal yields. Per the principle "signal over noise", critics come to us.

Active scraping (autonomous, daily):
1. **GitHub issues** on the Alpha Archive repo, anyone can file an issue to challenge a verdict; LLM auto-classifies it into a Tier-1 community_signal
2. **Replies on Alpha Archive-published landing pages** (when web UI ships, Phase 4), comments + "this is wrong" buttons
3. **Email submissions** to a published address (Phase 4)

That's it. No social-media trawl. Twitter et al. may be revisited in Phase 6+ if and only if a high-precision filter exists.

## Interaction with critique.md

The critic now has a NEW input: community signals attached to recent results.

Specifically:
- If ≥ 3 verified challenges exist on a recent `ship` verdict → critic flags as HIGH severity for actor review
- If a community-merged alternative implementation outperforms baseline → critic auto-proposes promoting alternative to baseline
- If repeated low-quality submissions on same paper → critic flags as potential spam coordination

## Interaction with learn.md

Learn now also reads:
- `data/community_runs/` (per-day rollup of community activity)
- `git log` on `alpha_archive/baselines/` (where merged community implementations live)

Attribution model extends:
- Did community-merged change reduce asymmetric loss in next 4 weeks? → amplify rules that surfaced it
- Did community challenge correctly predict a baseline failure? → add contributor's pattern to actor heuristics

## Hard constraints

- Community contributions can NEVER edit `north_star.md`, `learn.md`, `community.md`
- Community-merged code MUST pass the same sandbox gates as AI-generated code
- T3 verdict flips MUST be human-moderator approved; AI alone cannot flip on community input
- Every merged change is permanently versioned in git (no in-place mutation)
- Disclosure of conflicts of interest required for paper-author submissions

## Failure modes guarded against

| Failure | Mitigation |
|---|---|
| Coordinated brigading flips verdict on real signal | Bipartisan-agreement gate; T3 requires 7-day window |
| Community converges on wrong answer | Frozen fixture set acts as ground truth; AI critique remains independent |
| AI scraper amplifies low-quality external takes | Scraper produces signals, not auto-merged changes; humans gate everything |
| Reputation farming | Cap on rep gain per period; rep-decay for inactive accounts |
| Moderators captured by single faction | Periodic re-confirmation by repo owner; faction balance audit |
| Authors disputing legitimate replications | Disclosure flag + adjudication process; baseline never silently changes on author push |

## Operational cadence

| Cadence | Action |
|---|---|
| Per submission | Gate 1 + 2 run synchronously |
| Hourly | Gate 4 vote tally check; auto-promote what passes |
| Daily | Scraper run; reputation decay; spam audit |
| Weekly | Faction recompute; moderator activity review |
| Quarterly | Full reputation re-baseline; governance review |

## Bootstrap

Until reputation distribution + faction signal matures (~3 months minimum):
- All T2/T3 submissions require human moderator approval (no auto-merge)
- Bipartisan-agreement gate uses simple majority (waiver until factions stabilize)
- Reputation thresholds halved (vote ≥ 25, mod ≥ 500)

## Evolution policy for THIS file

`community.md` changes follow same rule as `critique.md`: proposed by `learn.md`'s analysis (or human PR), require explicit human approval, log changelog at bottom.

## Changelog

```
v0.1.0 (2026-05-01) | initial bootstrap with 3 contribution types, 5 gates, reputation system, Community-Notes-style bipartisan agreement
```
