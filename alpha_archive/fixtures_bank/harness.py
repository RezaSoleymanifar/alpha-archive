"""Run a published signal on free data, and be honest about what that proves.

The 127 Chen-Zimmermann specs each carry a definition and the t-statistic the
original paper reported. It is tempting to call matching that a replication. It
is not, and this module exists so nobody can accidentally claim it.

Three things stand between us and the published number:

The sample windows run 1963 to 2003. Free price data does not reach there for
anything but the survivors.

The original universe is every CRSP name, delisted ones included. Ours is names
that still trade today, which is the survivorship bias these papers were written
to measure around.

OSAP's own long-short return series, the only fixture that would settle it, is
published through a Google Drive link that returns a quota page.

So what runs here is a re-test, not a replication: the same signal, on a modern
window, on the universe we can actually get. A result that agrees with the paper
is weak evidence the effect is real and durable. A result that disagrees is not
a refutation, because the sample is different in three ways at once. Both go in
the ledger as SANITY_CHECK and neither can promote anything to VERIFIED.

    uv run python -m alpha_archive.fixtures_bank.harness --list
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import Callable

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CACHE = os.path.join(ROOT, "data", "cache", "bank")
RESULTS = os.path.join(ROOT, "data", "fixtures_bank")

START = "2005-01-01"
END = "2026-07-01"
TRADING_DAYS = 252
COST_BPS = 10.0          # one way, charged on turnover every rebalance
DECILE = 0.1             # long the top tenth, short the bottom tenth


@dataclass
class SpecResult:
    """One signal, run and scored. Never a verification."""
    name: str
    published_t: float | None
    published_sample: str
    observed_t: float | None = None
    observed_monthly_pct: float | None = None
    observed_sharpe: float | None = None
    months: int = 0
    names: int = 0
    same_sign: bool | None = None
    still_significant: bool | None = None
    status: str = "SANITY_CHECK"
    note: str = ""
    error: str = ""

    def to_dict(self) -> dict:
        out = self.__dict__.copy()
        out["status"] = "SANITY_CHECK"      # not settable from a run
        return out


def panel(tickers: list[str], refresh: bool = False) -> pd.DataFrame:
    """Daily adjusted closes for the test universe, cached once and shared."""
    os.makedirs(CACHE, exist_ok=True)
    path = os.path.join(CACHE, "panel.parquet")
    if os.path.exists(path) and not refresh:
        frame = pd.read_parquet(path)
        missing = [t for t in tickers if t not in frame.columns]
        if not missing:
            return frame[tickers]

    import yfinance as yf
    raw = yf.download(tickers, start=START, end=END, auto_adjust=True,
                      progress=False, group_by="column")
    close = raw["Close"] if isinstance(raw.columns, pd.MultiIndex) else raw
    close = close.dropna(how="all").sort_index()
    close.to_parquet(path)
    return close


def monthly_returns(close: pd.DataFrame) -> pd.DataFrame:
    return close.resample("ME").last().pct_change(fill_method=None)


def long_short(signal: pd.DataFrame, forward: pd.DataFrame,
               decile: float = DECILE) -> pd.Series:
    """Equal-weighted top-minus-bottom decile, costed on turnover.

    The signal at month t decides the position held through t+1, so `forward`
    must already be shifted. Getting that backwards is the single most common
    way a replication reports a spectacular number.
    """
    out: dict[pd.Timestamp, float] = {}
    held: set[str] = set()
    for date in signal.index:
        row = signal.loc[date].dropna()
        nxt = forward.loc[date].dropna() if date in forward.index else None
        if nxt is None or len(row) < 20:
            continue
        row = row[row.index.intersection(nxt.index)]
        if len(row) < 20:
            continue

        k = max(2, int(len(row) * decile))
        ranked = row.sort_values()
        short, long_ = ranked.index[:k], ranked.index[-k:]
        gross = nxt[long_].mean() - nxt[short].mean()

        now = set(long_) | set(short)
        turnover = len(now ^ held) / max(len(now | held), 1)
        held = now
        out[date] = gross - turnover * COST_BPS / 10_000.0
    return pd.Series(out).sort_index()


def score(returns: pd.Series, published_t: float | None,
          published_sample: str, name: str) -> SpecResult:
    result = SpecResult(name=name, published_t=published_t,
                        published_sample=published_sample)
    clean = returns.dropna()
    result.months = len(clean)
    if result.months < 36:
        result.error = f"only {result.months} months of returns, too few to score"
        return result

    mean, sd = clean.mean(), clean.std()
    result.observed_monthly_pct = round(float(mean * 100), 4)
    result.observed_t = round(float(mean / sd * np.sqrt(len(clean))), 3) if sd else None
    result.observed_sharpe = round(float(mean / sd * np.sqrt(12)), 3) if sd else None

    if published_t is not None and result.observed_t is not None:
        result.same_sign = (published_t > 0) == (result.observed_t > 0)
        result.still_significant = abs(result.observed_t) >= 2.0

    result.note = (
        f"Re-test on free data {START[:4]}-{END[:4]}, currently-listed names only, "
        f"{COST_BPS:.0f}bp one-way costs. The paper reported t={published_t} over "
        f"{published_sample} on the full CRSP universe including delisted names. "
        "These are different samples, so this neither confirms nor refutes the "
        "published figure. It says whether the effect is visible today on data "
        "anyone can get."
    )
    return result


def save(results: list[SpecResult], batch: str) -> str:
    os.makedirs(RESULTS, exist_ok=True)
    path = os.path.join(RESULTS, f"{batch}.json")
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        json.dump([r.to_dict() for r in results], fh, indent=1)
    return path
