"""The paper's evaluation, addressed to its own cells.

Every number here comes out keyed by where the paper prints it:

    T6/CSM approach/Baseline/k = 3/TW  ->  the terminal wealth we computed

so `tools/score_replication.py` can compare cell against cell without anybody
choosing which numbers to report. The addresses come from the checklist that
`tools/extract_artifacts.py` harvested off the PDF, not from this file.

Definitions, with the page they are on (Brou & Luger, JBF; PDF page numbers):

  strategy   binary switching. Long the index when the predicted excess return
             is positive, in bills otherwise. No leverage, no shorting, decided
             at the start of each month and held (p.29).
  costs      10bp of portfolio value, charged only when the position changes,
             applied as W(1+r)(1-c) — after the month's return, as written (p.30).
  TW         terminal wealth from $1 (p.29, and Table D1's note).
  AV         monthly mean x 12, in percent (p.30).
  SD         monthly sd x sqrt(12), in percent (p.30).
  SR         the paper says only "the Sharpe ratio". It is the monthly excess
             mean over the monthly sd of the portfolio return: buy-and-hold's
             12.65/15.00 is 0.84 and its monthly total-return ratio is 0.24,
             but its monthly excess ratio is 0.17, which is what Table 6 prints.
             Recovered from the numbers, not from the text.
  MDD        a fraction, despite the note saying percent. Every value in Table 6
             lies in [0.04, 0.51] and the 2007-09 drawdown really was ~51%.
  R2_OOS     1 - sum L(r - rhat) / sum L(r - rbar) against the rolling
             historical average, for squared and absolute loss, in percent (p.25).
  CER        mean-variance: mu - gamma/2 sigma^2. CRRA: the certainty equivalent
             of realised power utility. gamma = 5, gains are differences against
             a benchmark, annualised, in percentage points (p.33-34).

Where the paper is silent, the choice is named in a comment and recorded in
`ASSUMPTIONS` so it reaches the artifact file rather than dying here.
"""

from __future__ import annotations

import itertools
import json
import os

import numpy as np
import pandas as pd
from scipy import optimize, special, stats

from .decomp2026_paper import (
    KS, MC_NODES, PREDICTORS, WINDOW, _U, MEM, fit_mem, load, probit,
    rolling_windows, select_subset, _csm_scores, _linear_scores,
    forecast_csm, forecast_csr, forecast_historical_average, forecast_linear,
)

COST = 0.0010          # 10bp on a switch
GAMMA = 5.0            # risk aversion in Tables 7 and 8
MONTHS = 12

# What the paper does not say, and what this file does instead. These reach the
# artifact file so a disagreement can be traced to a choice rather than argued
# about. Every one of them was found by reading for silence, not for content.
ASSUMPTIONS = {
    "risk_free": "Goyal-Welch Rfree. The paper says 'excess returns' and never "
                 "names the rate.",
    "index": "CRSP_SPvw, with dividends. Never stated; the 12.65% buy-and-hold "
             "AV is unreachable without them.",
    "returns": "simple, not log. Never stated; the momentum appendix compounds "
               "(1+r) and the portfolio arithmetic only closes under simple.",
    "sharpe": "monthly excess mean over monthly total sd. Never stated; "
              "recovered from buy-and-hold's printed 0.17.",
    "mdd": "a fraction. The table note says percent and every value contradicts it.",
    "oos_start": "June 1981. p.22's counts give 487 months from June; p.31 says "
                 "May 1981, which would be 488.",
    "cost_timing": "W(1+r)(1-c) on a switch, as printed, so the cost lands after "
                   "the month's return rather than at the trade.",
    "metrics_gross": "AV, SD, SR and MDD are computed on the portfolio return "
                     "before costs; costs enter TW only. Not stated, and the "
                     "notation puts (1-c) in the wealth recursion alone.",
    "cer_annualised": "monthly CER gain x 12 for both preference types. The "
                      "paper says 'we annualize' and never says how.",
    "mc_nodes": f"deterministic {MC_NODES}-node midpoint grid for the integral in "
                "eq. (15), not random draws. The paper never states a draw count, "
                "and a seeded RNG would make every number depend on a choice the "
                "paper did not make.",
}

