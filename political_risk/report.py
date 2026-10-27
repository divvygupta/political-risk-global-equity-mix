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
    """How much each market's volatility would rise in each scenario, and what that does to portfolio risk."""
    from matplotlib.colors import LinearSegmentedColormap

    short = {"Tariff escalation": "Tariff\nescalation", "European security crisis": "European\nsecurity crisis",
             "U.S. fiscal standoff": "U.S. fiscal\nstandoff", "Emerging-market governance shock": "EM governance\nshock*"}
    order = [s_ for s_ in short if s_ in set(vols["scenario"])]
    piv = vols.pivot(index="country", columns="scenario", values="vol change")[order] * 100
    cur = vols.drop_duplicates("country").set_index("country")["current vol"] * 100
    piv = piv.loc[piv.mean(axis=1).sort_values(ascending=False).index]
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(9, 4.1), gridspec_kw={"width_ratios": [1.25, 1]})
    cmap = LinearSegmentedColormap.from_list("w2v", ["#ffffff", "#f6c9a8", VERMILLION])
    a1.imshow(piv.values, cmap=cmap, vmin=0, vmax=max(piv.values.max(), 1), aspect="auto")
    for i, c in enumerate(piv.index):
        for j, sc in enumerate(piv.columns):
            v = piv.loc[c, sc]
            a1.text(j, i, f"+{v:.0f}%", ha="center", va="center", fontsize=7.5,
                    color="white" if v > piv.values.max() * 0.7 else BLACK)
    a1.set_xticks(range(len(order)), [short[o] for o in order], fontsize=7)
    a1.set_yticks(range(len(piv)), [f"{c} (now {cur[c]:.0f}%)" for c in piv.index], fontsize=7.5)
    a1.tick_params(top=False, right=False, length=0)
    a1.set_title("(a) Rise in each market's volatility, first month")
    for sp in a1.spines.values():
        sp.set_visible(False)
    yy = np.arange(len(port))
    names = [short.get(s_, s_).replace("\n", " ").replace("*", "") for s_ in port.index]
    base = port["current 1-month VaR (95%)"].iloc[0] * 100
    a2.barh(yy, port["scenario 1-month VaR (95%)"] * 100, height=0.55, color=LIGHT, edgecolor=BLACK, lw=0.6)
    a2.axvline(base, color=BLACK, ls="--", lw=0.8)
    a2.text(base + 0.03, -0.62, f"Today: {base:.1f}%", fontsize=7, ha="left", va="bottom")
    for i, (_, r) in enumerate(port.iterrows()):
        a2.text(r["scenario 1-month VaR (95%)"] * 100 + 0.03, i,
                f"{r['scenario 1-month VaR (95%)'] * 100:.1f}%  (cut exposure {r['exposure cut to hold VaR'] * 100:.0f}%)",
                va="center", fontsize=6.8)
    a2.set_yticks(yy, names, fontsize=7.5)
    a2.set_ylim(len(port) - 0.5, -0.9)
    a2.set_xlim(base * 0.9, port["scenario 1-month VaR (95%)"].max() * 100 * 1.22)
    a2.set_xlabel("Per cent of portfolio value")
    a2.set_title("(b) Portfolio loss not exceeded in 19 months out of 20")
    fig.tight_layout()
    return _save(fig, out, "fig8_scenarios.png",
                 "Notes: (a) Projected percentage rise in each market's annualised volatility in the scenario's first month; "
                 "the label shows today's volatility. (b) One-month 95% value at\nrisk of an equal-weight portfolio of the "
                 "10 markets held by a Canadian-dollar investor, and the cut in exposure that brings it back to today's level. "
                 "Correlations are held at\nlast year's values, which understates risk in a crisis. *The news-based indices "
                 "barely registered past emerging-market governance shocks, so the model projects almost no change.\n" + SOURCE)


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


# --- Election surprises, leadership exits and the risk taxonomy ------------------------------
CLASS_STYLE = {"Upset": (VERMILLION, "D"), "Big miss": (ORANGE, "s"), "Toss-up": (BLUE, "^"), "As expected": (BLACK, "o")}
SHORT = {"USA": "US", "GBR": "UK", "DEU": "DE", "JPN": "JP", "FRA": "FR", "CAN": "CA", "AUS": "AU", "IND": "IN",
         "BRA": "BR", "ZAF": "ZA"}


