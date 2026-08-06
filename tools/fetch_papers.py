"""Pull the index's paper universe and render arXiv first pages as thumbnails.

Two halves, deliberately equal. One hundred come from arXiv q-fin, one hundred
from the core finance journals — Journal of Finance, JFE, RFS, JFQA and the
rest. Both halves are drawn the same way: OpenAlex, sorted by citations, so the
index is ranked by how often the field actually cites the work rather than by
how recently it appeared.

Citations come from OpenAlex `cited_by_count` (free, no key, polite pool via
mailto). Nothing here is a scrape: arXiv metadata comes from arXiv, journal
metadata from OpenAlex, and the only file fetched is the openly distributed
arXiv PDF whose first page becomes the thumbnail.

    uv run python tools/fetch_papers.py                 # 100 + 100, with thumbnails
    uv run python tools/fetch_papers.py --no-thumbs     # metadata only, fast
"""

from __future__ import annotations

import argparse
import json
import os
import re
import time
from datetime import datetime, timedelta, timezone

import httpx
import pypdfium2 as pdfium

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAPERS_JSON = os.path.join(ROOT, "data", "papers", "papers.json")
CITES_JSON = os.path.join(ROOT, "data", "papers", "citations.json")
THUMB_DIR = os.path.join(ROOT, "docs", "thumbs")

MAILTO = os.environ.get("ALPHA_ARCHIVE_MAILTO", "reza@soleymanifar.com")
UA = {"User-Agent": f"Alpha Archive ({MAILTO})"}
OPENALEX = "https://api.openalex.org/works"

ARXIV_SOURCE = "S4306400194"          # arXiv, as an OpenAlex source
FINANCE_SUBFIELD = "subfields/2003"   # Finance, so q-bio and ML noise stay out

# The journals publish development economics and tax policy beside asset
# pricing, and a citation ranking over the whole field surfaces the former.
# These are the OpenAlex topics a quant desk would actually read.
QUANT_TOPICS = [
    "T10047",   # Financial Markets and Investment Strategies
    "T11059",   # Market Dynamics and Volatility
    "T10067",   # Stochastic processes and financial applications
    "T10282",   # Financial Risk and Volatility Modeling
    "T11270",   # Complex Systems and Time Series Analysis
    "T12137",   # Economic theories and models — where CAPM and Jensen–Meckling sit
    "T11496",   # Credit Risk and Financial Regulations
]

# Where quants actually read, by tier. ISSNs, because journal names are ambiguous.
# SSRN is in here on purpose: it has no API of its own, but its DOIs are
# registered with Crossref, so OpenAlex carries the metadata and the citation
# count. Only the PDF and SSRN's own download ranking need a scrape, and we do
# not take either.
JOURNAL_ISSNS = [
    # tier 1 — the preprint tier, where finance work appears first
    "1556-5068",   # SSRN Electronic Journal (incl. the Financial Economics Network)
    # tier 2 — the big three, and what sits beside them
    "0022-1082",   # Journal of Finance
    "0304-405X",   # Journal of Financial Economics
    "0893-9454",   # Review of Financial Studies
    "0022-1090",   # Journal of Financial and Quantitative Analysis
    "1572-3097",   # Review of Finance
    "0025-1909",   # Management Science
    "2045-9920",   # Review of Asset Pricing Studies
    "0378-4266",   # Journal of Banking & Finance
    "0927-5398",   # Journal of Empirical Finance
    "1386-4181",   # Journal of Financial Markets
    "0046-3892",   # Financial Management
    # tier 3 — practitioner-facing, implementation-aware
    "0015-198X",   # Financial Analysts Journal (CFA Institute)
    "0095-4918",   # Journal of Portfolio Management
    "2640-3943",   # Journal of Financial Data Science
    "1469-7688",   # Quantitative Finance
    "2047-1238",   # Journal of Investment Strategies
    "1074-1240",   # Journal of Derivatives
    "1059-8596",   # Journal of Fixed Income
    "1465-1211",   # Journal of Risk
]