# Rows we do not build, and why. Named here so the gap is a statement rather
# than a silence, and so coverage counts them as NOT_ATTEMPTED rather than
# quietly leaving them out of the denominator.
NOT_BUILT = {
    "GARCH-M model": "The paper estimates it in R by QML and never writes the "
                     "forecast equation; whether the mean carries sigma or "
                     "sigma-squared rests on one orphaned subscript.",
    "MS model": "Estimated with the R package MSwM. The paper gives no forecast "
                "formula and does not say whether filtered or smoothed regime "
                "probabilities are used.",
}


# ------------------------------------------------------------------- strategy

def switching(forecast: np.ndarray, mkt: np.ndarray, rf: np.ndarray) -> dict:
    """The paper's switching rule, and everything Table 6 reports about it."""
    equity = forecast > 0
    ret = np.where(equity, mkt, rf)

    # Nothing is held before the first decision, so the first allocation is not
    # a switch. Charging it would put a cost on buy-and-hold, whose printed
    # 104.63 is exactly the uncosted compounding of the index.
    switched = np.empty(len(equity), dtype=bool)
    switched[0] = False
    switched[1:] = equity[1:] != equity[:-1]

    wealth = np.cumprod((1.0 + ret) * np.where(switched, 1.0 - COST, 1.0))
    peak = np.maximum.accumulate(wealth)
    return {
        "returns": ret,
        "excess": ret - rf,
        "wealth": wealth,
        "TW": float(wealth[-1]),
        "AV": float(ret.mean() * MONTHS * 100.0),
        "SD": float(ret.std(ddof=1) * np.sqrt(MONTHS) * 100.0),
        "SR": float((ret - rf).mean() / ret.std(ddof=1)),
        "MDD": float(np.max(1.0 - wealth / peak)),
        "switches": int(switched.sum()),
    }


def cer_mean_variance(ret: np.ndarray) -> float:
    return float(ret.mean() - 0.5 * GAMMA * ret.var(ddof=1))


def cer_crra(ret: np.ndarray) -> float:
    power = np.power(1.0 + ret, 1.0 - GAMMA)
    return float(np.mean(power) ** (1.0 / (1.0 - GAMMA)) - 1.0)


def r2_oos(actual: np.ndarray, model: np.ndarray, benchmark: np.ndarray,
           absolute: bool = False) -> float:
    """Campbell-Thompson R2 against the rolling historical average, in percent."""
    em, eb = actual - model, actual - benchmark
    loss = (np.abs if absolute else np.square)
    return float(100.0 * (1.0 - loss(em).sum() / loss(eb).sum()))


# ------------------------------------------------------------- copula models

def _rho_gaussian(z: np.ndarray, p: float, theta: float) -> np.ndarray:
    q = np.clip(theta, -0.999, 0.999)
    return stats.norm.cdf((stats.norm.ppf(np.clip(p, 1e-9, 1 - 1e-9))
                           + q * stats.norm.ppf(np.clip(z, 1e-9, 1 - 1e-9)))
                          / np.sqrt(1.0 - q * q))


def _rho_clayton(z: np.ndarray, p: float, theta: float) -> np.ndarray:
    t = max(theta, 1e-6)
    zz = np.clip(z, 1e-9, 1 - 1e-9)
    return 1.0 - (1.0 + ((1.0 - p) ** (-t) - 1.0) / zz ** (-t)) ** (-1.0 / t - 1.0)


def _rho_fgm(z: np.ndarray, p: float, theta: float) -> np.ndarray:
    t = np.clip(theta, -1.0, 1.0)
    return 1.0 - (1.0 - p) * (1.0 + t * p * (1.0 - 2.0 * z))


def _rho_frank(z: np.ndarray, p: float, theta: float) -> np.ndarray:
    """Frank, from the derivative of the copula rather than from the page.

    The printed expression for this one does not return a probability: at
    theta=1, p=0.6, z=0.3 it evaluates to 2.238. Differentiating C directly
    gives 0.553 and reduces to p as theta goes to zero, which is what the
    independence case requires. The PDF dropped a level of nesting.
    """
    t = theta if abs(theta) > 1e-8 else 1e-8
    zz = np.clip(z, 1e-9, 1 - 1e-9)
    a = np.exp(-t * zz) * (np.exp(-t * (1.0 - p)) - 1.0)
    b = (np.exp(-t) - 1.0) + (np.exp(-t * zz) - 1.0) * (np.exp(-t * (1.0 - p)) - 1.0)
    return np.clip(a / b, 1e-9, 1 - 1e-9)