def _strip(ax, per, col, label=True, label_classes=("Upset", "Big miss"), seed=0, gap=0.42):
    rng = np.random.default_rng(seed)
    classes = [c for c in CLASS_STYLE if c in set(per["surprise"])]
    for i, c in enumerate(classes):
        d = per[per["surprise"] == c].dropna(subset=[col])
        x = i - 0.08 + rng.uniform(-0.12, 0.12, len(d))
        colr, mk = CLASS_STYLE[c]
        ax.scatter(x, d[col], color=colr, marker=mk, s=16, lw=0.4, edgecolor=BLACK, zorder=3, alpha=0.9)
        ax.hlines(d[col].mean(), i - 0.34, i + 0.2, color=BLACK, lw=1.4, zorder=4)
        if label and c in label_classes:
            pts = sorted([(r[col], xi, f"{SHORT[r.country]} {str(r.date)[:4]}") for xi, (_, r) in zip(x, d.iterrows())
                          if r[col] > 1.96])
            last = -np.inf
            for yv, xi, txt in pts:
                ty = max(yv, last + gap)
                last = ty
                ax.annotate(txt, (xi, yv), xytext=(i + 0.2, ty), textcoords="data", fontsize=5.8, va="center",
                            arrowprops=dict(arrowstyle="-", lw=0.4, color=GREY, shrinkA=0, shrinkB=2))
    ax.axhline(1.96, color=GREY, lw=0.6, ls=(0, (4, 3)))
    names = {"Upset": "Upset", "Big miss": "Big\nmiss", "Toss-up": "Toss-\nup", "As expected": "As\nexpected"}
    ax.set_xticks(range(len(classes)),
                  [f"{names[c]}\n(n = {per.loc[per['surprise'] == c, col].notna().sum()})" for c in classes], fontsize=7)
    ax.set_xlim(-0.6, len(classes) - 0.2)


