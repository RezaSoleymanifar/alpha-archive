"""Generate docs/index.html for Alpha Archive.

Data-driven: every entry comes from a JSON record in data/replications/, so
running a paper and rerunning this adds it. Nothing about a result is retyped
by hand — a replication site that hand-copies its own numbers has the same
credibility problem as a backtest that hand-picks its sample.

The look is deliberate: an arXiv listing (serif titles, dense citation lines,
identifiers down the left) rendered on a CRT (scanlines, phosphor glow, and a
high-score table where the verdicts go). Papers are the content; the arcade is
the scoreboard, because "did this survive" really is a score.

    uv run python tools/build_site.py
"""

from __future__ import annotations

import glob
import html
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO = "https://github.com/RezaSoleymanifar/alpha-archive"

PAPERS = {
    "Mom12m": {
        "id": "AA-0001",
        "title": "Returns to Buying Winners and Selling Losers: "
                 "Implications for Stock Market Efficiency",
        "journal": "The Journal of Finance, 48(1), 65–91",
        "paper_url": "https://doi.org/10.1111/j.1540-6261.1993.tb04702.x",
        "impl_url": f"{REPO}/blob/main/alpha_archive/replications/jt1993.py",
        "run_cmd": "uv run python -m alpha_archive.replications.jt1993",
        "abstract": "Rank stocks on the return from twelve months ago to one month "
                    "ago. Buy the top decile, sell the bottom, rebalance monthly. The "
                    "original reports a strategy earning about 1% per month over "
                    "1964–1989, which became one of the most cited results in finance.",
        "class": "q-fin.PM",
    },
}

# Arcade verdicts. The word people remember is the one in the scoreboard.
TONES = [
    ("unverified", "UNVERIFIED", "grey"),
    ("survives", "PASS", "green"),
    ("decayed", "DECAYED", "amber"),
    ("positive", "WEAK", "amber"),
    ("does not survive", "FAIL", "red"),
    ("inconclusive", "NO READ", "grey"),
]


def tone(verdict: str) -> tuple[str, str]:
    for key, label, cls in TONES:
        if verdict.lower().startswith(key):
            return label, cls
    return "NO READ", "grey"


def load_results() -> list[dict]:
    out = []
    for path in sorted(glob.glob(os.path.join(ROOT, "data", "replications", "*.json"))):
        with open(path, encoding="utf-8") as fh:
            try:
                rec = json.load(fh)
            except json.JSONDecodeError:
                continue
        if "measured_monthly_pct" in rec and rec.get("paper") in PAPERS:
            out.append(rec)
    return out


def scoreboard(results: list[dict]) -> str:
    rows = []
    for r in results:
        meta = PAPERS[r["paper"]]
        label, cls = tone(r["verdict"])
        corr = r.get("umd_correlation")
        rows.append(
            f'<tr><td class="rk">{meta["id"]}</td>'
            f'<td class="nm"><a href="#{r["paper"].lower()}">{html.escape(r["paper"])}</a>'
            f'<i>{html.escape(r["authors"])} {r["year"]}</i></td>'
            f'<td class="num">{r["claimed_monthly_pct"]}%</td>'
            f'<td class="num {"neg" if r["measured_monthly_pct"] < 0 else ""}">'
            f'{r["measured_monthly_pct"]}%</td>'
            f'<td class="num">{corr}</td>'
            f'<td><span class="verdict {cls}">{label}</span></td></tr>'
        )
    return f"""<table class="board">
      <thead><tr><th>ID</th><th>SIGNAL</th><th class="num">CLAIMED</th>
      <th class="num">MEASURED</th><th class="num">SANITY r</th><th>STATUS</th></tr></thead>
      <tbody>{''.join(rows)}</tbody>
    </table>"""


def _verification_block(rec: dict) -> str:
    """The criterion, and why it has or has not been met.

    Declared before the run in alpha_archive.verification, against a fixture we
    did not produce. Rendering it here means a visitor can check that the bar
    was not moved to fit the number.
    """
    e = html.escape
    v = rec.get("verification")
    if not v:
        return ""
    crit = v.get("criterion", {})
    return f"""<div class="verify {'ok' if v['status'] == 'VERIFIED' else 'no'}">
        <b>VERIFICATION &middot; {e(v['status'])}</b>
        <p class="vreason">{e(v['reason'])}</p>
        <dl>
          <dt>criterion</dt><dd>{e(str(crit.get('statistic','')))} &ge; {crit.get('threshold','')}</dd>
          <dt>fixture</dt><dd>{e(str(crit.get('fixture','')))}</dd>
          <dt>declared by</dt><dd>{e(str(crit.get('fixture_source','')))} &mdash; not by us</dd>
          <dt>why that bar</dt><dd>{e(str(crit.get('rationale','')))}</dd>
        </dl>
      </div>"""


