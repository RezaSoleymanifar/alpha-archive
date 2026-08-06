"""Generate docs/index.html for Alpha Archive.

Data-driven: every card comes from a JSON record in data/replications/, so
running a new paper and rerunning this adds it to the site. Nothing about a
result is retyped by hand, which is the point — a replication site that
hand-copies its own numbers has the same credibility problem as a backtest
that hand-picks its sample.

    uv run python tools/build_site.py
"""

from __future__ import annotations

import glob
import html
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO = "https://github.com/RezaSoleymanifar/alpha-archive"

# Paper metadata that does not belong in a result record: where to read the
# original, and where the code that replicated it lives.
PAPERS = {
    "Mom12m": {
        "title": "Returns to Buying Winners and Selling Losers: "
                 "Implications for Stock Market Efficiency",
        "journal": "The Journal of Finance, 48(1), 65–91",
        "paper_url": "https://doi.org/10.1111/j.1540-6261.1993.tb04702.x",
        "impl_url": f"{REPO}/blob/main/alpha_archive/replications/jt1993.py",
        "run_cmd": "uv run python -m alpha_archive.replications.jt1993",
        "signal": "Rank on the return from 12 months ago to 1 month ago. "
                  "Long the top decile, short the bottom, rebalance monthly.",
    },
}

VERDICT_CLASS = {
    "decayed": "amber", "survives": "green",
    "does not survive": "red", "inconclusive": "grey", "positive": "amber",
}


def verdict_tone(verdict: str) -> str:
    for key, cls in VERDICT_CLASS.items():
        if verdict.lower().startswith(key):
            return cls
    return "grey"


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


def thumbnail(rec: dict, meta: dict) -> str:
    """A generated cover, not a scan of the paper — the original is copyrighted."""
    e = html.escape
    return f"""<div class="thumb">
      <span class="tj">{e(meta['journal'].split(',')[0])}</span>
      <span class="tt">{e(meta['title'])}</span>
      <span class="ta">{e(rec['authors'])} &middot; {rec['year']}</span>
      <span class="tm">{rec['claimed_monthly_pct']}%<i>per month claimed</i></span>
    </div>"""


def card(rec: dict) -> str:
    e = html.escape
    meta = PAPERS[rec["paper"]]
    tone = verdict_tone(rec["verdict"])
    corr = rec.get("umd_correlation")
    ok = corr is not None and corr >= 0.6

    eras = "".join(
        f"<tr><td>{e(label)}</td><td class='num'>{v['mean_monthly_pct']:+.3f}%</td>"
        f"<td class='num'>{v['t_stat']:+.2f}</td><td class='num dim'>{v['months']}</td></tr>"
        for label, v in rec.get("umd_by_era", {}).items()
    )
    caveats = "".join(f"<li>{e(c)}</li>" for c in rec.get("caveats", []))

    return f"""
  <article class="card" id="{e(rec['paper'].lower())}">
    <div class="head">
      {thumbnail(rec, meta)}
      <div class="meta">
        <span class="badge {tone}">{e(rec['verdict'].split('—')[0].strip())}</span>
        <h3>{e(meta['title'])}</h3>
        <p class="cite">{e(rec['authors'])} ({rec['year']}) &middot; {e(meta['journal'])}</p>
        <p class="sig">{e(meta['signal'])}</p>
        <div class="links">
          <a href="{meta['paper_url']}">Read the paper &rarr;</a>
          <a href="{meta['impl_url']}">Our implementation &rarr;</a>
        </div>
      </div>
    </div>

    <div class="grid">
      <div class="stat"><b>{rec['claimed_monthly_pct']}%</b>
        <span>claimed, per month</span><i>{e(rec['claimed_sample'])} &middot; t {rec['claimed_t_stat']}</i></div>
      <div class="stat"><b class="{'neg' if rec['measured_monthly_pct'] < 0 else ''}">{rec['measured_monthly_pct']}%</b>
        <span>we measured</span><i>{e(rec['measured_sample'])} &middot; t {rec['measured_t_stat']}</i></div>
      <div class="stat"><b>{rec['gap_monthly_pct']}%</b>
        <span>gap</span><i>{rec['months']} months &middot; {rec['universe_size']} names</i></div>
      <div class="stat check {'pass' if ok else 'fail'}"><b>{corr}</b>
        <span>correlation with published UMD</span>
        <i>{'implementation validated' if ok else 'implementation not validated'}</i></div>
    </div>

    <div class="verdict {tone}">
      <b>Verdict</b>
      <p>{e(rec['verdict'])}</p>
    </div>

    <details open>
      <summary>Is it us, or did the effect decay?</summary>
      <p class="lede">Before blaming a paper, check whether the published factor
      still works. If Ken French's own momentum series is flat over the same window,
      a weak result here is agreement with the literature rather than a refutation.</p>
      <table class="eras">
        <thead><tr><th>Ken French UMD</th><th class="num">mean</th>
        <th class="num">t</th><th class="num">months</th></tr></thead>
        <tbody>{eras}</tbody>
      </table>
    </details>

    <details>
      <summary>What this sample cannot tell you</summary>
      <ul class="caveats">{caveats}</ul>
    </details>

    <p class="rerun">Reproduce it: <code>{e(meta['run_cmd'])}</code>
      <span class="dim">&middot; generated {e(rec['generated_at'][:10])}</span></p>
  </article>"""


