"""batch_03: queue indices 30-38, re-tested on free data.

Nine published signals, all of them buildable from daily price and volume
except the conglomerate one, which needs business-segment sales weights that
no free source carries. Each signal is oriented so that the top decile is the
side the paper says earns more, which makes a positive observed t agree in
direction with a positive published t.

Every number this writes is a SANITY_CHECK. The papers ran on all of CRSP,
delisted names included, mostly 1963-2003; this runs on 98 names that are still
in the S&P 100 today, 2005-2026. Same signal, different world.
"""

from __future__ import annotations

import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from alpha_archive.fixtures_bank import harness
from alpha_archive.fixtures_bank.harness import (SpecResult, long_short,
                                                 monthly_returns, save, score)
from alpha_archive.fixtures_bank.universe import TICKERS

MIN_DAYS = 15          # a month with fewer trading days observed is not scored
FORM = 36              # months in a rolling estimation window


# --------------------------------------------------------------- data


def load() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    close = harness.panel(TICKERS)
    volume = pd.read_parquet(os.path.join(harness.CACHE, "volume.parquet"))
    shares = pd.read_parquet(os.path.join(harness.CACHE, "shares.parquet"))
    close = close.dropna(axis=1, how="all")
    volume = volume.reindex(columns=close.columns)
    return close, volume, shares


def month_index(close: pd.DataFrame) -> pd.DatetimeIndex:
    return close.resample("ME").last().index


def mask_thin(frame: pd.DataFrame, counts: pd.DataFrame) -> pd.DataFrame:
    return frame.where(counts >= MIN_DAYS)


# ------------------------------------------------------------ signals


def realized_vol(dret: pd.DataFrame) -> pd.DataFrame:
    """Ang et al: total volatility of daily returns in the past month.

    High volatility earned lower returns, so the signal is negated and the top
    decile is the calm names.
    """
    g = dret.groupby(pd.Grouper(freq="ME"))
    return -mask_thin(g.std(), g.count())


def return_skew(dret: pd.DataFrame) -> pd.DataFrame:
    """Bali, Engle and Murray: skewness of daily returns in the past month."""
    g = dret.groupby(pd.Grouper(freq="ME"))
    return -mask_thin(g.skew(), g.count())


def idio_skew(dret: pd.DataFrame, mkt: pd.Series) -> pd.DataFrame:
    """Skewness of the part of the daily return the market does not explain.

    The paper's residual is from Fama-French three factors. We have no SMB or
    HML without accounting data, so this is a one-factor residual against the
    equal-weighted universe return, which is a weaker control.
    """
    rows = {}
    for date, block in dret.groupby(pd.Grouper(freq="ME")):
        m = mkt.reindex(block.index)
        ok = m.notna()
        block, m = block[ok], m[ok]
        if len(block) < MIN_DAYS or m.var() == 0:
            continue
        beta = block.apply(lambda col: col.cov(m)) / m.var()
        resid = block - np.outer(m.values, beta.values)
        resid = resid - resid.mean()
        s = resid.skew()
        rows[date] = s.where(block.count() >= MIN_DAYS)
    return -pd.DataFrame(rows).T


def residual_momentum(mret: pd.DataFrame, mkt: pd.Series) -> pd.DataFrame:
    """Blitz, Huij and Martens: momentum in market-model residuals.

    Betas come from a rolling 36-month regression; the score is the mean
    residual over t-11 to t-1 divided by its own standard deviation, so the
    most recent month is skipped exactly as in plain momentum.
    """
    idx = mret.index
    out = pd.DataFrame(index=idx, columns=mret.columns, dtype=float)
    m = mkt.reindex(idx)
    for i in range(FORM, len(idx)):
        win = slice(i - FORM + 1, i + 1)
        x = m.iloc[win]
        if x.isna().any():
            continue
        X = np.column_stack([np.ones(len(x)), x.values])
        M = np.eye(len(x)) - X @ np.linalg.pinv(X)
        block = mret.iloc[win]
        good = block.notna().all(axis=0)
        if not good.any():
            continue
        resid = pd.DataFrame(M @ block.loc[:, good].values,
                             index=block.index, columns=block.columns[good])
        window = resid.iloc[-12:-1]                 # t-11 .. t-1
        sd = window.std()
        out.loc[idx[i], window.columns] = (window.mean() / sd.where(sd > 0))
    return out


def monthly_turnover(volume: pd.DataFrame, shares: pd.DataFrame,
                     idx: pd.DatetimeIndex) -> pd.DataFrame:
    """Average daily share turnover inside each month.

    Yahoo only publishes a share count back to 2013, so turnover simply does
    not exist before then and those months stay empty rather than being
    back-filled from a number nobody knew at the time.
    """
    sh = shares.reindex(columns=volume.columns)
    sh = sh.reindex(sh.index.union(volume.index)).ffill().reindex(volume.index)
    turn = volume / sh
    g = turn.groupby(pd.Grouper(freq="ME"))
    return mask_thin(g.mean(), g.count()).reindex(idx)


