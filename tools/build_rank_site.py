"""Build the ranked corpus into the site, reusing the page the site already has.

This deliberately imports `tools/build_site.py` rather than restating it. That
file already holds the layout, the card, the rail badges, the tag colouring and
the client-side filtering, and a second copy of all of it would drift from the
first within a day. What changes here is only what the page is *about*: the
rows come from the ranked corpus instead of the replication queue, and the sort
buttons name citation metrics instead of build states.

Two things the page has to do that the old one did not:

  sort      by any of the five numbers, because a reader who distrusts
            field-weighting should be able to fall back to raw citations
            without leaving the page.
  filter    by year and by topic, because "what mattered in 2021" is a
            different question from "what matters" and the corpus spans 35
            years.

Both are done on data attributes in the browser, so the whole thing stays one
static file with no backend.

    uv run python tools/build_rank_site.py --top 400
"""

from __future__ import annotations

import argparse
import html
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))

import build_site as bs                                      # noqa: E402

OUT = os.path.join(ROOT, "docs", "index.html")
DB = os.path.join(ROOT, "data", "corpus.duckdb")

BOILERPLATE = re.compile(
    r"^(abstract|summary|purpose|this (paper|article|study)\s+"
    r"(examines|investigates|studies|considers|analyzes|analyses|explores)?)\b",
    re.I)


def idea(abstract: str, limit: int = 300) -> str:
    """The paper's point, from how its authors opened, not from a model.

    A generated summary is a summary somebody has to check, and there are fifty
    thousand of these. The abstract's first sentences are what the authors
    themselves led with, which is the closest free thing to an honest line.
    """
    text = " ".join((abstract or "").split())
    if not text:
        return ""
    parts = re.split(r"(?<=[.!?])\s+(?=[A-Z])", text)
    kept: list[str] = []
    for part in parts:
        if not kept and BOILERPLATE.match(part) and len(part) < 60:
            continue
        kept.append(part)
        if sum(len(p) for p in kept) >= limit:
            break
    out = " ".join(kept)
    return (out[:limit].rsplit(" ", 1)[0] + "…") if len(out) > limit else out


# The buttons, and the data attribute each one sorts on. Every metric on a card
# is here: a ranking whose ordering cannot be questioned from the page itself
# is asking to be taken on faith.
SORTS = [
    ("sig", "significance", "data-sig"),
    ("cites", "most cited", "data-cites"),
    ("recent", "cited lately", "data-recent"),
    ("pct", "percentile", "data-pct"),
    ("vel", "momentum", "data-vel"),
    ("date", "newest", "data-date"),
]

# Year windows. Ranges rather than "last N days" because the corpus is
# historical: the useful question is which era, not how recent.
YEARS = [("0", "All years"), ("2020", "2020s"), ("2010", "2010s"),
         ("2000", "2000s"), ("1990", "1990s")]


def rows(top: int, since: int):
    import duckdb
    con = duckdb.connect(DB)
    have = {r[0] for r in con.execute("DESCRIBE ranked").fetchall()}

    def col(name: str) -> str:
        # A harvest taken before a column existed still builds a page; the
        # field is simply blank, which is visible rather than fatal.
        return name if name in have else f"'' AS {name}"

    frame = con.execute(f"""
        SELECT score, title, authors, venue, year, date, doi, citations,
               fwci, pctile, cites_recent2, cites_prior2, is_oa, oa_url,
               topic, {col('abstract')}, {col('topics')}, {col('keywords')}
        FROM ranked WHERE year >= ? ORDER BY fwci DESC NULLS LAST LIMIT ?""",
        [since, top]).df()
    total = con.execute("SELECT count(*) FROM ranked").fetchone()[0]
    con.close()
    return frame, total


def tags_for(r) -> list[str]:
    """The paper's taxonomy, from OpenAlex's own topic and keyword fields.

    Nothing is inferred. These are labels somebody else already attached to the
    work, which is why they can be trusted enough to filter on.
    """
    out: list[str] = []
    for source in (getattr(r, "topics", "") or "", getattr(r, "keywords", "") or ""):
        for part in str(source).split("|"):
            part = part.strip()
            if part and part not in out:
                out.append(part)
    if not out and r.topic:
        out = [r.topic]
    return out[:5]