# Working-paper series that carry no ISSN and so need their OpenAlex source id.
SERIES_SOURCES = ["S2809516038"]      # NBER Working Papers

# The leaderboard windows. Each is a publication-date cohort, ranked inside
# itself by citations — a month-old paper is never asked to out-cite Fama.
WINDOWS = [("30d", 30), ("12m", 365), ("5y", 1826), ("10y", 3653), ("all", None)]

# DOIs of the papers we have actually replicated, so their citation counts stay
# live rather than being typed in once and quietly going stale.
REPLICATED_DOIS = {
    "Mom12m": "10.1111/j.1540-6261.1993.tb04702.x",
    "Darmanin2026": "10.48550/arxiv.2607.20093",
}

THUMB_W = 320          # rendered wide, displayed smaller, so it stays crisp on retina

# Rough topical routing, so cards carry tags a reader can filter on.
TAG_RULES = [
    ("momentum", r"momentum|trend follow"),
    ("reversal", r"reversal|mean.revers"),
    ("volatility", r"volatilit|garch|realized vol"),
    ("machine-learning", r"machine learning|neural|deep learning|transformer|LLM|reinforcement"),
    ("options", r"option|implied vol|derivative pricing"),
    ("crypto", r"crypto|bitcoin|defi|blockchain|token"),
    ("portfolio", r"portfolio|allocation|optimi[sz]ation|risk parity"),
    ("microstructure", r"microstructur|limit order|high.frequenc|order flow"),
    ("factors", r"factor|cross.section|anomal|asset pricing"),
    ("risk", r"risk management|drawdown|tail risk|var\b|expected shortfall"),
    ("macro", r"macro|inflation|monetary|exchange rate|interest rate"),
    ("sentiment", r"sentiment|news|text|social media"),
]

# A desk wants a paper it could code. This keeps the index to work that proposes
# a signal, a portfolio rule, or a forecast — and drops the essays about
# governance, disclosure and policy that dominate a citation ranking otherwise.
STRATEGY = re.compile(
    r"cross[- ]section|time[- ]series[^.]{0,40}return|stock returns|"
    r"return predictab|predict(ing|s|ability|or)[^.]{0,40}(return|price|volatilit)|"
    r"trading strateg|trading rule|investment strateg|portfolio|"
    r"risk factors?|factor (model|zoo|premi|investing|momentum)|"
    r"risk premi|anomal|momentum|reversal|carry trade|value premium|"
    r"low.volatility|betting against beta|alpha|signal|backtest|market timing|"
    r"volatilit|hedg(e|ing)|option pricing|implied vol|statistical arbitrage|"
    r"pairs trading|mean.revers|machine learning|deep learning|neural network|"
    r"past (returns|performance|winners)|asset allocation|term structure|"
    r"order flow|limit order book|execution (cost|algorithm)|transaction cost|"
    r"expected shortfall|value at risk|drawdown|sharpe|illiquidity|liquidity risk|"
    r"asset pricing|bid[- ]ask|market maker|specialist market|term premium|"
    r"stochastic volatility|jump diffusion|risk parity|tail risk|forecast",
    re.I)

# The other side of the same coin: finance, but nothing a desk could code.
ESSAY = re.compile(
    r"corporate governance|agency (cost|problem|theory)|board of directors|"
    r"\bCEO\b|executive compensation|disclosure|earnings management|auditor|"
    r"litigation|tax(ation)? (policy|avoidance|compliance)|regulatory reform|"
    r"bank(ing)? (supervision|regulation|stability|competition)|microfinance|"
    r"financial (literacy|inclusion|education)|household finance|"
    r"survey (evidence|of|data)|questionnaire|gender|diversity|political|"
    r"lobbying|law and (economics|finance)|climate|carbon|green (bond|return)|"
    r"sustainab|ESG|corporate social respons|"
    r"initial public offering process|monetary policy transmission|"
    r"fiscal|inequality|labor market|housing (market|price)|"
    r"COVID|pandemic|sanctions|social (network|media)", re.I)

