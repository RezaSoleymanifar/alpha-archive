"""Reference implementation for Jegadeesh-Titman 1993 cross-sectional momentum.

Original paper: rank stocks by past 12-1 month return; long top decile, short
bottom decile; rebalance monthly; hold 3-12 months.

This implementation is the canonical "golden" version, what the LLM should
approximate when given the paper. Used as fixture in the meta-learning loop.
"""
from __future__ import annotations

import pandas as pd

LOOKBACK_DAYS = 252  # 12 months
SKIP_DAYS = 21       # skip most recent 1 month (12-1 momentum)


def signal(prices: pd.DataFrame) -> pd.DataFrame:
    """Compute 12-1 momentum signal cross-sectionally.

    Args:
        prices: DataFrame [date x ticker], adjusted close prices.
    Returns:
        DataFrame [date x ticker] of signal values (higher = more bullish).
    """
    # cumulative return from t-252 to t-21
    sig = (prices.shift(SKIP_DAYS) / prices.shift(LOOKBACK_DAYS)) - 1
    return sig


# Metadata for the meta-learning loop
SPEC = {
    "fixture_id": "momentum_jt1993",
    "hypothesis": "Stocks with high past 12-1 month returns continue to outperform; underreaction to recent news",
    "formula": "rank by (price[t-21] / price[t-252]) - 1; long top, short bottom",
    "data_required": ["adjusted_close"],
    "universe": "sp500",
    "rebalance_freq": "monthly",
    "horizon_days": 21,
    "expected_sign": "+",
    "claimed_sharpe": 0.7,
    "claimed_period": "1965-1989",
}


if __name__ == "__main__":
    from alpha_archive.backtest import run_signal_backtest
    from alpha_archive.fixtures import get_fixture

    fx = get_fixture("momentum_jt1993")
    result = run_signal_backtest(
        signal_fn=signal,
        signal_name="momentum_jt1993",
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

    print(f"\n=== Jegadeesh-Titman (1993) momentum replication ===")
    print(f"Sharpe (full):        {result.sharpe:.3f}")
    print(f"Sharpe (OOS 2024+):   {result.sharpe_oos}")
    print(f"Ann return:           {result.ann_return*100:.2f}%")
    print(f"Ann vol:              {result.ann_vol*100:.2f}%")
    print(f"Max DD:               {result.max_drawdown*100:.2f}%")
    print(f"Calmar:               {result.calmar:.3f}")
    print(f"Turnover (avg/day):   {result.turnover:.4f}")
    print()
    print(f"IC mean:              {result.ic_report.ic_mean:.4f}")
    print(f"IC std:               {result.ic_report.ic_std:.4f}")
    print(f"ICIR:                 {result.ic_report.icir:.3f}")
    print(f"IC t-stat:            {result.ic_report.t_stat:.3f}")
    print(f"IC grade:             {result.ic_report.grade()}")
    print()
    print(f"DSR:                  {result.dsr.get('dsr', 'n/a')}")
    print(f"DSR p-value:          {result.dsr.get('p_value', 'n/a')}")
    print()
    print(f"Replication score:    {result.replication_score:.2f}  (claimed Sharpe={fx.expected_sharpe_post_costs})")
    print(f"VERDICT:              {result.verdict.upper()}")
    for r in result.verdict_reasoning:
        print(f"  - {r}")