def entry(rec: dict) -> str:
    e = html.escape
    meta = PAPERS[rec["paper"]]
    label, cls = tone(rec["verdict"])
    corr = rec.get("umd_correlation")
    ok = corr is not None and corr >= 0.6

    eras = "".join(
        f"<tr><td>{e(k)}</td><td class='num'>{v['mean_monthly_pct']:+.3f}%</td>"
        f"<td class='num'>{v['t_stat']:+.2f}</td><td class='num dim'>{v['months']}</td></tr>"
        for k, v in rec.get("umd_by_era", {}).items()
    )
    caveats = "".join(f"<li>{e(c)}</li>" for c in rec.get("caveats", []))

    return f"""
  <article class="entry" id="{e(rec['paper'].lower())}">
    <aside class="ident">
      <span class="aid">{meta['id']}</span>
      <span class="cls">{meta['class']}</span>
      <span class="verdict {cls} big">{label}</span>
      <span class="corr bad">r = {corr}</span>
      <span class="corrnote">sanity check only &mdash; does not verify parity</span>
    </aside>

    <div class="body">
      <h3><a href="{meta['paper_url']}">{e(meta['title'])}</a></h3>
      <p class="byline">{e(rec['authors'])} &nbsp;({rec['year']})</p>
      <p class="cite">{e(meta['journal'])}</p>
      <p class="abstract"><b>Signal.</b> {e(meta['abstract'])}</p>

      <div class="scores">
        <div><span>CLAIMED</span><b>{rec['claimed_monthly_pct']}%</b>
          <i>{e(rec['claimed_sample'])} &middot; t&nbsp;{rec['claimed_t_stat']}</i></div>
        <div><span>MEASURED</span><b class="{'neg' if rec['measured_monthly_pct'] < 0 else ''}">
          {rec['measured_monthly_pct']}%</b>
          <i>{e(rec['measured_sample'])} &middot; t&nbsp;{rec['measured_t_stat']}</i></div>
        <div><span>GAP</span><b>{rec['gap_monthly_pct']}%</b>
          <i>{rec['months']} months &middot; {rec['universe_size']} names</i></div>
      </div>

      {_verification_block(rec)}

      <details open>
        <summary>Is it us, or did the effect decay?</summary>
        <p class="note">Before blaming a paper, check whether the published factor still
        works. If Ken French's own momentum series is flat over the same window, a weak
        result here is agreement with the literature rather than a refutation.</p>
        <table class="eras"><thead><tr><th>Ken French UMD</th><th class="num">mean</th>
        <th class="num">t</th><th class="num">n</th></tr></thead><tbody>{eras}</tbody></table>
      </details>

      <details>
        <summary>What this sample cannot tell you</summary>
        <ul class="caveats">{caveats}</ul>
      </details>

      <p class="links">
        <a href="{meta['paper_url']}">[ paper ]</a>
        <a href="{meta['impl_url']}">[ our code ]</a>
        <code>{e(meta['run_cmd'])}</code>
        <span class="dim">rerun {e(rec['generated_at'][:10])}</span>
      </p>
    </div>
  </article>"""


