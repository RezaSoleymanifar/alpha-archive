"""PIT-aware fundamentals loader from EODHD raw payloads.

EODHD's /fundamentals/{ticker} endpoint returns each statement's quarterly +
yearly entries with TWO dates:

    date         -> fiscal-period-end (e.g., AAPL Q4 FY25 = "2025-12-31")
    filing_date  -> when the 10-K/10-Q hit the SEC ("2026-01-30", ~30d later)

Backtest correctness REQUIRES gating on `filing_date`, NOT `date`. Otherwise
features peek at fundamentals before they were public.

This module loads cached EODHD JSONs from `data/_eodhd_probe/{TICKER}.US.json`
(probe set) or `data/_eodhd_full/{TICKER}.US.json` (universe pull, future) and
returns long-format DataFrames keyed on (ticker, filing_date).

Common usage:

    from alpha_archive.data.fundamentals import load_fundamentals_panel

    df = load_fundamentals_panel(
        tickers=["AAPL", "MSFT", "GE"],
        fields=["grossProfit", "totalRevenue", "totalAssets"],
        statement="quarterly",
    )
    # -> long DataFrame with columns: ticker, filing_date, fiscal_date,
    #    grossProfit, totalRevenue, totalAssets

    # As-of view: latest published value per ticker as known on 2024-06-30
    asof = as_of_panel(df, as_of="2024-06-30")
"""
from __future__ import annotations

import gzip
import json
import os
from dataclasses import dataclass
from functools import cache
from pathlib import Path
from typing import Iterable, Optional

import pandas as pd


REPO_ROOT = Path(__file__).resolve().parents[2]
PROBE_DIR = REPO_ROOT / "data" / "_eodhd_probe"
FULL_DIR = REPO_ROOT / "data" / "_eodhd_full"


def _grain_full_dir() -> Optional[Path]:
    """Locate grain's eodhd-fundamentals-full/ cache (gzipped raw PIT payloads,
    written by grain's `npm run eodhd:fund` after the May 2026 patch)."""
    candidates = [
        os.environ.get("GRAIN_DATA"),
        Path.home() / "dev" / "investor-copilot",
        REPO_ROOT.parent / "investor-copilot",
    ]
    for c in candidates:
        if c is None:
            continue
        p = Path(c) / "data" / "eodhd-fundamentals-full"
        if p.exists():
            return p
    return None


# Maps statement type to the path inside the EODHD payload
STATEMENT_PATH = {
    "income":   ["Financials", "Income_Statement"],
    "balance":  ["Financials", "Balance_Sheet"],
    "cashflow": ["Financials", "Cash_Flow"],
}


def _candidate_paths(ticker: str) -> list[Path]:
    """Where to look for a ticker's raw EODHD JSON, in priority order.

    Search order:
      1. alpha-archive local FULL_DIR (uncompressed JSON, post-bulk-pull)
      2. alpha-archive local PROBE_DIR (uncompressed JSON, sanity probe)
      3. grain's eodhd-fundamentals-full/ (gzipped, primary path post-patch)
    """
    t = ticker.upper().removesuffix(".US")
    paths = [
        FULL_DIR / f"{t}.US.json",
        PROBE_DIR / f"{t}.US.json",
        FULL_DIR / f"{t}.json",
        PROBE_DIR / f"{t}.json",
    ]
    grain = _grain_full_dir()
    if grain is not None:
        # Grain stores by raw ticker (no .US suffix), gzipped.
        paths += [grain / f"{t}.json.gz", grain / f"{t}.US.json.gz"]
    return paths


