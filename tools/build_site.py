"""Generate docs/index.html, a citation leaderboard for quant finance research.

Papers are ranked by citations inside a publication-date window: 30 days, 12
months, 5 years, all time. Every window ships in the page, so switching one is
a filter in the DOM rather than a request.

Layout follows the reference (huggingface.co/papers, successor to Papers With
Code): first-page thumbnail flush on the left, title and truncated abstract in
the middle, stacked actions on the right. Dark and light both supported.
The reference follows the reader's system theme, and rendering light against
its dark is most of why a copy reads as a copy.

Two sources feed it. data/papers/papers.json is the indexed universe, arXiv
q-fin on one side, the journals, SSRN and NBER on the other, with citation
counts from OpenAlex. data/replications/*.json are the few we have actually
run; those carry a result and a Code link, and everything else says plainly
that it has neither.

    uv run python tools/build_site.py
"""

from __future__ import annotations

import glob
import hashlib
import html
import json
import os
import re
import sys
from datetime import datetime, timedelta, timezone

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
                    "losers earned about 1.3% a month over 1964-1989, an effect large enough "
                    "that the authors argue markets cannot be fully efficient. We measure "
                    "−0.12%/mo on currently-listed large caps since 2006, but the reference "
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
        "abstract": "Tests five widely promoted retail signal families, trend, oscillator, "
                    "candlestick, volume and calendar rules, against three predeclared gates: "
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
    """Only the shortlist now, not the whole indexed corpus.

    Listing 1,114 papers made the site a directory of things nobody had read.
    Every card here has had its PDF read, its data traced to a free source, and
    its published numbers written down, which is the difference between a search
    result and a claim.
    """
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import shortlist

    out = []
    for p in shortlist.load():
        out.append({
            **p,
            "primary_category": p["area"],
            "status": p["state"],
            "citations_per_month": 0.0,
            "top_1pct": bool(p.get("percentile", 0) and p["percentile"] >= 0.99),
        })
    return out


def load_osap() -> list[dict]:
    """OSAP predictors: the canon, as implementable specs rather than PDFs."""
    path = os.path.join(ROOT, "data", "papers", "osap.json")
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as fh:
        return json.load(fh).get("predictors", [])


def load_citations() -> dict[str, int]:
    """Citation counts for the replicated papers, refreshed by fetch_papers."""
    path = os.path.join(ROOT, "data", "papers", "citations.json")
    if not os.path.exists(path):
        return {}
    with open(path, encoding="utf-8") as fh:
        return json.load(fh).get("citations", {})


def per_month(citations: int, published: str) -> float:
    """Citations a month since publication, the only fair way to compare a
    paper from last quarter with one from 1993."""
    from datetime import datetime, timezone
    text = published if len(published) >= 10 else f"{published[:4]}-01-01"
    try:
        when = datetime.strptime(text[:10], "%Y-%m-%d").replace(tzinfo=timezone.utc)
    except ValueError:
        return 0.0
    months = max((datetime.now(timezone.utc) - when).days / 30.44, 1.0)
    return round(citations / months, 2)


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
    return (f"<h4>Verification, "
            f"{e(v.get('status', '?').lower().replace('_', ' '))}</h4>"
            f"<p>{e(v.get('reason', ''))}</p>"
            f'<p class="fine">Bar: {e(str(crit.get("statistic", "")))} &ge; '
            f'{crit.get("threshold", "")}, against {e(str(crit.get("fixture", "")))} '
            f', declared by {e(str(crit.get("fixture_source", "")))}, not by us.</p>'
            f"<h4>Reference factor by era</h4>"
            f'<table><thead><tr><th>Ken French UMD</th><th class="n">mean</th>'
            f'<th class="n">t</th><th class="n">months</th></tr></thead>'
            f"<tbody>{eras}</tbody></table>"
            f"<h4>Sample limits</h4><ul>{caveats}</ul>")


def tag_class(tag: str) -> str:
    """Stable colour per tag, so a reader learns the palette."""
    palette = ["t-green", "t-blue", "t-pink", "t-purple", "t-amber", "t-teal"]
    return palette[sum(ord(c) for c in tag) % len(palette)]


