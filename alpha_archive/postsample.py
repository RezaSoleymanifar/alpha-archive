"""Run each published predictor on the years its own paper never saw.

Chen and Zimmermann already reproduced these in sample. Doing that again is
duplicated work. The open question is what happened *afterwards*: McLean and
Pontiff put post-publication decay near 58%, Hou, Xue and Zhang failed most of
the set under stricter tests, and the argument is unsettled. Every predictor
here carries a `SampleEndYear`, so the window the paper never saw is a
subtraction, and running it is a contribution rather than a repeat.

The rules this module holds to:

  * Nothing is published for a predictor until the implementation has been
    calibrated: run on the paper's OWN sample years and checked against the
    number the paper printed. An uncalibrated post-sample result is a claim
    about our code rather than about the market, and it is worse than no
    result because it looks like one.
  * The post-sample window starts the January after the paper's sample ended.
    Not one month after publication, and not a round number. The paper's own
    stated end date.
  * The claim is read from SignalDoc, never from us.
  * The five checks in `claims.py` run on the post-sample series, not the full
    one, because the full one contains the years the paper was fitted on.
  * A predictor with no implementation is recorded as pending rather than
    dropped, so the leaderboard shows what is missing as clearly as what ran.

Signals live in `SIGNALS`, keyed by SignalDoc acronym. Adding one is a function
that takes a price panel and returns a score per name per date; everything else
here already knows what to do with it.
"""

from __future__ import annotations

import csv
import io
import json
import os
from dataclasses import asdict, dataclass, field
from datetime import date
from typing import Any, Callable

import numpy as np
import pandas as pd

from .claims import Claim, verify
from .fixtures_openap import download_signaldoc

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STORE = os.path.join(ROOT, "data", "postsample")

TRADING_DAYS = 252


# ------------------------------------------------------------------ signals

# Each function returns the RAW quantity the paper names, never a direction.
# SignalDoc publishes a `Sign` per predictor saying which way it points, and the
# runner multiplies by it. Hardcoding a negation here is how a signal ends up
# reproducing the paper's effect backwards: I did exactly that on the first
# pass, and Beta came out inverted because I assumed low-beta when SignalDoc
# says the published portfolio is long high beta.

def _mom(prices: pd.DataFrame, lookback: int, skip: int = 21) -> pd.DataFrame:
    return prices.shift(skip) / prices.shift(lookback) - 1.0


def mom12m(prices: pd.DataFrame) -> pd.DataFrame:
    """Twelve-month return, skipping the most recent month."""
    return _mom(prices, 252)


def mom6m(prices: pd.DataFrame) -> pd.DataFrame:
    return _mom(prices, 126)


def strev(prices: pd.DataFrame) -> pd.DataFrame:
    """Last month's return. SignalDoc's sign makes it a reversal."""
    return prices / prices.shift(21) - 1.0


def maxret(prices: pd.DataFrame) -> pd.DataFrame:
    """The largest daily return in the trailing month."""
    return prices.pct_change().rolling(21).max()


def retvol(prices: pd.DataFrame) -> pd.DataFrame:
    """Trailing twelve-month volatility of daily returns."""
    return prices.pct_change().rolling(252).std()


def idiovol(prices: pd.DataFrame) -> pd.DataFrame:
    """Residual volatility against an equal-weighted market.

    The published version regresses on the Fama-French three factors. This uses
    a single market factor built from the panel itself, a weaker control, and
    every row it produces says so.
    """
    rets = prices.pct_change()
    market = rets.mean(axis=1)
    window = 252
    beta_ = rets.rolling(window).cov(market).div(market.rolling(window).var(), axis=0)
    resid = rets.sub(beta_.mul(market, axis=0))
    return resid.rolling(window).std()


def beta(prices: pd.DataFrame) -> pd.DataFrame:
    """Market beta against an equal-weighted market."""
    rets = prices.pct_change()
    market = rets.mean(axis=1)
    return rets.rolling(252).cov(market).div(market.rolling(252).var(), axis=0)


@dataclass(frozen=True)
class Signal:
    fn: Callable[[pd.DataFrame], pd.DataFrame]
    note: str = ""