# Data a stranger can fetch for free today: daily OHLCV, SEC filings,
# FRED/ALFRED macro, Ken French factors, FINRA short volume, Coinbase. A paper
# that needs anything below cannot be run by a reader, so it is not indexed.
UNOBTAINABLE = re.compile(
    r"tick[- ]by[- ]tick|tick data|intraday|high[- ]frequency|millisecond|"
    r"limit order book|order book|quote[- ]level|trade and quote|TAQ|"
    r"option (chain|surface|panel)|implied volatility surface|OptionMetrics|"
    r"IvyDB|analyst (forecast|estimate|recommendation)|I/?B/?E/?S|"
    r"institutional holdings|13F|short interest|securities lending|"
    r"proprietary (data|dataset)|broker(age)? (records|accounts)|"
    r"credit default swap|CDS spread|corporate bond transaction|TRACE|"
    r"mutual fund flows|hedge fund (holdings|returns database)|"
    r"earnings call transcript|patent|satellite|credit card (transaction|panel)",
    re.I)

# Codeable, but the deliverable is a theorem rather than a position.
THEORY_ONLY = re.compile(
    r"we prove|existence and uniqueness|viscosity solution|mean field game|"
    r"stochastic control problem|utility maximi[sz]ation problem|"
    r"convergence (rate|theorem|analysis)|finite difference scheme|"
    r"numerical scheme|discreti[sz]ation error|asymptotic expansion|"
    r"martingale representation|axiom|equilibrium existence|"
    r"general equilibrium model", re.I)

MIN_ABSTRACT = 260          # long enough to judge; classics are judged on title


def practical(rec: dict) -> tuple[bool, str]:
    """Three gates, in order: does it name a mechanism, can a reader get the
    data, and is the deliverable a position rather than a proof. Returns the
    verdict and the reason, because a filter you cannot argue with is a
    prejudice."""
    title = rec["title"]
    abstract = rec.get("abstract") or ""
    text = f"{title} {abstract}"

    if ESSAY.search(text):
        return False, "essay — governance, policy or disclosure, no mechanism"
    named = bool(STRATEGY.search(title)) or (
        len(abstract) >= MIN_ABSTRACT and bool(STRATEGY.search(abstract)))
    if not named:
        return False, "no mechanism named in title or abstract"
    if UNOBTAINABLE.search(text):
        return False, f"needs data we cannot fetch ({UNOBTAINABLE.search(text).group(0).lower()})"
    if THEORY_ONLY.search(text):
        return False, f"theory, not a position ({THEORY_ONLY.search(text).group(0).lower()})"
    return True, "runnable"


# What we could actually run today, given free data. Honest, and it drives a filter.
TESTABLE = re.compile(
    r"momentum|reversal|trend|moving average|cross.section|factor|anomal|"
    r"volatilit|portfolio|calendar|seasonal", re.I)
NEEDS_MORE = re.compile(
    r"option|implied|limit order|high.frequenc|microstructur|analyst|"
    r"earnings call|proprietary|intraday|order flow|tick", re.I)


def tags_for(text: str) -> list[str]:
    found = [tag for tag, pattern in TAG_RULES if re.search(pattern, text, re.I)]
    return found[:3] or ["quant-finance"]


def testability(text: str) -> tuple[str, str]:
    if NEEDS_MORE.search(text):
        return "blocked", "needs options, intraday or analyst data we do not have"
    if TESTABLE.search(text):
        return "queued", "runnable with free point-in-time data"
    return "triage", "not yet assessed"


# ---------------------------------------------------------------- openalex


def openalex(params: dict, client: httpx.Client) -> dict:
    params = {**params, "mailto": MAILTO}
    for attempt in range(4):
        r = client.get(OPENALEX, params=params, headers=UA, timeout=90)
        if r.status_code == 200:
            return r.json()
        if r.status_code in (429, 503):
            time.sleep(2.5 * (attempt + 1))
            continue
        r.raise_for_status()
    raise RuntimeError(f"OpenAlex kept failing: {params.get('filter')}")


