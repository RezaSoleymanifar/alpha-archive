"""Replication #2, Darmanin (2026), "Retail Trader's Ruin".

arXiv:2607.20093, posted 22 July 2026. The first *recent* paper here, and the
first with no external fixture: nobody has replicated it, so the paper's own
reported confidence intervals are the thing we must hit.

Why this one. It tests five retail signal families against three predeclared
gates and reports four REFUTED, two INCONCLUSIVE, none SUPPORTED. Two of the
six run on a single price series and are therefore reproducible exactly with
free data:

    Calendar   Sell-in-May on SPY,        8,358 daily obs   -> REFUTED
    Trend      50/200 cross on NASDAQ-100, 10,331 daily obs -> INCONCLUSIVE

The other four need Russell 3000 and S&P 500 point-in-time membership with
Shumway delisting corrections, which is exactly the data we do not have. We
run the two we can and say nothing about the four we cannot.

The criterion is declared before the run in alpha_archive.verification: our
bootstrap CI must overlap theirs *and* our gate classification must match. A
matching verdict from a non-overlapping interval is a coincidence, not a
replication, so both are required.

    uv run python -m alpha_archive.replications.darmanin2026
"""

from __future__ import annotations

import asyncio
import json
import os
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable

import numpy as np
import pandas as pd

from vintage.sources import yahoo

PAPER = "Darmanin2026"
ARXIV = "https://arxiv.org/abs/2607.20093"

# Predeclared in the paper, Section 3. Not ours to move.
DELTA_SHARPE = 0.20
DELTA_CAGR = 0.01
COST_BPS_PER_LEG = 5.0          # 10bps round trip, their headline retail cost
TRADING_DAYS = 252

BOOTSTRAP_DRAWS = 2000
MEAN_BLOCK = 20                 # stationary bootstrap, ~1 month of daily data
SEED = 20260722                 # the paper's arXiv date, so reruns are stable


# What the paper reports, transcribed once from Tables 2 and 3.
CLAIMS: dict[str, dict[str, Any]] = {
    "calendar": {
        "label": "Sell-in-May",
        "symbol": "SPY",
        "paper_obs": 8358,
        "sharpe_ci": (-0.618, 0.000),
        "sharpe_gate": "REFUTED",
        "cagr_ci": (-0.131, -0.026),
        "cagr_gate": "REFUTED",
        "spec_note": (
            "Table 1 describes this family as 'Sell-in-May (best of battery, Bonferroni "
            "+ BY)'. The paper searches a battery of calendar rules and reports the best "
            "after multiplicity correction. We run the single canonical November-April "
            "rule, so a disagreement on the economic gate is a specification difference "
            "before it is a replication failure."
        ),
    },
    "trend": {
        "label": "Golden/death cross (50/200)",
        "symbol": "^NDX",
        "paper_obs": 10331,
        "sharpe_ci": (-0.234, 0.265),
        "sharpe_gate": "INCONCLUSIVE",
        "cagr_ci": (-0.081, 0.024),
        "cagr_gate": "INCONCLUSIVE",
        "spec_note": "",
    },
}


@dataclass
class FamilyResult:
    family: str
    label: str
    symbol: str
    obs: int
    paper_obs: int
    sample: str
    exposure: float

    sharpe_gap: float
    sharpe_ci: tuple[float, float]
    sharpe_gate: str
    paper_sharpe_ci: tuple[float, float]
    paper_sharpe_gate: str
    sharpe_ci_overlaps: bool

    cagr_gap: float
    cagr_ci: tuple[float, float]
    cagr_gate: str
    paper_cagr_ci: tuple[float, float]
    paper_cagr_gate: str
    cagr_ci_overlaps: bool

    verdict: str
    notes: list[str] = field(default_factory=list)
    perturbations: list[dict[str, Any]] = field(default_factory=list)
    placebo: dict[str, Any] = field(default_factory=dict)


# ------------------------------------------------------------------ the rules


def sell_in_may(prices: pd.Series) -> pd.Series:
    """Long November through April, flat May through October."""
    month = prices.index.month
    return pd.Series(((month >= 11) | (month <= 4)).astype(float), index=prices.index)