SIGNALS: dict[str, Signal] = {
    "Mom12m": Signal(mom12m),
    "Mom6m": Signal(mom6m),
    "STreversal": Signal(strev),
    "MaxRet": Signal(maxret),
    "RetVol": Signal(retvol),
    "IdioVol3F": Signal(
        idiovol,
        "controls on a single equal-weighted market factor rather than the "
        "published three, so this is a weaker control than the paper's",
    ),
    "Beta": Signal(beta),
}

# VolSD was in this list and should not have been. SignalDoc calls it Volume
# Variance, which is the variance of trading volume, and what was implemented
# was the volatility of returns. That is a different predictor wearing the same
# acronym, and it calibrated to a t of the wrong sign because it was never the
# right signal. It comes back when volume data does.


# ------------------------------------------------------------------- the run

@dataclass
class PostSample:
    """One predictor, judged on the years after its own sample."""
    acronym: str
    description: str = ""
    authors: str = ""
    year: int | None = None
    sample_end_year: int | None = None
    claimed_t: float | None = None
    claimed_monthly_return: float | None = None
    published_sign: float | None = None
    data_category: str = ""

    window_start: str | None = None
    window_end: str | None = None
    years_out_of_sample: float | None = None
    # The window the paper never saw and the slice of it we can actually price
    # are different things when the price history is shorter than the gap.
    tested_start: str | None = None
    tested_end: str | None = None
    years_tested: float | None = None

    # Step one: does the implementation reproduce the paper on the paper's
    # own years? Until this passes, nothing downstream is published.
    sample_start_year: int | None = None
    calib_start: str | None = None
    calib_end: str | None = None
    calib_years: float | None = None
    calib_t: float | None = None
    calib_sharpe: float | None = None
    calibration: str = "not attempted"   # calibrated | miscalibrated | no_overlap
    calib_note: str = ""

    post_sharpe: float | None = None
    post_annual_return: float | None = None
    post_t: float | None = None
    decay: float | None = None            # 1 - post/claimed, on the t-statistic
    status: str = "pending"               # pending | ran | no_data | no_signal
    verdict: str | None = None
    reasons: list[str] = field(default_factory=list)
    note: str = ""

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def signaldoc_rows() -> list[dict[str, str]]:
    path = download_signaldoc()
    with io.open(path, encoding="utf-8-sig") as fh:
        return list(csv.DictReader(fh))


def _num(row: dict, key: str) -> float | None:
    try:
        return float(str(row.get(key, "")).strip())
    except (TypeError, ValueError):
        return None


def window_for(sample_end_year: int | None) -> tuple[str, str] | None:
    """The years the paper never saw: the January after its sample ended."""
    if not sample_end_year:
        return None
    start = f"{int(sample_end_year) + 1}-01-01"
    end = date.today().isoformat()
    if start >= end:
        return None
    return start, end


def catalogue() -> list[PostSample]:
    """Every predictor with its claim and its post-sample window, unrun."""
    out = []
    for row in signaldoc_rows():
        acronym = (row.get("Acronym") or "").strip()
        if not acronym:
            continue
        end_year = _num(row, "SampleEndYear")
        window = window_for(int(end_year) if end_year else None)
        rec = PostSample(
            acronym=acronym,
            description=(row.get("LongDescription") or "").strip(),
            authors=(row.get("Authors") or "").strip(),
            year=int(_num(row, "Year") or 0) or None,
            sample_end_year=int(end_year) if end_year else None,
            sample_start_year=(int(_num(row, "SampleStartYear"))
                               if _num(row, "SampleStartYear") else None),
            claimed_t=_num(row, "T-Stat"),
            claimed_monthly_return=_num(row, "Mean Return"),
            published_sign=_num(row, "Sign"),
            data_category=(row.get("Cat.Data") or "").strip(),
        )
        if window:
            rec.window_start, rec.window_end = window
            rec.years_out_of_sample = round(
                (date.fromisoformat(window[1]).year
                 - date.fromisoformat(window[0]).year), 1)
        if acronym not in SIGNALS:
            rec.status = "no_signal"
            rec.note = "no implementation yet"
        elif SIGNALS[acronym].note:
            rec.note = SIGNALS[acronym].note
        out.append(rec)
    return out


