"""Reference implementation for the MAX anomaly (Bali-Cakici-Whitelaw 2011).

Stocks with high maximum daily returns in the prior month underperform
in the following month — interpreted as retail lottery preference.
Long-short sorted by past-month max-daily-return.

Signal convention: higher = more bullish, so we return `-max_return`.
"""
from __future__ import annotations

import pandas as pd

LOOKBACK_DAYS = 21  # ~1 month


def signal(prices: pd.DataFrame) -> pd.DataFrame:
    """Negative max daily return over past month."""
    rets = prices.pct_change()
    max_ret = rets.rolling(LOOKBACK_DAYS, min_periods=LOOKBACK_DAYS // 2).max()
    return -max_ret


SPEC = {
    "fixture_id": "max_bali_2011",
    "hypothesis": "Retail lottery preference: investors overpay for stocks with extreme recent upside, mean-reverting underperformance follows",
    "formula": "rank by -max(daily_return, last 21d); long low-MAX, short high-MAX",
    "data_required": ["adjusted_close"],
    "universe": "sp500",
    "rebalance_freq": "monthly",
    "horizon_days": 21,
    "expected_sign": "+",
    "claimed_sharpe": 0.7,
    "claimed_period": "1962-2005",
}


if __name__ == "__main__":
    from alpha_archive.backtest import run_signal_backtest
    from alpha_archive.fixtures import get_fixture

    fx = get_fixture("max_bali_2011")
    result = run_signal_backtest(
        signal_fn=signal,
        signal_name="max_bali_2011",
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

    print(f"\n=== Bali-Cakici-Whitelaw (2011) MAX replication ===")
    print(f"Sharpe (full):        {result.sharpe:.3f}")
    print(f"Sharpe (OOS 2024+):   {result.sharpe_oos}")
    print(f"Ann return:           {result.ann_return*100:.2f}%")
    print(f"IC mean:              {result.ic_report.ic_mean:.4f}")
    print(f"ICIR:                 {result.ic_report.icir:.3f}")
    print(f"DSR:                  {result.dsr.get('dsr', 'n/a')}")
    print(f"Replication score:    {result.replication_score:.2f}  (claimed Sharpe={fx.expected_sharpe_post_costs})")
    print(f"VERDICT:              {result.verdict.upper()}")
    for r in result.verdict_reasoning:
        print(f"  - {r}")
