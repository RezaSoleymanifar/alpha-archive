"""Generate docs/index.html for Alpha Archive.

Papers With Code, for finance — with the part they never did. They index a
paper and link its repository. We run the code and report whether the claim
survives, on data anyone can fetch, with the bar written down first.

Data-driven: entries come from JSON in data/replications/, so running a paper
and rerunning this adds it. No result is retyped by hand — a replication site
that hand-copies its own numbers has the same credibility problem as a backtest
that hand-picks its sample.

The look is a journal, not an arcade: white page, serif titles, hairline rules,
booktabs tables. Quant research is read by people who read journals, and a
neon terminal reads as a toy no matter how good the statistics underneath are.

    uv run python tools/build_site.py
"""

from __future__ import annotations

import glob
import html
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO = "https://github.com/RezaSoleymanifar/alpha-archive"

# Metadata that does not belong in a result record.
PAPERS = {
    "Mom12m": {
        "id": "AA-0001",
        "title": "Returns to Buying Winners and Selling Losers: "
                 "Implications for Stock Market Efficiency",
        "authors": "Narasimhan Jegadeesh, Sheridan Titman",
        "venue": "The Journal of Finance, 48(1), 65–91",
        "year": 1993,
        "tags": ["cross-sectional", "momentum", "equities"],
        "paper_url": "https://doi.org/10.1111/j.1540-6261.1993.tb04702.x",
        "impl_url": f"{REPO}/blob/main/alpha_archive/replications/jt1993.py",
        "run_cmd": "uv run python -m alpha_archive.replications.jt1993",
        "claim": "Buying past winners and selling past losers earns about 1.3% a month, "
                 "and the effect is large enough that markets cannot be fully efficient.",
        "summary": "Rank stocks on the return from twelve months ago to one month ago, "
                   "buy the top decile and sell the bottom, hold three months. Reported "
                   "about 1.3% per month over 1964–1989 and became one of the most cited "
                   "results in finance.",
    },
    "Darmanin2026": {
        "id": "AA-0002",
        "title": "Retail Trader's Ruin: An Anatomy of Popular Signal Failure",
        "authors": "Adam Darmanin",
        "venue": "arXiv:2607.20093 [q-fin.ST]",
        "year": 2026,
        "tags": ["technical-analysis", "market-timing", "multiple-testing"],
        "paper_url": "https://arxiv.org/abs/2607.20093",
        "impl_url": f"{REPO}/blob/main/alpha_archive/replications/darmanin2026.py",
        "run_cmd": "uv run python -m alpha_archive.replications.darmanin2026",
        "claim": "None of the five most popular retail trading signals delivers a usable "
                 "edge. Moving-average crosses, RSI, candlestick patterns, volume indicators "
                 "and Sell-in-May: four are refuted outright, two cannot be resolved, and "
                 "not one is supported once costs and multiple testing are accounted for.",
        "summary": "Tests five widely promoted retail signal families against three "
                   "predeclared gates: statistical edge after multiplicity correction, "
                   "economic viability after costs, and survival under leverage. Reports "
                   "four refuted, two inconclusive, none supported.",
    },
}

TONE = {
    "REPLICATED": ("replicated", "ok"),
    "DIVERGES": ("diverges", "bad"),
    "UNVERIFIED": ("unverified", "warn"),
    "FIXTURE_UNAVAILABLE": ("fixture unavailable", "warn"),
}


def _tone(text: str) -> tuple[str, str]:
    upper = (text or "").upper()
    for key, pair in TONE.items():
        if upper.startswith(key):
            return pair
    if "GATES MATCH" in upper:
        return ("partial", "warn")
    return ("unresolved", "warn")


# ------------------------------------------------------------------- loading


def load_records() -> list[dict]:
    """Normalize both record shapes into one list of renderable entries."""
    out = []
    for path in sorted(glob.glob(os.path.join(ROOT, "data", "replications", "*.json"))):
        with open(path, encoding="utf-8") as fh:
            try:
                rec = json.load(fh)
            except json.JSONDecodeError:
                continue
        key = rec.get("paper")
        if key not in PAPERS:
            continue
        if "families" in rec:
            out.append({"kind": "families", "key": key, "rec": rec})
        elif "measured_monthly_pct" in rec:
            out.append({"kind": "single", "key": key, "rec": rec})
    order = {k: i for i, k in enumerate(PAPERS)}
    return sorted(out, key=lambda e: order.get(e["key"], 99))