def cross(fast: int = 50, slow: int = 200) -> Callable[[pd.Series], pd.Series]:
    """Long while the fast moving average sits above the slow one."""
    def rule(prices: pd.Series) -> pd.Series:
        f = prices.rolling(fast).mean()
        s = prices.rolling(slow).mean()
        return (f > s).astype(float)
    return rule


# ------------------------------------------------------------------ the maths


def strategy_returns(prices: pd.Series, position: pd.Series) -> pd.Series:
    """Daily returns of a long/flat rule, charged on every position change.

    The position is lagged a day: a rule computed from today's close cannot be
    traded until tomorrow, and skipping that lag is the classic way a timing
    backtest invents its edge.
    """
    daily = prices.pct_change()
    held = position.shift(1).fillna(0.0)
    turnover = held.diff().abs().fillna(held.abs())
    return (held * daily - turnover * COST_BPS_PER_LEG / 10_000.0).dropna()


def exposure_matched(prices: pd.Series, exposure: float) -> pd.Series:
    """Buy-and-hold scaled to the same average time in market.

    Comparing a rule that is invested half the time against fully invested
    buy-and-hold measures market exposure, not skill. Matching exposure is
    what makes the gap attributable to the timing decision.
    """
    return (prices.pct_change() * exposure).dropna()


def sharpe(r) -> Any:
    """Annualised Sharpe. Works on one series or on a (draws, n) bootstrap matrix."""
    a = np.asarray(r, dtype=float)
    if a.shape[-1] < 3:
        return float("nan")
    sd = a.std(axis=-1, ddof=1)
    mean = a.mean(axis=-1)
    out = np.divide(mean, sd, out=np.full(np.shape(sd), np.nan), where=sd > 0)
    out = out * np.sqrt(TRADING_DAYS)
    return float(out) if np.ndim(out) == 0 else out


def cagr(r) -> Any:
    """Compound annual growth. Summed log1p rather than a product, which
    underflows on thirty years of daily returns."""
    a = np.asarray(r, dtype=float)
    n = a.shape[-1]
    if n < 3:
        return float("nan")
    years = n / TRADING_DAYS
    out = np.exp(np.log1p(a).sum(axis=-1) / years) - 1.0
    return float(out) if np.ndim(out) == 0 else out


def stationary_bootstrap_ci(
    a: pd.Series, b: pd.Series, statistic: Callable[[pd.Series], float],
    draws: int = BOOTSTRAP_DRAWS, mean_block: int = MEAN_BLOCK,
) -> tuple[float, float]:
    """Politis-Romano stationary bootstrap CI for statistic(a) - statistic(b).

    Blocks of geometric length preserve the serial dependence in daily returns;
    an iid bootstrap would understate the interval and make everything look
    decisive. Both series are resampled on the *same* indices so the pairing
    between strategy and benchmark survives.
    """
    joined = pd.concat([a.rename("a"), b.rename("b")], axis=1).dropna()
    n = len(joined)
    if n < 100:
        return (float("nan"), float("nan"))

    av, bv = joined["a"].to_numpy(), joined["b"].to_numpy()
    idx = _bootstrap_indices(n, draws, mean_block)
    gaps = statistic(av[idx]) - statistic(bv[idx])
    return (float(np.percentile(gaps, 2.5)), float(np.percentile(gaps, 97.5)))


def _bootstrap_indices(n: int, draws: int, mean_block: int) -> np.ndarray:
    """Stationary-bootstrap index matrix, (draws, n), built without a Python loop.

    Walking the chain one step at a time costs draws*n iterations, 17 million
    per interval here, and this module needs dozens of intervals. The same
    process vectorises: mark where blocks restart, carry the most recent restart
    position forward with a running maximum, and offset from it.
    """
    rng = np.random.default_rng(SEED)
    t = np.arange(n)

    restart = rng.random((draws, n)) < (1.0 / mean_block)
    restart[:, 0] = True                                   # every path starts a block
    starts = rng.integers(0, n, size=(draws, n))

    # Column of the most recent restart, per row.
    last = np.maximum.accumulate(np.where(restart, t, 0), axis=1)
    origin = np.take_along_axis(starts, last, axis=1)      # where that block began
    return (origin + (t - last)) % n