COPULAS = {
    "Gaussian": (_rho_gaussian, (-0.95, 0.95), 0.0),
    "Frank": (_rho_frank, (-30.0, 30.0), 0.5),
    "Clayton": (_rho_clayton, (1e-4, 20.0), 0.5),
    "FGM": (_rho_fgm, (-1.0, 1.0), 0.0),
}


def _mem_cdf(mem: MEM, psi: np.ndarray, m: np.ndarray) -> np.ndarray:
    """F(m|x) = 1 - exp(-[(m/psi) Gamma(1+1/kappa)]^kappa), eq. (5)."""
    g = special.gamma(1.0 + 1.0 / mem.kappa)
    z = np.clip((m / np.clip(psi, 1e-12, None)) * g, 0.0, 50.0) ** mem.kappa
    return np.clip(1.0 - np.exp(-z), 1e-9, 1 - 1e-9)


def forecast_copula(frame: pd.DataFrame, subset: tuple[str, ...],
                    family: str) -> np.ndarray:
    """AG's copula decomposition: couple the magnitude MEM to a probit sign.

    Estimated by IFM, which the paper describes as the simplification of the
    joint likelihood: the MEM first, then the probit, then the single copula
    parameter on the deformed-probability likelihood of eq. (11).
    """
    rho, bounds, start = COPULAS[family]
    xs = frame["xs"].to_numpy()
    mag, sign = np.abs(xs), (xs > 0).astype(float)
    V = frame[list(subset)].to_numpy()

    out = []
    for t in rolling_windows(len(xs)):
        sl = slice(t - WINDOW, t)
        X = np.column_stack([np.ones(WINDOW), V[sl]])
        mem = fit_mem(X, mag[sl])
        beta = probit(X, sign[sl])

        psi_in = mem.psi(X)
        u = _mem_cdf(mem, psi_in, mag[sl])
        p_in = np.clip(stats.norm.cdf(np.clip(X @ beta, -8, 8)), 1e-9, 1 - 1e-9)

        def nll(theta: float) -> float:
            r = np.clip(rho(u, p_in, float(theta)), 1e-9, 1 - 1e-9)
            # Vectorised over t: rho takes a scalar p in the forecast step but
            # the in-sample likelihood needs one p per month, so it is called
            # elementwise here and broadcasting does the rest.
            return -float(np.sum(sign[sl] * np.log(r)
                                 + (1.0 - sign[sl]) * np.log(1.0 - r)))

        res = optimize.minimize_scalar(nll, bounds=bounds, method="bounded",
                                       options={"xatol": 1e-6})
        theta = float(res.x)

        row = np.concatenate([[1.0], V[t]])
        psi = float(mem.psi(row[None, :])[0])
        p = float(np.clip(stats.norm.cdf(np.clip(row @ beta, -8, 8)), 1e-9, 1 - 1e-9))
        q = mem.quantile(psi, _U)
        xi = float(np.mean(q * rho(_U, p, theta)))
        out.append(2.0 * xi - psi)
    return np.array(out)


# ------------------------------------------------- model confidence set (MCS)

def mcs_pvalues(losses: dict[str, np.ndarray], boot: int = 5000,
                block: int = 2, seed: int = 20260204) -> dict[str, float]:
    """Hansen, Lunde and Nason (2011), the T_max variant of Section 3.1.2.

    The paper reports p-values from the R MCS package and states neither the
    block length nor the number of replications, so the package's own defaults
    are used and recorded as an assumption. The seed is fixed because a p-value
    that moves between runs cannot be scored against a printed one.
    """
    names = list(losses)
    L = np.column_stack([losses[n] for n in names])
    n, m = L.shape
    rng = np.random.default_rng(seed)

    # Stationary bootstrap indices, shared across models so the resampling
    # cannot favour one of them.
    idx = np.empty((boot, n), dtype=np.int64)
    for b in range(boot):
        i, pos = rng.integers(0, n), 0
        while pos < n:
            run = min(rng.geometric(1.0 / block), n - pos)
            take = (np.arange(i, i + run) % n)
            idx[b, pos:pos + run] = take
            pos += run
            i = rng.integers(0, n)

    alive = list(range(m))
    pvals: dict[str, float] = {}
    running = 0.0
    while len(alive) > 1:
        sub = L[:, alive]
        d = sub - sub.mean(axis=1, keepdims=True)   # loss vs the live average
        dbar = d.mean(axis=0)
        boot_mean = d[idx].mean(axis=1)             # (boot, alive)
        var = boot_mean.var(axis=0, ddof=1)
        var = np.where(var < 1e-18, 1e-18, var)
        tstat = dbar / np.sqrt(var)
        tboot = (boot_mean - dbar) / np.sqrt(var)

        tmax, tmax_boot = tstat.max(), tboot.max(axis=1)
        p = float((tmax_boot >= tmax).mean())
        running = max(running, p)

        worst = int(np.argmax(tstat))
        pvals[names[alive[worst]]] = running
        alive.pop(worst)

    pvals[names[alive[0]]] = 1.0
    return pvals


