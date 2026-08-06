"""Reproduction is a per-artifact fact, not a per-paper one.

A paper prints eight numbers. Rebuild two of them exactly and the honest report
is "two of eight", not one adjective covering the whole thing. Calling that
paper ATTEMPTED throws away that two numbers landed to the cent. Calling it
REPRODUCED claims six that were never touched.

So the verdict lives on the artifact. Each one is a number the paper printed,
with the tolerance it has to be matched inside, and each carries its own state:

    REPRODUCED     rebuilt and inside tolerance
    MISSED         rebuilt and outside tolerance
    NOT_ATTEMPTED  nobody has built this yet
    UNOBTAINABLE   the fixture needed to check it cannot be got

The paper-level line is then arithmetic rather than judgement: two of eight
reproduced, none missed, six not attempted. Nobody has to trust an adjective.

A paper only reads as fully reproduced when every artifact is REPRODUCED and
there is at least one of them, which is deliberately hard.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import Any

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STORE = os.path.join(ROOT, "data", "artifacts")

REPRODUCED = "REPRODUCED"
MISSED = "MISSED"
NOT_ATTEMPTED = "NOT_ATTEMPTED"
UNOBTAINABLE = "UNOBTAINABLE"


@dataclass
class Artifact:
    """One number the paper printed, and whether we landed on it."""
    name: str
    published: float
    tolerance: float
    units: str = ""
    where: str = ""
    observed: float | None = None
    note: str = ""
    blocker: str = ""

    @property
    def state(self) -> str:
        if self.blocker:
            return UNOBTAINABLE
        if self.observed is None:
            return NOT_ATTEMPTED
        return (REPRODUCED if abs(self.observed - self.published) <= self.tolerance
                else MISSED)

    @property
    def gap(self) -> float | None:
        if self.observed is None:
            return None
        return round(abs(self.observed - self.published), 6)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "published": self.published,
            "observed": self.observed,
            "tolerance": self.tolerance,
            "units": self.units,
            "where": self.where,
            "gap": self.gap,
            "state": self.state,
            "note": self.note,
            "blocker": self.blocker,
        }


@dataclass
class Replication:
    paper: str
    title: str
    artifacts: list[Artifact] = field(default_factory=list)
    notebook: str = ""
    code: str = ""

    def tally(self) -> dict[str, int]:
        counts = {REPRODUCED: 0, MISSED: 0, NOT_ATTEMPTED: 0, UNOBTAINABLE: 0}
        for a in self.artifacts:
            counts[a.state] += 1
        return counts

    def headline(self) -> str:
        """The sentence that goes on the card. Arithmetic, not adjective."""
        counts = self.tally()
        total = len(self.artifacts)
        parts = [f"{counts[REPRODUCED]} of {total} published numbers reproduced"]
        if counts[MISSED]:
            parts.append(f"{counts[MISSED]} missed")
        if counts[UNOBTAINABLE]:
            parts.append(f"{counts[UNOBTAINABLE]} uncheckable")
        if counts[NOT_ATTEMPTED]:
            parts.append(f"{counts[NOT_ATTEMPTED]} not built yet")
        return ", ".join(parts)

    def complete(self) -> bool:
        counts = self.tally()
        return bool(self.artifacts) and counts[REPRODUCED] == len(self.artifacts)

    def to_dict(self) -> dict[str, Any]:
        return {
            "paper": self.paper,
            "title": self.title,
            "headline": self.headline(),
            "fully_reproduced": self.complete(),
            "tally": self.tally(),
            "notebook": self.notebook,
            "code": self.code,
            "artifacts": [a.to_dict() for a in self.artifacts],
        }

    def save(self) -> str:
        os.makedirs(STORE, exist_ok=True)
        path = os.path.join(STORE, f"{self.paper}.json")
        with open(path, "w", encoding="utf-8", newline="\n") as fh:
            json.dump(self.to_dict(), fh, indent=1)
        return path


def load_all() -> list[dict[str, Any]]:
    if not os.path.isdir(STORE):
        return []
    out = []
    for name in sorted(os.listdir(STORE)):
        if not name.endswith(".json"):
            continue
        with open(os.path.join(STORE, name), encoding="utf-8") as fh:
            try:
                out.append(json.load(fh))
            except json.JSONDecodeError:
                continue
    return out


def totals() -> dict[str, int]:
    """Across every replication: how many published numbers have we landed on."""
    counts = {REPRODUCED: 0, MISSED: 0, NOT_ATTEMPTED: 0, UNOBTAINABLE: 0}
    for rec in load_all():
        for key, n in (rec.get("tally") or {}).items():
            counts[key] = counts.get(key, 0) + n
    return counts