def card(*, thumb_html: str, title: str, url: str, abstract: str, venue: str,
         authors: str, date: str, tags: list[str], status: tuple[str, str],
         actions: list[tuple[str, str]], citations: int = 0, per_month: float = 0.0,
         percentile: float = 0.0, top1: bool = False, influential: int = 0,
         open_access: bool = False, spec_tstat: str = "",
         body: str = "", spec: str = "", confidence: float = 0.0,
         tier: str = "", digits: int = 0, appeal: int = 0,
         one_liner: str = "", search: str = "") -> str:
    def e(text: str) -> str:
        return html.escape(html.unescape(str(text)))

    label, cls = status
    tagrow = "".join(
        f'<a class="tag {tag_class(t)}" href="#" data-tag="{e(t)}">'
        f'<span class="dotm"></span>{e(t)}</a>' for t in tags)

    # Their SOTA line, ours: what we actually ran and where it landed.
    result = ""
    if body:
        result = (f'<p class="sota"><span class="badge">REPLICATED</span> '
                  f'<span class="on">on</span> '
                  f'<span class="bench">{e(label)}</span> '
                  f'<span class="sep">&middot;</span> '
                  f'<a href="#" class="expand">full result</a></p>')

    # "top 0.02%" reads; "0.0%" does not. Keep a digit that means something.
    top_pct = max(0.01, (1 - percentile) * 100)
    pct_txt = (", " if not percentile else
               f"{top_pct:.0f}%" if top_pct >= 10 else
               f"{top_pct:.1f}%" if top_pct >= 1 else
               f"{top_pct:.2f}%")
    rail = (
        f'<div class="rail">'
        f'<div class="stat"><svg viewBox="0 0 24 24" width="15" height="15" fill="none" '
        f'stroke="currentColor" stroke-width="1.8"><path d="M3 20h18M6 16l4-6 4 3 5-8"/></svg>'
        f'<b>{"\u2191" if citations else ""}{citations:,}</b><span>citations</span></div>'
        f'<div class="stat"><b class="{"hot" if top1 else ""}">{pct_txt}</b>'
        f'<span>top percentile</span></div>'
        + (f'<div class="stat"><b>{influential:,}</b><span>influential</span></div>'
           if influential else '')
        + (f'<div class="stat"><b class="hot">t={e(spec_tstat)}</b>'
           f'<span>paper claim</span></div>' if spec_tstat else '')
        # Effort and how sure we are it is reproducible, on the face rather than
        # folded away. Without these every card looks equally ready to build.
        + (f'<div class="stat"><b class="{"hot" if appeal >= 70 else ""}">{appeal}</b>'
           f'<span>quant appeal</span></div>' if appeal else '')
        + (f'<div class="stat"><b>{e(tier)}</b><span>effort</span></div>'
           f'<div class="stat"><b class="{"hot" if confidence >= 0.9 else ""}">'
           f'{confidence:.2f}</b><span>est. reproducible</span></div>' if tier else '')
        + '</div>')

    links = "".join(f'<a class="act" href="{href}">{e(text)}</a>'
                    for text, href in actions if href)

    return f"""
  <article class="card" data-status="{cls}" data-search="{e(search.lower())}"
           data-cites="{citations}" data-date="{e(date[:10])}" data-vel="{per_month}"
           data-pct="{percentile}" data-infl="{influential}"
           data-tags="{e(' '.join(tags))}" data-code="{1 if body else 0}"
           data-conf="{confidence}" data-tier="{e(tier)}" data-digits="{digits}"
           data-appeal="{appeal}"
           data-oa="{1 if open_access else 0}">
    <a class="fig" href="{url}">{thumb_html}</a>
    <div class="mid">
      <h2><a href="{url}">{e(title)}</a></h2>
      <p class="meta">{e(authors)} <span class="sep">&middot;</span> {e(venue)}
        <span class="sep">&middot;</span> {e(date)}</p>
      {f'<p class="finding">{e(one_liner)}</p>' if one_liner else ''}
      <p class="abs">{e(abstract)}</p>
      {result}
      <p class="tagrow">{tagrow}{links}</p>
      {f'<details><summary>Full result</summary>{body}</details>' if body else ''}
      {f'<details class="spec"><summary>What a replication must match</summary>{spec}</details>' if spec else ''}
    </div>
    {rail}
  </article>"""


def render_replication(rec: dict, cites: dict[str, int]) -> str:
    m = REPLICATED[rec["paper"]]
    label, cls = status_of(rec)
    n = int(cites.get(rec["paper"], 0))
    t = (f'<img src="{thumb_src(m["thumb"])}" alt="First page of the paper" loading="lazy" '
         f'decoding="async" width="320" height="414">'
         if m["thumb"] else f'<div class="gen">{thumb.for_record(rec)}</div>')
    return card(
        thumb_html=t, title=m["title"], url=m["paper_url"], abstract=m["abstract"],
        venue=m["venue"], authors=m["authors"], date=m["date"], tags=m["tags"],
        status=(label, cls), citations=n, per_month=per_month(n, m["date"]),
        actions=[(label, ""), ("Code", m["impl_url"]), ("Paper", m["paper_url"])],
        body=detail(rec),
        search=" ".join([m["title"], m["authors"], m["venue"], *m["tags"], label]),
    )


_THUMB_TAGS: dict[str, str] = {}


def thumb_src(rel: str) -> str:
    """Same filename, new bytes, is how a browser ends up showing yesterday's
    page for a second. Hash the file into the URL so a changed thumbnail is a
    different URL and nothing stale can be served."""
    if rel in _THUMB_TAGS:
        return _THUMB_TAGS[rel]
    path = os.path.join(ROOT, "docs", rel)
    tag = rel
    try:
        with open(path, "rb") as fh:
            tag = f"{rel}?v={hashlib.md5(fh.read()).hexdigest()[:8]}"
    except OSError:
        pass
    _THUMB_TAGS[rel] = tag
    return tag


