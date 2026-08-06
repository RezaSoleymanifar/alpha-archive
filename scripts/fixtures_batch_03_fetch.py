"""Fetch and cache the daily panels batch_03 needs: close, volume, and shares.

harness.panel() caches adjusted closes only. Four of the nine specs in this
batch (share volume, turnover volatility, volume variance, and the momentum
screen) need traded volume too, and Datar-Naik-Radcliffe turnover needs a share
count that yfinance only publishes back to about 2015. Everything lands in the
same cache directory the harness uses so a rerun costs nothing.
"""

from __future__ import annotations

import os
import sys
import time

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from alpha_archive.fixtures_bank import harness
from alpha_archive.fixtures_bank.universe import TICKERS


def main() -> None:
    os.makedirs(harness.CACHE, exist_ok=True)
    import yfinance as yf

    vol_path = os.path.join(harness.CACHE, "volume.parquet")
    close_path = os.path.join(harness.CACHE, "panel.parquet")

    if not (os.path.exists(vol_path) and os.path.exists(close_path)):
        raw = yf.download(TICKERS, start=harness.START, end=harness.END,
                          auto_adjust=True, progress=False, group_by="column")
        close = raw["Close"].dropna(how="all").sort_index()
        volume = raw["Volume"].dropna(how="all").sort_index()
        close = close.dropna(axis=1, how="all")
        volume = volume[close.columns]
        close.to_parquet(close_path)
        volume.to_parquet(vol_path)
        print("close", close.shape, "volume", volume.shape)
        print("dropped:", sorted(set(TICKERS) - set(close.columns)))
    else:
        close = pd.read_parquet(close_path)
        print("cached close", close.shape)

    shares_path = os.path.join(harness.CACHE, "shares.parquet")
    if not os.path.exists(shares_path):
        out = {}
        for i, tk in enumerate(close.columns):
            try:
                s = yf.Ticker(tk).get_shares_full(start="2004-01-01")
                if s is not None and len(s):
                    s = s[~s.index.duplicated(keep="last")]
                    s.index = pd.to_datetime(s.index).tz_localize(None).normalize()
                    out[tk] = s.groupby(level=0).last()
            except Exception as exc:
                print("shares fail", tk, type(exc).__name__)
            if i % 20 == 0:
                print("  shares", i, tk, flush=True)
            time.sleep(0.05)
        shares = pd.DataFrame(out).sort_index()
        shares.to_parquet(shares_path)
        print("shares", shares.shape, shares.index.min(), shares.index.max())


if __name__ == "__main__":
    main()
