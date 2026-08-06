"""Loop orchestrator, chain the autonomous self-improvement cycle.

One full loop iteration:
  1. POLL: pull new papers from configured sources (--skip-poll to bypass)
  2. TRIAGE: LLM-classify pending papers; emit triage_notes
  3. REPLICATE: for each newly-tradable paper, run end-to-end pipeline
  4. CRITIQUE: grade each new ReplicationReport against meta/critique.md
  5. ACTOR-PROPOSE: generate actor.md calibration proposal from critic findings
  6. METRICS-LOG: append asymmetric loss + verdict counts to data/meta_runs/metrics.jsonl
  7. (weekly only) LEARN: run aggregator → propose critique.md updates

DEFAULT SAFETY:
  - Steps 1-6 run autonomously (read + write data/, no git commits)
  - Step 5 emits a PROPOSAL markdown but does NOT auto-apply to actor.md
  - Step 7 emits a PROPOSAL markdown but does NOT auto-merge to critique.md
  - Set --auto-apply to apply actor.md proposals (still requires human commit)
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from alpha_archive.agent import critic, actor_self_edit, learn_aggregator


REPO_ROOT = Path(__file__).resolve().parents[2]
METRICS_FILE = REPO_ROOT / "data" / "meta_runs" / "metrics.jsonl"
REPL_DIR = REPO_ROOT / "data" / "replications"


@dataclass
class LoopResult:
    started_at: str
    finished_at: str = ""
    polled: int = 0
    triaged: int = 0
    new_tradable: int = 0
    replicated: int = 0
    critiqued: int = 0
    actor_changes_proposed: int = 0
    learn_run: bool = False
    metrics_snapshot: dict = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)


def _log_metrics(loop: LoopResult) -> None:
    """Append a per-loop metrics row to data/meta_runs/metrics.jsonl."""
    METRICS_FILE.parent.mkdir(parents=True, exist_ok=True)

    # Compute platform-level asymmetric loss from all replications
    total_loss = 0.0
    n = 0
    for p in REPL_DIR.glob("*.json"):
        try:
            r = json.loads(p.read_text(encoding="utf-8"))
            verdict = r.get("verdict", "unknown")
            bt = r.get("backtest") or {}
            repl = bt.get("replication_score")
            total_loss += critic._asymmetric_loss(verdict, None, repl)
            n += 1
        except Exception:
            continue
    avg_loss = total_loss / n if n else 0.0

    snapshot = {
        "ts": loop.finished_at,
        "loop_polled": loop.polled,
        "loop_triaged": loop.triaged,
        "loop_replicated": loop.replicated,
        "loop_critiqued": loop.critiqued,
        "loop_actor_proposals": loop.actor_changes_proposed,
        "platform_replications_total": n,
        "asymmetric_loss": round(avg_loss, 4),
        "L": round(avg_loss, 4),  # alias for learn_aggregator
    }
    loop.metrics_snapshot = snapshot
    with METRICS_FILE.open("a", encoding="utf-8") as f:
        f.write(json.dumps(snapshot) + "\n")


def run(*, skip_poll: bool = False,
        triage_limit: int = 20,
        replicate_limit: int = 5,
        run_learn: bool = False,
        auto_apply_actor: bool = False,
        critic_model: Optional[str] = None) -> LoopResult:
    """One full autonomous loop iteration."""
    loop = LoopResult(started_at=datetime.now(timezone.utc).isoformat())

    # Lazy imports, these depend on heavy modules
    from alpha_archive import ingest, triage as triage_mod
    from alpha_archive.db import Session, Paper

    # === Step 1: POLL ===
    if not skip_poll:
        try:
            summary = ingest.ingest(source="primary")
            loop.polled = sum(s.get("new", 0) for s in summary.values())
        except Exception as e:
            loop.errors.append(f"poll: {type(e).__name__}: {e}")

    # === Step 2: TRIAGE ===
    try:
        triaged = triage_mod.triage_pending(limit=triage_limit)
        if isinstance(triaged, dict):
            loop.triaged = sum(triaged.values()) if triaged else 0
        elif isinstance(triaged, list):
            loop.triaged = len(triaged)
        else:
            loop.triaged = int(triaged or 0)
    except Exception as e:
        loop.errors.append(f"triage: {type(e).__name__}: {e}")

    # === Step 3: REPLICATE newly-tradable ===
    s = Session()
    new_tradable = (
        s.query(Paper)
        .filter(Paper.triage_status == "tradable")
        .order_by(Paper.id.desc())
        .limit(replicate_limit)
        .all()
    )
    loop.new_tradable = len(new_tradable)

    for p in new_tradable:
        # Skip if already replicated
        if (REPL_DIR / f"{p.external_id or p.id}.json").exists():
            continue
        try:
            from alpha_archive import replicate as repl_mod
            paper_key = p.external_id or str(p.id)
            pdf_url = p.pdf_url
            if not pdf_url:
                continue
            repl_mod.replicate(paper_key, pdf_url, title=p.title)
            loop.replicated += 1
        except Exception as e:
            loop.errors.append(f"replicate {p.id}: {type(e).__name__}: {e}")

    # === Step 4: CRITIQUE ===
    try:
        written = critic.critique_all(model=critic_model)
        loop.critiqued = len(written)
    except Exception as e:
        loop.errors.append(f"critique: {type(e).__name__}: {e}")

    # === Step 5: ACTOR-PROPOSE ===
    try:
        proposal = actor_self_edit.propose()
        actor_self_edit.write_proposal(proposal)
        loop.actor_changes_proposed = len(proposal.get("proposed_changes", []))
        if auto_apply_actor and proposal.get("proposed_changes"):
            actor_self_edit.apply_proposal(proposal)
    except Exception as e:
        loop.errors.append(f"actor_propose: {type(e).__name__}: {e}")

    # === Step 6: METRICS-LOG ===
    loop.finished_at = datetime.now(timezone.utc).isoformat()
    try:
        _log_metrics(loop)
    except Exception as e:
        loop.errors.append(f"metrics: {type(e).__name__}: {e}")

    # === Step 7 (optional): LEARN ===
    if run_learn:
        try:
            learn_aggregator.aggregate(write=True)
            loop.learn_run = True
        except Exception as e:
            loop.errors.append(f"learn: {type(e).__name__}: {e}")

    return loop


def render_summary(loop: LoopResult) -> str:
    """Human-readable summary for CLI / cron logs."""
    lines = [
        "=" * 70,
        f"Alpha Archive autonomous loop, {loop.finished_at}",
        "=" * 70,
        f"  polled new papers:      {loop.polled}",
        f"  triaged pending:        {loop.triaged}",
        f"  newly tradable:         {loop.new_tradable}",
        f"  replicated end-to-end:  {loop.replicated}",
        f"  critiqued reports:      {loop.critiqued}",
        f"  actor-proposed changes: {loop.actor_changes_proposed}",
        f"  learn-aggregator run:   {loop.learn_run}",
        "",
        f"  platform asymmetric loss L: {loop.metrics_snapshot.get('asymmetric_loss', 'n/a')}",
        f"  platform replications total: {loop.metrics_snapshot.get('platform_replications_total', 'n/a')}",
    ]
    if loop.errors:
        lines += ["", f"  ERRORS ({len(loop.errors)}):"]
        for e in loop.errors[:10]:
            lines.append(f"    - {e}")
    lines += ["=" * 70]
    return "\n".join(lines)