# ------------------------------------------------------------------ the grid

MOMENTUM = (3, 6, 12)


def momentum_positions(frame: pd.DataFrame, months: int) -> np.ndarray:
    """Long when the past n months of index return are cumulatively positive."""
    mkt = frame["mkt"].to_numpy()
    cum = pd.Series(mkt).rolling(months).apply(lambda w: np.prod(1 + w) - 1.0,
                                               raw=True).to_numpy()
    return cum[WINDOW - 1:len(mkt) - 1]      # decided at t, held over t+1


def correlations(frame: pd.DataFrame) -> dict[str, float]:
    """Table 1, all three panels, over the whole 887-month sample (p.11).

    The decomposition is the paper's own: r is the raw excess return, s its
    sign and m its magnitude, each correlated against predictors already lagged
    one month by `load`. Panel C is the predictor block on its own, printed as
    an upper triangle, so only the cells the page actually fills are emitted.
    """
    r = frame["xs"].to_numpy()
    s = (r > 0).astype(float)
    m = np.abs(r)
    x = {p: frame[p].to_numpy() for p in PREDICTORS}

    def rho(a: np.ndarray, b: np.ndarray) -> float:
        return float(np.corrcoef(a, b)[0, 1])

    out: dict[str, float] = {}

    pa = "T1/Panel A: Between r and x"
    out[f"{pa}/r/r"] = 1.0
    for p in PREDICTORS:
        out[f"{pa}/r/{p}"] = rho(r, x[p])

    pb = "T1/Panel B: Between s , m , and x"
    series = {"s": s, "m": m}
    out[f"{pb}/s/s"] = 1.0
    out[f"{pb}/s/m"] = rho(s, m)
    out[f"{pb}/m/m"] = 1.0
    for row, values in series.items():
        for p in PREDICTORS:
            out[f"{pb}/{row}/{p}"] = rho(values, x[p])

    # Panel C prints the upper triangle only: the cell below the diagonal is
    # the same number and the page leaves it blank, so writing it would invent
    # an address the paper never used.
    pc = "T1/Panel C: Among x"
    for i, a in enumerate(PREDICTORS):
        out[f"{pc}/{a}/{a}"] = 1.0
        for b in PREDICTORS[i + 1:]:
            out[f"{pc}/{a}/{b}"] = rho(x[a], x[b])
    return out


# Appendix C dates its own crises, so nothing here is a guess: "The GFC is
# defined as August 2007 to March 2009, while the COVID-19 crisis period spans
# December 2019 to December 2021" (p.69), with k = 8 throughout and initial
# wealth normalised to $1 at the start of each window.
CRISES = {
    "Global Financial Crisis": ("2007-08", "2009-03"),
    "COVID-19 Crisis": ("2019-12", "2021-12"),
}


def crisis_tables(frame: pd.DataFrame,
                  forecasts: dict[str, np.ndarray],
                  paths: dict | None = None) -> dict[str, float]:
    """Table C1: the same strategies, scored inside two named windows.

    The forecasts are the ones already produced for k = 8; re-estimating inside
    the crisis would be a different exercise from the one the appendix
    describes, which evaluates the main analysis over a sub-period.
    """
    oos = frame.iloc[WINDOW:]
    index = oos.index
    mkt, rf = oos["mkt"].to_numpy(), oos["rf"].to_numpy()

    rows: dict[str, np.ndarray] = {"Buy and hold": np.ones(len(mkt))}
    for n in MOMENTUM:
        rows[f"{n}-month"] = momentum_positions(frame, n)
    rows.update(forecasts)

    out: dict[str, float] = {}
    for name, (start, end) in CRISES.items():
        mask = (index >= start) & (index <= f"{end}-31")
        for row, signal in rows.items():
            if row == "Historical average":
                continue
            if paths is not None:
                paths[f"{name}/{row}"] = switching(
                    signal[mask], mkt[mask], rf[mask])["wealth"]
            # Wealth restarts at $1 inside the window, so the slice is taken
            # before compounding rather than read off the full path.
            s = switching(signal[mask], mkt[mask], rf[mask])
            label = (f"TC1/Momentum/{row}" if row.endswith("-month")
                     else f"TC1/{row}")
            for metric in ("TW", "AV", "SD", "SR", "MDD"):
                out[f"{label}/{name}/{metric}"] = s[metric]
    return out


