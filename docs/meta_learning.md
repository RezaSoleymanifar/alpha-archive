# Meta-learning loop, how the agent learns from mistakes

## The problem

LLM-driven pipelines have failure modes at every step:

| Step | False positive | False negative |
|---|---|---|
| Triage | Wastes compute on non-tradable paper | **Rejects a real signal, main risk** |
| Spec extraction | Wrong formula → garbage backtest | Misses key parameter, signal looks weak |
| Code generation | Lookahead bias → fake-good Sharpe | Bug zeroes out signal, fake-bad |
| Backtest | Wrong CV → over-optimistic | Under-powered → false null |
| Verdict | Ship a noise factor | Kill a real factor |

Without a feedback loop, the platform has no idea which side it's failing on. Replicates 1000 papers, but doesn't know if 200 of them were missed alpha or 200 were false positives.

The meta-learning loop closes this gap.

## Core mechanism: ground-truth fixtures

A **fixture** is a paper with KNOWN expected outcome:

```python
{
    "paper_id": "jegadeesh_titman_1993",
    "title": "Returns to Buying Winners and Selling Losers",
    "expected_verdict": "ship",
    "expected_signal_sign": "+",
    "expected_ic_min": 0.02,        # has been replicated in 1000+ studies
    "expected_sharpe_post_costs": (0.4, 0.9),   # range from literature
    "expected_oos_decay": (0.3, 0.6),  # 30-60% post-pub per McLean & Pontiff
    "ground_truth_source": "Asness 2014 (replication), Hou-Xue-Zhang 2018",
}
```

Fixtures are vetted by humans (you), not auto-generated. ~20 cover the canon (FF3, FF5, momentum, BAB, quality, value, PEAD, insider trading, low-vol, etc.).

## What the loop does

```
1. RUN PIPELINE on every fixture monthly
   - triage → extract → codegen → backtest → verdict

2. MEASURE per fixture:
   - triage_correct?    (matched expected_verdict)
   - extraction_match?  (formula extracted correctly?)
   - code_correct?      (does it compute the right thing?)
   - backtest_match?    (Sharpe within expected range?)
   - verdict_correct?   (final ship/kill matched ground truth?)

3. AGGREGATE platform-level:
   - triage precision, recall, F1
   - extraction accuracy
   - replication score distribution
   - false-positive rate per verdict tier
   - false-negative rate per verdict tier

4. ALERT on regressions:
   - if any fixture flips verdict, page owner
   - if F1 drops > 5% week-over-week, freeze production updates

5. CALIBRATE thresholds:
   - if FN rate too high → loosen DSR threshold OR add second-opinion model
   - if FP rate too high → tighten thresholds

6. PROMPT TUNING:
   - failed fixtures generate negative examples for prompt refinement
   - success cases become few-shot examples
```

## Defensive layers (each independently reduces error)

### Layer 1: Self-consistency

Run extraction twice with slightly different prompts. Disagreement = flag for review.

```python
def self_consistent_extract(paper) -> tuple[Spec, float]:
    spec_a = extract(paper, seed=0)
    spec_b = extract(paper, seed=42, prompt_variant="restated")
    agreement = compare_specs(spec_a, spec_b)  # cosine sim of feature vectors
    if agreement < 0.85:
        return spec_a, agreement   # mark for human review
    return spec_a, agreement
```

### Layer 2: Multi-model ensemble (asymmetric voting)

Triage with both Haiku + Sonnet. Only mark "not tradable" if **both agree**. This biases toward false positives (cheap to filter later) and away from false negatives (irrecoverable).

```python
def triage_safe(paper) -> str:
    haiku_says = triage_haiku(paper)
    if haiku_says == "tradable":
        return "tradable"  # cheap model says yes → trust
    # haiku says not_tradable, verify with sonnet before discarding
    sonnet_says = triage_sonnet(paper)
    return sonnet_says
```

### Layer 3: Code validation gates

Before backtest runs, generated code must pass static checks:

```python
VALIDATIONS = [
    no_lookahead,           # no .shift(negative_int) outside of forward_return
    returns_proper_shape,   # output dim matches universe
    no_nan_explosion,       # > 50% NaN rejected
    deterministic,          # seed=N produces same output
    bounded_runtime,        # < 60s on 5yr SP500
    no_external_io,         # no urllib, sockets, file writes
]
```

### Layer 4: Replication score telemetry

For each fixture, track `claimed_sharpe / measured_sharpe`. Platform-wide:

```
mean_replication_score = mean(measured / claimed across fixtures)
```

- If mean drops below 0.4 → likely systematic methodology issue (cost too high? data wrong?)
- If mean above 1.5 → likely lookahead bias creeping in
- Calibrate cost model + CV strategy until score stabilizes near literature norm (~0.5-0.7 post-pub)

### Layer 5: Active learning queue

Uncertain cases go to human review. Reviewer's verdict becomes:
- New fixture (if novel ground truth)
- Few-shot example for prompt refinement
- Reward signal for fine-tuning later

```python
UNCERTAIN_TRIGGERS = [
    "self_consistency_score < 0.85",
    "triage_haiku != triage_sonnet",
    "DSR in [0.4, 0.6]  # borderline ship/iterate",
    "abs(replication_score - 1.0) > 0.7  # huge gap from claim",
    "code_validation_warnings > 0",
]
```

### Layer 6: Asymmetric verdict thresholds

False negative cost ≫ false positive cost (we lose a good signal forever vs we waste 30s of compute).

So:
- Default verdict bias: lean toward "iterate" not "kill"
- "kill" requires: DSR < 0.3 AND OOS Sharpe < 0 AND reviewer-confirmed

Result: low FN rate at cost of slightly higher manual review burden.

## Drift monitoring

The platform's behavior shifts over time:
- LLM model updates (Anthropic releases new Sonnet)
- Data source quality changes (yfinance API changes)
- Cost model recalibration

Drift detection:
- Re-run all fixtures on every model release
- Compare verdict distribution before/after
- If > 1 fixture flips verdict → block deployment, investigate

## Loss function for the platform

```
L = α · false_negatives + β · false_positives + γ · |replication_score - 0.6|

Default weights:
α = 5    # losing a real signal is expensive
β = 1    # false positive easy to filter downstream
γ = 2    # systematic miscalibration is bad
```

Track L weekly. Alert on uptick.

## Self-improvement loop

Every quarter:
1. Pull all fixture verdicts of last 90 days
2. Identify worst-performing categories (e.g., "options vol papers consistently misverdicted")
3. Generate prompt updates targeting that category
4. A/B test new prompt: 50% of next 100 papers go through new prompt
5. Compare F1; promote winner

This is the meta-learning loop in production: the system learns which paper types it fails on, and adapts.

## Open questions / future work

- **Reinforcement from human reviews**: each manual review = labeled example. After 1000 reviews, fine-tune a triage model.
- **Ensemble across methodologies**: run paper through 3 different CV schemes; report ensemble verdict if they disagree.
- **Author Q&A loop**: for high-stakes papers, post extracted spec publicly and let original author validate.
- **Adversarial fixtures**: construct papers that should be killed (fake patterns, p-hacked) and verify pipeline catches them.

## Bottom line

Without ground-truth fixtures, the agent flies blind. With them, every change to prompts, models, or methodology is testable. **Fixtures are the unit tests of LLM-driven research.**
