"""Autonomous external-mention scraper, MINIMAL SCOPE.

Per meta/community.md: we do NOT scrape Twitter / Reddit / Substack. Those
channels are 99% noise. Critics come to us via:
  - GitHub issues on the alpha_archive repo (working today via `gh` CLI)
  - Web UI comments on published landing pages (Phase 4)
  - Email submissions (Phase 4)

The Twitter/Reddit/Substack functions are kept as stubs but explicitly
disabled: calling them returns []. Revisit only if high-precision filtering
is built later (Phase 6+).
"""
from __future__ import annotations

import json
from dataclasses import dataclass


@dataclass
class ExternalMention:
    source: str
    source_url: str
    raw_text: str
    paper_id_guess: int | None = None


def scrape_github_issues(repo: str = "RezaSoleymanifar/alpha-archive") -> list[ExternalMention]:
    """Fetch open issues on the alpha_archive repo. Working today via `gh` CLI."""
    import subprocess
    try:
        out = subprocess.run(
            ["gh", "issue", "list", "--repo", repo, "--state", "all", "--json",
             "number,title,body,url,createdAt", "--limit", "50"],
            capture_output=True, text=True, timeout=30,
        )
    except Exception as e:
        return []
    if out.returncode != 0:
        return []
    try:
        items = json.loads(out.stdout)
    except json.JSONDecodeError:
        return []
    return [
        ExternalMention(
            source="github_issue",
            source_url=it["url"],
            raw_text=f"{it['title']}\n\n{it.get('body', '')}",
        )
        for it in items
    ]


def scrape_twitter(query: str) -> list[ExternalMention]:
    """DISABLED. Twitter is 99% noise; not worth the spam-filter cost.
    Re-enable only with high-precision filter (Phase 6+).
    """
    return []


def scrape_reddit(subreddits: list[str], query: str) -> list[ExternalMention]:
    """DISABLED. See scrape_twitter rationale."""
    return []


def scrape_substack(feed_urls: list[str]) -> list[ExternalMention]:
    """DISABLED. See scrape_twitter rationale."""
    return []


CLASSIFY_PROMPT = """You are classifying an external mention of an Alpha Archive paper replication.

The mention text is:
---
{text}
---

Classify the mention as ONE of:
  endorsement   (positive, agrees with Alpha Archive's verdict)
  critique      (challenges methodology, data, or verdict)
  alternative   (proposes a different implementation)
  discussion    (neutral discussion, no actionable claim)
  unrelated     (does not actually reference an Alpha Archive replication)

Output JSON: {{"signal_type": ..., "extracted_claim": "1-sentence", "actionable": true|false}}
"""


def classify_mention(mention: ExternalMention) -> dict:
    from ..llm import get_provider
    provider = get_provider()
    return provider.complete_json(
        CLASSIFY_PROMPT.format(text=mention.raw_text[:3000]),
        model="haiku",
        max_tokens=200,
    )


def run_daily_scrape() -> dict:
    """Top-level scrape job. Returns summary."""
    mentions = scrape_github_issues()
    # + scrape_twitter(...), scrape_reddit(...), scrape_substack(...) when configured
    return {
        "github_issues": len(mentions),
        "twitter": 0,
        "reddit": 0,
        "substack": 0,
        "note": "twitter/reddit/substack are stubs in v0.1.0",
    }
