"""End-to-end replication of Novy-Marx 2013 gross profitability anomaly
on EODHD-pulled fundamentals + grain prices.

Signal: GP/A = grossProfit / totalAssets, cross-sectionally ranked monthly.
Long top tercile, short bottom tercile, equal-weighted. Monthly rebalance,
1-month hold.

Uses PIT-correct gating: each month, the signal value for ticker T at
month-end M is the most recent grossProfit + totalAssets where
filing_date <= M. Lookahead-free.

Universe: whatever tickers are cached in data/_eodhd_probe/ (+ have
matching grain prices). Probe set has ~33 large US names — too small for
real published-Sharpe comparison, but sufficient to validate the pipeline
end-to-end on PIT EODHD data.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from alpha_archive.data.fundamentals import (
    list_cached_tickers, load_fundamentals_panel,
)
from alpha_archive.data.prices import load_price_panel


# ---- 1. Load data ---------------------------------------------------------

tickers = list_cached_tickers()
print(f"universe: {len(tickers)} tickers")

inc = load_fundamentals_panel(tickers, fields=["grossProfit"], statement="income")
bal = load_fundamentals_panel(tickers, fields=["totalAssets"], statement="balance")

# Merge on (ticker, fiscal_date) — both statements share fiscal periods
fund = pd.merge(
    inc[["ticker", "filing_date", "fiscal_date", "grossProfit"]],
    bal[["ticker", "fiscal_date", "totalAssets"]],
    on=["ticker", "fiscal_date"], how="inner",
).dropna(subset=["grossProfit", "totalAssets"])

# Filter junk: positive total assets only
fund = fund[fund["totalAssets"] > 0].copy()
fund["gpa"] = fund["grossProfit"] / fund["totalAssets"]

print(f"fundamentals panel: {len(fund)} (ticker, fiscal) rows after merge + clean")

# ---- 2. Build PIT signal panel (one signal value per ticker per month) ---

prices = load_price_panel(tickers=tickers, start="2000-01-01")
print(f"price panel: {prices.shape[0]} dates x {prices.shape[1]} tickers")

month_ends = prices.resample("ME").last().index
signal_rows = []
for me in month_ends:
    visible = fund[fund["filing_date"] <= me]
    if visible.empty:
        continue
    latest = visible.sort_values("filing_date").groupby("ticker").tail(1)
    latest = latest.set_index("ticker")["gpa"]
    for t, v in latest.items():
        signal_rows.append({"month_end": me, "ticker": t, "gpa": v})

signal = pd.DataFrame(signal_rows)
print(f"PIT signal panel: {len(signal)} (month, ticker) rows, "
      f"{signal['month_end'].nunique()} months, "
      f"avg cross-section size = {len(signal)/signal['month_end'].nunique():.1f}")

# ---- 3. Cross-sectional rank → tercile portfolios -----------------------

monthly_rets = prices.resample("ME").last().pct_change()
monthly_rets.index = pd.to_datetime(monthly_rets.index)

ls_rows = []
for me, group in signal.groupby("month_end"):
    if len(group) < 6:           # need enough names to form terciles
        continue
    if me not in monthly_rets.index:
        continue
    next_idx = monthly_rets.index.get_loc(me) + 1
    if next_idx >= len(monthly_rets.index):
        continue
    next_month = monthly_rets.index[next_idx]
    next_rets = monthly_rets.loc[next_month]
    # Rank into terciles
    g = group.copy()
    g["rank"] = g["gpa"].rank(pct=True)
    long  = g[g["rank"] >= 2/3]["ticker"].tolist()
    short = g[g["rank"] <= 1/3]["ticker"].tolist()
    long_rets  = next_rets.reindex(long).dropna()
    short_rets = next_rets.reindex(short).dropna()
    if len(long_rets) == 0 or len(short_rets) == 0:
        continue
    ls = long_rets.mean() - short_rets.mean()
    ls_rows.append({
        "month_end": me, "next_month": next_month,
        "n_long": len(long_rets), "n_short": len(short_rets),
        "long_ret": long_rets.mean(), "short_ret": short_rets.mean(),
        "ls_ret": ls,
    })

ls_df = pd.DataFrame(ls_rows)
print(f"L-S monthly observations: {len(ls_df)}")

# ---- 4. Performance metrics ---------------------------------------------

ls_ret = ls_df["ls_ret"].dropna()
print()
print("=" * 70)
print("Novy-Marx GP/A on probe universe — replication results")
print("=" * 70)
print(f"  observations:           {len(ls_ret)} months")
print(f"  date range:             {ls_df['next_month'].min().date()} -> "
      f"{ls_df['next_month'].max().date()}")
print(f"  L-S mean monthly ret:   {ls_ret.mean()*100:+.3f}%")
print(f"  L-S monthly vol:        {ls_ret.std()*100:.3f}%")
print(f"  L-S annualized Sharpe:  {ls_ret.mean()/ls_ret.std()*np.sqrt(12):+.3f}")
print(f"  L-S t-stat:             {ls_ret.mean()/(ls_ret.std()/np.sqrt(len(ls_ret))):.3f}")
print(f"  Hit rate (% positive):  {(ls_ret > 0).mean()*100:.1f}%")
print(f"  Avg long  cross-section: {ls_df['n_long'].mean():.1f}")
print(f"  Avg short cross-section: {ls_df['n_short'].mean():.1f}")

# Compare to literature
print()
print("=" * 70)
print("Literature comparison (Novy-Marx 2013 + post-pub decay)")
print("=" * 70)
print(f"  Original paper US sample 1963-2010, full universe, monthly:")
print(f"    expected Sharpe (annualized): ~0.45-0.55")
print(f"    expected t-stat:              4.0-5.0")
print(f"  Post-publication decay (McLean-Pontiff 2016): ~50% of original alpha")
print(f"    expected post-2013 Sharpe:    ~0.20-0.30")
print(f"  This replication caveats:")
print(f"    - tiny universe ({signal['ticker'].nunique()} large-cap survivors only)")
print(f"    - probe was today's-survivors only -> survivorship-biased UPWARD")
print(f"    - tercile cuts on 33 names give ~11/group -> high portfolio noise")
print(f"    - missing ~95% of HXZ universe (small/mid cap where the anomaly is strongest)")