def abstract_of(work: dict) -> str:
    """OpenAlex stores abstracts inverted, to sidestep redistribution limits."""
    inv = work.get("abstract_inverted_index")
    if not inv:
        return "No abstract released by the publisher."
    positions: list[tuple[int, str]] = []
    for word, idxs in inv.items():
        positions += [(i, word) for i in idxs]
    text = " ".join(w for _, w in sorted(positions))
    return re.sub(r"\s+", " ", text).strip()[:1400]


def per_month(citations: int, published: str) -> float:
    """Citations a month since publication, so a 2026 paper is not asked to
    out-total a 1993 one. Floored at one month, since nothing accrues faster."""
    try:
        when = datetime.strptime(published[:10], "%Y-%m-%d").replace(tzinfo=timezone.utc)
    except ValueError:
        return 0.0
    months = max((datetime.now(timezone.utc) - when).days / 30.44, 1.0)
    return round(citations / months, 2)


def arxiv_id_of(work: dict) -> str | None:
    for loc in work.get("locations") or []:
        url = loc.get("landing_page_url") or ""
        m = re.search(r"arxiv\.org/abs/(.+?)(?:v\d+)?$", url)
        if m:
            return m.group(1)
    doi = (work.get("doi") or "").lower()
    m = re.search(r"10\.48550/arxiv\.(.+)$", doi)
    return m.group(1) if m else None


def to_record(work: dict, source: str) -> dict:
    title = re.sub(r"\s+", " ", work.get("display_name") or "").strip()
    abstract = abstract_of(work)
    names = [a["author"]["display_name"]
             for a in work.get("authorships", [])[:8] if a.get("author")]
    venue = ((work.get("primary_location") or {}).get("source") or {}).get(
        "display_name") or "unpublished"
    axid = arxiv_id_of(work)
    status, why = testability(f"{title} {abstract}")
    # Any open-access PDF will do for a first page. arXiv is the common case,
    # but NBER, RePEc mirrors and OA journals carry one too, and a card with a
    # real first page reads as a paper rather than a row in a table.
    oa = (work.get("best_oa_location") or {}).get("pdf_url") \
        or (work.get("open_access") or {}).get("oa_url")
    published = work.get("publication_date") or f"{work.get('publication_year') or 1900}-01-01"
    url = work.get("doi") or (work.get("primary_location") or {}).get("landing_page_url") or ""
    if axid:
        url = f"https://arxiv.org/abs/{axid}"
        venue = f"arXiv:{axid}"
    return {
        "openalex_id": (work.get("id") or "").rsplit("/", 1)[-1],
        "arxiv_id": axid,
        "doi": work.get("doi"),
        "title": title,
        "authors": ", ".join(names[:3]) + (" et al." if len(names) > 3 else ""),
        "author_count": len(work.get("authorships", [])),
        "abstract": abstract,
        "published": published,
        "primary_category": venue,
        "url": url,
        "pdf": f"https://arxiv.org/pdf/{axid}" if axid else (oa or None),
        "thumb_key": axid or (work.get("id") or "").rsplit("/", 1)[-1],
        "citations": int(work.get("cited_by_count") or 0),
        "citations_per_month": per_month(int(work.get("cited_by_count") or 0), published),
        # Field- and year-normalised, so a 2026 paper is judged against 2026
        # papers. Raw counts can only ever rank by age.
        "percentile": round(float(
            (work.get("citation_normalized_percentile") or {}).get("value") or 0.0), 4),
        "top_1pct": bool((work.get("citation_normalized_percentile") or {})
                         .get("is_in_top_1_percent")),
        "source": source,
        "tags": tags_for(f"{title} {abstract}"),
        "status": status,
        "status_note": why,
    }