# ----------------------------------------------------------------- rendering


def _head(key: str, status_label: str, status_cls: str, extra: str = "") -> str:
    e, m = html.escape, PAPERS[key]
    tags = "".join(f'<span class="tag">{e(t)}</span>' for t in m["tags"])
    return f"""
    <header class="phead">
      <div class="pmeta">
        <span class="pid">{m['id']}</span>
        <span class="status {status_cls}">{e(status_label)}</span>
        {extra}
      </div>
      <h3><a href="{m['paper_url']}">{e(m['title'])}</a></h3>
      <p class="authors">{e(m['authors'])}</p>
      <p class="venue">{e(m['venue'])}</p>
      <p class="claim"><b>The claim.</b> {e(m['claim'])}</p>
      <p class="summary">{e(m['summary'])}</p>
      <p class="tags">{tags}</p>
      <p class="actions">
        <a class="btn" href="{m['paper_url']}">Paper</a>
        <a class="btn" href="{m['impl_url']}">Code</a>
        <code>{e(m['run_cmd'])}</code>
      </p>
    </header>"""


def render_single(rec: dict) -> str:
    """A record with one measured statistic — the JT-1993 shape."""
    e = html.escape
    key = rec["paper"]
    v = rec.get("verification", {})
    label, cls = _tone(v.get("status", rec.get("verdict", "")))

    eras = "".join(
        f"<tr><td>{e(k)}</td><td class='n'>{x['mean_monthly_pct']:+.3f}%</td>"
        f"<td class='n'>{x['t_stat']:+.2f}</td><td class='n muted'>{x['months']}</td></tr>"
        for k, x in rec.get("umd_by_era", {}).items()
    )
    caveats = "".join(f"<li>{e(c)}</li>" for c in rec.get("caveats", []))
    crit = v.get("criterion", {})

    return f"""
  <article class="paper" id="{e(key.lower())}">
    {_head(key, label, cls)}
    <table class="results">
      <thead><tr><th>Quantity</th><th class="n">Paper</th><th class="n">Ours</th>
      <th class="n">Difference</th></tr></thead>
      <tbody>
        <tr><td>Mean monthly return</td>
          <td class="n">{rec['claimed_monthly_pct']}%</td>
          <td class="n">{rec['measured_monthly_pct']}%</td>
          <td class="n neg">{rec['gap_monthly_pct']}%</td></tr>
        <tr><td><i>t</i>-statistic</td>
          <td class="n">{rec['claimed_t_stat']}</td>
          <td class="n">{rec['measured_t_stat']}</td><td class="n muted">—</td></tr>
        <tr><td>Sample</td>
          <td class="n">{e(rec['claimed_sample'])}</td>
          <td class="n">{e(rec['measured_sample'])}</td>
          <td class="n muted">{rec['months']} mo</td></tr>
      </tbody>
    </table>

    <div class="verify {cls}">
      <b>Verification — {e(v.get('status', 'UNKNOWN'))}</b>
      <p>{e(v.get('reason', ''))}</p>
      <dl>
        <dt>Criterion</dt><dd>{e(str(crit.get('statistic', '')))} ≥ {crit.get('threshold', '')}</dd>
        <dt>Fixture</dt><dd>{e(str(crit.get('fixture', '')))}</dd>
        <dt>Declared by</dt><dd>{e(str(crit.get('fixture_source', '')))}, not by us</dd>
      </dl>
    </div>

    <details><summary>Is it us, or did the effect decay?</summary>
      <p class="note">Before blaming a paper, check whether the published factor still works.
      If the reference factor is flat over the same window, a weak result here agrees with the
      literature rather than refuting the paper.</p>
      <table class="results"><thead><tr><th>Ken French UMD</th><th class="n">Mean</th>
      <th class="n"><i>t</i></th><th class="n">Months</th></tr></thead>
      <tbody>{eras}</tbody></table>
    </details>
    <details><summary>What this sample cannot tell you</summary>
      <ul class="caveats">{caveats}</ul></details>
  </article>"""