PAGE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Alpha Archive — every quantitative finance paper, replicated</title>
<meta name="description" content="Published trading signals re-run on point-in-time data with costs charged, each validated against a published factor before the paper is judged.">
<meta property="og:title" content="Alpha Archive — every quantitative finance paper, replicated">
<meta property="og:description" content="Published trading signals, re-run on point-in-time data with honest costs.">
<meta property="og:type" content="website">
<link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'><rect width='32' height='32' rx='6' fill='%23070a0e'/><path d='M7 24 L16 8 L25 24' stroke='%2335e08a' stroke-width='2.8' fill='none' stroke-linecap='round' stroke-linejoin='round'/><path d='M11 19 H21' stroke='%2335e08a' stroke-width='2.8' stroke-linecap='round'/></svg>">
<style>
:root{
  --bg:#070a0e;--panel:#0b1017;--line:#1b2733;--ink:#dfe9e3;--dim:#5d7789;
  --green:#35e08a;--red:#ff6b5e;--amber:#ffc46b;--blue:#7fb3ff;
  --mono:ui-monospace,"SF Mono","Cascadia Mono",Menlo,Consolas,monospace;
  --serif:"Iowan Old Style","Palatino Linotype",Palatino,Georgia,"Times New Roman",serif;
}
*{box-sizing:border-box}
body{
  margin:0;background:var(--bg);color:var(--ink);font-family:var(--mono);
  font-size:15.5px;line-height:1.6;
}
/* CRT scanlines — the arcade half, kept faint enough to read through. */
body::before{
  content:"";position:fixed;inset:0;pointer-events:none;z-index:9;
  background:repeating-linear-gradient(180deg,rgba(0,0,0,.22) 0 1px,transparent 1px 3px);
  mix-blend-mode:multiply;
}
body::after{
  content:"";position:fixed;inset:0;pointer-events:none;z-index:8;
  background:radial-gradient(120% 90% at 50% 40%,transparent 55%,rgba(0,0,0,.55) 100%);
}
.wrap{max-width:1020px;margin:0 auto;padding:0 20px;position:relative;z-index:1}
a{color:var(--green);text-decoration:none}
a:hover{text-decoration:underline}

/* ------------------------------------------------------------- masthead */
.masthead{border-bottom:2px solid var(--green);padding:34px 0 16px;margin-bottom:6px}
.brand{display:flex;align-items:baseline;gap:14px;flex-wrap:wrap}
h1{
  font-size:clamp(28px,5.6vw,46px);margin:0;letter-spacing:.14em;font-weight:700;
  color:var(--green);text-shadow:0 0 14px rgba(53,224,138,.45),0 0 34px rgba(53,224,138,.18);
}
.brand .sub{color:var(--dim);font-size:11.5px;letter-spacing:.3em;text-transform:uppercase}
.strap{font-family:var(--serif);font-size:clamp(16px,2.7vw,21px);line-height:1.45;
  margin:14px 0 0;max-width:40em;color:var(--ink)}
.intro{color:var(--dim);font-size:13.5px;max-width:52em;margin:10px 0 0;line-height:1.7}

h2{font-size:11.5px;letter-spacing:.3em;color:var(--dim);text-transform:uppercase;
   margin:46px 0 14px;font-weight:400;display:flex;align-items:center;gap:12px}
h2::after{content:"";flex:1;height:1px;background:var(--line)}

/* ----------------------------------------------------------- scoreboard */
.board{width:100%;border-collapse:collapse;font-size:13px;
  border:1px solid var(--line);background:var(--panel)}
.board th{
  background:#080d13;color:var(--dim);font-size:10px;letter-spacing:.22em;
  padding:10px 12px;text-align:left;border-bottom:1px solid var(--line);font-weight:400;
}
.board td{padding:11px 12px;border-bottom:1px solid var(--line);vertical-align:middle}
.board tr:last-child td{border-bottom:none}
.board .rk{color:var(--dim);font-size:11.5px;letter-spacing:.1em;white-space:nowrap}
.board .nm{font-weight:700}
.board .nm i{display:block;color:var(--dim);font-weight:400;font-style:normal;font-size:11.5px}
.num{text-align:right}
td.num{font-weight:700;white-space:nowrap}
td.num.neg{color:var(--red)}
.verdict{
  display:inline-block;padding:3px 10px;border-radius:3px;border:1px solid;
  font-size:10.5px;letter-spacing:.2em;font-weight:700;white-space:nowrap;
}
.verdict.big{font-size:12px;padding:6px 12px;text-align:center}
.verdict.green{color:var(--green);border-color:var(--green);background:rgba(53,224,138,.1);
  text-shadow:0 0 10px rgba(53,224,138,.5)}
.verdict.amber{color:var(--amber);border-color:var(--amber);background:rgba(255,196,107,.1);
  text-shadow:0 0 10px rgba(255,196,107,.45)}
.verdict.red{color:var(--red);border-color:var(--red);background:rgba(255,107,94,.1);
  text-shadow:0 0 10px rgba(255,107,94,.45)}
.verdict.grey{color:var(--dim);border-color:var(--line)}

/* --------------------------------------------------------------- entries */
.entry{display:grid;grid-template-columns:1fr;gap:18px;padding:24px 0;
  border-bottom:1px solid var(--line)}