def plot_election_surprises(el: pd.DataFrame, exits: pd.DataFrame, out: str) -> str:
    """How much stocks move after elections, by how the result compared with the polls, and after leader exits."""
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(9, 4.3), gridspec_kw={"width_ratios": [1, 1.05]})
    names = {"Upset": "Poll leader\nlost", "Big miss": "Right winner,\nresult far\nfrom polls",
             "Toss-up": "Too close\nto call", "As expected": "Polls were\nright"}
    classes = [c for c in ["Upset", "Big miss", "Toss-up", "As expected"] if c in set(el["surprise"])]
    rng = np.random.default_rng(0)
    for i, c in enumerate(classes):
        d = el.loc[el["surprise"] == c, "|SCAR [0,+1]|"]
        colr = CLASS_STYLE[c][0]
        a1.bar(i, d.mean(), width=0.62, color=colr, alpha=0.35, edgecolor=BLACK, lw=0.6)
        a1.scatter(i + rng.uniform(-0.18, 0.18, len(d)), d, color=colr, edgecolor=BLACK, lw=0.4, s=14, zorder=3)
    for c, lab in [("Upset", "Brexit"), ("Upset", "Brazil 2026")]:
        r = el[(el.surprise == c) & (el.event.str.contains("Brexit" if lab == "Brexit" else "Flavio"))]
        if len(r):
            i = classes.index(c)
            a1.annotate(lab, (i, r["|SCAR [0,+1]|"].iloc[0]), xytext=(10, 0), textcoords="offset points", fontsize=7,
                        va="center")
    wrong = el.loc[el["surprise"].isin(["Upset", "Big miss"]), "|SCAR [0,+1]|"].mean()
    right = el.loc[el["surprise"] == "As expected", "|SCAR [0,+1]|"].mean()
    a1.axhline(1, color=GREY, lw=0.7, ls=(0, (4, 3)))
    a1.text(0.97, 0.97, f"Average move\nPolls wrong (first two groups): {wrong:.1f}x\nPolls right: {right:.1f}x\n"
            "Dashed line: a normal day", transform=a1.transAxes, ha="right", va="top", fontsize=8, linespacing=1.4)
    means = el.groupby("surprise")["|SCAR [0,+1]|"].mean()
    a1.set_xticks(range(len(classes)),
                  [f"{names[c]}\n(n = {(el['surprise'] == c).sum()})\n{means[c]:.1f}x" for c in classes], fontsize=7.3)
    a1.set_ylabel("Size of the two-day stock move, multiples of a normal day")
    a1.set_title("(a) Elections: stocks move when the polls are wrong")
    a1.tick_params(top=False)
    d = exits.sort_values("SCAR [0,+1]").reset_index(drop=True)
    y = np.arange(len(d))
    sig = d["SCAR [0,+1]"].abs() > 1.96
    uk = d["country"] == "GBR"
    a2.axvspan(-1.96, 1.96, color=LIGHT, alpha=0.5, lw=0)
    a2.scatter(d.loc[~uk, "SCAR [0,+1]"], y[~uk], color=GREY, s=14, zorder=3, label="Other countries")
    a2.scatter(d.loc[uk, "SCAR [0,+1]"], y[uk], color=VERMILLION, marker="D", s=18, zorder=3, label="UK prime ministers")
    for i, r in d.iterrows():
        if sig[i] or uk[i]:
            a2.annotate(f"{r.event.split(' ')[0]} ({SHORT[r.country]} {str(r.date)[:4]})", (r["SCAR [0,+1]"], i),
                        xytext=(6 if r["SCAR [0,+1]"] >= 0 else -6, 0), textcoords="offset points", fontsize=6.6,
                        ha="left" if r["SCAR [0,+1]"] >= 0 else "right", va="center")
    _zero(a2, "x")
    a2.set_yticks([])
    a2.set_xlim(-4.2, 5.4)
    a2.set_ylim(-1.6, len(d))
    a2.text(0, -1.1, "not significant", ha="center", fontsize=7, color=GREY)
    a2.set_xlabel("Two-day stock move, multiples of a normal day")
    a2.set_title(f"(b) Leader exits: {int(sig.sum())} of {len(d)} moved the market")
    a2.legend(loc="lower right", fontsize=7)
    a2.tick_params(left=False, right=False, top=False)
    fig.tight_layout()
    return _save(fig, out, "fig10_election_surprises.png",
                 "Notes: Each country's stocks against MSCI ACWI over the result day and the next (market model), divided by "
                 "the market's normal two-day move. (a) Bars are group averages,\ndots are single elections. (b) Each dot is "
                 "a resignation or ouster of a head of government; the shaded band is not statistically significant at 5%.\n"
                 + SOURCE)


