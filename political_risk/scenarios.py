"""Forward-looking geopolitical scenarios: market volatility, portfolio risk, and currency effects.

Each scenario is calibrated to history. A country's political-risk shock is its
largest surprise in the scenario's analogue months, so the shocks reflect how
risk actually spread across countries in a comparable episode rather than
assumptions. The estimated panel VAR then turns each shock into a projected
path for that country's volatility. Holding correlations fixed, the projected
volatilities give the change in a portfolio's value at risk and the cut in
exposure needed to keep risk within its budget.

Separately, the analogue's daily window shows what markets actually did,
splitting each market's return for a Canadian-dollar investor into its local
equity move and its currency move against the Canadian dollar.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .config import SCENARIOS, Scenario

Z95 = 1.645  # one-sided 95% normal quantile
DAYS_PER_MONTH = 21


def _months_for(sc: Scenario, country: str) -> list[str]:
    return sc.months.get(country, sc.months.get("*", []))


def _window_for(sc: Scenario, country: str):
    return sc.windows.get(country, sc.windows.get("*"))


def scenario_shocks(pri: pd.DataFrame, scenarios=SCENARIOS) -> pd.DataFrame:
    """Political-risk shock (in standard deviations) by scenario and country.

    The shock is a country's largest ``pri_shock`` in the analogue months, floored at zero:
    a scenario raises risk, it does not lower it.
    """
    shock = pri["pri_shock"].unstack("country")
    shock.index = shock.index.to_period("M")
    out = {}
    for sc in scenarios:
        row = {}
        for c in shock.columns:
            months = [pd.Period(m, "M") for m in _months_for(sc, c)]
            vals = shock.loc[shock.index.isin(months), c].dropna()
            row[c] = max(vals.max(), 0.0) if len(vals) else 0.0
        out[sc.name] = row
    return pd.DataFrame(out).T


def cad_returns(prices: pd.DataFrame, fx: pd.DataFrame) -> pd.DataFrame:
    """Daily log returns for a Canadian-dollar investor (unhedged)."""
    r_usd = np.log(prices.drop(columns="BENCH")).diff()
    usdcad = fx["CAN"].reindex(r_usd.index).ffill()
    return r_usd.add(np.log(usdcad).diff(), axis=0)


def portfolio_risk(prices, fx, shocks: pd.DataFrame, var: dict, weights: pd.Series | None = None,
                   lookback_days: int = 252):
    """Projected volatility by country and the portfolio's one-month 95% value at risk under each scenario.

    The panel VAR gives the response of log volatility to a political-risk shock,
    per standard deviation of the shock's residual. Each country's daily volatility
    is scaled by exp(response x shock); correlations from the last ``lookback_days``
    are held fixed, which understates risk, since correlations tend to rise in crises.

    Returns (country volatility table, portfolio table).
    """
    r = cad_returns(prices, fx).dropna(how="all").iloc[-lookback_days:]
    cov = r.cov()
    countries = list(cov.columns)
    w = (weights if weights is not None else pd.Series(1 / len(countries), index=countries)).reindex(countries).fillna(0)
    sd_resid = np.sqrt(var["sigma"][0, 0])
    resp = var["irf"][:, 2, 0] / sd_resid  # log-vol response per unit of shock, by horizon
    base_vol = np.sqrt(np.diag(cov) * 252)
    base_var = Z95 * np.sqrt(w @ cov.values @ w * DAYS_PER_MONTH)

    vol_rows, port_rows = [], []
    for name, s in shocks.iterrows():
        s = s.reindex(countries).fillna(0).values
        m0 = np.exp(resp[0] * s)  # impact month
        m3 = np.exp(np.outer(resp[:3], s)).mean(axis=0)  # average over months 0-2
        for c, b, a, a3, sh in zip(countries, base_vol, m0, m3, s):
            vol_rows.append({"scenario": name, "country": c, "shock (s.d.)": sh, "current vol": b,
                             "scenario vol": b * a, "vol change": a - 1, "3-month avg vol change": a3 - 1})
        D = np.diag(m0)
        scn_var = Z95 * np.sqrt(w @ (D @ cov.values @ D) @ w * DAYS_PER_MONTH)
        port_rows.append({"scenario": name, "current 1-month VaR (95%)": base_var,
                          "scenario 1-month VaR (95%)": scn_var, "VaR increase": scn_var / base_var - 1,
                          "exposure cut to hold VaR": 1 - base_var / scn_var})
    return pd.DataFrame(vol_rows), pd.DataFrame(port_rows).set_index("scenario")


def analogue_outcomes(prices: pd.DataFrame, fx: pd.DataFrame, scenarios=SCENARIOS) -> pd.DataFrame:
    """What each market did during each scenario's historical analogue, for a Canadian-dollar investor.

    Simple returns over the window. ``local equity`` is the market's return in its own
    currency, ``currency vs CAD`` the change in that currency's value in Canadian dollars;
    in log terms the two add up to the Canadian-dollar return.
    """
    lp = np.log(prices.drop(columns="BENCH"))
    lfx = np.log(fx.reindex(prices.index).ffill())
    rows = []
    for sc in scenarios:
        for c in lp.columns:
            win = _window_for(sc, c)
            if win is None:
                continue
            a, b = pd.Timestamp(win[0]), pd.Timestamp(win[1])
            seg = lp.loc[a:b, c].dropna()
            if len(seg) < 2:
                continue
            t0, t1 = seg.index[0], seg.index[-1]
            usd = seg.iloc[-1] - seg.iloc[0]
            local_fx = lfx.loc[t1, c] - lfx.loc[t0, c]  # change in local per USD
            usdcad = lfx.loc[t1, "CAN"] - lfx.loc[t0, "CAN"]
            local_eq = usd + local_fx
            fx_vs_cad = usdcad - local_fx
            rows.append({"scenario": sc.name, "country": c, "start": t0.date(), "end": t1.date(),
                         "USD return": np.expm1(usd), "local equity": np.expm1(local_eq),
                         "currency vs CAD": np.expm1(fx_vs_cad), "CAD-investor return": np.expm1(local_eq + fx_vs_cad)})
    return pd.DataFrame(rows)
