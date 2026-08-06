"""Map the quant finance universe and score coverage with our current stack.

Stack assumed:
- Sharadar Core US Fundamentals + SEP + ACTIONS + DAILY + TICKERS ($300/mo)
- Ken French data library (free), factor returns
- HXZ q-factor library (free), factor returns
- FRED (free): macro time series
- OpenAP CrossSection (free): 326 anomaly return series
- grain (current): daily prices for ~3000 US tickers, 2011+
- yfinance fallback (free): daily prices, basic snapshot fundamentals

Score per cell: full / partial / blocked / na
Weight each cell by approximate share of academic qfin paper output (rough,
based on SSRN-FEN ejournal volume + JF/RFS/JFE/JFQA category breakdown).
"""
from __future__ import annotations

# (asset_class, style, horizon) -> (coverage, paper_volume_share_pct, notes)
UNIVERSE = [
    # === US equity cross-sectional factor research (largest bucket) ===
    ("us_equity",       "cross_sectional_factor",      "monthly",       "full",    18, "HXZ/FF/Novy-Marx/Stambaugh/AQR style. Sharadar PIT fundamentals + delistings = full coverage."),
    ("us_equity",       "ml_on_chars",                  "monthly",       "full",     5, "Gu-Kelly-Xiu, Kelly-Pruitt-Su, Bryzgalova-Pelger-Zhu. Same data as factor research."),
    ("us_equity",       "behavioral_attention",         "weekly_event",  "blocked",  3, "Google trends, news flow, social sentiment, none in Sharadar."),
    ("us_equity",       "post_earnings_drift",          "event_to_60d",  "partial",  3, "Announcement dates in Sharadar; surprise needs IBES analyst consensus (blocked)."),
    ("us_equity",       "insider_following",            "event_to_30d",  "blocked",  2, "Form 4 raw filings, not in Sharadar."),
    ("us_equity",       "merger_arbitrage",             "deal_window",   "blocked",  2, "Need standardized M&A deal database (SDC Platinum, Refinitiv)."),
    ("us_equity",       "ipo_seasoning",                "event_to_24m",  "partial",  1, "IPO dates inferable from first-trade in Sharadar; underwriter info missing."),
    ("us_equity",       "stat_arb_pairs",               "daily_weekly",  "full",     2, "Cointegration / pairs only needs prices."),
    ("us_equity",       "text_nlp_filings",             "quarterly",     "blocked",  2, "Lazy Prices / 10-K diffing, needs SEC EDGAR scrape (free) but not pre-processed."),
    ("us_equity",       "text_nlp_news",                "daily_event",   "blocked",  3, "Lopez-Lira ChatGPT, Ke-Kelly-Xiu, need news corpus (RavenPack/Refinitiv)."),
    ("us_equity",       "alt_data",                     "weekly",        "blocked",  2, "Satellite, credit card, web traffic, geolocation, vendor-specific, expensive."),
    ("us_equity",       "esg_factors",                  "monthly",       "blocked",  2, "MSCI/Sustainalytics ESG ratings, paid."),
    ("us_equity",       "options_implied",              "daily",         "blocked",  3, "Implied vol surfaces, skew, term, need OptionMetrics (~$5K+/yr)."),
    ("us_equity",       "microstructure_hft",           "intraday_tick", "blocked",  3, "TAQ ($$$$), no intraday in Sharadar."),

    # === International equities ===
    ("intl_equity",     "cross_sectional_factor",      "monthly",       "blocked",  4, "Need Compustat Global / FactSet / equivalent international panel."),
    ("intl_equity",     "country_rotation",             "monthly",       "partial",  2, "Country index ETFs via yfinance free; quality variable."),
    ("emerging_equity", "cross_sectional_factor",       "monthly",       "blocked",  2, "EM data is even harder."),

    # === Fixed income ===
    ("us_treasuries",   "carry_curve",                  "monthly",       "partial",  2, "FRED has yields free; no individual bond returns / TRACE."),
    ("us_corp_bonds",   "credit_factor",                "monthly",       "blocked",  2, "TRACE / Bloomberg, paid."),
    ("us_corp_bonds",   "credit_anomalies",             "monthly",       "blocked",  1, "Same blocker."),
    ("global_rates",    "macro_carry",                  "monthly",       "blocked",  1, "Bloomberg / Refinitiv."),

    # === FX ===
    ("fx_majors",       "carry",                        "weekly_monthly","blocked",  3, "Need spot + forward + interest rates panel, Bloomberg/Refinitiv."),
    ("fx_majors",       "momentum_trend",               "weekly",        "blocked",  2, "Same."),
    ("fx_emerging",     "carry",                        "monthly",       "blocked",  1, "Same plus harder."),

    # === Commodities ===
    ("commodities",     "trend_following",              "weekly",        "blocked",  2, "Need futures panel (CSI Data, Bloomberg, Quandl wiki, partial free)."),
    ("commodities",     "carry_term_structure",         "monthly",       "blocked",  2, "Same."),
    ("commodities",     "seasonality",                  "annual",        "blocked",  1, "Same."),

    # === Derivatives ===
    ("equity_options",  "vol_arb",                      "daily",         "blocked",  3, "OptionMetrics or live-IV-feed required."),
    ("equity_options",  "dispersion",                   "monthly",       "blocked",  1, "Same."),
    ("vix_products",    "volatility_carry",             "weekly",        "blocked",  1, "VIX futures + ETPs, partial via grain/yfinance, not enough for systematic."),
    ("rate_swaps",      "swaption_vol",                 "monthly",       "blocked",  1, "Bloomberg only."),
    ("credit_cds",      "spread_anomalies",             "monthly",       "blocked",  1, "Markit / Bloomberg."),

    # === Crypto ===
    ("crypto_spot",     "cross_sectional_factor",       "daily",         "blocked",  2, "CoinGecko/CCData free APIs, not in our stack."),
    ("crypto_perps",    "funding_basis",                "hourly_daily",  "blocked",  2, "Exchange APIs / Coinalyze / Glassnode."),
    ("crypto_onchain",  "tvl_yield_factor",             "daily",         "blocked",  1, "Glassnode / Dune / The Graph."),
    ("crypto_defi",     "yield_farming",                "hourly",        "blocked",  1, "Defillama / on-chain reads."),

    # === Microstructure & HFT ===
    ("us_equity",       "limit_order_book",             "millisecond",   "blocked",  2, "Cannot do without LOBSTER / NASDAQ ITCH / TAQ."),
    ("us_equity",       "execution_modeling",           "intraday",      "blocked",  1, "Need TAQ + own broker fills."),

    # === Multi-asset ===
    ("multi_asset",     "risk_parity",                  "monthly",       "blocked",  2, "Need bond + commodity + FX returns alongside equity."),
    ("multi_asset",     "carry_global",                 "monthly",       "blocked",  2, "Asness Carry, multi-asset by construction."),
    ("multi_asset",     "trend_csv",                    "weekly_monthly","blocked",  2, "Same; need futures panel."),

    # === Behavioral / sentiment / experimental ===
    ("us_equity",       "sentiment_index",              "weekly",        "partial",  1, "Baker-Wurgler index public; per-stock sentiment blocked."),
    ("us_equity",       "regulatory_event",             "event",         "partial",  1, "SEC actions free-text; needs scrape + parse."),

    # === Methodology-only papers (no specific data needed) ===
    ("methodology",     "portfolio_optimization",       "any",           "full",     6, "HRP, Black-Litterman, robust opt, RL allocation. Pure code, runs on any returns panel, your portfolio-management repo handles this."),
    ("methodology",     "risk_estimation",              "any",           "full",     2, "Covariance shrinkage, factor models, pure methodology."),
    ("methodology",     "backtesting_framework",        "na",            "full",     1, "CV, DSR, CPCV, pure code."),
    ("methodology",     "asset_pricing_theory",         "na",            "na",       3, "Pure math; no replication possible/needed."),
    ("methodology",     "derivatives_pricing",          "na",            "na",       2, "Stochastic calculus / Monte Carlo. No empirical data needed."),
]


