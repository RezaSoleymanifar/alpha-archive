"""Ground-truth fixtures for the meta-learning loop.

Each fixture = a well-known paper with documented expected outcome based on
published replications + literature consensus. Pipeline runs against these
fixtures continuously; precision/recall/F1 of pipeline vs ground-truth is
the platform-quality metric.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Fixture:
    fixture_id: str
    title: str
    authors: str
    year: int
    paper_url: str

    # Ground truth from literature
    expected_verdict: str          # ship | iterate | kill
    expected_signal_sign: str      # +, -, both
    expected_signal_type: str      # cross_sectional_equity, time_series, etc.
    expected_universe: str         # sp500, russell1000, all_us
    expected_horizon_days: int

    # Performance expectations (ranges from published replications)
    expected_ic_min: float
    expected_sharpe_post_costs: tuple[float, float]      # (low, high)
    expected_oos_decay_pct: tuple[float, float]          # (low, high) decay pct post-pub

    # Replication notes
    canonical_formula: str
    ground_truth_sources: list[str]
    notes: str = ""

    # Hand-coded reference implementation (golden, what code-gen should produce)
    reference_module: Optional[str] = None  # e.g., "alpha_archive.fixtures_impl.momentum_jt1993"


FIXTURES: list[Fixture] = [
    Fixture(
        fixture_id="momentum_jt1993",
        title="Returns to Buying Winners and Selling Losers: Implications for Stock Market Efficiency",
        authors="Jegadeesh, Titman",
        year=1993,
        paper_url="https://onlinelibrary.wiley.com/doi/abs/10.1111/j.1540-6261.1993.tb04702.x",
        expected_verdict="ship",
        expected_signal_sign="+",
        expected_signal_type="cross_sectional_equity",
        expected_universe="sp500",
        expected_horizon_days=21,
        expected_ic_min=0.02,
        expected_sharpe_post_costs=(0.4, 0.9),
        expected_oos_decay_pct=(0.30, 0.60),
        canonical_formula="rank cross-section by return(t-252, t-21); long top decile, short bottom decile; rebalance monthly",
        ground_truth_sources=[
            "Asness 2014 (replication on global universe)",
            "Hou-Xue-Zhang 2018 (factor zoo replication)",
            "AQR 2014 internal replication notes",
            "McLean & Pontiff 2016 (post-publication decay)",
        ],
        notes="Canonical cross-sectional momentum. Survives in 95%+ of replication studies. Strong signal in trending regimes; suffers in mean-reverting (e.g., 2009 momentum crash, March 2020).",
        reference_module="alpha_archive.fixtures_impl.momentum_jt1993",
    ),
    Fixture(
        fixture_id="value_fama_french_1992",
        title="The Cross-Section of Expected Stock Returns",
        authors="Fama, French",
        year=1992,
        paper_url="https://onlinelibrary.wiley.com/doi/abs/10.1111/j.1540-6261.1992.tb04398.x",
        expected_verdict="ship",
        expected_signal_sign="+",
        expected_signal_type="cross_sectional_equity",
        expected_universe="sp500",
        expected_horizon_days=21,
        expected_ic_min=0.015,
        expected_sharpe_post_costs=(0.3, 0.7),
        expected_oos_decay_pct=(0.40, 0.70),
        canonical_formula="rank cross-section by book-to-market (B/M); long top tercile, short bottom tercile",
        ground_truth_sources=[
            "Fama-French 1993 (FF3 model paper)",
            "Asness-Frazzini 2013 (Devil in HML's Details)",
            "Bali-Engle-Murray 2016 (Empirical Asset Pricing textbook)",
        ],
        notes="HML factor. Decay heavy post-2010, debate about whether dead. Use proxies if B/M unavailable: P/B, P/E.",
    ),
    Fixture(
        fixture_id="bab_frazzini_pedersen_2014",
        title="Betting Against Beta",
        authors="Frazzini, Pedersen",
        year=2014,
        paper_url="https://www.aqr.com/Insights/Research/Journal-Article/Betting-Against-Beta",
        expected_verdict="ship",
        expected_signal_sign="-",  # short high-beta, long low-beta
        expected_signal_type="cross_sectional_equity",
        expected_universe="sp500",
        expected_horizon_days=21,
        expected_ic_min=0.02,
        expected_sharpe_post_costs=(0.5, 1.2),
        expected_oos_decay_pct=(0.20, 0.40),
        canonical_formula="rank by 5yr rolling beta to market; long-short of low-vs-high beta, leveraged to unit beta",
        ground_truth_sources=[
            "AQR 2014 paper",
            "Asness-Frazzini-Pedersen 2018 update",
        ],
        notes="Robust across asset classes. Survives most replication checks.",
    ),
    Fixture(
        fixture_id="quality_qmj_2019",
        title="Quality Minus Junk",
        authors="Asness, Frazzini, Pedersen",
        year=2019,
        paper_url="https://www.aqr.com/Insights/Research/Journal-Article/Quality-Minus-Junk",
        expected_verdict="ship",
        expected_signal_sign="+",
        expected_signal_type="cross_sectional_equity",
        expected_universe="sp500",
        expected_horizon_days=21,
        expected_ic_min=0.02,
        expected_sharpe_post_costs=(0.4, 0.9),
        expected_oos_decay_pct=(0.20, 0.40),
        canonical_formula="composite of profitability + growth + safety + payout; long top, short bottom",
        ground_truth_sources=[
            "AQR 2019 paper",
            "Novy-Marx 2013 (gross profitability)",
        ],
        notes="Composite signal. Multi-factor; pipeline must handle composites correctly.",
    ),
    Fixture(
        fixture_id="low_vol_baker_haugen_1991",
        title="The Volatility Effect: Lower Risk Without Lower Return",
        authors="Baker, Haugen",
        year=1991,
        paper_url="https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2055431",
        expected_verdict="ship",
        expected_signal_sign="-",  # short high-vol, long low-vol
        expected_signal_type="cross_sectional_equity",
        expected_universe="sp500",
        expected_horizon_days=21,
        expected_ic_min=0.015,
        expected_sharpe_post_costs=(0.3, 0.8),
        expected_oos_decay_pct=(0.30, 0.50),
        canonical_formula="rank by 12mo trailing realized vol; long bottom quintile, short top quintile",
        ground_truth_sources=[
            "Baker-Bradley-Wurgler 2011 (Benchmarks as Limits to Arbitrage)",
            "Frazzini-Pedersen 2014 (related to BAB)",
        ],
        notes="Strong empirical support; related to BAB but distinct (raw vol vs CAPM beta).",
    ),
    # Adversarial / negative fixtures (should be killed)
    Fixture(
        fixture_id="adversarial_random_signal",
        title="[FAKE] Random Permutations as Predictors of Returns",
        authors="N/A",
        year=2099,
        paper_url="",
        expected_verdict="kill",
        expected_signal_sign="both",
        expected_signal_type="cross_sectional_equity",
        expected_universe="sp500",
        expected_horizon_days=21,
        expected_ic_min=-0.01,
        expected_sharpe_post_costs=(-0.3, 0.3),
        expected_oos_decay_pct=(0.0, 1.0),
        canonical_formula="random.uniform(-1, 1) per stock per day",
        ground_truth_sources=["fabricated for pipeline regression test"],
        notes="Adversarial fixture: pipeline MUST kill this. Catches false positive verdicts.",
        reference_module="alpha_archive.fixtures_impl.adversarial_random",
    ),
]


def get_fixture(fid: str) -> Fixture:
    for f in FIXTURES:
        if f.fixture_id == fid:
            return f
    raise KeyError(f"unknown fixture: {fid}")


def list_fixtures() -> list[str]:
    return [f.fixture_id for f in FIXTURES]


if __name__ == "__main__":
    for f in FIXTURES:
        print(f"  {f.fixture_id:35s}  expected={f.expected_verdict:8s}  Sharpe={f.expected_sharpe_post_costs}")
