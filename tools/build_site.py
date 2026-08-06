"""Generate docs/index.html — an index of finance papers, replicated where we can.

Layout follows the reference (huggingface.co/papers, successor to Papers With
Code): first-page thumbnail flush on the left, title and truncated abstract in
the middle, stacked actions on the right. Dark and light both supported —
the reference follows the reader's system theme, and rendering light against
its dark is most of why a copy reads as a copy.

Two sources feed it. data/replications/*.json are papers we have actually run
and carry results. data/papers/arxiv.json is the recent q-fin listing: those
are queued, carry no results, and every card says so.

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

REPLICATED = {
    "Mom12m": {
        "title": "Returns to Buying Winners and Selling Losers: "
                 "Implications for Stock Market Efficiency",
        "authors": "Narasimhan Jegadeesh, Sheridan Titman",
        "venue": "Journal of Finance",
        "date": "1993",
        "tags": ["momentum", "factors", "equities"],
        "abstract": "Past winners keep winning: buying prior 12-month winners and selling "
                    "losers earned about 1.3% a month over 1964–1989, an effect large enough "
                    "that the authors argue markets cannot be fully efficient. We measure "
                    "−0.12%/mo on currently-listed large caps since 2006 — but the reference "
                    "factor is flat over that window too, so this reads as decay rather than "
                    "refutation. Not verified: the parity fixture is unobtainable.",
        "paper_url": "https://doi.org/10.1111/j.1540-6261.1993.tb04702.x",
        "impl_url": f"{REPO}/blob/main/alpha_archive/replications/jt1993.py",
        "thumb": None,          # publisher PDF is paywalled; generated figure instead
    },
    "Darmanin2026": {
        "title": "Retail Trader's Ruin: An Anatomy of Popular Signal Failure",
        "authors": "Adam Darmanin",
        "venue": "arXiv:2607.20093",
        "date": "2026-07-22",
        "tags": ["technical-analysis", "market-timing", "factors"],
        "abstract": "Tests five widely promoted retail signal families — trend, oscillator, "
                    "candlestick, volume and calendar rules — against three predeclared gates: "
                    "statistical edge after multiplicity correction, economic viability after "
                    "costs, and survival under leverage. Four are refuted, two unresolved, "
                    "none supported. We reproduce the golden/death cross result exactly; "
                    "Sell-in-May matches on the statistical gate and differs on the economic "
                    "one, where the paper searches a battery of calendar rules and we run the "
                    "canonical one.",
        "paper_url": "https://arxiv.org/abs/2607.20093",
        "impl_url": f"{REPO}/blob/main/alpha_archive/replications/darmanin2026.py",
        "thumb": "thumbs/2607.20093.jpg",
    },
}


# ------------------------------------------------------------------- loading


def load_replications() -> list[dict]:
    out = []
    for path in sorted(glob.glob(os.path.join(ROOT, "data", "replications", "*.json"))):
        with open(path, encoding="utf-8") as fh:
            try:
                rec = json.load(fh)
            except json.JSONDecodeError:
                continue
        if rec.get("paper") in REPLICATED:
            out.append(rec)
    order = {k: i for i, k in enumerate(REPLICATED)}
    return sorted(out, key=lambda r: order.get(r["paper"], 99))


def load_queue() -> list[dict]:
    path = os.path.join(ROOT, "data", "papers", "arxiv.json")
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as fh:
        return json.load(fh).get("papers", [])


def status_of(rec: dict) -> tuple[str, str]:
    if "families" in rec:
        fams = rec["families"]
        ok = sum(1 for f in fams
                 if f["sharpe_gate"] == f["paper_sharpe_gate"]
                 and f["cagr_gate"] == f["paper_cagr_gate"]
                 and f["sharpe_ci_overlaps"] and f["cagr_ci_overlaps"])
        if ok == len(fams):
            return "reproduced", "ok"
        return ("partial", "warn") if ok else ("differs", "bad")
    return (("reproduced", "ok")
            if rec.get("verification", {}).get("status") == "VERIFIED"
            else ("unverified", "warn"))


# ----------------------------------------------------------------- rendering


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
            for f in rec["families"])
        perts = "".join(
            f"<tr><td>{e(f['label'])}</td><td>" + " · ".join(
                f"<code>{e(p['params'])}</code> {p['sharpe_gap']:+.3f}"
                for p in f["perturbations"]) + "</td></tr>"
            for f in rec["families"] if f.get("perturbations"))
        notes = "".join(f"<li>{e(n)}</li>"
                        for f in rec["families"] for n in f.get("notes", []))
        skipped = "".join(f"<li>{e(x)}</li>" for x in rec.get("not_attempted", []))
        return (f'<table><thead><tr><th rowspan="2">Family</th>'
                f'<th colspan="2" class="n">Sharpe gap, 95% CI</th>'
                f'<th colspan="2" class="n">CAGR gap, 95% CI</th></tr>'
                f'<tr><th class="n">paper</th><th class="n">ours</th>'
                f'<th class="n">paper</th><th class="n">ours</th></tr></thead>'
                f"<tbody>{rows}</tbody></table>"
                f'<p class="fine">Reproduced means the verdict matches <em>and</em> the '
                f"intervals overlap, on both gates. Thresholds are the paper's: "
                f"&delta;<sub>S</sub>={rec['delta_sharpe']}, "
                f"&delta;<sub>R</sub>={rec['delta_cagr']}. "
                f"Costs {rec['cost_bps_per_leg']}bps/leg. Stationary bootstrap, "
                f"{rec['bootstrap']['draws']:,} draws, mean block "
                f"{rec['bootstrap']['mean_block']}.</p>"
                f"<h4>Parameter sensitivity</h4>"
                f'<table class="plain"><tbody>{perts}</tbody></table>'
                + (f"<h4>Where we differ</h4><ul>{notes}</ul>" if notes else "")
                + f"<h4>Not attempted</h4><ul>{skipped}</ul>")

    v = rec.get("verification", {})
    crit = v.get("criterion", {})
    eras = "".join(
        f"<tr><td>{e(k)}</td><td class='n'>{x['mean_monthly_pct']:+.3f}%</td>"
        f"<td class='n'>{x['t_stat']:+.2f}</td><td class='n sub'>{x['months']}</td></tr>"
        for k, x in rec.get("umd_by_era", {}).items())
    caveats = "".join(f"<li>{e(c)}</li>" for c in rec.get("caveats", []))
    return (f"<h4>Verification &mdash; "
            f"{e(v.get('status', '?').lower().replace('_', ' '))}</h4>"
            f"<p>{e(v.get('reason', ''))}</p>"
            f'<p class="fine">Bar: {e(str(crit.get("statistic", "")))} &ge; '
            f'{crit.get("threshold", "")}, against {e(str(crit.get("fixture", "")))} '
            f'&mdash; declared by {e(str(crit.get("fixture_source", "")))}, not by us.</p>'
            f"<h4>Reference factor by era</h4>"
            f'<table><thead><tr><th>Ken French UMD</th><th class="n">mean</th>'
            f'<th class="n">t</th><th class="n">months</th></tr></thead>'
            f"<tbody>{eras}</tbody></table>"
            f"<h4>Sample limits</h4><ul>{caveats}</ul>")


def card(*, thumb_html: str, title: str, url: str, abstract: str, venue: str,
         authors: str, date: str, tags: list[str], status: tuple[str, str],
         actions: list[tuple[str, str]], body: str = "", search: str = "") -> str:
    e = html.escape
    label, cls = status
    tagrow = "".join(f'<a class="tag" href="#" data-tag="{e(t)}">{e(t)}</a>' for t in tags)
    acts = "".join(
        f'<a class="act" href="{href}">{e(text)}</a>' if href
        else f'<span class="act st {cls}">{e(text)}</span>'
        for text, href in actions)
    return f"""
  <article class="card" data-status="{cls}" data-search="{e(search.lower())}">
    <a class="fig" href="{url}">{thumb_html}</a>
    <div class="mid">
      <h2><a href="{url}">{e(title)}</a></h2>
      <p class="abs">{e(abstract)}</p>
      <p class="meta"><span class="org">{e(venue)}</span><span class="dot">&middot;</span>
        {e(authors)}<span class="dot">&middot;</span>Published {e(date)}</p>
      <p class="tagrow">{tagrow}</p>
      {f'<details><summary>Full result</summary>{body}</details>' if body else ''}
    </div>
    <div class="acts">{acts}</div>
  </article>"""


def render_replication(rec: dict) -> str:
    m = REPLICATED[rec["paper"]]
    label, cls = status_of(rec)
    t = (f'<img src="{m["thumb"]}" alt="First page" loading="lazy">'
         if m["thumb"] else f'<div class="gen">{thumb.for_record(rec)}</div>')
    return card(
        thumb_html=t, title=m["title"], url=m["paper_url"], abstract=m["abstract"],
        venue=m["venue"], authors=m["authors"], date=m["date"], tags=m["tags"],
        status=(label, cls),
        actions=[(label, ""), ("Code", m["impl_url"]), ("Paper", m["paper_url"])],
        body=detail(rec),
        search=" ".join([m["title"], m["authors"], m["venue"], *m["tags"], label]),
    )


QUEUE_STATUS = {
    "queued": ("queued", "queue"),
    "triage": ("triage", "queue"),
    "blocked": ("blocked", "muted"),
}


def render_queued(p: dict) -> str:
    label, cls = QUEUE_STATUS.get(p["status"], ("triage", "queue"))
    t = (f'<img src="{p["thumb"]}" alt="First page" loading="lazy">'
         if p.get("thumb") else '<div class="gen noimg">no preview</div>')
    return card(
        thumb_html=t, title=p["title"], url=p["url"],
        abstract=p["abstract"],
        venue=p["primary_category"], authors=p["authors"] or "—",
        date=p["published"], tags=p["tags"], status=(label, cls),
        actions=[(label, ""), ("Paper", p["url"]), ("PDF", p["pdf"])],
        search=" ".join([p["title"], p["authors"], p["primary_category"],
                         *p["tags"], label]),
    )


PAGE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Alpha Archive — finance papers with code, actually run</title>
<meta name="description" content="An index of quantitative finance papers, re-implemented and re-run on point-in-time data. What the paper claimed, what we measured, and whether it reproduced.">
<meta property="og:title" content="Alpha Archive">
<meta property="og:description" content="Finance papers with code, actually run.">
<link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'><rect width='32' height='32' rx='5' fill='%23111'/><path d='M8 23 L16 9 L24 23' stroke='%23fff' stroke-width='2.6' fill='none' stroke-linecap='round' stroke-linejoin='round'/><path d='M11.6 18.4 H20.4' stroke='%23fff' stroke-width='2.6' stroke-linecap='round'/></svg>">
<style>
:root{
  --page:#fff; --card:#fff; --ink:#12181f; --soft:#65758a; --line:#e6e9ef; --chip:#f2f4f7;
  --ok:#0f7a45; --okbg:#e8f6ee; --okbd:#bfe3ce;
  --warn:#8a5b00; --warnbg:#fdf5e6; --warnbd:#eddcb6;
  --bad:#a5231a; --badbg:#fdeeec; --badbd:#eec7c2;
  --accent:#e06c2b;
  --sans:-apple-system,BlinkMacSystemFont,"Segoe UI",Inter,Roboto,Helvetica,Arial,sans-serif;
  --mono:ui-monospace,"SF Mono","Cascadia Mono",Menlo,Consolas,monospace}
@media (prefers-color-scheme: dark){:root{
  --page:#0b0f14; --card:#11161d; --ink:#e8edf3; --soft:#8b9bb0; --line:#212a35; --chip:#1a222c;
  --ok:#4ade8a; --okbg:#12241b; --okbd:#20452f;
  --warn:#e3a94a; --warnbg:#241d10; --warnbd:#463a1c;
  --bad:#f2837a; --badbg:#251413; --badbd:#4a2320;
  --accent:#ff9a5c}}
*{box-sizing:border-box}
body{margin:0;background:var(--page);color:var(--ink);font-family:var(--sans);font-size:15px;
  line-height:1.55;-webkit-font-smoothing:antialiased}
a{color:inherit;text-decoration:none}
a:hover{text-decoration:underline}
.wrap{max-width:1560px;margin:0 auto;padding:0 32px}

.hero{padding:34px 0 18px}
.heroTop{display:flex;align-items:flex-start;gap:28px;flex-wrap:wrap}
h1{font-size:34px;font-weight:800;letter-spacing:-.02em;margin:0}
.tagline{color:var(--soft);font-size:15px;margin:5px 0 0}
.tagline b{color:var(--ink);font-weight:600}
.searchWrap{flex:1;min-width:280px;max-width:520px;margin-top:4px}
#q{width:100%;font:inherit;font-size:15px;padding:11px 16px;border:1px solid var(--line);
  border-radius:999px;background:var(--card);color:var(--ink)}
#q::placeholder{color:var(--soft)}
#q:focus{outline:none;border-color:var(--soft)}
.tabs{display:flex;gap:4px;align-items:center;margin-top:6px;flex-wrap:wrap}
.tab{font-size:14px;padding:7px 14px;border-radius:999px;border:1px solid transparent;
  background:transparent;color:var(--soft);cursor:pointer;font-weight:500;font-family:inherit}
.tab:hover{color:var(--ink)}
.tab.on{background:var(--chip);color:var(--ink);font-weight:600}
.tab.cta{background:var(--warnbg);color:var(--accent);border-color:var(--warnbd);
  font-weight:700;cursor:default}

.count{color:var(--soft);font-size:14px;padding:4px 0 14px}

.card{display:grid;grid-template-columns:1fr;border:1px solid var(--line);border-radius:10px;
  background:var(--card);margin-bottom:14px;overflow:hidden}
@media(min-width:900px){.card{grid-template-columns:212px 1fr 176px}}
.fig{display:block;background:var(--chip);overflow:hidden;line-height:0}
.fig img{width:100%;height:100%;max-height:246px;object-fit:cover;object-position:top center;
  display:block}
.gen{padding:10px;background:var(--chip);color:var(--ink);height:100%;display:flex;align-items:center}
.gen svg{width:100%;height:auto}
.noimg{display:flex;align-items:center;justify-content:center;min-height:150px;
  color:var(--soft);font-size:12px;background:var(--chip)}
.mid{padding:18px 22px;min-width:0}
.card h2{font-size:19px;line-height:1.33;margin:0 0 7px;font-weight:700;letter-spacing:-.01em}
.abs{margin:0 0 10px;font-size:14px;line-height:1.55;color:var(--soft);
  display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}
.meta{margin:0 0 9px;font-size:13px;color:var(--soft);display:flex;align-items:center;
  gap:7px;flex-wrap:wrap}
.org{background:var(--chip);border-radius:6px;padding:3px 9px;font-size:12px;font-weight:600;
  color:var(--ink)}
.dot{color:var(--line)}
.tagrow{margin:0;display:flex;gap:6px;flex-wrap:wrap}
.tag{font-size:11.5px;color:var(--soft);background:var(--chip);border-radius:5px;padding:3px 9px}
.tag:hover{color:var(--ink);text-decoration:none}
.acts{display:flex;flex-direction:column;gap:8px;padding:18px 18px 18px 0;align-self:start}
@media(max-width:899px){.acts{padding:0 22px 18px}}
.act{display:flex;align-items:center;justify-content:center;font-size:13.5px;font-weight:600;
  border:1px solid var(--line);border-radius:8px;padding:8px 12px;background:var(--card);
  white-space:nowrap}
a.act:hover{background:var(--chip);text-decoration:none}
.act.st{cursor:default}
.act.st.ok{color:var(--ok);background:var(--okbg);border-color:var(--okbd)}
.act.st.warn{color:var(--warn);background:var(--warnbg);border-color:var(--warnbd)}
.act.st.bad{color:var(--bad);background:var(--badbg);border-color:var(--badbd)}
.act.st.queue{color:var(--soft);background:var(--chip)}
.act.st.muted{color:var(--soft);background:transparent;border-style:dashed}

details{margin-top:12px;border-top:1px solid var(--line);padding-top:11px}
summary{cursor:pointer;font-size:13.5px;font-weight:600;color:var(--accent)}
details h4{font-size:11.5px;letter-spacing:.06em;text-transform:uppercase;color:var(--soft);
  margin:16px 0 7px;font-weight:700}
details p{font-size:13.5px;margin:0 0 8px}
details ul{margin:0;padding-left:18px;font-size:13px;color:var(--soft);line-height:1.65}
.fine{color:var(--soft);font-size:12.5px}
table{width:100%;border-collapse:collapse;font-size:13px;margin:4px 0 0}
th{color:var(--soft);font-size:10.5px;letter-spacing:.06em;text-transform:uppercase;
  font-weight:700;text-align:left;padding:6px 8px;border-bottom:1px solid var(--soft)}
td{padding:8px;border-bottom:1px solid var(--line);vertical-align:top}
table.plain th,table.plain td{border:none;padding:5px 8px}
.n{text-align:right;font-family:var(--mono);white-space:nowrap}
th.n{text-align:right}
.sub{color:var(--soft);font-size:11.5px;font-weight:400}
code{font-family:var(--mono)}
.empty{padding:44px 0;color:var(--soft);text-align:center}
footer{color:var(--soft);font-size:12.5px;padding:30px 0 60px;line-height:1.7;
  border-top:1px solid var(--line);margin-top:26px}
footer a{margin-right:18px;color:var(--soft)}
</style>
</head>
<body>
<div class="wrap">

  <div class="hero">
    <div class="heroTop">
      <div>
        <h1>Alpha Archive</h1>
        <p class="tagline">Finance papers with code &mdash; and we <b>run</b> the code.</p>
      </div>
      <div class="searchWrap">
        <input id="q" type="search" placeholder="Search papers, authors, tags&hellip;"
               autocomplete="off">
      </div>
      <div class="tabs">
        <button class="tab on" data-f="all">All</button>
        <button class="tab" data-f="done">Replicated</button>
        <button class="tab" data-f="queue">Queued</button>
        <button class="tab" data-f="muted">Blocked</button>
        <span class="tab cta">__DONE__ replicated</span>
      </div>
    </div>
  </div>

  <p class="count" id="count"></p>
  <div id="list">__CARDS__</div>
  <p class="empty" id="empty" hidden>No papers match.</p>

  <footer>
    <a href="__REPO__">GitHub</a>
    <a href="__REPO__/blob/main/docs/methodology.md">Methodology</a>
    <a href="https://github.com/RezaSoleymanifar/vintage">Vintage</a>
    <a href="https://www.openassetpricing.com/">Open Source Asset Pricing</a>
    <p>Queued papers come from the arXiv q-fin feed and carry no results yet &mdash; the
    status on each card says so. Thumbnails are the paper's own first page, rendered from
    the openly distributed arXiv PDF. MIT licensed. No data redistributed. Not affiliated
    with arXiv, Hugging Face, Papers with Code, or any cited author. Not investment advice.</p>
  </footer>
</div>

<script>
var cards = [].slice.call(document.querySelectorAll('.card'));
var q = document.getElementById('q'), count = document.getElementById('count'),
    empty = document.getElementById('empty'), filter = 'all';
var DONE = {ok: 1, warn: 1, bad: 1};

function apply() {
  var term = q.value.trim().toLowerCase(), shown = 0;
  cards.forEach(function (c) {
    var s = c.dataset.status, pass;
    if (filter === 'all') pass = true;
    else if (filter === 'done') pass = !!DONE[s];
    else pass = s === filter;
    var hit = !term || c.dataset.search.indexOf(term) !== -1;
    c.hidden = !(pass && hit);
    if (!c.hidden) shown++;
  });
  count.textContent = shown + (shown === 1 ? ' paper' : ' papers');
  empty.hidden = shown > 0;
}
q.addEventListener('input', apply);
document.querySelectorAll('.tab[data-f]').forEach(function (b) {
  b.addEventListener('click', function () {
    document.querySelectorAll('.tab[data-f]').forEach(function (x) {
      x.classList.remove('on');
    });
    b.classList.add('on'); filter = b.dataset.f; apply();
  });
});
document.querySelectorAll('.tag').forEach(function (t) {
  t.addEventListener('click', function (e) {
    e.preventDefault(); q.value = t.dataset.tag; apply();
  });
});
apply();
</script>
</body>
</html>
"""


def main() -> None:
    reps = load_replications()
    queue = load_queue()
    cards = [render_replication(r) for r in reps] + [render_queued(p) for p in queue]
    page = (PAGE.replace("__CARDS__", "\n".join(cards))
                .replace("__DONE__", str(len(reps)))
                .replace("__REPO__", REPO))
    out_dir = os.path.join(ROOT, "docs")
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, "index.html"), "w", encoding="utf-8", newline="\n") as fh:
        fh.write(page)
    print(f"wrote docs/index.html ({len(page):,} bytes) — "
          f"{len(reps)} replicated, {len(queue)} queued")


if __name__ == "__main__":
    main()
