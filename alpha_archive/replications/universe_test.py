"""Does universe size explain our 0.74 correlation with UMD, or is our code wrong?

Ours is an 8-long / 8-short book drawn from 80 mega-caps. French's UMD is a
size-and-momentum double sort over every NYSE, AMEX and NASDAQ name with NYSE
breakpoints. Those are different portfolios, so some gap is structural.

The question is which kind of gap it is:

  correlation rises with universe size  -> the ceiling was the universe, code fine
  correlation stays flat                -> our construction is wrong, fix that first

Tickers come from the SEC's own exchange file rather than a hand-typed list,
because a hand-picked universe is itself a judgement call and this test is
about removing judgement calls.

    uv run python -m alpha_archive.replications.universe_test
"""

from __future__ import annotations

import asyncio
import json
import os
import random
from datetime import datetime, timezone

import pandas as pd

from vintage.http import get_json
from vintage.sources import french

from .jt1993 import COST_BPS, long_short_monthly, momentum_12_1, price_panel, umd_monthly

SEC_TICKERS = "https://www.sec.gov/files/company_tickers_exchange.json"
SIZES = [80, 160, 320, 640]
SEED = 11
MIN_HISTORY = 3000          # trading days; drops recent listings that cannot rank


async def candidate_tickers(n: int) -> list[str]:
    """A seeded sample of currently-listed NYSE/NASDAQ names, from the SEC."""
    payload = await get_json(SEC_TICKERS, tier="monthly")
    fields = payload["fields"]
    ti, xi = fields.index("ticker"), fields.index("exchange")

    tickers = sorted({
        row[ti].strip().upper()
        for row in payload["data"]
        if row[xi] in ("NYSE", "Nasdaq") and row[ti]
        and row[ti].isalpha() and len(row[ti]) <= 4      # skip units, warrants, preferreds
    })
    random.Random(SEED).shuffle(tickers)
    return tickers[:n]


async def main() -> None:
    print("Universe-size test — is 0.74 our code, or our universe?\n")

    from .jt1993 import UNIVERSE as MEGA
    wanted = max(SIZES)
    pool = await candidate_tickers(wanted * 2)
    # Keep the original 80 as the smallest rung so the comparison is nested.
    pool = MEGA + [t for t in pool if t not in MEGA]

    print(f"  fetching prices for up to {wanted} names (this is the slow part)")
    prices = await price_panel(pool[:wanted])

    deep = prices.columns[prices.notna().sum() >= MIN_HISTORY]
    prices = prices[deep]
    print(f"  {len(deep)} names have >= {MIN_HISTORY} sessions of history\n")

    umd = await umd_monthly()
    signal = momentum_12_1(prices)

    rows = []
    for size in SIZES:
        cols = [c for c in prices.columns if c in MEGA][:size]
        cols += [c for c in prices.columns if c not in cols][: size - len(cols)]
        if len(cols) < size * 0.6:
            print(f"  skipping {size}: only {len(cols)} names available")
            continue

        ours = long_short_monthly(prices[cols], signal[cols])
        joined = pd.concat([ours.rename("o"), umd.rename("u")], axis=1, sort=True).dropna()
        corr = float(joined["o"].corr(joined["u"]))
        rows.append({
            "universe": len(cols),
            "correlation": round(corr, 4),
            "months": int(len(joined)),
            "mean_monthly_pct": round(float(ours.mean() * 100), 4),
            "legs": max(1, int(round(len(cols) * 0.10))),
        })
        print(f"  {len(cols):>4} names -> corr {corr:+.3f}   "
              f"({rows[-1]['legs']} per leg, mean {rows[-1]['mean_monthly_pct']:+.3f}%/mo)")

    verdict = _verdict(rows)
    print(f"\n  VERDICT: {verdict}")

    out = os.path.join("data", "replications", "universe_test.json")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8") as fh:
        json.dump({
            "test": "universe_size_vs_umd_correlation",
            "cost_bps": COST_BPS,
            "rungs": rows,
            "verdict": verdict,
            "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        }, fh, indent=2)
    print(f"  wrote {out}")


def _verdict(rows: list[dict]) -> str:
    if len(rows) < 2:
        return "not enough rungs to say"
    lift = rows[-1]["correlation"] - rows[0]["correlation"]
    if lift >= 0.08:
        return (f"universe was the ceiling — correlation rose {lift:+.3f} from "
                f"{rows[0]['universe']} to {rows[-1]['universe']} names. The construction "
                "is sound; the original 0.74 was a breadth limit, not a bug.")
    if lift <= -0.03:
        return (f"correlation fell {lift:+.3f} as the universe grew. Broader names are "
                "noisier here — worth checking liquidity filtering before trusting either.")
    return (f"correlation barely moved ({lift:+.3f}). Universe size is not the binding "
            "constraint, so the remaining gap is construction: French double-sorts on size "
            "and value-weights with NYSE breakpoints, and we do neither.")


if __name__ == "__main__":
    asyncio.run(main())
