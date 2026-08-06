"""The shared test universe for the fixtures-bank re-tests.

Every agent running specs from `_queue.json` sorts the same 100-odd names, so
the results sit on a common footing. This is the current S&P 100 membership,
which means it is survivorship-biased by construction: these are the names that
made it. That is a known and unfixable property of free data, and the reason
nothing run against this list can be called a replication.

`SECTORS` is a hand-coded GICS sector for each ticker, used by the industry
signals. It is today's classification applied to the whole history, so a name
that switched sectors (or that GICS reshuffled, as it did with the 2018
communication-services split) carries its modern label backwards.
"""

from __future__ import annotations

TICKERS: list[str] = [
    "AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "GOOG", "META", "BRK-B", "AVGO",
    "TSLA", "JPM", "WMT", "LLY", "V", "UNH", "XOM", "ORCL", "MA", "HD", "PG",
    "COST", "JNJ", "ABBV", "BAC", "KO", "NFLX", "MRK", "CVX", "AMD", "PEP",
    "TMO", "ADBE", "LIN", "CSCO", "ACN", "MCD", "ABT", "CRM", "WFC", "IBM",
    "GE", "DIS", "TXN", "VZ", "INTU", "AMGN", "CAT", "QCOM", "NOW", "PFIZ",
    "PM", "UNP", "SPGI", "GS", "RTX", "LOW", "HON", "BKNG", "NEE", "T",
    "AXP", "BLK", "SYK", "ELV", "TJX", "VRTX", "C", "MDT", "BSX", "ADP",
    "MMC", "PLD", "CB", "LMT", "SBUX", "MDLZ", "AMT", "ETN", "CI", "SO",
    "DE", "MO", "BMY", "DUK", "ADI", "CVS", "GILD", "APD", "CL", "SCHW",
    "ZTS", "ITW", "MU", "FDX", "CME", "GD", "EOG", "NSC", "SLB", "PYPL",
]

SECTORS: dict[str, str] = {
    "AAPL": "Information Technology", "MSFT": "Information Technology",
    "NVDA": "Information Technology", "AMZN": "Consumer Discretionary",
    "GOOGL": "Communication Services", "GOOG": "Communication Services",
    "META": "Communication Services", "BRK-B": "Financials",
    "AVGO": "Information Technology", "TSLA": "Consumer Discretionary",
    "JPM": "Financials", "WMT": "Consumer Staples", "LLY": "Health Care",
    "V": "Financials", "UNH": "Health Care", "XOM": "Energy",
    "ORCL": "Information Technology", "MA": "Financials",
    "HD": "Consumer Discretionary", "PG": "Consumer Staples",
    "COST": "Consumer Staples", "JNJ": "Health Care", "ABBV": "Health Care",
    "BAC": "Financials", "KO": "Consumer Staples",
    "NFLX": "Communication Services", "MRK": "Health Care", "CVX": "Energy",
    "AMD": "Information Technology", "PEP": "Consumer Staples",
    "TMO": "Health Care", "ADBE": "Information Technology",
    "LIN": "Materials", "CSCO": "Information Technology",
    "ACN": "Information Technology", "MCD": "Consumer Discretionary",
    "ABT": "Health Care", "CRM": "Information Technology",
    "WFC": "Financials", "IBM": "Information Technology",
    "GE": "Industrials", "DIS": "Communication Services",
    "TXN": "Information Technology", "VZ": "Communication Services",
    "INTU": "Information Technology", "AMGN": "Health Care",
    "CAT": "Industrials", "QCOM": "Information Technology",
    "NOW": "Information Technology", "PFIZ": "Health Care",
    "PM": "Consumer Staples", "UNP": "Industrials", "SPGI": "Financials",
    "GS": "Financials", "RTX": "Industrials",
    "LOW": "Consumer Discretionary", "HON": "Industrials",
    "BKNG": "Consumer Discretionary", "NEE": "Utilities",
    "T": "Communication Services", "AXP": "Financials", "BLK": "Financials",
    "SYK": "Health Care", "ELV": "Health Care",
    "TJX": "Consumer Discretionary", "VRTX": "Health Care",
    "C": "Financials", "MDT": "Health Care", "BSX": "Health Care",
    "ADP": "Industrials", "MMC": "Financials", "PLD": "Real Estate",
    "CB": "Financials", "LMT": "Industrials",
    "SBUX": "Consumer Discretionary", "MDLZ": "Consumer Staples",
    "AMT": "Real Estate", "ETN": "Industrials", "CI": "Health Care",
    "SO": "Utilities", "DE": "Industrials", "MO": "Consumer Staples",
    "BMY": "Health Care", "DUK": "Utilities",
    "ADI": "Information Technology", "CVS": "Health Care",
    "GILD": "Health Care", "APD": "Materials", "CL": "Consumer Staples",
    "SCHW": "Financials", "ZTS": "Health Care", "ITW": "Industrials",
    "MU": "Information Technology", "FDX": "Industrials",
    "CME": "Financials", "GD": "Industrials", "EOG": "Energy",
    "NSC": "Industrials", "SLB": "Energy", "PYPL": "Financials",
}