def _load_raw(ticker: str) -> Optional[dict]:
    """Read raw EODHD payload from disk. Returns None if not cached.
    Transparently handles both .json and .json.gz files.
    """
    for p in _candidate_paths(ticker):
        if not p.exists():
            continue
        try:
            if p.suffix == ".gz":
                with gzip.open(p, "rt", encoding="utf-8") as f:
                    d = json.load(f)
            else:
                d = json.loads(p.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        return d if isinstance(d, dict) else None
    return None


def _statement_block(raw: dict, statement: str, freq: str) -> dict:
    """Drill into raw payload to a specific quarterly/yearly statement block."""
    path = STATEMENT_PATH[statement]
    cur = raw
    for k in path:
        cur = (cur or {}).get(k, {})
    return (cur or {}).get(freq, {}) or {}


@dataclass(frozen=True)
class TickerFundamentals:
    """Coverage metadata for one ticker — useful for diagnostics."""
    ticker: str
    has_data: bool
    n_quarters: int = 0
    earliest_fiscal: Optional[str] = None
    latest_fiscal: Optional[str] = None
    has_filing_date: bool = False


def coverage(ticker: str, statement: str = "income", freq: str = "quarterly") -> TickerFundamentals:
    """Diagnostic: what does our cache have for this ticker?"""
    raw = _load_raw(ticker)
    if not raw:
        return TickerFundamentals(ticker=ticker, has_data=False)
    block = _statement_block(raw, statement, freq)
    if not block:
        return TickerFundamentals(ticker=ticker, has_data=True, n_quarters=0)
    sample = next(iter(block.values()))
    return TickerFundamentals(
        ticker=ticker,
        has_data=True,
        n_quarters=len(block),
        earliest_fiscal=min(block.keys()),
        latest_fiscal=max(block.keys()),
        has_filing_date="filing_date" in sample,
    )


def load_fundamentals_panel(
    tickers: Iterable[str],
    fields: Iterable[str],
    statement: str = "income",
    freq: str = "quarterly",
) -> pd.DataFrame:
    """Long-format PIT panel for the given tickers + fields.

    Columns: ticker, filing_date (datetime), fiscal_date (datetime), <fields...>

    Rows are the union across all tickers. Filing_date is parsed to datetime;
    rows missing filing_date fall back to fiscal_date + 45 days (conservative
    proxy matching the standard academic lag assumption).
    """
    if statement not in STATEMENT_PATH:
        raise ValueError(f"unknown statement: {statement!r}; "
                         f"choose from {list(STATEMENT_PATH)}")

    rows = []
    fields = list(fields)
    for ticker in tickers:
        raw = _load_raw(ticker)
        if not raw:
            continue
        block = _statement_block(raw, statement, freq)
        for fiscal_date, entry in block.items():
            row = {
                "ticker": ticker.upper().removesuffix(".US"),
                "fiscal_date": fiscal_date,
                "filing_date": entry.get("filing_date"),
            }
            for f in fields:
                v = entry.get(f)
                # EODHD ships strings for some numeric fields; coerce.
                if isinstance(v, str):
                    try: v = float(v)
                    except ValueError: v = None
                row[f] = v
            rows.append(row)

    if not rows:
        return pd.DataFrame(columns=["ticker", "filing_date", "fiscal_date", *fields])

    df = pd.DataFrame(rows)
    df["fiscal_date"] = pd.to_datetime(df["fiscal_date"], errors="coerce")
    df["filing_date"] = pd.to_datetime(df["filing_date"], errors="coerce")
    # Conservative fallback: 45-day lag from fiscal-period-end if filing_date missing
    fallback = df["fiscal_date"] + pd.Timedelta(days=45)
    df["filing_date"] = df["filing_date"].fillna(fallback)
    df = df.sort_values(["ticker", "filing_date"]).reset_index(drop=True)
    return df


def as_of_panel(panel: pd.DataFrame, as_of: str | pd.Timestamp) -> pd.DataFrame:
    """Latest filing per ticker known on `as_of`. Drops tickers with no
    publicly-available data by then. Returns wide one-row-per-ticker view.
    """
    as_of_ts = pd.Timestamp(as_of)
    visible = panel[panel["filing_date"] <= as_of_ts]
    if visible.empty:
        return panel.iloc[0:0].copy()
    latest = visible.sort_values("filing_date").groupby("ticker").tail(1)
    return latest.reset_index(drop=True)


def list_cached_tickers() -> list[str]:
    """All tickers we have raw fundamentals for on disk (alpha-archive local
    PROBE/FULL + grain's eodhd-fundamentals-full/)."""
    seen = set()
    for d in (FULL_DIR, PROBE_DIR):
        if d.exists():
            for p in d.glob("*.json"):
                t = p.stem.upper().removesuffix(".US")
                seen.add(t)
    grain = _grain_full_dir()
    if grain is not None:
        for p in grain.glob("*.json.gz"):
            t = p.name.removesuffix(".json.gz").upper().removesuffix(".US")
            seen.add(t)
    return sorted(seen)
