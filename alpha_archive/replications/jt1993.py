"""Replication #1 — Jegadeesh & Titman (1993), cross-sectional momentum.

The first paper run end to end on Vintage rather than on a local parquet, so
every number here is reproducible by a stranger with `pip install vintage-mcp`.

Three things happen, in this order, and the order matters:

1. **Validate the implementation before judging the paper.** Our long-short
   series is correlated against Ken French's published UMD factor. If that
   correlation is low, the finding is that *we* are wrong, not that momentum
   is. A replication that skips this step is measuring its own bugs.

2. **Score against what the paper actually claimed**, pulled from Open Source
   Asset Pricing rather than from memory: 1.31% per month, t = 3.74, over
   1964-1989.

3. **State what our sample cannot cover.** We are not running the paper. We
   run a survivor-biased large-cap universe over a modern window, because
   that is what free data permits. A gap against the claim is evidence about
   *this* sample, not a refutation of the original.

    uv run python -m alpha_archive.replications.jt1993
"""

from __future__ import annotations

import asyncio
import json
import os
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any

import numpy as np
import pandas as pd

from vintage.sources import french, openap, yahoo

from ..verification import evaluate, sanity

PAPER = "Mom12m"                    # the OpenAP acronym for JT 12-1 momentum
LOOKBACK, SKIP = 252, 21            # 12 months, skipping the most recent one
DECILE = 0.10                       # long the top 10%, short the bottom 10%
COST_BPS = 10.0                     # charged on turnover, every rebalance
HOLD_MONTHS = 3                     # the paper's K: J=12, K=3, overlapping cohorts
MIN_PRICE = 5.0                     # screen on the *unadjusted* close
START = "2005-01-01"

# A survivor-biased large-cap universe. This is the honest limit of free data:
# these are companies that are *still listed*, so the losers that delisted are
# structurally absent. Momentum's short leg is exactly where those names would
# have been, which biases this test against finding the paper's result.
UNIVERSE = [
    "AAPL", "MSFT", "AMZN", "GOOGL", "META", "NVDA", "JPM", "JNJ", "V", "PG",
    "UNH", "HD", "MA", "BAC", "XOM", "DIS", "ADBE", "CRM", "NFLX", "CSCO",
    "PFE", "KO", "PEP", "TMO", "ABT", "CVX", "MRK", "WMT", "INTC", "VZ",
    "CMCSA", "T", "NKE", "ORCL", "QCOM", "TXN", "AMD", "HON", "UNP", "LOW",
    "IBM", "GS", "MS", "CAT", "DE", "MMM", "AXP", "BKNG", "SBUX", "GILD",
    "ISRG", "AMGN", "LMT", "BLK", "SPGI", "PLD", "SYK", "MDT", "ADP", "C",
    "MO", "DUK", "SO", "BDX", "CL", "EOG", "SLB", "COP", "PSX", "MPC",
    "F", "GM", "DAL", "UAL", "MAR", "HLT", "EBAY", "PYPL", "INTU", "NOW",
]


@dataclass
class Result:
    paper: str
    authors: str
    year: int
    claimed_monthly_pct: float | None
    claimed_t_stat: float | None
    claimed_sample: str

    measured_monthly_pct: float
    measured_t_stat: float
    measured_sharpe_annual: float
    measured_sample: str
    months: int

    umd_correlation: float | None
    umd_months_compared: int
    verification: dict[str, Any]
    sanity_check: dict[str, Any] | None

    gap_monthly_pct: float | None
    verdict: str
    umd_by_era: dict[str, dict[str, float]] = field(default_factory=dict)
    caveats: list[str] = field(default_factory=list)
    universe_size: int = 0
    generated_at: str = ""


# ------------------------------------------------------------------ the data