def placeholder(p: dict) -> str:
    """No open PDF exists for most journal papers, Unpaywall confirms it, not
    a fetch failure. Draw the title page instead of apologising for it, so the
    card still reads as a paper."""
    e = html.escape

    def wrap(text: str, width: int, limit: int) -> list[str]:
        words, lines, cur = text.split(), [], ""
        for w in words:
            if len(cur) + len(w) + 1 > width:
                lines.append(cur)
                cur = w
                if len(lines) == limit:
                    return lines
            else:
                cur = f"{cur} {w}".strip()
        if cur and len(lines) < limit:
            lines.append(cur)
        return lines

    title = wrap(html.unescape(p.get("title") or ""), 26, 4)
    authors = (p.get("authors") or "").split(",")[0].strip()
    venue = (p.get("primary_category") or "")[:30]
    year = str(p.get("published") or "")[:4]

    y = 52
    body = []
    for line in title:
        body.append(f'<text x="106" y="{y}" text-anchor="middle" font-size="10.5" '
                    f'font-family="Georgia,serif" fill="#1a1814">{e(line)}</text>')
        y += 15
    y += 6
    if authors:
        body.append(f'<text x="106" y="{y}" text-anchor="middle" font-size="7.5" '
                    f'font-family="Georgia,serif" fill="#55504a">{e(authors)}</text>')
        y += 12
    if venue:
        body.append(f'<text x="106" y="{y}" text-anchor="middle" font-size="6.5" '
                    f'font-family="Georgia,serif" fill="#8a847c">{e(venue)} {e(year)}</text>')
        y += 16

    # a paragraph of grey rules, the shape a first page makes from across a room
    for i in range(14):
        w = 150 if i % 5 != 4 else 96
        body.append(f'<rect x="31" y="{y}" width="{w}" height="2.4" rx="1" '
                    f'fill="#1a1814" opacity="0.12"/>')
        y += 8
        if y > 232:
            break

    return ('<div class="gen ph"><svg viewBox="0 0 212 246" '
            'xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Title page">'
            '<rect width="212" height="246" fill="#f7f5f0"/>'
            + "".join(body) + '</svg></div>')


QUEUE_STATUS = {
    "queued": ("to build", "queue"),
    "replicated": ("replicated", "ok"),
    "triage": ("triage", "queue"),
    "blocked": ("blocked", "muted"),
}


def render_queued(p: dict) -> str:
    label, cls = QUEUE_STATUS.get(p["status"], ("triage", "queue"))
    t = (f'<img src="{thumb_src(p["thumb"])}" alt="First page of the paper" loading="lazy" '
         f'decoding="async" width="320" height="414">'
         if p.get("thumb") else placeholder(p))
    # No status pill on a paper we have not run. A leaderboard that labels
    # Sharpe "blocked" is describing our backlog, not the paper.
    acts = [("Paper", p["url"])]
    if p.get("pdf"):
        acts.append(("PDF", p["pdf"]))

    # What a replication has to land on, and what it will cost to try. Both come
    # from the PDF read, so neither is a guess.
    spec = ""
    if p.get("targets") or p.get("data_needed"):
        rows = "".join(f"<li>{html.escape(html.unescape(t))}</li>"
                       for t in (p.get("targets") or [])[:6])
        data = "".join(f"<li>{html.escape(html.unescape(d))}</li>"
                       for d in (p.get("data_needed") or [])[:5])
        spec = (
            "<h4>Must land on</h4><ul>" + (rows or "<li>, </li>") + "</ul>"
            + ("<h4>Free data it needs</h4><ul>" + data + "</ul>" if data else "")
            + f"<p class=\"note\">Effort <b>{p['tier']}</b>, {html.escape(p['tier_why'])}."
              f" Judged reproducible at confidence {p['confidence']:.2f}.</p>"
        )

    return card(
        thumb_html=t, title=p["title"], url=p["url"],
        abstract=p["abstract"],
        spec=spec,
        venue=p["primary_category"], authors=p["authors"] or ", ",
        date=p["published"], tags=p["tags"], status=(label, cls),
        citations=int(p.get("citations") or 0),
        per_month=float(p.get("citations_per_month") or 0.0),
        percentile=float(p.get("percentile") or 0.0), top1=bool(p.get("top_1pct")),
        influential=int(p.get("influential") or 0),
        open_access=bool(p.get("thumb")),
        actions=acts,
        confidence=float(p.get("confidence") or 0.0),
        appeal=int(p.get("appeal") or 0),
        one_liner=str(p.get("one_liner") or ""),
        tier=str(p.get("tier") or ""),
        digits=int(p.get("digits") or 0),
        search=" ".join([p["title"], p["authors"], p["primary_category"],
                         *p["tags"], label]),
    )


def render_spec(p: dict) -> str:
    """An OSAP entry is a claim plus a definition. The card says so, and puts
    the paper's own t-statistic where a citation count would go."""
    e = html.escape
    t = placeholder(p)
    acts = [("Definition", p["url"]),
            ("Vintage", "https://github.com/RezaSoleymanifar/vintage"
                        "/blob/main/COVERAGE.md")]
    return card(
        thumb_html=t, title=p["title"], url=p["url"], abstract=p["abstract"],
        venue=p["primary_category"], authors=p["authors"] or ", ",
        date=p["published"], tags=p["tags"], status=("spec", "queue"),
        citations=int(p.get("citations") or 0),
        per_month=float(p.get("citations_per_month") or 0.0),
        percentile=float(p.get("percentile") or 0.0), top1=bool(p.get("top_1pct")),
        influential=0, open_access=True, spec_tstat=str(p.get("tstat") or ""),
        actions=acts,
        search=" ".join([p["title"], p["authors"], p["primary_category"], *p["tags"],
                         "osap spec replicable"]),
    )