def _long_short(scores: pd.DataFrame, prices: pd.DataFrame,
                *, top: float = 0.2, cost_bps: float = 10.0) -> pd.Series:
    """Equal-weighted long the top fifth, short the bottom, monthly rebalance."""
    rets = prices.pct_change()
    weights = pd.DataFrame(0.0, index=prices.index, columns=prices.columns)
    holding: pd.Series | None = None
    turnover = pd.Series(0.0, index=prices.index)

    for day in prices.resample("ME").last().index:
        if day not in prices.index:
            continue
        seen = scores.loc[scores.index < day]
        if seen.empty:
            continue
        row = seen.iloc[-1].dropna()
        if len(row) < 10:
            continue
        n = max(2, int(len(row) * top))
        ranked = row.sort_values(ascending=False)
        target = pd.Series(0.0, index=prices.columns)
        target[ranked.index[:n]] = 0.5 / n
        target[ranked.index[-n:]] = -0.5 / n
        turnover.loc[day] = float((target - holding).abs().sum()) if holding is not None \
            else float(target.abs().sum())
        holding = target
        weights.loc[weights.index >= day] = target.values

    gross = (weights.shift(1) * rets).sum(axis=1)
    return (gross - turnover * (cost_bps / 10_000.0)).dropna()


MIN_CALIB_YEARS = 5.0
# How far the reproduced t may sit from the published one and still count as the
# same signal. Wide on purpose: the universe, the weighting and the cost model
# all differ from the paper, so this asks whether the implementation finds the
# same effect, not whether it lands on the same decimal.
CALIB_T_TOLERANCE = 0.6      # as a fraction of the published t
CALIB_MIN_T = 1.5


def _directed(rec: "PostSample", prices: pd.DataFrame) -> pd.DataFrame:
    """The raw signal, pointed the way SignalDoc says the paper pointed it."""
    raw = SIGNALS[rec.acronym].fn(prices)
    return raw * (rec.published_sign if rec.published_sign else 1.0)


def _score(scores: pd.DataFrame, prices: pd.DataFrame,
           start: str, end: str) -> tuple[pd.Series, str]:
    window = prices.loc[start:end]
    if len(window) < 300:
        return pd.Series(dtype=float), (
            f"only {len(window)} trading days available in {start}..{end}")
    net = _long_short(scores.loc[window.index], window)
    if net.empty or float(net.std()) == 0:
        return pd.Series(dtype=float), "the signal produced no tradeable cross-section"
    return net, ""


def _t_stat(net: pd.Series) -> float:
    from vintage.engine import validation
    return validation.newey_west_t(list(net.values)).get("newey_west_t") or 0.0


