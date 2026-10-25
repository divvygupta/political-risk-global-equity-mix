"""Monthly panel construction, fixed-effects panel VAR, and panel local projections."""

from __future__ import annotations

import numpy as np
import pandas as pd


# --- Monthly panel ---------------------------------------------------------------------
def monthly_panel(prices: pd.DataFrame, pri: pd.DataFrame) -> pd.DataFrame:
    """Country-month panel: excess return vs the global benchmark, realised volatility, PRI.

    - ``ret``: monthly log return of the country ETF (USD)
    - ``xret``: log return minus the benchmark's log return (country-specific performance)
    - ``rvol``: annualised realised volatility of daily returns within the month
    - ``log_rvol``: log of ``rvol``, the volatility variable used in the models
    """
    logp = np.log(prices)
    daily = logp.diff()
    month_end = logp.resample("ME").last()
    mret = month_end.diff()
    rvol = daily.resample("ME").std() * np.sqrt(252)
    mret.index = mret.index.to_period("M").to_timestamp()
    rvol.index = rvol.index.to_period("M").to_timestamp()

    rows = []
    for c in prices.columns.drop("BENCH"):
        d = pd.DataFrame({
            "ret": mret[c],
            "xret": mret[c] - mret["BENCH"],
            "rvol": rvol[c],
        })
        d["log_rvol"] = np.log(d["rvol"])
        d["country"] = c
        rows.append(d.reset_index(names="date"))
    panel = pd.concat(rows).set_index(["country", "date"]).sort_index()
    panel = panel.join(pri[["pri", "pri_rt", "pri_shock"]], how="inner")
    return panel.dropna(subset=["xret", "log_rvol", "pri"])


# --- Fixed-effects panel VAR -----------------------------------------------------------------
def _lagged_design(panel: pd.DataFrame, cols: list[str], p: int):
    Y, X, groups = [], [], []
    for c, g in panel.groupby(level="country"):
        g = g[cols].dropna()
        if len(g) <= p + 12:
            continue
        lags = [g.shift(k).add_suffix(f"_L{k}") for k in range(1, p + 1)]
        z = pd.concat([g] + lags, axis=1).dropna()
        y = z[cols]
        x = z.drop(columns=cols)
        # Country fixed effects: demean within country.
        Y.append((y - y.mean()).values)
        X.append((x - x.mean()).values)
        groups += [c] * len(z)
    return np.vstack(Y), np.vstack(X), np.array(groups)


def _fit_var(Y, X, k, p):
    B, *_ = np.linalg.lstsq(X, Y, rcond=None)
    resid = Y - X @ B
    sigma = resid.T @ resid / (len(Y) - X.shape[1])
    A = [B[(j * k):((j + 1) * k), :].T for j in range(p)]  # A[j][i, m]: effect of var m lag j+1 on var i
    return A, sigma, resid


def _irf(A, sigma, horizons):
    k = sigma.shape[0]
    p = len(A)
    P = np.linalg.cholesky(sigma)  # PRI shock ordered first
    comp = np.zeros((k * p, k * p))
    comp[:k, :] = np.hstack(A)
    if p > 1:
        comp[k:, :-k] = np.eye(k * (p - 1))
    out = np.zeros((horizons + 1, k, k))
    M = np.eye(k * p)
    for h in range(horizons + 1):
        out[h] = M[:k, :k] @ P
        M = comp @ M
    return out  # out[h, response, shock]


def select_lags(panel, cols, max_p=6):
    """Choose lag length by BIC on a common sample."""
    best = None
    for p in range(1, max_p + 1):
        Y, X, _ = _lagged_design(panel, cols, max_p)
        Xp = X[:, : len(cols) * p]
        _, sigma, _ = _fit_var(Y, Xp, len(cols), p)
        n = len(Y)
        bic = np.log(np.linalg.det(sigma)) + np.log(n) * (len(cols) ** 2 * p) / n
        if best is None or bic < best[1]:
            best = (p, bic)
    return best[0]


def panel_var(panel, cols=("pri_shock", "xret", "log_rvol"), p=None, horizons=12, n_boot=500, seed=0):
    """Fixed-effects panel VAR with Cholesky IRFs and a country-cluster bootstrap.

    Lags are built within each country, so no observation is lagged across a
    country boundary, a flaw of pooled VARs on stacked data. Political risk is
    ordered first: a political-risk surprise can move markets within the month,
    but not the reverse.
    """
    cols = list(cols)
    p = p or select_lags(panel, cols)
    Y, X, groups = _lagged_design(panel, cols, p)
    A, sigma, _ = _fit_var(Y, X, len(cols), p)
    base = _irf(A, sigma, horizons)

    rng = np.random.default_rng(seed)
    countries = np.unique(groups)
    draws = []
    for _ in range(n_boot):
        pick = rng.choice(countries, size=len(countries), replace=True)
        idx = np.concatenate([np.where(groups == c)[0] for c in pick])
        try:
            Ab, sb, _ = _fit_var(Y[idx], X[idx], len(cols), p)
            draws.append(_irf(Ab, sb, horizons))
        except np.linalg.LinAlgError:
            continue
    draws = np.array(draws)
    lo, hi = np.percentile(draws, [5, 95], axis=0)
    return {"p": p, "cols": cols, "irf": base, "lo": lo, "hi": hi, "n_obs": len(Y)}


# --- Panel local projections ------------------------------------------------------------------
def local_projections(panel, shock="pri_shock", outcomes=("xret", "log_rvol"), horizons=12, n_lags=2):
    """Jordà local projections with country and month fixed effects.

    For each horizon h, regress the outcome at t+h (cumulative for returns) on
    the political-risk shock at t, controlling for lags of the outcome and the
    shock. Month fixed effects absorb global shocks, so the estimate is the
    effect of a country's own political-risk surprise relative to other
    countries in the same month. Standard errors are Driscoll-Kraay, robust to
    cross-country correlation and serial correlation.
    """
    from linearmodels.panel import PanelOLS

    results = []
    for y in outcomes:
        for h in range(horizons + 1):
            rows = []
            for c, g in panel.groupby(level="country"):
                g = g.droplevel("country").copy()
                if y == "xret":
                    g["lhs"] = sum(g[y].shift(-j) for j in range(h + 1))  # cumulative t..t+h
                else:
                    g["lhs"] = g[y].shift(-h)
                for k in range(1, n_lags + 1):
                    g[f"{y}_L{k}"] = g[y].shift(k)
                    g[f"{shock}_L{k}"] = g[shock].shift(k)
                g["country"] = c
                rows.append(g.reset_index())
            d = pd.concat(rows).set_index(["country", "date"]).dropna(
                subset=["lhs", shock] + [f"{y}_L{k}" for k in range(1, n_lags + 1)]
                + [f"{shock}_L{k}" for k in range(1, n_lags + 1)])
            exog = d[[shock] + [f"{y}_L{k}" for k in range(1, n_lags + 1)] + [f"{shock}_L{k}" for k in range(1, n_lags + 1)]]
            res = PanelOLS(d["lhs"], exog, entity_effects=True, time_effects=True).fit(
                cov_type="kernel", kernel="bartlett", bandwidth=h + 1)
            results.append({"outcome": y, "h": h, "beta": res.params[shock], "se": res.std_errors[shock],
                            "pval": res.pvalues[shock], "nobs": res.nobs})
    out = pd.DataFrame(results)
    out["lo90"] = out["beta"] - 1.645 * out["se"]
    out["hi90"] = out["beta"] + 1.645 * out["se"]
    return out
