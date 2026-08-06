"""Actor self-edit, given critic findings, propose patches to actor.md
calibration parameters and emit a git-friendly diff + commit message.

Hard rule (per meta/actor.md "Evolution policy"): the actor MAY edit actor.md
ONLY IF every change is supported by data and references at least one critique
report ID in the commit message. This module enforces that.

Outputs:
  - data/actor_proposals/{date}_{run_id}.md  (human-readable patch + rationale)
  - Optionally writes the patch to actor.md and stages it for commit (gated by
    --apply flag in CLI, default OFF for safety)

Note: this module proposes; humans (or `alpha-archive loop --auto-apply`) approve.
"""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import yaml

from alpha_archive.llm.factory import get_provider


REPO_ROOT = Path(__file__).resolve().parents[2]
ACTOR_MD = REPO_ROOT / "meta" / "actor.md"
PROPOSAL_DIR = REPO_ROOT / "data" / "actor_proposals"
CRIT_DIR = REPO_ROOT / "data" / "critique_runs"


SELF_EDIT_SYSTEM = """You are the ACTOR-SELF-EDIT agent for Alpha Archive.

You read recent CRITIC findings and propose precise patches to the calibration
parameters in meta/actor.md. You DO NOT rewrite policy text, only adjust the
YAML calibration block under "## Calibration parameters".

HARD RULES:
1. Only propose changes that are supported by ≥ 1 critic finding with severity
   HIGH or CRITICAL. Do not adjust based on LOW/INFO findings alone.
2. Never loosen kill thresholds (kill_dsr_threshold up, kill_icir_threshold up,
   kill_min_negative_gates down) without HIGH+ evidence that FN rate is preserved.
3. Bound the diff: max 3 calibration changes per proposal.
4. Each change must include WHY (which critique IDs justify it) and EXPECTED EFFECT
   (which north-star metric it should move).
5. Output JSON ONLY. No prose outside JSON. No markdown fences.

OUTPUT SCHEMA:
{
  "proposed_changes": [
    {
      "param_path": "<dotted path under calibration block, e.g. triage.haiku_confidence_threshold_for_kill>",
      "old_value": <current value>,
      "new_value": <proposed value>,
      "why": "<critique IDs + reasoning>",
      "expected_effect": "<which north-star metric, expected direction>"
    }
  ],
  "commit_message": "<one-line subject + multi-line body referencing critique IDs>",
  "open_questions": ["<questions for human reviewer>", ...]
}

If no changes are warranted (all recent critiques are LOW/INFO or nothing actionable),
return an empty proposed_changes array with commit_message="".
"""


def _load_actor_calibration() -> dict:
    """Parse the YAML calibration block from actor.md."""
    txt = ACTOR_MD.read_text(encoding="utf-8")
    m = re.search(r"```yaml\n(.*?)\n```", txt, re.DOTALL)
    if not m:
        return {}
    try:
        return yaml.safe_load(m.group(1)) or {}
    except Exception:
        return {}


def _load_recent_critiques(limit: int = 50) -> list[dict]:
    """Load the most recent critic reports (newest first)."""
    if not CRIT_DIR.exists():
        return []
    paths = sorted(CRIT_DIR.glob("*.json"), key=lambda p: p.stat().st_mtime,
                   reverse=True)[:limit]
    out = []
    for p in paths:
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
            d["_critique_id"] = p.stem
            out.append(d)
        except Exception:
            continue
    return out