PAGE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Alpha Archive — every quantitative finance paper, replicated</title>
<meta name="description" content="Published trading signals, re-run on point-in-time data with honest costs. Each result validated against a published factor before the paper is judged.">
<meta property="og:title" content="Alpha Archive — every quantitative finance paper, replicated">
<meta property="og:description" content="Published trading signals, re-run on point-in-time data with honest costs.">
<meta property="og:type" content="website">
<link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'><rect width='32' height='32' rx='7' fill='%230b0f16'/><path d='M8 23 L16 9 L24 23' stroke='%2335e08a' stroke-width='2.6' fill='none' stroke-linecap='round' stroke-linejoin='round'/><path d='M11.5 18.5 H20.5' stroke='%2335e08a' stroke-width='2.6' stroke-linecap='round'/></svg>">
<style>
:root{
  --bg:#0b0f16;--panel:#0d1420;--line:#1f2b3a;--grid:#161f2c;
  --ink:#e8f1ec;--dim:#5f7a8c;--green:#35e08a;--red:#ff6b5e;--amber:#ffc46b;
  --mono:ui-monospace,"SF Mono","Cascadia Mono",Menlo,Consolas,monospace;
}
*{box-sizing:border-box}
body{
  margin:0;background:var(--bg);color:var(--ink);font-family:var(--mono);
  font-size:16px;line-height:1.55;
  background-image:linear-gradient(var(--grid) 1px,transparent 1px);background-size:100% 60px;
}
.wrap{max-width:960px;margin:0 auto;padding:0 20px}
a{color:var(--green);text-decoration:none}
a:hover{text-decoration:underline}
header{padding:62px 0 12px}
h1{font-size:clamp(31px,6.4vw,54px);margin:0 0 12px;letter-spacing:.03em;line-height:1.05}
h1 span{color:var(--green)}
.tag{font-size:clamp(15px,2.6vw,19px);color:var(--ink);margin:0 0 8px;max-width:34em;line-height:1.45}
.sub{color:var(--dim);font-size:14px;max-width:44em;line-height:1.6}
h2{font-size:12.5px;letter-spacing:.24em;color:var(--dim);text-transform:uppercase;
   margin:56px 0 16px;font-weight:400}

.card{background:var(--panel);border:1px solid var(--line);border-radius:13px;
      padding:22px;margin-bottom:20px}
