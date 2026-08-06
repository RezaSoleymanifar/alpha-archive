"""Gate 1, LLM-based screening of community submissions.

For each submission, the LLM judges:
  - on_topic         (matches paper / result?)
  - specific         (concrete claim, not vague)
  - evidence_supports (does evidence_payload back the claim?)
  - low_effort       (looks like spam or ChatGPT slop?)

Result: pass | spam | low_effort  + notes for the submitter.

Per meta/community.md.
"""
from __future__ import annotations

import json
from dataclasses import dataclass

from ..llm import get_provider

SCREEN_MODEL = "haiku"

SCREEN_PROMPT = """You are a moderator for Alpha Archive, an open-source platform that replicates academic quant finance papers and publishes verdicts (ship / iterate / kill). Users can submit challenges to Alpha Archive's automated replications.

Judge whether the following submission should pass initial screening.

PAPER TITLE: {paper_title}
ALPHASCOPE VERDICT: {verdict}

SUBMISSION TYPE: {submission_type}
USER CLAIM: {claim}
EVIDENCE TYPE: {evidence_type}
EVIDENCE PAYLOAD (truncated): {evidence_payload}
PROPOSED REMEDIATION: {proposed_remediation}

Output strict JSON:
{{
  "on_topic": true | false,
  "specific": true | false,
  "evidence_supports_claim": true | false,
  "low_effort_or_spam": true | false,
  "verdict": "pass" | "spam" | "low_effort" | "off_topic" | "weak_evidence",
  "notes": "1-sentence feedback for the submitter"
}}
"""


@dataclass
class ScreeningResult:
    verdict: str  # pass | spam | low_effort | off_topic | weak_evidence
    notes: str
    raw: dict


def screen_submission(
    paper_title: str,
    verdict: str,
    submission_type: str,
    claim: str,
    evidence_type: str | None,
    evidence_payload: str | None,
    proposed_remediation: str | None = None,
) -> ScreeningResult:
    provider = get_provider()
    prompt = SCREEN_PROMPT.format(
        paper_title=paper_title or "(unknown)",
        verdict=verdict or "(unknown)",
        submission_type=submission_type,
        claim=(claim or "")[:1500],
        evidence_type=evidence_type or "none",
        evidence_payload=(evidence_payload or "")[:2000],
        proposed_remediation=proposed_remediation or "none",
    )
    parsed = provider.complete_json(prompt, model=SCREEN_MODEL, max_tokens=300)
    return ScreeningResult(
        verdict=parsed.get("verdict", "off_topic"),
        notes=parsed.get("notes", ""),
        raw=parsed,
    )
