"""Reference implementation for the low-volatility anomaly.

Original: Baker-Haugen 1991, refined by Baker-Bradley-Wurgler 2011.
Stocks with low trailing realized volatility outperform high-vol stocks
on a risk-adjusted basis. Long-short sorted by trailing 12-month
realized vol, long bottom quintile, short top quintile.

Signal convention: higher = more bullish, so we return `-vol` (low-vol
stocks score high).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

LOOKBACK_DAYS = 252  # 12 months trailing


def signal(prices: pd.DataFrame) -> pd.DataFrame:
    """Negative trailing realized volatility: low-vol stocks score high."""
    rets = prices.pct_change()
    vol = rets.rolling(LOOKBACK_DAYS, min_periods=LOOKBACK_DAYS // 2).std()
    return -vol


SPEC = {
    "fixture_id": "low_vol_baker_haugen_1991",
    "hypothesis": "Low-volatility stocks deliver higher risk-adjusted returns; institutional benchmark-hugging suppresses arbitrage",
    "formula": "rank by -realized_vol(252d); long bottom quintile of vol, short top quintile",
    "data_required": ["adjusted_close"],
    "universe": "sp500",
    "rebalance_freq": "monthly",
    "horizon_days": 21,
    "expected_sign": "+",
    "claimed_sharpe": 0.5,
    "claimed_period": "1968-2008",
}


if __name__ == "__main__":
    from alpha_archive.backtest import run_signal_backtest
    from alpha_archive.fixtures import get_fixture

    fx = get_fixture("low_vol_baker_haugen_1991")
    result = run_signal_backtest(
        signal_fn=signal,
        signal_name="low_vol_baker_haugen_1991",
        universe=fx.expected_universe,
        start="2014-01-01",
        end="2026-04-01",
        horizon_days=fx.expected_horizon_days,
        cost_bps=5.0,
        n_trials_for_dsr=1,
        long_only=False,
        expected_sharpe=fx.expected_sharpe_post_costs,
        oos_split_date="2024-01-01",
    )

    print(f"\n=== Baker-Haugen (1991) low-vol replication ===")
    print(f"Sharpe (full):        {result.sharpe:.3f}")
    print(f"Sharpe (OOS 2024+):   {result.sharpe_oos}")
    print(f"Ann return:           {result.ann_return*100:.2f}%")
    print(f"Ann vol:              {result.ann_vol*100:.2f}%")
    print(f"Max DD:               {result.max_drawdown*100:.2f}%")
    print(f"IC mean:              {result.ic_report.ic_mean:.4f}")
    print(f"ICIR:                 {result.ic_report.icir:.3f}")
    print(f"DSR:                  {result.dsr.get('dsr', 'n/a')}")
    print(f"Replication score:    {result.replication_score:.2f}  (claimed Sharpe={fx.expected_sharpe_post_costs})")
    print(f"VERDICT:              {result.verdict.upper()}")
    for r in result.verdict_reasoning:
        print(f"  - {r}")
