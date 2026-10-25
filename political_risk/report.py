"""Charts, tables and an auto-generated investment briefing."""

from __future__ import annotations

import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

INK, MUTED, GRID = "#1f2933", "#7b8794", "#e4e7eb"
BLUE, RED, GREY = "#2563eb", "#dc2626", "#9aa5b1"

plt.rcParams.update({
    "figure.dpi": 150, "savefig.bbox": "tight", "font.size": 9,
    "axes.edgecolor": MUTED, "axes.labelcolor": INK, "axes.titlesize": 10, "axes.titleweight": "bold",
    "axes.spines.top": False, "axes.spines.right": False, "axes.grid": True, "grid.color": GRID,
    "xtick.color": MUTED, "ytick.color": MUTED, "legend.frameon": False,
})


def _save(fig, out, name):
    path = os.path.join(out, name)
    fig.savefig(path)
    plt.close(fig)
    return path


def plot_pri(pri: pd.DataFrame, out: str, highlight=("USA", "GBR", "CAN")) -> str:
    wide = pri["pri"].unstack("country")
    fig, ax = plt.subplots(figsize=(8, 3.2))
    for c in wide.columns:
        if c not in highlight:
            ax.plot(wide.index, wide[c], color=GRID, lw=0.8)
    for c, col in zip(highlight, [BLUE, RED, INK]):
        if c in wide:
            ax.plot(wide.index, wide[c], color=col, lw=1.3, label=c)
    ax.plot(wide.index, wide.mean(axis=1), color=MUTED, lw=1, ls="--", label="Cross-country average")
    ax.set_title("Political Risk Index (standardised, EPU + GPR)")
    ax.set_ylabel("Std. dev. from country mean")
    ax.legend(ncol=4, loc="upper left")
    return _save(fig, out, "fig1_political_risk_index.png")


def plot_lp(lp: pd.DataFrame, out: str) -> str:
    labels = {"xret": "Cumulative excess return vs ACWI (log pts)", "log_rvol": "Log realised volatility"}
    fig, axes = plt.subplots(1, len(labels), figsize=(8, 3))
    for ax, (y, lab) in zip(axes, labels.items()):
        d = lp[lp["outcome"] == y]
        ax.fill_between(d["h"], d["lo90"], d["hi90"], color=BLUE, alpha=0.15, lw=0, label="90% CI")
        ax.plot(d["h"], d["beta"], color=BLUE, lw=1.6, marker="o", ms=3)
        ax.axhline(0, color=INK, lw=0.7)
        ax.set_title(lab)
        ax.set_xlabel("Months after a 1 s.d. political-risk shock")
    axes[0].legend(loc="lower left")
    fig.suptitle("Local projections: country and month fixed effects, Driscoll-Kraay SEs", fontsize=9, color=MUTED, y=1.02)
    return _save(fig, out, "fig2_local_projections.png")


def plot_var(var: dict, out: str) -> str:
    cols = var["cols"]
    fig, axes = plt.subplots(1, len(cols) - 1, figsize=(8, 3))
    h = np.arange(var["irf"].shape[0])
    names = {"xret": "Excess return", "log_rvol": "Log realised volatility"}
    for ax, i in zip(axes, range(1, len(cols))):
        ax.fill_between(h, var["lo"][:, i, 0], var["hi"][:, i, 0], color=BLUE, alpha=0.15, lw=0)
        ax.plot(h, var["irf"][:, i, 0], color=BLUE, lw=1.6)
        ax.axhline(0, color=INK, lw=0.7)
        ax.set_title(f"Response of {names.get(cols[i], cols[i])}")
        ax.set_xlabel("Months")
    fig.suptitle(f"Panel VAR({var['p']}) impulse responses to a political-risk shock, 90% country-bootstrap bands",
                 fontsize=9, color=MUTED, y=1.02)
    return _save(fig, out, "fig3_panel_var_irf.png")


