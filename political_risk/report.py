"""Charts, tables and an auto-generated investment briefing."""

from __future__ import annotations

import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

# Okabe-Ito colours (colour-blind safe), used with distinct markers and line styles.
BLACK, BLUE, VERMILLION, GREEN, PURPLE, ORANGE = "#000000", "#0072B2", "#D55E00", "#009E73", "#CC79A7", "#E69F00"
GREY, LIGHT = "#8c8c8c", "#d9d9d9"
SOURCE = "Sources: Baker, Bloom and Davis (EPU); Caldara and Iacoviello (GPR); Yahoo Finance; author's calculations."

plt.rcParams.update({
    "figure.dpi": 150, "savefig.bbox": "tight", "savefig.facecolor": "white",
    "font.family": "STIXGeneral", "mathtext.fontset": "stix", "font.size": 9,
    "axes.titlesize": 9.5, "axes.titleweight": "normal", "axes.titlelocation": "left",
    "axes.linewidth": 0.6, "axes.edgecolor": BLACK, "axes.grid": False,
    "xtick.direction": "in", "ytick.direction": "in", "xtick.top": True, "ytick.right": True,
    "xtick.major.width": 0.6, "ytick.major.width": 0.6, "lines.linewidth": 1.2,
    "legend.frameon": False, "legend.fontsize": 8,
})


def _save(fig, out, name, source=SOURCE):
    if source:
        fig.text(0.01, -0.02, source, fontsize=7, color=GREY, ha="left", va="top")
    path = os.path.join(out, name)
    fig.savefig(path)
    plt.close(fig)
    return path


def _zero(ax, axis="y"):
    (ax.axhline if axis == "y" else ax.axvline)(0, color=BLACK, lw=0.5, ls=(0, (4, 3)))


def plot_pri(pri: pd.DataFrame, out: str, highlight=("USA", "GBR", "CAN")) -> str:
    wide = pri["pri"].unstack("country")
    avg = wide.mean(axis=1)
    fig, ax = plt.subplots(figsize=(7.5, 3))
    for c in wide.columns:
        if c not in highlight:
            ax.plot(wide.index, wide[c], color=LIGHT, lw=0.6)
    for c, col, ls in zip(highlight, [BLUE, VERMILLION, GREEN], ["-", "--", ":"]):
        if c in wide:
            ax.plot(wide.index, wide[c], color=col, lw=0.9, ls=ls, label=c)
    ax.plot(avg.index, avg, color=BLACK, lw=1.4, label="Average, 10 countries")
    for date, text in [("2016-06-01", "Brexit vote"), ("2022-03-01", "Invasion of\nUkraine"), ("2025-04-01", "U.S. tariffs")]:
        d = pd.Timestamp(date)
        if d in avg.index:
            ax.annotate(text, (d, avg[d] + 0.15), xytext=(d, wide.max().max() + 0.5), fontsize=7.5, ha="center",
                        va="bottom", arrowprops=dict(arrowstyle="-", lw=0.5, color=GREY))
    ax.set_ylim(top=wide.max().max() + 1.8)
    ax.set_ylabel("Standard deviations from country mean")
    ax.legend(ncol=4, loc="lower left", handlelength=2.2)
    return _save(fig, out, "fig1_political_risk_index.png")


def plot_lp(lp: pd.DataFrame, out: str) -> str:
    labels = {"xret": "(a) Cumulative excess return vs. ACWI", "log_rvol": "(b) Log realised volatility"}
    fig, axes = plt.subplots(1, 2, figsize=(7.5, 2.9))
    for ax, (y, lab) in zip(axes, labels.items()):
        d = lp[lp["outcome"] == y]
        ax.fill_between(d["h"], d["lo90"], d["hi90"], color=LIGHT, lw=0)
        ax.plot(d["h"], d["beta"], color=BLACK, marker="o", ms=3)
        _zero(ax)
        ax.set_title(lab)
        ax.set_xlabel("Months after shock")
        ax.set_xticks(range(0, 13, 2))
    axes[0].set_ylabel("Response to a 1 s.d. shock")
    return _save(fig, out, "fig2_local_projections.png",
                 "Notes: Panel local projections with country and month fixed effects; shaded area is the 90% confidence "
                 "interval (Driscoll-Kraay).\n" + SOURCE)


def plot_var(var: dict, out: str) -> str:
    cols = var["cols"]
    names = {"xret": "(a) Excess return", "log_rvol": "(b) Log realised volatility"}
    fig, axes = plt.subplots(1, len(cols) - 1, figsize=(7.5, 2.9))
    h = np.arange(var["irf"].shape[0])
    for ax, i in zip(axes, range(1, len(cols))):
        ax.fill_between(h, var["lo"][:, i, 0], var["hi"][:, i, 0], color=LIGHT, lw=0)
        ax.plot(h, var["irf"][:, i, 0], color=BLACK)
        _zero(ax)
        ax.set_title(names.get(cols[i], cols[i]))
        ax.set_xlabel("Months after shock")
        ax.set_xticks(range(0, 13, 2))
    return _save(fig, out, "fig3_panel_var_irf.png",
                 f"Notes: Fixed-effects panel VAR({var['p']}), Cholesky ordering with political risk first; shaded area is "
                 "the 90% country-bootstrap band.\n" + SOURCE)


