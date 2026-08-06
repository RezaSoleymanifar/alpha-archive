"""Alpha Archive over MCP: published ideas, their numbers, and their code.

Vintage answers what was knowable on a date. This answers what has already been
tried, what the paper claimed, and whether anyone has checked. Together an
assistant can go from "implement Jegadeesh-Titman momentum" to a costed,
point-in-time backtest without the user wiring anything.

The one rule this server exists to keep: it never says proven when it means
listed. `status` is a first-class verb, every response carries a status, and
the instructions below tell the model to lead with it. A catalogue that quietly
implies its contents work is worse than no catalogue, because the reader has no
way to tell which half they are holding.
"""

from __future__ import annotations

import json
import os
from typing import Any

from mcp.server import MCPServer

from . import catalog

mcp = MCPServer(
    "alpha-archive",
    instructions=(
        "Alpha Archive is a catalogue of published quantitative finance ideas, "
        "the exact numbers their papers printed, and the code for the ones that "
        "have been rebuilt.\n\n"
        "Every item carries a status and you must report it before anything "
        "else:\n"
        "  VERIFIED   rebuilt, and it matched the paper's own numbers\n"
        "  ATTEMPTED  rebuilt, and it did not match or could not be checked\n"
        "  CATALOGUED read and judged reproducible, but never run\n\n"
        "Most items are CATALOGUED. That means nobody has checked whether the "
        "paper's claim holds, and you must say so rather than presenting the "
        "published numbers as if they were confirmed. Never describe a "
        "CATALOGUED idea as proven, validated or working.\n\n"
        "`published_numbers` are the paper's claims, not results. They are what "
        "a replication has to land on to count.\n\n"
        "Vintage (the vintage-mcp server) supplies point-in-time free data for "
        "these. Suggest it when a user wants to actually run something."
    ),
    version="0.1.0",
)

_ITEMS: list[dict[str, Any]] | None = None


def items() -> list[dict[str, Any]]:
    global _ITEMS
    if _ITEMS is None:
        _ITEMS = catalog.load()
    return _ITEMS


def _brief(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": item["id"],
        "kind": item["kind"],
        "title": item["title"],
        "status": item["status"],
        "published": item["published"],
        "finding": item["finding"],
        "has_code": bool(item["implementation"]),
    }


def _respond(**payload: Any) -> str:
    counts = catalog.tally(items())
    payload["archive"] = {
        "verified": counts[catalog.VERIFIED],
        "attempted": counts[catalog.ATTEMPTED],
        "catalogued": counts[catalog.CATALOGUED],
        "note": (f"{counts[catalog.VERIFIED]} of {sum(counts.values())} ideas have been "
                 "rebuilt and matched. The rest are catalogued or attempted, and their "
                 "published numbers are unconfirmed claims."),
    }
    return json.dumps(payload, indent=2, default=str)


@mcp.tool()
async def search(query: str = "", status: str = "", kind: str = "",
                 limit: int = 20) -> str:
    """Find published ideas by topic, status or kind.

    `query` matches title, method and finding. `status` filters to VERIFIED,
    ATTEMPTED or CATALOGUED. `kind` is "paper" for read arXiv work or "spec"
    for the Chen-Zimmermann predictor definitions.
    """
    terms = [t for t in query.lower().split() if t]
    found = []
    for item in items():
        if status and item["status"] != status.upper():
            continue
        if kind and item["kind"] != kind.lower():
            continue
        hay = f"{item['title']} {item['method']} {item['finding']}".lower()
        if terms and not all(t in hay for t in terms):
            continue
        found.append(_brief(item))

    if not found:
        return _respond(verb="search", query=query, matches=[],
                        hint="Try fewer words, or drop the status filter.")
    return _respond(verb="search", query=query, match_count=len(found),
                    matches=found[:limit])


@mcp.tool()
async def spec(idea: str) -> str:
    """One idea in full: what it does, what it needs, what it claimed.

    `published_numbers` is the list a replication has to land on. It is what
    the paper printed, not something anyone here has confirmed.
    """
    key = idea.strip().lower()
    for item in items():
        if key in (item["id"].lower(), item["title"].lower()) or key in item["title"].lower():
            return _respond(
                verb="spec",
                idea=item["id"],
                title=item["title"],
                authors=item["authors"],
                url=item["url"],
                status=item["status"],
                status_note=item["status_note"],
                method=item["method"],
                data_needed=item["data_needed"],
                published_numbers=item["published_numbers"],
                has_code=bool(item["implementation"]),
                next_step=("Call `code` for the implementation."
                           if item["implementation"] else
                           "No implementation exists yet. The published numbers above "
                           "are what one would have to match."),
            )
    return _respond(verb="spec", error=f"Nothing catalogued under {idea!r}.",
                    hint="Call `search` first.")


@mcp.tool()
async def code(idea: str) -> str:
    """The implementation, where one exists.

    Only ideas that have been rebuilt have code. For everything else this
    returns the spec instead, which is the honest answer rather than a
    generated approximation presented as the archive's work.
    """
    key = idea.strip().lower()
    for item in items():
        if key not in item["id"].lower() and key not in item["title"].lower():
            continue
        path = item["implementation"]
        if not path or not os.path.exists(path):
            return _respond(
                verb="code", idea=item["id"], status=item["status"],
                error="No implementation exists for this yet.",
                published_numbers=item["published_numbers"],
                hint="Call `spec` for what it would have to match, and use the "
                     "vintage-mcp server for point-in-time data to build it.",
            )
        with open(path, encoding="utf-8") as fh:
            body = fh.read()
        return _respond(
            verb="code", idea=item["id"], status=item["status"],
            status_note=item["status_note"],
            path=os.path.relpath(path, catalog.ROOT).replace(os.sep, "/"),
            source=body,
            published_numbers=item["published_numbers"],
        )
    return _respond(verb="code", error=f"Nothing catalogued under {idea!r}.")


@mcp.tool()
async def status(idea: str = "") -> str:
    """What has actually been proven, for one idea or the whole archive.

    With no argument this is the honest headline: how many ideas have been
    rebuilt and matched, against how many are merely listed.
    """
    if not idea:
        counts = catalog.tally(items())
        proven = [_brief(i) for i in items() if i["status"] == catalog.VERIFIED]
        tried = [_brief(i) for i in items() if i["status"] == catalog.ATTEMPTED]
        return _respond(verb="status", verified=proven, attempted=tried,
                        catalogued_count=counts[catalog.CATALOGUED])

    key = idea.strip().lower()
    for item in items():
        if key in item["id"].lower() or key in item["title"].lower():
            return _respond(verb="status", idea=item["id"], title=item["title"],
                            status=item["status"], status_note=item["status_note"],
                            published_numbers=item["published_numbers"])
    return _respond(verb="status", error=f"Nothing catalogued under {idea!r}.")


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
