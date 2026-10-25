"""Portfolio applications: regime analysis, a political-risk-aware tilt backtest, stress tests."""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats


def regime_analysis(panel: pd.DataFrame) -> pd.DataFrame:
    """Next-month country performance by the country's real-time political-risk tercile.

    Terciles are formed within each month across countries, using only
    information available at the time (``pri_rt``), so the table answers:
    when a market's political risk is high relative to its peers, what tends
    to happen next?
    """
    d = panel.copy()
    d["next_xret"] = d.groupby(level="country")["xret"].shift(-1)
    d["next_rvol"] = d.groupby(level="country")["rvol"].shift(-1)
    d = d.dropna(subset=["pri_rt", "next_xret"])
    d["tercile"] = d.groupby(level="date")["pri_rt"].transform(
        lambda s: pd.qcut(s.rank(method="first"), 3, labels=["Low risk", "Medium", "High risk"]))
    g = d.groupby("tercile", observed=True)
    out = pd.DataFrame({
        "ann. excess return": g["next_xret"].mean() * 12,
        "ann. volatility of excess return": g["next_xret"].std() * np.sqrt(12),
        "avg realised vol": g["next_rvol"].mean(),
        "hit rate (beat benchmark)": g["next_xret"].apply(lambda s: (s > 0).mean()),
        "observations": g.size(),
    })
    hi, lo = d.loc[d["tercile"] == "High risk", "next_xret"], d.loc[d["tercile"] == "Low risk", "next_xret"]
    t, p = stats.ttest_ind(hi, lo, equal_var=False)
    out.attrs["high_minus_low_ann"] = (hi.mean() - lo.mean()) * 12
    out.attrs["t"] = t
    out.attrs["p"] = p
    return out


def tilt_weights(pri_rt: pd.DataFrame, n_tilt: int = 3, cut: float = 0.5, lookback: int = 3) -> pd.DataFrame:
    """Monthly weights for a political-risk-aware tilt of an equal-weight portfolio.

    At the start of month t, using real-time PRI to the end of month t-1, the
    ``n_tilt`` countries with the largest rise in political risk over the last
    ``lookback`` months have their weight cut by ``cut``. The freed weight goes
    pro rata to the other countries. Weights always sum to 1.
    """
    change = pri_rt - pri_rt.shift(lookback)
    signal = change.shift(1)  # information known before month t
    n = pri_rt.shape[1]
    w = pd.DataFrame(1.0 / n, index=pri_rt.index, columns=pri_rt.columns)
    for t in signal.index:
        s = signal.loc[t].dropna()
        if len(s) < n_tilt + 1:
            continue
        hit = s.nlargest(n_tilt).index
        row = pd.Series(1.0 / n, index=pri_rt.columns)
        freed = row[hit].sum() * cut
        row[hit] *= (1 - cut)
        others = row.index.difference(hit)
        row[others] += freed * row[others] / row[others].sum()
        w.loc[t] = row
    return w


def _metrics(r: pd.Series) -> dict:
    cum = r.cumsum()
    dd = cum - cum.cummax()
    return {"ann. return": r.mean() * 12, "ann. vol": r.std() * np.sqrt(12),
            "return/vol": (r.mean() * 12) / (r.std() * np.sqrt(12)), "max drawdown": dd.min()}


def backtest(panel: pd.DataFrame, **kwargs) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Compare the political-risk tilt with an equal-weight country portfolio.

    Returns (metrics table, monthly returns of both portfolios, tilt weights).
    """
    ret = panel["ret"].unstack("country").sort_index()
    pri_rt = panel["pri_rt"].unstack("country").reindex(ret.index)
    ret = ret.dropna(how="all")
    w_tilt = tilt_weights(pri_rt, **kwargs).reindex(ret.index)
    avail = ret.notna()
    w_eq = avail.div(avail.sum(axis=1), axis=0)
    w_t = w_tilt.where(avail, 0.0)
    w_t = w_t.div(w_t.sum(axis=1), axis=0)
    r_eq = (w_eq * ret.fillna(0)).sum(axis=1)
    r_tilt = (w_t * ret.fillna(0)).sum(axis=1)
    rets = pd.DataFrame({"Equal weight": r_eq, "Political-risk tilt": r_tilt}).iloc[kwargs.get("lookback", 3) + 1:]
    active = rets["Political-risk tilt"] - rets["Equal weight"]
    m = pd.DataFrame({k: _metrics(v) for k, v in rets.items()}).T
    m.loc["Political-risk tilt", "tracking error"] = active.std() * np.sqrt(12)
    m.loc["Political-risk tilt", "information ratio"] = (active.mean() * 12) / (active.std() * np.sqrt(12))
    m.loc["Political-risk tilt", "avg monthly turnover"] = w_t.diff().abs().sum(axis=1).mean() / 2
    return m, rets, w_t


def stress_test(prices: pd.DataFrame, windows: dict, weights: dict | None = None) -> pd.DataFrame:
    """Cumulative return of each country, the benchmark, and an equal-weight portfolio over political-stress windows."""
    r = np.log(prices).diff()
    rows = {}
    for name, (a, b) in windows.items():
        sl = r.loc[a:b]
        if sl.empty:
            continue
        cum = np.exp(sl.sum()) - 1
        countries = [c for c in prices.columns if c != "BENCH"]
        w = pd.Series(weights) if weights else pd.Series(1 / len(countries), index=countries)
        cum["Equal-weight portfolio"] = (w * cum[countries]).sum()
        rows[name] = cum
    return pd.DataFrame(rows).T