def render_families(rec: dict) -> str:
    """A record with one row per tested family — the Darmanin shape."""
    e = html.escape
    key = rec["paper"]
    fams = rec.get("families", [])
    replicated = sum(1 for f in fams if f["verdict"].startswith("REPLICATED"))
    label, cls = ("replicated", "ok") if replicated == len(fams) and fams else \
                 ("partial", "warn") if replicated else ("diverges", "bad")
    extra = f'<span class="count">{replicated}/{len(fams)} families reproduced</span>'

    def match_cell(f):
        """Judge both gates. Reporting only the statistical one would have shown
        Sell-in-May as reproduced while its card-level verdict said otherwise."""
        checks = [
            ("statistical", f["sharpe_gate"] == f["paper_sharpe_gate"], f["sharpe_ci_overlaps"]),
            ("economic", f["cagr_gate"] == f["paper_cagr_gate"], f["cagr_ci_overlaps"]),
        ]
        failed = [name for name, same, _ in checks if not same]
        if not failed and all(ov for _, _, ov in checks):
            return "<span class='status ok'>reproduced</span>"
        if not failed:
            return ("<span class='status warn'>gates agree</span>"
                    "<br><span class='muted'>interval does not overlap</span>")
        return (f"<span class='status bad'>differs</span>"
                f"<br><span class='muted'>on the {failed[0]} gate</span>")

    rows = "".join(
        f"<tr><td>{e(f['label'])}<br><span class='muted'>{e(f['symbol'])}, "
        f"{f['obs']:,} obs (paper {f['paper_obs']:,})</span></td>"
        f"<td class='n'>[{f['paper_sharpe_ci'][0]:.3f}, {f['paper_sharpe_ci'][1]:.3f}]<br>"
        f"<span class='muted'>{e(f['paper_sharpe_gate'])}</span></td>"
        f"<td class='n'>[{f['sharpe_ci'][0]:.3f}, {f['sharpe_ci'][1]:.3f}]<br>"
        f"<span class='muted'>{e(f['sharpe_gate'])}</span></td>"
        f"<td class='n'>{match_cell(f)}</td></tr>"
        for f in fams
    )
    perts = "".join(
        f"<tr><td>{e(f['label'])}</td><td>" + ", ".join(
            f"<code>{e(p['params'])}</code> {p['sharpe_gap']:+.3f}" for p in f["perturbations"]
        ) + "</td></tr>" for f in fams if f.get("perturbations")
    )
    placebo = "".join(
        f"<tr><td>{e(f['label'])}</td><td class='n'>{f['placebo']['mean_sharpe_gap']:+.3f}</td>"
        f"<td class='n'>{f['placebo']['max_abs_sharpe_gap']:.3f}</td>"
        f"<td class='n muted'>{f['placebo']['runs']}</td></tr>"
        for f in fams if f.get("placebo")
    )
    skipped = "".join(f"<li>{e(x)}</li>" for x in rec.get("not_attempted", []))

    return f"""
  <article class="paper" id="{e(key.lower())}">
    {_head(key, label, cls, extra)}
    <table class="results">
      <caption><b>Two separate questions.</b> The middle columns show the paper's
      <i>statistical</i> gate and ours. That answers <i>does the rule work</i>, where
      "inconclusive" is a legitimate finding rather than a failure. The last column answers
      <i>did we reproduce their answer</i>, and reproducing an inconclusive result counts as
      a success.<br><br>
      <b>Why ranges rather than numbers.</b> Neither side reports a single figure. Each
      reports an interval the true value probably sits in. A family counts as reproduced
      only when the verdicts match <i>and</i> the intervals share ground, on both the
      statistical and the economic gate. Two people can reach the same verdict from
      different numbers; if the intervals never touch, we computed different things and the
      agreement was luck.</caption>
      <thead><tr><th>Family</th><th class="n">Paper, statistical gate</th>
      <th class="n">Ours</th><th class="n">Both gates reproduced?</th></tr></thead>
      <tbody>{rows}</tbody>
    </table>
    <p class="note">Thresholds are the paper's own: a family is refuted when the interval's
    upper bound falls below δ<sub>S</sub> = {rec['delta_sharpe']}, never on bare
    non-significance. Costs are {rec['cost_bps_per_leg']} bps per leg. Intervals come from a
    stationary bootstrap, {rec['bootstrap']['draws']:,} draws, mean block
    {rec['bootstrap']['mean_block']} days.</p>

    <details open><summary>Did the authors' parameter choices carry the result?</summary>
      <p class="note">Every rule embeds free choices. Re-running across them shows whether a
      finding lives only at the parameters that were reported.</p>
      <table class="results"><tbody>{perts}</tbody></table></details>

    <details><summary>Placebo: the same machinery on coin flips</summary>
      <p class="note">Random signals pushed through the identical pipeline. Whatever appears
      here is manufactured by the method, not found in the market.</p>
      <table class="results"><thead><tr><th>Family</th><th class="n">Mean gap</th>
      <th class="n">Max |gap|</th><th class="n">Runs</th></tr></thead>
      <tbody>{placebo}</tbody></table></details>

    <details><summary>Not attempted</summary><ul class="caveats">{skipped}</ul></details>
  </article>"""


