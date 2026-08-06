# Where the papers come from

Every row below is a place quants actually read. The question this page answers
is narrower than "is it good": **can we index it without scraping?**

The rule is the same one the archive runs on, if a stranger cannot fetch it the
way we fetched it, it does not go in. That means public APIs and registered
metadata only. No headless browsers, no HTML parsing of pages that did not offer
an API, no download counts lifted off a listing.

Status is as of 2026-08-06, verified by calling each endpoint.

## Indexed today

| Tier | Source | How we reach it | What we get |
|---|---|---|---|
| 1 | **SSRN, Financial Economics Network** | OpenAlex, via Crossref DOIs (`10.2139/ssrn.*`), ISSN 1556-5068 | Title, authors, abstract, date, citations. 1.66M works indexed. |
| 1 | **arXiv q-fin** | arXiv API for the listing, OpenAlex for citations; source `S4306400194` filtered to the Finance subfield | Everything, plus the openly distributed PDF, which is why only arXiv cards carry a first-page thumbnail. |
| 1 | **NBER Working Papers** | OpenAlex source `S2809516038` | Title, authors, abstract, date, citations. 36,566 works. |
| 2 | **Journal of Finance, JFE, RFS** | OpenAlex by ISSN | Metadata and citations. Abstracts where the publisher released them. |
| 2 | **JFQA, Management Science, Review of Asset Pricing Studies** | OpenAlex by ISSN, filtered to the Economics/Econometrics/Finance field | Same. The field filter is what keeps Management Science's information-systems canon out of a finance index. |
| 3 | **Financial Analysts Journal** | OpenAlex by ISSN | Same. |
| 3 | **Journal of Portfolio Management** | OpenAlex by ISSN | Same. |
| 3 | **Journal of Financial Data Science** | OpenAlex by ISSN | Same. |
| 3 | **Quantitative Finance, Journal of Investment Strategies, Journal of Derivatives, Journal of Fixed Income, Journal of Risk** | OpenAlex by ISSN | Same. |

## Correcting an earlier claim

An earlier note in this project said SSRN "has no free API, so it can't be
fetched without scraping." That is half right and the wrong half was load-bearing.
SSRN has no API of its own, but SSRN papers carry registered DOIs, so their
metadata and citation counts arrive through OpenAlex and Crossref like any other
work. SSRN is indexed here, and nothing was scraped to do it.

What SSRN still withholds: the PDF, and the download counts its own top-ten lists
are built from. Neither is available without scraping, so neither appears here.

## Not indexed, and why

| Tier | Source | Why not |
|---|---|---|
| 2 | **JFE data appendices** | The appendix is a file inside a paywalled article, not a catalogued work. Nothing to query. |
| 4 | **AQR, Robeco, Man AHL, Research Affiliates libraries** | Firm research libraries publish as web pages with no API and usually no DOI. Some AQR papers reach us anyway, because the authors also post them to SSRN, and that copy is the one we index. |
| 4 | **Alpha Architect, Quantpedia, Quantocracy** | Aggregators and summaries. Indexing them would be indexing a description of a paper rather than the paper, and Quantpedia's encyclopedia is a paid product besides. Useful for discovery; not a source. |
| 4 | **Open Source Asset Pricing (Chen-Zimmermann)** | Not a paper feed. It is the replication scoreboard, 331 predictors with claimed t-statistics. It belongs in the results, not the index, and is already wired into [Vintage](https://github.com/RezaSoleymanifar/vintage) as `openap:`. |
| none | **Risk.net** | Subscription, no public metadata endpoint. |

## Ranking

Papers are ranked by citation count inside a publication-date window: 30 days,
12 months, 5 years, all time. Citations come from OpenAlex `cited_by_count`.

Two honest caveats travel with that number, and both are on the page:

1. **Citations lag.** A paper published last month has none, and will have none
   for a year or more. The 30-day window is therefore ordered by date, and says
   so rather than presenting a list of zeros as a ranking.
2. **Totals favour age.** Jensen and Meckling have had fifty years to accumulate
   71,268 citations. Each card also shows citations per month since publication,
   which is the comparison that treats a 2026 paper fairly.

## Reproducing this

```bash
uv run python tools/fetch_papers.py      # 100 arXiv + 100 published, per window
uv run python tools/build_site.py        # renders docs/index.html
```

OpenAlex asks for an email in the `mailto` parameter in exchange for the polite
pool; set `ALPHA_ARCHIVE_MAILTO` to yours. No key, no account, no quota to buy.
