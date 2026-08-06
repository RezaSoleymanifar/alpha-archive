# Meta, agent operating system

Five files that govern how the agent self-improves:

```
meta/
├── north_star.md   IMMUTABLE, the goal. Human-PR only.
├── actor.md        MUTABLE, current pipeline policy. Actor edits, must align with north_star.
├── critique.md     MUTABLE, how to evaluate the actor. Edited only by learn.md proposals.
├── community.md    MUTABLE, crowdsourcing layer governing human-in-the-loop contributions.
└── learn.md        IMMUTABLE, meta-meta loop that improves critique + community. Human-PR only.
```

## Loop

```
                    ┌───────────────┐
                    │  north_star   │  ← immutable goal
                    └───────┬───────┘
                            │ aligns to
                            ▼
   ┌──────────┐         ┌────────┐         ┌────────────┐
   │  actor   │ ──runs──▶│pipeline│ ──emits─▶│   results  │
   └────▲─────┘         └────────┘         └─────┬──────┘
        │                                        │
        │ updates self                           │ feeds
        │ in response to                         ▼
        │                            ┌─────────────────────┐
        └────────reads───────────────│ critique  │ community │  ← parallel evidence
                                     │           │   notes   │     sources
                                     └────┬──────┴────┬──────┘
                                          │ both       │
                                          │ aggregated │
                                          ▼ by         ▼
                                       ┌──────────────────┐
                                       │       learn      │ ← improves critique +
                                       └──────────────────┘   community rules
                                          (weekly, human-PR)
```

## Roles

- **north_star.md**, defines the optimization objective + quality bar. Never changes without human approval.
- **actor.md**, defines current pipeline policy + calibration. Self-edits in response to critique. All edits via git for auditability.
- **critique.md**, defines how to grade actor's outputs. Updated by learn's proposals (human-approved).
- **community.md**, governs crowdsourced contributions (challenges, alternatives, annotations). Twitter-Community-Notes-style bipartisan agreement; reputation system; AI-driven scraper for external mentions.
- **learn.md**, meta-meta: analyzes git history of actor + critique + outcome metrics + community signals, proposes improvements. Never self-modifies.

## Why 5 layers

| Layer | Mutability | Edited by | Defends against |
|---|---|---|---|
| north_star | immutable | human only | Goodhart on the objective itself |
| actor | mutable | actor | Pipeline becomes static / can't improve |
| critique | mutable | learn (proposed), human (approved) | Critique becomes biased / blind |
| community | mutable | learn (proposed), human (approved) | AI critique drifts from real practitioners |
| learn | immutable | human only | Self-improvement loop optimizes away from the goal |

Each layer's mutability is one less than the layer below it. This prevents any layer from rewriting its own constitution.

Critique and community are PARALLEL evidence sources (neither dominates), both feed `learn` which arbitrates.

## Operational cadence

| Cadence | Action |
|---|---|
| Per pipeline run | actor executes; critique evaluates and writes report |
| Daily | actor commits any policy updates from accumulated critiques |
| Weekly | learn analyzes attribution, opens PR with critique improvements |
| Quarterly | human audit: sample critique-driven actor commits, validate improvements were genuine |

## Invariants

These must hold at all times:
1. north_star.md hash is in the build manifest
2. Every actor.md commit references at least one critique report ID in its message
3. Every critique.md change came through a learn-proposed PR
4. learn.md never appears in `git log --author=actor` or `git log --author=critique`
5. Held-out fixture set passes at all times (≥ 95% verdict accuracy)

## How to inspect the system's health

```bash
# Latest platform metrics
cat data/meta_runs/metrics.jsonl | tail -1

# Recent actor evolution
git log -p meta/actor.md | head -100

# Recent critique evolution
git log -p meta/critique.md | head -100

# Asymmetric loss trend (last 10 runs)
jq '.asymmetric_loss' data/meta_runs/metrics.jsonl | tail -10

# Fixture pass rate
uv run python examples/run_meta_loop.py
```