PAGE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Quantitative Finance with Code, papers rebuilt and checked against their own numbers</title>
<meta name="description" content="Quantitative finance papers rebuilt in code and scored against the numbers they printed. Every paper read in full, its data traced to a free source, its targets written down before anything was run.">
<meta property="og:title" content="Quantitative Finance with Code">
<meta property="og:description" content="Papers rebuilt in code and scored against the numbers they printed.">
<link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'><rect width='32' height='32' rx='6' fill='%230d0d0d'/><text x='16' y='23' font-size='20' font-family='Georgia,serif' fill='%233ddc84' text-anchor='middle'>&#945;</text></svg>">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Newsreader:ital,opsz,wght@0,6..72,400;0,6..72,500;0,6..72,600;1,6..72,400;1,6..72,500&family=Inter:wght@400;500;600&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
<style>
:root{
  --page:#0d0d0d; --nav:#000; --card:#121212; --chip:#1a1a1a; --line:#262523;
  --ink:#f2ede3; --soft:#8f8a80; --dim:#6b665e;
  --accent:#7ea9dd; --alpha:#3ddc84; --alphaglow:rgba(61,220,132,.55);
  --ok:#7fd6a2; --warn:#e3b35c; --bad:#e08b80;
  --sans:Inter,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;
  --serif:Newsreader,Georgia,"Times New Roman",serif;
  --mono:"JetBrains Mono",ui-monospace,Menlo,Consolas,monospace;
}
*{box-sizing:border-box}
body{margin:0;background:var(--page);color:var(--ink);font-family:var(--sans);
  font-size:14px;line-height:1.55;-webkit-font-smoothing:antialiased}
a{color:inherit;text-decoration:none}
a:hover{text-decoration:underline}
.wrap{max-width:1500px;margin:0 auto;padding:0 42px}
@media(max-width:900px){.wrap{padding:0 18px}}

/* ------------------------------------------------------------------- nav */
.topbar{background:var(--nav);border-bottom:1px solid var(--line)}
.topbar .wrap{display:flex;align-items:center;gap:26px;height:66px}
.brand{display:flex;align-items:baseline;gap:3px;font-family:var(--serif);
  font-size:21px;font-weight:500;white-space:nowrap}
.brand:hover{text-decoration:none}
.brand .a{color:var(--alpha);font-style:italic;font-size:1.95em;line-height:.7;
  animation:pulse 3.4s ease-in-out infinite;
  text-shadow:0 0 18px var(--alphaglow),0 0 44px var(--alphaglow)}
@keyframes pulse{
  0%,100%{text-shadow:0 0 20px var(--alphaglow),0 0 46px var(--alphaglow),
                      0 0 78px var(--alphaglow)}
  50%{text-shadow:0 0 10px var(--alphaglow),0 0 22px var(--alphaglow)}}
@media (prefers-reduced-motion:reduce){.brand .a{animation:none}}
.nlinks{display:flex;gap:24px;font-size:14px}
.nlinks a{color:var(--soft);padding:4px 0}
.nlinks a:hover{color:var(--ink);text-decoration:none}
.nlinks a.on{color:var(--ink);border-bottom:1.5px solid var(--ink)}
.navright{display:flex;align-items:center;gap:12px;margin-left:auto}
.pill{border:1px solid var(--line);border-radius:8px;padding:9px 16px;font-size:13.5px;
  font-weight:500;white-space:nowrap;background:var(--card)}
.pill:hover{background:var(--chip);text-decoration:none}
.searchbox{display:flex;align-items:center;gap:9px;border:1px solid var(--line);
  border-radius:9px;padding:8px 12px;background:var(--card);min-width:250px}
.searchbox svg{color:var(--dim);flex:none}
#q{border:0;background:none;color:var(--ink);font:inherit;font-size:13.5px;width:100%;outline:none}
#q::placeholder{color:var(--dim)}
.kbd{font-family:var(--mono);font-size:10px;color:var(--dim);border:1px solid var(--line);
  border-radius:4px;padding:2px 5px;line-height:1.25;text-align:center;white-space:nowrap}
.signin{display:flex;align-items:center;gap:8px;border:1px solid var(--line);
  border-radius:8px;padding:8px 15px;font-size:13.5px;font-weight:500;background:var(--card)}
.signin:hover{background:var(--chip);text-decoration:none}
@media(max-width:1180px){.nlinks{display:none}}
@media(max-width:760px){.searchbox{display:none}}

.strip{background:#151412;border-bottom:1px solid var(--line);text-align:center;
  padding:9px 0;font-size:13px;color:var(--soft)}
.strip a{color:var(--ink);text-decoration:underline;text-underline-offset:3px}

/* ------------------------------------------------------------------ head */
.head{padding:34px 0 4px}
h1{font-family:var(--serif);font-size:clamp(32px,4.2vw,46px);font-weight:500;
  letter-spacing:-.01em;margin:0;line-height:1.1}
h1 em{font-style:italic;color:var(--accent)}
.sub{font-family:var(--serif);font-style:italic;font-size:15.5px;color:var(--soft);
  margin:8px 0 0}

/* ---------------------------------------------------------------- layout */
.cols{display:grid;grid-template-columns:1fr;gap:34px;padding:20px 0 60px}
@media(min-width:1080px){.cols{grid-template-columns:236px 1fr}}
.side h3{font-family:var(--mono);font-size:10.5px;letter-spacing:.13em;
  text-transform:uppercase;color:var(--dim);font-weight:400;margin:0 0 14px}