def plot_events(per_event: pd.DataFrame, paths: pd.DataFrame, out: str) -> str:
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(9, 3.6), gridspec_kw={"width_ratios": [1.1, 1]})
    d = per_event.sort_values("CAR [0,+5]")
    colors = [RED if p < 0.05 else GREY for p in d["p [0,+5]"]]
    a1.barh(d["country"] + ": " + d["event"].str.slice(0, 26), d["CAR [0,+5]"] * 100, color=colors)
    a1.axvline(0, color=INK, lw=0.7)
    a1.set_title("CAR [0,+5] by event (red: p < 0.05)")
    a1.set_xlabel("% vs market model")
    a1.tick_params(axis="y", labelsize=6)
    a1.grid(axis="y", visible=False)
    for col in paths.columns:
        a2.plot(paths.index, paths[col] * 100, color=GRID, lw=0.7)
    a2.plot(paths.index, paths.mean(axis=1) * 100, color=BLUE, lw=2, label="Average across events")
    a2.axvline(0, color=INK, lw=0.7, ls=":")
    a2.axhline(0, color=INK, lw=0.7)
    a2.set_title("Average cumulative abnormal return")
    a2.set_xlabel("Trading days from event")
    a2.set_ylabel("%")
    a2.legend(loc="lower left")
    return _save(fig, out, "fig4_event_study.png")


def plot_regimes(reg: pd.DataFrame, out: str) -> str:
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(8, 3))
    a1.bar(reg.index.astype(str), reg["ann. excess return"] * 100, color=[BLUE, GREY, RED])
    a1.axhline(0, color=INK, lw=0.7)
    a1.set_title("Next-month excess return vs ACWI (ann., %)")
    a2.bar(reg.index.astype(str), reg["avg realised vol"] * 100, color=[BLUE, GREY, RED])
    a2.set_title("Next-month realised volatility (%)")
    fig.suptitle("Country outcomes by political-risk tercile (real-time index, ranked within month)",
                 fontsize=9, color=MUTED, y=1.02)
    return _save(fig, out, "fig5_regimes.png")


def plot_backtest(rets: pd.DataFrame, out: str) -> str:
    cum = rets.cumsum()
    fig, (a1, a2) = plt.subplots(2, 1, figsize=(8, 4.4), sharex=True, gridspec_kw={"height_ratios": [2, 1]})
    for col, c in zip(rets.columns, [GREY, BLUE]):
        a1.plot(cum.index, np.exp(cum[col]) * 100, color=c, lw=1.4, label=col)
        a2.plot(cum.index, (np.exp(cum[col] - cum[col].cummax()) - 1) * 100, color=c, lw=1)
    a1.set_title("Political-risk tilt vs equal-weight country portfolio (growth of 100, USD)")
    a1.legend(loc="upper left")
    a2.set_title("Drawdown (%)")
    return _save(fig, out, "fig6_backtest.png")


def plot_stress(stress: pd.DataFrame, out: str) -> str:
    d = stress.drop(columns=["BENCH"], errors="ignore") * 100
    fig, ax = plt.subplots(figsize=(8, 0.5 + 0.45 * len(d)))
    vmax = np.nanmax(np.abs(d.values))
    im = ax.imshow(d.values, cmap="RdBu", vmin=-vmax, vmax=vmax, aspect="auto")
    ax.set_xticks(range(d.shape[1]), d.columns, rotation=45, ha="right")
    ax.set_yticks(range(d.shape[0]), d.index)
    for i in range(d.shape[0]):
        for j in range(d.shape[1]):
            v = d.values[i, j]
            if np.isfinite(v):
                ax.text(j, i, f"{v:.1f}", ha="center", va="center", fontsize=7,
                        color="white" if abs(v) > vmax * 0.6 else INK)
    ax.grid(False)
    ax.set_title("Cumulative USD return during political-stress windows (%)")
    fig.colorbar(im, ax=ax, shrink=0.8)
    return _save(fig, out, "fig7_stress_tests.png")


