"""Deflated Sharpe Ratio (Bailey + Lopez de Prado 2014).

Adjusts an observed Sharpe ratio for:
  - Number of trials N (multiple-testing inflation)
  - Skew + kurtosis of returns (non-normality)
  - Sample size T

Returns probability that the true SR > 0 given the data + corrections.
"""
from __future__ import annotations

import math

import numpy as np
from scipy import stats


def expected_max_sharpe(n_trials: int) -> float:
    """Expected max Sharpe under null (all strategies have true SR = 0).
    Uses extreme value approximation: E[max] ≈ √(2 · ln(N)) for N >= 2.
    """
    if n_trials <= 1:
        return 0.0
    # More accurate: includes (1 - γ_E) / sqrt(N - 1) correction
    euler_mascheroni = 0.5772156649
    inv_phi = stats.norm.ppf(1.0 - 1.0 / n_trials)
    inv_phi_2 = stats.norm.ppf(1.0 - 1.0 / (n_trials * np.e))
    e_max = (1 - euler_mascheroni) * inv_phi + euler_mascheroni * inv_phi_2
    return float(e_max)


def deflated_sharpe_ratio(
    observed_sharpe: float,
    returns: np.ndarray,
    n_trials: int = 1,
    annualization: float = 1.0,
) -> dict:
    """
    Compute DSR.

    Args:
        observed_sharpe: the (annualized) Sharpe to test, e.g., 1.5
        returns: array of period returns the SR was computed from (e.g., daily)
        n_trials: # of strategies tested when picking this one (>=1)
        annualization: factor used to annualize the SR (e.g., √252 for daily)

    Returns dict with:
        sr_observed, expected_max_sr, sr_std, dsr, p_value, significant_at_5pct
    """
    r = np.asarray(returns).astype(float)
    r = r[~np.isnan(r)]
    T = len(r)
    if T < 30:
        return {
            "sr_observed": observed_sharpe,
            "dsr": float("nan"),
            "notes": "insufficient sample (T<30)",
        }

    skew = float(stats.skew(r))
    excess_kurt = float(stats.kurtosis(r))  # scipy returns excess by default
    kurt = excess_kurt + 3

    # Variance of SR estimator (Mertens 2002 / Lopez de Prado 2014)
    # var(SR) ≈ (1 - γ_3 · SR + ((γ_4 - 1) / 4) · SR²) / (T - 1)
    # Use non-annualized SR for the variance calc (raw daily SR)
    sr_raw = observed_sharpe / annualization if annualization else observed_sharpe
    var_sr = (1.0 - skew * sr_raw + ((kurt - 1) / 4.0) * sr_raw**2) / (T - 1)
    if var_sr <= 0:
        return {
            "sr_observed": observed_sharpe,
            "dsr": float("nan"),
            "notes": f"degenerate variance (skew={skew:.3f}, kurt={kurt:.3f})",
        }
    sr_std = math.sqrt(var_sr)

    # Expected max SR under null, in the same (raw) scale
    expected_max_raw = expected_max_sharpe(n_trials) * sr_std
    expected_max_annualized = expected_max_raw * annualization

    # Z-score: how many std-errs above expected-by-chance is the observed SR?
    z = (sr_raw - expected_max_raw) / sr_std

    # DSR = Φ(z), probability that true SR > 0 given multiple-testing adjustment
    dsr = float(stats.norm.cdf(z))
    p_value = 1.0 - dsr

    return {
        "sr_observed": observed_sharpe,
        "expected_max_sr": expected_max_annualized,
        "sr_std": sr_std * annualization,
        "n_trials": n_trials,
        "T": T,
        "skew": skew,
        "kurtosis": kurt,
        "z_score": z,
        "dsr": dsr,
        "p_value": p_value,
        "significant_at_5pct": dsr > 0.95,
    }


if __name__ == "__main__":
    # Sanity check: 1000 trials, observed annual Sharpe 2.0, T=252 daily
    rng = np.random.default_rng(0)
    fake_rets = rng.normal(0.0008, 0.012, 252)  # ~0.8 daily, ~1.06 annualized
    obs_sr = (fake_rets.mean() / fake_rets.std()) * np.sqrt(252)
    print(f"Observed annualized Sharpe: {obs_sr:.3f}")
    res = deflated_sharpe_ratio(obs_sr, fake_rets, n_trials=1000, annualization=np.sqrt(252))
    import json
    print(json.dumps({k: (round(v, 4) if isinstance(v, float) else v) for k, v in res.items()}, indent=2))