def plot_risk_taxonomy(summary: pd.DataFrame, aligned: tuple, out: str) -> str:
    """Event risks with expected and surprise outcomes vs. exogenous risks: path, size and volatility."""
    mean, se = aligned
    styles = {"Event risk: expected outcome": (BLACK, "-", "Event risk, expected outcome"),
              "Event risk: surprise outcome": (VERMILLION, "--", "Event risk, surprise outcome"),
              "Exogenous risk": (BLUE, ":", "Exogenous risk")}
    fig, (a1, a2, a3) = plt.subplots(1, 3, figsize=(9, 3.1), gridspec_kw={"width_ratios": [1.35, 1, 1]})
    for c in mean.columns:
        col, ls, lab = styles[c]
        a1.fill_between(mean.index, (mean[c] - 1.96 * se[c]) * 100, (mean[c] + 1.96 * se[c]) * 100, color=col,
                        alpha=0.12, lw=0)
        a1.plot(mean.index, mean[c] * 100, color=col, ls=ls, label=f"{lab} (n = {int(summary.loc[c, 'n'])})")
    _zero(a1)
    a1.axvline(0, color=GREY, lw=0.5)
    a1.set_xlabel("Trading days relative to news")
    a1.set_ylabel("Per cent")
    a1.set_title("(a) Cumulative abnormal return, signed so\n      the first move is up")
    a1.legend(loc="upper left", fontsize=6.3)
    x = np.arange(len(summary))
    labels = [styles[c][2].replace(", ", ",\n").replace("Exogenous risk", "Exogenous\nrisk") for c in summary.index]
    a2.bar(x, summary["mean |equity move| (x normal day)"], width=0.55, color=[styles[c][0] for c in summary.index],
           alpha=0.85, edgecolor=BLACK, lw=0.5)
    for i, (c, r) in enumerate(summary.iterrows()):
        a2.text(i, r["mean |equity move| (x normal day)"] + 0.08, f"{r['share with significant move'] * 100:.0f}% significant",
                ha="center", fontsize=6.3)
    a2.set_ylim(0, summary["mean |equity move| (x normal day)"].max() * 1.18)
    a2.set_xticks(x, labels, fontsize=6.5)
    a2.set_ylabel("Multiples of a normal day")
    a2.set_title("(b) Average absolute move, days 0 to +1")
    w = 0.32
    a3.bar(x - w / 2, summary["vol before (x normal)"], width=w, color=LIGHT, edgecolor=BLACK, lw=0.5,
           label="10 days before")
    a3.bar(x + w / 2, summary["vol after (x normal)"], width=w, color=GREY, edgecolor=BLACK, lw=0.5,
           label="10 days after")
    a3.axhline(1, color=BLACK, lw=0.5, ls=(0, (4, 3)))
    a3.set_xticks(x, labels, fontsize=6.5)
    a3.set_ylim(0, max(summary[["vol before (x normal)", "vol after (x normal)"]].max()) * 1.25)
    a3.set_ylabel("Multiples of normal volatility")
    a3.set_title("(c) Abnormal-return volatility")
    a3.legend(loc="upper left", fontsize=6.5)
    fig.tight_layout()
    return _save(fig, out, "fig11_risk_taxonomy.png",
                 "Notes: Event risks have a known date (elections, scheduled votes and fiscal statements); exogenous risks "
                 "arrive without warning (invasions,\nsackings, resignations, attacks). Market model on ACWI; shading is the "
                 "95% confidence interval.\n" + SOURCE)


