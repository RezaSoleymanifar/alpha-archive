"""Generate docs/index.html — a browsable index of replicated finance papers.

Papers With Code for finance. It is an index, not an essay: cards you can scan,
filter and search, with the numbers on the card and the reasoning behind a
disclosure triangle. Anything that reads like a methodology lecture belongs in
docs/methodology.md, not on the front page.

Entries come from JSON in data/replications/, so running a paper and rerunning
this adds it. No figure is retyped by hand.

    uv run python tools/build_site.py
"""

from __future__ import annotations

import glob
import html
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import thumb

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO = "https://github.com/RezaSoleymanifar/alpha-archive"

PAPERS = {
    "Mom12m": {
        "id": "AA-0001",
        "title": "Returns to Buying Winners and Selling Losers: "
                 "Implications for Stock Market Efficiency",
        "authors": "Jegadeesh, Titman",
        "venue": "Journal of Finance",
        "year": 1993,
        "tags": ["momentum", "cross-sectional", "equities"],
        "claim": "Past winners keep winning: about 1.3% a month over 1964–1989.",
        "finding": "We measure −0.12%/mo on currently-listed large caps since 2006, but the "
                   "reference factor is flat over that window too, so this is decay rather "
                   "than refutation. Not verified — the parity fixture is unobtainable.",
        "paper_url": "https://doi.org/10.1111/j.1540-6261.1993.tb04702.x",
        "impl_url": f"{REPO}/blob/main/alpha_archive/replications/jt1993.py",
        "run_cmd": "python -m alpha_archive.replications.jt1993",
    },
    "Darmanin2026": {
        "id": "AA-0002",
        "title": "Retail Trader's Ruin: An Anatomy of Popular Signal Failure",
        "authors": "Darmanin",
        "venue": "arXiv:2607.20093",
        "year": 2026,
        "tags": ["technical-analysis", "market-timing", "multiple-testing"],
        "claim": "None of the five most popular retail signals beats buy-and-hold.",
        "finding": "We reproduce the golden/death cross result exactly. Sell-in-May matches on "
                   "the statistical gate and differs on the economic one, where the paper "
                   "searches a battery of calendar rules and we run the canonical one.",
        "paper_url": "https://arxiv.org/abs/2607.20093",
        "impl_url": f"{REPO}/blob/main/alpha_archive/replications/darmanin2026.py",
        "run_cmd": "python -m alpha_archive.replications.darmanin2026",
    },
}


def load() -> list[dict]:
    out = []
    for path in sorted(glob.glob(os.path.join(ROOT, "data", "replications", "*.json"))):
        with open(path, encoding="utf-8") as fh:
            try:
                rec = json.load(fh)
            except json.JSONDecodeError:
                continue
        if rec.get("paper") in PAPERS:
            out.append(rec)
    order = {k: i for i, k in enumerate(PAPERS)}
    return sorted(out, key=lambda r: order.get(r["paper"], 99))


def status_of(rec: dict) -> tuple[str, str]:
    """One word on the card. What happened when we ran it."""
    if "families" in rec:
        fams = rec["families"]
        ok = sum(1 for f in fams
                 if f["sharpe_gate"] == f["paper_sharpe_gate"]
                 and f["cagr_gate"] == f["paper_cagr_gate"]
                 and f["sharpe_ci_overlaps"] and f["cagr_ci_overlaps"])
        if ok == len(fams):
            return "reproduced", "ok"
        return ("partial", "warn") if ok else ("differs", "bad")
    status = rec.get("verification", {}).get("status", "")
    return ("reproduced", "ok") if status == "VERIFIED" else ("unverified", "warn")


def metrics(rec: dict) -> str:
    """The numbers, on the card, without a click."""
    if "families" in rec:
        cells = []
        for f in rec["families"]:
            ok = (f["sharpe_gate"] == f["paper_sharpe_gate"]
                  and f["cagr_gate"] == f["paper_cagr_gate"]
                  and f["sharpe_ci_overlaps"] and f["cagr_ci_overlaps"])
            cells.append(
                f'<div class="m"><span class="k">{html.escape(f["label"])}</span>'
                f'<span class="v">{f["paper_sharpe_gate"].lower()}</span>'
                f'<span class="s {"ok" if ok else "bad"}">'
                f'{"matched" if ok else "differs"}</span></div>'
            )
        return "".join(cells)
    return (
        f'<div class="m"><span class="k">paper</span>'
        f'<span class="v">{rec["claimed_monthly_pct"]}%/mo</span>'
        f'<span class="s">t {rec["claimed_t_stat"]}</span></div>'
        f'<div class="m"><span class="k">ours</span>'
        f'<span class="v neg">{rec["measured_monthly_pct"]}%/mo</span>'
        f'<span class="s">t {rec["measured_t_stat"]}</span></div>'
        f'<div class="m"><span class="k">sample</span>'
        f'<span class="v">{rec["months"]} mo</span>'
        f'<span class="s">{rec["universe_size"]} names</span></div>'
    )


