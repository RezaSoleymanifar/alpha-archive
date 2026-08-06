"""Learn aggregator, meta-meta loop per meta/learn.md.

Runs weekly. Reads:
  - git log meta/actor.md (every actor change + commit message)
  - git log meta/critique.md (every critique-rule change)
  - data/meta_runs/metrics.jsonl (platform metrics time series)
  - data/critique_runs/*.json (critic findings history)

Computes:
  - For each actor commit, find the upstream critique it cites (via commit-msg
    regex), look up the next 3 platform metric snapshots, attribute Δ asymmetric
    loss to that critique
  - Aggregate per critique-rule (or per finding-category) the mean attribution

Emits:
  - data/learn_runs/{date}_attribution.json (rule-level attribution table)
  - data/learn_runs/{date}_proposal.md      (proposed critique.md edits)

This module is INTENTIONALLY proposal-only. Per meta/learn.md hard constraints,
it MUST NOT auto-merge or auto-edit critique.md. Output is a markdown PR draft
the human reviews and merges manually.
"""
from __future__ import annotations

import json
import re
import subprocess
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
META_DIR = REPO_ROOT / "meta"
METRICS_FILE = REPO_ROOT / "data" / "meta_runs" / "metrics.jsonl"
CRIT_DIR = REPO_ROOT / "data" / "critique_runs"
LEARN_DIR = REPO_ROOT / "data" / "learn_runs"

CRITIQUE_REF_PATTERN = re.compile(
    r"\bcritique[/_-]?(?:id|ref)?[:#]?\s*([A-Za-z0-9_]+)", re.IGNORECASE
)


def _git_log(path: str, since_days: int = 90) -> list[dict]:
    """Return list of {sha, ts, subject, body} for commits touching `path`."""
    try:
        out = subprocess.check_output(
            ["git", "log", f"--since={since_days}.days.ago",
             "--format=%H%x09%cI%x09%s%x09%b%x1e", "--", path],
            cwd=REPO_ROOT, encoding="utf-8", errors="replace",
        )
    except subprocess.CalledProcessError:
        return []
    commits = []
    for raw in out.split("\x1e"):
        raw = raw.strip()
        if not raw:
            continue
        parts = raw.split("\t", 3)
        if len(parts) < 3:
            continue
        sha, ts, subj = parts[0], parts[1], parts[2]
        body = parts[3] if len(parts) > 3 else ""
        commits.append({"sha": sha, "ts": ts, "subject": subj, "body": body})
    return commits


def _load_metrics() -> list[dict]:
    """Read metrics.jsonl, sorted by timestamp ascending."""
    if not METRICS_FILE.exists():
        return []
    rows = []
    for line in METRICS_FILE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except Exception:
            continue
    rows.sort(key=lambda r: r.get("ts", ""))
    return rows


def _attribute_changes(actor_commits: list[dict],
                       metrics: list[dict]) -> dict[str, list[float]]:
    """For each actor commit citing a critique, attribute Δ asymmetric loss
    to that critique. Returns {critique_id_or_category: [Δ L, ...]}.
    """
    attribution: dict[str, list[float]] = defaultdict(list)
    if not metrics:
        return attribution

    for commit in actor_commits:
        msg = (commit.get("subject", "") + "\n" + commit.get("body", "")).strip()
        refs = CRITIQUE_REF_PATTERN.findall(msg)
        if not refs:
            continue
        commit_ts = commit.get("ts", "")
        # Find pre/post metric snapshots straddling commit_ts
        pre = next((m for m in reversed(metrics) if m.get("ts", "") < commit_ts), None)
        post_window = [m for m in metrics if m.get("ts", "") > commit_ts][:3]
        if not pre or not post_window:
            continue
        pre_loss = pre.get("asymmetric_loss") or pre.get("L")
        post_loss = sum(m.get("asymmetric_loss") or m.get("L") or 0
                        for m in post_window) / len(post_window)
        if pre_loss is None or post_loss is None:
            continue
        delta = post_loss - pre_loss  # negative = improvement
        for ref in refs:
            attribution[ref].append(float(delta))
    return attribution


