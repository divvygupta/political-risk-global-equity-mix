"""Run the full political-risk analysis and write charts, tables and a briefing to ./results.

    python run_analysis.py              # real data, written to ./results (cached downloads in ./data)
    python run_analysis.py --synthetic  # offline demo on simulated data with a known effect
"""

from __future__ import annotations

import argparse
import os

from political_risk import allocation, config, data, econometrics, events, index, report


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--synthetic", action="store_true", help="use simulated data (no internet needed)")
    ap.add_argument("--refresh", action="store_true", help="re-download market data")
    ap.add_argument("--out", default="results")
    ap.add_argument("--boot", type=int, default=500, help="panel VAR bootstrap draws")
    a = ap.parse_args(argv)
    os.makedirs(a.out, exist_ok=True)

    if a.synthetic:
        prices, epu, gpr = data.synthetic_dataset()
    else:
        prices, epu, gpr = data.load_prices(refresh=a.refresh), data.load_epu(), data.load_gpr()

    pri, pca = index.build_pri(epu, gpr)
    pri = pri[pri.index.get_level_values("date") >= config.START]
    panel = econometrics.monthly_panel(prices, pri)

    print("Local projections ...")
    lp = econometrics.local_projections(panel)
    print("Panel VAR ...")
    var = econometrics.panel_var(panel, n_boot=a.boot)
    print("Event study ...")
    per_event, ev_summary, paths = events.event_study(prices)
    print("Regimes, backtest, stress tests ...")
    regimes = allocation.regime_analysis(panel)
    metrics, rets, weights = allocation.backtest(panel)
    stress = allocation.stress_test(prices, config.STRESS_WINDOWS)

    figs = [report.plot_pri(pri, a.out), report.plot_lp(lp, a.out), report.plot_var(var, a.out),
            report.plot_events(per_event, paths, a.out), report.plot_regimes(regimes, a.out),
            report.plot_backtest(rets, a.out), report.plot_stress(stress, a.out)]

    tables = {"local_projections.csv": lp, "event_study_by_event.csv": per_event,
              "event_study_summary.csv": ev_summary, "regimes.csv": regimes,
              "backtest_metrics.csv": metrics, "stress_tests.csv": stress}
    for name, t in tables.items():
        t.to_csv(os.path.join(a.out, name))

    dates = panel.index.get_level_values("date")
    latest = pri["pri_rt"].unstack("country").ffill().iloc[-1]
    res = {"lp": lp, "var": var, "regimes": regimes, "metrics": metrics, "event_summary": ev_summary, "per_event": per_event,
           "stress": stress, "weights": weights, "pca": pca, "pri_latest": latest,
           "n_countries": panel.index.get_level_values("country").nunique(),
           "start": dates.min().strftime("%b %Y"), "end": dates.max().strftime("%b %Y")}
    brief = report.briefing(res, a.out, synthetic=a.synthetic)
    print(f"\nWrote {len(figs)} charts, {len(tables)} tables and {brief}")
    print(metrics.round(3).to_string())


if __name__ == "__main__":
    main()