PAGE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Alpha Archive — finance papers, with code that we actually run</title>
<meta name="description" content="Papers with code, for finance. Published trading signals re-implemented on point-in-time data with costs charged, judged against a bar declared before the run.">
<meta property="og:title" content="Alpha Archive — finance papers, with code that we actually run">
<meta property="og:description" content="Papers with code, for finance. We run the code and report whether the claim survives.">
<meta property="og:type" content="website">
<link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'><rect width='32' height='32' rx='5' fill='%23111'/><path d='M8 23 L16 9 L24 23' stroke='%23fff' stroke-width='2.6' fill='none' stroke-linecap='round' stroke-linejoin='round'/><path d='M11.6 18.4 H20.4' stroke='%23fff' stroke-width='2.6' stroke-linecap='round'/></svg>">
<style>
:root{
  --page:#f7f7f5; --card:#ffffff; --ink:#16191d; --soft:#5b6570; --rule:#e0e2e0;
  --hair:#c9ccc9; --ok:#136f42; --warn:#8a5a00; --bad:#a02219; --link:#0b4f9e;
  --serif:"Iowan Old Style","Palatino Linotype",Palatino,Georgia,"Times New Roman",serif;
  --sans:-apple-system,BlinkMacSystemFont,"Segoe UI",Inter,Helvetica,Arial,sans-serif;
  --mono:ui-monospace,"SF Mono","Cascadia Mono",Menlo,Consolas,monospace;
}
*{box-sizing:border-box}
body{margin:0;background:var(--page);color:var(--ink);font-family:var(--sans);
  font-size:16px;line-height:1.6;-webkit-font-smoothing:antialiased}
.wrap{max-width:940px;margin:0 auto;padding:0 22px}
a{color:var(--link);text-decoration:none}
a:hover{text-decoration:underline}

.masthead{border-bottom:1px solid var(--hair);padding:44px 0 26px}
h1{font-family:var(--serif);font-size:clamp(30px,5vw,44px);margin:0 0 4px;
  letter-spacing:-.01em;font-weight:600}
.kicker{font-size:11px;letter-spacing:.22em;text-transform:uppercase;color:var(--soft);
  margin:0 0 14px}
.lede{font-family:var(--serif);font-size:clamp(17px,2.5vw,21px);line-height:1.5;
  margin:0 0 14px;max-width:36em}
.sub{color:var(--soft);font-size:14.5px;max-width:44em;margin:0 0 8px;line-height:1.68}

h2{font-size:11px;letter-spacing:.22em;text-transform:uppercase;color:var(--soft);
  margin:44px 0 14px;font-weight:600;padding-bottom:7px;border-bottom:1px solid var(--rule)}

.paper{background:var(--card);border:1px solid var(--rule);border-radius:6px;
  padding:26px 28px;margin-bottom:20px}
.pmeta{display:flex;align-items:center;gap:11px;flex-wrap:wrap;margin-bottom:11px}
.pid{font-family:var(--mono);font-size:11.5px;color:var(--soft);letter-spacing:.06em}
.status{font-size:10.5px;letter-spacing:.14em;text-transform:uppercase;font-weight:700;
  padding:3px 9px;border-radius:3px;border:1px solid}
