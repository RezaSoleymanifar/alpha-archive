"""Audit Sharadar coverage on a hand-curated sample of recent (2020-2025)
popular quant finance papers from the empirical asset pricing canon.

Source venues: SSRN-FEN top papers, NBER WP, Journal of Finance, Review of
Financial Studies, Journal of Financial Economics, Critical Finance Review.

Each entry records the paper's *core* data requirements (the irreducible
inputs the methodology depends on), independent of nice-to-haves.
"""
from __future__ import annotations


PAPERS = [
    # === Pure US-equity factor / anomaly papers, Sharadar's sweet spot ===
    {
        "id": "gu_kelly_xiu_2020",
        "title": "Empirical Asset Pricing via Machine Learning",
        "authors": "Gu, Kelly, Xiu",
        "venue": "RFS 2020",
        "data": ["us_equity_returns", "compustat_94_chars", "macro_predictors"],
        "needs": ["pit_fundamentals", "delistings", "long_history_1957"],
    },
    {
        "id": "kelly_pruitt_su_2024",
        "title": "Complexity Everywhere",
        "authors": "Kelly, Pruitt, Su",
        "venue": "RFS forthcoming",
        "data": ["us_equity_returns", "compustat_features"],
        "needs": ["pit_fundamentals", "long_history"],
    },
    {
        "id": "bryzgalova_pelger_zhu_2023",
        "title": "Forest Through the Trees: Building Cross-Sections of Stock Returns",
        "authors": "Bryzgalova, Pelger, Zhu",
        "venue": "JF 2024",
        "data": ["us_equity_returns", "compustat_anomaly_chars"],
        "needs": ["pit_fundamentals", "delistings"],
    },
    {
        "id": "stambaugh_yu_yuan_2024",
        "title": "Mispricing Factors (updated)",
        "authors": "Stambaugh, Yu, Yuan",
        "venue": "RFS 2024 update",
        "data": ["us_equity_returns", "11_anomaly_chars"],
        "needs": ["pit_fundamentals"],
    },
    {
        "id": "chen_zimmermann_2022",
        "title": "Open Source Cross-Section of Stock Returns",
        "authors": "Chen, Zimmermann",
        "venue": "Critical Finance Review 2022",
        "data": ["us_equity_returns", "compustat_209_predictors"],
        "needs": ["pit_fundamentals", "delistings", "long_history"],
    },
    {
        "id": "novy_marx_2013",
        "title": "Other Side of Value: Gross Profitability",
        "authors": "Novy-Marx",
        "venue": "JFE 2013 (still cited as base case)",
        "data": ["us_equity_returns", "gross_profit", "total_assets"],
        "needs": ["pit_fundamentals"],
    },
    {
        "id": "frazzini_pedersen_2014",
        "title": "Betting Against Beta",
        "authors": "Frazzini, Pedersen",
        "venue": "JFE 2014 (evergreen)",
        "data": ["us_equity_returns", "market_returns"],
        "needs": ["delistings", "long_history"],
    },
    {
        "id": "hou_xue_zhang_2018",
        "title": "Replicating Anomalies",
        "authors": "Hou, Xue, Zhang",
        "venue": "RFS 2020",
        "data": ["us_equity_returns", "compustat_452_anomaly_chars"],
        "needs": ["pit_fundamentals", "delistings", "long_history_1967"],
    },
    {
        "id": "asness_frazzini_pedersen_2019_quality",
        "title": "Quality Minus Junk",
        "authors": "Asness, Frazzini, Pedersen",
        "venue": "RAS 2019 (evergreen)",
        "data": ["us_equity_returns", "compustat_quality_chars"],
        "needs": ["pit_fundamentals", "international_optional"],
    },

    # === ML / NLP on financial text, Sharadar partial / blocked ===
    {
        "id": "cong_tang_wang_2024",
        "title": "AlphaPortfolio: Direct Construction Through DRL",
        "authors": "Cong, Tang, Wang",
        "venue": "JF 2024",
        "data": ["us_equity_returns", "compustat_features", "lstm_sequences"],
        "needs": ["pit_fundamentals", "long_history"],
    },
    {
        "id": "ke_kelly_xiu_2024_textual",
        "title": "Predicting Returns with Text Data",
        "authors": "Ke, Kelly, Xiu",
        "venue": "RFS 2024",
        "data": ["us_equity_returns", "news_text_corpus"],
        "needs": ["news_data_blocked"],
    },
    {
        "id": "lopez_lira_2024_chatgpt",
        "title": "Can ChatGPT Forecast Stock Price Movements?",
        "authors": "Lopez-Lira, Tang",
        "venue": "WP 2023, viral",
        "data": ["us_equity_returns", "news_headlines", "llm_sentiment"],
        "needs": ["news_data_blocked"],
    },

    # === Multi-asset / international / derivatives, Sharadar blocked ===
    {
        "id": "asness_moskowitz_pedersen_2013",
        "title": "Value and Momentum Everywhere",
        "authors": "Asness, Moskowitz, Pedersen",
        "venue": "JF 2013 (canonical multi-asset)",
        "data": ["international_equity", "bonds", "currencies", "commodities"],
        "needs": ["non_us_universe"],
    },
    {
        "id": "moreira_muir_2017_vol_managed",
        "title": "Volatility-Managed Portfolios",
        "authors": "Moreira, Muir",
        "venue": "JF 2017",
        "data": ["us_equity_returns", "factor_returns_kf", "realized_vol"],
        "needs": ["long_history"],
    },
    {
        "id": "bali_2011_max",
        "title": "Maxing Out: Stocks as Lotteries",
        "authors": "Bali, Cakici, Whitelaw",
        "venue": "JFE 2011 (still replicated)",
        "data": ["us_equity_returns", "daily_max_return"],
        "needs": ["daily_prices"],
    },
    {
        "id": "asness_carry_2024",
        "title": "Carry (multi-asset, updated)",
        "authors": "Asness, Moskowitz, Pedersen, et al",
        "venue": "WP / book",
        "data": ["bonds", "currencies", "commodities", "international_equity"],
        "needs": ["non_us_universe", "non_equity_assets"],
    },
    {
        "id": "garleanu_pedersen_2024",
        "title": "Active vs Passive Investing",
        "authors": "Garleanu, Pedersen",
        "venue": "JF 2024",
        "data": ["mutual_fund_flows", "etf_holdings", "us_equity_returns"],
        "needs": ["fund_flow_data_blocked"],
    },

    # === Alternative data / behavioral, Sharadar blocked ===
    {
        "id": "da_engelberg_gao_2011",
        "title": "In Search of Attention",
        "authors": "Da, Engelberg, Gao",
        "venue": "JF 2011 (still canonical)",
        "data": ["us_equity_returns", "google_search_volume"],
        "needs": ["alt_data_blocked"],
    },
    {
        "id": "edmans_2011_satisfaction",
        "title": "Does Stock Market Fully Value Intangibles? Employee Satisfaction",
        "authors": "Edmans",
        "venue": "JFE 2011",
        "data": ["us_equity_returns", "100_best_companies_list"],
        "needs": ["alt_data_blocked"],
    },
    {
        "id": "cohen_lou_malloy_2020",
        "title": "Lazy Prices",
        "authors": "Cohen, Lou, Malloy",
        "venue": "JF 2020",
        "data": ["us_equity_returns", "10k_text_changes"],
        "needs": ["filings_nlp_blocked"],
    },

    # === Options / IV, Sharadar blocked ===
    {
        "id": "an_ang_bali_cakici_2014",
        "title": "Joint Cross Section of Stocks and Options",
        "authors": "An, Ang, Bali, Cakici",
        "venue": "JF 2014",
        "data": ["us_equity_returns", "options_implied_vol"],
        "needs": ["options_data_blocked"],
    },
    {
        "id": "muravyev_2016",
        "title": "Order Flow and Expected Option Returns",
        "authors": "Muravyev",
        "venue": "JF 2016",
        "data": ["options_chain", "options_order_flow"],
        "needs": ["options_microstructure_blocked"],
    },

    # === Microstructure / HFT, Sharadar blocked ===
    {
        "id": "kyle_obizhaeva_2016",
        "title": "Market Microstructure Invariance",
        "authors": "Kyle, Obizhaeva",
        "venue": "Econometrica 2016",
        "data": ["intraday_trades", "limit_order_book"],
        "needs": ["taq_blocked"],
    },
]