def gate(ci: tuple[float, float], delta: float) -> str:
    """The paper's classification. REFUTED needs material exclusion, never
    bare non-significance. That distinction is the point of their design."""
    lo, hi = ci
    if np.isnan(lo) or np.isnan(hi):
        return "NO READ"
    if hi < 0:
        return "REFUTED"           # significantly negative
    if hi <= delta:
        return "REFUTED"           # material exclusion
    if lo > delta:
        return "SUPPORTED"
    return "INCONCLUSIVE"


def overlaps(a: tuple[float, float], b: tuple[float, float]) -> bool:
    return not (a[1] < b[0] or b[1] < a[0])


# -------------------------------------------------------------------- the run


async def load(symbol: str) -> pd.Series:
    rows = await yahoo.prices(symbol, field="adjclose")
    s = pd.Series({pd.Timestamp(r["observed_at"]): r["value"] for r in rows if r["value"]})
    return s.sort_index()


def evaluate_rule(prices: pd.Series, rule: Callable[[pd.Series], pd.Series]) -> dict[str, Any]:
    position = rule(prices)
    strat = strategy_returns(prices, position)
    exposure = float(position.shift(1).fillna(0.0).reindex(strat.index).mean())
    bench = exposure_matched(prices, exposure).reindex(strat.index).dropna()
    strat = strat.reindex(bench.index)

    s_ci = stationary_bootstrap_ci(strat, bench, sharpe)
    c_ci = stationary_bootstrap_ci(strat, bench, cagr)
    return {
        "exposure": round(exposure, 4),
        "sharpe_gap": round(sharpe(strat) - sharpe(bench), 4),
        "sharpe_ci": (round(s_ci[0], 4), round(s_ci[1], 4)),
        "cagr_gap": round(cagr(strat) - cagr(bench), 4),
        "cagr_ci": (round(c_ci[0], 4), round(c_ci[1], 4)),
        "obs": int(len(strat)),
    }


async def run_family(name: str) -> FamilyResult:
    claim = CLAIMS[name]
    prices = await load(claim["symbol"])
    rule = sell_in_may if name == "calendar" else cross(50, 200)

    print(f"\n  [{name}] {claim['label']} on {claim['symbol']}")
    print(f"      {len(prices):,} obs, paper reports {claim['paper_obs']:,} "
          f"({len(prices) - claim['paper_obs']:+,})")

    r = evaluate_rule(prices, rule)
    s_gate, c_gate = gate(r["sharpe_ci"], DELTA_SHARPE), gate(r["cagr_ci"], DELTA_CAGR)
    s_ov = overlaps(r["sharpe_ci"], claim["sharpe_ci"])
    c_ov = overlaps(r["cagr_ci"], claim["cagr_ci"])

    print(f"      sharpe gap {r['sharpe_gap']:+.3f}  CI {r['sharpe_ci']}  -> {s_gate}"
          f"   (paper {claim['sharpe_ci']} {claim['sharpe_gate']}, "
          f"overlap {'yes' if s_ov else 'NO'})")
    print(f"      cagr   gap {r['cagr_gap']:+.3f}  CI {r['cagr_ci']}  -> {c_gate}"
          f"   (paper {claim['cagr_ci']} {claim['cagr_gate']}, "
          f"overlap {'yes' if c_ov else 'NO'})")

    matched = s_gate == claim["sharpe_gate"] and c_gate == claim["cagr_gate"]
    if matched and s_ov and c_ov:
        verdict = "REPLICATED, same gate classification, and both intervals overlap the paper's"
    elif matched:
        verdict = ("gates match but an interval does not overlap, agreement here is not "
                   "evidence of the same computation")
    else:
        verdict = "DIVERGES, our gate classification differs from the paper's"

    notes = [n for n in [claim.get("spec_note")] if n]
    if not s_ov or not c_ov:
        notes.append(
            f"Our sample carries {abs(len(prices) - claim['paper_obs']):,} more or fewer "
            "observations than the paper's, and the bootstrap block length is our choice "
            "rather than theirs, so intervals are not expected to match to the digit."
        )

    # Perturbation: did the authors' parameter choices carry the result?
    perturbations = []
    if name == "trend":
        for f, s in [(20, 100), (50, 200), (100, 300), (10, 50)]:
            pr = evaluate_rule(prices, cross(f, s))
            perturbations.append({"params": f"{f}/{s}", "sharpe_gap": pr["sharpe_gap"],
                                  "gate": gate(pr["sharpe_ci"], DELTA_SHARPE)})
    else:
        for lo, hi, label in [(11, 4, "Nov-Apr"), (10, 4, "Oct-Apr"),
                              (11, 5, "Nov-May"), (12, 3, "Dec-Mar")]:
            def r2(p, lo=lo, hi=hi):
                m = p.index.month
                return pd.Series(((m >= lo) | (m <= hi)).astype(float), index=p.index)
            pr = evaluate_rule(prices, r2)
            perturbations.append({"params": label, "sharpe_gap": pr["sharpe_gap"],
                                  "gate": gate(pr["sharpe_ci"], DELTA_SHARPE)})

    # Placebo: the same machinery on coin-flip signals. Anything the pipeline
    # reports here is manufactured by the pipeline, not found in the market.
    rng = np.random.default_rng(SEED)
    gaps = []
    for _ in range(12):
        fake = pd.Series(rng.integers(0, 2, len(prices)).astype(float), index=prices.index)
        gaps.append(evaluate_rule(prices, lambda p, f=fake: f)["sharpe_gap"])
    placebo = {
        "runs": len(gaps),
        "mean_sharpe_gap": round(float(np.mean(gaps)), 4),
        "max_abs_sharpe_gap": round(float(np.max(np.abs(gaps))), 4),
        "reading": (
            "Coin-flip signals trade almost every day, so this figure is dominated by cost "
            "drag rather than by spurious edge. It says what daily churn costs against an "
            "exposure-matched hold, not what the pipeline invents from noise. A turnover-"
            "matched null would be the sharper test for the low-turnover rules above."
        ),
    }

    return FamilyResult(
        family=name, label=claim["label"], symbol=claim["symbol"],
        obs=r["obs"], paper_obs=claim["paper_obs"],
        sample=f"{prices.index[0].date()}..{prices.index[-1].date()}",
        exposure=r["exposure"],
        sharpe_gap=r["sharpe_gap"], sharpe_ci=r["sharpe_ci"], sharpe_gate=s_gate,
        paper_sharpe_ci=claim["sharpe_ci"], paper_sharpe_gate=claim["sharpe_gate"],
        sharpe_ci_overlaps=s_ov,
        cagr_gap=r["cagr_gap"], cagr_ci=r["cagr_ci"], cagr_gate=c_gate,
        paper_cagr_ci=claim["cagr_ci"], paper_cagr_gate=claim["cagr_gate"],
        cagr_ci_overlaps=c_ov,
        verdict=verdict, notes=notes, perturbations=perturbations, placebo=placebo,
    )


