"""Reference implementation for Betting-Against-Beta (Frazzini-Pedersen 2014).

Cross-sectional rolling beta to a market proxy. Low-beta stocks
outperform high-beta on a risk-adjusted basis; the original BAB factor
leverages low-beta and de-leverages high-beta to unit beta. This
simplified replication uses the long-low-beta / short-high-beta sort
without the leverage step (sufficient for IC + sign verification on
Phase-0.5 calibration).

Market proxy: cross-sectional equal-weight mean of universe returns
(avoids needing SPY in the universe).

Signal convention: higher = more bullish, so we return `-beta`.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

WINDOW = 252  # 1y rolling


def _rolling_beta(stock_rets: pd.DataFrame, mkt_rets: pd.Series, window: int) -> pd.DataFrame:
    """Per-ticker rolling OLS beta to market over `window` days."""
    # cov(s, m) / var(m), computed with rolling sums for speed
    var_m = mkt_rets.rolling(window, min_periods=window // 2).var()

    def _beta_one(col: pd.Series) -> pd.Series:
        cov_sm = col.rolling(window, min_periods=window // 2).cov(mkt_rets)
        return cov_sm / var_m

    return stock_rets.apply(_beta_one)


def signal(prices: pd.DataFrame) -> pd.DataFrame:
    """Negative trailing beta to equal-weight market proxy."""
    rets = prices.pct_change()
    mkt = rets.mean(axis=1)  # equal-weight market proxy
    beta = _rolling_beta(rets, mkt, WINDOW)
    return -beta


SPEC = {
    "fixture_id": "bab_frazzini_pedersen_2014",
    "hypothesis": "Leverage-constrained investors bid up high-beta stocks; low-beta delivers higher risk-adjusted returns",
    "formula": "rank by -beta(252d) vs equal-weight market; long bottom-beta, short top-beta",
    "data_required": ["adjusted_close"],
    "universe": "sp500",
    "rebalance_freq": "monthly",
    "horizon_days": 21,
    "expected_sign": "+",
    "claimed_sharpe": 0.85,
    "claimed_period": "1926-2012",
}


if __name__ == "__main__":
    from alpha_archive.backtest import run_signal_backtest
    from alpha_archive.fixtures import get_fixture

    fx = get_fixture("bab_frazzini_pedersen_2014")
    result = run_signal_backtest(
        signal_fn=signal,
        signal_name="bab_frazzini_pedersen_2014",
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

    print(f"\n=== Frazzini-Pedersen (2014) BAB replication ===")
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
