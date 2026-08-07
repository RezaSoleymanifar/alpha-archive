"""arXiv 2606.04153 (Brou & Luger, JBF): the paper as specified, not as guessed.

The earlier attempt in `decomp2026.py` reproduced the benchmark and then missed
the headline by a third. It was not a hard replication that went wrong, it was a
different model: it used log|r| where the paper uses |r|, a logit where the paper
uses a probit, OLS where the paper uses a Weibull multiplicative error model, an
expanding window where the paper rolls a fixed 400, and it averaged over every
subset for a method that the paper says selects exactly one.

What the paper actually specifies, with the page it is on:

  decomposition   R = M(2S - 1), M = |R| raw, S = 1{R > 0}. Applied to raw
                  excess returns, not mean-adjusted ones (p.8, p.12).
  magnitude       Weibull MEM. log(psi_t) = w + d'x_{t-1}, psi = E[M|x], and a
                  Weibull error scaled so E[eta|x] = 1 (p.12, eqs. 4-6).
  sign            probit, conditioned on the *realised contemporaneous*
                  magnitude: p* = Phi(w + d'x_{t-1} + b m_t) (p.18, eq. 13).
  forecast        m_{t+1} is unknown at t, so it is integrated out rather than
                  plugged in (p.18, eq. 15):

                      xi* = int_0^1 q(u) Phi(w + d'x + b q(u)) du
                      E[R|x] = 2 xi* - psi

                  Substituting a point forecast psi-hat for m gives a different,
                  Jensen-biased quantity. This is the single most important line
                  in the file.
  estimation      the two blocks share no parameters, so the MEM and the probit
                  maximise separately with no loss of efficiency (p.19).
  window          rolling, fixed length L = 400, re-estimated every month (p.24).
  subsets         one k-subset chosen by AUC on the first 400 observations and
                  held fixed. CSR is the only method that averages over subsets
                  (p.22).

The sample is 887 monthly observations, February 1948 to December 2021, split
400 in-sample and 487 out-of-sample. That is reproduced exactly, which is why
the disagreements below are about models rather than about data.

    uv run python -m alpha_archive.replications.decomp2026_paper
"""

from __future__ import annotations

import itertools
import os
import warnings
from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy import optimize, special, stats

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA = os.path.join(ROOT, "data", "cache", "goyal", "PredictorData.xlsx")

PREDICTORS = ["dp", "dfy", "tms", "tbl", "ltr", "dfr", "ntis", "infl"]
SAMPLE_START, SAMPLE_END = "1948-01", "2021-12"
WINDOW = 400              # rolling window length L, and the in-sample block
KS = (1, 2, 3, 4, 5, 6, 7, 8)

# Monte Carlo integration of eq. (15). A deterministic midpoint grid rather than
# random draws: the paper does not state its draw count, and a seeded RNG would
# make every number in this file depend on a choice the paper never made. The
# midpoint rule on 4096 nodes is accurate to well past the third decimal the
# paper prints, and it is identical on every machine and every run.
MC_NODES = 4096
_U = (np.arange(MC_NODES) + 0.5) / MC_NODES


def load() -> pd.DataFrame:
    """Goyal-Welch monthly, built to the paper's 887 observations.

    The count is the check: get the vintage, the index, the risk-free rate or
    the lag wrong and it is not 887, so this function failing loudly is worth
    more than any comment in it.
    """
    with warnings.catch_warnings():
        # openpyxl objects to a header in Goyal's workbook. Cosmetic.
        warnings.simplefilter("ignore", UserWarning)
        m = pd.read_excel(DATA, sheet_name="Monthly")

    m["date"] = pd.to_datetime(m["yyyymm"].astype(str), format="%Y%m")
    m = m.set_index("date")

    m["mkt"] = pd.to_numeric(m["CRSP_SPvw"], errors="coerce")
    m["rf"] = m["Rfree"].astype(float)
    m["xs"] = m["mkt"] - m["rf"]
    m["dp"] = np.log(m["D12"]) - np.log(m["Index"])
    m["dfy"] = m["BAA"].astype(float) - m["AAA"].astype(float)
    m["tms"] = m["lty"].astype(float) - m["tbl"].astype(float)
    m["dfr"] = m["corpr"].astype(float) - m["ltr"].astype(float)
    for col in ("tbl", "ltr", "ntis", "infl"):
        m[col] = pd.to_numeric(m[col], errors="coerce")

    # Appendix D's ninth predictor, built here rather than downstream because
    # it needs eleven months of history that exist before the sample opens.
    # Computed on the untrimmed series and shifted once, so that after the
    # common predictor lag below it spans t-12 to t-2, as the paper writes it.
    m["mom"] = ((1.0 + m["mkt"]).rolling(11).apply(np.prod, raw=True) - 1.0).shift(1)

    columns = PREDICTORS + ["mom", "mkt", "rf", "xs"]
    frame = m.loc[SAMPLE_START:SAMPLE_END, columns].copy()
    # Predictors are dated t-1 and forecast t. Shifting once here is what makes
    # every model below out-of-sample by construction rather than by promise.
    for col in PREDICTORS + ["mom"]:
        frame[col] = frame[col].shift(1)
    # `mom` is not one of the eight, so it must not decide which months survive:
    # dropping on the eight keeps the paper's 887 whatever the appendix needs.
    frame = frame.dropna(subset=PREDICTORS + ["mkt", "rf", "xs"])

    if len(frame) != 887:
        raise RuntimeError(
            f"expected the paper's 887 observations, built {len(frame)}. "
            "The data vintage or the lag alignment has moved.")
    return frame