def plot_events(per_event: pd.DataFrame, paths: pd.DataFrame, out: str) -> str:
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(9, 4.8), gridspec_kw={"width_ratios": [1.15, 1]})
    d = per_event.sort_values("CAR [0,+5]").reset_index(drop=True)
    se = (d["CAR [0,+5]"] / d["t [0,+5]"]).abs()
    y = np.arange(len(d))
    a1.errorbar(d["CAR [0,+5]"] * 100, y, xerr=1.96 * se * 100, fmt="none", ecolor=GREY, elinewidth=0.6)
    sig = d["p [0,+5]"] < 0.05
    a1.scatter(d.loc[sig, "CAR [0,+5]"] * 100, y[sig], color=BLACK, s=14, zorder=3, label="p < 0.05")
    a1.scatter(d.loc[~sig, "CAR [0,+5]"] * 100, y[~sig], facecolor="white", edgecolor=BLACK, s=14, zorder=3,
               lw=0.7, label="Not significant")
    a1.set_yticks(y, d["country"] + ", " + d["event"], fontsize=6.3)
    _zero(a1, "x")
    a1.set_title("(a) Abnormal return, days 0 to +5")
    a1.set_xlabel("Per cent")
    a1.legend(loc="lower right")
    m = paths.mean(axis=1) * 100
    s = paths.std(axis=1) / np.sqrt(paths.shape[1]) * 100
    a2.fill_between(m.index, m - 1.96 * s, m + 1.96 * s, color=LIGHT, lw=0)
    a2.plot(m.index, m, color=BLACK)
    _zero(a2)
    a2.axvline(0, color=GREY, lw=0.5)
    a2.set_title("(b) Average cumulative abnormal return")
    a2.set_xlabel("Trading days relative to event")
    a2.set_ylabel("Per cent")
    fig.tight_layout()
    return _save(fig, out, "fig4_event_study.png",
                 "Notes: Market model on ACWI, estimated over days -250 to -30. Bars and shading are 95% confidence intervals.\n"
                 + SOURCE)


def plot_regimes(reg: pd.DataFrame, out: str) -> str:
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(7, 2.7))
    x = np.arange(len(reg))
    for ax, col, title in [(a1, "ann. excess return", "(a) Next-month excess return vs. ACWI, annualised"),
                           (a2, "avg realised vol", "(b) Next-month realised volatility")]:
        ax.bar(x, reg[col] * 100, width=0.55, color=LIGHT, edgecolor=BLACK, lw=0.6)
        ax.set_xticks(x, reg.index.astype(str))
        ax.set_title(title)
        ax.set_ylabel("Per cent")
    _zero(a1)
    a1.set_xlabel("Political-risk tercile (within month)")
    a2.set_xlabel("Political-risk tercile (within month)")
    return _save(fig, out, "fig5_regimes.png")


def plot_backtest(rets: pd.DataFrame, out: str) -> str:
    cum = rets.cumsum()
    fig, (a1, a2) = plt.subplots(2, 1, figsize=(7.5, 4.2), sharex=True, gridspec_kw={"height_ratios": [2, 1]})
    for col, c, ls in zip(rets.columns, [BLACK, BLUE], ["-", "--"]):
        a1.plot(cum.index, np.exp(cum[col]) * 100, color=c, ls=ls, label=col)
        a2.plot(cum.index, (np.exp(cum[col] - cum[col].cummax()) - 1) * 100, color=c, ls=ls, lw=0.9)
    a1.set_title("(a) Growth of 100, U.S. dollars")
    a1.legend(loc="upper left")
    a2.set_title("(b) Drawdown, per cent")
    return _save(fig, out, "fig6_backtest.png")