def main() -> None:
    print("=" * 90)
    print("QUANT FINANCE UNIVERSE, coverage with our stack")
    print("(Sharadar Core US + Ken French + HXZ q-factors + FRED + OpenAP + grain + yfinance)")
    print("=" * 90)

    # Headline rollup by coverage status, weighted by paper volume share
    bucket_pct: dict[str, float] = {"full": 0, "partial": 0, "blocked": 0, "na": 0}
    bucket_n: dict[str, int] = {"full": 0, "partial": 0, "blocked": 0, "na": 0}
    for asset, style, horizon, cov, vol, _ in UNIVERSE:
        bucket_pct[cov] += vol
        bucket_n[cov] += 1
    total_pct = sum(bucket_pct.values())

    print()
    print(f"Universe size: {len(UNIVERSE)} cells, {total_pct}% total share (rounded approx)")
    print()
    print("Coverage rollup, weighted by paper-volume share")
    print("-" * 70)
    for v in ("full", "partial", "blocked", "na"):
        n = bucket_n[v]
        share = bucket_pct[v]
        bar = "#" * int(share / 2)
        label = {"full": "FULL  (replicate end-to-end)",
                 "partial": "PART  (paper supports + partial methodology)",
                 "blocked": "BLOK  (need extra data subscription)",
                 "na":      "n/a   (theory / pure-method, no replication needed)"}[v]
        print(f"  {label:<48}  cells={n:>2}  share={share:>4}%  {bar}")
    print()

    addressable = bucket_pct["full"] + bucket_pct["partial"] + bucket_pct["na"]
    print(f"Addressable share of academic qfin output: ~{addressable}%")
    print(f"Blocked (needs extra data): ~{bucket_pct['blocked']}%")
    print()

    # Slice by asset class
    print("Slice by asset class")
    print("-" * 90)
    by_asset: dict[str, dict[str, float]] = {}
    for asset, _, _, cov, vol, _ in UNIVERSE:
        d = by_asset.setdefault(asset, {"full": 0, "partial": 0, "blocked": 0, "na": 0, "_n": 0})
        d[cov] += vol
        d["_n"] += 1
    for asset, d in sorted(by_asset.items(), key=lambda x: -(x[1]["full"] + x[1]["partial"] + x[1]["na"])):
        tot = d["full"] + d["partial"] + d["blocked"] + d["na"]
        print(f"  {asset:<20}  cells={int(d['_n']):>2}  share={int(tot):>3}%   "
              f"FULL={int(d['full']):>2}%  PART={int(d['partial']):>2}%  BLOK={int(d['blocked']):>2}%  NA={int(d['na']):>2}%")
    print()

    # Detail table
    print("Detail (sorted by coverage tier then asset)")
    print("=" * 90)
    order = {"full": 0, "partial": 1, "na": 2, "blocked": 3}
    sym_map = {"full": "[FULL]", "partial": "[PART]", "blocked": "[BLOK]", "na": "[ N/A]"}
    for asset, style, horizon, cov, vol, note in sorted(UNIVERSE, key=lambda x: (order[x[3]], x[0], x[1])):
        sym = sym_map[cov]
        print(f"  {sym} {asset:<18} | {style:<28} | {horizon:<14} | share={vol:>2}%  {note}")


if __name__ == "__main__":
    main()
