"""Areas and tasks, in the shape Papers With Code uses.

Their site works because a task is a page: one narrow, named problem with the
papers that attempt it listed side by side, so a reader lands on "Image
Classification" and sees the field rather than a search result. Flat tags cannot
do that: "portfolio" covers 429 papers here and answers nothing.

So the same two levels. An AREA is the wing of the building; a TASK is the room,
and the room is what a reader actually wants. A task earns its place only if
several papers attempt it and a replication of one could be compared against a
replication of another. Anything vaguer belongs in the area's catch-all.

Classification is deliberately single-primary. A paper appears on exactly one
task page, because a paper that appears everywhere makes every page useless.
Secondary tags stay as tags.
"""

from __future__ import annotations

import re
from typing import Any

# (area, task, blurb, pattern). Order matters: the first match wins, so the
# specific patterns are listed before the general ones inside each area.
TASKS: list[tuple[str, str, str, str]] = [
    # ---------------------------------------------------------- portfolios
    ("Portfolio Construction", "Index Tracking",
     "Reproduce an index with fewer names, trading as little as possible.",
     r"index track|tracking error|enhanced index|replicat\w+ the index|sparse index"),
    ("Portfolio Construction", "Mean-Variance Optimization",
     "The Markowitz problem and what has to be fixed to make it usable.",
     r"mean.variance|markowitz|efficient frontier|minimum.variance|tangency portfolio"),
    ("Portfolio Construction", "Risk Parity and Allocation",
     "Weighting by risk contribution rather than by conviction.",
     r"risk parity|equal risk|budget\w* allocation|hierarchical risk|diversification ratio"),
    ("Portfolio Construction", "Tactical Asset Allocation",
     "Rotating between assets on a signal instead of holding a fixed mix.",
     r"tactical|rotation|market timing|allocation rule|regime.aware portfolio|"
     r"overlay|glide path|dynamic allocation"),
    ("Portfolio Construction", "Portfolio Optimization",
     "Everything else that turns a set of assets into a set of weights.",
     r"portfolio|allocation|weights|kelly|utility maximi"),

    # ---------------------------------------------------------- prediction
    ("Forecasting", "Volatility Forecasting",
     "Predicting the size of the next move rather than its direction.",
     r"volatilit\w* forecast|garch|realized volatilit|stochastic volatilit|"
     r"variance forecast|\bHAR\b|vol.of.vol"),
    ("Forecasting", "Return Prediction",
     "Predicting direction or magnitude of returns from past observables.",
     r"return predict|price predict|forecast\w* return|stock predict|"
     r"directional forecast|equity premium"),
    ("Forecasting", "Regime Detection",
     "Identifying which state the market is in before acting on it.",
     r"regime|state.switching|markov switch|structural break|change.?point|"
     r"phase transition|turning point"),
    ("Forecasting", "Time Series Foundation Models",
     "General-purpose sequence models applied to financial series.",
     r"foundation model|TimesFM|Chronos|zero.?shot forecast|pretrained.*time series"),

    # ---------------------------------------------------------------- risk
    ("Risk", "Value at Risk and Expected Shortfall",
     "Quantile risk measures, and whether their breaches count out correctly.",
     r"value.at.risk|\bVaR\b|expected shortfall|\bES\b forecast|backtesting risk|"
     r"quantile risk|solvency"),
    ("Risk", "Tail Risk and Extremes",
     "The far end of the distribution, where the averages stop describing it.",
     r"tail risk|heavy tail|extreme value|tail depend|rogue wave|black swan|"
     r"tail index|hill estimator"),
    ("Risk", "Return Distributions",
     "Fitting what returns actually look like rather than assuming normality.",
     r"distribution of (stock |asset |financial )?returns|skew.?t|stable distribution|"
     r"tempered|jones.faddy|fat.?tail\w* distribution|moment\w* of returns"),
    ("Risk", "Drawdown and Downside Control",
     "Limiting how far a strategy falls, not just how much it varies.",
     r"drawdown|downside risk|loss control|capital preservation|CVaR|conditional value"),

    # -------------------------------------------------------- asset pricing
    ("Asset Pricing", "Factor Models",
     "Building and testing the systematic sources of return.",
     r"factor model|fama.french|risk factor|characteristic\w* sorted|"
     r"cross.section of (expected )?returns|principal component.*return"),
    ("Asset Pricing", "Anomaly Replication",
     "Re-testing published predictors, usually to find less than was claimed.",
     r"anomal|predictor\w* librar|replicat\w+ .*(finding|result|anomal)|"
     r"p.hacking|multiple testing|out.of.sample decay|open source asset pricing"),
    ("Asset Pricing", "Momentum and Reversal",
     "The two oldest cross-sectional effects and their many qualifications.",
     r"momentum|trend follow|reversal|mean.revers|relative strength"),
    ("Asset Pricing", "Correlation Structure",
     "What the covariance matrix does over time, and what survives cleaning.",
     r"correlation (matrix|structure|network)|covariance (matrix|estimat)|"
     r"random matrix|eigenvalue|shrinkage estimat|network of (stocks|assets)"),

    # ---------------------------------------------------------- derivatives
    ("Derivatives", "Option Pricing",
     "Valuing contingent claims under something other than Black-Scholes.",
     r"option pricing|black.scholes|implied volatilit|volatility surface|"
     r"levy process|heston|local volatilit|exotic option"),
    ("Derivatives", "Hedging",
     "Holding the offsetting position, and what it costs to keep holding it.",
     r"hedg\w+|delta.neutral|replication portfolio|greeks"),
    ("Derivatives", "Volatility Products",
     "VIX and the instruments written on volatility itself.",
     r"\bVIX\b|\bVXO\b|VSTOXX|variance swap|volatility index|term structure of vol"),

    # -------------------------------------------------------- microstructure
    ("Market Microstructure", "Optimal Execution",
     "Working an order without paying for the privilege.",
     r"optimal execution|market impact|\bTWAP\b|\bVWAP\b|implementation shortfall|"
     r"order splitting|almgren"),
    ("Market Microstructure", "Liquidity and Price Impact",
     "Measuring what it costs to trade, and when that cost moves.",
     r"liquidit|bid.ask spread|amihud|kyle.?s? lambda|price impact|market depth|"
     r"order flow|market maker"),

    # ------------------------------------------------------ alternative data
    ("Alternative Data", "Sentiment Analysis",
     "Turning text into a number a portfolio can act on.",
     r"sentiment|news analytic|social media|investor attention|textual analysis|"
     r"tone of|media coverage"),
    ("Alternative Data", "LLM Agents for Trading",
     "Language models placed in the decision loop rather than the feature set.",
     r"\bLLM\b|large language model|agentic|\bGPT\b|\bClaude\b|"
     r"language model.*(portfolio|trading|invest)"),
    ("Alternative Data", "Event Studies",
     "Measuring the reaction to a dated, identifiable event.",
     r"event study|announcement effect|merger|acquisition|earnings surprise|"
     r"abnormal return|insider tradin|form 4"),

    # --------------------------------------------------------------- crypto
    ("Crypto", "Crypto Asset Pricing",
     "Whether the equity toolkit survives contact with digital assets.",
     r"crypto|bitcoin|ethereum|digital asset|\bDeFi\b|token|stablecoin|on.chain"),

    # ----------------------------------------------------------------- macro
    ("Macro", "Term Structure",
     "The yield curve, and what its shape is worth predicting.",
     r"term structure|yield curve|interest rate model|bond yield|nelson.siegel"),
    ("Macro", "Macro-Financial Linkages",
     "Where the real economy shows up in asset prices.",
     r"macro|inflation|monetary polic|central bank|exchange rate|business cycle|"
     r"recession|\bGDP\b|unemployment"),
]

