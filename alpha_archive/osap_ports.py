"""Chen and Zimmermann's own portfolio returns, as the calibration fixture.

Calibrating against a t-statistic recomputed on our universe was never a
calibration. It compared our number to the paper's number with a different
universe, a different weighting and a different cost model in between, so a
disagreement could not be attributed to anything.

This is the fixture: the monthly long-short return series Chen and Zimmermann
publish per predictor, fetched through their own package. Calibration becomes a
correlation between their series and ours over the months both cover, which is
a question about the implementation rather than about the sample.

The earlier note in this repository said the series was Google Drive only and
returned interstitials. That was true of the raw Drive links and is not true of
`openassetpricing`, which is the authors' package and fetches it in seconds.

    from alpha_archive.osap_ports import long_short
    theirs = long_short("Mom12m")     # a monthly pandas Series, in percent
"""

from __future__ import annotations

import io
import os
import warnings

import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE = os.path.join(ROOT, "data", "cache", "osap_ports.parquet")

# Which portfolio column carries the published long-short leg. The file holds
# every decile as well, and taking the wrong one would compare our spread to
# their bottom decile.
LONG_SHORT = "LS"


def _download() -> pd.DataFrame:
    import openassetpricing as oap

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        frame = oap.OpenAP().dl_port("op", "pandas")
    return frame


def table(refresh: bool = False) -> pd.DataFrame:
    """Every predictor's published portfolio returns, cached on disk.

    The download is ~66k rows per predictor set and takes seconds, but it is a
    network call inside a calibration loop, so it is fetched once.
    """
    if not refresh and os.path.exists(CACHE):
        return pd.read_parquet(CACHE)
    frame = _download()
    os.makedirs(os.path.dirname(CACHE), exist_ok=True)
    frame.to_parquet(CACHE, index=False)
    return frame


_TABLE: pd.DataFrame | None = None


def _cached() -> pd.DataFrame:
    global _TABLE
    if _TABLE is None:
        _TABLE = table()
    return _TABLE


def available() -> set[str]:
    return set(_cached()["signalname"].unique())


def long_short(acronym: str) -> pd.Series:
    """The published long-short series for one predictor, month-end indexed.

    Returns an empty Series when the predictor is not in the file, which is a
    fact about the fixture and is reported rather than worked around.
    """
    frame = _cached()
    rows = frame[(frame["signalname"] == acronym) & (frame["port"] == LONG_SHORT)]
    if rows.empty:
        return pd.Series(dtype=float)
    out = rows.set_index(pd.to_datetime(rows["date"]))["ret"].sort_index()
    out.index = out.index.to_period("M").to_timestamp("M")
    return out[~out.index.duplicated(keep="last")]


def compare(ours: pd.Series, theirs: pd.Series) -> dict:
    """How close our monthly series is to the published one.

    `ours` is daily; it is compounded to month end before comparing, because the
    fixture is monthly and resampling theirs would invent detail it does not
    have.
    """
    if ours.empty or theirs.empty:
        return {"months": 0, "correlation": None,
                "note": "one of the two series is empty"}

    monthly = (1 + ours).resample("ME").prod() - 1.0
    monthly = monthly * 100.0                      # the fixture is in percent
    joined = pd.concat([monthly.rename("ours"), theirs.rename("theirs")],
                       axis=1).dropna()
    if len(joined) < 24:
        return {"months": len(joined), "correlation": None,
                "note": f"only {len(joined)} overlapping months, too few to judge"}

    corr = float(joined["ours"].corr(joined["theirs"]))
    return {
        "months": len(joined),
        "from": str(joined.index[0].date()),
        "to": str(joined.index[-1].date()),
        "correlation": round(corr, 3),
        "ours_mean": round(float(joined["ours"].mean()), 4),
        "theirs_mean": round(float(joined["theirs"].mean()), 4),
        "note": "",
    }