async def price_panel(
    tickers: list[str], with_nominal: bool = True
) -> tuple[pd.DataFrame, pd.DataFrame | None]:
    """(adjusted closes, unadjusted closes) as dates x tickers.

    Returns need the adjusted series; the price screen needs the unadjusted one,
    because a split-adjusted history makes large caps look like penny stocks in
    their early years.
    """
    adj, nom, missing = {}, {}, []

    def series(rows):
        return pd.Series(
            {pd.Timestamp(r["observed_at"]): r["value"] for r in rows if r["value"]}
        ).sort_index()

    for i, t in enumerate(tickers, 1):
        try:
            rows = await yahoo.prices(t, field="adjclose")
        except Exception as exc:                      # a dead ticker is data
            missing.append(f"{t} ({type(exc).__name__})")
            continue
        if not rows:
            missing.append(f"{t} (empty)")
            continue
        adj[t] = series(rows)

        if with_nominal:
            try:
                nom[t] = series(await yahoo.prices(t, field="close"))
            except Exception:
                nom[t] = adj[t]                       # screen degrades, never crashes
        if i % 40 == 0:
            print(f"    ... {i}/{len(tickers)} tickers")

    if missing:
        print(f"    unavailable: {len(missing)} — {', '.join(missing[:8])}"
              + (" ..." if len(missing) > 8 else ""))

    start = pd.Timestamp(START)
    panel = pd.DataFrame(adj).sort_index()
    panel = panel[panel.index >= start]
    if not with_nominal:
        return panel, None
    npanel = pd.DataFrame(nom).sort_index()
    return panel, npanel[npanel.index >= start]


# --------------------------------------------------------------- the signal


def momentum_12_1(prices: pd.DataFrame) -> pd.DataFrame:
    """The paper's rule: return from t-12 months to t-1 month."""
    return prices.shift(SKIP) / prices.shift(LOOKBACK) - 1.0


def long_short_monthly(
    prices: pd.DataFrame,
    signal: pd.DataFrame,
    nominal: pd.DataFrame | None = None,
    hold_months: int = HOLD_MONTHS,
    min_price: float = MIN_PRICE,
) -> pd.Series:
    """Decile long-short with overlapping cohorts, costs charged on turnover.

    Two things here are the paper's construction rather than a simplification:

    **Overlapping holds.** Jegadeesh-Titman's headline strategy is J=12, K=3 —
    form on twelve-month momentum, then hold three months. The standard way to
    run that as a single monthly series is overlapping cohorts: a new decile
    portfolio is formed each month and held for `hold_months`, so the live book
    is the average of the last three cohorts and only a third of it turns over.
    That lower turnover matters twice, once in the returns and once in costs.

    **A price screen on nominal prices.** Sub-$5 stocks are dominated by
    bid-ask bounce, which momentum sorts pick up as signal. The screen has to
    use the *unadjusted* close: on a split-adjusted series Apple trades near $2
    in 2006, so screening adjusted prices would throw out the largest company
    in the sample for being a penny stock.
    """
    month_ends = prices.resample("ME").last().index
    forward = prices.resample("ME").last().pct_change().shift(-1)
    nominal_me = nominal.resample("ME").last() if nominal is not None else None

    cohorts: list[pd.Series] = []          # newest first, at most hold_months
    returns, prev_book = {}, pd.Series(dtype=float)

    for date in month_ends:
        row = signal.loc[signal.index <= date]
        if row.empty:
            continue
        s = row.iloc[-1].dropna()

        if nominal_me is not None and min_price > 0 and date in nominal_me.index:
            eligible = nominal_me.loc[date].reindex(s.index)
            s = s[eligible >= min_price]

        if len(s) >= 20:                    # too thin to rank into deciles
            k = max(1, int(round(len(s) * DECILE)))
            ranked = s.sort_values()
            w = pd.Series(0.0, index=s.index)
            w[ranked.index[-k:]] = 0.5 / k              # long the winners
            w[ranked.index[:k]] = -0.5 / k              # short the losers
            cohorts.insert(0, w)
            del cohorts[hold_months:]

        if not cohorts or date not in forward.index:
            continue

        book = pd.concat(cohorts, axis=1).fillna(0.0).mean(axis=1)
        nxt = forward.loc[date].reindex(book.index).fillna(0.0)

        gross = float((book * nxt).sum())
        turnover = float((book - prev_book.reindex(book.index).fillna(0.0)).abs().sum())
        # Stamp the return with the month it was *earned*, not the month the
        # weights were formed. Getting this backwards shifts the whole series
        # by a month and drops the correlation against UMD from 0.74 to 0.01 —
        # which is exactly what a sanity check exists to catch.
        returns[date + pd.offsets.MonthEnd(1)] = gross - turnover * COST_BPS / 10_000.0
        prev_book = book

    return pd.Series(returns).sort_index().dropna()