def detail(rec: dict) -> str:
    e = html.escape
    if "families" in rec:
        rows = "".join(
            f"<tr><td>{e(f['label'])}<div class='sub'>{e(f['symbol'])} · "
            f"{f['obs']:,} obs (paper {f['paper_obs']:,})</div></td>"
            f"<td class='n'>[{f['paper_sharpe_ci'][0]:.3f}, {f['paper_sharpe_ci'][1]:.3f}]"
            f"<div class='sub'>{e(f['paper_sharpe_gate'].lower())}</div></td>"
            f"<td class='n'>[{f['sharpe_ci'][0]:.3f}, {f['sharpe_ci'][1]:.3f}]"
            f"<div class='sub'>{e(f['sharpe_gate'].lower())}</div></td>"
            f"<td class='n'>[{f['paper_cagr_ci'][0]:.3f}, {f['paper_cagr_ci'][1]:.3f}]</td>"
            f"<td class='n'>[{f['cagr_ci'][0]:.3f}, {f['cagr_ci'][1]:.3f}]</td></tr>"
            for f in rec["families"]
        )
        perts = "".join(
            f"<tr><td>{e(f['label'])}</td><td>" + " · ".join(
                f"<code>{e(p['params'])}</code> {p['sharpe_gap']:+.3f}"
                for p in f["perturbations"]) + "</td></tr>"
            for f in rec["families"] if f.get("perturbations")
        )
        notes = "".join(f"<li>{e(n)}</li>"
                        for f in rec["families"] for n in f.get("notes", []))
        skipped = "".join(f"<li>{e(x)}</li>" for x in rec.get("not_attempted", []))
        return f"""
      <table><thead><tr><th rowspan="2">Family</th>
        <th colspan="2" class="n">Sharpe gap, 95% CI</th>
        <th colspan="2" class="n">CAGR gap, 95% CI</th></tr>
        <tr><th class="n">paper</th><th class="n">ours</th>
            <th class="n">paper</th><th class="n">ours</th></tr></thead>
        <tbody>{rows}</tbody></table>
      <p class="fine">Reproduced means the verdict matches <em>and</em> the intervals overlap,
      on both gates. Thresholds are the paper's: δ<sub>S</sub>={rec['delta_sharpe']},
      δ<sub>R</sub>={rec['delta_cagr']}. Costs {rec['cost_bps_per_leg']}bps/leg. Stationary
      bootstrap, {rec['bootstrap']['draws']:,} draws, mean block {rec['bootstrap']['mean_block']}.</p>
      <h4>Parameter sensitivity</h4>
      <table class="plain"><tbody>{perts}</tbody></table>
      {'<h4>Where we differ</h4><ul>' + notes + '</ul>' if notes else ''}
      <h4>Not attempted</h4><ul>{skipped}</ul>"""

    v = rec.get("verification", {})
    crit = v.get("criterion", {})
    eras = "".join(
        f"<tr><td>{e(k)}</td><td class='n'>{x['mean_monthly_pct']:+.3f}%</td>"
        f"<td class='n'>{x['t_stat']:+.2f}</td><td class='n sub'>{x['months']}</td></tr>"
        for k, x in rec.get("umd_by_era", {}).items()
    )
    caveats = "".join(f"<li>{e(c)}</li>" for c in rec.get("caveats", []))
    return f"""
      <h4>Verification — {e(v.get('status', '?').lower().replace('_', ' '))}</h4>
      <p>{e(v.get('reason', ''))}</p>
      <p class="fine">Bar: {e(str(crit.get('statistic', '')))} ≥ {crit.get('threshold', '')},
      against {e(str(crit.get('fixture', '')))} — declared by
      {e(str(crit.get('fixture_source', '')))}, not by us.</p>
      <h4>Reference factor by era</h4>
      <table><thead><tr><th>Ken French UMD</th><th class="n">mean</th><th class="n">t</th>
      <th class="n">months</th></tr></thead><tbody>{eras}</tbody></table>
      <h4>Sample limits</h4><ul>{caveats}</ul>"""