# ------------------------------------------------------------------ estimators

def _ols(X: np.ndarray, y: np.ndarray) -> np.ndarray:
    return np.linalg.lstsq(X, y, rcond=None)[0]


def _design(values: np.ndarray, cols: list[int]) -> np.ndarray:
    return np.column_stack([np.ones(len(values)), values[:, cols]])


def probit(X: np.ndarray, y: np.ndarray, start: np.ndarray | None = None) -> np.ndarray:
    """Probit by Newton on the exact Hessian.

    The log-likelihood is globally concave (Maddala 1983 p.26, cited by the
    paper at p.19), so this converges from any start and the starting value is
    not a free parameter anyone has to justify.
    """
    beta = np.zeros(X.shape[1]) if start is None else start.copy()
    for _ in range(80):
        eta = np.clip(X @ beta, -8, 8)
        cdf = np.clip(stats.norm.cdf(eta), 1e-12, 1 - 1e-12)
        pdf = stats.norm.pdf(eta)
        lam = pdf * (y - cdf) / (cdf * (1 - cdf))
        w = pdf ** 2 / (cdf * (1 - cdf))
        hess = X.T @ (X * w[:, None]) + 1e-8 * np.eye(X.shape[1])
        step = np.linalg.solve(hess, X.T @ lam)
        beta += step
        if np.max(np.abs(step)) < 1e-9:
            break
    return beta


@dataclass
class MEM:
    """Fitted Weibull multiplicative error model for the magnitude."""
    w: float
    delta: np.ndarray
    kappa: float

    def psi(self, X: np.ndarray) -> np.ndarray:
        """E[M | x] = exp(w + delta'x). X carries its own intercept column."""
        beta = np.concatenate([[self.w], self.delta])
        return np.exp(np.clip(X @ beta, -20, 5))

    def quantile(self, psi: float, u: np.ndarray) -> np.ndarray:
        """q(u) = psi * Gamma(1+1/kappa)^-1 * (-log(1-u))^(1/kappa)  (p.15)."""
        g = special.gamma(1.0 + 1.0 / self.kappa)
        return psi / g * (-np.log(1.0 - u)) ** (1.0 / self.kappa)


def fit_mem(X: np.ndarray, m: np.ndarray) -> MEM:
    """Maximise the Weibull MEM likelihood of eq. (6).

    log f = log k - k*log(psi) + k*log(G) + (k-1)*log(m) - [(m/psi) G]^k,
    with G = Gamma(1 + 1/k), which is the scaling that forces E[eta|x] = 1.
    """
    m = np.clip(m, 1e-10, None)
    logm = np.log(m)
    start = np.concatenate([[np.log(m.mean())], np.zeros(X.shape[1] - 1), [1.0]])

    def nll(theta: np.ndarray) -> float:
        kappa = theta[-1]
        if not (0.05 < kappa < 50.0):
            return 1e12
        logpsi = np.clip(X @ theta[:-1], -20.0, 5.0)
        g = special.gamma(1.0 + 1.0 / kappa)
        z = np.exp(np.clip(kappa * (logm - logpsi + np.log(g)), -700, 700))
        ll = (np.log(kappa) - kappa * logpsi + kappa * np.log(g)
              + (kappa - 1.0) * logm - z)
        return -float(np.sum(ll)) if np.isfinite(ll).all() else 1e12

    res = optimize.minimize(nll, start, method="Nelder-Mead",
                            options={"maxiter": 8000, "xatol": 1e-8, "fatol": 1e-8})
    theta = res.x
    return MEM(w=float(theta[0]), delta=theta[1:-1], kappa=float(theta[-1]))


# -------------------------------------------------------------------- selection

def auc(scores: np.ndarray, positive: np.ndarray) -> float:
    """Area under the ROC curve, by the paper's own counting formula (p.23).

    Ties are worth a half, which is what the 1/2 term in the printed formula is
    doing and what separates this from a naive rank correlation.
    """
    up, down = scores[positive], scores[~positive]
    if len(up) == 0 or len(down) == 0:
        return 0.5
    diff = up[None, :] - down[:, None]
    return float((np.sum(diff > 0) + 0.5 * np.sum(diff == 0)) / (len(up) * len(down)))