.head{display:grid;grid-template-columns:1fr;gap:18px}
@media(min-width:720px){.head{grid-template-columns:186px 1fr}}
.thumb{display:flex;flex-direction:column;gap:6px;padding:16px 14px;border-radius:9px;
  background:linear-gradient(160deg,#131d2b,#0a1119);border:1px solid var(--line);min-height:186px}
.tj{color:var(--green);font-size:9.5px;letter-spacing:.18em;text-transform:uppercase}
.tt{color:var(--ink);font-size:12.5px;line-height:1.35;font-weight:700;margin-top:2px}
.ta{color:var(--dim);font-size:11px;margin-top:auto}
.tm{color:var(--green);font-size:21px;font-weight:700;line-height:1.1}
.tm i{display:block;color:var(--dim);font-size:9.5px;font-style:normal;letter-spacing:.1em;
      text-transform:uppercase;margin-top:2px}
.meta h3{margin:9px 0 5px;font-size:17px;line-height:1.35}
.cite{margin:0 0 9px;color:var(--dim);font-size:13px}
.sig{margin:0 0 12px;font-size:13.5px;color:var(--ink);line-height:1.55}
.links{display:flex;flex-wrap:wrap;gap:16px;font-size:13.5px}
.badge{display:inline-block;font-size:10.5px;letter-spacing:.15em;text-transform:uppercase;
  padding:3px 9px;border-radius:5px;border:1px solid}
.badge.green{color:var(--green);border-color:rgba(53,224,138,.45);background:rgba(53,224,138,.09)}
.badge.amber{color:var(--amber);border-color:rgba(255,196,107,.45);background:rgba(255,196,107,.09)}
.badge.red{color:var(--red);border-color:rgba(255,107,94,.45);background:rgba(255,107,94,.09)}
.badge.grey{color:var(--dim);border-color:var(--line)}

.grid{display:grid;grid-template-columns:1fr 1fr;gap:1px;margin:20px 0 0;
  background:var(--line);border:1px solid var(--line);border-radius:10px;overflow:hidden}
@media(min-width:760px){.grid{grid-template-columns:repeat(4,1fr)}}
.stat{background:var(--panel);padding:14px 13px}
.stat b{display:block;font-size:25px;color:var(--green);line-height:1.15}
.stat b.neg{color:var(--red)}
.stat span{display:block;color:var(--dim);font-size:11.5px;margin-top:4px;line-height:1.35}
.stat i{display:block;color:var(--dim);font-size:10.5px;font-style:normal;opacity:.75;margin-top:5px}
.check.pass b{color:var(--green)}
.check.fail b{color:var(--red)}

.verdict{margin-top:18px;padding:13px 15px;border-radius:9px;border-left:3px solid var(--dim);
  background:#0a111a}
.verdict.amber{border-left-color:var(--amber)}
.verdict.green{border-left-color:var(--green)}
.verdict.red{border-left-color:var(--red)}
.verdict b{display:block;font-size:10.5px;letter-spacing:.18em;text-transform:uppercase;
  color:var(--dim);margin-bottom:5px}
.verdict p{margin:0;font-size:14.5px;line-height:1.5}

details{margin-top:15px;border-top:1px solid var(--line);padding-top:13px}
summary{cursor:pointer;color:var(--ink);font-size:13.5px;font-weight:700}
summary::marker{color:var(--green)}
.lede{color:var(--dim);font-size:13px;line-height:1.6;margin:10px 0 12px;max-width:56em}
table{width:100%;border-collapse:collapse;font-size:13px}
th,td{text-align:left;padding:7px 10px;border-bottom:1px solid var(--line)}
th{color:var(--dim);font-weight:400;font-size:11px;letter-spacing:.1em;text-transform:uppercase}
td.num,th.num{text-align:right}
td.num{color:var(--ink);font-weight:700}
td.dim{color:var(--dim);font-weight:400}
.caveats{margin:10px 0 0;padding-left:18px;color:var(--dim);font-size:13px;line-height:1.65}
.caveats li{margin-bottom:6px}
.rerun{margin:16px 0 0;font-size:12.5px;color:var(--dim)}
.rerun code{color:var(--green)}
.dim{color:var(--dim)}

.how{display:grid;grid-template-columns:1fr;gap:12px}
@media(min-width:720px){.how{grid-template-columns:1fr 1fr 1fr}}
.step{background:var(--panel);border:1px solid var(--line);border-radius:11px;padding:17px}
.step b{display:block;color:var(--green);font-size:13px;margin-bottom:6px;letter-spacing:.05em}
.step p{margin:0;color:var(--dim);font-size:13px;line-height:1.6}
footer{padding:56px 0 70px;color:var(--dim);font-size:13px;line-height:1.7}
footer .links{margin-bottom:14px;gap:18px}
</style>
</head>
<body>
<div class="wrap">

  <header>
    <h1>Alpha <span>Archive</span></h1>
    <p class="tag">Every quantitative finance paper, replicated on point-in-time data
    with costs charged — and validated against a published factor <i>before</i> the
    paper gets judged.</p>
    <p class="sub">Roughly two thirds of published anomalies fail to replicate. Almost
    nobody re-checks them, and the ones who do publish a PDF once and stop. This runs
    continuously, shows its working, and states what each sample cannot cover. Every
    number below is produced by code in the repo, from data anyone can fetch — no
    private dataset, no local file.</p>
  </header>

  <h2>Replications</h2>
  __CARDS__

  <h2>How a replication works</h2>
  <div class="how">
    <div class="step"><b>1 &middot; Validate the code</b><p>The signal is correlated against
    a published factor first. If that fails, the finding is that we are wrong — not that
    the paper is. Our first run caught exactly this: a one-month alignment slip that put
    the correlation at 0.006 and would otherwise have shipped as a failed replication.</p></div>
    <div class="step"><b>2 &middot; Score against the claim</b><p>The paper's own numbers
    come from Chen &amp; Zimmermann's Open Source Asset Pricing, not from memory, so the
    bar is the published one and cannot drift to suit the result.</p></div>
    <div class="step"><b>3 &middot; Separate decay from bugs</b><p>If the published factor
    is also flat over our window, a weak result is agreement with the literature. That
    distinction is the difference between a finding and a headline.</p></div>
  </div>

  <h2>Built on</h2>
  <div class="how">
    <div class="step"><b>Vintage</b><p>The data layer. Point-in-time prices, filings and
    factors from the SEC, the St. Louis Fed and Dartmouth, with every value carrying the
    date it became public. <a href="https://github.com/RezaSoleymanifar/vintage">Repo</a>
    &middot; <a href="https://rezasoleymanifar.github.io/vintage/">Site</a></p></div>
    <div class="step"><b>Open Source Asset Pricing</b><p>Chen &amp; Zimmermann's documented
    scoreboard of 331 published predictors — the claimed return and t-statistic for each.
    <a href="https://www.openassetpricing.com/">openassetpricing.com</a></p></div>
    <div class="step"><b>Ken French Data Library</b><p>Dartmouth's published factors, used
    as the yardstick that validates an implementation before it is trusted.</p></div>
  </div>

  <footer>
    <div class="links">
      <a href="__REPO__">GitHub</a>
      <a href="__REPO__/blob/main/docs/methodology.md">Methodology</a>
      <a href="https://github.com/RezaSoleymanifar/vintage">Vintage</a>
    </div>
    <p>MIT licensed. Alpha Archive redistributes no data and reproduces no paper text —
    it links to originals and publishes its own code and results. Not affiliated with
    arXiv, Cornell University, or any cited author. Nothing here is investment advice.</p>
  </footer>

</div>
</body>
</html>
"""


def main() -> None:
    results = load_results()
    if not results:
        raise SystemExit("no replication records found in data/replications/")
    cards = "\n".join(card(r) for r in results)
    page = PAGE.replace("__CARDS__", cards).replace("__REPO__", REPO)

    out_dir = os.path.join(ROOT, "docs")
    os.makedirs(out_dir, exist_ok=True)
    out = os.path.join(out_dir, "index.html")
    with open(out, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(page)
    print(f"wrote {out} ({len(page):,} bytes, {len(results)} replication(s))")


if __name__ == "__main__":
    main()
