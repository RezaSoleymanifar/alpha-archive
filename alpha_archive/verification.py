"""Verification criteria, declared before a run and frozen.

The rule this module exists to enforce: **a replication is verified only when
it clears a criterion that was written down before the result was seen, against
a fixture we did not produce.**

This is not hypothetical rigour. On the first replication the criterion was set
at 0.6 correlation, the result came back at 0.74, and it was called "validated".
That is grading your own exam. Worse, 0.6 was chosen *after* seeing that 0.9 was
unreachable — the threshold moved to fit the number.

So:

- `Criterion` is frozen. Nothing in a run can change one.
- The default status is NOT_VERIFIED. Passing is something you earn.
- If the fixture cannot be fetched, the status is FIXTURE_UNAVAILABLE, which is
  a kind of failure, not a pass with an asterisk.
- A weaker check may run, but it is labelled SANITY_CHECK and can never promote
  a result to verified.

There is no middle tier. "Partially validated" is the phrase you reach for when
you want credit you have not earned.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable


class Status(str, Enum):
    VERIFIED = "VERIFIED"
    NOT_VERIFIED = "NOT_VERIFIED"
    FIXTURE_UNAVAILABLE = "FIXTURE_UNAVAILABLE"


@dataclass(frozen=True)
class Criterion:
    """What must be true for a replication to count as verified.

    `fixture` names the artifact we are matching and who produced it. If we
    produced it, it is not a fixture — it is an opinion.
    """
    name: str
    fixture: str
    fixture_source: str
    statistic: str
    threshold: float
    rationale: str
    like_for_like: bool
    fetchable: bool
    blocker: str = ""

    def judge(self, observed: float | None) -> tuple[Status, str]:
        if not self.fetchable:
            return Status.FIXTURE_UNAVAILABLE, (
                f"{self.fixture} is not fetchable, so this cannot be verified. {self.blocker}"
            )
        if observed is None:
            return Status.NOT_VERIFIED, f"{self.statistic} was not computed."
        if observed >= self.threshold:
            return Status.VERIFIED, (
                f"{self.statistic} = {observed:.4f} clears the {self.threshold} bar "
                f"against {self.fixture}."
            )
        return Status.NOT_VERIFIED, (
            f"{self.statistic} = {observed:.4f} is below the {self.threshold} bar "
            f"against {self.fixture}. The implementation must change, not the bar."
        )


@dataclass(frozen=True)
class SanityCheck:
    """A weaker comparison that informs but never verifies.

    Kept separate from `Criterion` in the type system so it is not possible to
    accidentally treat one as the other.
    """
    name: str
    against: str
    statistic: str
    note: str

    def describe(self, observed: float | None) -> str:
        value = "not computed" if observed is None else f"{observed:.4f}"
        return f"{self.statistic} vs {self.against}: {value}. {self.note}"


# --------------------------------------------------------------- the registry

# Declared here, away from any run, so a result cannot reach back and edit one.

CRITERIA: dict[str, Criterion] = {
    "Mom12m": Criterion(
        name="Mom12m parity",
        fixture="Open Source Asset Pricing's own monthly long-short return series for Mom12m",
        fixture_source="Chen & Zimmermann, openassetpricing.com",
        statistic="correlation with the fixture's monthly return series",
        threshold=0.95,
        rationale=(
            "Same signal, same equal-weighted decile construction, same holding "
            "period. A like-for-like comparison should be near-identical, so the "
            "bar is 0.95 rather than something that merely rhymes with the paper."
        ),
        like_for_like=True,
        fetchable=False,
        blocker=(
            "OpenAP publishes portfolio returns via Google Drive only. Those links "
            "return quota-exceeded and virus-scan interstitials rather than the file, "
            "and the GitHub releases carry no data assets. Until a stable URL exists, "
            "or CRSP is reproduced from free sources, this stays unverified."
        ),
    ),
}

SANITY: dict[str, SanityCheck] = {
    "Mom12m": SanityCheck(
        name="UMD directional check",
        against="Ken French UMD",
        statistic="correlation",
        note=(
            "UMD is value-weighted and double-sorted on size with NYSE breakpoints; "
            "this spec is an equal-weighted decile. They are different portfolios, so "
            "a high correlation is not available even from perfect code. This says "
            "whether we built momentum at all. It cannot verify parity."
        ),
    ),
}


def evaluate(paper: str, observed: float | None) -> dict[str, Any]:
    """Judge a replication against its declared criterion."""
    criterion = CRITERIA.get(paper)
    if criterion is None:
        return {
            "status": Status.NOT_VERIFIED.value,
            "reason": f"No verification criterion is declared for {paper}. "
                      "Declare one before running, not after.",
        }
    status, reason = criterion.judge(observed)
    return {
        "status": status.value,
        "reason": reason,
        "criterion": {
            "fixture": criterion.fixture,
            "fixture_source": criterion.fixture_source,
            "statistic": criterion.statistic,
            "threshold": criterion.threshold,
            "rationale": criterion.rationale,
            "like_for_like": criterion.like_for_like,
        },
        "what_would_verify_it": criterion.blocker or (
            f"{criterion.statistic} of at least {criterion.threshold} "
            f"against {criterion.fixture}."
        ),
    }


def sanity(paper: str, observed: float | None) -> dict[str, Any] | None:
    check = SANITY.get(paper)
    if check is None:
        return None
    return {
        "name": check.name,
        "against": check.against,
        "observed": observed,
        "description": check.describe(observed),
        "verifies": False,
    }