.side .grp{margin-bottom:34px}
.side a.row{display:flex;align-items:baseline;gap:8px;padding:5px 0;color:var(--ink);
  font-size:14.5px}
.side a.row:hover{color:var(--accent);text-decoration:none}
.side a.row span{font-family:var(--mono);font-size:11.5px;color:var(--dim)}

/* Area headers group the task rows beneath them, the way a Papers With Code
   sidebar reads: the wing of the building, then the rooms. */
.side .area{display:flex;align-items:baseline;justify-content:space-between;
  margin:14px 0 4px;padding-top:9px;border-top:1px solid var(--line)}
.side .area:first-of-type{border-top:0;padding-top:0;margin-top:2px}
.side .areaname{font-size:10.5px;letter-spacing:.11em;text-transform:uppercase;
  color:var(--dim);font-weight:700}
.side .areacount{font-family:var(--mono);font-size:10.5px;color:var(--dim)}
.side a.row.task{padding-left:9px;border-left:2px solid transparent}
.side a.row.task:hover{border-left-color:var(--accent)}

/* What a replication has to match. Folded away by default because it is a
   reference, not a pitch, but it is the whole reason the card is here. */
/* What the paper found, ahead of what it says about itself. An abstract is
   written to get published; this is written to be skimmed. */
.finding{margin:8px 0 6px;font-size:14.5px;line-height:1.55;color:var(--ink);
  border-left:2px solid var(--accent);padding-left:11px}
details.spec{margin-top:9px}
details.spec>summary{cursor:pointer;font-size:12px;color:var(--dim);
  font-family:var(--mono);letter-spacing:.02em}
details.spec>summary:hover{color:var(--accent)}
details.spec h4{margin:12px 0 5px;font-size:10.5px;letter-spacing:.1em;
  text-transform:uppercase;color:var(--dim)}
details.spec ul{margin:0;padding-left:17px}
details.spec li{font-size:12.5px;line-height:1.55;margin-bottom:4px}
details.spec .note{font-size:12px;color:var(--dim);margin-top:10px}
.side .more{display:inline-block;margin-top:10px;font-family:var(--serif);
  font-style:italic;font-size:14px;color:var(--soft)}
@media(max-width:1079px){.side{order:2}}

/* -------------------------------------------------------------------- bar */
.bar{display:flex;align-items:center;gap:10px;flex-wrap:wrap;margin-bottom:6px}
.tab{font-family:var(--mono);font-size:12.5px;color:var(--soft);background:none;
  border:0;border-radius:7px;padding:8px 13px;cursor:pointer}
