"""What RGRR has to hit, written down before any of it was built.

arXiv 2607.06117 — a two-ETF rule that maps screened QQQ-DIA relative states and
macro relief states into a continuous QQQ weight. Table 16 reports it across
four out-of-sample start dates, which is the reason this paper was picked first:
one window could be luck, four windows with a rule this intricate could not be.

The tolerances below are the entire argument, so here is the reasoning, fixed
in advance and not to be revisited once a number comes back.

CAGR, +/- 0.50pp. Yahoo's adjusted closes are restated whenever a distribution
is reclassified, so two people pulling QQQ on different days get slightly
different histories. Half a point over eighteen years is that noise and not much
more. Anything wider would let a materially different rule pass.

Sharpe, +/- 0.05. Daily Sharpe over thousands of observations is stable, and the
paper states it to two decimals. A tolerance smaller than its own precision
would be theatre.

Max drawdown, +/- 1.00pp. A drawdown is one path through one pair of days, so it
moves more than an average does under small data differences, and it does not
average out over the sample the way CAGR does.

Turnover, +/- 30pp on a base of roughly 400pp, so about 7 percent relative.
Turnover is the most fragile statistic here: it depends on the exact rebalance
calendar and on how a weight change smaller than a tick is treated. This is the
one place a wide band is honest rather than convenient.

Attribution alpha, +/- 0.60pp with the t-statistic reported alongside. The paper
reports 3.57% at t=2.72 for QQQ excess return; matching the point estimate while
missing significance would not be a replication of the claim.

A window counts as replicated only when CAGR, Sharpe and max drawdown all clear.
Turnover is reported and judged but does not gate, because the paper's cost model
is stated at 10bps one-way and any turnover difference is already priced into the
CAGR that does gate. Saying that here, in advance, is the point.
"""

from __future__ import annotations

from ..verification import ScalarTarget

PAPER = "2607.06117"
TITLE = "Regime-Gated Relative Rotation between QQQ and DIA"
COST_BPS = 10.0          # one-way, as stated in the paper
HORIZONS = (21, 63, 126)

# The four out-of-sample starts Table 16 reports, all ending 2026-07-02.
WINDOWS = {
    "2008": "2008-07-25",
    "2018": "2018-06-28",
    "2020": "2020-01-02",
    "2022": "2022-01-03",
}
END = "2026-07-02"

# Gating statistics. A window is replicated when all three clear.
GATING = ("cagr", "sharpe", "max_drawdown")

_WHY = {
    "cagr": "Yahoo restates adjusted closes when distributions are reclassified; "
            "half a point over eighteen years is that noise.",
    "sharpe": "Daily Sharpe over thousands of observations is stable, and the "
              "paper states it to two decimals.",
    "max_drawdown": "A drawdown is one path through one pair of days, so it moves "
                    "more than an average under small data differences.",
    "turnover": "Depends on the exact rebalance calendar and on how sub-tick "
                "weight changes are treated. Reported, but not gating.",
}
_TOL = {"cagr": 0.50, "sharpe": 0.05, "max_drawdown": 1.00, "turnover": 30.0}
_UNITS = {"cagr": "%", "sharpe": "", "max_drawdown": "%", "turnover": "%"}

# Table 16, transcribed from the paper. RGRR and the three static baselines.
#   window -> arm -> {cagr, sharpe, max_drawdown, turnover}
TABLE_16: dict[str, dict[str, dict[str, float]]] = {
    "2008": {
        "RGRR": {"cagr": 16.85, "sharpe": 0.97, "max_drawdown": -29.25, "turnover": 505.89},
        "QQQ": {"cagr": 19.22, "sharpe": 0.95, "max_drawdown": -35.12},
        "DIA": {"cagr": 13.88, "sharpe": 0.84},
        "50/50": {"cagr": 16.75, "sharpe": 0.95},
    },
    "2018": {
        "RGRR": {"cagr": 18.33, "sharpe": 0.94, "max_drawdown": -29.41, "turnover": 444.60},
        "QQQ": {"cagr": 20.50, "sharpe": 0.89, "max_drawdown": -35.12},
        "DIA": {"cagr": 12.41, "sharpe": 0.72},
        "50/50": {"cagr": 16.69, "sharpe": 0.86, "max_drawdown": -32.28},
    },
    "2020": {
        "RGRR": {"cagr": 18.69, "sharpe": 0.93, "max_drawdown": -29.41, "turnover": 408.16},
        "QQQ": {"cagr": 21.29, "sharpe": 0.90},
        "DIA": {"cagr": 11.98, "sharpe": 0.67},
        "50/50": {"cagr": 16.88, "sharpe": 0.84},
    },
    "2022": {
        "RGRR": {"cagr": 15.19, "sharpe": 0.87, "max_drawdown": -23.62, "turnover": 354.33},
        "QQQ": {"cagr": 14.65, "sharpe": 0.70, "max_drawdown": -34.83},
        "DIA": {"cagr": 10.64, "sharpe": 0.75},
        "50/50": {"cagr": 12.93, "sharpe": 0.76},
    },
}

# Table 5, the static baselines over the full 2008-07-25 to 2026-07-02 sample.
# These gate nothing about RGRR itself but they are the cheapest possible check
# that the price data was assembled correctly — if buy-and-hold QQQ does not
# come out at 17.17%, nothing downstream is worth reading.
TABLE_5 = {
    "DIA": {"cagr": 11.65, "sharpe": 0.66, "max_drawdown": -44.54},
    "50/50": {"cagr": 14.62, "sharpe": 0.78, "max_drawdown": -45.53},
    "QQQ": {"cagr": 17.17, "sharpe": 0.82, "max_drawdown": -47.83},
}

# Table 7, the factor attribution. Alphas are annualised percentages.
TABLE_7 = {
    "QQQ excess return": {"alpha": 3.57, "t": 2.72, "r2": 0.92},
    "DIA excess return": {"alpha": -0.62, "t": -0.41, "r2": 0.86},
    "QQQ-DIA relative": {"alpha": 4.19, "t": 1.92, "r2": 0.38},
}
ALPHA_TOLERANCE = 0.60


def targets_for(window: str, arm: str = "RGRR") -> list[ScalarTarget]:
    """Frozen targets for one arm in one out-of-sample window."""
    published = TABLE_16[window][arm]
    out = []
    for stat, value in published.items():
        out.append(ScalarTarget(
            name=f"{arm} {window} {stat.replace('_', ' ')}",
            published=value,
            tolerance=_TOL[stat],
            units=_UNITS[stat],
            table=f"Table 16, {window} out-of-sample",
            rationale=_WHY[stat],
        ))
    return out


def baseline_targets() -> list[ScalarTarget]:
    """Buy-and-hold checks. If these miss, the data is wrong, not the rule."""
    out = []
    for arm, published in TABLE_5.items():
        for stat, value in published.items():
            out.append(ScalarTarget(
                name=f"{arm} buy-and-hold {stat.replace('_', ' ')}",
                published=value,
                tolerance=_TOL[stat],
                units=_UNITS[stat],
                table="Table 5, 2008-07-25 to 2026-07-02",
                rationale=(
                    "A static hold has no free parameters, so a miss here is a data "
                    "assembly error and nothing downstream is worth reading."
                ),
            ))
    return out


def all_targets() -> list[ScalarTarget]:
    out = baseline_targets()
    for window in WINDOWS:
        out += targets_for(window)
    return out
