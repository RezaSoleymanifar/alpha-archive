"""Critic agent, grades ReplicationReports against meta/critique.md.

Reads:
  - data/replications/{paper_id}.json  (ReplicationReport written by replicate.py)
  - meta/critique.md                   (rubric)
  - meta/north_star.md                 (asymmetric loss + decision boundaries)

Emits:
  - data/critique_runs/{paper_id}_{ts}.json  (structured findings)

Findings schema (per paper):
  {
    "paper_id": str,
    "run_ts": ISO8601,
    "north_star_alignment_score": int 0-100,
    "asymmetric_loss": float,
    "findings": [
      {
        "severity": "CRITICAL"|"HIGH"|"MEDIUM"|"LOW"|"INFO",
        "category": "outcome_alignment"|"process"|"false_negative"|"false_positive"
                    |"methodology_drift"|"reproducibility",
        "claim": str,
        "evidence": str,
        "proposed_actor_change": str (free-text patch suggestion)
      }, ...
    ],
    "anti_patterns_triggered": [str],   # from critique.md anti-pattern list
    "open_questions": [str]
  }
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from alpha_archive.llm.factory import get_provider


REPO_ROOT = Path(__file__).resolve().parents[2]
REPL_DIR = REPO_ROOT / "data" / "replications"
CRIT_DIR = REPO_ROOT / "data" / "critique_runs"
META_DIR = REPO_ROOT / "meta"


CRITIC_SYSTEM = """You are the CRITIC agent for the Alpha Archive paper-replication
pipeline. Your job is to grade a single replication run against the rubric in
meta/critique.md and the quality bar in meta/north_star.md.

You do NOT execute the pipeline. You only read its outputs and produce structured
feedback. Be specific, evidence-based, and reference exact metric values from the
report. Never propose changes to north_star.md or learn.md.

OUTPUT FORMAT: return a single JSON object matching this schema exactly. No prose
outside JSON. No markdown fences.

{
  "north_star_alignment_score": <int 0-100>,
  "asymmetric_loss_for_this_run": <float>,
  "findings": [
    {
      "severity": "CRITICAL"|"HIGH"|"MEDIUM"|"LOW"|"INFO",
      "category": "outcome_alignment"|"process"|"false_negative"|"false_positive"|"methodology_drift"|"reproducibility",
      "claim": "<one-sentence finding>",
      "evidence": "<exact metric value or quoted spec text supporting the claim>",
      "proposed_actor_change": "<concrete patch suggestion for actor.md, or empty string>"
    }
  ],
  "anti_patterns_triggered": ["<anti-pattern name from critique.md>", ...],
  "open_questions": ["<questions for human reviewer>", ...]
}
"""


def _load(p: Path) -> str:
    return p.read_text(encoding="utf-8") if p.exists() else ""


def _asymmetric_loss(verdict: str, expected_verdict: Optional[str],
                     repl_score: Optional[float]) -> float:
    """L = 5·FN + 1·FP + 2·|repl_score - 0.6|. Compute per-paper contribution."""
    fn = 1 if (verdict == "kill" and expected_verdict == "ship") else 0
    fp = 1 if (verdict == "ship" and expected_verdict == "kill") else 0
    score_term = abs((repl_score or 0.6) - 0.6) if repl_score is not None else 0.0
    return 5.0 * fn + 1.0 * fp + 2.0 * score_term


@dataclass
class CriticFinding:
    severity: str
    category: str
    claim: str
    evidence: str
    proposed_actor_change: str = ""


@dataclass
class CriticReport:
    paper_id: str
    run_ts: str
    north_star_alignment_score: int
    asymmetric_loss: float
    findings: list[dict] = field(default_factory=list)
    anti_patterns_triggered: list[str] = field(default_factory=list)
    open_questions: list[str] = field(default_factory=list)


def critique_report(report_path: Path,
                    *,
                    expected_verdict: Optional[str] = None,
                    model: Optional[str] = None) -> CriticReport:
    """Run the critic on a single ReplicationReport JSON.

    Args:
        report_path: path to data/replications/{paper_id}.json
        expected_verdict: ground-truth verdict if known (from fixture); used for
                          asymmetric loss + FN/FP detection
        model: LLM model alias (default: provider's "sonnet")

    Returns:
        CriticReport with structured findings.
    """
    if not report_path.exists():
        raise FileNotFoundError(report_path)

    report = json.loads(report_path.read_text(encoding="utf-8"))
    paper_id = report.get("paper_id", report_path.stem)
    verdict = report.get("verdict", "unknown")
    backtest = report.get("backtest") or {}
    repl_score = backtest.get("replication_score")

    # Compute deterministic asymmetric loss (independent of LLM)
    loss = _asymmetric_loss(verdict, expected_verdict, repl_score)

    # Build LLM prompt
    critique_md = _load(META_DIR / "critique.md")
    north_star_md = _load(META_DIR / "north_star.md")

    prompt = f"""# RUBRIC (meta/critique.md)
{critique_md}

# QUALITY BAR (meta/north_star.md, relevant excerpt)
{north_star_md}

# REPLICATION REPORT TO GRADE
{json.dumps(report, indent=2, default=str)}

# CONTEXT
- Expected verdict (from fixture, if known): {expected_verdict or "UNKNOWN"}
- Computed asymmetric loss for this run: {loss:.3f}

Apply the rubric. Identify findings. Return the JSON object per the schema in your
system prompt.
"""

    provider = get_provider()
    try:
        parsed = provider.complete_json(prompt, model=model, temperature=0.0,
                                        max_tokens=4000)
    except Exception as e:
        # If LLM fails, still produce a deterministic report so the loop continues
        return CriticReport(
            paper_id=paper_id,
            run_ts=datetime.now(timezone.utc).isoformat(),
            north_star_alignment_score=0,
            asymmetric_loss=loss,
            findings=[asdict(CriticFinding(
                severity="HIGH",
                category="process",
                claim=f"Critic LLM call failed: {type(e).__name__}",
                evidence=str(e)[:300],
                proposed_actor_change="",
            ))],
            open_questions=["LLM provider unavailable; rerun critic when fixed."],
        )

    return CriticReport(
        paper_id=paper_id,
        run_ts=datetime.now(timezone.utc).isoformat(),
        north_star_alignment_score=int(parsed.get("north_star_alignment_score", 0)),
        asymmetric_loss=float(parsed.get("asymmetric_loss_for_this_run", loss)),
        findings=parsed.get("findings", []),
        anti_patterns_triggered=parsed.get("anti_patterns_triggered", []),
        open_questions=parsed.get("open_questions", []),
    )


def write_critique(report: CriticReport) -> Path:
    """Persist a critic report to data/critique_runs/{paper_id}_{ts}.json."""
    CRIT_DIR.mkdir(parents=True, exist_ok=True)
    ts = report.run_ts.replace(":", "").replace("-", "").split(".")[0]
    out = CRIT_DIR / f"{report.paper_id}_{ts}.json"
    out.write_text(json.dumps(asdict(report), indent=2, default=str),
                   encoding="utf-8")
    return out


def critique_all(model: Optional[str] = None,
                 expected_verdicts: Optional[dict[str, str]] = None) -> list[Path]:
    """Run critic on every ReplicationReport in data/replications/. Returns paths
    written.
    """
    expected_verdicts = expected_verdicts or {}
    written: list[Path] = []
    if not REPL_DIR.exists():
        return written
    for p in sorted(REPL_DIR.glob("*.json")):
        rep = critique_report(p, expected_verdict=expected_verdicts.get(p.stem),
                              model=model)
        written.append(write_critique(rep))
    return written