COVERAGE = {
    # COVERED by Sharadar Core US + SEP + ACTIONS + DAILY + TICKERS
    "us_equity_returns": "covered",
    "us_equity_prices": "covered",
    "daily_prices": "covered",
    "market_returns": "covered",
    "compustat_94_chars": "covered",  # ~80 of 94 in Sharadar; close enough
    "compustat_features": "covered",
    "compustat_anomaly_chars": "covered",
    "compustat_209_predictors": "covered",  # ~150 line items, ~80% overlap
    "compustat_452_anomaly_chars": "partial",  # ~70% overlap
    "compustat_quality_chars": "covered",
    "11_anomaly_chars": "covered",
    "gross_profit": "covered",
    "total_assets": "covered",
    "pit_fundamentals": "covered",
    "delistings": "covered",
    "long_history_1957": "partial",  # Sharadar starts ~1999
    "long_history_1967": "partial",  # same
    "long_history": "partial",  # same
    "daily_max_return": "covered",
    "lstm_sequences": "covered",  # derivable from price panel
    "factor_returns_kf": "covered",  # supplement Ken French free
    "realized_vol": "covered",
    "international_optional": "covered",  # paper works on US only too

    # NOT COVERED by Sharadar (need other data source)
    "news_text_corpus": "not_covered",
    "news_headlines": "not_covered",
    "news_data_blocked": "not_covered",
    "llm_sentiment": "not_covered",
    "international_equity": "not_covered",
    "bonds": "not_covered",
    "currencies": "not_covered",
    "commodities": "not_covered",
    "non_us_universe": "not_covered",
    "non_equity_assets": "not_covered",
    "mutual_fund_flows": "not_covered",
    "etf_holdings": "not_covered",
    "fund_flow_data_blocked": "not_covered",
    "google_search_volume": "not_covered",
    "100_best_companies_list": "not_covered",
    "alt_data_blocked": "not_covered",
    "10k_text_changes": "not_covered",
    "filings_nlp_blocked": "not_covered",
    "options_implied_vol": "not_covered",
    "options_chain": "not_covered",
    "options_order_flow": "not_covered",
    "options_data_blocked": "not_covered",
    "options_microstructure_blocked": "not_covered",
    "intraday_trades": "not_covered",
    "limit_order_book": "not_covered",
    "taq_blocked": "not_covered",
}


