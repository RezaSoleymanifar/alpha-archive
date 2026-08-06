"""Bootstrap fixtures from Open Source Asset Pricing project (Chen + Zimmermann).

Source: https://github.com/OpenSourceAP/CrossSection (SignalDoc.csv)
License: open / academic

For each cross-sectional anomaly documented:
  - extract paper info (author, year, signal description)
  - map OpenAP's `Predictability` field to expected_verdict
  - map OpenAP's `T-Stat` to expected_sharpe range
  - map OpenAP's `Sign` to expected_signal_sign

Result: ~200 ground-truth fixtures with peer-reviewed labels, feeds the
meta-learning loop's F1 / asymmetric-loss computation.
"""
from __future__ import annotations

import csv
import json
import math
import urllib.request
from pathlib import Path

from .fixtures import Fixture, FIXTURES

OPENAP_URL = "https://raw.githubusercontent.com/OpenSourceAP/CrossSection/master/SignalDoc.csv"
CACHE_DIR = Path(__file__).resolve().parents[1] / "data" / "fixtures"
CACHE_DIR.mkdir(parents=True, exist_ok=True)
OPENAP_CACHE = CACHE_DIR / "openap_signaldoc.csv"


# Predictability label -> expected_verdict
# Per OpenAP coding scheme (1_clear, 2_likely, 3_not, 4_indep, etc.)
PREDICTABILITY_TO_VERDICT = {
    "1_clear":  "ship",     # replicates clearly in OpenAP
    "2_likely": "iterate",  # likely effect, but marginal or noisy
    "3_not":    "kill",     # doesn't replicate
    "4_indep":  "iterate",  # independent/different result vs original
    "indirect": "iterate",
    "":         "iterate",
}

# Cat.Signal -> we only fixture Predictor (real factors); Placebo also useful as adversarial
CAT_SIGNAL_KEEP = {"Predictor", "Placebo"}