def calibrate(rec: PostSample, prices: pd.DataFrame) -> PostSample:
    """Step one: reproduce the paper on the paper's own years.

    Passing this is what earns the right to say anything about the years after
    it. Failing it is a finding about our implementation, not about the market,
    and the page has to say which of the two it is looking at.
    """
    signal = SIGNALS.get(rec.acronym)
    if signal is None or not rec.sample_start_year or not rec.sample_end_year:
        rec.calibration = "no_overlap"
        rec.calib_note = "no implementation, or the paper's sample years are unstated"
        return rec

    have_start = str(prices.index[0].date())
    start = max(f"{rec.sample_start_year}-01-01", have_start)
    end = f"{rec.sample_end_year}-12-31"
    if start >= end:
        rec.calibration = "no_overlap"
        rec.calib_note = (f"the paper's sample ends in {rec.sample_end_year} and our "
                          f"price history starts in {have_start[:4]}, so there is no "
                          f"overlap to calibrate on")
        return rec

    net, why = _score(_directed(rec, prices), prices, start, end)
    if net.empty:
        rec.calibration = "no_overlap"
        rec.calib_note = why
        return rec

    rec.calib_start, rec.calib_end = start, str(net.index[-1].date())
    rec.calib_years = round(len(net) / TRADING_DAYS, 1)
    rec.calib_sharpe = round(float(net.mean() / net.std()) * np.sqrt(TRADING_DAYS), 3)
    rec.calib_t = round(_t_stat(net), 3)

    if rec.calib_years < MIN_CALIB_YEARS:
        rec.calibration = "no_overlap"
        rec.calib_note = (f"only {rec.calib_years} years of the paper's sample are "
                          f"priced, below the {MIN_CALIB_YEARS} needed to calibrate")
        return rec

    claimed = rec.claimed_t or 0.0
    if claimed <= 0:
        rec.calibration = "no_overlap"
        rec.calib_note = "the paper publishes no t-statistic to calibrate against"
        return rec

    close = abs(rec.calib_t - claimed) <= CALIB_T_TOLERANCE * claimed
    if rec.calib_t >= CALIB_MIN_T and close:
        rec.calibration = "calibrated"
        rec.calib_note = (f"reproduces t = {rec.calib_t} against the published "
                          f"{claimed}, on {rec.calib_years} years of the paper's "
                          f"own sample")
    else:
        rec.calibration = "miscalibrated"
        rec.calib_note = (f"reproduces t = {rec.calib_t} against the published "
                          f"{claimed}. The implementation does not find the "
                          f"paper's effect on the paper's own years, so nothing "
                          f"is claimed about the years after it")
    return rec


def run_one(rec: PostSample, prices: pd.DataFrame) -> PostSample:
    """Step two, and only for an implementation that calibrated."""
    rec = calibrate(rec, prices)
    signal = SIGNALS.get(rec.acronym)
    if signal is None or not rec.window_start:
        return rec
    if rec.calibration != "calibrated":
        rec.status = "uncalibrated"
        return rec

    net, why = _score(_directed(rec, prices), prices,
                      rec.window_start, rec.window_end)
    if net.empty:
        rec.status = "no_data"
        rec.note = why
        return rec

    rec.tested_start = str(net.index[0].date())
    rec.tested_end = str(net.index[-1].date())
    rec.years_tested = round(len(net) / TRADING_DAYS, 1)
    rec.post_sharpe = round(float(net.mean() / net.std()) * np.sqrt(TRADING_DAYS), 3)
    total = float((1 + net).prod())
    years = len(net) / TRADING_DAYS
    rec.post_annual_return = round(total ** (1 / years) - 1, 4) if total > 0 else None

    claim = Claim(
        paper_id=f"openap_{rec.acronym.lower()}",
        source="Open Source Asset Pricing SignalDoc",
        claimed_t=rec.claimed_t,
        claimed_annual_return=((rec.claimed_monthly_return / 100.0 * 12.0)
                               if rec.claimed_monthly_return is not None else None),
        sample_start_year=rec.sample_start_year,
        sample_end_year=rec.sample_end_year,
    )
    verdict = verify(claim, list(net.values), trials=1)
    rec.verdict = verdict.status
    rec.reasons = verdict.reasons
    rec.post_t = verdict.detail.get("newey_west", {}).get("newey_west_t")
    if rec.claimed_t and rec.post_t is not None and rec.claimed_t > 0:
        rec.decay = round(1 - (rec.post_t / rec.claimed_t), 3)
    rec.status = "ran"
    return rec


def run_all(prices: pd.DataFrame) -> list[PostSample]:
    return [run_one(rec, prices) for rec in catalogue()]


def save(records: list[PostSample]) -> str:
    os.makedirs(STORE, exist_ok=True)
    path = os.path.join(STORE, "postsample.json")
    payload = {
        "generated_at": date.today().isoformat(),
        "note": ("Each predictor scored only on the years after its own paper's "
                 "sample ended. In-sample reproduction is Chen and Zimmermann's "
                 "work; this is the part they did not do."),
        "records": [r.as_dict() for r in records],
    }
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(payload, fh, indent=1)
    return path


def load() -> list[dict[str, Any]]:
    path = os.path.join(STORE, "postsample.json")
    if not os.path.exists(path):
        return []
    with io.open(path, encoding="utf-8") as fh:
        return json.load(fh).get("records", [])
