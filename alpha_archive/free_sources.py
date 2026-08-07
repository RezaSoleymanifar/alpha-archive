"""What is actually free, verified by fetching it.

A paper was rejected because it needed the alternative.me Fear and Greed Index,
which the judgement called "outside the free stack". That index is free, keyless,
and serves 3,106 daily observations back to 2018. Nobody checked. The paper sat
in the drop pile until an audit went looking.

That is not a one-off mistake, it is a predictable one: deciding whether a source
is obtainable feels like recall, so it gets answered from memory instead of from
a request. The fix is to stop asking anyone to remember.

Everything here was fetched on the date recorded, with the status code and
payload size kept. `contradictions()` reads a rejection and returns the free
sources it names as blockers, so a wrong drop is caught mechanically rather than
by somebody happening to re-read it.

    uv run python -m alpha_archive.free_sources --verify   # refetch everything
    uv run python -m alpha_archive.free_sources --audit    # scan the ledger
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass
from typing import Any

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LEDGER = os.path.join(ROOT, "data", "triage", "ledger.json")


@dataclass(frozen=True)
class Free:
    """A source that is genuinely free, and the proof it was checked."""
    name: str
    serves: str
    endpoint: str
    verified: str          # date it last returned a real payload
    note: str = ""
    pattern: str = ""      # how a rejection would refer to it

    def matches(self, text: str) -> bool:
        return bool(re.search(self.pattern or re.escape(self.name), text or "", re.I))


# Verified 2026-08-07 by fetching each one. Status and size in the note.
FREE: list[Free] = [
    Free("Crypto Fear and Greed Index",
         "daily sentiment 0-100, 3,106 observations from 2018-02",
         "https://api.alternative.me/fng/?limit=0",
         "2026-08-07", "200, no key, no rate limit",
         r"fear\s*(and|&)\s*greed|alternative\.me"),

    Free("CoinGecko",
         "historical crypto prices, market caps and volumes for thousands of coins",
         "https://api.coingecko.com/api/v3/coins/markets?vs_currency=usd",
         "2026-08-07", "200 keyless; the history endpoint rate-limits, so throttle",
         r"coingecko|coinmarketcap|crypto market cap|historical market cap"),

    Free("World Bank indicators",
         "every WDI series for every country",
         "https://api.worldbank.org/v2/country/USA/indicator/NY.GDP.MKTP.CD?format=json",
         "2026-08-07", "200, keyless", r"world bank|\bWDI\b"),

    Free("Wikipedia pageviews",
         "daily article views since 2015, a free attention proxy",
         "https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/en.wikipedia"
         "/all-access/user/Bitcoin/daily/20240101/20240107",
         "2026-08-07", "200, keyless", r"wikipedia|pageview|search volume|attention proxy"),

    Free("Yahoo international listings",
         "daily OHLCV for listed equities on most world exchanges",
         "https://query1.finance.yahoo.com/v8/finance/chart/005930.KS?range=1mo&interval=1d",
         "2026-08-07",
         "200 verified for Korea .KS, China .SS, India .NS, Turkey .IS, Spain .MC, "
         "Vietnam .VN. Also .KQ .SZ .T .HK .L .TO .AX .SA .DE .PA .MI .AS .ST .CO .HE .OL",
         r"korea|korean|\bKRX\b|chinese|china|A-share|shanghai|shenzhen|"
         r"\bBIST\b|turkish|\bIBEX\b|spanish|vietnam|\bVN30\b|indian|\bNIFTY\b|"
         r"japanese|\bTOPIX\b|hong kong|non-US (market|exchange|listing)"),
]

# The opposite list. If a rejection names one of these, it is almost certainly
# right, and an overturn needs a specific argument rather than optimism.
GENUINELY_PAID = re.compile(
    r"\bCRSP\b|\bCompustat\b|\bI/?B/?E/?S\b|Bloomberg|Refinitiv|RavenPack|"
    r"OptionMetrics|\bTAQ\b|\bWRDS\b|tick data|order book|limit order|"
    r"option chain|implied vol(atility)? surface|credit rating|analyst (estimate|consensus)|"
    r"proprietary|internal (loss|risk|PnL)",
    re.I,
)


# The rejection has to actually claim the thing is out of reach. Merely naming
# a free source is not a contradiction: most correct drops say "the prices are
# free on Yahoo, but the claim needs investor-identity flow data", and flagging
# those buries the real errors in noise. First pass fired on 14 rejections of
# which 12 were correct.
UNAVAILABLE = re.compile(
    r"outside the (free|available)|not in the free|no free source|"
    r"not (freely )?(available|obtainable|accessible|covered)|"
    r"cannot be (obtained|sourced|got|retrieved)|"
    r"(vintage|we|the stack) (does|do) not (cover|have|serve)|"
    r"unavailable|beyond the free|out of reach",
    re.I,
)

# Phrases that concede the source IS reachable. If one of these sits near the
# mention, the rejection already knew and the blocker is something else.
CONCEDED = re.compile(
    r"(are|is|were) free|free on|freely available|covered by|available (on|from|via)|"
    r"vintage (covers|serves|has)|only build|prices? (are|is) (free|on)",
    re.I,
)


def contradictions(reason: str, data_needed: list[str] | None = None) -> list[Free]:
    """Free sources this rejection treats as out of reach when they are not.

    Three conditions, all required. The rejection names a source we have
    fetched; it claims that source is unavailable; and it does not elsewhere
    concede the source is reachable. Anything less flags correct drops, and a
    check that cries wolf gets switched off.
    """
    text = (reason or "") + " " + " ".join(data_needed or [])
    if GENUINELY_PAID.search(text):
        return []
    if not UNAVAILABLE.search(text):
        return []
    if CONCEDED.search(text):
        return []
    return [f for f in FREE if f.matches(text)]


def verify(timeout: int = 30) -> int:
    """Refetch every endpoint. This is the only thing that keeps the file true."""
    import httpx

    headers = {"User-Agent": "alpha-archive (reza@soleymanifar.com)"}
    bad = 0
    for source in FREE:
        try:
            response = httpx.get(source.endpoint, headers=headers,
                                 timeout=timeout, follow_redirects=True)
            ok = response.status_code == 200
            bad += not ok
            print(f"  {response.status_code}  {len(response.content):>8,}  {source.name}")
        except Exception as exc:
            bad += 1
            print(f"  ERR {type(exc).__name__:<16} {source.name}")
    return bad


def audit() -> list[dict[str, Any]]:
    """Every rejection that names a source we can prove is free."""
    with open(LEDGER, encoding="utf-8") as fh:
        papers = json.load(fh)["papers"]

    flagged = []
    for key, entry in papers.items():
        if entry.get("verdict") != "drop":
            continue
        hits = contradictions(entry.get("reason", ""), entry.get("data_needed"))
        if hits:
            flagged.append({
                "arxiv_id": key,
                "gap": entry.get("gap"),
                "confidence": entry.get("confidence"),
                "free_sources_named": [h.name for h in hits],
                "endpoints": [h.endpoint for h in hits],
                "reason": (entry.get("reason") or "")[:300],
            })
    flagged.sort(key=lambda f: f["confidence"] or 0)
    return flagged


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--verify", action="store_true")
    ap.add_argument("--audit", action="store_true")
    args = ap.parse_args()

    if args.verify or not args.audit:
        print("refetching every source in the registry")
        bad = verify()
        print(f"\n{len(FREE) - bad} of {len(FREE)} still answering")
        if bad and not args.audit:
            raise SystemExit(1)

    if args.audit:
        flagged = audit()
        print(f"\n{len(flagged)} rejection(s) name a source that is verifiably free")
        for item in flagged:
            print(f"\n  {item['arxiv_id']}  confidence {item['confidence']}  "
                  f"[{item['gap']}]")
            print(f"    names free: {', '.join(item['free_sources_named'])}")
            print(f"    said: {item['reason'][:180]}")
        out = os.path.join(ROOT, "data", "triage", "_free_source_conflicts.json")
        with open(out, "w", encoding="utf-8", newline="\n") as fh:
            json.dump(flagged, fh, indent=1)
        print(f"\nwrote {out}")


if __name__ == "__main__":
    main()