@media(min-width:760px){.entry{grid-template-columns:132px 1fr;gap:26px}}
.ident{display:flex;flex-direction:column;gap:7px;align-items:flex-start}
.aid{color:var(--green);font-size:12.5px;letter-spacing:.14em;font-weight:700}
.cls{color:var(--dim);font-size:10.5px;letter-spacing:.14em}
.corr{font-size:19px;font-weight:700;margin-top:4px}
.corr.ok{color:var(--green)}
.corr.bad{color:var(--red)}
.corrnote{color:var(--dim);font-size:10px;letter-spacing:.06em;line-height:1.35}

.body h3{font-family:var(--serif);font-size:clamp(19px,3vw,25px);line-height:1.28;
  margin:0 0 7px;font-weight:600}
.body h3 a{color:var(--ink)}
.byline{font-family:var(--serif);font-size:16px;margin:0 0 3px;color:var(--ink)}
.cite{color:var(--dim);font-size:12.5px;margin:0 0 13px}
.abstract{font-family:var(--serif);font-size:15.5px;line-height:1.62;margin:0 0 16px;
  color:var(--ink);max-width:58em}
.abstract b{color:var(--green);font-family:var(--mono);font-size:12px;letter-spacing:.1em}

.scores{display:grid;grid-template-columns:1fr 1fr;gap:1px;background:var(--line);
  border:1px solid var(--line);margin-bottom:15px}
@media(min-width:640px){.scores{grid-template-columns:repeat(3,1fr)}}
.scores div{background:var(--panel);padding:12px 13px}
.scores span{display:block;color:var(--dim);font-size:9.5px;letter-spacing:.22em}
.scores b{display:block;font-size:26px;line-height:1.2;color:var(--green);margin-top:3px;
  text-shadow:0 0 12px rgba(53,224,138,.35)}
.scores b.neg{color:var(--red);text-shadow:0 0 12px rgba(255,107,94,.35)}
.scores i{display:block;color:var(--dim);font-size:10.5px;font-style:normal;margin-top:4px}

.verify{border:1px solid var(--line);border-left:3px solid var(--dim);padding:12px 14px;
  margin:0 0 15px;background:rgba(255,255,255,.015)}
.verify.no{border-left-color:var(--red)}
.verify.ok{border-left-color:var(--green)}
.verify b{display:block;color:var(--red);letter-spacing:.2em;font-size:11px;margin-bottom:7px}
.verify.ok b{color:var(--green)}
.vreason{margin:0 0 10px;font-size:13px;line-height:1.6;color:var(--ink)}
.verify dl{margin:0;display:grid;grid-template-columns:1fr;gap:2px 14px;font-size:12px}
@media(min-width:640px){.verify dl{grid-template-columns:110px 1fr}}
.verify dt{color:var(--dim);letter-spacing:.12em;font-size:10px;padding-top:3px}
.verify dd{margin:0 0 6px;color:var(--ink);line-height:1.55}

details{border-top:1px solid var(--line);padding-top:11px;margin-top:11px}
summary{cursor:pointer;font-size:13px;font-weight:700;color:var(--ink)}
summary::marker{color:var(--green)}
.note{color:var(--dim);font-size:12.5px;line-height:1.65;margin:9px 0 11px;max-width:56em}
.eras{width:100%;border-collapse:collapse;font-size:12.5px}
.eras th,.eras td{text-align:left;padding:6px 10px;border-bottom:1px solid var(--line)}
.eras th{color:var(--dim);font-size:10px;letter-spacing:.14em;font-weight:400}
.eras td.num{color:var(--ink)}
.eras td.dim{color:var(--dim);font-weight:400}
.caveats{margin:9px 0 0;padding-left:17px;color:var(--dim);font-size:12.5px;line-height:1.65}
.caveats li{margin-bottom:5px}
.links{margin:15px 0 0;font-size:12px;display:flex;flex-wrap:wrap;gap:14px;align-items:center}
.links code{color:var(--green);opacity:.8}
.dim{color:var(--dim)}