# ------------------------------------------------------------- the yardstick


async def umd_monthly() -> pd.Series:
    """Ken French's published momentum factor, monthly, as a decimal."""
    rows = await french.load("momentum")
    series = {
        pd.Timestamp(r["observed_at"]): float(r["value"])
        for r in rows
        if r.get("field") == "Mom" and r.get("value") is not None and r.get("observed_at")
    }
    # Vintage already returns these as decimals, not percent. Sanity-checked
    # against April 2009 = -34.4%, the momentum crash.
    return pd.Series(series).sort_index()


def umd_eras(umd: pd.Series) -> dict[str, dict[str, float]]:
    """UMD's own record, split by era.

    This is what separates "our universe is too narrow" from "the effect
    decayed". If the published factor is also flat over our window, a weak
    result here is agreement with the literature rather than a bug.
    """
    windows = {
        "1964-1989 (paper sample)": umd["1964":"1989"],
        "1990-2005 (post-publication)": umd["1990":"2005"],
        "2006-2026 (our window)": umd["2006":],
        "1927-2026 (full)": umd,
    }
    return {
        label: {"mean_monthly_pct": round(float(s.mean() * 100), 4),
                "t_stat": round(t_stat(s), 3),
                "months": int(len(s))}
        for label, s in windows.items() if len(s) > 12
    }


def t_stat(x: pd.Series) -> float:
    if len(x) < 3 or x.std(ddof=1) == 0:
        return float("nan")
    return float(x.mean() / (x.std(ddof=1) / np.sqrt(len(x))))


# ------------------------------------------------------------------- the run


async def run() -> Result:
    print("Jegadeesh & Titman (1993) — replication on Vintage\n")

    print("  [1/4] what the paper claimed, from Open Source Asset Pricing")
    claim = await openap.get(PAPER)
    print(f"        {claim['authors']} {int(claim['year'])}: "
          f"{claim['value']}%/month, t = {claim['t_stat']}, "
          f"{claim['sample_start']}-{claim['sample_end']}")

    print(f"\n  [2/4] prices for {len(UNIVERSE)} tickers, via Vintage")
    prices, nominal = await price_panel(UNIVERSE)
    print(f"        panel: {prices.shape[0]} days x {prices.shape[1]} tickers, "
          f"{prices.index[0].date()} to {prices.index[-1].date()}")

    print(f"\n  [3/4] decile long-short, {HOLD_MONTHS}-month overlapping hold, "
          f"nominal price >= ${MIN_PRICE:.0f}")
    ours = long_short_monthly(prices, momentum_12_1(prices), nominal)
    print(f"        {len(ours)} monthly observations")

    print("\n  [4/4] validating the implementation against Ken French UMD")
    umd = await umd_monthly()
    joined = pd.concat([ours.rename("ours"), umd.rename("umd")], axis=1, sort=True).dropna()
    corr = float(joined["ours"].corr(joined["umd"])) if len(joined) > 12 else None
    print(f"        correlation with UMD: {corr:.3f} over {len(joined)} months"
          if corr is not None else "        not enough overlap to validate")

    # The criterion is declared in alpha_archive.verification, before any run,
    # against a fixture we did not produce. Nothing here can move it. The
    # correlation below is a sanity check and is deliberately not passed to
    # evaluate() — a check against a differently-constructed factor cannot
    # verify parity, no matter how high it comes back.
    verification = evaluate(PAPER, None)
    sanity_result = sanity(PAPER, corr)

    measured_pct = float(ours.mean() * 100)
    tstat = t_stat(ours)
    sharpe = float(ours.mean() / ours.std(ddof=1) * np.sqrt(12)) if ours.std(ddof=1) else float("nan")
    claimed = claim["value"]
    gap = round(measured_pct - claimed, 3) if claimed is not None else None

    eras = umd_eras(umd)
    ours_era = eras.get("2006-2026 (our window)", {})
    umd_flat_too = abs(ours_era.get("t_stat", 9)) < 2.0

    if verification["status"] != "VERIFIED":
        verdict = (f"UNVERIFIED — {verification['reason']} Numbers below are a measurement "
                   "on our sample, not a replication of the paper.")
    elif umd_flat_too and tstat < 2.0:
        verdict = ("decayed — the published factor is also flat over this window, so this "
                   "agrees with the literature rather than contradicting the paper")
    elif tstat >= 2.0 and measured_pct > 0:
        verdict = "survives on this sample"
    elif measured_pct > 0:
        verdict = "positive but not significant on this sample"
    else:
        verdict = "does not survive on this sample"

    return Result(
        paper=PAPER,
        authors=claim["authors"],
        year=int(claim["year"]),
        claimed_monthly_pct=claimed,
        claimed_t_stat=claim["t_stat"],
        claimed_sample=f"{claim['sample_start']}-{claim['sample_end']}",
        measured_monthly_pct=round(measured_pct, 4),
        measured_t_stat=round(tstat, 3),
        measured_sharpe_annual=round(sharpe, 3),
        measured_sample=f"{ours.index[0].date()}..{ours.index[-1].date()}",
        months=len(ours),
        umd_correlation=round(corr, 4) if corr is not None else None,
        umd_months_compared=len(joined),
        verification=verification,
        sanity_check=sanity_result,
        gap_monthly_pct=gap,
        verdict=verdict,
        umd_by_era=eras,
        universe_size=int(prices.shape[1]),
        generated_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        caveats=[
            "Universe is survivor-biased: only currently-listed large caps. The "
            "delisted losers momentum would have shorted are structurally absent, "
            "which biases this test against the paper's result.",
            f"Sample is {ours.index[0].date()}..{ours.index[-1].date()}, not the "
            f"paper's {claim['sample_start']}-{claim['sample_end']}. This is a "
            "different experiment, not a refutation.",
            f"{prices.shape[1]} names versus all of NYSE/AMEX in the original, so "
            "deciles here are far coarser.",
            f"Costs charged at {COST_BPS:.0f} bps on turnover; the paper reported gross.",
            f"Holding period is {HOLD_MONTHS} months with overlapping cohorts, matching "
            f"the documented spec. Names below ${MIN_PRICE:.0f} nominal are screened out at "
            "formation.",
            "Prices are Yahoo adjusted closes, which are adjusted retroactively.",
        ],
    )


