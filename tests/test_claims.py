"""The claim verifier, checked on series whose answer is known by construction.

The failure mode that matters is a verdict of HOLDS on something that should
not hold, because that is the one that ends up on a card with a green tick.
Every case below is built so the right answer is not in doubt.
"""

from __future__ import annotations

import random

import pytest

from alpha_archive.claims import (Claim, GATES, claim_from_openap, render_table,
                                  verify)

CLAIM = Claim(paper_id="test", source="fixture", claimed_t=4.0,
              claimed_annual_return=0.10, sample_start_year=1970,
              sample_end_year=1990)


def series(seed: int, n: int, drift: float, sigma: float = 0.007) -> list[float]:
    rng = random.Random(seed)
    return [drift + rng.gauss(0, sigma) for _ in range(n)]


def test_a_persistent_edge_holds():
    verdict = verify(CLAIM, series(4, 2600, 0.0006), trials=12)
    assert verdict.status == "HOLDS"
    assert "clears every gate" in verdict.reasons[0]


def test_a_dead_signal_fails_on_the_t_statistic():
    verdict = verify(CLAIM, series(4, 2600, 0.0), trials=40)
    assert verdict.status == "FAILS"
    assert any("Newey-West t" in r for r in verdict.reasons)


def test_an_edge_confined_to_one_stretch_is_not_called_clean():
    rng = random.Random(8)
    returns = [(0.004 if i < 500 else 0.0) + rng.gauss(0, 0.007) for i in range(2600)]
    verdict = verify(CLAIM, returns, trials=6)
    assert verdict.status in {"WEAKER", "FAILS"}
    assert any("held-out path" in r for r in verdict.reasons)


def test_a_large_erosion_from_the_published_t_is_reported():
    strong_claim = Claim(paper_id="t", source="fixture", claimed_t=9.0)
    verdict = verify(strong_claim, series(4, 2600, 0.0006), trials=4)
    assert verdict.status == "WEAKER"
    assert any("falls to" in r for r in verdict.reasons)


def test_selection_across_specs_can_sink_a_result():
    """Every spec is a period-specific fit, so choosing between them is noise."""
    rng = random.Random(2)
    n, cfgs = 1200, 6
    span = n // cfgs
    competing = {}
    for c in range(cfgs):
        competing[f"spec{c}"] = {
            f"d{i:05d}": (0.05 if i // span == c else 0.0) + rng.gauss(0, 0.01)
            for i in range(n)
        }
    chosen = list(competing["spec0"].values())
    verdict = verify(CLAIM, chosen, trials=cfgs, competing_series=competing)
    assert verdict.detail["probability_of_backtest_overfitting"]["pbo"] >= 0.5
    assert verdict.status == "FAILS"
    assert any("PBO" in r for r in verdict.reasons)


def test_too_short_a_series_is_refused_rather_than_judged():
    verdict = verify(CLAIM, series(1, 30, 0.001), trials=3)
    assert verdict.status == "INSUFFICIENT"
    assert verdict.table == []


def test_nan_returns_are_dropped_not_counted():
    values = series(5, 300, 0.0005) + [float("nan")] * 50
    verdict = verify(CLAIM, values, trials=2)
    assert verdict.status != "INSUFFICIENT"
    years = next(r for r in verdict.table if r["metric"] == "years of history")
    assert years["replicated"] == pytest.approx(300 / 252, abs=0.05)


def test_the_gates_are_frozen():
    with pytest.raises(Exception):
        GATES.newey_west_t = 1.0


def test_every_verdict_records_the_gates_it_was_judged_against():
    verdict = verify(CLAIM, series(4, 2600, 0.0006), trials=3)
    gates = verdict.detail["gates"]
    assert gates["newey_west_t"] == GATES.newey_west_t
    assert "frozen" in gates["declared"]


def test_the_table_has_a_row_per_metric_and_renders():
    verdict = verify(CLAIM, series(4, 2600, 0.0006), trials=3)
    metrics = [r["metric"] for r in verdict.table]
    assert metrics == ["annual return", "Sharpe", "t-statistic",
                       "worst held-out path", "overfitting probability",
                       "years of history"]
    table = render_table(verdict)
    assert table.startswith("| | claimed | replicated | survives |")
    assert "n/a" in table


def test_a_claim_is_built_from_a_signaldoc_row():
    claim = claim_from_openap({
        "Acronym": "Mom12m", "Authors": "Jegadeesh and Titman",
        "Year": "1993", "T-Stat": "4.29", "Mean Return": "1.10",
        "SampleStartYear": "1965", "SampleEndYear": "1989",
        "Predictability in OP": "1_clear",
    })
    assert claim.paper_id == "openap_mom12m"
    assert claim.claimed_t == 4.29
    # SignalDoc quotes a monthly mean in percent.
    assert claim.claimed_annual_return == pytest.approx(0.132)
    assert claim.sample_start_year == 1965
    assert "Jegadeesh" in claim.source


def test_a_signaldoc_row_missing_numbers_still_makes_a_claim():
    claim = claim_from_openap({"Acronym": "X", "T-Stat": "", "Mean Return": "n/a"})
    assert claim.paper_id == "openap_x"
    assert claim.claimed_t is None
    assert claim.claimed_annual_return is None