# Every area gets a home for papers that match it broadly but no task exactly.
CATCH_ALL = "General"

AREAS = list(dict.fromkeys(area for area, _, _, _ in TASKS))

# Tasks whose patterns are wide enough to catch a paper that belongs somewhere
# more specific. "portfolio" appears in a volatility-forecasting abstract as
# often as in a portfolio paper, so these are tried only after every narrow task
# in every area has failed, otherwise ordering inside one area silently
# outranks precision in another.
BROAD = {"Portfolio Optimization", "Macro-Financial Linkages", "Crypto Asset Pricing"}

_COMPILED = [(area, task, blurb, re.compile(pattern, re.I))
             for area, task, blurb, pattern in TASKS]
_NARROW = [t for t in _COMPILED if t[1] not in BROAD]
_BROAD = [t for t in _COMPILED if t[1] in BROAD]

BLURBS = {(area, task): blurb for area, task, blurb, _ in TASKS}


def classify(text: str) -> tuple[str, str]:
    """The single task a paper belongs on, and its area.

    Narrow tasks are tried first across every area, then the wide ones. A paper
    forecasting volatility with an LLM lands on volatility forecasting rather
    than on the LLM page, and one that forecasts volatility to size a portfolio
    lands there too rather than under portfolio optimization. The subject a
    reader would compare across papers wins; the technique stays a tag.
    """
    for area, task, _, pattern in _NARROW:
        if pattern.search(text or ""):
            return area, task
    for area, task, _, pattern in _BROAD:
        if pattern.search(text or ""):
            return area, task
    return "Asset Pricing", CATCH_ALL


def tags_for(text: str, limit: int = 4) -> list[str]:
    """Every task pattern a paper touches, as secondary labels."""
    hit = [task for _, task, _, pattern in _COMPILED if pattern.search(text or "")]
    return list(dict.fromkeys(hit))[:limit]


def tally(papers: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Areas and tasks with their counts, for the navigation pane.

    Empty tasks are dropped. A taxonomy is a promise that a page has something
    on it, and Papers With Code does not list rooms with nothing in them.
    """
    counts: dict[tuple[str, str], int] = {}
    for paper in papers:
        key = (paper.get("area"), paper.get("task"))
        counts[key] = counts.get(key, 0) + 1

    out = []
    for area in AREAS:
        # CATCH_ALL is already a key in `counts` when anything landed there, so
        # appending it separately listed it twice.
        tasks = [{"task": task, "count": counts[(a, task)],
                  "blurb": BLURBS.get((a, task), "")}
                 for (a, task) in counts if a == area]
        if not tasks:
            continue
        tasks.sort(key=lambda t: -t["count"])
        out.append({"area": area, "count": sum(t["count"] for t in tasks), "tasks": tasks})
    out.sort(key=lambda a: -a["count"])
    return out