def card(r) -> str:
    e = html.escape
    link = f"https://doi.org/{r.doi}" if r.doi else (r.oa_url or "")
    tags = tags_for(r)
    mom = (r.cites_recent2 / max(r.cites_prior2 or 0, 3)) if r.cites_recent2 else 0.0
    fwci = float(r.fwci) if r.fwci is not None else 0.0

    rail = (
        '<div class="rail">'
        + bs.badge("flask", f"{fwci:,.0f}× field", cls="hot")
        + bs.badge("cite", f"{int(r.citations):,} citations")
        + (bs.badge("spark", f"{int(r.cites_recent2):,} cited 2y")
           if r.cites_recent2 else "")
        + bs.badge("calendar", str(int(r.year)))
        + (bs.badge("paper", "Paper", href=link) if link else "")
        + (bs.badge("pdf", "PDF", href=r.oa_url) if r.oa_url else "")
        + "</div>")

    tagrow = "".join(
        f'<a class="tag {bs.tag_class(t)}" href="#" data-tag="{e(t)}">'
        f'<span class="dotm"></span>{e(t)}</a>' for t in tags)

    point = idea(getattr(r, "abstract", "") or "")
    search = " ".join([str(r.title or ""), str(r.authors or ""),
                       str(r.venue or ""), *tags]).lower()

    return f"""
  <article class="card" data-status="ok" data-search="{e(search)}"
           data-sig="{fwci:.4f}" data-cites="{int(r.citations)}"
           data-recent="{int(r.cites_recent2 or 0)}"
           data-pct="{float(r.pctile or 0):.4f}" data-vel="{mom:.4f}"
           data-date="{e(str(r.date or ''))}" data-year="{int(r.year)}"
           data-oa="{1 if r.is_oa else 0}" data-code="0"
           data-tags="{e(' '.join(tags))}">
    <div class="mid">
      <h2><a href="{e(link)}" target="_blank" rel="noopener">{e(str(r.title or ''))}</a></h2>
      <p class="meta">{e(str(r.authors or '')[:130])}
        <span class="sep">&middot;</span> {e(str(r.venue or 'unpublished'))}
        <span class="sep">&middot;</span> {int(r.year)}
        <span class="sep">&middot;</span> {int(r.citations):,} citations</p>
      {f'<p class="finding">{e(point)}</p>' if point else ''}
      <p class="tagrow">{tagrow}</p>
    </div>
    {rail}
  </article>"""


def sidebar(frame) -> tuple[str, str, str]:
    """Topics by count, topics by momentum, and the journals carrying them.

    Every number in here is counted from the rows on the page. Nothing is a
    round figure somebody liked the look of, which matters because a sidebar
    is exactly where invented numbers hide.
    """
    from collections import Counter, defaultdict

    tags = Counter(t for r in frame.itertuples() for t in tags_for(r))
    venues = Counter(str(r.venue) for r in frame.itertuples() if r.venue)

    # Trending: citations earned in the last two years over the two before,
    # averaged across a topic's papers. A topic at 2.4x is one the field has
    # started citing twice as fast, which is a different fact from being large.
    recent, prior = defaultdict(int), defaultdict(int)
    for r in frame.itertuples():
        for t in tags_for(r):
            recent[t] += int(r.cites_recent2 or 0)
            prior[t] += int(r.cites_prior2 or 0)
    trend = {t: recent[t] / max(prior[t], 1) for t in recent
             if tags[t] >= 4 and prior[t] >= 20}

    def rowset(counter, limit: int) -> str:
        return "".join(
            f'<a class="row" href="#" data-tag="{html.escape(name)}">'
            f'<span>{html.escape(name)}</span><b>{count:,}</b></a>'
            for name, count in counter.most_common(limit))

    # Only genuine risers. A "trending" list whose entries are all below 1.0 is
    # a list of topics in decline wearing the wrong label, so if nothing is
    # rising the section says so rather than filling itself.
    rising = [(n, v) for n, v in sorted(trend.items(), key=lambda kv: -kv[1])
              if v > 1.0][:8]
    trending = "".join(
        f'<a class="row" href="#" data-tag="{html.escape(name)}">'
        f'<span>{html.escape(name)}</span><b>{ratio:.1f}&times;</b></a>'
        for name, ratio in rising) or (
        '<p class="more" style="font-style:normal">No topic on this page is '
        'being cited faster than it was two years ago.</p>')

    return rowset(tags, 12), trending, rowset(venues, 12)