def fetch_half(filter_str: str, limit: int, source: str, client: httpx.Client) -> list[dict]:
    """Most-cited *implementable* works matching a filter, paged with a cursor.

    The practical() gate rejects roughly four in five, so this reads far past
    `limit` pages before it has that many keepers."""
    out: list[dict] = []
    cursor = "*"
    seen = 0
    while len(out) < limit and cursor and seen < limit * 25:
        page = openalex({"filter": filter_str, "sort": "cited_by_count:desc",
                         "per-page": 100, "cursor": cursor}, client)
        results = page.get("results", [])
        seen += len(results)
        for work in results:
            rec = to_record(work, source)
            if rec["title"] and practical(rec)[0]:
                out.append(rec)
        cursor = (page.get("meta") or {}).get("next_cursor")
        if not results:
            break
        time.sleep(0.4)
    return out[:limit]


def window_filter(days: int | None) -> str:
    if days is None:
        return ""
    since = datetime.now(timezone.utc) - timedelta(days=days)
    return f",from_publication_date:{since:%Y-%m-%d}"


def dedupe(records: list[dict]) -> list[dict]:
    """One row per paper. A working paper and its journal version are the same
    work to a reader, so the more-cited copy wins and the other is dropped."""
    best: dict[str, dict] = {}
    for rec in sorted(records, key=lambda r: -r["citations"]):
        key = re.sub(r"[^a-z0-9]+", " ", rec["title"].lower()).strip()
        if key and key not in best:
            best[key] = rec
    return sorted(best.values(), key=lambda r: -r["citations"])


def fetch_replicated_citations(client: httpx.Client) -> dict[str, int]:
    """Live citation counts for the papers we have run, keyed by our own id."""
    out: dict[str, int] = {}
    for key, doi in REPLICATED_DOIS.items():
        try:
            page = openalex({"filter": f"doi:https://doi.org/{doi}", "per-page": 1}, client)
            hits = page.get("results") or []
            out[key] = int(hits[0].get("cited_by_count") or 0) if hits else 0
        except Exception as exc:
            print(f"    citations failed for {key}: {type(exc).__name__}")
            out[key] = 0
        time.sleep(0.4)
    return out


# ------------------------------------------------------- semantic scholar

S2_BATCH = "https://api.semanticscholar.org/graph/v1/paper/batch"


def add_influential(papers: list[dict], client: httpx.Client) -> int:
    """Semantic Scholar separates citations that actually build on a paper from
    the ones that name-check it. Free, no key, 500 ids a call."""
    index: dict[str, dict] = {}
    for p in papers:
        key = (f"ARXIV:{p['arxiv_id']}" if p.get("arxiv_id")
               else f"DOI:{(p.get('doi') or '').rsplit('doi.org/', 1)[-1]}"
               if p.get("doi") else None)
        if key and not key.endswith(":"):
            index.setdefault(key, p)
    ids = list(index)
    found = 0
    for i in range(0, len(ids), 400):
        chunk = ids[i:i + 400]
        for attempt in range(4):
            r = client.post(S2_BATCH, params={"fields": "influentialCitationCount"},
                            json={"ids": chunk}, timeout=120)
            if r.status_code == 200:
                for key, row in zip(chunk, r.json()):
                    if row and row.get("influentialCitationCount") is not None:
                        index[key]["influential"] = int(row["influentialCitationCount"])
                        found += 1
                break
            time.sleep(3.0 * (attempt + 1))
        time.sleep(1.2)                    # the shared pool is not generous
    return found


# ------------------------------------------------------------------ thumbs


def render_thumb(paper: dict) -> str | None:
    """First page as a JPEG. Returns the path relative to docs/, or None."""
    if not paper.get("pdf"):
        return None
    os.makedirs(THUMB_DIR, exist_ok=True)
    safe = str(paper.get("thumb_key") or paper.get("arxiv_id") or "").replace("/", "_")
    if not safe:
        return None
    rel = f"thumbs/{safe}.jpg"
    dest = os.path.join(THUMB_DIR, f"{safe}.jpg")
    if os.path.exists(dest) and os.path.getsize(dest) > 2000:
        return rel

    try:
        r = httpx.get(paper["pdf"], headers=UA, timeout=180, follow_redirects=True)
        if r.status_code != 200 or not r.content.startswith(b"%PDF"):
            return None
        page = pdfium.PdfDocument(r.content)[0]
        img = page.render(scale=2.0).to_pil().convert("RGB")
        img = img.resize((THUMB_W, round(img.height * THUMB_W / img.width)))
        img.save(dest, "JPEG", quality=72, optimize=True)
        return rel
    except Exception as exc:
        print(f"    thumb failed for {safe}: {type(exc).__name__}")
        return None


