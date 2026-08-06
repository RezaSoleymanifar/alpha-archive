"""Gate 4, Community Notes-style bipartisan agreement check.

A submission requires SAME-DIRECTION votes from at least 2 distinct factions
to pass merge consideration. This prevents:
- AI-trusters always voting against challenges (single-faction rejection)
- AI-skeptics always voting for challenges (single-faction acceptance)

Per meta/community.md.
"""
from __future__ import annotations

from collections import Counter
from typing import Iterable


def check_bipartisan_agreement(
    votes: Iterable[dict],
    *,
    min_factions: int = 2,
    direction_required: str = "agree",
    rep_weighted: bool = True,
) -> tuple[bool, dict]:
    """Each vote dict must have: {vote: 'agree'|'disagree', faction: str, weight: float}

    Returns (passed, evidence_dict).
    """
    by_faction = {}
    for v in votes:
        if v["vote"] != direction_required:
            continue
        f = v.get("faction", "unknown")
        if f == "unknown":
            continue
        by_faction.setdefault(f, 0.0)
        by_faction[f] += v.get("weight", 1.0) if rep_weighted else 1.0

    distinct_factions = len(by_faction)
    passed = distinct_factions >= min_factions
    return passed, {
        "by_faction": by_faction,
        "distinct_factions_in_direction": distinct_factions,
        "min_required": min_factions,
        "direction_checked": direction_required,
    }