def card(rec: dict) -> str:
    e = html.escape
    m = PAPERS[rec["paper"]]
    label, cls = status_of(rec)
    tags = "".join(f'<a class="tag" href="#" data-tag="{e(t)}">{e(t)}</a>' for t in m["tags"])
    search = " ".join([m["title"], m["authors"], m["venue"], *m["tags"], label]).lower()

    return f"""
  <article class="card" data-status="{cls}" data-search="{e(search)}" id="{e(rec['paper'].lower())}">
    <div class="fig">{thumb.for_record(rec)}</div>

    <div class="mid">
      <h2><a href="{m['paper_url']}">{e(m['title'])}</a></h2>
      <p class="abs">{e(m['claim'])} {e(m['finding'])}</p>
      <p class="meta">
        <span class="org">{e(m['venue'])}</span>
        <span class="dot">·</span>{e(m['authors'])}
        <span class="dot">·</span>Published {m['year']}
      </p>
      <p class="tagrow">{tags}</p>
      <details><summary>Full result</summary>{detail(rec)}</details>
    </div>

    <div class="acts">
      <span class="act status {cls}">{e(label)}</span>
      <a class="act" href="{m['impl_url']}">Code</a>
      <a class="act" href="{m['paper_url']}">Paper</a>
    </div>
  </article>"""


PAGE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Alpha Archive — finance papers with code, actually run</title>
<meta name="description" content="An index of finance papers re-implemented and re-run on point-in-time data. Each entry shows what the paper claimed, what we measured, and whether it reproduced.">
<meta property="og:title" content="Alpha Archive">
<meta property="og:description" content="Finance papers with code, actually run.">
<link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'><rect width='32' height='32' rx='5' fill='%23111'/><path d='M8 23 L16 9 L24 23' stroke='%23fff' stroke-width='2.6' fill='none' stroke-linecap='round' stroke-linejoin='round'/><path d='M11.6 18.4 H20.4' stroke='%23fff' stroke-width='2.6' stroke-linecap='round'/></svg>">
<style>
:root{--bg:#f6f7f9;--card:#fff;--ink:#111418;--soft:#61707e;--line:#e3e7eb;
  --ok:#0f7a45;--okbg:#e8f6ee;--warn:#8a5b00;--warnbg:#fdf5e6;--bad:#a5231a;--badbg:#fdeeec;
  --link:#0b5fd0;
  --sans:-apple-system,BlinkMacSystemFont,"Segoe UI",Inter,Roboto,Helvetica,Arial,sans-serif;
  --mono:ui-monospace,"SF Mono","Cascadia Mono",Menlo,Consolas,monospace}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font-family:var(--sans);font-size:15px;
  line-height:1.55;-webkit-font-smoothing:antialiased}
a{color:var(--link);text-decoration:none}
a:hover{text-decoration:underline}
.wrap{max-width:1000px;margin:0 auto;padding:0 20px}

header.site{background:var(--card);border-bottom:1px solid var(--line);position:sticky;top:0;z-index:5}
.bar{display:flex;align-items:center;gap:16px;padding:13px 0;flex-wrap:wrap}
.logo{font-weight:700;font-size:17px;letter-spacing:-.01em;color:var(--ink);white-space:nowrap}
.logo span{color:var(--soft);font-weight:400;font-size:13px;margin-left:8px}
#q{flex:1;min-width:180px;font:inherit;font-size:14px;padding:7px 12px;border:1px solid var(--line);
  border-radius:6px;background:#fbfcfd}