def plot_themes(themes: pd.DataFrame, paths: pd.DataFrame, out: str) -> str:
    """Thematic risks: total relative performance, currency, and how gradually the move built."""
    d = themes.reset_index(drop=True)
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(9, 3.9), gridspec_kw={"width_ratios": [1.1, 1]})
    y = np.arange(len(d))[::-1]
    a1.barh(y, d["relative return"] * 100, height=0.6, color=[GREY if v < 0 else LIGHT for v in d["relative return"]],
            edgecolor=BLACK, lw=0.4, label="Equities vs. ACWI")
    a1.scatter(d["currency"] * 100, y, color=ORANGE, marker="D", s=12, zorder=3, label="Currency vs. U.S. dollar")
    _zero(a1, "x")
    a1.set_yticks(y, [f"{t} ({SHORT[c]})" for t, c in zip(d["theme"], d["country"])], fontsize=6.3)
    a1.set_xlabel("Per cent over the theme window")
    a1.set_title("(a) Performance over each theme")
    a1.legend(loc="upper center", bbox_to_anchor=(0.45, -0.13), ncol=2, fontsize=6.5)
    picks = d.reindex(d["relative return"].abs().sort_values(ascending=False).index).head(5)
    for (_, r), col, ls in zip(picks.iterrows(), [BLACK, VERMILLION, BLUE, GREEN, PURPLE], ["-", "--", ":", "-.", "-"]):
        p = paths[(r.theme, r.country)].dropna() * 100
        a2.plot(p.index / 21, p.values, color=col, ls=ls, lw=1.0, label=f"{r.theme} ({SHORT[r.country]})")
    _zero(a2)
    a2.set_xlabel("Months since the theme began")
    a2.set_ylabel("Per cent vs. ACWI")
    a2.set_title("(b) The five largest moves built up over months")
    a2.legend(loc="upper center", bbox_to_anchor=(0.5, -0.13), ncol=2, fontsize=6.2)
    fig.tight_layout()
    return _save(fig, out, "fig12_thematic_risks.png",
                 "Notes: Relative return of each market's U.S.-dollar ETF against ACWI from the close before the theme began; "
                 "currency is the local currency against the U.S. dollar.\n" + SOURCE)


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
    sp = res.get("surprises")
    if sp is not None and len(sp["elections"]):
        el, bc, tests, ex, tax, th = (sp[k] for k in ["elections", "by_class", "tests", "exits", "taxonomy", "themes"])
        surp = el[el["surprise"].isin(["Upset", "Big miss"])]
        exp_ = el[el["surprise"] == "As expected"]
        te, tc = tests.loc["Equity: surprise vs. as expected"], tests.loc["Currency: surprise vs. as expected"]
        top = el.reindex(el["|SCAR [0,+1]|"].sort_values(ascending=False).index).head(3)
        n_sig_up = int((el.loc[el.surprise == "Upset", "|SCAR [0,+1]|"] > 1.96).sum())
        n_up = int((el.surprise == "Upset").sum())
        lines += ["", "## Election surprises, leader exits and the risk taxonomy", "",
                  f"**Polls vs. results.** Across {len(el)} national elections in the 10 markets, each classed against its "
                  f"final polls, results that went against the polls moved the country's equities (against ACWI, days 0 to +1) "
                  f"by {surp['|SCAR [0,+1]|'].mean():.1f} times a normal day's move on average, against "
                  f"{exp_['|SCAR [0,+1]|'].mean():.1f} times for results that matched the polls (Welch p = {te['welch p']:.3f}, "
                  f"Mann-Whitney p = {te['mann-whitney p']:.3f}). {n_sig_up} of {n_up} upsets moved equities significantly. "
                  f"Currencies moved more after surprises too ({surp['|FX z [0,+1]|'].mean():.1f} vs. "
                  f"{exp_['|FX z [0,+1]|'].mean():.1f} times a normal day), but the difference is not statistically "
                  f"significant (p = {tc['welch p']:.2f}).", "",
                  "| Poll outcome | Elections | Mean absolute equity move | Times a normal day | Mean absolute currency move | Significant equity moves |",
                  "|---|---|---|---|---|---|"]
        for c, r in bc.iterrows():
            lines.append(f"| {c} | {int(r.n)} | {_fmt_pct(r['mean |equity move|'])} | {r['mean |equity move| (x normal day)']:.1f} | "
                         f"{_fmt_pct(r['mean |currency move|'])} | {_fmt_pct(r['share with significant equity move'], 0)} |")
        lines += ["", "Largest election reactions relative to each market's normal volatility: " + "; ".join(
            f"{r.country} {str(r.date)[:4]} ({r.event}, {r.surprise.lower()}): {_fmt_pct(r['CAR [0,+1]'])}"
            for _, r in top.iterrows()) + ".",
            "Even big political changes move markets little when the polls saw them coming, for example "
            + " and ".join(f"{r.country} {str(r.date)[:4]} ({r.event}, {_fmt_pct(r['CAR [0,+1]'])})"
                           for _, r in exp_[exp_.event.str.contains("loses")].iterrows()) + ".", ""]
        sig_ex = ex[ex["|SCAR [0,+1]|"] > 1.96]
        uk = ex[ex.country == "GBR"]
        lines += [f"**Leader exits.** Of {len(ex)} departures of a head of government, {len(sig_ex)} moved the country's "
                  f"equities significantly: " + "; ".join(f"{r.country} {r.event} ({_fmt_pct(r['CAR [0,+1]'])})"
                                                         for _, r in sig_ex.iterrows()) + ". "
                  f"The UK's {len(uk)} prime-ministerial exits since 2010 moved UK equities by between "
                  f"{_fmt_pct(uk['CAR [0,+1]'].min())} and {_fmt_pct(uk['CAR [0,+1]'].max())} against ACWI. A resignation "
                  "is usually the end of a crisis markets have already priced, not the start of one.", ""]
        e1, e2, e3 = (tax.loc[k] for k in ["Event risk: expected outcome", "Event risk: surprise outcome", "Exogenous risk"])
        lines += ["**Event, exogenous and thematic risks.**", "",
                  f"- *Event risks* (known date, uncertain outcome): when the outcome matched expectations "
                  f"(n = {int(e1.n)}), the average move was {e1['mean |equity move| (x normal day)']:.1f} times a normal day "
                  f"and {_fmt_pct(e1['share with significant move'], 0)} were significant. When it did not (n = {int(e2.n)}), "
                  f"{e2['mean |equity move| (x normal day)']:.1f} times and {_fmt_pct(e2['share with significant move'], 0)}. "
                  f"About {_fmt_pct(1 - e2['median share of move kept after 10 days'], 0)} of a typical surprise move "
                  f"reversed within ten days.",
                  f"- *Exogenous risks* (no warning, n = {int(e3.n)}): {e3['mean |equity move| (x normal day)']:.1f} times "
                  f"a normal day on average, {_fmt_pct(e3['mean signed equity move'])} in the average direction, and "
                  f"volatility stayed {e3['vol after (x normal)']:.1f} times normal for the next ten days, against "
                  f"{e1['vol after (x normal)']:.1f} after an expected event. The first move tended to keep going rather than "
                  "reverse.",
                  ]
        if len(th):
            neg = th[th["relative return"] < 0]
            fm = th.loc[th["relative return"].abs() > 0.1, "first-month share"].dropna()
            lines += [f"- *Thematic risks* (building over months): in {len(neg)} of {len(th)} theme-market pairs the market "
                      f"lagged ACWI over the theme, by up to {_fmt_pct(-th['relative return'].min(), 0)}. For the {len(fm)} "
                      f"moves larger than 10%, the first month was a poor guide: no more than {_fmt_pct(fm.max(), 0)} of "
                      f"the eventual move had happened after one month, and in {int((fm < 0).sum())} cases the market had "
                      f"first moved the other way. The moves built up gradually, so no single day stands out. Volatility "
                      f"relative to ACWI was {th['excess vol (x prior)'].median():.2f} times its pre-theme level (median).", "",
                      "| Theme | Market | Window | Equities vs. ACWI | Currency vs. USD | Volatility vs. before |",
                      "|---|---|---|---|---|---|"]
            for _, r in th.iterrows():
                lines.append(f"| {r.theme} | {r.country} | {r.start} to {r.end} | {_fmt_pct(r['relative return'])} | "
                             f"{_fmt_pct(r.currency)} | {r['excess vol (x prior)']:.2f}x |")
        lines += ["", "**What this means for the fund.**", "",
                  "- Price *the polling error*, not the election. Hedging scheduled events pays only when the polls are "
                  "close or have a record of missing (referendums, first rounds, parliamentary seat counts).",
                  "- Exogenous shocks are not predictable from the calendar; they belong in the risk budget (liquidity, "
                  "limits and standing hedges), and their effect on volatility lasts longer than an election's.",
                  "- Thematic risks are slow and show up in the political-risk index and in currencies over months: they are "
                  "a strategic allocation and currency-hedging decision, not a trading one.", ""]
    lines += ["", "## Stress tests (cumulative USD return)", "", (stress * 100).round(1).to_markdown(), "",
              "## Method notes and limitations", "",
              "- PRI uses within-country z-scores; `pri_rt` uses expanding windows so the backtest has no look-ahead.",
              "- Local projections include two lags of the outcome and the shock; Driscoll-Kraay errors allow for "
              "cross-country and serial correlation.",
              "- Panel VAR is identified with political risk ordered first; results may depend on this ordering.",
              "- Ten markets and roughly two decades of data limit statistical power. Treat estimates as indicative.",
              "- Scenario shocks are calibrated to historical analogues; projections assume each market's volatility "
              "responds only to its own political risk and that correlations do not change.",
              "- Event dates are the first U.S. trading day on which the news could be priced, taken from public reporting.",
              "- Election surprise classes are judgements based on final polls and seat projections; with 5 upsets and 8 big "
              "misses, the comparison is indicative. Currencies are not available for the United States.",
              "- Theme windows are set by hand around well-known episodes, and other news moved markets in the same "
              "windows, so the thematic results describe what happened rather than isolate cause.", ""]
    path = os.path.join(out, "briefing.md")
    with open(path, "w") as f:
        f.write("\n".join(lines))
    return path