# -------------------------------------------------------------------- main


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--per-half", type=int, default=100,
                    help="papers from each of arXiv and the journals")
    ap.add_argument("--no-thumbs", action="store_true")
    args = ap.parse_args()

    econ = ",primary_topic.id:" + "|".join(QUANT_TOPICS)   # keeps the desk in view
    arxiv_filter = (f"primary_location.source.id:{ARXIV_SOURCE},"
                    f"primary_topic.subfield.id:{FINANCE_SUBFIELD}")
    journal_filter = "primary_location.source.issn:" + "|".join(JOURNAL_ISSNS) + econ
    series_filter = "primary_location.source.id:" + "|".join(SERIES_SOURCES) + econ
    per_window = max(args.per_half // len(WINDOWS), 1)

    arxiv: list[dict] = []
    journals: list[dict] = []
    with httpx.Client(follow_redirects=True) as client:
        for key, days in WINDOWS:
            since = window_filter(days)
            print(f"{key}: top {per_window} from each side")
            arxiv += fetch_half(arxiv_filter + since, per_window, "arxiv", client)
            pool = fetch_half(journal_filter + since, per_window, "journal", client)
            pool += fetch_half(series_filter + since, max(per_window // 2, 4),
                               "journal", client)
            journals += dedupe(pool)[:per_window]

        print("influential citations from Semantic Scholar")
        got = add_influential(arxiv + journals, client)
        print(f"  matched {got}")

        print("citation counts for the replicated papers")
        cites = fetch_replicated_citations(client)
        print("  ", cites)

    # A paper found in the 30-day cohort is also in the 12-month one; the page
    # assigns windows from each card's date, so one row per paper is enough.
    arxiv, journals = dedupe(arxiv), dedupe(journals)
    print(f"  arxiv {len(arxiv)}, journals {len(journals)} after dedupe")
    papers = dedupe(arxiv + journals)

    if not args.no_thumbs:
        targets = [p for p in papers if p.get("pdf")]
        print(f"rendering first pages ({len(targets)} open PDFs)", flush=True)
        done = 0
        for i, p in enumerate(targets, 1):
            p["thumb"] = render_thumb(p)
            done += bool(p["thumb"])
            if i % 25 == 0:
                print(f"    {i}/{len(targets)}  ok={done}", flush=True)
            time.sleep(0.8)                  # be a good citizen with the hosts
    got = sum(1 for p in papers if p.get("thumb"))
    print(f"  thumbnails: {got}/{len(papers)}")

    # A paper nobody can open is a paper nobody can rerun. The archive promises
    # a stranger can reproduce the result, so a paywalled PDF is disqualifying
    # regardless of how often it is cited.
    if not args.no_thumbs:
        before = len(papers)
        papers = [p for p in papers if p.get("thumb")]
        print(f"  dropped {before - len(papers)} papers with no open pdf")

    counts: dict[str, int] = {}
    for p in papers:
        counts[p["source"]] = counts.get(p["source"], 0) + 1
    print("  by source:", counts)

    os.makedirs(os.path.dirname(PAPERS_JSON), exist_ok=True)
    stamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
    with open(PAPERS_JSON, "w", encoding="utf-8") as fh:
        json.dump({"fetched_at": stamp, "papers": papers}, fh, indent=2)
    with open(CITES_JSON, "w", encoding="utf-8") as fh:
        json.dump({"fetched_at": stamp, "citations": cites}, fh, indent=2)
    print(f"wrote {PAPERS_JSON} and {CITES_JSON}")


if __name__ == "__main__":
    main()