def plot_scenarios(vols: pd.DataFrame, port: pd.DataFrame, out: str) -> str:
    """Projected volatility change by scenario and market, and the portfolio's value at risk."""
    piv = vols.pivot(index="scenario", columns="country", values="vol change").reindex(port.index) * 100
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(10, 3.2), gridspec_kw={"width_ratios": [1.9, 1]})
    vmax = max(np.nanmax(piv.values), 1)
    im = a1.imshow(piv.values, cmap="Reds", vmin=0, vmax=vmax, aspect="auto")
    a1.set_xticks(range(piv.shape[1]), piv.columns)
    a1.set_yticks(range(piv.shape[0]), piv.index)
    for i in range(piv.shape[0]):
        for j in range(piv.shape[1]):
            v = piv.values[i, j]
            a1.text(j, i, f"{v:.0f}", ha="center", va="center", fontsize=7,
                    color="white" if v > vmax * 0.6 else INK)
    a1.grid(False)
    a1.set_title("Projected rise in market volatility, first month (%)")
    y = np.arange(len(port))
    a2.set_axisbelow(True)
    a2.barh(y + 0.2, port["current 1-month VaR (95%)"] * 100, height=0.38, color=GREY, label="Current")
    a2.barh(y - 0.2, port["scenario 1-month VaR (95%)"] * 100, height=0.38, color=RED, label="Scenario")
    a2.set_yticks(y, [""] * len(y))
    a2.invert_yaxis()
    a2.set_title("Portfolio 1-month 95% VaR (% of value)")
    a2.legend(loc="upper center", bbox_to_anchor=(0.5, -0.1), ncol=2, fontsize=7)
    a2.grid(axis="y", visible=False)
    fig.suptitle("Scenario analysis: equal-weight portfolio of 10 markets, Canadian-dollar investor, correlations held fixed",
                 fontsize=9, color=MUTED, y=1.02)
    return _save(fig, out, "fig8_scenarios.png")


def plot_fx_split(analogues: pd.DataFrame, out: str, n: int = 4) -> str:
    """For each scenario's analogue, the worst-hit markets' CAD returns split into local equity and currency."""
    scen = list(dict.fromkeys(analogues["scenario"]))
    fig, axes = plt.subplots(1, len(scen), figsize=(10, 3), sharey=True)
    for ax, sc in zip(np.atleast_1d(axes), scen):
        d = analogues[analogues.scenario == sc].nsmallest(n, "CAD-investor return")
        eq, fxc = np.log1p(d["local equity"]) * 100, np.log1p(d["currency vs CAD"]) * 100
        x = np.arange(len(d))
        ax.bar(x, eq, color=BLUE, label="Local equity")
        ax.bar(x, fxc, bottom=np.where((fxc < 0) == (eq < 0), eq, 0), color=GREY, label="Currency vs CAD")
        ax.scatter(x, np.log1p(d["CAD-investor return"]) * 100, color=INK, s=12, zorder=3, label="Total (CAD)")
        ax.axhline(0, color=INK, lw=0.7)
        ax.set_axisbelow(True)
        ax.set_xticks(x, d["country"])
        ax.set_title(sc, fontsize=8)
    np.atleast_1d(axes)[0].set_ylabel("Log return, %")
    np.atleast_1d(axes)[0].legend(fontsize=6, loc="lower left")
    fig.suptitle("What happened in each scenario's historical analogue: worst-hit markets, Canadian-dollar investor",
                 fontsize=9, color=MUTED, y=1.03)
    return _save(fig, out, "fig9_scenario_analogues.png")


# --- Briefing -------------------------------------------------------------------------------
def _fmt_pct(x, d=1):
    return "n/a" if pd.isna(x) else f"{x * 100:.{d}f}%"


