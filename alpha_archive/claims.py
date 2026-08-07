"""Does the paper's number survive the checks the paper did not run?

A replication that reports its own Sharpe next to the published one answers
"did we reproduce it". That is the easy half. The harder half is whether the
published number would have survived the standard corrections, and most papers
predate them or skip them:

  * a t-statistic that assumes independent daily returns, when they are not
  * a single sample, when the result may live in one stretch of it
  * a number selected from however many specifications were tried to find it
  * a sample too short for the trial count behind it

`vintage.engine.validation` implements those. This module points them at a
replication and prints the gap.

The rule from `verification.py` holds here too: every threshold is declared in
`GATES` before a run and frozen. A verdict that could be argued into existence
after seeing the number is not a verdict.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Sequence

from vintage.engine import validation

TRADING_DAYS = 252


@dataclass(frozen=True)
class Gates:
    """The bar, written down first.

    `newey_west_t` is the conventional 2.0 rather than Harvey, Liu and Zhu's
    3.0. The trial count is handled separately and explicitly by PBO and by
    minimum backtest length, so applying a multiple-testing haircut here as
    well would charge for it twice.
    """
    newey_west_t: float = 2.0
    t_erosion_fraction: float = 0.30
    pbo_ceiling: float = 0.50
    worst_path_sharpe: float = 0.0
    min_years_multiple: float = 1.0


GATES = Gates()


@dataclass(frozen=True)
class Claim:
    """What the paper said, and where that came from."""
    paper_id: str
    source: str
    claimed_t: float | None = None
    claimed_annual_return: float | None = None
    claimed_sharpe: float | None = None
    sample_start_year: int | None = None
    sample_end_year: int | None = None
    notes: str = ""


@dataclass
class ClaimVerdict:
    paper_id: str
    status: str                       # HOLDS | WEAKER | FAILS | INSUFFICIENT
    reasons: list[str] = field(default_factory=list)
    table: list[dict[str, Any]] = field(default_factory=list)
    detail: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "paper_id": self.paper_id,
            "status": self.status,
            "reasons": self.reasons,
            "table": self.table,
            "detail": self.detail,
        }


def _annualized_sharpe(returns: Sequence[float]) -> float:
    n = len(returns)
    if n < 2:
        return 0.0
    mean = sum(returns) / n
    var = sum((r - mean) ** 2 for r in returns) / (n - 1)
    if var <= 0:
        return 0.0
    return (mean / math.sqrt(var)) * math.sqrt(TRADING_DAYS)


def _annual_return(returns: Sequence[float]) -> float:
    if not returns:
        return 0.0
    total = 1.0
    for r in returns:
        total *= (1.0 + r)
    years = len(returns) / TRADING_DAYS
    if years <= 0 or total <= 0:
        return 0.0
    return total ** (1.0 / years) - 1.0


def _row(metric: str, claimed: Any, replicated: Any, survives: Any) -> dict[str, Any]:
    return {"metric": metric, "claimed": claimed,
            "replicated": replicated, "survives": survives}


def _cpcv_paths(returns: Sequence[float], *, n_groups: int = 6,
                n_test_groups: int = 2) -> dict[str, Any]:
    """Sharpe on every combination of held-out blocks.

    The signal is not fitted, so nothing leaks through the boundary in the
    usual sense. What this catches is a result that lives in one stretch of the
    sample: hold that stretch out and the number collapses.
    """
    n = len(returns)
    if n < 120:
        return {"paths": None, "note": "fewer than 120 observations to split"}
    try:
        splits = validation.combinatorial_purged(
            n, n_groups=n_groups, n_test_groups=n_test_groups,
            horizon=1, embargo_pct=0.01,
        )
    except ValueError as exc:
        return {"paths": None, "note": str(exc)}

    sharpes = sorted(_annualized_sharpe([returns[i] for i in test]) for _, test in splits)
    return {
        "paths": len(sharpes),
        "worst": round(sharpes[0], 3),
        "median": round(sharpes[len(sharpes) // 2], 3),
        "best": round(sharpes[-1], 3),
        "share_positive": round(sum(1 for s in sharpes if s > 0) / len(sharpes), 3),
    }


def verify(
    claim: Claim,
    daily_returns: Sequence[float],
    *,
    trials: int = 1,
    competing_series: dict[str, dict[str, float]] | None = None,
) -> ClaimVerdict:
    """Score one replication against the paper's claim and the standard checks.

    `daily_returns` is the replication's realized net return series.
    `trials` is how many specifications were tried to arrive at it, which is
    what the minimum backtest length is a function of. `competing_series` are
    those specifications' return series, if they were kept, so PBO can ask
    whether picking this one would have held up.
    """
    returns = [float(r) for r in daily_returns if r == r]  # drop NaN
    if len(returns) < 60:
        return ClaimVerdict(
            paper_id=claim.paper_id,
            status="INSUFFICIENT",
            reasons=[f"only {len(returns)} return observations, too few to judge"],
        )

    rep_sharpe = _annualized_sharpe(returns)
    rep_return = _annual_return(returns)
    nw = validation.newey_west_t(returns)
    minbtl = validation.min_backtest_length(max(trials, 1), rep_sharpe)
    paths = _cpcv_paths(returns)

    pbo: dict[str, Any] = {"pbo": None, "note": "no competing specifications supplied"}
    if competing_series and len(competing_series) >= 2:
        _, matrix = validation.align(list(competing_series.values()))
        if matrix:
            pbo = validation.probability_of_overfitting(matrix)

    years = len(returns) / TRADING_DAYS
    reasons: list[str] = []
    failed = False
    weaker = False

    t_obs = nw.get("newey_west_t")
    if t_obs is None:
        weaker = True
        reasons.append(f"t-statistic could not be computed: {nw.get('note')}")
    elif t_obs < GATES.newey_west_t:
        failed = True
        reasons.append(
            f"Newey-West t of {t_obs} is below {GATES.newey_west_t}. Once daily "
            "autocorrelation is accounted for, the mean return is not "
            "distinguishable from zero."
        )

    if claim.claimed_t and t_obs is not None and claim.claimed_t > 0:
        erosion = (claim.claimed_t - t_obs) / claim.claimed_t
        if erosion > GATES.t_erosion_fraction:
            weaker = True
            reasons.append(
                f"the published t of {claim.claimed_t} falls to {t_obs} here, "
                f"a {erosion:.0%} loss."
            )

    if paths.get("paths") and paths["worst"] < GATES.worst_path_sharpe:
        weaker = True
        reasons.append(
            f"the worst held-out path has a Sharpe of {paths['worst']}, so the "
            "result does not hold on every stretch of the sample."
        )

    if pbo.get("pbo") is not None and pbo["pbo"] >= GATES.pbo_ceiling:
        failed = True
        reasons.append(
            f"PBO of {pbo['pbo']} across {pbo.get('configurations')} "
            "specifications: choosing this one was fitting noise."
        )

    needed = minbtl.get("min_backtest_years")
    if minbtl.get("beyond_any_available_history"):
        failed = True
        reasons.append(
            f"at this Sharpe and {trials} trials, no sample long enough to "
            "distinguish the result from noise exists."
        )
    elif needed and years < needed * GATES.min_years_multiple:
        weaker = True
        reasons.append(
            f"{years:.1f} years of replication history against the {needed} "
            f"years {trials} trials would require."
        )

    status = "FAILS" if failed else "WEAKER" if weaker else "HOLDS"
    if status == "HOLDS":
        reasons.append(
            "clears every gate declared before the run: Newey-West t, worst "
            "held-out path, overfitting probability and sample length."
        )

    table = [
        _row("annual return",
             f"{claim.claimed_annual_return:.2%}" if claim.claimed_annual_return is not None else None,
             f"{rep_return:.2%}", None),
        _row("Sharpe",
             round(claim.claimed_sharpe, 2) if claim.claimed_sharpe is not None else None,
             round(rep_sharpe, 2), None),
        _row("t-statistic", claim.claimed_t, nw.get("unadjusted_t"), nw.get("newey_west_t")),
        _row("worst held-out path", None, None, paths.get("worst")),
        _row("overfitting probability", None, None, pbo.get("pbo")),
        _row("years of history",
             (claim.sample_end_year - claim.sample_start_year)
             if claim.sample_start_year and claim.sample_end_year else None,
             round(years, 1), needed),
    ]

    return ClaimVerdict(
        paper_id=claim.paper_id,
        status=status,
        reasons=reasons,
        table=table,
        detail={
            "source_of_claim": claim.source,
            "newey_west": nw,
            "min_backtest_length": minbtl,
            "combinatorial_purged_cv": paths,
            "probability_of_backtest_overfitting": pbo,
            "gates": {
                "newey_west_t": GATES.newey_west_t,
                "t_erosion_fraction": GATES.t_erosion_fraction,
                "pbo_ceiling": GATES.pbo_ceiling,
                "worst_path_sharpe": GATES.worst_path_sharpe,
                "min_years_multiple": GATES.min_years_multiple,
                "declared": "frozen in claims.GATES before any run",
            },
        },
    )


def claim_from_openap(row: dict[str, Any]) -> Claim:
    """A Claim from one Open Source Asset Pricing SignalDoc row.

    OSAP is the reason this is possible at all: it publishes, per predictor,
    what the original paper reported and over which years, so there is
    something to compare against without opening a paywalled PDF.
    """
    def num(key: str) -> float | None:
        try:
            return float(str(row.get(key, "")).strip())
        except (TypeError, ValueError):
            return None

    acronym = (row.get("Acronym") or "").strip()
    start, end = num("SampleStartYear"), num("SampleEndYear")
    mean_ret = num("Mean Return")
    return Claim(
        paper_id=f"openap_{acronym.lower()}",
        source=(
            f"Open Source Asset Pricing SignalDoc, from "
            f"{row.get('Authors', '?')} ({row.get('Year', '?')})"
        ),
        claimed_t=num("T-Stat"),
        # SignalDoc quotes a monthly mean return in percent.
        claimed_annual_return=(mean_ret / 100.0 * 12.0) if mean_ret is not None else None,
        claimed_sharpe=None,
        sample_start_year=int(start) if start else None,
        sample_end_year=int(end) if end else None,
        notes=(row.get("Predictability in OP") or "").strip(),
    )


def render_table(verdict: ClaimVerdict) -> str:
    """The gap table as markdown, for a card or a pull request."""
    head = "| | claimed | replicated | survives |\n|---|---|---|---|\n"
    body = "".join(
        f"| {r['metric']} | {_cell(r['claimed'])} | {_cell(r['replicated'])} "
        f"| {_cell(r['survives'])} |\n"
        for r in verdict.table
    )
    return head + body


def _cell(value: Any) -> str:
    return "n/a" if value is None else str(value)