/* ---------------------------------------------------------------- panels */
.how{display:grid;grid-template-columns:1fr;gap:12px}
@media(min-width:720px){.how{grid-template-columns:1fr 1fr 1fr}}
.step{background:var(--panel);border:1px solid var(--line);padding:16px}
.step b{display:block;color:var(--green);font-size:11px;letter-spacing:.18em;margin-bottom:7px}
.step p{margin:0;color:var(--dim);font-size:12.5px;line-height:1.65}
footer{padding:48px 0 66px;color:var(--dim);font-size:12.5px;line-height:1.75}
footer .flinks{display:flex;flex-wrap:wrap;gap:18px;margin-bottom:13px}
</style>
</head>
<body>
<div class="wrap">

  <div class="masthead">
    <div class="brand">
      <h1>ALPHA ARCHIVE</h1>
      <span class="sub">replication registry</span>
    </div>
    <p class="strap">Every quantitative finance paper, re-run on point-in-time data with
    costs charged — and validated against a published factor <i>before</i> the paper is
    judged.</p>
    <p class="intro">Roughly two thirds of published anomalies fail to replicate. Almost
    nobody re-checks them, and those who do publish once and stop. This runs continuously,
    shows its working, and states what each sample cannot cover.</p>
    <p class="intro"><b style="color:var(--green)">A replication is only marked verified when it
    clears a threshold written down before the run, measured against a fixture we did not
    produce.</b> If the fixture cannot be fetched, the status is unverified — not a pass with
    an asterisk. There is no "partially validated" tier, because that is the phrase you reach
    for when you want credit you have not earned. Every figure below comes from code in the
    repository, from data anyone can fetch.</p>
  </div>

  <h2>Scoreboard</h2>
  __BOARD__

  <h2>Replications</h2>
  __ENTRIES__

  <h2>How a replication works</h2>
  <div class="how">
    <div class="step"><b>01 &middot; DECLARE THE BAR</b><p>The criterion is written down before
    the run, against a fixture we did not produce, and frozen. The first version of this failed
    that test: the bar was set at 0.6 after 0.9 turned out to be unreachable. Moving a threshold
    to fit a result is the thing this project exists to catch.</p></div>
    <div class="step"><b>02 &middot; SCORE THE CLAIM</b><p>The paper's own numbers come from
    Chen &amp; Zimmermann's Open Source Asset Pricing, not from memory, so the bar is the
    published one and cannot drift to suit the result.</p></div>
    <div class="step"><b>03 &middot; DECAY OR BUG</b><p>If the published factor is also flat
    over our window, a weak result is agreement with the literature. That distinction is the
    difference between a finding and a headline.</p></div>
  </div>

  <h2>Built on</h2>
  <div class="how">
    <div class="step"><b>VINTAGE</b><p>The data layer. Point-in-time prices, filings and
    factors from the SEC, the St. Louis Fed and Dartmouth, every value carrying the date it
    became public. <a href="https://github.com/RezaSoleymanifar/vintage">Repo</a> &middot;
    <a href="https://rezasoleymanifar.github.io/vintage/">Site</a></p></div>
    <div class="step"><b>OPEN SOURCE ASSET PRICING</b><p>Chen &amp; Zimmermann's documented
    scoreboard of 331 published predictors — the claimed return and t-statistic for each.
    <a href="https://www.openassetpricing.com/">openassetpricing.com</a></p></div>
    <div class="step"><b>KEN FRENCH DATA LIBRARY</b><p>Dartmouth's published factors, used as
    the yardstick that validates an implementation before it is trusted.</p></div>
  </div>

  <footer>
    <div class="flinks">
      <a href="__REPO__">GitHub</a>
      <a href="__REPO__/blob/main/docs/methodology.md">Methodology</a>
      <a href="https://github.com/RezaSoleymanifar/vintage">Vintage</a>
    </div>
    <p>MIT licensed. Alpha Archive redistributes no data and reproduces no paper text — it
    links to originals and publishes its own code and results. Not affiliated with arXiv,
    Cornell University, or any cited author. Nothing here is investment advice.</p>
  </footer>

</div>
</body>
</html>
"""


def main() -> None:
    results = load_results()
    if not results:
        raise SystemExit("no replication records found in data/replications/")

    page = (
        PAGE.replace("__BOARD__", scoreboard(results))
        .replace("__ENTRIES__", "\n".join(entry(r) for r in results))
        .replace("__REPO__", REPO)
    )

    out_dir = os.path.join(ROOT, "docs")
    os.makedirs(out_dir, exist_ok=True)
    out = os.path.join(out_dir, "index.html")
    with open(out, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(page)
    print(f"wrote {out} ({len(page):,} bytes, {len(results)} replication(s))")


if __name__ == "__main__":
    main()
