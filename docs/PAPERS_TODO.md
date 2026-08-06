# Papers to build

90 of 333 judged papers are reproducible on free data. The other 243 are not, and [the ledger](../data/triage/ledger.json) records why for each one.

Effort is a tier, not an hour count. It is inferred from what the judgement recorded — how many sources a paper needs, how large its universe is, and whether anything must be trained — because that is the most those signals honestly support.

| Tier | Meaning | Count |
|---|---|---|
| **S** | Closed-form on a small universe. A sitting. | 19 |
| **M** | An estimator to fit, or several sources to join. | 44 |
| **L** | A model to train. Results move with the seed. | 27 |

Ordered cheapest first, then by confidence, then by how numeric the published targets are. A paper with many exact numbers can be declared right or wrong; a paper with prose claims can only be argued about.

---

## 1. Fitting Accumulated Stock Returns with Tempered Skew t-Distribution

`2606.19318` · [arXiv](https://arxiv.org/abs/2606.19318v1) · **S** — closed-form on a small universe · confidence 0.93 · 2026-06-17

Fits a tempered modified-Jones-Faddy Skew-t distribution (derived from a capped inverse-gamma stationary variance) to empirical distributions of S&P 500 returns accumulated over tau = 20, 30, ..., 120 trading days, 1980-2025.

**Data**
- Yahoo Finance ^GSPC daily close, 1980-01-01 to 2025 (log returns accumulated over tau = 20,30,...,120 trading days, overlapping windows)

**Must land on**
- Table 1 fitted parameters, tau=20: beta_l 1.658, beta_g 2.229, alpha 9.079e-5, kappa_1 0.009273, mu 0.01565
- Table 1 fitted parameters, tau=120: beta_l 1.670, beta_g 2.539, alpha 9.270e-5, kappa_1 0.008374, mu 0.05405
- Table 1: beta_l stays near 1.52-1.68 and beta_g rises from ~2.23 to ~2.54 as tau goes 20 -> 120
- Table 3 empirical vs fitted mean m1: tau=20 0.000772 vs 0.00116; tau=60 0.00240 vs 0.00217; tau=120 0.00488 vs 0.00460
- Table 3 empirical vs fitted variance m2: tau=20 0.00206 vs 0.00228; tau=60 0.00570 vs 0.00666; tau=120 0.0115 vs 0.0136 (near-linear in tau)
- Table 4 first Pearson skewness zeta_1 (data vs fit): tau=20 -0.2565 vs -0.1551; tau=60 -0.1392 vs -0.2068; tau=120 -0.1468 vs -0.2080
- Table 4 Fisher-Pearson skewness for the fitted distribution: -4.20 (tau=20) to -4.95 (tau=120), with -12.29 at tau=50
- Figure 2/3: gain-side CCDF shows power-law behaviour that bends (tempers) toward a finite tail cut-off as tau increases

## 2. Conformal Kelly: Conformal Prediction Intervals as the Scale in Fractional Kelly Position Sizing

`2608.01494` · [arXiv](https://arxiv.org/abs/2608.01494v1) · **S** — closed-form on a small universe · confidence 0.93 · 2026-08-02

Ridge forecast on 21/63/252-day momentum plus EWMA(20) vol, then position size = fractional Kelly scaled by the width of a 75% conformal prediction interval.

**Data**
- daily adjusted closes for 8 US ETFs: SPY, QQQ, DIA, MDY, GLD, SLV, USO, DBC (Yahoo Finance), May 2006 - Sep 2024
- nothing else - no options, tick, intraday, or vendor data

**Must land on**
- DEV window (2016-2021) Config A: 28.45% annualised log growth, Sharpe 1.336, max drawdown 27.68%, Calmar 1.127
- DEV window Config B: 25.84% log growth, Sharpe 1.386, max drawdown 20.26%; SPY buy-and-hold benchmark 15.94% growth, Sharpe 0.98, 33.7% max drawdown
- LOCKBOX (2022+) out-of-sample results of 8.5% and 7.0% annualised for the two pre-registered configurations

## 3. What Useful Alphas?

`2607.06502` · [arXiv](https://arxiv.org/abs/2607.06502v1) · **S** — closed-form on a small universe · confidence 0.93 · 2026-07-07

Recomputes ~200 published long-short anomaly portfolios from the Chen-Zimmermann open-source signal library under alternative sample periods and size screens, then shrinks the cross-section of t-statistics for luck.

**Data**
- Open Source Asset Pricing (openassetpricing.com) long-short portfolio returns and predictor definitions for ~200 published anomalies
- market capitalization breakpoints for the non-micro / top-3,000 screens
- Ken French market factor for the CAPM alpha regressions

**Must land on**
- Median zero-investment long-short return of 48 bp/month through Dec 2005 (all stocks) falling to 19 bp post-2005, 26 bp for non-micro, and 7 bp for post-2005 non-micro
- Post-2005 non-micro panel: median t-statistic 0.45, median CAPM alpha 9 bp/month with t-stat 0.64, median annualized Sharpe 0.11, interquartile range -4 to +18 bp, 67% of anomalies positive
- Empirical Bayes shrinkage step: cross-anomaly variance of t-statistics of 1.09 implying a near-zero luck-adjusted return even for top-decile anomalies

## 4. Enhancing the Black-Scholes Model for Option Valuation via Lévy Processes and Malliavin Calculus

`2606.22796` · [arXiv](https://arxiv.org/abs/2606.22796v1) · **S** — closed-form on a small universe · confidence 0.92 · 2026-06-22

Adds a Levy subordinator to the volatility process in a Black-Scholes-type model, derives a European call price via multidimensional Ito calculus and an exact ATM implied-volatility expression via Malliavin calculus, then calibrates an OU (Stein-Stein) volatility process to a VIX-derived volatility proxy.

**Data**
- daily CBOE VIX index close, 2022-01-03 to 2022-09-14, from FRED (VIXCLS) or CBOE; volatility proxy sigma_t = VIX_t/100
- daily step Delta = 1/252 for the exact discrete-time OU transition

**Must land on**
- Table 1 summary statistics: VIX mean 25.63, median 25.58, sd 4.26, min 16.60, max 36.45; sigma_t mean 0.2563, median 0.2558, sd 0.0426, min 0.1660, max 0.3645
- Table 2 OU (Stein-Stein) calibration on sigma_t: mean-reversion speed alpha-hat = 31.0046 per year, long-run mean m-hat = 0.2609, vol-of-vol c-hat = 0.3153, half-life 5.6338 trading days
- Figure 1: model ATM implied-volatility proxy tracks the market proxy sigma_t = VIX_t/100 over the sample

## 5. Probability Weighting Meets Heavy Tails: An Econometric Framework for Behavioral Asset Pricing

`2511.16563` · [arXiv](https://arxiv.org/abs/2511.16563v1) · **S** — closed-form on a small universe · confidence 0.91 · 2025-11-20

Fits Normal, Laplace and Student's t distributions, plus a bounded behavioral probability-weighting transformation that preserves infinite divisibility, to daily returns of 86 exchange-traded assets across 25 categories from Jan 2004 to Dec 2024, comparing AIC, normality-test rejections, 99% VaR error and rolling-window out-of-sample forecasts.

**Data**
- daily adjusted closes for SPY, VTI, IVV (5,252 / 4,775 / 5,252 obs), IJH, MDY, VO (5,252 / 5,673 / 4,775), VTEB (2,799), MUB (4,145), Jan 2004 - Dec 2024, Yahoo Finance
- the remaining 78 tickers spanning international developed, emerging markets, treasury/corporate/municipal bond, commodity and sector ETFs to reach 432,752 observations across 86 assets
- 1,000-day rolling estimation window for the out-of-sample Diebold-Mariano comparisons

**Must land on**
- Table 1: SPY mean 0.0006, sd 0.0121, skew -0.37, kurtosis 5.68, min -0.095, max 0.110 over 5,252 obs; MDY sd 0.0145, skew -0.44, kurtosis 7.24 over 5,673 obs; VTEB sd 0.0029, kurtosis 4.22 over 2,799 obs
- Table 2: average AIC Normal -26,250.4 (best in 0 of 86), Student's t -27,815.8 (best in 76, 88.4%), Laplace -27,284.1 (best in 10, 11.6%); mean Student-t improvement 1,565 AIC points
- Gaussianity rejected at 5% for 100% of the 86 assets on Shapiro-Wilk, Jarque-Bera, Anderson-Darling and Kolmogorov-Smirnov
- Table 3: 99% VaR average error 19.7% Normal vs 3.2% behavioral Student's t overall; by class US equities 18.3% vs 2.9%, international 19.8% vs 3.1%, emerging 24.3% vs 3.4%, corporate bonds 16.2% vs 2.8%, commodities 22.1% vs 3.5%; violation rates 2.1% vs 1.1%
- Estimated degrees of freedom 4-7 for equity indices and 8-12 for bond exposures; mean weighting parameter alpha-hat 0.78 with H0: alpha=1 rejected in 72% of cases; behavioral spec wins Diebold-Mariano in 81% of cases

## 6. Portfolio Optimization and Tail-Risk Analytics of Actively Managed ETFs

`2607.03082` · [arXiv](https://arxiv.org/abs/2607.03082v1) · **S** — closed-form on a small universe · confidence 0.90 · 2026-07-03

Builds buy-and-hold, mean-variance, CVaR-95/99 and tangency portfolios (long-only and long-short, static and rolling-window dynamic) over a 30-fund universe of actively managed ETFs, and reports Sharpe/Sortino/Calmar/STARR/Rachev ratios plus Hill and POT-GPD tail diagnostics.

**Data**
- Daily adjusted closes for the 30-fund universe, 2020-12-04 to 2025-12-24, Yahoo Finance: ARKK, ARKG, ARKF, ARKQ, ARKW, FBCG, GQRE, JEPI, JPST, JCPB, DYNF, PTTRX, TOTL, ANGL, JMUB, AOR, AOA, AOM, AOK, GAA, KMLM, DBMF, QAI, IVOL and the remaining six thematic/alternative funds listed in Table 1
- Risk-free rate for Sharpe/tangency: 3-month T-bill (FRED DTB3) over the same window
- Transaction-cost assumption of 50 bp on turnover for the net-of-cost table

**Must land on**
- Table 1 daily log-return summary stats: ARKK mean 0.0009, sd 0.0254, skew 0.0824, ex-kurt 2.8737; ARKQ 0.0015 / 0.0199 / 0.1496 / 3.8613; JEPI 0.0001 / 0.0070 / 0.3191 / 27.6095; JPST 0.0000 / 0.0009 / -3.4698 / 12.4865; PTTRX 0.0001 / 0.0033 / -0.3076 / 1.0450
- Table 4 Sharpe ratios (Hist LO / Dyn LO / Hist LS / Dyn LS): MVP 1.1971 / 0.7007 / 1.4365 / 1.2818; TVP 1.1468 / 0.7747 / 3.1441 / 0.8379; C95 1.2958 / 1.0660 / 1.7773 / 1.3818; TC95 1.1022 / 0.4764 / 3.1584 / 1.7172; C99 1.3635 / 0.7529 / 1.6713 / 1.5489; TC99 1.0544 / 0.3605 / 3.0517 / 1.8306
- Table 5 Calmar ratios: MVP 2.3156 / 1.2340 / 2.3182 / 2.1386; TVP 2.0159 / 1.1177 / 5.6147 / 1.5858; C95 2.4719 / 1.8153 / 2.9027 / 2.1471; TC99 1.8370 / 0.6490 / 7.5406 / 2.4624
- Table 6 STARR ratios: C99 Hist LO 12.4632, TC99 Hist LS 30.5929, C95 Dyn LO 11.0352
- Table 7 Rachev ratios: TC99 1.0692 / 1.0733 / 1.5550 / 1.2852; MVP 0.9939 / 0.9974 / 1.0170 / 0.9524
- Table 8 turnover / net terminal wealth at 50 bp: BHP turnover 0.0, gross 118.42, net 118.42; LO TVP/TC95/TC99 turnover 3873.1, gross 177.07, net 120.50, cost drag 56.57; LO C99 turnover 2993.7, gross 98.76, net 73.33, drag 25.43 (net wealth change -12.219)
- Table 11 tail quantiles (VaR/ES grid): LO TVP 0.905 / 1.325 / 1.638 / 2.024 / 10.918; LO MVP 0.812 / 1.155 / 1.435 / 1.741 / 9.489

## 7. Correlation Structures and Regime Shifts in Nordic Stock Markets

`2601.06090` · [arXiv](https://arxiv.org/abs/2601.06090v1) · **S** — closed-form on a small universe · confidence 0.90 · 2025-12-31

Tracks the leading eigenvalues of the rolling correlation matrix of daily log-returns across three Nordic indices, and tests whether the eigenstructure dynamics identify regimes usable for portfolio construction.

**Data**
- daily adjusted closes for OMXS30, OMXC20 and OMXH25 constituents, January 2006 to September 2025 (Yahoo suffixes .ST, .CO, .HE)
- the three index levels over the same window

**Must land on**
- Table 1 descriptive statistics of log-returns for each of the three markets
- Figure 1 time evolution of the four largest correlation-matrix eigenvalues
- Figure 3 dynamics of the largest standardized eigenvalue across the 2008 and 2020 regime shifts

## 8. Market Reactions and Information Spillovers in Bank Mergers: A Multi-Method Analysis of the Japanese Banking Sector

`2512.06550` · [arXiv](https://arxiv.org/abs/2512.06550v1) · **S** — closed-form on a small universe · confidence 0.85 · 2025-12-06

Multi-method event study of two Japanese bank M&A events - the October 3, 2005 MUFG creation and the April 1, 2018 Resona Holdings merger - estimating CARs with the market model, CAPM and Fama-French three-factor model over a +/-20-day window, then VAR/Granger causality and impulse responses for spillovers to other banks, plus propensity-score matching for the ATT.

**Data**
- Daily closes for MUFG 8306.T and Resona 8308.T plus a Japanese bank peer group (8316.T, 8411.T, 8309.T, 8331.T, 8355.T etc.) around 2005-10-03 and 2018-04-01, estimation window of ~250 trading days pre-event - Yahoo Finance
- Market proxy: TOPIX (^TOPX / 1306.T) or Nikkei 225 (^N225) daily - Yahoo Finance
- Fama-French Japan/Asia-Pacific-ex-Japan daily 3 factors and RF - Ken French data library

**Must land on**
- MUFG (2005-10-03) event study: CAPM mean daily AR 0.69% (t = 7.05), CAR 29.79%; market model 0.27% (t = 2.84), CAR 12.01%; Fama-French 3-factor 0.64% (t = 6.48), CAR 27.37%
- Resona (2018-04-01) event study: CAPM mean daily AR 0.18% (t = 5.02), CAR 5.64%; market model 0.23% (t = 6.22), CAR 6.99%; Fama-French 3-factor 0.18% (t = 5.04), CAR 5.66%
- Resona Granger causality by horizon: lag 2 F = 3.8 (p = 0.02), lag 3 F = 2.31 (p = 0.07), lags 4-6 insignificant
- MUFG Granger causality: lag 1 F = 4.67 (p = 0.03), lag 2 F = 2.56 (p = 0.08), lag 3 F = 3.26 (p = 0.02), lag 4 F = 2.38 (p = 0.05)

## 9. GARTFIMA Models: A Class of Observation-Driven Models with Tempered Fractional Dynamics

`2607.19311` · [arXiv](https://arxiv.org/abs/2607.19311) · **S** — closed-form on a small universe · confidence 0.85 · 2026-07-21

Observation-driven (GAS-style) conditional-mean model for squared log-returns with a tempered fractional differencing operator, fitted by partial maximum likelihood.

**Data**
- AMZN daily adjusted closes, 18 Feb 2019 to 30 Jun 2022, 847 observations (Yahoo Finance, named by the authors)
- optional second application: USEPA AirNow daily max PM2.5, Virginia Beach, Jan 2023 to Dec 2025 (free but outside Vintage)

**Must land on**
- AMZN Gamma-ARTFIMA(2,d,lambda,2) estimates d_hat=0.8715, lambda_hat=0.0525, AIC=-12284, log-likelihood=6148.1
- AMZN Gamma-ARFIMA(2,d,2) benchmark d_hat=0.1220, AIC=-12216, log-likelihood=6115
- AMZN in-sample forecast accuracy RMSE 0.0008 / MAPE 0.4845 for ARTFIMA vs RMSE 0.0011 / MAPE 1.4432 for ARFIMA

## 10. Option Pricing with Time-Changed Fractional Brownian Motion: A Fractional Variance Gamma Model

`2608.03925` · [arXiv](https://arxiv.org/abs/2608.03925v1) · **S** — closed-form on a small universe · confidence 0.85 · 2026-08-04

Fractional Variance Gamma: fractional Brownian motion evaluated at a gamma activity-time change, estimated by two-stage feasible GMM on unconditional return moments across multiple horizons.

**Data**
- daily S&P 500 index levels Jan 1 2010 - Dec 31 2019, N = 2516 (paper uses CRSP; Yahoo ^GSPC is the same series)
- no option chains: the authors explicitly defer empirical option-pricing evaluation to future research

**Must land on**
- Section 7 GMM table, full fVG at p = 2: Hurst H* approximately 0.45 (0.4511), sigma* 0.1398, theta* -0.5885, v* 0.0044
- Nested-model comparison at p = 2: restricted fBSM H* 0.4659 and 0.3491 against the full specification, and the BSM/VG benchmarks estimated under the same GMM objective
- Stability of H* across moment truncations p in {2,3,4,5} on the same 2010-2019 sample

## 11. Anchored Geodesic Analysis for Multivariate Extremes

`2607.13112` · [arXiv](https://arxiv.org/abs/2607.13112v1) · **S** — closed-form on a small universe · confidence 0.85 · 2026-07-14

Anchored geodesic component analysis - dimension reduction of the extremal angular measure via great subspheres through a balanced complete-dependence anchor, reducing to eigenanalysis of a second-moment matrix of anchored tangent departures.

**Data**
- Ken French daily returns for the four 2x3 bivariate sorts (Size-BM, Size-OP, Size-INV, Size-Momentum), d=24 portfolios, from 1973-07-02
- Open Source Asset Pricing anomaly panel for the robustness check

**Must land on**
- Cumulative anchored variation explained on the Fama-French 24-portfolio daily panel: 64.6% at 3 components, 76.3% at 5, 86.4% at 8 and 91.1% at 10
- Mean relative error of the capped-excess and normalized VaR approximations: 3.4% at rank 5, 1.9% at rank 8, 1.25% at rank 10, 0.84% at rank 12
- Figure 3 both panels (explained variation curve and average relative portfolio error vs rank, with bootstrap 95% bands) on the top 5% radii tail sample

## 12. Fragility of Minimum-Variance Portfolios

`2607.18624` · [arXiv](https://arxiv.org/abs/2607.18624) · **S** — closed-form on a small universe · confidence 0.84 · 2026-07-21

Closed-form long-only minimum-variance weights under a block-diagonal correlation assumption, exposing threshold effects, plus structured shrinkage schemes that robustify against them.

**Data**
- monthly returns for V, MA, SHEL, CVX, XOM, KO, PEP, Jan 2018 to Jan 2025 (Yahoo adjusted closes)
- market factor returns for residualization (Ken French Mkt-RF)
- simulated block-diagonal and factor-model covariance data generated in-notebook

**Must land on**
- Real seven-ticker portfolio 6.23% turnover and 5.65 average active positions
- Two-asset fragile Markowitz example (sigma1=0.99, sigma2=1, rho=0.99): 14.23% turnover and 1.73 average active positions
- Section 6 out-of-sample excess-variance 'Area' metric and turnover for structured-shrinkage vs classical and clustering benchmarks across the three data environments

## 13. Deep Generative Models for Synthetic Financial Data: Applications to Portfolio and Risk Modeling

`2512.21798` · [arXiv](https://arxiv.org/abs/2512.21798v2) · **S** — closed-form on a small universe · confidence 0.82 · 2025-12-25

Trains TimeGAN and a VAE on daily S&P 500 log-returns and evaluates the synthetic series on statistical similarity, temporal structure, and three downstream tasks: mean-variance portfolio weights, VaR/ES risk estimation, and backtested portfolio performance, always against the real series.

**Data**
- Yahoo Finance ^GSPC daily adjusted close, January 2000 to June 2024, converted to log-returns
- Rolling-window lengths T = 10, 20, 60 days as specified for the robustness checks
- Risk-free rate for the Sharpe computation: FRED DTB3 (paper does not state it explicitly)

**Must land on**
- Table 1: real S&P 500 daily log-returns 2000-2024 have mean 0.00041, standard deviation 0.0127, skewness -0.45, kurtosis 7.88 (these four are pure free-data checks)
- Table 3: real-data volatility 1.27, VaR(0.95) -2.11, ES(0.95) -2.88; TimeGAN 1.30 / -2.05 / -2.79; VAE 1.19 / -1.92 / -2.63
- Table 4: portfolio metrics on real training data Sharpe 0.89, return metric 1.31, max drawdown 23.4%; TimeGAN 0.84 / 1.26 / 25.1; VAE 0.78 / 1.14 / 27.6

## 14. Drawdown Risk Beyond Brownian Motion: A Monte-Carlo Framework, Non-Gaussian Extensions, and Long Memory

`2608.00127` · [arXiv](https://arxiv.org/abs/2608.00127v1) · **S** — closed-form on a small universe · confidence 0.82 · 2026-07-31

Monte-Carlo mapping from Sharpe ratio and return structure to four drawdown risk measures, extended to skewed/fat-tailed archetypes and fractional Brownian long memory.

**Data**
- none - fully synthetic Monte Carlo (Brownian, non-Gaussian archetypes, fractional Brownian motion)
- optionally free daily returns for a real-strategy calibration extension (Ken French factors or Yahoo Finance ETF returns)

**Must land on**
- Table 1 Gaussian decision panel: at Sharpe 1 over 3 years, median max drawdown 1.16 vol and 90th percentile 1.88 vol; median recovery time 0.86 years, 90th percentile 1.82 years
- Table 4 one-day-fixed fBm risk at H=0.8: 8.01x max drawdown and 13.13x max loss versus the Brownian baseline
- Figure 4 validation of the Monte-Carlo drawdown depth and length against the Rej-Seager-Bouchaud closed forms at the 5% level

## 15. Retail Trader's Ruin: An Anatomy of Popular Signal Failure

`2607.20093` · [arXiv](https://arxiv.org/abs/2607.20093v1) · **S** — closed-form on a small universe · confidence 0.72 · 2026-07-22

Runs five retail signal families (50/200 SMA crossover, RSI-14 / MACD / Bollinger, on-balance-volume, sell-in-May calendar rules, seven candlestick patterns) against exposure-matched benchmarks at 10bps round-trip cost, then applies three predeclared gates: stationary-bootstrap Sharpe-gap CIs with Benjamini-Yekutieli control, net-of-cost CAGR-gap CIs, and a finite-bankroll ruin simulation.

**Data**
- Daily OHLCV for NASDAQ-100 index (trend, oscillator families) and SPY (calendar family) - Yahoo Finance
- Daily OHLCV for a US cross-section (volume, candlestick, momentum families) - Yahoo Finance
- Ken French momentum factor as an external parity check on the Jegadeesh-Titman 12-1 calibration

**Must land on**
- Table 2 gate (a) Sharpe-gap 95% CIs vs delta_S=0.20: trend [-0.234, 0.265], oscillator [-0.608, -0.175], calendar [-0.618, 0.000]
- Table 3 gate (b) CAGR-gap 95% CIs vs delta_R=0.01: oscillator [-0.149, -0.044], calendar [-0.131, -0.026], momentum [-0.044, 0.130]
- Table 4 gate (c) quarterly liquidation probabilities at 2x leverage: trend 0.009 [0.0065, 0.0124], oscillator 0.013 [0.0097, 0.0167], volume 0.000 [0.000, 0.001]

## 16. A novel robust mixed integer linear programming model for index tracking problem under no rebalancing: heuristic optimization approach

`2607.09556` · [arXiv](https://arxiv.org/abs/2607.09556v1) · **S** — closed-form on a small universe · confidence 0.72 · 2026-07-10

Robust mixed-integer linear program that picks a small no-rebalancing tracking basket, solved exactly with CPLEX and by a genetic-algorithm heuristic (GALB).

**Data**
- Yahoo Finance daily OHLCV for Dow Jones (29), CAC 40 (39) and EURO STOXX 50 (50) constituents plus the index levels, July 2018 to January 2024
- OR-Library index-tracking instances (free flat files, external to Vintage)
- a MILP solver - paper uses CPLEX, open HiGHS/CBC would substitute

**Must land on**
- Table 2 Dow Jones in-sample MAD tracking error: 0.00341 for the proposed model versus 0.0100 for Model 1 and 0.00324 for Model 3
- Dow Jones out-of-sample MAD: 0.00402 proposed versus 0.00866 Model 1 and 0.00458 Model 3
- Table 3 CAC 40 out-of-sample MAD: 0.00454 proposed versus 0.00458 Model 3

## 17. Generative AI-enhanced Sector-based Investment Portfolio Construction

`2512.24526` · [arXiv](https://arxiv.org/abs/2512.24526v1) · **S** — closed-form on a small universe · confidence 0.72 · 2025-12-31

Prompts twelve LLMs to pick and weight stocks inside each of the eleven S&P 500 sector indices, then scores those portfolios against equal-weight, minimum-variance, maximum-return and maximum-Sharpe benchmarks under mean-variance optimization.

**Data**
- daily adjusted closes for the S&P 500 sector constituents named in the paper's selection tables (Yahoo)
- the eleven SPDR sector index levels as benchmarks
- the published per-model stock selections, transcribed from Table 1 and Figures 1-2

**Must land on**
- the mean-variance frontier and Sharpe ratio of each LLM-weighted sector portfolio against its equal-weighted counterpart
- whether the LLM-weighted portfolios beat minimum-variance and maximum-Sharpe optimizations, per sector

## 18. Mandate without Managers: Automated Market Makers as Verifiable Portfolio Products

`2608.02917` · [arXiv](https://arxiv.org/abs/2608.02917v1) · **S** — closed-form on a small universe · confidence 0.70 · 2026-08-03

Simulate a geometric-mean market maker (Balancer G3M) with a multi-asset fee band so arbitrage-only order flow enforces a target-weight portfolio, then compare its CAGR and tracking error to the incumbent funds.

**Data**
- daily adjusted closes for VBIAX, EQL, EDOW (Yahoo Finance)
- daily adjusted closes for VTI and BND, the 11 Sector SPDR ETFs, and the 30 DJIA constituents
- no on-chain or DEX data; arbitrage order flow is simulated

**Must land on**
- Table 1 dominance region for VBIAX on monthly tracking error against the economic mandate: fee gamma in [2.73%, 3.90%]
- Table 1 dominance region for EQL on daily tracking error: gamma in [3.22%, 7.09%], over Jun 19 2018 - May 29 2026
- Table 1 dominance region for EDOW on daily tracking error: gamma in [3.32%, 9.90%], over Nov 11 2024 - Jun 29 2026

## 19. Two Sides of Schur Damping: High-Dimensional Pseudo-Likelihoods and Portfolio Allocation

`2606.14798` · [arXiv](https://arxiv.org/abs/2606.14798v1) · **S** — closed-form on a small universe · confidence 0.55 · 2026-06-11

Shows that the damped Schur complement used in spatial Vecchia pseudo-likelihoods and the gamma parameter interpolating hierarchical risk parity and minimum variance are the same object, with the same closed-form James-Stein / Ledoit-Wolf optimal intensity, then runs a small out-of-sample log-likelihood experiment on daily asset returns comparing undamped, closed-form and held-out-tuned damping.

**Data**
- daily closes for a 60-asset cross-section (universe undisclosed by the paper; any liquid 60-name US equity or ETF panel from Yahoo Finance reproduces the design)
- return windows sized to give aspect ratios n/p of 0.5, 0.8, 1.2, 2.0 and 3.0 with p=60, i.e. 30 to 180 daily observations per fit, plus a held-out split

**Must land on**
- Table 2 out-of-sample log-likelihood by damping at n/p = 0.5: undamped -188.1, closed-form gamma* -73.7, tuned gamma -37.4
- Table 2 at n/p = 0.8: -64.4 / -39.0 / -28.4; at 1.2: -34.2 / -25.0 / -19.8; at 2.0: -22.6 / -19.4 / -17.3; at 3.0: -17.7 / -16.1 / -15.1
- Mean closed-form reliability gamma-bar* rising 0.65, 0.71, 0.77, 0.84, 0.88 and tuned gamma 0.43, 0.58, 0.71, 0.79, 0.86 across the same aspect ratios
- The claim that the closed-form gamma* beats undamped Vecchia by order 100 nats at n/p = 0.5 and that the gap vanishes by n/p = 3

## 20. Relief-Gated Relative Rotation for QQQ-DIA Allocation: Globally Screened Relative States, Fixed Position Mapping, Incremental Interaction Admission, and Walk-Forward Validation

`2607.06117` · [arXiv](https://arxiv.org/abs/2607.06117v1) · **M** — 4 separate sources · confidence 0.96 · 2026-07-07

A two-ETF allocation rule (RGRR) mapping screened QQQ-DIA relative states and macro relief states into a continuous QQQ weight, with signals globally screened by horizon-specific HAC regressions and correlation de-duplication, then frozen during rolling walk-forward validation that re-selects only signal-family lambdas; the final stack is one main effect, nine second-order and two third-order interactions with a 10 bps one-way turnover cost.

**Data**
- Yahoo Finance daily adjusted close/returns: QQQ and DIA 2006-06-22 to 2026-07-02 (5,018 daily returns), SPY for the drawdown state, HYG and SHY for the credit-relief state, ^VIX for the volatility states
- 10-year Treasury yield for the rate-relief state: FRED DGS10 or Yahoo ^TNX, 21-day change, expanding-standardized with 252-day warmup
- Ken French data library: Fama-French five factors plus momentum, daily, for the Table 7 attribution
- OOS starts 2008-07-25, 2018-06-28, 2020-01-02, 2022-01-03; 10 bps one-way turnover cost; horizons 21, 63, 126 days

**Must land on**
- Table 16, 2018 OOS: RGRR 18.33% CAGR, Sharpe 0.94, max drawdown -29.41%, turnover 444.60%; 100% QQQ 20.50% / 0.89 / -35.12%; 100% DIA 12.41% / 0.72; 50/50 16.69% / 0.86 / -32.28%
- Table 16, 2020 OOS: RGRR 18.69% / 0.93 / -29.41% / 408.16% turnover; QQQ 21.29% / 0.90; DIA 11.98% / 0.67; 50/50 16.88% / 0.84
- Table 16, 2022 OOS: RGRR 15.19% / 0.87 / -23.62% / 354.33% turnover; QQQ 14.65% / 0.70 / -34.83%; DIA 10.64% / 0.75; 50/50 12.93% / 0.76 (the one window where RGRR beats QQQ on CAGR)
- Table 16, 2008 start: RGRR 16.85% / 0.97 / -29.25% / 505.89% turnover, final wealth 13.73x; QQQ 19.22% / 0.95 / -35.12% / 19.25x; DIA 13.88% / 0.84; 50/50 16.75% / 0.95
- Table 5 static baselines 2008-07-25 to 2026-07-02: 100% DIA 11.65% / 0.66 / -44.54%, 50/50 14.62% / 0.78 / -45.53%, 100% QQQ 17.17% / 0.82 / -47.83%
- Table 14 lineage, 2018 OOS: all-screened 17.32% / 0.91, Main+IX2 standard 17.44% / 0.92, Main+IX2 turnover-penalized 17.65% / 0.93, RGRR 18.33% / 0.94
- Table 9 fixed-mapping sensitivity: tilt0p50_tau0p75_eta0p05 gives 17.32% CAGR, Sharpe 0.91, max drawdown -29.52%
- Table 7 attribution alphas: QQQ excess return 3.57% (t 2.72, R2 0.92), DIA excess return -0.62% (t -0.41, R2 0.86), QQQ-DIA relative 4.19% (t 1.92, R2 0.38)

## 21. Continuous Cash-Overlay Filters for a Static Growth--Defensive Risk Sleeve: Slow-Tail Compensation, V-Shape Crash Brakes, Walk-Forward Validation, and Max-Cash Combination

`2606.09025` · [arXiv](https://arxiv.org/abs/2606.09025v2) · **M** — 6 separate sources · confidence 0.95 · 2026-06-08

Overlays cash on a fixed 50/50 growth-defensive ten-ETF risky sleeve using two independent filters - a slow-tail compensation/rate-headwind score with a 30% material-trade gate, and a fast V-shape crash brake on VIX, rate, credit and drawdown states - then takes the larger requested cash weight each day, validated by expanding and rolling walk-forward.

**Data**
- daily adjusted closes for the growth basket QQQ, XLK, VGT, SPYG, VUG and the defensive basket SCHD, VYM, VTV, FDVV, COWZ, 2017-06-28 to 2026-04-30 (2222 trading days), Yahoo Finance
- HYG and SHY daily adjusted closes for the credit relative-return state, Yahoo Finance
- VIX daily level for 756-day rolling percentile and 5/10/21-day changes (Yahoo ^VIX or FRED VIXCLS)
- 10-year Treasury yield (^TNX) and 3-month bill (^IRX) for rate headwind and curve inversion
- Moody's BAA and AAA corporate yields and their 21-day change, FRED
- contemporaneous cash / risk-free rate series for the cash sleeve return, FRED

**Must land on**
- Common window 2017-07-19 to 2026-04-30: max-cash combination CAGR 18.83% vs 16.62% for 100% R, max drawdown -18.05% vs -33.59%, turnover 355.82%, Sharpe-style score 4.54 vs 3.85
- Main walk-forward OOS: expanding combination 19.35% vs 17.59% for 100% R with MDD -22.05% vs -33.59%; rolling version 18.50% at the same -22.05%
- Table 5 selected full-sample at 10bp cost: slow-tail 17.83% CAGR, Sharpe 0.94, MDD -33.59%; V-shape 17.32%, 1.07, -23.77%; max-cash 18.83%, 1.18, -18.05%
- Table 13 components: slow-tail only 17.63% / -33.59%, V-shape only 17.63% / -23.77%, 100% R 16.62% / -33.59%
- Table 14 event diagnostics: COVID crash 2020-02-19 to 2020-03-23 max-cash -14.58% vs -15.11% for 100% R with 58.64% average cash; April 2025 crash 2025-03-25 to 2025-04-08 -10.10% vs -10.11% with 19.33% cash; calendar 2022 -8.95% vs -18.05%
- Table 7 slow-tail standalone walk-forward: expanding 18.79% vs 17.59%, rolling 18.12%; Table 11 V-shape expanding 15.59% with MDD -25.98%

## 22. The Impact of Bitcoin ETF Approval on Bitcoin's Hedging Properties Against Traditional Assets

`2512.12815` · [arXiv](https://arxiv.org/abs/2512.12815v1) · **M** — an estimator has to be fitted and checked · confidence 0.95 · 2025-12-14

Tests whether the January 2024 US spot Bitcoin ETF approval changed Bitcoin's co-movement with equities, gold and the dollar, using 30/60-day rolling correlations, Chow structural-break tests on both pairwise OLS and the rolling-correlation series, and an ARMA-DCC-GARCH(1,1) model.

**Data**
- Yahoo Finance daily adjusted close: BTC-USD, ^GSPC, GC=F (or GLD), DX-Y.NYB, pre-event 2023-10-01 to 2024-01-09 and post-event 2024-01-11 to 2024-04-30
- Same tickers extended to roughly 2022-11 through 2024-07 to reproduce the 30-day and 60-day rolling correlation charts in Figure 1
- Excess returns computed against a short risk-free rate (FRED DGS1MO or DTB3)

**Must land on**
- Table 1 ADF on excess returns: Bitcoin -41.4453, S&P 500 -20.2299, Gold -71.0724, DXY -71.6057, all p = 0.0000
- Table 2 pre vs post means: Bitcoin price 26,328 -> 60,503 (std 7,035 -> 9,919), return -0.0008 -> 0.0018; S&P 500 4,183 -> 5,141 (std 280 -> 182); Gold 1,880 -> 2,214; DXY 104.9 -> 104.5 (std 3.1 -> 0.9)
- Table 3 pairwise-OLS Chow: S&P 500 excess return 0.1427 (p = 0.8670, no break), Gold 2.3225 (p = 0.0991, break), DXY 8.7886 (p = 0.0002, break)
- Table 4 Chow on rolling-correlation series: BTC-S&P500 30-day 139.42, 60-day 269.30, BTC-Gold 30-day 135.96, BTC-DXY 30-day 105.86, all p = 0.0000, all breaks confirmed
- Table 5 ARMA-GARCH volatility equation for Bitcoin: Omega 2.4025 (t 2.197, p 0.0281), Alpha1 0.1184 (t 1.874, p 0.0609), Alpha2 0.1683, Beta1 0.1399, Beta2 0.3563, with alpha1+beta approx 0.49
- Qualitative DCC result: BTC-S&P 500 dynamic correlation rebounds post-approval, BTC-Gold drifts toward zero, BTC-DXY stays negative

## 23. Low-Turnover Rebalancing for Sparse Index Tracking

`2512.22109` · [arXiv](https://arxiv.org/abs/2512.22109v2) · **M** — 500 names · confidence 0.95 · 2025-12-26

Separates sparse index-tracker construction from maintenance: builds the initial tracker with a calibrated shrinkage model and posterior support screening, then at each rebalance defaults to holding and only makes self-financing local repairs when realised tracking error deteriorates and posterior directional gates agree.

**Data**
- Yahoo Finance daily adjusted closes for S&P 500 constituents 2020-01-03 to 2025-12-31, filtered to the 397 names present across the whole horizon (fixed universe, no entry/exit)
- Yahoo Finance ^GSPC daily levels over the same window as the tracking benchmark
- Named holdings appear in Tables 4-5 (NVDA, AVGO, CMCSA, GOOG, GL, HOLX, INCY, AMAT, AMD, PWR, HPE, ARE, JNJ, AMT, ORLY) for spot-checking the H11 and H13 recovery trades

**Must land on**
- Table 1: mean holding-window tracking error 20.556bp, median 19.409bp, maximum 36.074bp over H1-H16
- Table 1: H1-H8 mean TE 15.131bp versus H9-H16 mean TE 25.981bp; H10-H13 27.587bp; H14-H16 25.680bp
- Table 1: total one-way sequential turnover 5.0%, final portfolio 55 active names, top-10 mass 45.8%, top-25 mass 72.8%
- Table 7: competitor mean TE MM 17.261bp, MSE 17.265bp, TEV 17.374bp, NNEN 25.148bp, NNL 31.321bp, against tracker 20.556bp, with competitor turnover 492.3% / 663.4% / 680.0% / 403.1% / 443.2% versus 5.0%
- Table 6 protocol decomposition: (150,25)-Tracker mean TE 20.556 / median 19.409 / max 36.074 / turnover 5.0%; (130,50) 23.942; static hold 22.704; rolling reconstruction 17.711 at 604.6% turnover
- Table 3: recovery events fire in holds 10, 11, 13, 14, 15, 16 with 1.0% one-way turnover each and 7 to 13 names touched

## 24. Crashing Together, Rallying Apart: Dynamic Conditional Tail Dependence in Cryptocurrency Markets

`2606.16840` · [arXiv](https://arxiv.org/abs/2606.16840v1) · **M** — an estimator has to be fitted and checked · confidence 0.95 · 2026-06-15

Filters daily log returns of the thirteen largest cryptocurrencies with AR(1)-GJR-GARCH(1,1)-t, transforms residuals to Pareto margins, and fits Husler-Reiss graphical extremes models separately to the lower and upper tails over 89 overlapping 750-day windows (15-day steps), benchmarked against a Bayesian Gaussian graphical model.

**Data**
- Yahoo Finance daily adjusted close for BTC-USD, LTC-USD, DOGE-USD, ETH-USD, SOL-USD, ADA-USD, AVAX-USD, XRP-USD, XLM-USD, TRX-USD, BNB-USD, LINK-USD, DOT-USD, 2020-10-01 to 2026-06-14
- Coinbase spot as a cross-check for the same thirteen pairs over the same window

**Must land on**
- Section 4.1: both extremal graphs have edge density close to 0.87; the average asset is directly linked to between ten and eleven of the other twelve in either tail; global transitivity near 0.87; graph diameter equals 2 in every one of the 89 windows
- Design constants a replication must hit: 89 overlapping windows of 750 days advanced in 15-day steps, exceedance threshold p = 0.20, mid-points spanning late 2021 to 2025
- Figure 1 (lower tail): Bitcoin's pairwise extremal correlation chi-hat with ETH runs ~0.78-0.81, with DOGE ~0.70-0.75, and with SOL falls from ~0.75 (2022) to ~0.60 (2025)
- Figure 1 (upper tail): Bitcoin-ETH chi-hat ~0.66-0.76, and BTC-DOGE rises from ~0.60 (2022) to ~0.71 (2025) while BTC-TRX falls to ~0.54, i.e. the upper tail thins while the lower tail stays near-complete
- Robustness: the structural findings hold at thresholds p = 0.10 and 0.15 and at window lengths 500, 750 and 1000 days

## 25. A Spectral Generalisation of the Variance Ratio: Eigenstructure of Long-Horizon Portfolio Covariance and a Multi-Memory Factor Model of U.S. Equity Returns

`2607.03858` · [arXiv](https://arxiv.org/abs/2607.03858v1) · **M** — 4 separate sources · confidence 0.94 · 2026-07-04

Generalises the Lo-MacKinlay variance ratio to a multivariate spectral statistic (kappa, eigenvector-overlap) in both a return channel and a squared-return volatility channel, then fits a nine-parameter five-factor multi-memory model (fBm persistent/antipersistent, ARFIMA, MSM cascade) to eigenmode profiles via moving-block-bootstrapped L-BFGS-B.

**Data**
- Ken French 49 Industry Portfolios, daily value-weighted, 1969-07-01 to 2026-03-31 (T = 14,309 days, N = 48 after dropping columns with missing values)
- Same FF 49 file split into firsthalf 1969-1997 and secondhalf 1998-2026 sub-panels
- Ken French 100 Portfolios Formed on Size and Book-to-Market, daily, 1969-2026
- Ken French Europe 25 Portfolios Formed on Size and Book-to-Market, daily (cross-region replication panel)

**Must land on**
- fBm exponents stable across all four US panels: H_P approx 0.52-0.57 (persistent factor), H_A approx 0.17-0.27 (antipersistent factor)
- Table 3 bootstrap loss medians across the four panels: 19.3, 24.1, 18.6, 47.7
- Table 6 rank-1 (market mode) volatility-channel MSM weight: sensitivity panel w_vol_MSM = 1.00, secondhalf = 1.00, firsthalf = 0.29 (90% CI [0.10, 1.00]), FF 100 = 0.66
- Table 6 rank-1 per-mode weight rows: Sensitivity 0.16 / 0.31 / 0.19 / 1.00 / 0.00; Firsthalf 0.31 / 0.07 / 0.41 / 0.29 / 0.04; Secondhalf 0.23 / 0.38 / 0.12 / 1.00 / 0.00; FF 100 0.37 / 0.10 / 0.16 / 0.66 / 0.02
- Rolling-window (28-year windows, 2-year strides, 15 windows centred 1983-06 to 2011-06, 1000 bootstrap replicates each): median w_vol_MSM rises monotonically from 0.30 at the 1985 centre to 0.93 at the 1991 centre and saturates at 1.00 from the 1995-centred window onward; 1983-centre 90% upper bound 0.80 < 1999-centre lower bound 0.84
- MSM lowest-frequency cascade duration 1/gamma_1: 2.2 years (firsthalf) vs 4.0 years (secondhalf), bootstrap medians
- Table 8 cross-channel beta-inversion permutation test: Sensitivity rho = -0.578 (p < 1e-4), FF 100 rho = -0.615 (p < 1e-4), Firsthalf +0.181 (p = 0.215), Secondhalf -0.056 (p = 0.700)

## 26. Broken Symmetry of Stock Returns -- a Modified Jones-Faddy Skew t-Distribution

`2512.23640` · [arXiv](https://arxiv.org/abs/2512.23640v2) · **M** — an estimator has to be fitted and checked · confidence 0.94 · 2025-12-29

Splits the return distribution into gain and loss halves with separate stochastic-volatility parameters, and fits a modified Jones-Faddy skew t-distribution to daily S&P 500 log-returns by Bayesian estimation.

**Data**
- daily S&P 500 closes, 1980 to 2025 (Yahoo ^GSPC)

**Must land on**
- Figure 1 linear fit to log(St/S0) with slope mu_1 = 3.0860e-04 per day over 1980-2025
- Figure 2 detrended series x_t = r_t - mu_1 t, including the 2000 peak near +0.75 and the 2009 trough near -0.78
- Table 1 Bayesian-fitted parameters of the modified Jones-Faddy skew t against the symmetric baselines

## 27. Regime-Conditional Distributional Comparison of Trading Strategies: A GAMLSS/ZAGA Framework Applied to the S&P 500

`2606.31251` · [arXiv](https://arxiv.org/abs/2606.31251v1) · **M** — an estimator has to be fitted and checked · confidence 0.93 · 2026-06-30

Runs a 146-fold walk-forward backtest (160-day in-sample, 40-day out-of-sample, 40-day step) of a polynomial-kernel SVM on seven technical indicators against buy-and-hold on the S&P 500, then models the two fold-level Adjusted Information Ratio sequences jointly with a GAMLSS/Zero-Adjusted-Gamma regression conditioned on realised volatility and cumulative momentum, testing three nulls by parametric bootstrap.

**Data**
- ^GSPC daily closing prices, 2002-01-02 to 2025-12-31 (Yahoo Finance)
- Seven technical indicators computed from that series: SMA(15) deviation, MACD(12,26) minus 9-day signal, stochastic oscillator fastK(14)/fastD(3)/slowD(3), RSI(14), Williams %R(14), all lagged one period
- SVM polynomial kernel with p = 7, c = 2, d = 2 in regression mode; walk-forward T_IS = 160, T_OOS = 40, step 40, giving B = 146 folds

**Must land on**
- B = 146 complete folds, pooled n = 292; RS algorithm converges in 2 cycles with df = 12, residual df = 280; GAIC(BIC) = -1430.30, global deviance = -1498.43, GAIC(AIC) = -1474.43
- Table 2 Panel A (log mu): intercept -6.0478 (t = -26.704), D_SIG 1.7435 (t = 3.364, p = 0.0009), MOM 53.7625 (t = 14.387), RV -229.0470 (t = -14.222), D_SIG x MOM -57.4065 (t = -11.476), D_SIG x RV 141.2516 (t = 2.949, p = 0.0035)
- Table 2 Panel B (log sigma): intercept -0.1106 (t = -1.804), D_SIG 0.5802 (t = 6.466)
- Table 3 regime-specific E(IR*): Min. BH 0.000000 vs SVMP 0.011411 (Delta E = +0.011411); Median 0.001172 vs 0.003159 (+0.001986); Mean 0.000584 vs 0.002725 (+0.002142); 3rd Qu. 0.002706 vs 0.002136 (-0.000571); Max. 0.022197 vs 0.000068 (-0.022130)
- Table 3 variances: Median Var(BH) 1.100e-6 vs Var(SVMP) 5.797e-5; Max. 3.949e-4 vs 2.000e-8 (Delta Var = -3.949e-4)
- Table 4 parametric bootstrap p-values (N_b = 9,999): p1 = 1.0000 from Min. through Mean, 0.1143 at 3rd Qu., 0.0000 at Max.; p2 = 1.0000 through 3rd Qu. (0.9979) then 0.0000 at Max.; p3 = NA at Min., 0.8768 at 1st Qu., 0.0000 from Median onward

## 28. HODL Strategy or Fantasy? 480 Million Crypto Market Simulations and the Macro-Sentiment Effect

`2512.02029` · [arXiv](https://arxiv.org/abs/2512.02029v1) · **M** — 6 separate sources · confidence 0.93 · 2025-11-19

Runs 480 million Monte Carlo buy-hold-sell episodes across 378 non-stablecoin crypto assets over six holding-horizon buckets and eight baskets, netting trading fees and the 1-month T-bill opportunity cost, then fits a Bayesian multi-horizon local projection of forward returns and Sharpe on macro-finance predictors and the Crypto Fear and Greed Index.

**Data**
- daily High/Low/Close/Volume for the 378 surviving non-stablecoin tokens as SYMBOL-USD on Yahoo Finance, longest available history through 2025-04-26 or later
- screens to reproduce the universe: drop first-date >= 2024-01-01; drop stablecoins (mean close in [0.97,1.03] and sd <= 0.03); drop 365-day average volume < $100,000; drop last observation before 2025-04-26; drop >= 10 days with High=0, Volume=0 or Volume < $500
- 1-month Treasury bill rate for the cash opportunity cost, FRED (DGS1MO / TB4WK)
- weekly macro-finance series from FRED, Friday value stamped on the Monday of that week (codes in Appendix A.2.1)
- Crypto Fear and Greed Index daily series aggregated to weekly means, Alternative.me free API
- weekly BTC-USD log returns from Sunday closes, reindexed to the Monday that starts the week

**Must land on**
- ALL basket at the 731-1095 day horizon: median excess return -0.284 (-28.4%), mean 3.027, top-quartile mean 13.267 (+1,326.7%), and 1% CVaR that wipes out principal net of fees
- Table 4 ALL basket across horizons 1-30 / 31-90 / 91-180 / 181-365 / 366-730 / 731-1095: mean excess 0.045, 0.216, 0.597, 1.324, 2.876, 3.027 and median -0.017, -0.068, -0.112, -0.160, -0.196, -0.284
- Table 4 BTC basket medians are positive at every horizon (0.009, 0.058, 0.191, 0.519, 1.514, 2.969), the survivorship-bias contrast against ALL
- Table 4 ETH 731-1095 mean 5.308, median 1.643; XRP 366-730 mean 0.684, median 0.045
- Figure 1: CVaR(1%) rises monotonically with holding horizon for ALL and XRP, while ETH tail risk moderates from 0.899 to 0.872 in the longest bucket and BTC's CVaR falls as its Sharpe rises
- Table 2 MCMC convergence: R-hat 1.00 for all eight baskets, minimum ESS 907 (ALL), divergence rates <= 0.0005
- Figure 4: the most cross-basket-stable predictors are exclusively macro-finance factors, with FGI_EMA24 the single most stable predictor for forward mean excess return

## 29. Mens: Nonlinear shrinkage estimation in nonparanormal models for financial applications

`2607.19825` · [arXiv](https://arxiv.org/abs/2607.19825) · **M** — 500 names · confidence 0.93 · 2026-07-22

MENS applies the Ledoit-Wolf analytic nonlinear-shrinkage function to the eigenvalues of the normal-scores rank-covariance matrix, rescaled by MAD marginal volatilities, and plugs the result into a global minimum-variance portfolio.

**Data**
- Daily closing prices for S&P 500 constituents, 2013-02-08 to 2018-02-07 (paper uses a public CSV panel of 505 tickers; Yahoo Finance daily closes are a direct substitute)
- Dollar volume from the same daily OHLCV to pick the p=200 most liquid names

**Must land on**
- Table 3 MENS row: annualized out-of-sample volatility 0.0945, annualized return 0.0633, Sharpe 0.670, median condition number 339, median lambda_min 0.201, turnover 1.50
- Table 3 Ledoit-Wolf linear-shrinkage row: annualized volatility 0.1105, return 0.0741, Sharpe 0.671, condition number 1126, lambda_min 0.054, turnover 2.55
- Figure 6(a) cumulative out-of-sample GMV wealth curve 2014-2018 (MENS 9.4% vs LW 11.0% annualized vol) and Figure 6(b) rolling condition-number curve

## 30. The Three-Dimensional Decomposition of Volatility Memory

`2512.02166` · [arXiv](https://arxiv.org/abs/2512.02166v1) · **M** — 4 separate sources · confidence 0.92 · 2025-12-01

Decomposes volatility memory into level, shape and tempo gates (regime-switching, fractional integration, business-time clock), shows GARCH-type models are special cases, and compares gated models against GARCH, EGARCH and GJR on rolling one-step-ahead variance forecasts and 1%/5% VaR-ES for SPY and EURUSD.

**Data**
- daily adjusted closes for SPY, January 2005 to December 2024, Yahoo Finance
- daily EUR/USD (EURUSD=X on Yahoo, or ECB reference rates), same window, aligned on common trading days
- daily VIX (^VIX on Yahoo or FRED VIXCLS) as the implied-volatility gate input for SPY
- daily SPY trading volume for the 252-day rolling volume quantile feature

**Must land on**
- Table 2 SPY out-of-sample (n = 3,684): GARCH(1,1) QLIKE -8.184, RMSE 0.000555, FZ(1%) 0.0068, FZ(5%) 0.0032, VaR(1%) 1.17%, VaR(5%) 4.51%, Kupiec p 0.44
- Table 2 SPY: GJR-GARCH QLIKE -8.173 / RMSE 0.000574; RSM -7.808 / 0.000685; G-Clock -7.644 / 0.000649 with the lowest FZ(5%) of -0.0090; G-FIGARCH QLIKE blows up to 2.24e6 with RMSE 0.000548
- Table 3 SPY DM/Vuong: G-Clock vs GARCH(1,1) on QLIKE DM 1.72 (p 0.086), Vuong 1.95 (p 0.051); G-FIGARCH vs GARCH(1,1) on RMSE DM -2.11 (p 0.035)
- Table 4 EURUSD out-of-sample (n = 4,800): G-FIGARCH best at QLIKE -9.9079, RMSE 0.000041, FZ(1%) 0.000722, VaR(1%) 0.27%, VaR(5%) 2.88%, Kupiec p 0.0005; GARCH(1,1) -9.8492 / 0.000043 / VaR(5%) 3.87% / p 0.4414; RSM worst at -9.5234
- Table 5 EURUSD DM/Vuong: G-FIGARCH vs GARCH(1,1) on QLIKE DM -2.88 (p 0.004), Vuong 2.02 (p 0.043)
- The directional claim: fractional-memory gates win in FX while regime and clock gates win in equities

## 31. A new decomposition approach to modeling financial returns: Conditioning sign on magnitude

`2606.04153` · [arXiv](https://arxiv.org/abs/2606.04153v1) · **M** — 4 separate sources · confidence 0.92 · 2026-06-02

Decomposes monthly excess returns into sign and magnitude, models the magnitude marginal and the sign conditional on contemporaneous magnitude, and forecasts S&P 500 excess returns out of sample against linear regression, complete subset regression, GARCH-M, Markov switching, copula-based decompositions and momentum switching rules, selecting predictor subsets by in-sample AUC.

**Data**
- Welch-Goyal monthly predictor file, Jan 1948 - Dec 2021, from Amit Goyal's website (free): dp, ep, btm, dfy, tms, tbl, ltr, dfr, ntis, infl
- monthly S&P 500 value-weighted excess return over the same window (same file; cross-checkable against Ken French's Mkt-RF)
- split: first 400 monthly observations Feb 1948 - May 1981 for in-sample selection and estimation, remaining 487 (May 1981 - Dec 2021) for out-of-sample evaluation
- final eight-predictor set after dropping ep and btm for correlation above 0.80; 10 bp transaction cost; Ledoit-Wolf HACPW Sharpe test

**Must land on**
- Buy-and-hold benchmark over May 1981 - Dec 2021: annualized return 12.65%, sd 15.00%, Sharpe 0.17, terminal wealth $104.63
- Table 6 at k=3: CSM terminal wealth $181.68 with Sharpe 0.21, significant vs buy-and-hold at the 5% level; copula strategies (Gaussian/Frank/FGM) $165.23; CSR $98.22; linear model $112.79
- Table 6 at k=7: copula strategies TW $176-$178 with Sharpe 0.22 (significant at 10%); CSM Baseline TW $168.05, Sharpe 0.22
- Linear predictive regression degrades with dimension: TW $71.58 at k=4 and $62.31 at k=5; CSR peaks at $126.80
- Momentum switching benchmarks: 12-month TW $100.21 with Sharpe 0.20; 3-month and 6-month variants finish below $50
- Table 1 correlations: tbl_{t-1} has the largest absolute correlation with r_t (-0.097) and with the sign component s_t (-0.143); dfy_{t-1} correlates most with magnitude m_t (0.166), followed by dfr_{t-1} (-0.146); max pairwise predictor correlation about 0.50
- Positive out-of-sample R2_OOS (Campbell-Thompson) for the decomposition models under both squared and absolute loss; Figure 4 shows CSM (Baseline) terminal wealth is stable across k while linear methods collapse

## 32. First-passage horizons in horizontal visibility graphs: a rank-invariant estimator of path roughness for rough volatility models

`2512.02352` · [arXiv](https://arxiv.org/abs/2512.02352v3) · **M** — an estimator has to be fitted and checked · confidence 0.91 · 2025-12-02

Defines the forward visibility horizon on a horizontal visibility graph, proves it equals the first-passage time and has an exact 1/k iid survival law, derives theta(H)=1-H from fBm persistence theory, and estimates theta with a Hill-MLE using Clauset-Shalizi-Newman threshold selection on simulated paths and on the VIX.

**Data**
- daily CBOE VIX close (FRED series VIXCLS), 2000-01-01 to 2026, the exact series the paper uses
- no other real data; the fBm, rough Bergomi, Heston, GARCH(1,1) and FIGARCH benchmarks are simulated at T=2^16

**Must land on**
- VIX rolling estimate theta-hat = 0.91 +/- 0.19 across 45 four-year windows (W=1024 days, step 126 days), 2000-2026
- VIX theta-hat lies far below the overlapping-window iid Monte-Carlo null, p < 0.001
- Table 1 fBm Davies-Harte at T=2^16: H=0.1 gives theta-hat 0.900 (sd 0.013) against the prediction 0.90, bias -0.0003
- Table 2 control processes at T=2^16: iid Gaussian theta-hat 1.024 (sd 0.002), against the exact iid value 1.00
- Table 4 censoring sensitivity for the VIX rolling windows (W=1024, step 126 days)

## 33. Covariance-Aware Simplex Projection for Cardinality-Constrained Portfolio Optimization

`2512.19986` · [arXiv](https://arxiv.org/abs/2512.19986v1) · **M** — 500 names · confidence 0.90 · 2025-12-23

Introduces CASP, a two-stage repair operator for cardinality-constrained portfolios: select K assets by volatility-normalized score, then project weights onto the constrained simplex under the covariance-induced (tracking-error) metric rather than the Euclidean one, and drops it into a MOGWO metaheuristic.

**Data**
- Yahoo Finance daily adjusted close for 100 S&P 500 constituents, 2020-01-02 to 2024-11-29 (1,237 trading days); named members include AAPL, MSFT, NVDA, GOOGL, META, JNJ, UNH, LLY, PFE, JPM, BAC, GS, XOM, CVX
- Yahoo Finance sustainability/governance risk fields for the same tickers (auditRisk, boardRisk, compensationRisk, shareHolderRightsRisk, overallRisk) to rebuild ESG = 0.4*G + 0.6*ES
- Splits as specified: train 2020-01 to 2023-12 (1,006 days), test 2024-01 to 2024-11 (231 days); plus expanding splits train 2020-2021/test 2022 and train 2020-2022/test 2023

**Must land on**
- Dataset statistics that are pure free-data checks: annualized return range [-12.3%, 54.1%], annualized volatility range [22.4%, 65.5%], covariance condition number 285.0
- Table 1 (500 random projections): CASP-Basic portfolio variance 0.0442 versus Euclidean baseline, a 15.7% variance reduction with p < 1e-54 (Wilcoxon signed-rank); VolNorm+Euc 0.0449 / 14.3%, MinVar+Euc 0.0399 / 23.9%, Sharpe+Euc 0.0603 / -15.1%, RA-CASP 0.0485 / 7.4%
- Table 2 (train 2020-2023, test 2024): in-sample Sharpe Euclidean 1.306, VolNorm+Euc 1.338, CASP-Basic 1.347, RA-CASP 1.650, Sharpe+Euc 1.533; out-of-sample rank correlations 0.29 / 0.24 / 0.07 / 0.25 / 0.09; RA-CASP is 26.3% above Euclidean (1.650 vs 1.306, p < 0.0001)
- Table 3 walk-forward mean realized Sharpe: test 2022 Euclidean -0.638, CASP-Basic -0.559, RA-CASP -0.918; test 2023 0.879 / 0.474 / 0.593; test 2024 1.306 / 1.347 / 1.650
- Table 5 (15 independent MOGWO runs): best Sharpe Euclidean 0.861, CASP-Basic 0.703, RA-CASP 1.137 (32.0% above Euclidean, p = 0.0001), Sharpe+Euc 1.145; hypervolume 0.0040 / 0.0027 / 0.0142 / 0.0093

## 34. Needles in a haystack: using forensic network science to uncover insider trading

`2512.18918` · [arXiv](https://arxiv.org/abs/2512.18918v1) · **M** — an estimator has to be fitted and checked · confidence 0.90 · 2025-12-21

Builds a weighted network over corporate insiders from SEC Form 4 filings, with edge weights given by a symmetric same-week linear-decay temporal alignment kernel over each pair's trade dates at a shared issuer, then flags coordinated groups via centrality and OddBall egonet anomaly detection against calibrated and shuffled null models.

**Data**
- SEC EDGAR Form 4 filings, Part 1 non-derivative transactions, 2014-2024 full-index bulk download (roughly 2.9 million reported trades)
- Filter: remove institutional reporting owners (LLC, LP, Inc), keep individual directors, C-suite executives and >10% holders; aggregate line items sharing insider, issuer, direction and calendar day
- No price data required - the method uses trade dates and directions only

**Must land on**
- Table 1: 70,941 insiders, 9,426 companies, 2,735,932 trades after filtering, 461,785 after daily aggregation; 1,326,228 purchases and 1,409,704 sales raw (243,640 and 218,145 aggregated); average trades per insider 38.6 raw and 6.51 aggregated
- Figure 1 / text: the resulting network is sparse with 1,313 connected components
- Table 4: distribution of connected components by number of companies - 93.3% span one company, 4.6% two, 0.9% three, 0.5% four, 0.3% five, 0.3% six, 0.1% seven, 0.0% eight, 0.1% nine
- Table 2: observed network topology diverges from both the calibrated generative null and the quarterly constrained-shuffled null across four metrics drawn from 1,000 null replications (Figure 2)

## 35. Continuous Hidden Markov Models for Equity Returns: Heavy-Tail Emission Families and Regime-Conditional Value-at-Risk

`2606.23492` · [arXiv](https://arxiv.org/abs/2606.23492v1) · **M** — an estimator has to be fitted and checked · confidence 0.88 · 2026-06-22

Fits four-emission-family continuous hidden Markov models (Gaussian, Student-t, Laplace, GED) to daily equity growth rates by EM, and tests whether a few-state HMM reproduces heavy tails, near-zero return ACF and slow absolute-return ACF decay, plus regime-conditional VaR backtests.

**Data**
- daily SPY prices 2014-01-03 to 2024-01-03 in-sample (T=2,516) and 2024-01-04 to 2026-04-20 out-of-sample (T=572), Yahoo Finance
- 30-ticker sector-balanced panel, ten GICS sectors x three large caps, including LLY, UNH and NEM, same daily window, Yahoo Finance
- six-asset multi-asset basket for the Student-t copula on CHMM-N marginals, daily closes, Yahoo Finance

**Must land on**
- Table 1 observed SPY excess kurtosis 7.68 in-sample and 5.29 out-of-sample
- Table 1 KS pass rate (%) IS/OoS: CHMM-N 91.5/78.0, CHMM-t penalised 91.9/81.4, CHMM-L 80.5/63.6, CHMM-GED 90.3/78.4, ML HSMM-N 98.4/91.0, bootstrap 99.8/91.8, Gaussian iid 0.0/1.5, GARCH(1,1) 27.4/59.6
- Table 1 simulated excess kurtosis: bootstrap 7.55/6.86, Laplace iid 2.96/2.80, GARCH(1,1) 7.59/2.70, CHMM-N 3.83/3.62
- Table 1 ACF-MAE on |G| / raw G: observed-matching bootstrap 0.0628/0.0235, GARCH(1,1)-t 0.0316/0.0173, CHMM-N 0.0462/0.0240
- 30-ticker panel: in-sample KS pass median 96.8%, out-of-sample median 69.1%, mean 66.2 +/- 28.2%, 11 of 30 tickers below 60%
- Table 3 regime-conditional VaR backtest on SPY OoS (T=572): CHMM-N K=3 at alpha=0.05 gives 35 violations (6.12%), LR statistics 1.41 / 0.01 / 1.42, p 0.49 and 0.16; at alpha=0.01, 9 violations (1.57%)

## 36. The Aligned Economic Index & The State Switching Model

`2512.20460` · [arXiv](https://arxiv.org/abs/2512.20460v2) · **M** — 5 separate sources · confidence 0.88 · 2025-12-23

Introduces a state-switching predictive regression for the US equity premium in which the market state is set in real time by whether the 10Y-3M term spread was flat or inverted in the preceding tau months, and compares partial-least-squares, PCA and forecast-combination aggregations of the Welch-Goyal predictor set.

**Data**
- Welch-Goyal (2008) updated annual/monthly data file from Amit Goyal's website: the 14 standard predictors plus corporate bond premium and lagged equity premium, monthly, Jan 1950-Dec 2017; baseline sample Jan 1960-Dec 2017 (696 observations)
- S&P 500 log return including dividends minus the 3-month T-bill (both contained in the Goyal file; FRED DTB3 as a cross-check)
- FRED DGS10 and DTB3 to build the 10-year minus 3-month term spread state indicator (down state if flat or inverted at any point in the preceding tau = 9 months)
- NBER recession dates (FRED USREC) for the expansion/recession split in Table 2
- Estimation split: 1960-1979 initial window, 1980-2017 out-of-sample evaluation

**Must land on**
- Table 1 Panel A (one-state): EP_LS beta 0.05 with t = 4.38, in-sample adjusted R2 = 4.65%, out-of-sample R2 = 2.60%; EP_CA 0.20 (t = 1.96), 0.61%, 0.31%; EF_C 0.13 (t = 0.84), -0.08%, 1.18%
- Table 1 Panel B (state-switching): EP_LS delta = -0.27 (t = -2.51), beta1 = 0.03 (t = 3.46), gamma1 = 0.06 (t = 3.68), in-sample R2 = 5.90%, out-of-sample R2 = 4.12%; EP_CA 1.65% / 1.58%; EF_C 1.02% / 2.64%
- All three state-switching R2_oos values exceed the Campbell-Thompson 0.50% threshold, while in the one-state model only EP_LS does
- Table 2 Panel A: EP_LS out-of-sample R2 of 1.45% during expansions, significant at 5%; Panel B state-switching R2_oos of 1.71% and 11.21% in the corresponding state columns

## 37. Stochastic Volatility in Mean Models with Heavy Tails: A Fast Approximate Bayesian Inference Using Hidden Markov Models

`2606.22615` · [arXiv](https://arxiv.org/abs/2606.22615v1) · **M** — an estimator has to be fitted and checked · confidence 0.86 · 2026-06-21

Extends approximate Bayesian estimation of Stochastic Volatility in Mean models to Student-t, slash and variance-gamma errors from the scale-mixture-of-normals family, replacing numerical integration with special functions and a discretised HMM likelihood, then fits the models to four equity index return series and backtests VaR.

**Data**
- daily closes for the S&P 500 (^GSPC), DAX 30 (^GDAXI), NIKKEI 225 (^N225) and IBOVESPA (^BVSP), Yahoo Finance, over the paper's stated sample (the digest truncates the exact dates; Table 7 fixes them)
- log returns in percent, the four series aligned on their own trading calendars

**Must land on**
- Table 7 summary statistics (mean, sd, skewness, excess kurtosis) of the four index return series
- Table 8 SVM posterior means and 95% credibility intervals for S&P 500 and NIKKEI 225 under HMC versus the HMM-with-importance-sampling machinery; Table 9 the same for DAX 30 and IBOVESPA
- Table 10 model selection: SVM-VG gives the best LPS and DIC for most series, with SVM-S superior for IBOVESPA
- Table 11 elapsed fitting time: the HMM approach is roughly ten times faster than MCMC in every application
- Table 12 Jarque-Bera and Ljung-Box (10 lags) p-values on one-step-ahead forecast pseudo-residuals
- Table 13 empirical VaR violation rates with unconditional-coverage, independence and conditional-coverage backtest p-values
- Figure 1 exp(h_t/2) estimates tracking S&P 500 absolute returns, HMM overlapping MCMC

## 38. Stock Investment: The p-index Approach

`2606.08569` · [arXiv](https://arxiv.org/abs/2606.08569v1) · **M** — 500 names · confidence 0.85 · 2026-06-07

Defines a p-index as the model put premium per insured dollar guaranteeing at least a delta return, computed from a binomial tree fitted to each stock's own price path, then ranks stocks by p-index and p-ratio to run fair-price, momentum, contrarian and MCIRS strategies on the SSE 50 and the S&P 500 over 2018-2023.

**Data**
- daily closes for the fifty SSE 50 constituents, 2018-2023, Yahoo Finance .SS tickers; weekly Monday-to-Friday closes drive the p-index
- daily closes for the five hundred S&P 500 constituents, 2018-2023, Yahoo Finance
- SSE 50 and S&P 500 index levels and constituent lists over the period, plus GICS-style sector labels for the seven-sector cut
- risk-free rate r used as the delta target (China 1-year deposit / US T-bill, FRED DGS1MO or DGS3MO)
- market trading volume series for the high/low-sentiment regime split (Figure 10)

**Must land on**
- SSE 50 fair-price strategy, materials sector annualized returns 11.04% (one-week), 11.93% (two-week), 10.18% (one-month), and -1.02% at the fourth horizon (Table 1)
- SSE 50 one-week momentum/contrarian: p-ratio-efficient-contrarian 9.97% annualized, p-index-inefficient-momentum 9.01%, p-index-efficient-contrarian 6.48%
- SSE 50 top-three-weighting stocks under fair price: 2.31% annualized at the one-week horizon
- S&P 500 2018-2023: p-index-efficient-momentum 3.69% annualized, p-ratio-inefficient-contrarian 3.67%, beta-efficient-momentum 3.48%
- Table 2 p-values for p-index differences between high- and low-yield companies: median test 0.014088, 0.543472, 0.004586, 0.002811; Wilcoxon 0.001684, 0.016622, 0.000006, 0.000057
- Qualitative result to reproduce: on SSE 50 efficient stocks fail to sustain momentum and inefficient stocks show no mean reversion, while on the S&P 500 the opposite holds

## 39. Real-time identification of the onset of financial rogue waves

`2606.31475` · [arXiv](https://arxiv.org/abs/2606.31475v2) · **M** — 4 separate sources · confidence 0.85 · 2026-06-30

Maps volatility-index time series onto a Schrodinger equation with a Kerr-nonlinearity potential built from the Fourier-filtered envelope wave, tracks the numerical gradient of the minimum eigenvalue in an 80-trading-day moving window, and uses spikes in that gradient as a real-time rogue-wave (extreme-event) warning indicator.

**Data**
- VIX daily highs, 1990-2025 (CBOE historical data, free)
- VXO daily series covering the 1988-2020 window shown in Fig. 6 (CBOE historical data)
- VSTOXX daily series 1999-2025 (STOXX free download, or Yahoo ^V2TX)
- No other inputs: all regime covariates are derived from the index series itself

**Must land on**
- Table 1 VIX peak detection at the reliability threshold of 300: peaks detected 75.0% (>2.5 SWH) and 60.0% (>2 SWH), false signals 0% and 0%, precision 84.2% for both, precision excluding late signals 94.1% and 100%
- Table 2 VXO (threshold 700): peaks detected 87.5% / 76.9%, false signals 15.8% / 15.8%, precision 63.2% / 73.7%, precision excluding late signals 66.7% / 82.4%
- Table 3 VSTOXX (threshold 300): peaks detected 87.5% / 88.9%, false signals 11.8% / 11.8%, precision 70.6% / 76.5%, precision excluding late signals 80.0% / 86.7%
- Only the 2018 VIX peak is missed in the simulated real-time run; the 2008 warning fires on Thursday 18 September 2008, 18 trading days before the 14 October 2008 envelope peak
- Figure 5 Pearson cross-correlation between the 10-day maximum eigenvalue gradient and index height peaks just after lag tau = 0 at roughly 0.75-0.80 for all three indices, flattening about ten days later
- Window length L = 80 trading days performs best in all three indices; low signal cutoff 50 used to build the warning indicator

## 40. Modelling financial time series with $φ^{4}$ quantum field theory

`2512.17225` · [arXiv](https://arxiv.org/abs/2512.17225v1) · **M** — 500 names · confidence 0.85 · 2025-12-19

Fits a phi^4 scalar quantum field theory with inhomogeneous couplings and explicit symmetry breaking to an ensemble of S&P 500 stock log-return series, compares its reproduction of market mean and kurtosis against a binarized Ising model, extracts finite-size scaling exponents for the learned weights and biases, and forecasts next-day price changes for AAPL, MSFT and NVDA.

**Data**
- Yahoo Finance daily adjusted closes for S&P 500 constituents, 20 years back from 2023-01-01 (and a second run back from 2013-01-01), converted to log-returns
- Specific subsets: V = 20 stocks for the market mean/kurtosis comparison spanning the 2008 crisis; V = 64 for the scaling reference, with V' = 48, 32, 16 subsets for finite-size scaling
- Yahoo Finance daily closes for AAPL, MSFT and NVDA for the forecasting section (149-day conditioning window, October 2022 episode for the NVDA/MSFT conditioning experiment)

**Must land on**
- Scaling exponents at 01/01/2023: k_wij = -0.96(1) and k_ai = -0.81(1), with RMS of residuals reported alongside (bias RMS 0.84)
- Scaling exponents at 01/01/2013 using 40/40/50 random subsets for V' = 48/32/16: k_wij = -1.11(4) and k_ai = -0.87(3), RMS of residuals 0.47 and 0.86
- AAPL next-trading-day forecasting: mean absolute error 0.019 for the phi^4 result versus 0.023 for the rescaled mean prediction
- Figure 6: the phi^4 MAE is lower than rolling-window linear regression for every window size up to at least 400 days; the phi^4 effective training window is 250 days
- Figure 2: the 250-day moving-average market kurtosis of the real S&P 500 subset is reproduced by phi^4 but not by the binarized Ising model, with the 2008 crisis spike as the reference episode

## 41. Are cryptocurrencies real financial bubbles? Evidence from quantitative analyses

`2607.21826` · [arXiv](https://arxiv.org/abs/2607.21826v1) · **M** — an estimator has to be fitted and checked · confidence 0.85 · 2026-07-23

Log-Periodic Power Law (JLS) fitted by OLS, GLS and MLE to detect super-exponential price growth, cross-checked with Phillips-Shi-Yu right-tailed BSADF explosive-root tests for bubble date stamping.

**Data**
- daily BTC-USD close prices, 1 Dec 2016 - 16 Jan 2018 (Coinbase OHLCV)
- daily ETH-USD close prices, same window (Coinbase OHLCV)

**Must land on**
- Bitcoin LPPL critical-time estimates landing in mid-December 2017 and the first half of January 2018, ahead of the observed crashes
- Ether LPPL bubble signal in mid-June 2017 anticipating the 12 June 2017 crash, plus the weaker signal around 12 January 2018
- PSY BSADF and BSADF* date-stamping sequences against simulated 95% critical values over the 1 Dec 2016 - 16 Jan 2018 sample

## 42. Portfolio Allocation under Heterogeneous Scales and Multifractality

`2608.04987` · [arXiv](https://arxiv.org/abs/2608.04987v1) · **M** — an estimator has to be fitted and checked · confidence 0.85 · 2026-08-05

Replace the covariance matrix in mean-variance optimization with the sign-preserving MFCCA multifractal fluctuation matrix indexed by scale s and order q, solved as a QP with no-short-selling on a 520-day rolling window rebalanced monthly.

**Data**
- daily closing prices for Nikkei 225, S&P 500, WTI crude, gold XAU/USD (Yahoo Finance: ^N225, ^GSPC, CL=F, GC=F), Jan 2011 - Nov 2023
- no other data; synthetic ARFIMA / Markov-switching multifractal series are generated in-notebook

**Must land on**
- Figure 6 out-of-sample panel (a): average monthly drawdown in the 7.50-8.50% band across annual required returns 0-3%, with the proposed MMFC portfolio lowest at every re
- Figure 5 in-sample panels (b) and (c): rolling-window average 10-day 99% VaR of 5.0-5.4% and 10-day 97.5% ES of 5.0-5.3%, MMFC smallest ES at every re
- Table I synthetic benchmark: 50-seed average 10-period 99% VaR / 97.5% ES ranking MV > MD > MMFD > MC > MMFC (needs no data at all)

## 43. Leakage-Aware Benchmarking of LLM Forecasting: Real-Time Nowcasts as the Decision-Time Input for Macro Factor Ranking

`2606.22719` · [arXiv](https://arxiv.org/abs/2606.22719v1) · **M** — 5 separate sources · confidence 0.84 · 2026-06-21

Runs a leakage-controlled monthly walk-forward in which a retrieval-augmented Qwen2.5-7B critic-actor pipeline scores seven U.S. equity style factors from decision-time-only inputs (lag-shifted FRED macro, archived Cleveland Fed daily CPI nowcast, FOMC/CPI event summaries), and compares its rank IC against kNN macro-analog and ridge baselines.

**Data**
- FRED monthly CPI level and YoY, UNRATE, 10y minus 3m term spread, and VIXCLS, 1990-04 through 2026-03, with the stated one-month publication lag on CPI and unemployment
- Cleveland Fed daily CPI nowcast archive queried at each month-end (free; the paper's parsed copy is frozen at 2026-05-13)
- monthly factor returns for SMB, HML, RMW, CMA and UMD from the Ken French data library, plus BAB and QMJ from the AQR public factor library or the Chen-Zimmermann Open Source Asset Pricing signals
- MKT_RF from Ken French for the rolling 60-month beta used to build market-adjusted residual factor returns
- test window 2023-04-30 through 2026-03-31, 36 monthly decisions

**Must land on**
- Table 1 monthly Spearman rank IC, mean / median: full LLM pipeline +0.131 / +0.154, 95% CI [-0.02, +0.28], permutation p = 0.11
- Table 1 kNN macro analog +0.070 / +0.161, CI [-0.11, +0.24], p = 0.44
- Table 1 nowcast-only ridge +0.045 / +0.125, p = 0.63; macro + nowcast ridge +0.058 / +0.071 (n = 34), p = 0.51
- Table 1 ablation rows: zero-shot CoT +0.007 / +0.027 (p = 0.92), + raw analog retrieval +0.006 / +0.063 (p = 0.94), + critic rule synthesis +0.088 / +0.009 (p = 0.21)
- Table 2 non-overlapping 12-month sub-window mean ICs: +0.111 (2023-04 to 2024-03), +0.165 (2024-04 to 2025-03), +0.117 (2025-04 to 2026-03)
- Table 3 long-top-2 / short-bottom-2 with 5 bps per unit weight change: nowcast-only ridge -0.9% return, Sharpe -0.12, max drawdown -10.6%; macro + nowcast ridge -0.2%, Sharpe -0.01, max drawdown -10.8%

## 44. (In)Efficient Market States and Rough Volatility Detected via Grunwald-Letnikov Fractional Derivative

`2606.27932` · [arXiv](https://arxiv.org/abs/2606.27932v1) · **M** — an estimator has to be fitted and checked · confidence 0.83 · 2026-06-26

Introduces a regime-adaptive KS / GL-KS self-similarity test built on the discrete Grunwald-Letnikov fractional derivative, proves the filtered empirical-process limit and Hurst-estimator consistency, validates by Monte Carlo, then applies it to daily log-realized-volatility series and to daily equity-index log-price trajectories to classify rough volatility and (in)efficient market states.

**Data**
- Daily closes for the index panel - Yahoo tickers ^AEX, ^AORD, ^AXJO, ^BFX, ^BVSP, ^DJI, ^FCHI, ^FTSE, FTSEMIB.MI, ^GDAXI (plus the remaining realized-library indices), full history through ~2023, sample lengths 5,900-13,500 daily observations
- Optional: daily realized-variance series for the same indices (Oxford-Man / realized-library archive) for the log-volatility table
- Monte Carlo replication of fBm/fGn paths at H in {0.1,...,0.9}, N in {100, 250, 500, 1000, 5000} for the size/power tables

**Must land on**
- Full-window GL-KS Hurst estimates on log prices: DJI 0.5221 (95% CI 0.5036-0.5407, N=13,516), AEX 0.5235 (0.5023-0.5447, N=10,922), FTSE 0.5005 (0.4800-0.5210, N=10,519), BFX 0.5167 (0.4934-0.5401), BUX 0.5093 (0.4814-0.5371), AORD 0.5105 (0.4827-0.5384), FTSEMIB 0.5015 (0.4760-0.5271)
- Indices where the unfiltered KS branch is selected instead: AXJO 0.4921 (0.4684-0.5159), BVSP 0.4875 (0.4631-0.5120), FCHI 0.4964 (0.4747-0.5181)
- Empirical size of GL-KS in the long-memory regime stays near nominal (about 0.9-1.2% at 1%, 4.7-5.4% at 5%, 9.8-10.5% at 10%) while the unfiltered KS statistic inflates to 47.1% / 76.9% / 88.5% at N=100 and stays at 5.1% / 16.3% / 27.8% even at N=5,000
- Hurst estimator RMSE at N=1000: 0.0196 at H=0.10 rising to 0.0492 at H=0.80; at N=5000: 0.0087 at H=0.10

## 45. Recovering Structural Organization in Noisy Correlation Networks Using Financial Systems as a Testbed

`2607.10297` · [arXiv](https://arxiv.org/abs/2607.10297v1) · **M** — 500 names · confidence 0.82 · 2026-07-11

Splits the empirical correlation matrix into a structured component (eigenvalues above the Marchenko-Pastur bound) and noise, builds networks from the denoised matrix, and forms equal-weighted portfolios from peripheral assets.

**Data**
- Yahoo Finance daily closes for 425 S&P 500 names, 3,271 trading days, 2010-01-01 to 2022-12-31
- Yahoo Finance daily closes for NIFTY 200 (140 names) and NIFTY 500 (312 names) via .NS tickers
- index level series for the benchmark Sharpe comparison

**Must land on**
- Table 1 spectral properties: 16 eigenmodes above the Marchenko-Pastur upper bound for S&P 500 (3.76% of eigenvalues), 10 for NIFTY 200 (7.14%), 12 for NIFTY 500 (3.85%)
- Sharpe ratio of ~0.81 for the equal-weighted M=40 peripheral-asset portfolio versus ~0.51 for the market benchmark
- Figures 5-6 core-periphery centralization Q^cp time series: 0.55-0.96 for structured networks versus 0.45-0.63 for randomized ones

## 46. Local Gaussian Correlation in the Tails: A Scarcity Diagnostic, an Optimal Local Bandwidth, and the Limits of Adaptivity

`2607.03888` · [arXiv](https://arxiv.org/abs/2607.03888v2) · **M** — 4 separate sources · confidence 0.80 · 2026-07-04

Derives the first location-specific AMISE-optimal bandwidth for local Gaussian correlation, maps via Monte Carlo where adaptivity beats a global plug-in, then applies both estimators to GARCH-filtered daily equity returns and compares bootstrap stability of the tail-dependence surfaces.

**Data**
- SPY daily adjusted close, 2005-01-01 to 2024-12-31 (Yahoo Finance)
- TLT daily adjusted close, 2005-2024 (Yahoo Finance)
- EEM daily adjusted close, 2005-2024 (Yahoo Finance)
- common-trading-day intersection of the three series: n = 5030 days after filtering

**Must land on**
- Table 3 AR(1)-GARCH(1,1)-t fits, 2005-2024: SPY alpha1 = 0.141, beta1 = 0.854, nu = 5.6, resid skew -0.71, excess kurt 2.56, Ljung-Box(sq, lag 10) p = 0.41
- Table 3: TLT alpha1 = 0.054, beta1 = 0.941, nu = 15.5, resid skew -0.09, excess kurt 0.76, LB2 p = 0.13
- Table 3: EEM alpha1 = 0.097, beta1 = 0.888, nu = 9.1, resid skew -0.37, excess kurt 1.58, LB2 p = 0.06
- Table 4 diagonal-quantile local correlations SPY/EEM: q=0.01 rho_global 0.87 vs rho_adaptive 0.86 (eff_n 75); q=0.50 0.78 vs 0.79 (eff_n 1035); q=0.95 0.83 vs 0.82 (eff_n 258); q=0.99 0.81 vs 0.80 (eff_n 61)
- Table 4 SPY/TLT: q=0.05 0.37 vs 0.33 (eff_n 57); q=0.50 -0.29 vs -0.288 (eff_n 843); q=0.95 0.64 vs 0.63 (eff_n 56)
- Section 8.3 bootstrap (B=200): median adaptive/global SD ratio 0.93 for SPY/TLT (0.83 in the eff_n<40 tail band) and 0.74 for SPY/EEM (0.52 in the tail); adaptive more stable on 61% and 72% of the supported grid
- SPY/EEM adaptive bootstrap SE at q=0.95: 0.024 vs 0.055 global

## 47. Synthetic Financial Data Generation for Enhanced Financial Modelling

`2512.21791` · [arXiv](https://arxiv.org/abs/2512.21791v1) · **M** — an estimator has to be fitted and checked · confidence 0.80 · 2025-12-25

Sets up a multi-criteria evaluation framework (MMD and KS for fidelity, ACF and volatility clustering for temporal structure, mean-variance optimization and volatility forecasting for utility, NNDT for privacy) and applies it to ARIMA-GARCH, VAE and TimeGAN generators trained on daily S&P 500 returns.

**Data**
- Yahoo Finance ^GSPC daily close, January 2000 to March 2024, log-returns, ADF-tested and standardized
- Same series held out for the downstream volatility-forecasting evaluation (models trained on synthetic, evaluated on real returns)

**Must land on**
- Table 3: real S&P 500 daily returns have mean 0.12, standard deviation 1.85, skewness -0.41, kurtosis 5.62 (percent units); ARIMA-GARCH 0.11 / 1.79 / -0.32 / 4.85; VAE 0.09 / 1.29 / -0.08 / 3.18; TimeGAN 0.12 / 1.82 / -0.39 / 5.31
- Table 5: portfolio optimization scored against the real-data portfolio - TimeGAN 0.89 / -0.03 / 0.91, VAE 0.85 / -0.07 / 0.82, ARIMA-GARCH 0.81 / -0.11 / 0.73
- Table 6: volatility forecasting on real returns - TimeGAN errors 0.103 / 0.079 with R2 0.63, VAE 0.117 / 0.087 / 0.59, ARIMA-GARCH 0.124 / 0.091 / 0.56

## 48. Iterative detection of global factors near the BBP phase transition

`2607.06908` · [arXiv](https://arxiv.org/abs/2607.06908v1) · **M** — 500 names · confidence 0.80 · 2026-07-08

Iterative global-factor (IGF) detection using the participation-ratio structure of Brown-Harding factor eigenvectors to separate weak factors from Marcenko-Pastur edge noise near the BBP transition.

**Data**
- daily adjusted closes for S&P 500 constituents, Jan 2005 - Dec 2022 (Yahoo Finance), filtered to the 417 names with under 5% missing data
- optionally Ken French factor returns to regress the detected statistical factors on FF economic factors

**Must land on**
- Figure 7: IGF-detected factor count fluctuating roughly between 4 and 14 across the 185 moving windows while the Onatski test returns 1 factor in most windows
- Median detected factor count of 7 at threshold tau = 0.3 over the 185 windows of 834 daily observations shifted by 20 trading days
- Figure 8: sensitivity of the detected factor count to the participation-ratio threshold tau

## 49. Local and Global Balance in Financial Correlation Networks: an Application to Investment Decisions

`2512.10606` · [arXiv](https://arxiv.org/abs/2512.10606v1) · **M** — 5 separate sources · confidence 0.78 · 2025-12-11

Builds signed correlation networks from rolling windows of daily stock log-returns, computes global balance kappa(G) and node-level local balance kappa_i(G) via matrix exponentials, and concentrates an equal-weight portfolio in the assets whose local balance deviates most from a high global balance, benchmarked against 1/N.

**Data**
- Daily closes 2005-01-05 to 2020-09-17 for the 18 DAX members continuously in the index over the window (Yahoo, .DE)
- Same window for the 42 continuous EuroStoxx members (Yahoo, .PA / .DE / .AS / .MI / .MC)
- Same window for the 80 continuous FTSE members (Yahoo, .L)
- Same window for the 199 continuous Nikkei 225 members (Yahoo, .T)
- Rolling window length dT >= N with a 10-day step, per the paper's setting

**Must land on**
- Table 2.1 Pearson (Spearman) correlations of global balance with average market return and with Sharpe ratio: DAX -0.262 (-0.317) and -0.313 (-0.350); ESX -0.177 (-0.274) and -0.227 (-0.316); FTSE -0.215 (-0.324) and -0.199 (-0.325); NIKKEI -0.236 (-0.236) and -0.250 (-0.233)
- Table 3.1 in-sample Nikkei Sharpe-ratio moments at tauG=0.90, tauL=0.46: selected stocks mean 0.1697782, variance 0.2853324, skew 0.06643058, kurtosis 0.6962828 vs remaining stocks mean -0.01147054, variance 0.2928941, skew -0.09771086, kurtosis 1.240045
- Table 3.4 out-of-sample Nikkei at tauG=0.95, tauL=0.50: selected Sharpe 0.258769 vs remaining 0.05657042; skewness 1.751952 vs 0.1199921
- Table 3.4 at tauL=0.45: selected mean 0.2603452, variance 0.5146761, skew 1.716332 vs global 0.04530861 / 0.2191899 / 0.5939232
- Figure 3.1 thresholds under which the concentrated portfolio beats 1/N in terminal value without higher volatility: DAX (0.75, 0.35), ESX (0.75, 0.25), FTSE (0.90, 0.40), NIKKEI (0.90, 0.45)

## 50. Portfolio Optimization via Transfer Learning

`2511.21221` · [arXiv](https://arxiv.org/abs/2511.21221v1) · **M** — 5 separate sources · confidence 0.78 · 2025-11-26

Builds a transfer-learning portfolio rule that weights source-market datasets by forward validation so that uninformative sources are asymptotically discarded, proves it attains the maximum Sharpe ratio, and applies it to five dual-listed A-share/H-share firms in four sectors and to six US industry baskets of five large-cap names each.

**Data**
- daily closes for the five dual-listed firms in Energy, Manufacturing, Finance and Medical on both A-share (.SS / .SZ) and H-share (.HK) lines, July 2021 - June 2025, 968 observations, Yahoo Finance; Appendix G names the companies
- daily closes for the five largest market-cap US names in Real Estate, Financial, Construction, Furniture, Manufacturing and Marketing, January 2020 - December 2023, 877 observations, Yahoo Finance; out-of-sample block is October - December 2023 (|O| = 63)
- daily EXPI, VICI, NMRK, INVH, JLL returns Jan 2021 - Dec 2023 (753 days) for the FF3 calibration, Yahoo Finance
- daily MKT, SMB, HML factors over the same windows, Ken French data library (paper used CRSP)
- daily risk-free rate, Ken French or FRED DGS3MO

**Must land on**
- Table 2 SSR, Energy: TL 0.129 (A-shares) and 0.448 (H-shares) vs Non-transfer 0.128 and 0.364, Pool 0.111 and 0.358, TL-equal 0.101 and 0.394
- Table 2 SSR, Medical: TL 0.186 (A) and 0.968 (H) vs Non-transfer 0.183 and 0.753
- Table 2 SSR, Manufacturing: TL 0.138 / 0.191; Financial: TL 0.132 / 0.244
- Table 4 US sectors SSR under TL: Real Estate 0.129, Financial 0.354, Construction 0.089, Furniture -0.002, Manufacturing 0.181, Marketing 0.084, against Non-transfer -0.004, 0.198, -0.072, -0.046, -0.012, 0.053
- Table 5 average transferring weights, e.g. Real Estate target puts 0.523 on the first source and Manufacturing 0.519 on the third

## 51. Are Three Matrices All You Need To Beat the Market? Observable Matrix Dynamics for Portfolio Optimization

`2607.27461` · [arXiv](https://arxiv.org/abs/2607.27461v1) · **M** — 500 names · confidence 0.78 · 2026-07-29

Three price-only matrices - an arccos correlation distance matrix plus monthly decile-rank Markov transition matrices for trailing return and trailing volatility - feed covariate-conditioned rank forecasts that drive a dollar-neutral momentum long-short blended with an opportunistic long-only sleeve.

**Data**
- Daily adjusted closes and volumes for S&P 500 constituents, 2005-Jul 2026 (Yahoo Finance; paper uses CRSP pre-2018 and Yahoo Finance 2018-Jul 2026)
- Shares outstanding for market caps (SEC EDGAR XBRL)
- Optional: size/beta/illiquidity/momentum covariates, all computable from prices; the paper's Compustat ratio panel is only used in the wider descriptive study

**Must land on**
- Headline Sharpe of 1.06 for the blended long-short + long-only book vs the market's 0.78 over Jan 2022 - Dec 2024, net of 5 bps costs and marked to market daily
- Forward-test Sharpe of 1.32 vs the market's 1.14 over Jan 2025 - Jul 2026
- Residual-distance-diversified variant lifting Sharpe to 1.08 and 1.44 and annualized return from 18% to 20% and 44% to 56% on the two windows

## 52. Composite likelihood inference of fractional Gaussian processes with sequentially optimal subset selection

`2606.11962` · [arXiv](https://arxiv.org/abs/2606.11962v2) · **M** — an estimator has to be fitted and checked · confidence 0.76 · 2026-06-10

Derives Fisher and Godambe information for fractional Brownian motion and fractional Gaussian noise, builds a composite-likelihood estimator whose sub-vector design sequentially maximises Godambe information, and compares it against method-of-moments and full MLE on simulated paths and then on log-volatility and wind-speed series.

**Data**
- VIX daily close, January 1996 to January 2026 (Yahoo ^VIX, CBOE, or FRED VIXCLS), log-transformed, rolling windows of 500 observations with sub-vectors of 15 consecutive observations
- Meteo-France station 7591 (Embrun, Hautes-Alpes) 3-hour wind speed, 1996-2024, free public download, for Table 2
- optional and NOT free: 5-minute S&P 500 realised variance Jan 2000 - Nov 2018 for the RV rows (Oxford-Man library, discontinued)

**Must land on**
- Mean estimated Hurst exponent of log-VIX 0.423 (composite likelihood) vs 0.432 (moments), with standard deviations 0.025 and 0.042
- Table 1 VIX hit ratio: moments 52.23% at nu=5 and 52.12% at nu=10; composite likelihood 52.36% and 52.21%
- Table 1 VIX forecast MSE: moments 4.946e-3 and 4.939e-3; composite likelihood 4.938e-3 (DMW -1.81) and 4.928e-3 (DMW -2.12)
- Table 2 wind speed: moments hit ratio 64.40% (nu=5) and 64.57% (nu=10), MSE 0.1767 and 0.1763
- Reference values from the RV leg if the series can be sourced: mean Hurst 0.124 (composite) vs 0.129 (moments), sd 0.049 and 0.063; hit ratios 66.11%/66.35% vs 66.20%/66.49%

## 53. Bitcoin Runs on a Clock: Why Every Price Indicator Dies and the Halving Clock Doesn't

`2607.26188` · [arXiv](https://arxiv.org/abs/2607.26188v1) · **M** — 4 separate sources · confidence 0.72 · 2026-07-28

Dates each cycle's top and bottom mechanically, measures the elapsed days from each halving, and tests the clustering against a block-bootstrap null; separately shows Pi Cycle (111d SMA / 2x350d SMA), Mayer (price / 200d SMA), MVRV and Puell extremes decay monotonically across epochs.

**Data**
- Bitcoin daily OHLC (paper uses Bitstamp 2011-2026; Coinbase BTC-USD from Dec 2014 covers the three mature halving epochs)
- known halving dates / block heights at 210k, 420k, 630k, 840k (public constants)
- FRED M2 for the liquidity-versus-clock comparison (Figure 8)
- optional and NOT in Vintage: Coin Metrics CapMVRVCur and IssTotUSD for the MVRV and Puell indicators

**Must land on**
- Figure 1 / Table 1: mature-cycle tops at 525, 546 and 534 days after the 2016, 2020 and 2024 halvings, and bottoms at 406/364/366 days after each top
- Figure 3 turn-timing null: 0 of 10,000 block-bootstrap paths reproduce the top clustering, p in the 5e-6 to 1e-3 range
- Figure 2 power-law trend on log price versus log time with fitted exponent of approximately 5.6

## 54. Bayesian Distributionally Robust Merton Problem with Nonlinear Wasserstein Projections

`2512.01408` · [arXiv](https://arxiv.org/abs/2512.01408v1) · **M** — 500 names · confidence 0.71 · 2025-12-01

Places a single Wasserstein ambiguity set on the drift prior in a Bayesian Merton problem rather than time-rectangular ambiguity, reduces the robust control to optimising a nonlinear functional of the prior, calibrates the radius by a nonlinear Wasserstein projection, and compares the resulting DRBC policy against Bayesian Merton, DRC and myopic DRO-Markowitz.

**Data**
- daily adjusted closes for S&P 500 constituents, 2017-01-01 to 2024-12-31, Yahoo Finance (5 years of pre-training data plus the 2022-01-01 onward trading period)
- the constituent list over the sample so the 100 random 20-stock draws can be redrawn
- risk-free rate: the paper simplifies to 5% during trading and 4% for evaluation, so no series is strictly required, but FRED DGS3MO reproduces the stated rise from ~0% to 5%

**Must land on**
- Figure 2: across 100 random 20-stock S&P 500 draws traded daily from 2022-01-01, DRBC Sharpe ratios concentrate near 0.45-0.50 while Bayesian Merton concentrates near 0.30-0.40, with DRBC's right tail reaching ~1.15
- Figure 3: DRBC dominates DRO-Markowitz with a riskless asset, whose Sharpe distribution peaks at 0.05-0.15 with almost no mass above 0.5
- Figure 4 and Figure 5: DRBC versus DRO-Markowitz without a riskless asset, and versus DRC
- Table 2 (synthetic control, 100 simulations): Bayesian Merton Sharpe 2.1319 (sd 3.1203), DRBC 2.1374 (3.1261), DRMV_no_rf 1.9890 (3.5466), DRMV_rf 2.1037 (3.6072), DRC 1.9778 (3.4019)

## 55. Gaussian Boson Sampling for Asset Clustering in Statistical Arbitrage Portfolios

`2607.19279` · [arXiv](https://arxiv.org/abs/2607.19279v1) · **M** — 500 names · confidence 0.68 · 2026-07-21

Beta-residualized daily returns over a 5-day rolling window form an RMT-filtered correlation matrix; clusters are found by Spectral, SPONGE, and simulated Gaussian Boson Sampling dense-subgraph search, then traded as mean-reverting StatArb baskets.

**Data**
- daily close prices and dividends for S&P 500 constituents (paper uses WRDS; Yahoo adjusted closes substitute)
- market index daily returns for beta estimation (SPY or Ken French Mkt-RF)
- VIX level for the regime split (FRED VIXCLS)

**Must land on**
- Table 1 (100-stock lossless) Sharpe of 2.035 +/- 0.512 for Spectral, 2.242 +/- 0.669 for SPONGE, 2.248 +/- 0.293 for GBS Roots
- Table 1 total return 0.236 +/- 0.031 for GBS Roots vs 0.214 +/- 0.064 for SPONGE, with p=0.023 for the return difference
- Figure 5 cross-regime Sharpe across 2008 / 2017 / 2020 / 2022 and its positive correlation with VIX

## 56. Extending the application of dynamic Bayesian networks in calculating market risk: Standard and stressed expected shortfall

`2512.12334` · [arXiv](https://arxiv.org/abs/2512.12334v1) · **M** — an estimator has to be fitted and checked · confidence 0.66 · 2025-12-13

Produces 7,286 out-of-sample 10-day 97.5% expected shortfall and stressed ES forecasts for the S&P 500 (proxying a US bank equities trading desk), comparing ten traditional models (historical simulation, delta-normal, ARCH, GARCH, EGARCH, RiskMetrics under normal and skewed Student's t) against three dynamic Bayesian network structure-learning algorithms, then backtests all of them.

**Data**
- Yahoo Finance ^GSPC daily close 1991-03-15 to 2020-02-14 for the 7,286-day out-of-sample window, plus two preceding 1,264-day blocks (initial BN training and model calibration) back to roughly 1981 for the DBN arm
- Rolling 1,264-day calibration window, overlapping 10-day log returns, no square-root-of-time scaling (Basel direct 10-day method)
- For the DBN arm: the 41 macroeconomic and financial series of Appendix A, most obtainable from FRED, US Treasury yield curve and CBOE VIX family, forward-filled to daily

**Must land on**
- Returns descriptive statistics over the sample: mean 0.03%, std 1.10%, min -9.47%, max 10.96%, skewness -0.28, kurtosis 12.10
- Table 1 (ES breaches out of 7,286, normal / skewed t): ARCH(1) 19/19, GARCH(1,1) 10/21, EGARCH(1,1) 8/2, RiskMetrics 11/18; historical simulation 3, and MMHC, PC (Stable), SI-HITON-PC each 3
- Table 4 (SES breaches, normal / skewed t): ARCH(1) 2/1, GARCH(1,1) 3/0, EGARCH(1,1) 3/0, RiskMetrics 2/0; historical simulation 0, delta-normal 0, and all three BN models 0; every SES model lands in the BCBS green zone
- Table 6 forecasting error measures (ES / SES): ARCH(1) 0.0973, 0.1197, 107.948% / 0.1115, 0.1169, 117.343%; GARCH(1,1) 0.0834, 0.0892, 88.821% / 0.1337, 0.1415, 141.757%; EGARCH(1,1) 0.0864, 0.0935, 92.717% / 0.1447, 0.1534, 150.688%; RiskMetrics 0.1363, 0.1533, 147.160%; historical simulation 0.1700, 0.1728, 178.391%; delta-normal 0.1056, 0.1076, 110.690%; MMHC 0.1700, 0.1728, 178.409%; PC (Stable) 0.1698, 0.1727, 178.313%; SI-HITON-PC 0.1700, 0.1728, 178.391%
- Headline conclusion: all models fail conditional ES backtests at the 2.5% level; EGARCH(1,1) normal is most accurate for ES and GARCH(1,1) normal for SES

## 57. The Nonstationarity-Complexity Tradeoff in Return Prediction

`2512.23596` · [arXiv](https://arxiv.org/abs/2512.23596v1) · **M** — 5 separate sources · confidence 0.62 · 2025-12-29

Proposes ATOMS, a tournament model-selection procedure that jointly picks model class (ridge vs random forest) and training-window length under non-stationarity, then forecasts monthly excess returns of Kenneth French's 17 industry portfolios, Sep 1987-Nov 2016.

**Data**
- Ken French data library: 17 Industry Portfolios, monthly and daily value-weighted returns, Sep 1987-Nov 2016
- Ken French data library: daily and monthly Fama-French 3 factors (Mkt-RF, SMB, HML) plus RF, same window
- 94 characteristic-sorted long-short decile portfolio returns: Open Source Asset Pricing (Chen-Zimmermann) portfolio returns as the free stand-in for the CRSP/Compustat build of Gu-Kelly-Xiu (2020)
- 15 macroeconomic SDF factors from Chen, Pelger and Zhu (2024), published with the paper's replication code
- NBER recession dates (FRED series USREC) to define the 1990, 2001 and 2007-2009 subperiods

**Must land on**
- Table 2 / abstract: ATOMS average out-of-sample R2 = 0.049 across the 17 industries over 1990-2016, a 14% improvement over Fixed-val(512) (0.043) and more than double Fixed-val(32) (0.022); Fixed-CV = 0.035
- Table 2, Gulf War recession column: ATOMS R2 = 0.027 (positive) while Fixed-val(32) = 0.009, Fixed-val(512) = -0.031, Fixed-CV = -0.007
- Table 2, 2001 recession: ATOMS R2 = 0.125 vs Fixed-CV 0.071 (540bp gain) and Fixed-val(512) 0.117 (80bp gain)
- Table 2, 2008 crisis column: ATOMS 0.041 vs Fixed-val(32) -0.001, Fixed-val(512) 0.039, Fixed-CV 0.014
- Table 3: average cumulative-wealth excess ratio of ATOMS over baselines 3.38 / 0.48 / 0.31 / 3.54; abstract states a 31% higher cumulative return averaged across industries

## 58. Long-memory GARCH via a two-dimensional Markov chain

`2607.25189` · [arXiv](https://arxiv.org/abs/2607.25189v1) · **M** — an estimator has to be fitted and checked · confidence 0.62 · 2026-07-28

GARCH variant where level-and-slope updates of a latent power-law kernel sit in a two-dimensional Markov state, giving state-dependent decay of past shocks and long memory; estimated by Gaussian QMLE on three parameters.

**Data**
- daily open-to-close returns for SPX, FTSE 100, DAX, Nikkei 225, KOSPI, Jan 2000 - Jun 2018 (Yahoo Finance ^GSPC, ^FTSE, ^GDAXI, ^N225, ^KS11 has open and close)
- Bitcoin daily returns 2012-2025 (Coinbase from Dec 2014; paper uses Bitstamp)
- NOT in Vintage: Oxford-Man Institute 5-minute realized variance, needed only for the QLIKE and HAR-RV benchmark

**Must land on**
- Table 2 parameter estimates and fitted stability factors ranging from 0.732 for Bitcoin to 0.905 for KOSPI
- Table 4 in-sample log-likelihoods: LM-GARCH within +/-8 points of GARCH(1,1) and 13-25 points behind FIGARCH across all five indices
- Figure 6 Nikkei 225 squared-return autocorrelation out to lag 200, empirical versus LM-GARCH-implied versus GARCH(1,1)-implied

## 59. Liquidity Premium and Investment Horizons

`2607.01377` · [arXiv](https://arxiv.org/abs/2607.01377v1) · **M** — 5 separate sources · confidence 0.55 · 2026-07-01

Constructs firm-month signed order flow (volume x sign of daily price change), volume volatility, and two Kyle-lambda estimators (a within-month price-impact regression and an Amihud-style average) from daily US equity data, then runs panel and Fama-MacBeth cross-sectional regressions predicting one-month-ahead returns with Newey-West adjustment.

**Data**
- Daily close, volume, shares outstanding and return for US primary listings (NYSE/AMEX/NASDAQ), 2020-01-01 to 2025-12-31 (Yahoo Finance)
- SEC Form 25 delisting notices over 2020-2025 to reinstate names that left the listed universe
- Monthly 13-week T-bill yield as the risk-free rate (FRED DTB3 / H.15)
- MKT, SMB, HML and MOM monthly factor returns (Ken French Data Library) for the factor-spanning test
- Filters to match the paper: month-end price >= $1, at least 15 nonzero-volume trading days per firm-month, 1%/99% winsorisation

**Must land on**
- Table 1 filtered universe: 9,893 unique point-in-time firms, coverage 2020-01-01 to 2025-12
- Table 5 order-flow return regressions: intercepts 0.01229 (t = 19.40), 0.01723 (t = 26.56), 0.01197 (t = 17.04), 0.0153 (t = 20.99); N = 438,500 / 438,500 / 337,722 / 329,252; R-squared 0.0484 / 0.0007 / 0.0468 / 0.0031
- Table 6 Kyle-lambda return regressions: coefficients -101.2 (t = -6.46), 136.1 (t = 0.48), 53.69 (t = 1.30), 1355 (t = 4.08); N about 438,465-438,471; R-squared 0.0001 / 0.0000 / 0.0000 / 0.0001
- Table 3 volume-based variables: mean dollar volume 25,104,816.66, mean volume volatility 698,023.91, mean signed flow 927,410.24, signed-flow median 10,606.00
- Table 8 lambda-construction robustness: N = 438,471 / 438,471 / 438,465 / 438,465 with R-squared 0.0000-0.0001
- Qualitative signs a replication must land on: signed order flow predicts contemporaneous and one-month-ahead returns positively; volume volatility predicts lower subsequent returns

## 60. Signature-Based Optimal Execution for Statistical Arbitrage with Path-Dependent Trading Signals

`2606.31387` · [arXiv](https://arxiv.org/abs/2606.31387v2) · **M** — 4 separate sources · confidence 0.50 · 2026-06-30

Models both the alpha process and the trading speed as linear functionals of the truncated signature of a time-augmented market path, proves the restricted path-dependent execution problem reduces to a finite-dimensional concave quadratic programme, and compares the fitted policy's return on turnover against a z-score pairs-trading benchmark on synthetic OU spreads and on a Shell/BP backtest.

**Data**
- SHEL.L intraday (hourly) bars, January 2025 to December 2025 (Yahoo Finance, 1h interval within the 730-day window)
- BP.L intraday (hourly) bars, same window (Yahoo Finance)
- Train/test split: signature moments estimated from four-day trading windows Jan-Oct 2025; policy evaluated on Nov-Dec 2025
- Execution parameters as published: Lambda = diag(1e-1, 1e-2), eta = 1e-2, phi = 0, gamma = 1, c_alpha = 1, beta = 1, signature truncation N = 2, lambda_ridge = 0, 8-hour rolling z-score window

**Must land on**
- Historical Shell/BP out-of-sample window (Nov-Dec 2025): signature policy return on turnover approximately 9 bps versus approximately 2 bps for the z-score threshold benchmark
- In that test window the z-score strategy records negative November performance while the signature policy stays positive on accounting PnL
- Synthetic OU benchmark (10,000 training paths, 5,000 test paths, kappa = 50, sigma_M = sigma_X = 0.02, rho = 0.3, c_alpha = 1.5): signature ROT approximately 9 bps versus 6 bps for the z-score rule
- Appendix D calibration check: closed-form OU blocks give relative coefficient error 1.3e-2 and objective gap 2.4e-3, versus 9.3e-2 and 1.2e-1 for the M = 25 small-sample empirical fit

## 61. Institutional Backing and Crypto Volatility: A Hybrid Framework for DeFi Stabilization

`2512.19251` · [arXiv](https://arxiv.org/abs/2512.19251v1) · **M** — 5 separate sources · confidence 0.45 · 2025-12-22

Builds a daily panel of 18 major cryptocurrencies (Jan 2020 - Nov 2024) with Parkinson price risk, Amihud illiquidity, log market-cap change, a published decentralization index, Google-Trends attractiveness and a Crypto-50 realized volatility, then estimates panel EGLS (RE, FE, dynamic) testing whether institutionally backed 'HyFi-like' coins are less exposed to market-wide turbulence.

**Data**
- Yahoo Finance daily OHLCV, 2020-01-01 to 2024-11-24, for the 18 sampled coins listed in Table 3 (BTC, ETH, SOL, XRP, ADA, BNB, CRO, OKB, XLM, UNI and the remaining eight), 1,790 observations each; Coinbase spot as a cross-check on the majors
- Daily market capitalisation for the Size variable - reconstruct as close price times circulating supply, since Yahoo does not carry historical market cap
- Google Trends daily search volume per coin for the Attractiveness proxy
- Decentralization index values are published in the paper's Table 4 (BTC 0.5493, ETH 0.7073, SOL 0.6454, XRP 0.6671, ADA 0.6201, BNB 0.6923, CRO 0.7304, OKB 0.6929, XLM 0.7710, UNI 0.5648) - no data pull needed
- A cap-weighted top-50 crypto index for the 30-day realized market volatility, rebuilt from free per-coin prices

**Must land on**
- Table 9 fixed-effects: HyFi x Market Volatility coefficient -0.3422 (s.e. 0.0261, p < 0.01); dynamic FE interaction -0.2778 (0.0285)
- Table 9: HyFi-like main effect -0.0091 (0.0044) in random effects and -0.0102 (0.0004) in dynamic RE; Market Volatility 0.4239 / 0.4797 / 0.3123 / 0.3728 across the four specifications
- Table 9: lagged price-risk persistence phi = 0.3467 (dynamic RE) and 0.2918 (dynamic FE); adjusted R2 0.6460 / 0.6782 / 0.7149 / 0.7458; Hausman 6.4912 [p = 0.3705] static, 3434.2322 [p = 0.0000] dynamic
- Text: long-run attenuation beta_INT/(1-phi) = -0.392; implied short-run slopes 0.3728 non-HyFi versus 0.0950 HyFi, long-run 0.526 versus 0.134
- Table 7 descriptive statistics on 30,923 observations: mean daily price risk 0.063, median 0.049, max 1.436, min 0.003, std 0.054, skew 4.284, kurtosis 47.374

## 62. Squeezed Covariance Matrix Estimation: Analytic Eigenvalue Control

`2512.23021` · [arXiv](https://arxiv.org/abs/2512.23021v1) · **M** — 4 separate sources · confidence 0.45 · 2025-12-28

Reformulates the Gerber Informational Quality correlation estimator as a convex 'squeezing' combination of PSD atomic channel matrices with a closed-form eigenfloor, giving PSD by construction and analytic eigenvalue/condition-number control, then runs long-only monthly tangency backtests with 10bp costs against shrinkage, random-matrix and Gerber estimators.

**Data**
- Monthly total returns Jan 1988-Dec 2024 for a 10-sleeve universe: US large-cap (^SP500TR, Yahoo), US small-cap (^RUT / IWM, Yahoo), developed ex-US (EFA, Yahoo; MSCI EAFE pre-2001 needs a proxy), emerging markets (EEM, Yahoo), US growth (IWF / ^SP500 Growth, Yahoo)
- Aggregate bond total return: FRED BAMLCC0A0CMTRIV; high-yield total return: FRED BAMLHYH0A0HYM2TRIV
- Listed real estate (VNQ / ^RMZ, Yahoo), gold (GC=F or GLD, Yahoo), broad commodities (^SPGSCI, Yahoo)
- Risk-free / T-bill rate for the tangency objective: FRED DTB3

**Must land on**
- Table 4: AIQ1 after-cost out-of-sample Sharpe 0.56 (highest), AIQ2 0.54, LS1 0.54, GS1 0.51, GS* 0.51, GS3 0.50, GS2 0.44, over 2000-2024 with monthly rebalancing and 10bp costs
- Table 4: AIQ1 annualized volatility 7.70% and AIQ2 7.65%, versus LS1 at 11.40%; AIQ drawdowns approximately -28% versus LS1 -36.53%
- Table 5 aggregate rank score (sum of per-metric ranks, lower better): AIQ1 = 34 (best), AIQ2 = 52, GS1 = 63, GS* = 65, LS1 = 69, GS2 = 116 (worst)
- Calibration split: in-sample 1988-1999 for hyperparameters, out-of-sample 2000-2024, lookback tau = 20 months, N = 10

## 63. Investigating Conditional Restricted Boltzmann Machines in Regime Detection

`2512.21823` · [arXiv](https://arxiv.org/abs/2512.21823v2) · **M** — 4 separate sources · confidence 0.40 · 2025-12-26

Trains Conditional Restricted Boltzmann Machines (Bernoulli-Bernoulli on 16-bit discretized returns, and Gaussian-Bernoulli on z-scored returns) with Persistent Contrastive Divergence on a 19-series cross-asset panel, then studies whether the model's free energy works as an unsupervised systemic-risk / regime signal.

**Data**
- Yahoo Finance daily: ^GSPC, ^VIX, ^VIX3M, ^SKEW, MTUM, VLUE, QUAL, DX-Y.NYB, CL=F, GC=F, Jan 2013 to Jan 2025
- FRED daily: DGS2, DGS10, T10Y2Y, T10YIE, plus BAMLC0A0CM (IG OAS) and BAMLH0A0HYM2 (HY OAS) as free stand-ins for LUACOAS and LF98TRUU
- Substitutes required for three Bloomberg-only inputs: MOVE (^MOVE on Yahoo is partial), CESIUSD (Citi Economic Surprise, no free source), BFCIUS (use FRED NFCI)
- Train/test split fixed by the paper: train 2013-2019, test 2020-2025

**Must land on**
- Figure 3: Bernoulli-Bernoulli free energy over 2013-2025 oscillates in roughly the -98,000 to -108,000 band with no discernible level shift at the COVID-19 crash or the 2022 inflation shock, i.e. the discrete model fails as a regime detector
- Figures 4-5: Gaussian-Bernoulli CRBM reproduces the static cross-asset correlation matrix but the QQ plot of synthetic versus real returns collapses toward Gaussian in the tails
- Figures 6-7: Gaussian free-energy series spikes coincide with VIX spikes over the 2020-2025 test window, with the quadratic (magnitude) and structural (correlation) components separating pure magnitude shocks from regime changes (Figure 8)

## 64. Stochastic Volatility Modelling with LSTM Networks: A Hybrid Approach for S&P 500 Index Volatility Forecasting

`2512.12250` · [arXiv](https://arxiv.org/abs/2512.12250v1) · **L** — a model has to be trained, so results move with the seed · confidence 0.94 · 2025-12-13

Forecasts 21-day rolling realized volatility of the S&P 500 with a hybrid model that feeds stochastic-volatility model output into an LSTM, using a rolling-window scheme with per-window hyperparameter tuning, and evaluates against standalone SV and LSTM by error metrics, Diebold-Mariano style tests, and a trading simulation.

**Data**
- Yahoo Finance ^GSPC daily close 1998-01-01 to 2024-12-31; daily log returns; 21-day rolling unbiased standard deviation as the target
- Rolling-window training with out-of-sample evaluation over January 2014 - December 2024 (11 windows), hyperparameter grid as published in Tables 4-5

**Must land on**
- Table 1 descriptive statistics, close prices: mean 2044.98, median 1432.73, std 1220.20, min 676.53, max 6090.27, skewness 1.3333, kurtosis 0.8033
- Table 1 log returns: mean 0.000265, median 0.000633, std 0.012225, min -0.127652, max 0.109572, skewness -0.3822, kurtosis 9.8617
- Table 3: SV model MAPE 18.12% versus 21-day rolling historical volatility, MSE 9e-6
- Table 6: LSTM MAPE 5.29% on January 2014 - December 2024
- Table 14 sensitivity MAPE row: 5.73%, 5.84%, 6.40%, 4.75% across dense-layer variants
- Table 15 investment simulation, best strategy: Sharpe 0.54, Calmar 0.26, annualized return 10.03%, annualized std 22.96%, max drawdown -38.27%, total return 183.02%; competing variants Sharpe -0.54, -0.46, -0.56, -0.76 with total returns -80.18%, -76.60%, -82.00%, -88.94%; second best 0.53 / 9.92% / 179.96%
- Headline ordering: hybrid SV-LSTM beats both standalone SV and standalone LSTM on the 2014-2024 out-of-sample window

## 65. Adaptive Weighted Genetic Algorithm-Optimized SVR for Robust Long-Term Forecasting of Global Stock Indices for investment decisions

`2512.15113` · [arXiv](https://arxiv.org/abs/2512.15113v1) · **L** — a model has to be trained, so results move with the seed · confidence 0.93 · 2025-12-17

Builds an improved genetic-algorithm-optimized SVR (IGA-SVR) that weights the most recent five years of training MAPE, and forecasts one year ahead of daily closing prices for five global equity indices, benchmarked against LSTM and a forward-validating GA-SVR (OGA-SVR).

**Data**
- Yahoo Finance daily close: ^NSEI (Nifty 50), ^DJI (Dow Jones Industrial Average), ^GDAXI (DAX), ^N225 (Nikkei 225), 000001.SS (SSE Composite), April 2008 - December 2024, forward-filled to a common calendar
- Test protocol: last year of data held out, rolled over four one-year prediction windows (2021, 2022, 2023, 2024)

**Must land on**
- Abstract: IGA-SVR cuts MAPE by 19.87% versus LSTM and by 50.03% versus OGA-SVR across the five indices, 2021-2024
- Index-level table (SSE): average MAPE 8.65% (LSTM), 16.03% (OGA-SVR), 7.15% (IGA-SVR); yearly MAPE rows 12.38/9.5/3.05, 4.36/28.62/14.5, 9.46/6.19/5.66, 8.41/19.81/5.39
- Average execution time 271 s (LSTM), 4 s (OGA-SVR), 22 s (IGA-SVR); yearly 223/275/290/294 s for LSTM
- Table 3 hyperparameter search box: C in [0.01, 1], epsilon in [0.1, 1], RBF gamma in [0, 'scale'/10], 30 GA generations
- Table 1 positive/negative closing shares: DJI 54/46, NIFTY 53/47, DAX 53/47, N225 53/47, SSE 52/48

## 66. Addressing Market Regime Changes and Heavy-Tailed Returns in Portfolio Optimization via Bayesian VAR and Elliptical Black-Litterman

`2606.09104` · [arXiv](https://arxiv.org/abs/2606.09104v1) · **L** — a model has to be trained, so results move with the seed · confidence 0.92 · 2026-06-08

Combines a 600-model Bayesian-averaged VAR ensemble over HAR features with an elliptical (Student-t) Black-Litterman step, a transformer that generates views and a CNN that estimates risk aversion, then refines the resulting weights with a TD3 reinforcement-learning agent on 29 DJIA stocks.

**Data**
- daily adjusted close and volume for the 29 DJIA constituents excluding NVDA, January 2014 - December 2024, Yahoo Finance / yfinance
- split of 1640 training days, 547 validation days, 547 test days; transaction cost 0.25% per rebalance, 15-day lookback window
- risk-free rate for the Sharpe and Sortino calculations, FRED DGS3MO

**Must land on**
- Table 2 test set: BAVAR-BLED 57.26% return, Sharpe 1.72, Sortino 2.70, MDD -8.85%, vol 12.64%
- Table 2 benchmarks: Dual MA 48.14% / 1.59, TimeXer 47.77% / 1.57, Informer 39.59% / 1.52, Equal Weight 45.16% / 1.51, PatchTST 42.21% / 1.50, iTransformer 45.33% / 1.45, Momentum 48.03% / 1.44, Risk-Adj DRL 52.70% / 1.21, Min Variance 20.92% / 0.92, EIIE 34.49% / 0.73, Mean-Variance 35.86% / 0.72, A2C 7.78% / 0.65, PPO -0.39% / -0.01
- Table 4 ablation: BAVAR 100 models 52.62% / 1.68, w/o BLED 46.26% / 1.41, BAVAR 1000 models 43.11% / 1.48, w/o CNN risk 41.28% / 1.35, w/o HAR 39.28% / 1.39, w/o transformer views 37.59% / 1.33, w/o BAVAR -6.45% / 0.05 with MDD -29.33%

## 67. Exploratory Mean-Variance with Jumps: An Equilibrium Approach

`2512.09224` · [arXiv](https://arxiv.org/abs/2512.09224v1) · **L** — a model has to be trained, so results move with the seed · confidence 0.90 · 2025-12-10

Solves the exploratory (RL-regularised) time-inconsistent mean-variance problem under jump diffusion, obtains a Gaussian equilibrium policy centred on the classical equilibrium control, trains it with an orthogonality-condition actor-critic loss, and evaluates it on 14 rolling ten-year-train / one-year-test windows of the S&P 500.

**Data**
- S&P 500 total-return index, daily, 2000-01-01 to 2023-12-31 (Yahoo Finance ^SP500TR)
- US 3-month Treasury bill yield, daily, same window (Yahoo Finance ^IRX, or FRED DTB3)
- 14 eleven-year rolling windows 2000-2010 through 2013-2023, first 10 years train / final year evaluate

**Must land on**
- Table 1 MLE 'ground truth' Merton jump-diffusion parameters fitted to the 2000-2023 S&P 500: mu = 0.0878, sigma = 0.1321, zeta_J = 27.6813, mu_J = -0.0040, sigma_J = 0.0274, implied delta = 0.1449
- Table 4 evaluation-year terminal portfolio mean / volatility / Sharpe: 2010 1.0666 / 0.1726 / 0.3784; 2013 1.2297 / 0.1006 / 2.2791; 2017 1.0880 / 0.0427 / 1.8451; 2019 1.4672 / 0.1384 / 3.2274; 2020 1.6298 / 0.4761 / 1.3158; 2021 1.8431 / 0.1726 / 4.8834
- Table 4 the two loss years: 2018 mean 0.9975, vol 0.1412, Sharpe -0.1548 (risk-free 1.0194); 2022 mean 0.2339, vol 0.3555, Sharpe -2.2119 (risk-free 1.0202)
- Table 4 MLE-parameter comparison policy is beaten on Sharpe in every evaluation year except 2018 and 2022 (e.g. 2021 SR_MLE 2.2434 vs model 4.8834; 2019 2.0840 vs 3.2274)
- Headline count: mean terminal value exceeds the risk-free portfolio in 12 of the 14 evaluation windows (abstract states profitable in 13 of 14 tests)
- Table 3 training-period terminal means: 2009-2019 3.6082, 2010-2020 4.9670, 2011-2021 5.5411, 2012-2022 7.4664, 2013-2023 5.2763
- Table 2 simulated-data check (secondary): gamma = 1 realized mean 1.1998 vs theoretical 1.2021; gamma = 5 realized 1.0400 vs theoretical 1.0404

## 68. Macro Economists in the Machine: A Multi-Agent LLM Framework for Commodity-Related ETF Portfolio Construction

`2606.08283` · [arXiv](https://arxiv.org/abs/2606.08283v1) · **L** — a model has to be trained, so results move with the seed · confidence 0.90 · 2026-06-06

Feeds identical FRED macro z-scores to a Hawkish LLM agent, a Dovish agent, a Debate agent and a deterministic z-score Rule agent, routes all four tilt vectors through the same inverse-volatility portfolio engine over 124 weekly rebalances on fifteen commodity-related ETFs, and tests Sharpe differences by stationary block bootstrap.

**Data**
- daily adjusted closes for GLD, SLV, PALL, TMET, USO, BNO, DBO, GSG, PDBC, FTGC, BCI, COWZ, CORN, WEAT, SOYB from October 2022, Yahoo Finance; evaluation runs October 2023 to February 2026 over 124 weekly rebalancing dates
- FRED series VIXCLS plus broad trade-weighted dollar index, fed funds rate, INDPRO, breakeven inflation, real yield and UNRATE, with release-lag-aware timing and rolling 156-week z-scores
- risk-free rate for Sharpe, FRED

**Must land on**
- Table 3 full period: Rule Agent 7.11% annualized return, 13.50% vol, Sharpe 0.53, MDD -9.15%, hit rate 55.65%; Hawkish 7.74% / 13.57% / 0.57 / -9.37%; Dovish 7.61% / 13.57% / 0.56 / -9.48%; Debate 7.69% / 13.57% / 0.57 / -9.40%; Inverse Volatility 6.68% / 12.81% / 0.52 / -9.54%
- Delta-Sharpe versus the Rule Agent: Hawkish +0.044 and Debate +0.040, both p < 0.10 under stationary block bootstrap; Debate versus best single agent -0.004 with p = 0.769
- Table 6 sub-period Sharpe: Rates Peak 2023 -1.46 (Rule), -1.33 (Hawkish), -1.32 (Dovish), -1.32 (Debate), -1.30 (Inverse Vol); Soft Landing 2024-25 0.84, 0.86, 0.85, 0.86, 0.80
- Table 7 transaction-cost ladder at 0/5/10/20/30 bps one-way: Rule 0.526, 0.520, 0.514, 0.503, 0.491; Hawkish 0.571, 0.567, 0.562, 0.554, 0.546; Inverse Vol 0.521, 0.514, 0.508, 0.494, 0.481 - the Rule Agent's edge over passive disappears near 5 bps while the LLM agents survive to 30 bps
- Debate Agent Sharpe sits 0.001 above the arithmetic mean of Hawkish and Dovish Sharpe ratios
- Active-return attribution: largest positive contributions from SLV, GLD and PALL; BNO and CORN detract

## 69. Hybrid LSTM and PPO Networks for Dynamic Portfolio Optimization

`2511.17963` · [arXiv](https://arxiv.org/abs/2511.17963v1) · **L** — a model has to be trained, so results move with the seed · confidence 0.90 · 2025-11-22

Trains per-asset LSTM return forecasters and feeds their predictions into a PPO allocator with Top-K sparse long-only weights across a 32-asset universe of Nasdaq-100 names, IDX30 Indonesian equities, the 10-year Treasury yield and the ten largest cryptocurrencies, then compares to equal-weight, index and single-model baselines.

**Data**
- daily adjusted closes for Nasdaq-100 constituents, Jan 2018 - Dec 2024, Yahoo Finance
- daily adjusted closes for IDX30 constituents (Yahoo .JK suffix), same window
- ^TNX US 10-year Treasury yield, Yahoo Finance (or DGS10 on FRED)
- BTC-USD, ETH-USD, XRP-USD, BNB-USD, SOL-USD, DOGE-USD, ADA-USD, TRX-USD, TON-USD, DOT-USD daily closes, Yahoo Finance
- SPY for the S&P 500 benchmark row, Yahoo Finance
- chronological 70/30 train-test split on the weekly series, 0.1% per-unit-turnover transaction cost

**Must land on**
- Table 2 Hybrid LSTM+PPO Top-5: annual return 0.2538, volatility 0.2653, Sharpe 0.9565, max drawdown -0.1369
- Table 2 Hybrid LSTM+PPO Top-10: 0.0983 / 0.2168 / Sharpe 0.4535 / MDD -0.1197; Top-30: 0.1025 / 0.1780 / Sharpe 0.5756 / MDD -0.1060
- Table 2 PPO-only Top-10 Sharpe 1.0219 (return 0.2020, vol 0.1977, MDD -0.0787) - the single best baseline
- Table 2 LSTM-only Top-5 return -0.0303, Sharpe -0.0575; Top-30 return 0.1575, Sharpe 0.4821
- Table 2 benchmarks: S&P 500 return 0.0679, vol 0.2000, Sharpe 0.0034, MDD -0.0787; Equal-Weight return 0.0042, Sharpe 0.0003, MDD -0.0719
- Figure 6: drawdowns shrink monotonically as Top-K rises from 5 to 30; Figure 8: all three hybrid equity curves finish above both single-model baselines and the traditional benchmarks

## 70. Integrating LSTM Networks with Neural Levy Processes for Financial Forecasting

`2512.07860` · [arXiv](https://arxiv.org/abs/2512.07860v1) · **L** — a model has to be trained, so results move with the seed · confidence 0.88 · 2025-11-26

Ensembles a Grey-Wolf-tuned LSTM price forecast with volatility paths from a Levy-Merton jump-diffusion (and a fractional Heston variant), calibrating the stochastic model by neural network, Marine Predators Algorithm or TorchSDE, and scores the hybrid against a plain LSTM on three daily price series.

**Data**
- Brent crude daily prices Jan 2010 - Jul 2024 (Yahoo BZ=F, or FRED DCOILBRENTEU)
- STOXX Europe 600 daily index level Jan 2010 - Jul 2024 (Yahoo ^STOXX)
- FTSE MIB (IT40) daily index level Jan 2010 - Jul 2024 (Yahoo FTSEMIB.MI / ^FTMIB)

**Must land on**
- Table 1 Brent: LSTM-Levy with NN calibration MAE 0.00045, MSE 4.5e-6, RMSE 0.0021213, MSPE 1.52e-5, R2 0.996976 vs plain LSTM R2 0.9858887
- Table 1 Brent: LSTM-Levy torchsde R2 0.7470060 and LSTM-Levy MPA R2 0.9606901
- Table 3 STOXX 600: LSTM-Levy NN R2 0.9766209 vs plain LSTM 0.9688279; torchsde 0.1804342; MPA 0.7934849
- Table 5 IT40: LSTM-Levy NN R2 0.9981446 vs plain LSTM 0.996717; torchsde 0.7715017; MPA 0.899238
- Table 7 LSTM-Fractional-Heston (NN-calibrated) R2 0.9939523 (Brent), 0.9818162 (STOXX 600), 0.997859 (IT40)
- Table 2 Levy parameters for Brent by method: NN runtime 240 s with (0.58, 0.05, 0.19, 0.0004, 0.45); torchsde 3158 s; MPA 2273 s

## 71. Bayesian Modeling for Uncertainty Management in Financial Risk Forecasting and Compliance

`2512.15739` · [arXiv](https://arxiv.org/abs/2512.15739v1) · **L** — a model has to be trained, so results move with the seed · confidence 0.86 · 2025-12-06

Builds a Bayesian pipeline with three arms: a discount-factor dynamic linear model for one-step-ahead log-realized-volatility and 95% VaR on S&P 500 daily returns (train 2000-2019, test 2020-01-02 to 2024-12-30), Bayesian logistic regression for card-fraud detection on IEEE-CIS, and a hierarchical Beta state-space model for compliance risk, comparing against GARCH(1,1)-t and an LSTM.

**Data**
- S&P 500 daily closes / log-returns 2000-01-01 to 2024-12-30 - Yahoo ^GSPC (train 2000-2019, out-of-sample T=1,257 days 2020-01-02 to 2024-12-30)
- Daily realized-volatility proxy for the log-RV forecasting table (e.g. squared-return or range-based RV from ^GSPC OHLC, or an archived realized library)
- IEEE-CIS Fraud Detection dataset (free Kaggle) for the fraud arm

**Must land on**
- 95% VaR backtest on S&P 500, T=1,257: DLM N=75 exceedances, p-hat=0.060, LR_uc=2.335 (p=0.127), LR_ind=4.131 (p=0.042), LR_cc=6.465 (p=0.039)
- GARCH(1,1)-t: N=130, p-hat=0.103, LR_uc=58.513 (p=0.000), LR_ind=1.766 (p=0.184), LR_cc=60.279 (p=0.000)
- LSTM: N=68, p-hat=0.054, LR_uc=0.433 (p=0.510), LR_ind=1.398 (p=0.237), LR_cc=1.831 (p=0.400)
- Volatility forecasting: Bayesian DLM MAE 0.0589 / RMSE 0.0754 / CRPS 0.0412 / 94% coverage 97.4%; GARCH(1,1) 0.0684 / 0.0684 / 0.0683 / 100%; LSTM 0.0511 / 0.0808 / 0.0511 / 94.7%
- Fraud detection: Bayesian logistic AUC-ROC 0.953, precision@5%FPR 0.030, recall 0.842 vs XGBoost 0.93 / 0.027 / 0.80, Random Forest 0.91, Isolation Forest 0.85

## 72. A3T-GCN for FTSE100 Components Price Forecasting

`2511.21873` · [arXiv](https://arxiv.org/abs/2511.21873v1) · **L** — a model has to be trained, so results move with the seed · confidence 0.82 · 2025-11-26

Applies an A3T-GCN (attention temporal graph convolutional network) to forecast next-day closing prices of 79 FTSE 100 constituents, with node features RSI, MACD, normalized and log returns and annualized log returns over 1W/2W/1M/2M windows, and graphs built from sector classification plus Pearson correlation of returns.

**Data**
- Yahoo Finance daily OHLCV for 79 FTSE 100 constituents (.L tickers), 2007-2024, approx. 375,329 observations / 4,751 daily observations per name
- London Stock Exchange 25-industry sector classification for the sector-based graph edges (free from LSE / Yahoo profile sector fields)
- Derived node features computed from the same prices: RSI, MACD, normalized returns, log returns, ALR1W, ALR2W, ALR1M, ALR2M

**Must land on**
- Table 4 Primary (5-day sequence, 1-day horizon): MAE 0.0441, MSE 0.0044, RMSE 0.0660, MRE 3.46%
- Table 4 Version 4 (5SL8D): MAE 0.1227, MSE 0.0288, RMSE 0.1698, MRE 11.67% - roughly triple the 1-day MAE/RMSE and nine times the MSE
- Table 4 Version 5 (30SL1D): MAE 0.0512, MSE 0.0051, RMSE 0.0712, MRE 4.86%, i.e. worse than the 5-day sequence at the 1-day horizon
- Table 4 Version 8 (30SL8D): MAE 0.0850, MSE 0.0139, RMSE 0.1179, MRE 8.09%; the 30-length model overtakes the 5-length model from a 3-day horizon onward
- Table 3 one-sample t-test, Pearson-on-returns graph vs Spearman-on-fundamental-ratios graph: mean squared-error difference -0.0008468, t = -18.5332, p = 1.110e-76, 95% CI [-0.0009364, -0.0007573]
- Ablation: removing the ALR features destroys the 5-day sequence's advantage over the 30-day sequence; ALR adds ~3:03 min compute vs ~6:48 min for extending the sequence to 30

## 73. Interpretable Hypothesis-Driven Trading:A Rigorous Walk-Forward Validation Framework for Market Microstructure Signals

`2512.12924` · [arXiv](https://arxiv.org/abs/2512.12924v1) · **L** — a model has to be trained, so results move with the seed · confidence 0.82 · 2025-12-15

Builds a walk-forward validation harness for five hand-crafted market-microstructure hypothesis types (institutional accumulation, flow momentum, mean reversion, breakout, range-bound value) driven by a 54-feature vector from daily OHLCV, with an RL agent selecting which hypothesis type to trade, tested over 34 rolling out-of-sample quarters.

**Data**
- Yahoo Finance daily OHLCV via yfinance for 100 US large-cap equities (10 per GICS sector, top-10 by average dollar volume, ADV >= $10M, market cap >= $5B as of January 2015) plus SPY, 2015-01-02 to 2024-10-31 (2,475 trading days)
- ^VIX daily close (CBOE, free) for the regime split (2017-2019 VIX average 14.5, 2020 VIX peak 82.7)

**Must land on**
- Aggregate: mean quarterly return 0.14% (0.55% annualized), quarterly std 0.82%, annualized Sharpe 0.33, max drawdown -2.76%, beta 0.058
- Fold-level win rate 41% (14 of 34 folds positive), best fold +2.73%, worst fold -1.04%; trade-level win rate 46.5% over 140 trades
- Significance: t-stat 0.96, p = 0.34 two-sided, df = 33, 95% bootstrap CI [-0.12%, +0.43%], Monte Carlo permutation p = 0.98, binomial win-rate p = 0.89
- Table 3 regimes: Low Volatility 2015-2019 16 folds -0.16% quarterly, 37.5% win, Sharpe -0.21; Pre-COVID Bull 2017-2019 8 folds -0.32%, 37.5%, -0.58; COVID Crash 2020Q1-Q2 2 folds -0.15%, 50.0%, -3.30; Bear Market 2022 4 folds -0.70%, 0.0%, -3.23; high-volatility 2020-2024 +0.60% quarterly
- Benchmark comparison: strategy 0.55% annualized vs SPY 13.2% annualized over the same window

## 74. Heads, Not Backbones: Output Heads Dominate Architectures on Fat-Tailed Returns

`2606.30037` · [arXiv](https://arxiv.org/abs/2606.30037v1) · **L** — a model has to be trained, so results move with the seed · confidence 0.82 · 2026-06-29

Crosses four deep forecasting backbones (TimesNet, DLinear, N-BEATS, iTransformer) with three output heads (point/Huber, single-Gaussian NLL, K=4 Gaussian-mixture NLL) on S&P 500 monthly log-returns 1871-2023, under 5 anchored walk-forward folds x 3 seeds, scoring CRPS-skill, pinball, coverage, Diebold-Mariano and Model Confidence Set, plus ARIMA(2,0)/GARCH(1,1) classical baselines.

**Data**
- S&P 500 monthly log-returns, 1871-01 to 2023-12 (1,832 months) - Shiller ie_data free CSV; post-1927 cross-check with Yahoo ^GSPC monthly
- Cross-asset / cross-frequency generalisation panels (equity index and daily-frequency series) - Yahoo Finance daily and monthly closes
- Risk-free rate for any excess-return variant - FRED DGS3MO / Ken French RF

**Must land on**
- Head-mean CRPS-Skill-Score: point head -0.09%, Gaussian head +1.18%, GMM head +3.59% (averaged over 4 backbones x 4 horizons)
- Head gradient point-to-GMM = 3.7 percentage points; point-to-Gaussian ~1.3% CRPS improvement, Gaussian-to-mixture a further ~2.4%
- Backbone spread within the Gaussian head at h=1 = 5.07 pp; within GMM head at h=1 = 3.9 pp
- Model Confidence Set on squared errors excludes none of the 12 variants at the 5% level
- GARCH_gmm is best h=1 model at +12.92% CRPS-SS and best h=3 at +10.33%, then collapses to -50.52% at h=6
- Classical baselines beat TimesNet_point by +6.8% to +17.0% at h in {1,3} and lose by -36.6% to -50.5% at h in {6,12} (the 'h-split')
- Mixture beats point at p<0.05 in all 16 (backbone,horizon) cells; smallest gain +2.64% (iTransformer_gmm h=1), largest +6.48% (N-BEATS_gmm h=1)

## 75. CryptoGAT: Are Time Series Models Effective for Cryptocurrency Forecasting?

`2606.27670` · [arXiv](https://arxiv.org/abs/2606.27670v1) · **L** — a model has to be trained, so results move with the seed · confidence 0.80 · 2026-06-26

Argues that temporal models fail on pure-price crypto prediction and instead proposes CryptoGAT, a lightweight correlation-graph attention network over the cross-section of coins, evaluated on daily OHLCV for 66 major cryptocurrencies (15/04/2023 to 08/01/2026, 999 trading days, 6:2:2 chronological split, 30-day lookback) against LSTM, GRU, ALSTM, PatchTST, iTransformer, StockMixer, TGN, Graphormer, MASTER, with IC/ICIR/Precision@N and a top-K long portfolio.

**Data**
- Daily OHLCV for the 66 largest cryptocurrencies by market cap, 2023-04-15 to 2026-01-08 (999 aligned trading days) - Yahoo Finance <SYM>-USD tickers or Coinbase spot daily candles
- Market-cap screen (> $200M) to rebuild the universe - free CoinGecko/CoinMarketCap snapshot
- Preprocessing as stated: prices normalized to prior close, volume to its 5-day MA, 30-day rolling lookback windows, 6:2:2 chronological split
- NASDAQ benchmark panel used by StockMixer (daily OHLCV, free on Yahoo) for the cross-market ablation

**Must land on**
- CryptoGAT/GAT portfolio: annualized Sharpe 3.128 with no costs, cumulative return 229.12%, max drawdown -36.63%, daily volatility 4.25%, average daily turnover 35.5%
- Cost sensitivity (per side): 0.000% -> SR 3.128 / +779% ann. return; 0.050% -> 2.920 / +673%; 0.075% -> 2.840 / +624%; 0.100% -> 2.759 / +579%; 0.200% -> 2.438 / +424%; 0.300% -> 2.117 / +305%
- Ablation on crypto: GAT IC 0.037 / ICIR 0.138 vs StockMixer IC 0.011 / ICIR 0.113; adding time mixing to GAT collapses IC to 0.006 and ICIR to 0.023
- Same ablation on NASDAQ reverses: StockMixer IC 0.043 / ICIR 0.501, dropping time mixing cuts IC to 0.018; GAT only 0.035 / 0.377
- iTransformer IC and Sharpe stay negative across lookbacks L in {5,10,15,30,60} while GAT improves monotonically with L

## 76. Partial multivariate transformer as a tool for cryptocurrencies time series prediction

`2512.04099` · [arXiv](https://arxiv.org/abs/2512.04099v1) · **L** — a model has to be trained, so results move with the seed · confidence 0.80 · 2025-11-22

Applies the Partial-Multivariate Transformer to next-day log-return forecasting for BTCUSDT and ETHUSDT, training on sampled feature subsets of OHLCV plus six technical indicators, benchmarking against eleven statistical, recurrent and Transformer baselines under Bayesian tuning, and converting forecasts into a sign-based long/short simulation.

**Data**
- daily BTCUSDT OHLC, base and quote volume, and trade count, Oct 5 2017 - May 20 2025, Binance public klines API (Coinbase spot BTC-USD is the in-scope substitute)
- daily ETHUSDT over the same window, same source
- chronological 70/20/10 train/validation/test split with min-max scaling fit on train only

**Must land on**
- Table III BTCUSDT statistical: PMformer MSE 6.5798e-4 (lowest), vs univariate LSTM 6.5832e-4, Informer 6.6062e-4, Naive Repeat 14.308e-4
- Table III BTCUSDT trading: PMformer total ROI 20.62%, Sharpe 3.83, max drawdown -13.8%, directional accuracy 59.8%; FEDformer ROI 38.08% and Sharpe 4.54; Autoformer 24.5% and 4.00
- Table III ETHUSDT statistical: PMformer MSE 9.6063e-4 (lowest), PatchTST 9.6872e-4, Informer 9.7276e-4
- Table III ETHUSDT trading: PMformer ROI -0.67% and Sharpe -0.84, best model Autoformer only +0.59% ROI and 0.68 Sharpe - the paper's headline disconnect between accuracy and profitability

## 77. When Directional Accuracy Lies: A Base-Rate-Honest Benchmark for LoRA-Adapted TimesFM on Equity Forecasting

`2607.12248` · [arXiv](https://arxiv.org/abs/2607.12248v2) · **L** — a model has to be trained, so results move with the seed · confidence 0.80 · 2026-07-14

LoRA fine-tune of the TimesFM foundation model on daily equity prices, benchmarked with expanding walk-forward folds and held-out tickers against always-up, random-walk, persistence and AR(1) baselines.

**Data**
- Yahoo Finance daily split/dividend-adjusted closes for NASDAQ-100 and S&P 500 constituents plus QQQ and the 11 SPDR sector ETFs, 2005-01-01 to 2026-01-01
- sector labels for the per-sector split (derivable from SPDR sector ETF membership)

**Must land on**
- Table 5 excess directional accuracy at h=128: -0.081 for pooled LoRA on NASDAQ-100 (base rate 0.710) and -0.017 on S&P 500 (base rate 0.658)
- Figure 2 always-up base-rate curve versus raw pooled directional accuracy across horizons - reproducible from adjusted closes alone
- Table 7 held-out MAE: pooled LoRA 25.15 vs zero-shot 26.44 vs always-up 24.91 on NASDAQ-100

## 78. Robust Transformer-Based One-Step Stock Index Forecasting via Shifted Data Augmentation

`2606.15701` · [arXiv](https://arxiv.org/abs/2606.15701v1) · **L** — a model has to be trained, so results move with the seed · confidence 0.78 · 2026-06-14

Modifies a Transformer encoder-decoder for one-step-ahead daily index forecasting, adds cosine-annealing-with-warmup scheduling and a Shifted Data Augmentation scheme, and sweeps dropout, heads/dimensions, sequence length and activation on VN30 and S&P 500 daily closes 2009-2025 with an 85/15 chronological split.

**Data**
- Yahoo Finance ^GSPC daily close, 2009-01-01 to 2025-12-31, z-scored on the first 85% of observations
- VN30 index daily close over the same window (Ho Chi Minh Stock Exchange; free coverage uncertain on Yahoo, so this leg may be partially blocked)

**Must land on**
- Table 7 (S&P 500, modified Transformer + cosine annealing + SDA, best row): MAE 122.2 (21.5), RMSE 189.4 (35.6), MAPE 2.00% (0.33) at dropout/SDA parameter 0.9; ReLU variant MAE 181.6, RMSE 272.1, MAPE 2.96%
- Table 6 (VN30, same configuration): MAE 17.45 (2.31), RMSE 24.18 (2.75), MAPE 1.23% (0.16); ReLU variant MAE 30.74, RMSE 48.01, MAPE 2.00%
- Table 3 (S&P 500 baseline Transformer): best MAE 422.5 (41.1), RMSE 600.9 (56.2), MAPE 6.87% (0.65)
- Table 2 (VN30 baseline Transformer): best MAE 42.24 (3.74), RMSE 78.70 (6.33), MAPE 2.55% (0.26)
- Table 5 (S&P 500 modified Transformer, no SDA): MAE 230.1 (35.8), RMSE 315.2 (48.0), MAPE 3.76% (0.58) at 16 heads / d=8
- Table 4 (VN30 modified Transformer, no SDA): MAE 22.13 (1.66), RMSE 39.24 (3.74), MAPE 1.37% (0.09) at 16 heads / d=8
- Ordering claims: cosine annealing beats the generalized inverse-power scheduler on both datasets, and SDA cuts both the error and the across-seed standard deviation over 10 independent runs

## 79. Zero-Copy Semantic Contagion: An In-Memory Streaming Architecture for Evolving Attention Graphs

`2606.05733` · [arXiv](https://arxiv.org/abs/2606.05733v1) · **L** — a model has to be trained, so results move with the seed · confidence 0.75 · 2026-06-04

Streams news text through a zero-copy Rust parser into a multivariate neural Hawkes process with per-node continuous-time LSTM states and a bilinear latent projection, learning a directed cross-company attention graph, then tests whether the top-3 excited tickers per news event show extreme next-day absolute returns.

**Data**
- FNSPID corpus restricted to July 2022 - 638 articles with timestamps, full text and primary ticker tags (public HuggingFace dataset)
- daily OHLCV for the 47 FNSPID tickers across 11 sectors for July 2022 plus a pre-holdout window to estimate return percentile thresholds, Yahoo Finance
- MiniLM-L6-v2 sentence embeddings (384-dim), c-LSTM hidden 64, bilinear latent 16, pruning threshold 0.01, seed 42, first 60% of events as warm-up and last 40% as temporal holdout

**Must land on**
- Table 2 full model precision at the 75/80/85/90/95th percentile thresholds: 0.281, 0.226, 0.165, 0.151, 0.095
- Table 2 random baseline: 0.178, 0.125, 0.109, 0.089, 0.069, giving lift vs random of 1.58x, 1.81x, 1.51x, 1.70x, 1.36x
- Sector heuristic at the 90th percentile is 0.045, so the full model is 3.36x the sector baseline
- Zero-adjacency ablation (w/o Graph) drives precision to exactly 0.000 at every threshold; w/o Bilinear and w/o Pruning stay within 0.003 of the full model
- Portfolio signal: long top-10 / short bottom-10 by instantaneous intensity, rebalanced daily, gives a positive annualised return with a 57.1% daily win rate over 7 holdout trading days
- Predictive lead time: intensity spikes precede realised extreme returns by a mean of 61.5 hours (median 48 hours); mean active out-degree of the learned graph 0.96
- Table 1 FNSPID per-ticker baselines at the 5-day horizon: TimesNet R2 0.892, GRU/LSTM 0.856, Transformer 0.808, RNN 0.650, CNN 0.513

## 80. LLM-Generated Counterfactual Stress Scenarios for Portfolio Risk Simulation via Hybrid Prompt-RAG Pipeline

`2512.07867` · [arXiv](https://arxiv.org/abs/2512.07867v1) · **L** — a model has to be trained, so results move with the seed · confidence 0.72 · 2025-11-26

Prompts GPT-5-mini and Llama-3.1-8B for structured G7 macro stress scenarios (GDP, inflation, policy rate), then maps those shocks through a three-factor PCA model fitted on SPY/IEF/GLD returns into 63-day VaR and CVaR for two ETF portfolios, benchmarked against LLM-free historical-bootstrap, EWMA and GARCH(1,1)-t baselines.

**Data**
- SPY, IEF, GLD daily adjusted closes, 2012-2025, Yahoo Finance (PCA factor estimation window 2015-2025; calm covariance 2012-2019)
- XLE, XLF, XLK, XLY, XLI, XLU, XLV, XLP, XLB, XLRE daily adjusted closes for Portfolio B, Yahoo Finance
- GFC and COVID sub-samples of the same ETF series for the crisis covariance
- IMF World Economic Outlook April 2025 G7 projections for real GDP growth, headline inflation and short-term rate (free download); FRED equivalents serve as substitutes
- 3-month T-bill / risk-free rate for excess returns, FRED

**Must land on**
- Table 1: Portfolio A (60% SPY / 30% IEF / 10% GLD) 63-day VaR0.95 / CVaR0.95 in decimal loss - historical bootstrap 0.0491 / 0.0932, EWMA (lambda=0.94, normal) 0.0725 / 0.0909, GARCH(1,1)-t simulated 0.0856 / 0.1202
- Table 2 deterministic GPT-5-mini macro shocks by country, e.g. United States mean GDP shock -1.42 pp, inflation 3.36 pp, rate 4.64 pp; Germany -1.53 / 3.45 / 3.51; Japan -1.35 / 2.67 / 1.33
- Table 3 unconditional scenario severity: GPT-5-mini mean GDP shock -1.44 vs Llama-3.1-8B-Instruct -1.67
- Table 4 mean VaR/CVaR multiples ~3.74-3.79 (GPT-5-mini) and 3.56-3.70 (Llama) across RAG/news toggles
- Scenario counts surviving plausibility filtering: 627 / 617 / 307 of 840 intended for deterministic GPT-5-mini, non-deterministic GPT-5-mini, Llama-3.1-8B-Instruct

## 81. Learning Predictive Ambiguity Sets for Decision-Focused Distributionally Robust Optimization

`2607.09820` · [arXiv](https://arxiv.org/abs/2607.09820v1) · **L** — a model has to be trained, so results move with the seed · confidence 0.72 · 2026-07-10

A deep contextual network emits a nominal scenario distribution plus a state-dependent Wasserstein radius, defining a contextual ambiguity set for a distributionally robust portfolio choice trained with decision loss.

**Data**
- daily adjusted closes for 20 named S&P 500 constituents (TMUS, PPG, LYB, ALB, GPC, STE, WRB, VRTX, BLK, VEEV, INCY, PAYX, TXT, CSCO, MOS, OXY, HON, MAS, AMGN, IEX), Jan 2018 - Jun 2026, Yahoo Finance

**Must land on**
- Table 2: LPAS-W out-of-sample annualized return 26.28%, Sharpe ratio 1.30, final wealth 1.61 over the 515-observation test window
- Table 2 baseline rows: equal-weight, predict-then-optimize, and historical Wasserstein DRO metrics on the same 20-asset panel
- Figures 1-2: cumulative wealth and drawdown paths of LPAS vs baselines over the 2018-2026 test period

## 82. SciPhy Reinforcement Learning for Portfolio Optimization

`2607.15195` · [arXiv](https://arxiv.org/abs/2607.15195v1) · **L** — a model has to be trained, so results move with the seed · confidence 0.70 · 2026-07-16

Offline physics-informed RL: a pathwise Hamilton-Jacobi equation is fit by a PINN on realized ETF trajectories to learn a Gibbs target-holdings policy under a quadratic price-impact cost model, driven by a synthetic oracle alpha with controlled out-of-sample R-squared.

**Data**
- Yahoo Finance daily OHLCV for 14 ETFs (SPY, IWM, QQQ, DIA, EEM, EFA, FXE, FXI, TLT, HYG, SLV, GLD, USO, VNQ), 2019-01-01 to 2025-12-31
- average daily volume from the same OHLCV (spreads reconstructed via Corwin-Schultz, no vendor feed needed)

**Must land on**
- Table 4 out-of-sample Sharpe of 1.489 for the Gibbs policy vs 1.074 equal-weight and 0.937 behavioral (T=31 days, q=0.2, 120 episodes)
- Table 5 out-of-sample Sharpe of 0.526 for Gibbs vs 0.126 equal-weight and 0.025 behavioral (T=63 days, q=0.2)
- Table 3 out-of-sample Sharpe 1.120 with annualized return 0.090 and turnover 0.5414 (T=31, q=0.1, R2=0.0501)

## 83. Neural Network-Driven Volatility Drag Mitigation under Aggressive Leverage

`2607.23068` · [arXiv](https://arxiv.org/abs/2607.23068v1) · **L** — a model has to be trained, so results move with the seed · confidence 0.70 · 2026-07-25

Compact end-to-end neural network for global minimum-variance weights: a five-parameter hyperbolic weighted moving average replaces the lag-transformation layer, a bidirectional GRU eigencleans the correlation matrix, and a marginal-volatility net rescales, all trained to minimize realized out-of-sample portfolio variance.

**Data**
- daily OHLCV and adjusted closes for US common equities and ADRs on NYSE/NASDAQ, 1990-2024 (Yahoo Finance)
- daily market capitalization for the top-1000 universe screen (price x shares outstanding, shares from SEC EDGAR XBRL)
- risk-free rate for Sharpe ratios (FRED DGS3MO / DTB3)

**Must land on**
- Table 1 Sharpe ratio of 1.12 for the compact neural network at leverage 3.0, vs 0.99 Average Oracle, 0.88 HRP, 0.86 equal-weight
- Table 1 annualized volatility of 0.36 for the NN vs 0.53 HRP and 0.63 equal-weight, and max drawdown -0.77 vs -0.89 HRP, at leverage 3.0
- Table 1 first forced-liquidation leverage threshold of 2.77 for the NN vs 2.73 Average Oracle, 2.66 HRP, 2.61 market-cap weighting

## 84. Belief at Risk: Quantifying Agentic AI Model Risk with LLM-Inferred Bayesian State Filters

`2606.15473` · [arXiv](https://arxiv.org/abs/2606.15473v1) · **L** — a model has to be trained, so results move with the seed · confidence 0.68 · 2026-06-13

Represents an agentic AI system as a POMDP in which an LLM returns a schema-constrained probability vector over four latent regimes (Risk-on, Neutral, Risk-off, Crisis), tempered by eta and passed through a Bayesian filter; posterior entropy, belief drift and rolling 95% CVaR combine into a Belief-at-Risk measure, and beliefs map to portfolio exposures of +1 / +0.5 / -0.5 / -1.

**Data**
- Yahoo Finance daily adjusted close for AAPL, MSFT, GOOGL, AMZN, JPM, SPY, 2021-01-01 to 2025-12-31
- An LLM returning a 4-simplex regime probability vector per day (Risk-on / Neutral / Risk-off / Crisis) with tempering parameter eta; transition prior P diagonally dominant, b0 = (0.25, 0.25, 0.25, 0.25), filter floor 1e-12

**Must land on**
- Table 1 specification: K = 4 regimes, rolling CVaR window W = 60 trading days, alpha = 95%, exposures w(RO)=1, w(N)=0.5, w(RF)=-0.5, w(C)=-1
- Table 2: Neutral posterior mean 0.748, sd 0.271, min 0.0674, max 0.948, occupancy frequency 0.84; Risk-off mean 0.089, sd 0.162, min 0.000431, max 0.688, frequency 0.0781
- Figure 3: Belief-at-Risk peaks at roughly 0.030-0.032 during the March-June 2025 tariff/trade shock, against a baseline of about 0.003-0.005 in late 2024 and again after September 2025
- Figure 3 event alignment: local BaR spikes at the yen carry unwind, US election, tariff/trade policy shock, Israel-Iran escalation, FOMC caution and the US trade window
- Table 3: out-of-sample performance diagnostics for the belief-state portfolio over 2021-2025 (CVaR-based downside consequence of acting on the inferred belief state)

## 85. Integration of LSTM Networks in Random Forest Algorithms for Stock Market Trading Predictions

`2512.02036` · [arXiv](https://arxiv.org/abs/2512.02036v1) · **L** — a model has to be trained, so results move with the seed · confidence 0.60 · 2025-11-20

Trains 482 per-asset LSTM networks on price-derived technical indicators, a Random Forest on bimonthly fundamental variables, and a hybrid that feeds each LSTM's test AUC, weighted probability and train-test AUC gap into the Random Forest, predicting the 10-trading-day direction and then simulating a weekly top-30-by-AUC equal-weight strategy against the S&P 500, Nasdaq Composite and EuroStoxx 50.

**Data**
- daily OHLC for the 482 listed companies from each asset's inception through 2023, Yahoo Finance (list at github.com/JuanCarlosKing/StockmarketAlgoritmicTrading)
- bimonthly fundamental panel for 2023 (collected on the 1st and 15th of each month): EBITDA, P/E, price-to-book, analyst recommendation, 3y beta vs local index, volume/shares %, moving-average distances - from the same GitHub deposit
- ^GSPC, ^IXIC and ^STOXX50E weekly levels for the benchmark comparison, Yahoo Finance

**Must land on**
- Table 3: Fundamental model Train AUC 0.690 / Test AUC 0.563 (95% CI [0.548, 0.578]); Technical models average Train 0.631 / Test 0.527 with significance AUC 0.493 (CI [-0.296, 1.282]); Hybrid Train 0.686 / Test 0.566 (CI [0.550, 0.581])
- Hybrid beats the best fundamental model by exactly 0.003 AUC and the average technical model by 0.071 AUC
- Table 1 Random Forest fundamental best model: test accuracy 54.3%, validation accuracy 56.0%, recall 0.620 test, precision 0.482 test, specificity 0.483 test, F1 0.543
- Figure 5: 'LSTM prediction' ranks 15th in hybrid feature importance with importance 0.025076; Figure 7 (filtering to LSTM test AUC > 0.6): it moves to 1st with importance 0.066
- Figure 8: over weeks 0-3 the top-30 equal-weight system posts a smaller loss than all three indices in week 1 and higher cumulative return than all three by week 3

## 86. Interpretable Deep Learning for Stock Returns: A Consensus-Bottleneck Asset Pricing Model

`2512.16251` · [arXiv](https://arxiv.org/abs/2512.16251v5) · **L** — a model has to be trained, so results move with the seed · confidence 0.60 · 2025-12-18

Builds CB-APM, a deep asset pricing model whose hidden layer is forced through a bottleneck that must reproduce nine analyst-consensus variables, trained with a joint loss weighted by lambda, then evaluates annual out-of-sample return R2, decile and long-short portfolios, and GRS pricing tests.

**Data**
- Open Source Asset Pricing (Chen-Zimmermann) firm-level signal panel: 114 predictors plus the nine analyst-consensus variables (AnalystRevision, ChangeInRecommendation, ChForecastAccrual, EarningsForecastDisparity, FEPS, ForecastDispersion, REV6, AnalystValue, AOP), monthly, Jan 1994-Dec 2023
- FRED-MD monthly database (115 macro predictors), same window, for the macro autoencoder embedding
- Welch-Goyal file from Goyal's website for the 8 macro variables of Gu-Kelly-Xiu (2020) and the T-bill rate used to form risk premia
- Monthly returns and market cap for the roughly 4,683 NYSE/Amex/Nasdaq firms: Yahoo Finance adjusted closes plus SEC Form 25 delisting filings as the free stand-in for CRSP (605,722 firm-month observations in the merged panel)
- Ken French factor returns for the GRS pricing tests against canonical factor models

**Must land on**
- Table 1: out-of-sample annual return R2 peaks at 10.46% at lambda = 0.3 versus the lambda = 0 deep-learning benchmark at 7.63%, a 37% increase; at lambda = 1.0 it is still 9.37%
- Average out-of-sample R2 of 24.21% for approximating the analyst-consensus variables; the consensus-only specification (lambda to infinity) reaches R2 = 30.30%
- Long-short portfolios: mean monthly log return rises from 1.53% at lambda = 0 to 2.20% at lambda = 0.3, with annualized Sharpe going from 1.10 to 1.44
- Table 3: monotonic decile spreads with high-minus-low approaching 2.3% per month for the regularized specification
- Table 5: GRS tests increasingly reject canonical factor models as the consensus bottleneck tightens, i.e. the CB-APM decile portfolios are not spanned by standard factors

## 87. Robust Control under Stationary Ambiguity

`2608.04832` · [arXiv](https://arxiv.org/abs/2608.04832v1) · **L** — a model has to be trained, so results move with the seed · confidence 0.60 · 2026-08-05

Train LSTM deep-hedging policies inside a GBM simulator whose volatility parameter is randomized under a 'refresh latent model' that keeps the filtering ambiguity stationary, then backtest the policy on real daily equity paths.

**Data**
- daily closes for S&P 100 constituents as of Dec 2015 (Yahoo Finance), fit window Jan 2006 - Dec 2015, backtest Jan 2016 - Dec 2025
- point-in-time S&P 100 membership list (not in the stack, but approximable)
- no real option data: payoffs are synthetic functions of the normalized spot path

**Must land on**
- Figure 10 left panel: log spectral-risk ratio vs the BS-HIST delta benchmark for each of the 10 payoffs, RLM improvement running up to roughly 0.5 and beating SLM on 6 of 10 payoffs
- Fitted randomization prior on 128-day realized volatility from 2006-2015 S&P 100 windows: InvGamma MLE alpha-hat = 1.63, beta-hat = 0.07
- Figure 10 right panel: same relative risk on the top 10% of windows ranked by max/min 21-day rolling realized variance, where BS-EWMA overtakes SLM on 5 of 10 payoffs

## 88. Model Validation of Agentic AI Systems: A POMDP-Based Framework for Belief-State, Forecast, and Policy Validation

`2606.17383` · [arXiv](https://arxiv.org/abs/2606.17383v1) · **L** — a model has to be trained, so results move with the seed · confidence 0.55 · 2026-06-16

Casts an agentic AI portfolio manager as a POMDP: an LLM acts as an approximate Bayesian filter inferring five latent market regimes (AI Boom, Soft Landing, Inflation Shock, Recession, Crisis) from market and macro information, feeding belief-conditioned views into a Black-Litterman long-only monthly-rebalanced portfolio, validated by performance, calibration, coverage, ablation and sensitivity tests.

**Data**
- Yahoo Finance daily adjusted close for the ETF sleeve including SPY and TLT (plus the tech-equity sleeve implied by the text), Jan 2024 - Jun 2026 (252-day lookback before a Jan 2025 start)
- FRED macro series used as agent observations (rates, inflation, credit spreads) over the same window
- An LLM to regenerate the five-regime posterior probability vectors; beliefs are shown only as a plot (Figure 1), not tabulated

**Must land on**
- Table 2: Forecasting POMDP CAGR 0.1587, vol 0.1092, Sharpe 1.6811, Sortino 1.3514, max DD -0.0782, Calmar 2.0296, terminal wealth 1.2320
- Table 2: POMDP Utility CAGR 0.1818, vol 0.1234, Sharpe 1.4977, Sortino 1.7901, max DD -0.1011, Calmar 1.7993, terminal wealth 1.2670
- Table 2 benchmarks (exactly reproducible from free prices): Equal Weight and Risk Parity both CAGR 0.2307, vol 0.1754, Sharpe 1.2587, Sortino 2.4743, max DD -0.1180, Calmar 1.9545, terminal wealth 1.3419; 60/40 SPY/TLT CAGR 0.1145, vol 0.1380, Sharpe 0.9494, max DD -0.1065; Max Sharpe CAGR 0.1013, vol 0.1512, Sharpe 0.8698, max DD -0.1389
- Table 1 parameters: 252-day lookback, 21-day holding, monthly rebalance, risk aversion 3.50, max asset weight 0.35, prior shrinkage 0.25, view weight 0.65, long-only fully invested
- Table 6 sensitivity: base Sharpe 1.681; risk aversion 2.0 -> 1.749, 5.0 -> 1.643; view weight 0.40 -> 1.582, 0.80 -> 1.743; prior shrinkage 0.10 -> 1.692, 0.50 -> 1.663
- Table 4 belief calibration (mean posterior vs realized): AI Boom 0.074 vs 0.278; Soft Landing 0.075 vs 0.222; Inflation Shock 0.165 vs 0.167; Recession 0.136 vs 0.000; Crisis 0.550 vs 0.333
- Figure 1: Crisis-state posterior peaks near 0.95 around May 2025 (tariff uncertainty) and falls to ~0.20-0.45 by mid-2026

## 89. A Hybrid Architecture for Options Wheel Strategy Decisions: LLM-Generated Bayesian Networks for Transparent Trading

`2512.01123` · [arXiv](https://arxiv.org/abs/2512.01123v1) · **L** — a model has to be trained, so results move with the seed · confidence 0.55 · 2025-11-30

An LLM builds a context-specific Bayesian network per trade decision for an options 'wheel' strategy (sell puts 10% OTM, hold assignment, sell calls), populating CPTs from an 8,919-trade historical archive; backtested 2007-2025 on leveraged ETFs and mega-cap tech.

**Data**
- Yahoo Finance daily adjusted OHLC for TQQQ, SOXL, UPRO, TECL, FAS, NVDA, GOOGL, AMZN, TSLA, Jan 2007 - Sep 2025
- Yahoo Finance daily adjusted close for QQQ, QYLD, PUTW, Jan 2020 - Sep 2025 (benchmark leg)
- Option premiums reconstructed via Black-Scholes on realized vol from the same Yahoo price history (no free historical chain exists); commissions $0.65/contract + $0.10 exchange fee, min $1.00; slippage 0.15% puts / 0.12% calls

**Must land on**
- Table 4: average annual return 15.3% gross / 15.0% net of costs; final portfolio value $1,447,985 from $100,000 initial; total premium collected $1,915,748; 8,919 trades (475.7/yr); average premium/trade $214.79; average premium rate 11.15%; average monthly return 1.19%; 19/19 winning years
- Table 4: 1,563 puts sold, 1,553 (99.4%) expired worthless, 5,803 rolled, 0 assigned
- Table 7 / QQQ baseline: our Sharpe 1.08 vs QQQ 0.62; Sortino 1.45 vs 0.78; max drawdown -8.2% vs -60.0%; QQQ annual return 17.53%; certainty-equivalent return 12.8-14.1% vs QQQ 8.2-11.3%
- Table 8 (2020-2025): QYLD 6.61% return, Sharpe 0.45, Sortino 0.46, max DD -24.75%; PUTW 9.03%, Sharpe 0.65, Sortino 0.66, max DD -28.40%
- Table 5 crisis years: 2008 +18.6% (SPX -36.2%, QQQ -40.8%); 2018 +24.1%; 2022 +27.4% (SPX -18.2%, QQQ -32.6%)
- Table 12 ablation: LLM-generated 15.3% return / Sharpe 1.08 / -8.2% DD vs random structure 9.2% / 0.67 / -18.7% vs fixed template 11.5% / 0.82 / -14.2%
- Table 10: our method vs QQQ return difference -0.19%, t = -1.45, p = 0.147

## 90. End-to-End Parametric Portfolio Policies for Cross-Asset Futures Timing: When Do AI Models Beat Simple Rules?

`2607.00475` · [arXiv](https://arxiv.org/abs/2607.00475v1) · **L** — a model has to be trained, so results move with the seed · confidence 0.50 · 2026-07-01

Trains end-to-end LSTM and transformer allocation policies that map the cross-section of daily returns directly to long/short weights on sixteen liquid CME futures using a differentiable Sharpe loss, benchmarked walk-forward against equal weighting, risk parity and time-series momentum with transaction-cost sensitivity and alpha/beta decomposition.

**Data**
- Daily continuous-contract closes 2001-2024 for the sixteen CME futures on Yahoo Finance: ES=F, NQ=F, RTY=F (equity index); ZT=F, ZF=F, ZN=F, ZB=F (rates); 6E=F, 6J=F (FX); CL=F, NG=F (energy); GC=F, HG=F, SI=F (metals); ZC=F, ZW=F (agriculturals)
- Volume/open-interest based roll to splice contract months, using trailing data only
- Transaction-cost grid of 0, 1, 2, 5 and 10 bp per unit turnover

**Must land on**
- Table III net Sharpe of the cross-asset portfolio across 0/1/2/5/10 bp cost: 1/N 0.52 / 0.52 / 0.52 / 0.52 / 0.52; risk parity 0.15 / 0.14 / 0.14 / 0.13 / 0.11; TSMOM 0.37 / 0.36 / 0.35 / 0.33 / 0.29; LSTM 0.50 / 0.42 / 0.33 / 0.06 / -0.38; transformer 0.55 / 0.54 / 0.54 / 0.52 / 0.50
- Table II pooled cross-asset out-of-sample gross Sharpe: 1/N 0.52, risk parity 0.15, TSMOM 0.37, LSTM 0.50, transformer 0.55 (transformer mean return 0.05, vol 0.08)
- Table II equity sub-universe: 1/N Sharpe 0.78 (significant), risk parity 0.79 (significant), TSMOM 0.45
- Fig. 1 sample-period structure 2001-2024: mean pairwise daily-return correlation 0.67 within an asset class and 0.05 across classes
- Table IV per-universe alpha/beta: rates alpha +0.1 with t-stat significant, beta -0.3, benchmark Sharpe 0.52

