# Political Risk and the Global Equity Mix

How should a multi-asset fund account for political risk across its country exposures? This project builds a monthly political risk index for 10 equity markets (2008–2026) and tests what it means for returns, volatility, event risk and country allocation. Results are refreshed monthly by GitHub Actions; the latest briefing is in [`results/briefing.md`](results/briefing.md), and the full write-up is in [`report/Political_Risk_Report.pdf`](report/Political_Risk_Report.pdf).

## Main findings

Data: 10 markets, May 2008 to July 2026, 2,124 country-month observations, 30 political events.

1. **Political risk is a volatility story, not a return story.** A one-standard-deviation political-risk surprise raises a country's realised volatility by about **2% in the same month** (p = 0.003), relative to other markets that month. Including moves shared across markets, the panel VAR shows volatility rising about **6% on impact**, then decaying to under 1% within four months (still statistically above normal for most of the year).
2. **No lasting return penalty.** The same shock comes with a −0.26 pp excess return versus ACWI in the month (p = 0.05), which reverses within a quarter. Markets reprice political risk quickly rather than drifting lower.
3. **What kind of event matters more than whether there is one.** Unscheduled **governance shocks**, such as finance-minister dismissals and leadership scandals, cost **−4.8% over three days** on average (n = 8, p = 0.02). **Scheduled elections** show no significant effect (+0.8%, n = 14, p = 0.46), because markets price and hedge them in advance.
4. **A simple underweighting rule adds little.** Halving exposure to the three markets with the fastest-rising political risk improved return/volatility only from 0.28 to 0.30 (information ratio 0.16), before costs.

**Implication:** political risk belongs in the **risk budget** (position sizing, risk limits, hedging around unscheduled instability) rather than in return forecasts.

![Local projections](results/fig2_local_projections.png)
![Event study](results/fig4_event_study.png)

## Data