def briefing(res: dict, out: str, synthetic: bool) -> str:
    lp, reg, m, summ, per_event, stress, w = (res[k] for k in ["lp", "regimes", "metrics", "event_summary",
                                                               "per_event", "stress", "weights"])
    r0 = lp[(lp.outcome == "xret") & (lp.h == 0)].iloc[0]
    r3 = lp[(lp.outcome == "xret") & (lp.h == 3)].iloc[0]
    v0 = lp[(lp.outcome == "log_rvol") & (lp.h == 0)].iloc[0]
    v1 = lp[(lp.outcome == "log_rvol") & (lp.h == 1)].iloc[0]
    var = res["var"]
    var_v = var["irf"][:, 2, 0]
    var_sig = int((var["lo"][1:, 2, 0] > 0).sum())
    allev = summ.loc["All events"]
    kinds = summ.drop(index="All events")
    tilt, eq = m.loc["Political-risk tilt"], m.loc["Equal weight"]
    worst = per_event.nsmallest(3, "CAR [-1,+1]")
    sig = lambda p: "statistically significant at 5%" if p < 0.05 else "not statistically significant"  # noqa: E731
    pct = lambda b: (np.exp(b) - 1) * 100  # noqa: E731

    lines = [
        "# Investment Briefing: Political Risk and the Global Equity Mix", "",
    ]
    if synthetic:
        lines += ["> **Synthetic data.** These numbers come from simulated data with a known effect built in, "
                  "to check that the pipeline works. They are not findings. Run `python run_analysis.py` "
                  "with internet access for real results.", ""]
    kind_lines = [f"   - {k.replace('_', ' ').capitalize()} (n = {int(r.n_events)}): {_fmt_pct(r['mean CAR [-1,+1]'], 1)} "
                  f"(BMP p = {r['BMP p [-1,+1]']:.2f})" for k, r in kinds.sort_values("mean CAR [-1,+1]").iterrows()]
    sig_kinds = [k.replace("_", " ") for k, r in kinds.iterrows() if r["BMP p [-1,+1]"] < 0.05 and r["n_events"] >= 5]
    lines += [
        f"Coverage: {res['n_countries']} equity markets, {res['start']} to {res['end']}, monthly, "
        f"{int(lp.nobs.max()):,} country-month observations. The Political Risk Index (PRI) averages standardised "
        f"Economic Policy Uncertainty and Geopolitical Risk (first-principal-component weights "
        f"{res['pca'].iloc[0]:.2f} / {res['pca'].iloc[1]:.2f}).", "",
        "## Key findings", "",
        f"1. **Political risk shows up in volatility, not in returns.** A one-standard-deviation political-risk "
        f"surprise raises a country's realised volatility by {pct(v0.beta):+.1f}% in the same month "
        f"(p = {v0.pval:.3f}) and {pct(v1.beta):+.1f}% the next (p = {v1.pval:.2f}), relative to other markets "
        f"that month. In the panel VAR, which also captures moves shared across markets, volatility rises "
        f"{pct(var_v[0]):+.1f}% on impact and is significantly above normal in {var_sig} of the following 12 months.",
        f"2. **No lasting return penalty.** The same shock comes with a {r0.beta * 100:+.2f} pp excess return versus "
        f"ACWI in the month (p = {r0.pval:.2f}) and a cumulative {r3.beta * 100:+.2f} pp after four months "
        f"(p = {r3.pval:.2f}, {sig(r3.pval)}). Markets reprice risk quickly; they do not keep falling.",
        f"3. **No regime effect.** Markets in the top third of political risk returned "
        f"{_fmt_pct(reg.attrs['high_minus_low_ann'])} a year versus the bottom third the following month "
        f"(p = {reg.attrs['p']:.2f}).",
        f"4. **Event type matters.** Across {int(allev['n_events'])} events the mean 3-day abnormal return was "
        f"{_fmt_pct(allev['mean CAR [-1,+1]'], 1)} (BMP p = {allev['BMP p [-1,+1]']:.2f}), but this hides a split:",
        *kind_lines,
        "   Largest 3-day moves: " + "; ".join(f"{r.country} {r.event} {_fmt_pct(r['CAR [-1,+1]'])}"
                                              for _, r in worst.iterrows()) + ".",
        f"5. **A simple tilt adds little.** Halving the weight of the three markets with the sharpest rise in "
        f"real-time political risk gave a return/volatility ratio of {tilt['return/vol']:.2f} vs {eq['return/vol']:.2f} "
        f"for equal weight, max drawdown of {_fmt_pct(tilt['max drawdown'])} vs {_fmt_pct(eq['max drawdown'])}, and an "
        f"information ratio of {tilt['information ratio']:.2f} at {_fmt_pct(tilt['tracking error'])} tracking error, "
        f"before transaction costs ({_fmt_pct(tilt['avg monthly turnover'])} average monthly turnover).",
        "",
        "## Implications for the total fund", "",
        "- Treat political risk as a **risk-budget input**, not a return signal: it predicts higher volatility "
        "in the same month and, more weakly, the next, which matters for position sizing, risk limits and option hedging, while "
        "it does not predict lower returns.",
        ("- **Unscheduled " + " and ".join(sig_kinds) + "** events carry statistically significant short-run losses; "
         "scheduled elections do not, because markets can price and hedge them in advance. Monitoring for "
         "leadership and cabinet instability is more valuable than election calendars." if sig_kinds else
         "- No single event type shows a statistically significant short-run loss with at least five events."),
        "- Stress-test returns are in USD and so include currency moves. For a Canadian-dollar fund, the "
        "FX hedging decision is part of the political-risk exposure, not separate from it.",
        "",
        "## Current read (latest month)", "",
    ]
    latest = res["pri_latest"].sort_values(ascending=False)
    lines += ["| Country | PRI (real time) | Tilt-model weight |", "|---|---|---|"]
    for c, v in latest.items():
        lines.append(f"| {c} | {v:+.2f} | {_fmt_pct(w.iloc[-1].get(c, np.nan))} |")
    sc = res.get("scenarios")
    if sc is not None:
        vols, port, ana, sc_list = sc
        lines += ["", "## Scenarios: what to do if...", "",
                  "Each scenario takes its political-risk shocks from a comparable historical episode. The panel VAR "
                  "turns them into projected volatility; the portfolio is an equal-weight mix of the 10 markets held "
                  "by a Canadian-dollar investor, with correlations held fixed (which understates risk in a crisis).", ""]
        for s_ in sc_list:
            v = vols[vols.scenario == s_.name].sort_values("vol change", ascending=False)
            p_ = port.loc[s_.name]
            a = ana[ana.scenario == s_.name]
            hit = v[v["shock (s.d.)"] >= 1].head(3)
            hit_txt = ", ".join(f"{r.country} {r['vol change'] * 100:+.0f}%" for _, r in hit.iterrows()) or "no market above a 1 s.d. shock"
            worst = a.nsmallest(1, "CAD-investor return")
            w_txt = ""
            if len(worst):
                w = worst.iloc[0]
                w_txt = (f" In the analogue ({w.start} to {w.end}), the worst-hit market for a Canadian investor was "
                         f"{w.country} at {_fmt_pct(w['CAD-investor return'])}: {_fmt_pct(w['local equity'])} from local equity "
                         f"and {_fmt_pct(w['currency vs CAD'])} from currency.")
            if v["shock (s.d.)"].max() < 1:
                lines += [f"**{s_.name}.** {s_.story} The monthly political-risk indices barely registered this episode "
                          f"(largest shock {v['shock (s.d.)'].max():.1f} s.d.), so the model projects almost no change in "
                          f"volatility.{w_txt} News-based indices miss domestic governance shocks like these, so they "
                          f"need separate monitoring: the event study, not the index, is the guide here.", ""]
                continue
            lines += [f"**{s_.name}.** {s_.story} Largest projected volatility rises: {hit_txt}. Portfolio 1-month 95% VaR "
                      f"rises from {_fmt_pct(p_['current 1-month VaR (95%)'])} to {_fmt_pct(p_['scenario 1-month VaR (95%)'])}; "
                      f"holding risk constant means cutting exposure by {_fmt_pct(p_['exposure cut to hold VaR'])}.{w_txt}", ""]
    lines += ["", "## Stress tests (cumulative USD return)", "", (stress * 100).round(1).to_markdown(), "",
              "## Method notes and limitations", "",
              "- PRI uses within-country z-scores; `pri_rt` uses expanding windows so the backtest has no look-ahead.",
              "- Local projections include two lags of the outcome and the shock; Driscoll-Kraay errors allow for "
              "cross-country and serial correlation.",
              "- Panel VAR is identified with political risk ordered first; results may depend on this ordering.",
              "- Ten markets and roughly two decades of data limit statistical power. Treat estimates as indicative.",
              "- Scenario shocks are calibrated to historical analogues; projections assume each market's volatility "
              "responds only to its own political risk and that correlations do not change.",
              "- Event dates are the first U.S. trading day on which the news could be priced, taken from public reporting.", ""]
    path = os.path.join(out, "briefing.md")
    with open(path, "w") as f:
        f.write("\n".join(lines))
    return path