def with_momentum(frame: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    """Appendix D's ninth predictor: momentum, t-12 to t-2 (p.74).

    "the cumulative return from month t-12 to t-2, excluding the most recent
    month to mitigate short-term reversal effects". `load` builds the column
    off the untrimmed series so the sample keeps its 887 months here; this
    only names it as a predictor.
    """
    return frame.dropna(subset=["mom"]), PREDICTORS + ["mom"]


def full_set_table(frame: pd.DataFrame, families: tuple[str, ...]) -> dict[str, float]:
    """Table D1: every model re-estimated on all nine predictors at once.

    One subset rather than a grid, so this is a single pass of each forecast
    rather than another eight.
    """
    wide, names = with_momentum(frame)
    subset = tuple(names)
    oos = wide.iloc[WINDOW:]
    mkt, rf, xs = (oos["mkt"].to_numpy(), oos["rf"].to_numpy(),
                   oos["xs"].to_numpy())
    ha = forecast_historical_average(wide)

    forecasts = {
        "Linear model": forecast_linear(wide, subset),
        "CSR approach": forecast_csr(wide, len(subset)),
        "CSM approach/Baseline": forecast_csm(wide, subset, poly=False),
        "CSM approach/Poly": forecast_csm(wide, subset, poly=True),
    }
    for fam in families:
        forecasts[f"Copula-based approach/{fam}"] = forecast_copula(
            wide, subset, fam)

    out: dict[str, float] = {}
    for row, fc in forecasts.items():
        s = switching(fc, mkt, rf)
        out[f"TD1/{row}/OOS/Squared"] = r2_oos(xs, fc, ha)
        out[f"TD1/{row}/OOS/Absolute"] = r2_oos(xs, fc, ha, absolute=True)
        for metric in ("TW", "AV", "SD", "SR", "MDD"):
            out[f"TD1/{row}/OOS/{metric}"] = s[metric]
    return out


def build(ks: tuple[int, ...] = KS, families: tuple[str, ...] = tuple(COPULAS),
          verbose: bool = True, paths: dict | None = None) -> dict:
    frame = load()
    oos = frame.iloc[WINDOW:]
    mkt, rf, xs = (oos["mkt"].to_numpy(), oos["rf"].to_numpy(),
                   oos["xs"].to_numpy())

    ha = forecast_historical_average(frame)
    computed: dict[str, float] = {}
    notes: dict[str, str] = {}

    # Benchmarks. They do not depend on k, and the paper repeats them across
    # every k panel, so they are written into all of them.
    bench = {"Buy and hold": switching(np.ones(len(mkt)), mkt, rf)}
    for n in MOMENTUM:
        bench[f"{n}-month"] = switching(momentum_positions(frame, n), mkt, rf)
    ha_stats = switching(ha, mkt, rf)

    def put(cell: str, value: float) -> None:
        computed[cell] = float(value)

    # Table 1 does not depend on k, so it is computed once rather than eight
    # times with the last write winning.
    computed.update(correlations(frame))

    for k in ks:
        if verbose:
            print(f"k={k}", flush=True)
        lin_sub = select_subset(frame, k, _linear_scores)
        csm_sub = select_subset(frame, k, _csm_scores)

        forecasts: dict[str, np.ndarray] = {
            "Historical average": ha,
            "Linear model": forecast_linear(frame, lin_sub),
            "CSR approach": forecast_csr(frame, k),
            "CSM approach/Baseline": forecast_csm(frame, csm_sub, poly=False),
            "CSM approach/Poly": forecast_csm(frame, csm_sub, poly=True),
        }
        for fam in families:
            forecasts[f"Copula-based approach/{fam}"] = forecast_copula(
                frame, csm_sub, fam)

        notes[f"k={k}"] = (f"linear subset {lin_sub}, decomposition subset {csm_sub}")

        stats_by_row = {}
        for row, fc in forecasts.items():
            stats_by_row[row] = switching(fc, mkt, rf)

        # Wealth paths, kept so the figures can be redrawn without re-running
        # the grid. Only the k values the paper plots are worth the disk.
        if paths is not None and k in (3, 8):
            for row, s in list(bench.items()) + list(stats_by_row.items()):
                paths[f"k{k}/{row}"] = s["wealth"]

        # Appendix C runs at k = 8, so its windows are scored off this pass
        # rather than from a second run of the same eight forecasts.
        if k == 8:
            computed.update(crisis_tables(frame, forecasts, paths))

        # ---- Table 3: out-of-sample R2, both losses, in percent
        for row, fc in forecasts.items():
            if row == "Historical average":
                continue
            put(f"T3/{row}/k = {k}/Squared", r2_oos(xs, fc, ha))
            put(f"T3/{row}/k = {k}/Absolute", r2_oos(xs, fc, ha, absolute=True))

        # ---- Tables 4 and 5: average loss x100 and the MCS p-value
        for table, absolute in (("T4", False), ("T5", True)):
            loss = {r: (np.abs(xs - f) if absolute else (xs - f) ** 2)
                    for r, f in forecasts.items()}
            p = mcs_pvalues(loss)
            metric = "MAE" if absolute else "MSE"
            for row in forecasts:
                put(f"{table}/{row}/k = {k}/{metric}", loss[row].mean() * 100.0)
                put(f"{table}/{row}/k = {k}/MCS p-value", p[row])

        # ---- Table 6 (k in 1,2,3,7) and B1 (k in 4,5,6,8)
        table = "T6" if k in (1, 2, 3, 7) else "TB1"
        for row, s in list(bench.items()) + list(stats_by_row.items()):
            if row == "Historical average":
                continue
            prefix = (f"{table}/Momentum/{row}" if row.endswith("-month")
                      else f"{table}/{row}")
            for metric in ("TW", "AV", "SD", "SR", "MDD"):
                put(f"{prefix}/k = {k}/{metric}", s[metric])

        # ---- Tables 7 and 8: CER gains, annualised, in percentage points
        t7 = "T7" if k in (1, 2, 3, 7) else "TB2"
        t8 = "T8" if k in (1, 2, 3, 7) else "TB3"
        base_mv = cer_mean_variance(ha_stats["returns"])
        base_cr = cer_crra(ha_stats["returns"])
        csm_mv = cer_mean_variance(stats_by_row["CSM approach/Baseline"]["returns"])
        csm_cr = cer_crra(stats_by_row["CSM approach/Baseline"]["returns"])

        for row, s in list(bench.items()) + list(stats_by_row.items()):
            if row in ("Historical average", "Buy and hold"):
                continue
            label = f"{row} momentum" if row.endswith("-month") else row
            mv = cer_mean_variance(s["returns"])
            cr = cer_crra(s["returns"])
            put(f"{t7}/Panel A: Mean-variance preferences/{label}/k = {k}",
                (mv - base_mv) * MONTHS * 100.0)
            put(f"{t7}/Panel B: CRRA preferences/{label}/k = {k}",
                (cr - base_cr) * MONTHS * 100.0)
            if row.startswith("Copula") or row == "CSM approach/Poly":
                short = label.split("/")[-1] if row.startswith("Copula") else label
                put(f"{t8}/Panel A: Mean-variance preferences/{short}/k = {k}",
                    (mv - csm_mv) * MONTHS * 100.0)
                put(f"{t8}/Panel B: CRRA preferences/{short}/k = {k}",
                    (cr - csm_cr) * MONTHS * 100.0)

    if 8 in ks:
        if verbose:
            print("D1 (nine predictors)", flush=True)
        computed.update(full_set_table(frame, families))

    return {"computed": computed, "notes": notes,
            "assumptions": ASSUMPTIONS, "not_built": NOT_BUILT}


if __name__ == "__main__":
    import sys
    ks = tuple(int(x) for x in sys.argv[1:]) or KS
    payload = build(ks)
    out = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__)))), "data", "computed_2606.04153.json")
    with open(out, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(payload, fh, indent=1)
    print(f"{len(payload['computed'])} cells -> {out}")