| Input | Source | Frequency |
|---|---|---|
| Economic Policy Uncertainty (EPU) by country | Baker, Bloom and Davis (2016), [policyuncertainty.com](https://www.policyuncertainty.com) | Monthly |
| Country Geopolitical Risk (GPR) | Caldara and Iacoviello (2022), [matteoiacoviello.com/gpr.htm](https://www.matteoiacoviello.com/gpr.htm) | Monthly |
| Country equity returns, in USD | iShares country ETFs (IVV, EWG, EWJ, EWU, EWQ, EWC, EWA, INDA, EWZ, EZA) via `yfinance` | Daily |
| Global benchmark | iShares MSCI ACWI | Daily |

Countries: United States, Germany, Japan, United Kingdom, France, Canada, Australia, India, Brazil and South Africa. USD returns put the markets on a common basis and reflect what a foreign investor earns, currency included. The sample starts in April 2008 (ACWI launch); India starts in 2012 (INDA launch). South Africa has no EPU series, so its index uses GPR alone.

## Method

**Political Risk Index (PRI).** Log EPU and log GPR are standardised within each country and combined using first-principal-component weights. With two standardised inputs this is an equal-weighted average. Two versions are kept:
- `pri`: full-sample standardisation, used in the econometrics.
- `pri_rt`: expanding-window standardisation, which uses only data available at the time, so the backtest has no look-ahead.

The **political-risk shock** is the standardised AR(1) innovation in each country's PRI: the part of this month's political risk that was not predictable from last month.

**Panel local projections** (Jordà, 2005). For horizons of 0–12 months, the cumulative excess return over ACWI and log realised volatility are regressed on the shock, controlling for two lags of each. Country and month fixed effects isolate each country's own political risk from global shocks. Driscoll-Kraay standard errors allow for cross-country and serial correlation.

**Fixed-effects panel VAR** of [shock, excess return, log volatility]. Lags are built within each country, lag length is chosen by BIC, and the model is identified with a Cholesky ordering (political risk first). Bands come from a 500-draw country-cluster bootstrap.

**Event study.** The normal return for each event comes from a market model on ACWI fitted over trading days [−250, −30]. Cumulative abnormal returns are reported for [−1,+1], [0,+5] and [0,+10]. Tests are run per event and across events with the Boehmer-Musumeci-Poulsen standardised test, by event type (election, policy shock, governance, geopolitical, unrest).

**Portfolio applications:**
- *Regimes:* next-month outcomes by within-month PRI tercile.
- *Tilt backtest:* equal-weight country portfolio vs. halving the three fastest-rising PRI markets, using signals known at the start of each month.
- *Stress tests:* returns during Brexit, the 2016 U.S. election, the Russian invasion of Ukraine, the UK mini-budget and the 2025 U.S.–Canada tariff shock.

## Outputs (`results/`)

| File | Content |
|---|---|
| `briefing.md` | Investment briefing: findings, total-fund implications, current country read, stress tests |
| `fig1_political_risk_index.png` | PRI over time |
| `fig2_local_projections.png` | Return and volatility responses to a political-risk shock |
| `fig3_panel_var_irf.png` | Panel VAR impulse responses |
| `fig4_event_study.png` | Abnormal returns by event and on average |
| `fig5_regimes.png` | Outcomes by political-risk tercile |
| `fig6_backtest.png` | Tilt vs. equal weight: growth and drawdowns |
| `fig7_stress_tests.png` | Market returns in political-stress windows |
| `*.csv` | All underlying tables |

## How to run

```bash
pip install -r requirements.txt
python run_analysis.py              # downloads data (cached in data/), writes results/
python run_analysis.py --refresh    # re-download prices
python run_analysis.py --synthetic  # offline demo on simulated data
pytest                              # tests
```

The **Analysis** workflow runs the tests on every push and pull request. Each month, and on demand, it reruns the analysis on the latest data and commits the updated `results/`.

## Tests

The tests run on simulated data with a known effect built in: a political-risk shock lowers next-month returns by 2%, and events carry a −2% abnormal return. They check that:
- the models recover the built-in effects, and the event study finds nothing when no effect is present;
- the real-time index and portfolio weights never use future data;
- portfolio weights always sum to one.

## Limitations

- Ten markets and 18 years limit statistical power, and some event types have only 2–3 events.
- The panel VAR depends on its ordering assumption; the local projections do not.
- EPU and GPR are text-based measures and pick up media attention as well as underlying risk.
- Excess returns are in USD and include currency effects.
- The backtest excludes transaction costs; turnover is reported so their effect can be judged.

## Project structure

```
political_risk/
  config.py        countries, tickers, data sources, events, stress windows
  data.py          downloads with caching, plus a synthetic data generator
  index.py         Political Risk Index and shocks
  econometrics.py  monthly panel, local projections, panel VAR
  events.py        market-model event study with BMP tests
  allocation.py    regimes, tilt backtest, stress tests
  report.py        charts and briefing
run_analysis.py    end-to-end pipeline
results/           latest charts, tables and briefing
report/            written report (LaTeX source and PDF)
tests/             tests on synthetic data
```

## Background

This project extends my earlier [Political Risk and Financial Markets](https://github.com/divvygupta/The-Impact-of-Political-Risk-on-Financial-Markets-A-Panel-VAR-and-Event-Study-Analysis) study. That study used annual governance indicators for 2005–2020 and found no significant long-run effect on volatility or FDI, plus event reactions of 3–5% that were not significant at 5%. This project tests whether that null result came from the data rather than the economics:
- monthly data instead of annual, with about 11 times as many observations;
- inputs that capture political-risk news rather than slow-moving governance scores;
- an event model that removes global market moves;
- a direct link to portfolio decisions.

**Tools:** Python, pandas, NumPy, SciPy, scikit-learn, linearmodels, Matplotlib, yfinance, pytest, GitHub Actions
