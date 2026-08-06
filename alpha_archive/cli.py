"""Alpha Archive CLI."""
from __future__ import annotations

import json

import typer
from rich import print as rprint
from rich.table import Table

from .db import init_db, Paper, Session
from .ingest import ingest as ingest_fn, SOURCES
from .triage import triage_pending
from sqlalchemy import select, func

app = typer.Typer(help="Alpha Archive, paper-to-backtest replication engine")


@app.command("init")
def cmd_init():
    """Initialize SQLite database."""
    p = init_db()
    rprint(f"[green]initialized[/green] {p}")


@app.command("llm-info")
def cmd_llm_info():
    """Show which LLM provider is selected and why."""
    from .llm.factory import info
    import json as _json
    rprint(_json.dumps(info(), indent=2))


@app.command("poll")
def cmd_poll(
    source: str = typer.Argument("all", help=f"one of {list(SOURCES.keys())} or 'all'"),
    limit: int = typer.Option(None, help="max papers per source"),
):
    """Poll source(s) for new papers."""
    summary = ingest_fn(source=source, limit=limit)
    table = Table(title=f"ingest summary ({source})")
    table.add_column("source")
    table.add_column("new", justify="right")
    table.add_column("dup", justify="right")
    table.add_column("polled", justify="right")
    for src, stats in summary.items():
        table.add_row(src, str(stats["new"]), str(stats["duplicate"]), str(stats["total_polled"]))
    rprint(table)


@app.command("triage")
def cmd_triage(
    limit: int = typer.Option(50, help="max papers to triage"),
    dry_run: bool = typer.Option(False, help="don't call LLM, just list"),
):
    """LLM-triage pending papers."""
    summary = triage_pending(limit=limit, dry_run=dry_run)
    rprint(json.dumps(summary, indent=2))


@app.command("stats")
def cmd_stats():
    """Show per-source paper counts and triage status."""
    init_db()
    with Session() as s:
        rows = s.execute(
            select(Paper.source, Paper.triage_status, func.count())
            .group_by(Paper.source, Paper.triage_status)
        ).all()
    table = Table(title="paper counts")
    table.add_column("source")
    table.add_column("triage_status")
    table.add_column("count", justify="right")
    for src, status, n in sorted(rows):
        table.add_row(src or "?", status or "?", str(n))
    rprint(table)


@app.command("replicate")
def cmd_replicate(
    paper_id: str = typer.Argument(..., help="paper id (will be db key)"),
    pdf_url: str = typer.Argument(..., help="direct PDF URL"),
    title: str = typer.Option(None),
    use_llm: bool = typer.Option(True, help="use LLM for spec+code (requires ANTHROPIC_API_KEY)"),
):
    """End-to-end: download PDF -> extract spec -> generate code -> backtest -> verdict."""
    from .replicate import replicate
    from dataclasses import asdict
    rpt = replicate(paper_id, pdf_url, title=title, use_llm=use_llm)
    rprint(f"[bold]paper:[/bold] {paper_id}")
    rprint(f"[bold]status:[/bold] {rpt.pipeline_status}")
    if rpt.pipeline_errors:
        rprint(f"[red]errors:[/red] {rpt.pipeline_errors}")
    if rpt.spec:
        rprint(f"[bold]spec:[/bold] horizon={rpt.spec.get('horizon_days')}, universe={rpt.spec.get('universe')}, sign={rpt.spec.get('expected_sign')}")
    if rpt.backtest:
        rprint(f"[bold]backtest:[/bold] Sharpe={rpt.backtest.get('sharpe'):.3f} IC={rpt.backtest.get('ic_mean'):.4f} ICIR={rpt.backtest.get('icir'):.3f}")
    if rpt.verdict:
        color = {"ship": "green", "iterate": "yellow", "kill": "red"}.get(rpt.verdict, "white")
        rprint(f"[bold {color}]verdict: {rpt.verdict.upper()}[/bold {color}]")
        for r in rpt.verdict_reasoning:
            rprint(f"  - {r}")


@app.command("install-fixtures")
def cmd_install_fixtures(
    source: str = typer.Argument("openap", help="fixture source: openap"),
    force: bool = typer.Option(False, help="re-download source data"),
):
    """Bootstrap fixture set from external ground-truth corpus.

    `openap` = Open Source Asset Pricing project (Chen + Zimmermann),
    326 documented anomalies with peer-reviewed verdicts. Free.
    """
    if source != "openap":
        rprint(f"[red]unknown source: {source}[/red]")
        raise typer.Exit(1)
    from .fixtures_openap import install_openap_fixtures, stats
    s = stats()
    rprint(f"[bold]OpenAP corpus:[/bold] {s['total']} documented anomalies")
    rprint(f"  by verdict: {s['by_verdict']}")
    rprint(f"  by sign:    {s['by_sign']}")
    added = install_openap_fixtures(force_download=force)
    rprint(f"[green]registered {added} new fixtures into the meta-loop[/green]")