async def main() -> None:
    print(f"Darmanin (2026), Retail Trader's Ruin, {ARXIV}")
    print("  Replicating the two families that run on a single price series.")
    print("  The other four need Russell 3000 / S&P 500 point-in-time membership.")

    results = [await run_family(n) for n in ("calendar", "trend")]

    print("\n" + "=" * 72)
    for r in results:
        print(f"  {r.label:<30} {r.verdict}")
        print(f"    perturbations: " + ", ".join(
            f"{p['params']}={p['sharpe_gap']:+.3f}({p['gate'][:4]})" for p in r.perturbations))
        print(f"    placebo (coin flips): mean gap {r.placebo['mean_sharpe_gap']:+.3f}, "
              f"max |gap| {r.placebo['max_abs_sharpe_gap']:.3f}")
    print("=" * 72)

    out = os.path.join("data", "replications", "darmanin2026.json")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8") as fh:
        json.dump({
            "paper": PAPER, "arxiv": ARXIV, "authors": "Adam Darmanin", "year": 2026,
            "delta_sharpe": DELTA_SHARPE, "delta_cagr": DELTA_CAGR,
            "cost_bps_per_leg": COST_BPS_PER_LEG,
            "bootstrap": {"draws": BOOTSTRAP_DRAWS, "mean_block": MEAN_BLOCK, "seed": SEED},
            "families": [asdict(r) for r in results],
            "not_attempted": [
                "Oscillator (RSI), NASDAQ-100, reproducible in principle, not yet run",
                "Volume (OBV), needs Russell 3000 point-in-time membership",
                "Candlestick, needs Russell 3000 point-in-time membership",
                "Momentum calibration, needs S&P 500 point-in-time membership",
            ],
            "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        }, fh, indent=2)
    print(f"\nwrote {out}")


if __name__ == "__main__":
    asyncio.run(main())