def download_signaldoc(force: bool = False) -> Path:
    if OPENAP_CACHE.exists() and not force:
        return OPENAP_CACHE
    print(f"downloading {OPENAP_URL} ...")
    req = urllib.request.Request(OPENAP_URL, headers={"User-Agent": "AlphaArchive/0.1"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        OPENAP_CACHE.write_bytes(resp.read())
    return OPENAP_CACHE


def _safe_float(s: str) -> float | None:
    try:
        return float(s)
    except (TypeError, ValueError):
        return None


def _safe_int(s: str) -> int | None:
    try:
        return int(float(s))
    except (TypeError, ValueError):
        return None


def _t_stat_to_sharpe_range(t_stat: float | None,
                             n_months: int | None) -> tuple[float, float]:
    """Rough conversion: Sharpe ≈ t_stat / sqrt(N_months/12) for monthly portfolio.
    Add ±30% range for uncertainty + cost adjustment.
    """
    if t_stat is None:
        return (0.0, 0.6)
    if n_months is None or n_months < 12:
        n_months = 240  # ~20 yrs, typical OpenAP sample
    annualized_sharpe = t_stat / math.sqrt(n_months / 12)
    # post-cost decay: drop 30%
    realistic = annualized_sharpe * 0.7
    return (max(0.0, realistic - 0.3), realistic + 0.3)


def _sign_to_str(s: str) -> str:
    """OpenAP Sign field is -1, 1, or empty. Map to '+' / '-' / 'both'."""
    try:
        v = float(s)
        if v > 0:
            return "+"
        if v < 0:
            return "-"
    except (TypeError, ValueError):
        pass
    return "both"


def _row_to_fixture(row: dict) -> Fixture | None:
    acronym = (row.get("Acronym") or "").strip()
    if not acronym:
        return None

    cat_signal = (row.get("Cat.Signal") or "").strip()
    if cat_signal not in CAT_SIGNAL_KEEP:
        return None

    predict = (row.get("Predictability in OP") or "").strip()
    # Override: Placebo factors should kill regardless of original predictability
    if cat_signal == "Placebo":
        verdict = "kill"
    else:
        verdict = PREDICTABILITY_TO_VERDICT.get(predict, "iterate")

    sign = _sign_to_str(row.get("Sign", ""))
    t_stat = _safe_float(row.get("T-Stat", ""))

    sample_start = _safe_int(row.get("SampleStartYear", ""))
    sample_end = _safe_int(row.get("SampleEndYear", ""))
    n_months = (sample_end - sample_start) * 12 if sample_start and sample_end else None
    sharpe_range = _t_stat_to_sharpe_range(t_stat, n_months)

    portfolio_period = _safe_float(row.get("Portfolio Period", "")) or 1.0
    horizon_days = max(1, int(portfolio_period * 21))

    cat_form = (row.get("Cat.Form") or "").strip().lower()
    is_cross_sectional = cat_form in ("continuous", "discrete", "categorical", "")

    return Fixture(
        fixture_id=f"openap_{acronym.lower()}",
        title=f"OpenAP: {row.get('LongDescription', acronym)[:160]}",
        authors=row.get("Authors") or "",
        year=_safe_int(row.get("Year", "")) or 0,
        paper_url=f"https://www.openassetpricing.com/signals/{acronym}/",
        expected_verdict=verdict,
        expected_signal_sign=sign,
        expected_signal_type="cross_sectional_equity" if is_cross_sectional else "time_series",
        expected_universe="us_all",
        expected_horizon_days=horizon_days,
        expected_ic_min=0.005 if verdict == "kill" else 0.015,
        expected_sharpe_post_costs=sharpe_range,
        expected_oos_decay_pct=(0.20, 0.70),
        canonical_formula=(row.get("Detailed Definition") or row.get("LongDescription", ""))[:500],
        ground_truth_sources=[
            "Open Source Asset Pricing (Chen + Zimmermann)",
            f"Original: {row.get('Authors', '?')} {row.get('Year', '?')} ({row.get('Journal', '?')})",
        ],
        notes=(
            f"OpenAP cat={cat_signal}, predictability={predict}, "
            f"published_t={t_stat}, rep_quality={row.get('Signal Rep Quality', '')}"
        ),
        reference_module=None,  # auto-generated; no hand-coded reference impl
    )


def load_openap_fixtures(force_download: bool = False) -> list[Fixture]:
    """Return all fixtures parsed from OpenAP SignalDoc.csv."""
    path = download_signaldoc(force=force_download)
    fixtures = []
    with path.open(encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            fx = _row_to_fixture(row)
            if fx is not None:
                fixtures.append(fx)
    return fixtures


def install_openap_fixtures(force_download: bool = False) -> int:
    """Append OpenAP fixtures to the global FIXTURES list. Returns count added."""
    new_fixtures = load_openap_fixtures(force_download=force_download)
    existing_ids = {fx.fixture_id for fx in FIXTURES}
    added = 0
    for fx in new_fixtures:
        if fx.fixture_id not in existing_ids:
            FIXTURES.append(fx)
            added += 1
    return added


def stats() -> dict:
    """Summary of OpenAP fixtures by predictability + verdict."""
    fixtures = load_openap_fixtures()
    by_verdict = {}
    by_sign = {}
    for fx in fixtures:
        by_verdict[fx.expected_verdict] = by_verdict.get(fx.expected_verdict, 0) + 1
        by_sign[fx.expected_signal_sign] = by_sign.get(fx.expected_signal_sign, 0) + 1
    return {
        "total": len(fixtures),
        "by_verdict": by_verdict,
        "by_sign": by_sign,
    }


if __name__ == "__main__":
    s = stats()
    print(json.dumps(s, indent=2))
    print("\nfirst 5 fixtures:")
    for fx in load_openap_fixtures()[:5]:
        print(f"  {fx.fixture_id:35s}  verdict={fx.expected_verdict:8s}  sign={fx.expected_signal_sign}  Sharpe~{fx.expected_sharpe_post_costs}")
