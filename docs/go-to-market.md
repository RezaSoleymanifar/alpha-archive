# Alpha Archive go-to-market

## Audience tiers

| Audience | Pain | What Alpha Archive provides | Acquisition channel |
|---|---|---|---|
| **Quant retail / Twitter** | Reads papers, doesn't have time/skill to backtest | One-click verdict per paper | Quant Twitter, r/quant, Hacker News |
| **Hedge fund DD / LP teams** | Vetting fund manager pitches that cite papers | "did this paper actually work post-publication?" | LinkedIn, conferences (CFA, AIMA) |
| **Quant researchers** | Factor zoo navigation; what's worth replicating? | Filtered universe of survivors | Twitter, ResearchGate, conferences |
| **Students / educators** | Learning quant finance; need reproducible examples | Open code per paper | Reddit r/algotrading, university courses |
| **Content creators (newsletters, YT)** | Need fresh content backed by data | Weekly "5 papers replicated" newsletter | Substack, YouTube collaborations |

## Distribution wedge, what makes it spread

### 1. SEO moat
Every replicated paper = a landing page indexed by Google. Search "[paper title]" → Alpha Archive page in top 3.

Volume: 80K+ pages over 5 years. Each gets occasional traffic from people Googling the paper. Compound.

### 2. Social loop
Each result is a tweet:
> "📄 Replicated: 'Insider Trading and Stock Returns' (Cohen et al 2012)
> Claimed Sharpe: 1.2
> Our Sharpe: 0.8 (DSR-corrected)
> Replication score: 0.67 (✅ partial)
> Decay: -28% post-pub
> Code: alpha-archive.io/papers/12345"

Quant Twitter eats this. Each post drives 100-1000 visits. Replicate 3/week = consistent presence.

### 3. Newsletter
Weekly digest of:
- 5 newest replications
- 1 surprising result (over- or under-claim)
- 1 alpha decay update on previously shipped signal
- Reader-submitted papers

Substack-friendly. Free tier acquires; paid tier funds.

### 4. Open data + open code
GitHub repo with all generated code. Pull requests for improvements. Lowers barrier for quant blogger ecosystem to cite us.

### 5. Conference & academic credibility
- Submit Alpha Archive itself as a paper to JFE/JF/RFS, "Replicating the factor zoo at scale"
- Sponsor / present at AFA, EFA, CFA Institute events
- Partner with academic departments for student projects

## Launch sequence

### Pre-launch (months 1-2)
- Build phase 1-3 (working pipeline + Streamlit MVP)
- Replicate 50 known classic papers (FF3, FF5, momentum, BAB, quality, value)
- Validate methodology against published results
- Write 3 launch blog posts

### Soft launch (month 3)
- Launch on Hacker News with title: "Alpha Archive: I built an LLM-powered replication engine for quant finance papers"
- Cross-post r/algotrading, r/quant, r/machinelearning
- Email 50 quant Twitter accounts with personalized DM + 1 result they'd find interesting
- Ship newsletter signup form

### Growth (months 4-12)
- Weekly newsletter (build to 5K subs)
- Hit 500 replicated papers
- 1 viral result per quarter (expected: a famous paper that fails replication = headline material)
- Get cited in 1 academic paper

### Scale (year 2+)
- alpha-archive.io = standard reference for quant practitioners
- Hire researcher to investigate flagged anomalies
- Pro tier subscriber funnel
- Conference sponsorship + presence

## What could kill it

| Risk | Mitigation |
|---|---|
| LLM-generated code is buggy → bad results | Human review queue + sandbox + replication-against-known-papers |
| Paper authors complain | Methodology is transparent; publish dispute resolution process |
| Data vendor cost spike | Multi-vendor strategy + parquet caching |
| Rate-limiting from arXiv/SSRN | Stagger polls + use official APIs where available |
| Backtest engine errors | Open-source code + community PR loop |
| Becomes too academic / nerdy | Newsletter editorial voice, accessible explainers |
| Fund managers gate access via cease-and-desist | Stay in pure-academic-paper lane; no proprietary signal extraction |

## Why now

- LLMs (Sonnet, Haiku) are now good enough to extract structured specs from PDFs
- LLM cost dropped 10x in 18 months → economics work
- Quant retail audience growing (TradingView, Quantopian alumni, r/algotrading)
- Generative AI hype wave drives interest in "AI applied to X"
- Factor zoo conversation is mainstream (Harvey, Liu, Zhu 2016 paper widely cited)

## Success metrics

| Metric | 6 months | 12 months | 24 months |
|---|---|---|---|
| Papers replicated | 200 | 1,000 | 10,000 |
| Newsletter subscribers | 500 | 5,000 | 25,000 |
| Twitter followers | 1K | 10K | 50K |
| Monthly visitors | 5K | 50K | 250K |
| Citations in academic papers | 0 | 2 | 10 |
| Pro tier MRR | $0 | $1K | $20K |
| Press mentions | 1 | 5 | 20 |

## Reza-specific bonus value

Whether or not Alpha Archive grows commercially:
- **Interview gold**: every QR seat will love this project. Demonstrates ML + finance + product + scale thinking.
- **Network**: contacts at AlphaArchitect, Quantpedia, Two Sigma research will engage
- **Content asset**: blog posts compound into a public profile
- **Optionality**: even at small scale (100 users) it's a discussion piece in interviews
- **Non-zero acqui-hire path**: if it gets traction, AlphaArchitect / Quantpedia / Refinitiv could be acquirers