@app.command("evaluate")
def cmd_evaluate():
    """Run the meta-learning evaluation loop on all fixtures."""
    from .meta.eval_loop import evaluate_all_fixtures
    from .meta.calibration import log_metrics, regression_check
    from pathlib import Path
    summary = evaluate_all_fixtures(output_path=Path("data/meta_runs/latest.json"))
    print(summary.summarize())
    log_metrics(summary)
    alerts = regression_check(summary)
    if alerts:
        rprint("[red]REGRESSION ALERTS:[/red]")
        for a in alerts:
            rprint(f"  ! {a}")


@app.command("list")
def cmd_list(
    source: str = typer.Option(None),
    status: str = typer.Option(None, help="pending|tradable|not_tradable|error"),
    limit: int = typer.Option(20),
):
    """List papers (filterable)."""
    init_db()
    with Session() as s:
        q = select(Paper).order_by(Paper.published_at.desc().nulls_last()).limit(limit)
        if source:
            q = q.where(Paper.source == source)
        if status:
            q = q.where(Paper.triage_status == status)
        rows = list(s.scalars(q))
    table = Table(title=f"papers (limit {limit})")
    table.add_column("id", justify="right")
    table.add_column("source")
    table.add_column("status")
    table.add_column("published")
    table.add_column("title")
    for p in rows:
        table.add_row(
            str(p.id),
            p.source,
            p.triage_status,
            (p.published_at.isoformat()[:10] if p.published_at else ""),
            (p.title or "")[:80],
        )
    rprint(table)


@app.command("critique")
def cmd_critique(
    paper_id: str = typer.Option(None, help="single paper id; default = all"),
    model: str = typer.Option(None, help="LLM model alias (provider-specific)"),
):
    """Run the CRITIC agent on ReplicationReports -> data/critique_runs/."""
    from pathlib import Path as _P
    from .agent import critic
    if paper_id:
        report = critic.critique_report(_P("data/replications") / f"{paper_id}.json", model=model)
        out = critic.write_critique(report)
        rprint(f"[green]wrote[/green] {out}")
        rprint(f"  alignment_score={report.north_star_alignment_score} "
               f"L={report.asymmetric_loss:.3f} findings={len(report.findings)}")
    else:
        written = critic.critique_all(model=model)
        rprint(f"[green]critiqued {len(written)} reports[/green]")
        for p in written[-5:]:
            rprint(f"  {p}")


@app.command("actor-propose")
def cmd_actor_propose(
    apply_changes: bool = typer.Option(False, "--apply",
        help="apply proposed changes to meta/actor.md (default: propose only)"),
    critique_limit: int = typer.Option(20, help="max recent critiques to consider"),
):
    """Generate actor.md calibration proposal from recent CRITIC findings."""
    from .agent import actor_self_edit
    proposal = actor_self_edit.propose(critique_limit=critique_limit)
    out = actor_self_edit.write_proposal(proposal)
    rprint(f"[green]proposal written[/green] {out}")
    n = len(proposal.get("proposed_changes", []))
    rprint(f"  {n} changes proposed")
    if apply_changes and n > 0:
        applied = actor_self_edit.apply_proposal(proposal)
        if applied:
            rprint("[yellow]applied to meta/actor.md, review + commit manually[/yellow]")
        else:
            rprint("[red]apply failed[/red]")


@app.command("learn")
def cmd_learn(
    since_days: int = typer.Option(90, help="window for git-log + metrics analysis"),
):
    """Run LEARN aggregator -> data/learn_runs/{date}_{attribution,proposal}."""
    from .agent import learn_aggregator
    art = learn_aggregator.aggregate(since_days=since_days, write=True)
    rprint(f"[green]learn run complete[/green]")
    rprint(f"  actor commits analyzed:    {art['actor_commits_analyzed']}")
    rprint(f"  critique commits analyzed: {art['critique_commits_analyzed']}")
    rprint(f"  metric snapshots:          {art['metric_snapshots_available']}")
    rprint(f"  rules attributed:          {len(art['rule_attribution'])}")
    rprint(f"  summary: {art['summary']}")


@app.command("loop")
def cmd_loop(
    skip_poll: bool = typer.Option(False, "--skip-poll", help="skip source polling"),
    triage_limit: int = typer.Option(20, help="max papers to triage this iteration"),
    replicate_limit: int = typer.Option(5, help="max new tradable papers to replicate"),
    run_learn: bool = typer.Option(False, "--learn", help="also run LEARN aggregator (weekly)"),
    auto_apply: bool = typer.Option(False, "--auto-apply",
        help="apply actor proposals to meta/actor.md (default: propose only)"),
):
    """Run one full autonomous loop: poll -> triage -> replicate -> critique -> propose."""
    from .agent import loop as loop_mod
    result = loop_mod.run(
        skip_poll=skip_poll,
        triage_limit=triage_limit,
        replicate_limit=replicate_limit,
        run_learn=run_learn,
        auto_apply_actor=auto_apply,
    )
    print(loop_mod.render_summary(result))


if __name__ == "__main__":
    app()
