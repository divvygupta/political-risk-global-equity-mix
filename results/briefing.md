# Investment Briefing: Political Risk and the Global Equity Mix

Coverage: 10 equity markets, May 2008 to Jul 2026, monthly, 2,124 country-month observations. The Political Risk Index (PRI) averages standardised Economic Policy Uncertainty and Geopolitical Risk (first-principal-component weights 0.50 / 0.50).

## Key findings

1. **Political risk shows up in volatility, not in returns.** A one-standard-deviation political-risk surprise raises a country's realised volatility by +2.0% in the same month (p = 0.003) and +1.3% the next (p = 0.10), relative to other markets that month. In the panel VAR, which also captures moves shared across markets, volatility rises +5.6% on impact and is significantly above normal in 11 of the following 12 months.
2. **No lasting return penalty.** The same shock comes with a -0.26 pp excess return versus ACWI in the month (p = 0.05) and a cumulative +0.21 pp after four months (p = 0.43, not statistically significant). Markets reprice risk quickly; they do not keep falling.
3. **No regime effect.** Markets in the top third of political risk returned 0.5% a year versus the bottom third the following month (p = 0.83).
4. **Event type matters.** Across 30 events the mean 3-day abnormal return was -1.4% (BMP p = 0.16), but this hides a split:
   - Governance (n = 8): -4.8% (BMP p = 0.02)
   - Policy shock (n = 3): -3.1% (BMP p = 0.05)
   - Geopolitical (n = 2): -1.4% (BMP p = 0.33)
   - Unrest (n = 3): -1.1% (BMP p = 0.57)
   - Election (n = 14): 0.8% (BMP p = 0.46)
   Largest 3-day moves: BRA Temer recording scandal -14.0%; ZAF Finance minister Nene dismissed -11.7%; GBR Brexit referendum result -7.9%.
5. **A simple tilt adds little.** Halving the weight of the three markets with the sharpest rise in real-time political risk gave a return/volatility ratio of 0.30 vs 0.28 for equal weight, max drawdown of -46.0% vs -48.2%, and an information ratio of 0.16 at 1.3% tracking error, before transaction costs (12.6% average monthly turnover).

## Implications for the total fund

- Treat political risk as a **risk-budget input**, not a return signal: it predicts higher volatility in the same month and, more weakly, the next, which matters for position sizing, risk limits and option hedging, while it does not predict lower returns.
- **Unscheduled governance** events carry statistically significant short-run losses; scheduled elections do not, because markets can price and hedge them in advance. Monitoring for leadership and cabinet instability is more valuable than election calendars.
- Stress-test returns are in USD and so include currency moves. For a Canadian-dollar fund, the FX hedging decision is part of the political-risk exposure, not separate from it.

## Current read (latest month)

| Country | PRI (real time) | Tilt-model weight |
|---|---|---|
| CAN | +1.56 | 5.0% |
| USA | +1.49 | 12.1% |
| DEU | +1.43 | 12.1% |
| IND | +1.26 | 12.1% |
| GBR | +0.98 | 12.1% |
| AUS | +0.97 | 12.1% |
| FRA | +0.90 | 12.1% |
| BRA | +0.78 | 5.0% |
| JPN | +0.45 | 12.1% |
| ZAF | -2.23 | 5.0% |

## Stress tests (cumulative USD return)

|                                     |   USA |   DEU |   JPN |   GBR |   FRA |   CAN |   AUS |   IND |   BRA |   ZAF |   BENCH |   Equal-weight portfolio |
|:------------------------------------|------:|------:|------:|------:|------:|------:|------:|------:|------:|------:|--------:|-------------------------:|
| Brexit referendum (Jun 2016)        |  -4.1 |  -9.1 |  -2.5 | -13.2 | -10.2 |  -4.2 |  -5.7 |  -2.9 |  -2.1 | -10.4 |    -5.4 |                     -6.4 |
| Trump election (Nov 2016)           |   1.8 |   0   |  -0.9 |   1.6 |   0   |   0.2 |   0   |  -3.5 | -10.2 |  -8.1 |     0.6 |                     -1.9 |
| UK mini-budget (Sep 2022)           |  -1.8 |  -3.7 |  -1.8 |  -5.6 |  -3.8 |  -3.7 |  -2.8 |  -3.7 |  -6.2 |  -2.1 |    -2.3 |                     -3.5 |
| Invasion of Ukraine (Feb-Mar 2022)  |  -3.1 | -15.6 |  -7.8 |  -8.6 | -13.7 |   0.4 |  -0.9 |  -7.7 |  -0.6 |  -1.5 |    -5.4 |                     -5.9 |
| U.S.-Canada tariff shock (Feb 2025) |  -0.5 |  -1.5 |  -1.2 |  -0.7 |  -0.8 |  -1.1 |  -0.7 |   0.9 |   0.3 |   0   |    -0.5 |                     -0.5 |

## Method notes and limitations

- PRI uses within-country z-scores; `pri_rt` uses expanding windows so the backtest has no look-ahead.
- Local projections include two lags of the outcome and the shock; Driscoll-Kraay errors allow for cross-country and serial correlation.
- Panel VAR is identified with political risk ordered first; results may depend on this ordering.
- Ten markets and roughly two decades of data limit statistical power. Treat estimates as indicative.
- Event dates are the first U.S. trading day on which the news could be priced, taken from public reporting.