def plot_stress(stress: pd.DataFrame, out: str) -> str:
    d = stress.drop(columns=["BENCH"], errors="ignore") * 100
    port = d.pop("Equal-weight portfolio") if "Equal-weight portfolio" in d else None
    n = len(d)
    fig, axes = plt.subplots(1, n, figsize=(2.0 * n, 3.2), sharex=True)
    lim = np.nanmax(np.abs(d.values)) * 1.1
    for k, (ax, (name, row)) in enumerate(zip(np.atleast_1d(axes), d.iterrows())):
        r = row.sort_values()
        ax.barh(range(len(r)), r.values, height=0.6, color=[GREY if v < 0 else LIGHT for v in r.values],
                edgecolor=BLACK, lw=0.4)
        ax.set_yticks(range(len(r)), r.index, fontsize=7)
        if port is not None:
            ax.axvline(port[name], color=VERMILLION, lw=0.9, ls="--", label="Equal-weight portfolio")
        _zero(ax, "x")
        ax.set_xlim(-lim, lim / 2)
        ax.set_title(f"({chr(97 + k)}) {name}", fontsize=8)
    fig.supxlabel("Cumulative return, per cent (U.S. dollars)", fontsize=8.5, y=0.04)
    fig.tight_layout(rect=(0, 0.05, 1, 1))
    h, l = np.atleast_1d(axes)[0].get_legend_handles_labels()
    fig.legend(h, l, loc="lower right", fontsize=7.5, bbox_to_anchor=(0.99, 0.0))
    return _save(fig, out, "fig7_stress_tests.png")


def plot_scenarios(vols: pd.DataFrame, port: pd.DataFrame, out: str) -> str:
    """Projected volatility rise by market for each scenario, and the portfolio's value at risk."""
    piv = vols.pivot(index="country", columns="scenario", values="vol change")[list(port.index)] * 100
    piv = piv.loc[piv.max(axis=1).sort_values().index]
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(8, 3.4), gridspec_kw={"width_ratios": [1.3, 1]})
    y = np.arange(len(piv))
    for col, c, mk in zip(piv.columns, [BLUE, VERMILLION, GREEN, PURPLE], ["o", "s", "^", "D"]):
        a1.scatter(piv[col], y, color=c, marker=mk, s=18, label=col, zorder=3)
    a1.set_yticks(y, piv.index)
    _zero(a1, "x")
    a1.set_xlabel("Per cent")
    a1.set_title("(a) Projected rise in volatility, first month")
    a1.legend(loc="upper center", bbox_to_anchor=(0.5, -0.17), ncol=2, fontsize=7, handletextpad=0.3)
    yy = np.arange(len(port))
    a2.barh(yy, port["scenario 1-month VaR (95%)"] * 100, height=0.55, color=LIGHT, edgecolor=BLACK, lw=0.6)
    a2.axvline(port["current 1-month VaR (95%)"].iloc[0] * 100, color=BLACK, ls="--", lw=0.8)
    a2.text(port["current 1-month VaR (95%)"].iloc[0] * 100, -0.5, " Current VaR", fontsize=7, va="bottom")
    a2.set_yticks(yy, [s.replace(" shock", "").replace("Emerging-market", "EM") for s in port.index], fontsize=7.5)
    a2.set_ylim(len(port) - 0.5, -0.75)
    lo = port["current 1-month VaR (95%)"].iloc[0] * 100 * 0.85
    a2.set_xlim(lo, port["scenario 1-month VaR (95%)"].max() * 100 * 1.04)
    a2.set_xlabel("Per cent of portfolio value")
    a2.set_title("(b) One-month 95% value at risk")
    fig.tight_layout()
    return _save(fig, out, "fig8_scenarios.png",
                 "Notes: Equal-weight portfolio of 10 markets held by a Canadian-dollar investor; correlations held at their "
                 "last-year values.\n" + SOURCE)


def plot_fx_split(analogues: pd.DataFrame, out: str, n: int = 4) -> str:
    """For each scenario's analogue, the worst-hit markets' CAD returns split into local equity and currency."""
    scen = list(dict.fromkeys(analogues["scenario"]))
    fig, axes = plt.subplots(1, len(scen), figsize=(8, 2.9), sharey=True)
    for k, (ax, sc) in enumerate(zip(np.atleast_1d(axes), scen)):
        d = analogues[analogues.scenario == sc].nsmallest(n, "CAD-investor return")
        eq, fxc = np.log1p(d["local equity"]) * 100, np.log1p(d["currency vs CAD"]) * 100
        x = np.arange(len(d))
        ax.bar(x, eq, width=0.6, color=BLUE, label="Local equity")
        ax.bar(x, fxc, width=0.6, bottom=np.where((fxc < 0) == (eq < 0), eq, 0), color=ORANGE, label="Currency vs. CAD")
        ax.scatter(x, np.log1p(d["CAD-investor return"]) * 100, color=BLACK, marker="D", s=10, zorder=3, label="Total")
        _zero(ax)
        ax.set_xticks(x, d["country"])
        ax.set_title(f"({chr(97 + k)}) {sc.replace(' shock', '')}", fontsize=8)
    np.atleast_1d(axes)[0].set_ylabel("Log return, per cent")
    np.atleast_1d(axes)[0].legend(loc="lower left", fontsize=6.5)
    fig.tight_layout()
    return _save(fig, out, "fig9_scenario_analogues.png",
                 "Notes: Returns over each historical analogue window for a Canadian-dollar investor; four worst-hit markets.\n"
                 + SOURCE)


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