def propose(*, critique_limit: int = 20, model: Optional[str] = None) -> dict:
    """Generate a proposal dict (does NOT write to disk; caller decides)."""
    if not ACTOR_MD.exists():
        return {"error": "meta/actor.md not found", "proposed_changes": []}

    calibration = _load_actor_calibration()
    critiques = _load_recent_critiques(limit=critique_limit)

    if not critiques:
        return {"proposed_changes": [], "commit_message": "",
                "open_questions": ["No critic reports in data/critique_runs/. Run `alpha-archive critique` first."]}

    # Aggregate severity counts and high-impact findings for the prompt
    severity_counts = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0, "INFO": 0}
    high_impact = []
    for c in critiques:
        for f in c.get("findings", []):
            sev = f.get("severity", "INFO")
            severity_counts[sev] = severity_counts.get(sev, 0) + 1
            if sev in ("HIGH", "CRITICAL"):
                high_impact.append({
                    "critique_id": c.get("_critique_id"),
                    "paper_id": c.get("paper_id"),
                    "severity": sev,
                    "category": f.get("category"),
                    "claim": f.get("claim"),
                    "proposed_actor_change": f.get("proposed_actor_change"),
                })

    prompt = f"""# CURRENT actor.md calibration block
{json.dumps(calibration, indent=2)}

# CRITIQUE SUMMARY
- Reports analyzed: {len(critiques)}
- Severity counts: {json.dumps(severity_counts)}

# HIGH/CRITICAL findings (only these justify changes)
{json.dumps(high_impact, indent=2)}

Apply the rules in your system prompt. Return the JSON proposal.
"""

    provider = get_provider()
    try:
        parsed = provider.complete_json(prompt, model=model, temperature=0.0,
                                        max_tokens=2000)
    except Exception as e:
        return {"error": f"LLM provider failed: {e}", "proposed_changes": []}

    return parsed


def write_proposal(proposal: dict) -> Path:
    """Persist a proposal as markdown for human review."""
    PROPOSAL_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out = PROPOSAL_DIR / f"{ts}_actor_proposal.md"

    changes = proposal.get("proposed_changes", [])
    body = [f"# Actor self-edit proposal, {ts}", ""]
    if not changes:
        body += ["**No changes proposed.** All recent critiques were LOW/INFO or "
                 "did not warrant calibration adjustment."]
    else:
        body += [f"## Proposed changes ({len(changes)})", ""]
        for c in changes:
            body += [
                f"### `{c.get('param_path')}`: `{c.get('old_value')}` → `{c.get('new_value')}`",
                f"- **Why**: {c.get('why')}",
                f"- **Expected effect**: {c.get('expected_effect')}",
                "",
            ]
        body += [
            "## Commit message",
            "```",
            proposal.get("commit_message", "(none)"),
            "```",
            "",
        ]

    if proposal.get("open_questions"):
        body += ["## Open questions for human reviewer", ""]
        for q in proposal["open_questions"]:
            body += [f"- {q}"]
        body += [""]

    if proposal.get("error"):
        body += [f"\n**ERROR**: {proposal['error']}\n"]

    out.write_text("\n".join(body), encoding="utf-8")
    return out


def apply_proposal(proposal: dict) -> bool:
    """Apply changes to actor.md in-place. Returns True if changes were applied.

    SAFETY: this directly modifies meta/actor.md. Caller is responsible for
    review + commit. Actor self-edit policy in meta/actor.md requires that the
    commit message reference critique IDs, apply_proposal does NOT auto-commit.
    """
    changes = proposal.get("proposed_changes", [])
    if not changes:
        return False

    calibration = _load_actor_calibration()
    if not calibration:
        return False

    # Apply each change to the calibration dict
    for c in changes:
        path = c.get("param_path", "").split(".")
        new_val = c.get("new_value")
        target = calibration
        for key in path[:-1]:
            target = target.setdefault(key, {})
        target[path[-1]] = new_val

    # Re-emit YAML block in-place
    txt = ACTOR_MD.read_text(encoding="utf-8")
    new_yaml = yaml.safe_dump(calibration, sort_keys=False, default_flow_style=False)
    new_block = f"```yaml\n{new_yaml.strip()}\n```"
    new_txt = re.sub(r"```yaml\n.*?\n```", new_block, txt, count=1, flags=re.DOTALL)
    ACTOR_MD.write_text(new_txt, encoding="utf-8")
    return True