def build(top: int, since: int) -> str:
    frame, total = rows(top, since)
    cards = "".join(card(r) for r in frame.itertuples())
    toptags, trendtags, journals = sidebar(frame)

    page = bs.PAGE
    page = page.replace(
        "<h1>Quantitative finance <em>with code</em></h1>",
        "<h1>Quantitative finance research <em>that matters</em></h1>")
    page = page.replace(
        "<p class=\"sub\">Papers rebuilt in code and scored against the numbers "
        "they printed.</p>",
        f'<p class="sub">Ranked by significance in the field. '
        f'{total:,} papers, each scored against what work of its own age and '
        f'field normally earns.</p>')

    # The sort bar. Replaced wholesale rather than patched, because every button
    # on the old one named a build state and none of them exist here.
    old_bar = page[page.index('<div class="bar">'):page.index('<p class="note"')]
    new_bar = ('<div class="bar">'
               + "".join(f'<button class="tab{" on" if i == 0 else ""}" '
                         f'data-s="{key}">{label}</button>'
                         for i, (key, label, _) in enumerate(SORTS))
               + '<button class="tab bd" data-oa="1">Open access</button>'
               + '<div class="right">'
               + "".join(f'<button class="tab{" on" if y == "0" else ""}" '
                         f'data-y="{y}">{label}</button>' for y, label in YEARS)
               + '</div></div>\n\n      ')
    page = page.replace(old_bar, new_bar)

    # The old card is a three-column grid whose first column is the paper's
    # scanned first page. There are no scans here -- OpenAlex gives metadata,
    # not PDFs -- so the grid loses that column and the rail keeps its width.
    # A card built for a thumbnail and an abstract leaves a hole when it has
    # neither. Nothing here invents content to fill it; the card is simply
    # shorter, which is what a card with less in it should be.
    page = page.replace(".card{display:grid;grid-template-columns:1fr;gap:22px;padding:26px 0;",
                        ".card{display:grid;grid-template-columns:1fr;gap:22px;padding:15px 0;")

    # "Sign in" signs into nothing. A control that does not work is the same
    # class of lie as a number that was made up.
    page = re.sub(r'<a class="signin"[^>]*>.*?</a>', "", page, flags=re.S)

    page = page.replace(
        "@media(min-width:820px){.card{grid-template-columns:200px minmax(0,1fr) 122px}}",
        "@media(min-width:820px){.card{grid-template-columns:minmax(0,1fr) 150px}}")

    page = page.replace(
        "Quantitative Finance with Code, papers rebuilt and checked "
        "against their own numbers",
        "Quantitative finance research that matters")

    page = (page.replace("__TOPTAGS__", toptags)
            .replace("__TRENDTAGS__", trendtags)
            .replace("__SOURCES__", journals)
            .replace("__CARDS__", cards)
            .replace("Top topics", "Topics")
            .replace("Trending topics", "Trending topics")
            .replace("<h3>Sources</h3>", "<h3>Journals</h3>")
            .replace("__REPO__", bs.REPO))

    # The client-side sorting and the year filter. The old script sorted on
    # build-readiness and filtered on a rolling day window; both are replaced.
    page = re.sub(r"var SORT = \{.*?\n\};",
                  "var SORT = {\n"
                  + "".join(
                      f"  {key}: function (a, b) {{ return "
                      + (f"(b.dataset.date > a.dataset.date ? 1 : -1); }},\n"
                         if key == "date" else
                         f"(+b.dataset.{attr.split('-')[1]}) - "
                         f"(+a.dataset.{attr.split('-')[1]}); }},\n")
                      for key, _, attr in SORTS)
                  + "};", page, flags=re.S)
    page = page.replace("sortBy = 'ready'", "sortBy = 'sig'")
    page = page.replace("days = 0,", "fromYear = 0,")
    page = page.replace(
        "var pass = c.dataset.date >= since && (!codeOnly || c.dataset.code === '1') &&",
        "var pass = (!fromYear || (+c.dataset.year >= fromYear &&\n"
        "                 +c.dataset.year < fromYear + 10)) &&")
    page = page.replace("var term = q.value.trim().toLowerCase(), since = cutoff(days),",
                        "var term = q.value.trim().toLowerCase(),")
    page = page.replace(
        """document.querySelectorAll('.tab[data-w]').forEach(function (b) {
  b.addEventListener('click', function () {
    document.querySelectorAll('.tab[data-w]').forEach(function (x) { x.classList.remove('on'); });
    b.classList.add('on'); days = +b.dataset.w; apply();
  });
});""",
        """document.querySelectorAll('.tab[data-y]').forEach(function (b) {
  b.addEventListener('click', function () {
    document.querySelectorAll('.tab[data-y]').forEach(function (x) { x.classList.remove('on'); });
    b.classList.add('on'); fromYear = +b.dataset.y; apply();
  });
});""")
    return page


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--top", type=int, default=400)
    ap.add_argument("--since", type=int, default=1990)
    args = ap.parse_args()

    page = build(args.top, args.since)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(page)
    print(f"{args.top:,} cards -> {OUT} ({len(page):,} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