.tab:hover{color:var(--ink)}
.tab.on{background:#e9e4da;color:#14130f;font-weight:500}
.tab.bd{border:1px solid var(--line);display:inline-flex;align-items:center;gap:7px}
.tab.bd.on{border-color:#e9e4da}
.bar .right{margin-left:auto;display:flex;gap:4px;flex-wrap:wrap}
.bar .right .tab{font-family:var(--sans);font-size:13px}

.count{color:var(--dim);font-size:12.5px;font-family:var(--mono);padding:16px 0 4px}
.note{color:var(--warn);font-size:13px;margin:0 0 12px}
.note[hidden],.card[hidden]{display:none}

/* ------------------------------------------------------------------ card */
.card{display:grid;grid-template-columns:1fr;gap:22px;padding:26px 0;
  border-bottom:1px solid var(--line)}
@media(min-width:820px){.card{grid-template-columns:200px minmax(0,1fr) 122px}}
.fig{display:block;line-height:0;align-self:start}
.fig img{width:100%;height:auto;aspect-ratio:320/414;object-fit:cover;
  object-position:top center;border:1px solid var(--line);border-radius:2px;
  display:block;background:#fff}
.gen{border:1px solid var(--line);border-radius:2px;background:var(--card);
  color:var(--ink);display:block}
.gen svg{width:100%;height:auto;display:block}
.mid{min-width:0}
.card h2{font-family:var(--serif);font-size:22px;font-weight:500;line-height:1.28;
  margin:0 0 8px;letter-spacing:-.005em}
.card h2 a:hover{color:var(--accent);text-decoration:none}
.meta{margin:0 0 10px;font-size:13.5px;color:var(--soft)}
.meta .sep{color:var(--dim);margin:0 3px}
.abs{font-family:var(--serif);font-size:15.5px;line-height:1.55;color:var(--soft);
  margin:0 0 12px;display:-webkit-box;-webkit-line-clamp:3;-webkit-box-orient:vertical;
  overflow:hidden}
.sota{font-family:var(--mono);font-size:12.5px;margin:0 0 12px;color:var(--soft)}
.sota .badge{color:var(--warn);font-weight:500}
.sota .bench{color:var(--accent)}
.sota .sep{color:var(--dim)}
.sota .expand{color:var(--soft);text-decoration:underline;text-underline-offset:3px}
.tagrow{margin:0;display:flex;gap:7px;flex-wrap:wrap;align-items:center}
.tag{font-family:var(--mono);font-size:11.5px;border:1px solid var(--line);
  border-radius:6px;padding:4px 10px;color:var(--ink);display:inline-flex;
  align-items:center;gap:6px;background:var(--card)}
.tag:hover{text-decoration:none;border-color:var(--soft)}
.dotm{width:5px;height:5px;border-radius:50%;background:currentColor;display:block}
.t-green{color:#7fd6a2}.t-blue{color:#8fb8ea}.t-pink{color:#e79ab8}
.t-purple{color:#b9a2e8}.t-amber{color:#e3b35c}.t-teal{color:#77cfc9}
.tag.t-green,.tag.t-blue,.tag.t-pink,.tag.t-purple,.tag.t-amber,.tag.t-teal{
  border-color:currentColor;background:rgba(255,255,255,.02)}
.act{font-family:var(--mono);font-size:11.5px;border:1px solid var(--line);
  border-radius:6px;padding:4px 10px;color:var(--soft);background:var(--card)}
.act:hover{color:var(--ink);text-decoration:none}

.rail{display:flex;flex-direction:row;gap:22px;align-self:start}
@media(min-width:820px){.rail{flex-direction:column;gap:18px;border-left:1px solid var(--line);
  padding-left:20px;height:100%}}
.stat{text-align:center;color:var(--soft)}
.stat svg{margin:0 auto 4px;display:block;color:var(--dim)}
.stat b{display:block;font-family:var(--mono);font-size:15px;font-weight:500;color:var(--ink)}
.stat b.hot{color:var(--ok)}
.stat span{display:block;font-family:var(--mono);font-size:9.5px;letter-spacing:.1em;
  text-transform:uppercase;color:var(--dim);margin-top:3px}

details{margin-top:14px;border-top:1px solid var(--line);padding-top:12px}
summary{cursor:pointer;font-size:13px;font-weight:500;color:var(--accent);
  font-family:var(--mono)}
details h4{font-family:var(--mono);font-size:10.5px;letter-spacing:.08em;
  text-transform:uppercase;color:var(--dim);margin:16px 0 7px;font-weight:400}
details p{font-size:13.5px;margin:0 0 8px;color:var(--soft)}
details ul{margin:0;padding-left:18px;font-size:13px;color:var(--soft);line-height:1.65}
.fine{color:var(--dim);font-size:12.5px}
table{width:100%;border-collapse:collapse;font-size:13px;margin:4px 0 0}
th{color:var(--dim);font-size:10.5px;letter-spacing:.06em;text-transform:uppercase;
  font-weight:400;text-align:left;padding:6px 8px;border-bottom:1px solid var(--line);
  font-family:var(--mono)}
td{padding:8px;border-bottom:1px solid var(--line);vertical-align:top;color:var(--soft)}
table.plain th,table.plain td{border:none;padding:5px 8px}
.n{text-align:right;font-family:var(--mono);white-space:nowrap;color:var(--ink)}
th.n{text-align:right}
.sub2{color:var(--dim);font-size:11.5px}
code{font-family:var(--mono);color:var(--ink)}
.empty{padding:54px 0;color:var(--dim);text-align:center}
footer{border-top:1px solid var(--line);color:var(--dim);font-size:12.5px;
  padding:26px 0 60px;line-height:1.75}
footer a{margin-right:18px;color:var(--soft)}
</style>
</head>
<body>

<nav class="topbar">
  <div class="wrap">
    <a class="brand" href="./"><span class="a">&alpha;</span>-Archive</a>
    <div class="nlinks">
      <a class="on" href="./">Trending</a>
      <a href="__REPO__/blob/main/docs/selection.md">Selection</a>
      <a href="__REPO__/blob/main/docs/sources.md">Sources</a>
      <a href="__REPO__/blob/main/docs/methodology.md">Methodology</a>
      <a href="__REPO__/issues/new">Submit</a>
    </div>
    <div class="navright">
      <a class="pill" href="__REPO__/issues/new">Submit feedback</a>
      <div class="searchbox">
        <svg viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor"
             stroke-width="2"><circle cx="11" cy="11" r="7"/><path d="M20 20l-3.5-3.5"/></svg>
        <input id="q" type="search" placeholder="Search papers, authors, tags..."
               autocomplete="off">
        <span class="kbd">Ctrl K</span>
      </div>
      <a class="signin" href="__REPO__">Sign in</a>
    </div>
  </div>
</nav>


<div class="wrap">
  <div class="head">
    <h1>Quantitative finance <em>with code</em></h1>
    <p class="sub">Papers rebuilt in code and scored against the numbers they printed.</p>
  </div>

  <div class="cols">
    <aside class="side">
      <div class="grp">
        <h3>Top topics</h3>
        __TOPTAGS__
        <a class="more" href="#" data-tag="">all topics &rarr;</a>
      </div>
      <div class="grp">
        <h3>Trending topics</h3>
        __TRENDTAGS__
      </div>
      <div class="grp">
        <h3>Sources</h3>
        __SOURCES__
      </div>
    </aside>

    <main>
      <div class="bar">
        <button class="tab on" data-s="ready">worth reading</button>
        <button class="tab" data-s="pct">impact</button>
        <button class="tab" data-s="vel">trending</button>
        <button class="tab" data-s="date">newest</button>
        <button class="tab" data-s="cites">most cited</button>
        <button class="tab bd" data-c="1">
          <svg viewBox="0 0 16 16" width="13" height="13" fill="currentColor"><path d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.01 8.01 0 0 0 16 8c0-4.42-3.58-8-8-8Z"/></svg>
          Has code</button>
        <button class="tab bd" data-oa="1">
          <svg viewBox="0 0 24 24" width="13" height="13" fill="none" stroke="currentColor"
               stroke-width="1.9"><rect x="4" y="10" width="16" height="10" rx="2"/><path d="M8 10V7a4 4 0 0 1 7.6-1.8"/></svg>
          Open access</button>
        <div class="right">
          <button class="tab" data-w="30">30 Days</button>
          <button class="tab" data-w="365">12 Months</button>
          <button class="tab" data-w="1826">5 Years</button>
          <button class="tab" data-w="3653">10 Years</button>
          <button class="tab on" data-w="0">All Time</button>
        </div>
      </div>

      <p class="count" id="count"></p>
      <p class="note" id="note" hidden></p>
      <div id="list">__CARDS__</div>
      <p class="empty" id="empty" hidden>No papers match.</p>
    </main>
  </div>

  <footer>
    <a href="__REPO__">GitHub</a>
    <a href="__REPO__/blob/main/docs/selection.md">Selection</a>
    <a href="__REPO__/blob/main/docs/sources.md">Sources</a>
    <a href="__REPO__/blob/main/docs/methodology.md">Methodology</a>
    <a href="__REPO__/blob/main/docs/audit.md">Audit</a>
    <a href="https://github.com/RezaSoleymanifar/vintage">Vintage</a>
    <p>Metadata and citation counts from OpenAlex; influential-citation counts from
    Semantic Scholar. Thumbnails are each paper's own first page, rendered from an
    openly distributed PDF. A result appears only where we have run the paper.
    MIT licensed. No data redistributed. Not affiliated with arXiv, OpenAlex, SSRN,
    NBER, Papers with Code, or any cited author. Not investment advice.</p>
  </footer>
</div>

<script>
var list = document.getElementById('list');
var cards = [].slice.call(document.querySelectorAll('.card'));
var q = document.getElementById('q'), count = document.getElementById('count'),
    empty = document.getElementById('empty'), note = document.getElementById('note'),
    days = 0, sortBy = 'ready', codeOnly = false, oaOnly = false, tagFilter = '';
var LABEL = {30: 'the last 30 days', 365: 'the last 12 months', 1826: 'the last 5 years',
             3653: 'the last 10 years', 0: 'all time'};
var HOW = {ready: 'by what a quant would want to read', pct: 'by normalised citation percentile',
           cites: 'by citations', vel: 'by citations per month', date: 'newest first'};
var SORT = {
  // Confidence that it is reproducible, then how numeric its published targets
  // are. A paper with exact numbers can be declared right or wrong; one with
  // prose claims can only be argued about, so it ranks below.
  ready: function (a, b) { return (+b.dataset.appeal) - (+a.dataset.appeal) ||
                                  (+b.dataset.conf) - (+a.dataset.conf); },
  pct:   function (a, b) { return (+b.dataset.pct) - (+a.dataset.pct) ||
                                  (+b.dataset.infl) - (+a.dataset.infl) ||
                                  (+b.dataset.cites) - (+a.dataset.cites); },
  cites: function (a, b) { return (+b.dataset.cites) - (+a.dataset.cites); },
  vel:   function (a, b) { return (+b.dataset.vel) - (+a.dataset.vel); },
  date:  function (a, b) { return b.dataset.date > a.dataset.date ? 1 : -1; }
};

function reorder() {
  var frag = document.createDocumentFragment();
  cards.slice().sort(function (a, b) {
    return SORT[sortBy](a, b) || (b.dataset.date > a.dataset.date ? 1 : -1);
  }).forEach(function (c) { frag.appendChild(c); });
  list.appendChild(frag);
}

function cutoff(n) {
  if (!n) return '0000-00-00';
  return new Date(Date.now() - n * 86400000).toISOString().slice(0, 10);
}

function apply() {
  var term = q.value.trim().toLowerCase(), since = cutoff(days), shown = 0, cited = 0;
  cards.forEach(function (c) {
    var pass = c.dataset.date >= since && (!codeOnly || c.dataset.code === '1') &&
               (!oaOnly || c.dataset.oa === '1') &&
               (!tagFilter || c.dataset.tags.indexOf(tagFilter) !== -1);
    var hit = !term || c.dataset.search.indexOf(term) !== -1;
    c.hidden = !(pass && hit);
    if (!c.hidden) { shown++; if (+c.dataset.cites > 0) cited++; }
  });
  count.textContent = shown + (shown === 1 ? ' paper' : ' papers') + ' from ' +
    LABEL[days] + ', ranked ' + HOW[sortBy] + (codeOnly ? ', with code' : '') +
    (oaOnly ? ', open access' : '') +
    (tagFilter ? ', tagged ' + tagFilter : '');
  empty.hidden = shown > 0;
  note.hidden = !(shown > 0 && cited === 0 && sortBy !== 'date');
  if (!note.hidden) {
    note.textContent = 'Nothing published in this window has been cited yet, ' +
      'citations take a year or more to accrue, so these are ordered by date.';
  }
}

q.addEventListener('input', apply);
document.addEventListener('keydown', function (ev) {
  if ((ev.ctrlKey || ev.metaKey) && ev.key === 'k') { ev.preventDefault(); q.focus(); }
});
document.querySelectorAll('.tab[data-w]').forEach(function (b) {
  b.addEventListener('click', function () {
    document.querySelectorAll('.tab[data-w]').forEach(function (x) { x.classList.remove('on'); });
    b.classList.add('on'); days = +b.dataset.w; apply();
  });
});
document.querySelectorAll('.tab[data-s]').forEach(function (b) {
  b.addEventListener('click', function () {
    document.querySelectorAll('.tab[data-s]').forEach(function (x) { x.classList.remove('on'); });
    b.classList.add('on'); sortBy = b.dataset.s; reorder(); apply();
  });
});
document.querySelectorAll('.tab[data-c]').forEach(function (b) {
  b.addEventListener('click', function () {
    codeOnly = !codeOnly; b.classList.toggle('on', codeOnly); apply();
  });
});
document.querySelectorAll('.tab[data-oa]').forEach(function (b) {
  b.addEventListener('click', function () {
    oaOnly = !oaOnly; b.classList.toggle('on', oaOnly); apply();
  });
});
document.querySelectorAll('[data-tag]').forEach(function (t) {
  t.addEventListener('click', function (ev) {
    ev.preventDefault();
    tagFilter = (tagFilter === t.dataset.tag) ? '' : t.dataset.tag;
    document.querySelectorAll('.side a.row').forEach(function (r) {
      r.style.color = (r.dataset.tag && r.dataset.tag === tagFilter) ? 'var(--accent)' : '';
    });
    apply();
  });
});
document.querySelectorAll('.expand').forEach(function (a) {
  a.addEventListener('click', function (ev) {
    ev.preventDefault();
    var d = a.closest('.card').querySelector('details');
    if (d) { d.open = !d.open; d.scrollIntoView({block: 'nearest'}); }
  });
});
reorder();
apply();
</script>
</body>
</html>
"""


def main() -> None:
    reps = load_replications()
    queue = load_queue()
    cites = load_citations()
    done = {REPLICATED[r["paper"]]["title"].lower() for r in reps}
    kept = [p for p in queue if p["title"].lower() not in done]
    specs = load_osap()
    # The shortlist and what has been built from it. The OSAP predictor specs
    # are still loaded for the counter, but they are not papers we read and
    # judged, and mixing them in was what made this a directory again.
    cards = ([render_replication(r, cites) for r in reps]
             + [render_queued(p) for p in kept])

    # Sidebar counts come from the corpus, so they cannot drift from it.
    counts: dict[str, int] = {}
    recent: dict[str, int] = {}
    cutoff = (datetime.now(timezone.utc) - timedelta(days=365)).strftime("%Y-%m-%d")
    for p in kept:
        for t in p["tags"]:
            counts[t] = counts.get(t, 0) + 1
            if (p.get("published") or "") >= cutoff:
                recent[t] = recent.get(t, 0) + 1
    total, total_recent = sum(counts.values()) or 1, sum(recent.values()) or 1

    # Areas and tasks, in the shape Papers With Code uses. A flat tag list said
    # "portfolio: 429" and answered nothing; a task is a page with a question on
    # it, and the count is a promise the page has papers.
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from alpha_archive import taxonomy

    toptags = ""
    for area in taxonomy.tally(kept):
        toptags += (f'<div class="area"><span class="areaname">'
                    f'{html.escape(area["area"])}</span>'
                    f'<span class="areacount">{area["count"]}</span></div>')
        for t in area["tasks"]:
            title = f' title="{html.escape(t["blurb"])}"' if t.get("blurb") else ""
            toptags += (
                f'<a class="row task" href="#" data-tag="{html.escape(t["task"])}"'
                f'{title}>{html.escape(t["task"])}<span>{t["count"]}</span></a>')

    lift = sorted(((t, (recent.get(t, 0) / total_recent) / (n / total))
                   for t, n in counts.items() if recent.get(t, 0) >= 2),
                  key=lambda kv: -kv[1])[:7]
    trendtags = "".join(
        f'<a class="row" href="#" data-tag="{html.escape(t)}">{html.escape(t)}'
        f'<span>{x:.1f}x</span></a>' for t, x in lift)

    srcs: dict[str, int] = {}
    for p in kept:
        key = p.get("source") or "other"
        srcs[key] = srcs.get(key, 0) + 1
    names = {"arxiv": "arXiv q-fin", "journal": "Journals, SSRN, NBER"}
    sources = "".join(
        f'<a class="row" href="{REPO}/blob/main/docs/sources.md">{names.get(k, k)}'
        f'<span>{n}</span></a>' for k, n in sorted(srcs.items(), key=lambda kv: -kv[1]))

    page = (PAGE.replace("__CARDS__", chr(10).join(cards))
                .replace("__TOPTAGS__", toptags)
                .replace("__TRENDTAGS__", trendtags)
                .replace("__SOURCES__", sources)
                .replace("__NPAPERS__", f"{len(cards):,}")
                .replace("__NSPEC__", f"{len(specs):,}")
                .replace("__NCODE__", str(len(reps)))
                .replace("__REPO__", REPO))
    out_dir = os.path.join(ROOT, "docs")
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, "index.html"), "w", encoding="utf-8", newline="\n") as fh:
        fh.write(page)
    print(f"wrote docs/index.html ({len(page):,} bytes), "
          f"{len(cards)} cards, {len(reps)} with results")


if __name__ == "__main__":
    main()