def aggregate(*, since_days: int = 90, write: bool = True) -> dict:
    """Run a learn aggregation cycle. Returns a dict; optionally writes
    artifacts to data/learn_runs/.
    """
    actor_commits = _git_log(str(META_DIR / "actor.md"), since_days=since_days)
    critique_commits = _git_log(str(META_DIR / "critique.md"), since_days=since_days)
    metrics = _load_metrics()

    attribution = _attribute_changes(actor_commits, metrics)

    # Roll up per-rule
    rule_summary = []
    for ref, deltas in attribution.items():
        n = len(deltas)
        mean = sum(deltas) / n if n else 0.0
        verdict = (
            "promote" if (n >= 5 and mean < -2.0) else
            "demote" if (n >= 5 and mean > 2.0) else
            "low_signal" if (n >= 5) else
            "needs_more_data"
        )
        rule_summary.append({
            "critique_ref": ref,
            "fired_n_times": n,
            "mean_delta_L": round(mean, 3),
            "verdict": verdict,
        })
    rule_summary.sort(key=lambda r: r["mean_delta_L"])

    artifact = {
        "run_ts": datetime.now(timezone.utc).isoformat(),
        "since_days": since_days,
        "actor_commits_analyzed": len(actor_commits),
        "critique_commits_analyzed": len(critique_commits),
        "metric_snapshots_available": len(metrics),
        "rule_attribution": rule_summary,
        "summary": (
            "ATTRIBUTION CHAIN BROKEN, no actor commits cited critiques."
            if not attribution else
            f"{len(attribution)} critique refs attributed across "
            f"{sum(len(d) for d in attribution.values())} actor commits."
        ),
    }

    if write:
        LEARN_DIR.mkdir(parents=True, exist_ok=True)
        ts = datetime.now(timezone.utc).strftime("%Y%m%d")
        attribution_file = LEARN_DIR / f"{ts}_attribution.json"
        attribution_file.write_text(
            json.dumps(artifact, indent=2, default=str), encoding="utf-8"
        )

        # Generate proposal markdown
        proposal_file = LEARN_DIR / f"{ts}_proposal.md"
        proposal_file.write_text(_render_proposal(artifact), encoding="utf-8")

    return artifact


def _render_proposal(artifact: dict) -> str:
    lines = [
        f"# Learn aggregator, proposed critique.md updates",
        f"Run: {artifact['run_ts']}",
        f"Window: last {artifact['since_days']} days",
        "",
        "## Inputs analyzed",
        f"- actor.md commits: {artifact['actor_commits_analyzed']}",
        f"- critique.md commits: {artifact['critique_commits_analyzed']}",
        f"- platform metric snapshots: {artifact['metric_snapshots_available']}",
        "",
        "## Summary",
        artifact["summary"],
        "",
        "## Rule attribution table",
        "",
        "| critique_ref | fired_n | mean Δ L | verdict |",
        "|---|---:|---:|---|",
    ]
    for r in artifact["rule_attribution"]:
        lines.append(
            f"| `{r['critique_ref']}` | {r['fired_n_times']} | "
            f"{r['mean_delta_L']:+.3f} | {r['verdict']} |"
        )
    if not artifact["rule_attribution"]:
        lines.append("| _(none, no attribution chain established)_ | | | |")
    lines += [
        "",
        "## Recommended actions",
        "",
        "_Per meta/learn.md hard constraint: this is a PROPOSAL only. Human "
        "reviewer must approve any critique.md change._",
        "",
    ]
    promotes = [r for r in artifact["rule_attribution"] if r["verdict"] == "promote"]
    demotes = [r for r in artifact["rule_attribution"] if r["verdict"] == "demote"]
    if promotes:
        lines += ["### PROMOTE (rules that improved L)", ""]
        for r in promotes:
            lines.append(f"- `{r['critique_ref']}`, strengthen / make more strict")
        lines += [""]
    if demotes:
        lines += ["### DEMOTE (rules that degraded L)", ""]
        for r in demotes:
            lines.append(f"- `{r['critique_ref']}`, weaken or remove")
        lines += [""]
    if not promotes and not demotes:
        lines.append("- No high-confidence promotions/demotions yet. Need more "
                     "actor-commit / critique-attribution evidence.")
    return "\n".join(lines)