def select_subset(frame: pd.DataFrame, k: int, score_fn) -> tuple[str, ...]:
    """The k-subset with the highest in-sample AUC over the first 400 months.

    Chosen once and held fixed out-of-sample, which is what the paper says at
    p.22 and what keeps the selection itself from peeking at the test period.
    """
    block = frame.iloc[:WINDOW]
    positive = block["xs"].to_numpy() > 0
    best, best_auc = None, -np.inf
    for subset in itertools.combinations(PREDICTORS, k):
        score = score_fn(block, list(subset))
        value = auc(score, positive)
        if value > best_auc:
            best, best_auc = subset, value
    return best


def _linear_scores(block: pd.DataFrame, subset: list[str]) -> np.ndarray:
    X = np.column_stack([np.ones(len(block)), block[subset].to_numpy()])
    return X @ _ols(X, block["xs"].to_numpy())


def _csm_scores(block: pd.DataFrame, subset: list[str]) -> np.ndarray:
    """In-sample sign score for selection: the probit index on realised |r|.

    Selection ranks subsets by directional accuracy, and for the decomposition
    the object that carries direction is the sign equation, so the index is the
    score. Using E[R] here instead would rank subsets by a quantity the sign
    model never sees.
    """
    xs = block["xs"].to_numpy()
    X = np.column_stack([np.ones(len(block)), block[subset].to_numpy(),
                         np.abs(xs)])
    beta = probit(X, (xs > 0).astype(float))
    return X @ beta


# ------------------------------------------------------------------- forecasts

def rolling_windows(n: int) -> range:
    """Index of each forecast origin: 400 observations behind, one month ahead."""
    return range(WINDOW, n)


def forecast_historical_average(frame: pd.DataFrame) -> np.ndarray:
    xs = frame["xs"].to_numpy()
    return np.array([xs[t - WINDOW:t].mean() for t in rolling_windows(len(xs))])


def forecast_linear(frame: pd.DataFrame, subset: tuple[str, ...]) -> np.ndarray:
    xs = frame["xs"].to_numpy()
    V = frame[list(subset)].to_numpy()
    out = []
    for t in rolling_windows(len(xs)):
        X = np.column_stack([np.ones(WINDOW), V[t - WINDOW:t]])
        beta = _ols(X, xs[t - WINDOW:t])
        out.append(float(np.concatenate([[1.0], V[t]]) @ beta))
    return np.array(out)


def forecast_csr(frame: pd.DataFrame, k: int) -> np.ndarray:
    """Every subset of size k, fitted and equally weighted (p.6).

    No selection at all: this is the one method where averaging is the method,
    and collapsing it to a chosen subset would make it the linear model.
    """
    xs = frame["xs"].to_numpy()
    subsets = [list(s) for s in itertools.combinations(range(len(PREDICTORS)), k)]
    V = frame[PREDICTORS].to_numpy()
    out = []
    for t in rolling_windows(len(xs)):
        y = xs[t - WINDOW:t]
        preds = []
        for cols in subsets:
            X = np.column_stack([np.ones(WINDOW), V[t - WINDOW:t][:, cols]])
            beta = _ols(X, y)
            preds.append(float(np.concatenate([[1.0], V[t, cols]]) @ beta))
        out.append(float(np.mean(preds)))
    return np.array(out)


def forecast_csm(frame: pd.DataFrame, subset: tuple[str, ...],
                 poly: bool = False) -> np.ndarray:
    """The paper's own method, eq. (15).

    The magnitude is integrated out over its fitted Weibull, never plugged in.
    """
    xs = frame["xs"].to_numpy()
    mag = np.abs(xs)
    sign = (xs > 0).astype(float)
    V = frame[list(subset)].to_numpy()

    out = []
    for t in rolling_windows(len(xs)):
        sl = slice(t - WINDOW, t)
        Xm = np.column_stack([np.ones(WINDOW), V[sl]])
        mem = fit_mem(Xm, mag[sl])

        cols = [np.ones(WINDOW), V[sl], mag[sl]]
        if poly:
            cols += [mag[sl] ** 2, mag[sl] ** 3]
        beta = probit(np.column_stack(cols), sign[sl])

        row = np.concatenate([[1.0], V[t]])
        psi = float(mem.psi(row[None, :])[0])
        q = mem.quantile(psi, _U)
        index = float(row @ beta[:len(row)]) + beta[len(row)] * q
        if poly:
            index = index + beta[len(row) + 1] * q ** 2 + beta[len(row) + 2] * q ** 3
        xi = float(np.mean(q * stats.norm.cdf(np.clip(index, -8, 8))))
        out.append(2.0 * xi - psi)
    return np.array(out)


def oos_frame(frame: pd.DataFrame) -> pd.DataFrame:
    """The 487 months every forecast above is aligned to."""
    return frame.iloc[WINDOW:]


if __name__ == "__main__":
    f = load()
    print(f"{len(f)} observations, {f.index[0]:%Y-%m} to {f.index[-1]:%Y-%m}")
    print(f"in-sample {WINDOW}, out-of-sample {len(f) - WINDOW}")
    for k in (1, 2, 3):
        lin = select_subset(f, k, _linear_scores)
        csm = select_subset(f, k, _csm_scores)
        print(f"  k={k}  linear={lin}  csm={csm}")
