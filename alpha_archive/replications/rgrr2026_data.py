"""Prices for the RGRR replication, and the baseline check that gates the rest.

Nothing about the rule is here. This assembles the seven series the paper names
and then asks the cheapest possible question: does buy-and-hold QQQ over the
paper's own sample come out at the CAGR the paper printed for it?

A static hold has no parameters, no signal and no rebalancing. If it misses,
the disagreement is in the prices — the sample window, the adjustment
convention, the annualisation — and every later number would inherit that error
while looking like a modelling result. So this runs first and gates everything.

RESULT, 2026-08-06: six of nine targets clear, three miss narrowly.

    QQQ   cagr 17.73 vs 17.17   miss by 0.056 beyond a 0.50 tolerance
    DIA   mdd -43.26 vs -44.54  miss by 0.276 beyond a 1.00 tolerance
    50/50 mdd -44.49 vs -45.53  miss by 0.041 beyond a 1.00 tolerance

The convention is not the problem, and that was established by elimination
rather than assumed. Price-only returns put DIA's CAGR at 9.07 against a
published 11.65, and starting from the 2006 data start puts every drawdown near
-53 against a published -47.83. Both are far worse than what is here. Shifting
the start date across a fortnight moves QQQ's CAGR by 0.16 and its drawdown not
at all, so the window is not it either.

What is left is that the price series itself differs slightly from the authors'.
Every miss runs the same way — our drawdowns are shallower and QQQ compounds
faster — which is what a later pull of Yahoo's adjusted history looks like after
distributions have been reclassified. That is the reason the CAGR tolerance was
set at half a point in the first place; it was set slightly too tight.

The tolerance stays where it is. It was written down before the run, and a bar
that moves when it is missed was never a bar. What this changes is the reading
of everything downstream: the rule cannot be replicated more precisely than the
buy-and-hold it is built from, so roughly half a point of CAGR and a point of
drawdown is the floor on replication error here, not evidence about the rule.

    uv run python -m alpha_archive.replications.rgrr2026_data
"""

from __future__ import annotations

import os

import numpy as np
import pandas as pd

from ..criteria import rgrr2026 as spec
from ..verification import Status

CACHE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "data", "cache", "rgrr")

TICKERS = ["QQQ", "DIA", "SPY", "HYG", "SHY", "^VIX", "^TNX"]
START = "2006-06-22"          # the paper's data start
TRADING_DAYS = 252


def load(refresh: bool = False) -> pd.DataFrame:
    """Daily adjusted closes for every series the paper names."""
    os.makedirs(CACHE, exist_ok=True)
    path = os.path.join(CACHE, "prices.parquet")
    if os.path.exists(path) and not refresh:
        return pd.read_parquet(path)

    import yfinance as yf

    # auto_adjust folds splits and dividends into the close, which is what a
    # total-return CAGR needs. ^VIX and ^TNX have no distributions, so the
    # setting is a no-op for them.
    raw = yf.download(TICKERS, start=START, end="2026-07-03",
                      auto_adjust=True, progress=False, group_by="column")
    close = raw["Close"] if isinstance(raw.columns, pd.MultiIndex) else raw
    close = close.dropna(how="all").sort_index()
    close.to_parquet(path)
    return close


def stats(equity: pd.Series) -> dict[str, float]:
    """CAGR, Sharpe and max drawdown, in the units Table 16 prints.

    Sharpe is excess of nothing: the paper reports a plain return-over-vol
    ratio for its static baselines, and subtracting a cash rate here would
    silently make every comparison a different statistic.
    """
    equity = equity.dropna()
    if len(equity) < 2:
        return {"cagr": float("nan"), "sharpe": float("nan"),
                "max_drawdown": float("nan")}

    years = (equity.index[-1] - equity.index[0]).days / 365.25
    cagr = (equity.iloc[-1] / equity.iloc[0]) ** (1 / years) - 1

    daily = equity.pct_change().dropna()
    sharpe = daily.mean() / daily.std() * np.sqrt(TRADING_DAYS) if daily.std() else np.nan

    drawdown = equity / equity.cummax() - 1
    return {
        "cagr": float(cagr * 100),
        "sharpe": float(sharpe),
        "max_drawdown": float(drawdown.min() * 100),
    }


def hold(close: pd.DataFrame, weights: dict[str, float],
         start: str, end: str) -> pd.Series:
    """Equity curve of a fixed-weight, daily-rebalanced hold."""
    window = close.loc[start:end, list(weights)]
    returns = window.pct_change().dropna(how="all")
    blended = sum(returns[t] * w for t, w in weights.items())
    return (1 + blended.fillna(0)).cumprod()


def check_baselines(close: pd.DataFrame) -> tuple[bool, list[str]]:
    """Table 5. The gate on everything that follows."""
    arms = {
        "QQQ": {"QQQ": 1.0},
        "DIA": {"DIA": 1.0},
        "50/50": {"QQQ": 0.5, "DIA": 0.5},
    }
    observed = {name: stats(hold(close, w, spec.WINDOWS["2008"], spec.END))
                for name, w in arms.items()}

    lines, passed = [], True
    for target in spec.baseline_targets():
        arm = target.name.split(" buy-and-hold ")[0]
        stat = target.name.split(" buy-and-hold ")[1].replace(" ", "_")
        status, message = target.judge(observed[arm].get(stat))
        passed &= status is Status.VERIFIED
        lines.append(f"  [{'PASS' if status is Status.VERIFIED else 'FAIL'}] {message}")
    return passed, lines


def main() -> None:
    close = load()
    print(f"{len(close):,} sessions, {close.index[0].date()} to {close.index[-1].date()}")
    print("series:", ", ".join(close.columns))
    missing = close.isna().sum()
    if missing.any():
        print("gaps:", {k: int(v) for k, v in missing.items() if v})
    print()

    passed, lines = check_baselines(close)
    print("Table 5 buy-and-hold, 2008-07-25 to 2026-07-02")
    print(chr(10).join(lines))
    print()
    print("data gate:", "PASSED" if passed else "FAILED — do not build the rule on this")


if __name__ == "__main__":
    main()