.status.ok{color:var(--ok);border-color:#b7dcc7;background:#eef7f2}
.status.warn{color:var(--warn);border-color:#e6d3a8;background:#fdf7ea}
.status.bad{color:var(--bad);border-color:#e8c0bb;background:#fdf0ee}
.count{font-size:12px;color:var(--soft)}
.paper h3{font-family:var(--serif);font-size:clamp(19px,2.7vw,24px);line-height:1.3;
  margin:0 0 6px;font-weight:600}
.paper h3 a{color:var(--ink)}
.authors{font-family:var(--serif);font-size:16px;margin:0 0 2px}
.venue{color:var(--soft);font-size:13.5px;margin:0 0 12px}
.claim{font-family:var(--serif);font-size:16.5px;line-height:1.58;margin:0 0 12px;
  padding:11px 14px;background:#f4f6f8;border-left:3px solid var(--hair);max-width:56em}
.claim b{font-family:var(--sans);font-size:10.5px;letter-spacing:.14em;
  text-transform:uppercase;color:var(--soft);display:block;margin-bottom:4px}
.summary{font-family:var(--serif);font-size:16px;line-height:1.62;margin:0 0 13px;max-width:56em}
.tags{margin:0 0 14px;display:flex;gap:7px;flex-wrap:wrap}
.tag{font-size:11px;color:var(--soft);border:1px solid var(--rule);border-radius:3px;
  padding:2px 8px;background:#fafaf8}
.actions{display:flex;align-items:center;gap:10px;flex-wrap:wrap;margin:0 0 4px}
.btn{font-size:13px;font-weight:600;border:1px solid var(--hair);border-radius:4px;
  padding:5px 13px;color:var(--ink);background:#fafaf8}
.btn:hover{background:#f0f0ec;text-decoration:none}
.actions code{font-family:var(--mono);font-size:12px;color:var(--soft)}

table.results{width:100%;border-collapse:collapse;font-size:14px;margin:18px 0 0}
table.results caption{caption-side:top;text-align:left;color:var(--soft);font-size:12.5px;
  line-height:1.65;padding:0 0 14px;max-width:60em}
table.results caption b{color:var(--ink)}
table.results thead th{font-size:11px;letter-spacing:.1em;text-transform:uppercase;
  color:var(--soft);font-weight:600;text-align:left;padding:0 10px 7px;
  border-bottom:1px solid var(--ink)}
table.results tbody td{padding:10px;border-bottom:1px solid var(--rule);vertical-align:top}
table.results tbody tr:last-child td{border-bottom:1px solid var(--ink)}
.n{text-align:right;font-family:var(--mono);font-size:13px;white-space:nowrap}
th.n{text-align:right}
.muted{color:var(--soft);font-weight:400;font-size:12px}
.neg{color:var(--bad)}

.verify{border:1px solid var(--rule);border-left:3px solid var(--hair);border-radius:4px;
  padding:14px 16px;margin-top:18px;background:#fbfbf9}
.verify.warn{border-left-color:#d9b96a}
.verify.bad{border-left-color:#c98079}
.verify.ok{border-left-color:#79b795}
.verify b{display:block;font-size:11px;letter-spacing:.14em;text-transform:uppercase;
  color:var(--soft);margin-bottom:7px}
.verify p{margin:0 0 11px;font-size:13.5px;line-height:1.6}
.verify dl{margin:0;display:grid;grid-template-columns:1fr;gap:1px 16px;font-size:12.5px}
@media(min-width:640px){.verify dl{grid-template-columns:96px 1fr}}
.verify dt{color:var(--soft);font-weight:600}
.verify dd{margin:0 0 6px;line-height:1.55}

details{margin-top:16px;border-top:1px solid var(--rule);padding-top:12px}
summary{cursor:pointer;font-size:13.5px;font-weight:600}
.note{color:var(--soft);font-size:13px;line-height:1.65;margin:10px 0 0;max-width:58em}
.caveats{margin:10px 0 0;padding-left:19px;color:var(--soft);font-size:13px;line-height:1.7}

.how{display:grid;grid-template-columns:1fr;gap:14px}
@media(min-width:720px){.how{grid-template-columns:1fr 1fr 1fr}}
.step{background:var(--card);border:1px solid var(--rule);border-radius:6px;padding:18px}
.step b{display:block;font-size:14px;margin-bottom:7px;font-family:var(--serif)}
.step p{margin:0;color:var(--soft);font-size:13.5px;line-height:1.65}
footer{padding:44px 0 64px;color:var(--soft);font-size:13px;line-height:1.75;
  border-top:1px solid var(--rule);margin-top:44px}
footer .flinks{display:flex;gap:18px;flex-wrap:wrap;margin-bottom:12px}
</style>
</head>
<body>
<div class="wrap">

  <div class="masthead">
    <p class="kicker">Alpha Archive</p>
    <h1>Finance papers, with code that we actually run.</h1>
    <p class="lede">Papers With Code indexes a paper and links its repository. We take the
    next step: re-implement the signal, run it on point-in-time data with costs charged, and
    report whether the claim survives.</p>
    <p class="sub">Roughly two thirds of published anomalies fail to replicate, and almost
    nobody re-checks them. A replication is marked verified only when it clears a threshold
    written down before the run, measured against something we did not produce. If that
    reference cannot be obtained, the status is unverified — not a pass with an asterisk, and
    never a "partially validated" tier. Every figure below is produced by code in the
    repository from data anyone can fetch.</p>
  </div>

  <h2>Replications</h2>
  __ENTRIES__

  <h2>Method</h2>
  <div class="how">
    <div class="step"><b>Declare the bar first</b><p>The criterion is written down before the
    run and frozen. An earlier version of this failed that test: the threshold was set at 0.6
    after 0.9 proved unreachable. Moving a bar to fit a result is the thing this project
    exists to catch.</p></div>
    <div class="step"><b>Perturb what the authors chose</b><p>Every rule embeds free choices —
    lookback, holding period, breakpoints. Re-running across them shows whether a finding lives
    only at the reported parameters. This needs no external reference, which is why it works
    for papers nobody has replicated.</p></div>
    <div class="step"><b>Say what the sample cannot cover</b><p>Free data means survivor-biased
    universes and short accounting history. Those limits are printed with every result, because
    a gap against a claim is often evidence about our sample rather than about the paper.</p></div>
  </div>

  <h2>Built on</h2>
  <div class="how">
    <div class="step"><b>Vintage</b><p>The data layer. Point-in-time prices, filings and factors
    from the SEC, the St. Louis Fed and Dartmouth, each value carrying the date it became public.
    <a href="https://github.com/RezaSoleymanifar/vintage">Repository</a> ·
    <a href="https://rezasoleymanifar.github.io/vintage/">Site</a></p></div>
    <div class="step"><b>Open Source Asset Pricing</b><p>Chen &amp; Zimmermann's documented
    scoreboard of 331 published predictors, with the claimed return and t-statistic for each.
    <a href="https://www.openassetpricing.com/">openassetpricing.com</a></p></div>
    <div class="step"><b>Ken French Data Library</b><p>Dartmouth's published factors, used as a
    reference series when a like-for-like construction exists.</p></div>
  </div>

  <footer>
    <div class="flinks">
      <a href="__REPO__">GitHub</a>
      <a href="__REPO__/blob/main/docs/methodology.md">Methodology</a>
      <a href="https://github.com/RezaSoleymanifar/vintage">Vintage</a>
    </div>
    <p>MIT licensed. Alpha Archive redistributes no data and reproduces no paper text — it
    links to originals and publishes its own code and results. Not affiliated with arXiv,
    Cornell University, Papers With Code, or any cited author. Nothing here is investment
    advice.</p>
  </footer>

</div>
</body>
</html>
"""


def main() -> None:
    records = load_records()
    if not records:
        raise SystemExit("no replication records found in data/replications/")

    entries = "\n".join(
        render_families(e["rec"]) if e["kind"] == "families" else render_single(e["rec"])
        for e in records
    )
    page = PAGE.replace("__ENTRIES__", entries).replace("__REPO__", REPO)

    out_dir = os.path.join(ROOT, "docs")
    os.makedirs(out_dir, exist_ok=True)
    out = os.path.join(out_dir, "index.html")
    with open(out, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(page)
    print(f"wrote {out} ({len(page):,} bytes, {len(records)} paper(s))")


if __name__ == "__main__":
    main()