def score(paper: dict) -> tuple[str, list[tuple[str, str]]]:
    fields = paper["data"] + paper["needs"]
    cls = [(f, COVERAGE.get(f, "unknown")) for f in fields]
    classes = [c for _, c in cls]
    if any(c == "not_covered" for c in classes):
        return "blocked", cls
    if all(c == "covered" for c in classes):
        return "full", cls
    return "partial", cls


def main() -> None:
    print("== Sharadar coverage on hand-curated popular qfin papers ==")
    print(f"Sample: {len(PAPERS)} papers from RFS / JF / JFE / NBER / SSRN-FEN")
    print()

    bucket_counts = {"full": 0, "partial": 0, "blocked": 0, "unknown": 0}
    by_paper = []
    for p in PAPERS:
        v, cls = score(p)
        bucket_counts[v] += 1
        by_paper.append((p, v, cls))

    print("Verdict rollup")
    print("-" * 50)
    for v in ("full", "partial", "blocked", "unknown"):
        n = bucket_counts[v]
        pct = 100 * n / len(PAPERS)
        bar = "#" * int(pct / 4)
        print(f"  {v:>8}: {n:>3} ({pct:>5.1f}%) {bar}")
    print()

    # Slice by paper category for sharper read
    print("Slice by paper category")
    print("-" * 50)
    cat_buckets: dict[str, dict[str, int]] = {}
    for p, v, _ in by_paper:
        # crude category heuristic
        if "options" in p["id"] or "muravyev" in p["id"]:
            cat = "options/derivatives"
        elif "kyle" in p["id"]:
            cat = "microstructure/HFT"
        elif "asness_carry" in p["id"] or "asness_moskowitz_pedersen_2013" in p["id"]:
            cat = "multi-asset/international"
        elif "garleanu_pedersen_2024" in p["id"]:
            cat = "fund-flows/holdings"
        elif "ke_kelly_xiu_2024" in p["id"] or "lopez_lira" in p["id"] or "cohen_lou" in p["id"] or "da_engelberg" in p["id"] or "edmans" in p["id"]:
            cat = "alt-data/text/NLP"
        else:
            cat = "US equity factor (Sharadar sweet spot)"
        d = cat_buckets.setdefault(cat, {"full": 0, "partial": 0, "blocked": 0})
        d[v] = d.get(v, 0) + 1

    for cat, counts in cat_buckets.items():
        total = sum(counts.values())
        full_pct = 100 * counts.get("full", 0) / total
        part_pct = 100 * counts.get("partial", 0) / total
        block_pct = 100 * counts.get("blocked", 0) / total
        print(f"  {cat:<40} n={total}  FULL={full_pct:>4.0f}%  PART={part_pct:>4.0f}%  BLOK={block_pct:>4.0f}%")
    print()

    print("Per-paper detail")
    print("=" * 80)
    for p, v, cls in sorted(by_paper, key=lambda x: (x[1] != "full", x[1] != "partial", x[0]["id"])):
        sym = {"full": "[FULL]", "partial": "[PART]", "blocked": "[BLOK]", "unknown": "[??? ]"}[v]
        print(f"{sym} {p['id']}  ({p['venue']})")
        print(f"       {p['title'][:75]}")
        for tok, c in cls:
            mark = {"covered": "+", "partial": "~", "not_covered": "-", "unknown": "?"}[c]
            print(f"       {mark} {tok}  [{c}]")
        print()


if __name__ == "__main__":
    main()