def rolling_cv(level: pd.DataFrame, window: int = FORM) -> pd.DataFrame:
    """Coefficient of variation of a monthly volume series, past `window`."""
    mean = level.rolling(window, min_periods=window).mean()
    sd = level.rolling(window, min_periods=window).std()
    return sd / mean.where(mean > 0)


# --------------------------------------------------------------- run


def main() -> None:
    close, volume, shares = load()
    dropped = sorted(set(TICKERS) - set(close.columns))
    print(f"universe {len(close.columns)} names, dropped {len(dropped)}: {dropped}")

    dret = close.pct_change(fill_method=None)
    mkt_d = dret.mean(axis=1)                       # equal-weighted universe
    mret = monthly_returns(close)
    mkt_m = mret.mean(axis=1)
    forward = mret.shift(-1)
    idx = month_index(close)

    mvol_shares = volume.groupby(pd.Grouper(freq="ME")).sum().reindex(idx)
    mvol_dollar = (close * volume).groupby(pd.Grouper(freq="ME")).sum().reindex(idx)
    counts = volume.groupby(pd.Grouper(freq="ME")).count().reindex(idx)
    mvol_shares = mvol_shares.where(counts >= MIN_DAYS)
    mvol_dollar = mvol_dollar.where(counts >= MIN_DAYS)
    turn = monthly_turnover(volume, shares, idx)

    specs: list[tuple[str, float, str, object, str]] = [
        ("Realized (Total) Volatility", 2.86, "1963-2000",
         realized_vol(dret),
         "Standard deviation of daily returns within the month, negated so the "
         "long leg is the low-volatility decile the paper favours."),

        ("Momentum based on FF3 residuals", 8.218550486, "1930-2009",
         residual_momentum(mret, mkt_m),
         "Residual momentum from a rolling 36-month market-model regression, "
         "scored as mean residual over t-11..t-1 divided by residual standard "
         "deviation. The paper uses all three Fama-French factors; SMB and HML "
         "need accounting data we do not have, so this controls for the market "
         "alone and is the weaker version of the signal."),

        ("Conglomerate return", 5.51, "1977-2009", None,
         ""),

        ("Return skewness", 4.01, "1963-2012",
         return_skew(dret),
         "Skewness of daily returns within the month, negated: the paper finds "
         "lottery-like right-skewed names underperform."),

        ("Idiosyncratic skewness (3F model)", 4.35, "1963-2012",
         idio_skew(dret, mkt_d),
         "Skewness of daily market-model residuals within the month, negated. "
         "One market factor stands in for Fama-French three, so the residual "
         "still contains any size and value tilt."),

        ("Share Volume", 8.86, "1962-1991",
         None,
         ""),

        ("Share turnover volatility", 3.74, "1966-1995",
         -rolling_cv(mvol_shares),
         "Coefficient of variation of monthly share volume over the past 36 "
         "months, negated. Chordia, Subrahmanyam and Anshuman scale volume by "
         "shares outstanding first; a coefficient of variation is invariant to "
         "any constant scaling, so this differs from their turnover measure "
         "only through drift in the share count, not through its level."),

        ("Short term reversal", 12.44, "1934-1987",
         -mret,
         "Last month's return, negated. The published t=12.44 came from a "
         "universe full of microcaps, where reversal is largest; nothing like "
         "it should be expected on 98 mega-caps."),

        ("Volume Variance", 3.56, "1966-1995",
         -rolling_cv(mvol_dollar),
         "Coefficient of variation of monthly dollar volume over the past 36 "
         "months, negated, following the paper's negative pricing of volume "
         "variability."),
    ]

    # Datar, Naik and Radcliffe turnover, only over the years a share count exists.
    specs[5] = (
        "Share Volume", 8.86, "1962-1991", -turn,
        "Average daily share volume divided by shares outstanding, negated. "
        "Yahoo's share count starts in 2013, so this runs on a shorter window "
        "than the other eight and the pre-2013 months are dropped rather than "
        "back-filled.",
    )

    results: list[SpecResult] = []
    for i, (title, pt, sample, signal, extra) in enumerate(specs):
        if signal is None:
            r = SpecResult(name=title, published_t=pt, published_sample=sample,
                           error="needs business-segment sales data (Compustat "
                                 "segments) to weight each division's industry "
                                 "return; not derivable from price or volume")
            r.note = ("Cohen and Lou build a pseudo-conglomerate from the "
                      "stand-alone firms in each of a conglomerate's reported "
                      "business segments. Segment identity and segment sales "
                      "weights are the whole signal and no free price source "
                      "carries them, so this one is recorded unbuilt rather "
                      "than approximated.")
            results.append(r)
            print(f"{title}: {r.error}")
            continue

        sig = signal.reindex(index=idx).astype(float)
        rets = long_short(sig, forward)
        r = score(rets, pt, sample, title)
        r.names = int(sig.notna().sum(axis=1).max())
        if extra:
            r.note = r.note + " Implementation: " + extra
        results.append(r)
        print(f"{title}: t={r.observed_t} m={r.observed_monthly_pct}% "
              f"months={r.months} names={r.names} {r.error}")

        if (i + 1) % 3 == 0:
            save(results, "batch_03")

    path = save(results, "batch_03")
    print("wrote", path)


if __name__ == "__main__":
    main()