def report(r: Result) -> None:
    print("\n" + "=" * 68)
    print(f"  {r.authors} ({r.year}) — {r.paper}")
    print("=" * 68)
    print(f"  claimed    {r.claimed_monthly_pct:>8}%/mo   t = {r.claimed_t_stat:<6} "
          f"({r.claimed_sample})")
    print(f"  measured   {r.measured_monthly_pct:>8}%/mo   t = {r.measured_t_stat:<6} "
          f"({r.measured_sample}, {r.months} months)")
    print(f"  gap        {r.gap_monthly_pct:>8}%/mo")
    print(f"  annualised Sharpe: {r.measured_sharpe_annual}")
    print()
    v = r.verification
    print(f"  VERIFICATION: {v['status']}")
    print(f"    criterion: {v['criterion']['statistic']} >= {v['criterion']['threshold']}")
    print(f"    fixture:   {v['criterion']['fixture']}")
    print(f"    {v['reason']}")
    if r.sanity_check:
        print()
        print(f"  sanity check (does not verify): {r.sanity_check['description']}")
    print()
    if r.umd_by_era:
        print("  Ken French's own UMD, by era — is it us, or did it decay?")
        for label, e in r.umd_by_era.items():
            print(f"    {label:<30} {e['mean_monthly_pct']:+7.3f}%/mo  "
                  f"t {e['t_stat']:+6.2f}  n={e['months']}")
        print()
    print(f"  VERDICT: {r.verdict}")
    print("\n  What this sample cannot tell you:")
    for c in r.caveats:
        print(f"    - {c}")
    print("=" * 68)


def main() -> None:
    result = asyncio.run(run())
    report(result)
    out = os.path.join("data", "replications", f"{PAPER.lower()}_vintage.json")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(asdict(result), fh, indent=2)
    print(f"\nwrote {out}")


if __name__ == "__main__":
    main()