#q:focus{outline:2px solid #cfe0f8;border-color:#8fb6ec}
.filters{display:flex;gap:6px;flex-wrap:wrap}
.f{font-size:12.5px;padding:5px 11px;border:1px solid var(--line);border-radius:20px;
  background:#fbfcfd;color:var(--soft);cursor:pointer}
.f.on{background:var(--ink);border-color:var(--ink);color:#fff}

.count{color:var(--soft);font-size:13px;padding:18px 0 10px}

/* Card: figure left, text centre, actions right — the reference layout. */
.card{background:var(--card);border:1px solid var(--line);border-radius:10px;
  padding:16px;margin-bottom:14px;display:grid;gap:18px;grid-template-columns:1fr}
@media(min-width:760px){.card{grid-template-columns:240px 1fr 152px}}
.fig{border:1px solid var(--line);border-radius:6px;overflow:hidden;background:#fff;
  align-self:start;line-height:0}
.fig svg{width:100%;height:auto;display:block}

.mid{min-width:0}
.card h2{font-size:19px;line-height:1.32;margin:0 0 8px;font-weight:650;letter-spacing:-.01em}
.card h2 a{color:var(--ink)}
.abs{margin:0 0 10px;font-size:14.5px;line-height:1.55;color:#3d4750}
.meta{margin:0 0 10px;font-size:13px;color:var(--soft);display:flex;align-items:center;
  gap:7px;flex-wrap:wrap}
.org{background:#eef1f4;border-radius:5px;padding:2px 8px;font-size:12px;
  font-weight:600;color:#3d4750}
.dot{color:#c3ccd4}
.tagrow{margin:0;display:flex;gap:6px;flex-wrap:wrap}
.tag{font-size:11.5px;color:var(--soft);background:#eef1f4;border-radius:4px;padding:3px 8px}
.tag:hover{background:#e2e7ec;text-decoration:none}

.acts{display:flex;flex-direction:column;gap:8px;align-self:start}
.act{display:flex;align-items:center;justify-content:center;gap:6px;font-size:13px;
  font-weight:600;border:1px solid var(--line);border-radius:7px;padding:7px 12px;
  color:var(--ink);background:#fff;white-space:nowrap}
a.act:hover{background:#f2f5f8;text-decoration:none}
.act.status{cursor:default}
.act.status.ok{color:var(--ok);background:var(--okbg);border-color:#bfe3ce}
.act.status.warn{color:var(--warn);background:var(--warnbg);border-color:#eddcb6}
.act.status.bad{color:var(--bad);background:var(--badbg);border-color:#eec7c2}

.empty{padding:36px 0;color:var(--soft);text-align:center}
footer{color:var(--soft);font-size:12.5px;padding:26px 0 56px;line-height:1.7}
footer a{margin-right:16px}
</style>
</head>
<body>

<header class="site"><div class="wrap"><div class="bar">
  <span class="logo">Alpha Archive<span>finance papers with code, actually run</span></span>
  <input id="q" type="search" placeholder="Search papers, authors, tags…" autocomplete="off">
  <div class="filters">
    <button class="f on" data-f="all">All</button>
    <button class="f" data-f="ok">Reproduced</button>
    <button class="f" data-f="warn">Unresolved</button>
    <button class="f" data-f="bad">Differs</button>
  </div>
</div></div></header>

<div class="wrap">
  <p class="count" id="count"></p>
  <div id="list">__CARDS__</div>
  <p class="empty" id="empty" hidden>No papers match.</p>
  <footer>
    <a href="__REPO__">GitHub</a>
    <a href="__REPO__/blob/main/docs/methodology.md">Methodology</a>
    <a href="https://github.com/RezaSoleymanifar/vintage">Vintage</a>
    <a href="https://www.openassetpricing.com/">Open Source Asset Pricing</a>
    <p>MIT licensed. No data redistributed, no paper text reproduced. Not affiliated with
    arXiv, Papers with Code, or any cited author. Not investment advice.</p>
  </footer>
</div>

<script>
var cards = [].slice.call(document.querySelectorAll('.card'));
var q = document.getElementById('q'), count = document.getElementById('count'),
    empty = document.getElementById('empty'), filter = 'all';

function apply() {
  var term = q.value.trim().toLowerCase(), shown = 0;
  cards.forEach(function (c) {
    var okStatus = filter === 'all' || c.dataset.status === filter;
    var okTerm = !term || c.dataset.search.indexOf(term) !== -1;
    var show = okStatus && okTerm;
    c.hidden = !show;
    if (show) shown++;
  });
  count.textContent = shown + (shown === 1 ? ' paper' : ' papers');
  empty.hidden = shown > 0;
}

q.addEventListener('input', apply);
document.querySelectorAll('.f').forEach(function (b) {
  b.addEventListener('click', function () {
    document.querySelectorAll('.f').forEach(function (x) { x.classList.remove('on'); });
    b.classList.add('on');
    filter = b.dataset.f;
    apply();
  });
});
document.querySelectorAll('.tag').forEach(function (t) {
  t.addEventListener('click', function (e) {
    e.preventDefault();
    q.value = t.dataset.tag;
    apply();
  });
});
apply();
</script>
</body>
</html>
"""


def main() -> None:
    records = load()
    if not records:
        raise SystemExit("no replication records in data/replications/")
    page = PAGE.replace("__CARDS__", "\n".join(card(r) for r in records)) \
               .replace("__REPO__", REPO)
    out_dir = os.path.join(ROOT, "docs")
    os.makedirs(out_dir, exist_ok=True)
    out = os.path.join(out_dir, "index.html")
    with open(out, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(page)
    print(f"wrote {out} ({len(page):,} bytes, {len(records)} papers)")


if __name__ == "__main__":
    main()
