"""Monthly Political Risk Index (PRI) built from EPU and GPR."""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.decomposition import PCA


def _within_z(s: pd.Series, expanding: bool, min_periods: int = 36) -> pd.Series:
    if expanding:
        mu = s.expanding(min_periods).mean()
        sd = s.expanding(min_periods).std()
    else:
        mu, sd = s.mean(), s.std()
    return (s - mu) / sd


def build_pri(epu: pd.DataFrame, gpr: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series]:
    """Combine log EPU and log GPR into a monthly Political Risk Index per country.

    Each component is standardised within country. Weights come from the first
    principal component of the pooled standardised components, so the index
    captures the common political-risk signal. Two versions are returned:

    - ``pri``: full-sample standardisation, for econometric analysis
    - ``pri_rt``: real-time (expanding-window) standardisation, with no look-ahead,
      for the portfolio backtest

    ``pri_shock`` is the innovation from a country-level AR(1) of ``pri``:
    the surprise component of political risk.

    Returns (panel DataFrame indexed by [country, date], PCA weights).
    """
    df = pd.merge(epu, gpr, on=["date", "country"], how="outer").sort_values(["country", "date"])
    # Keep the index's composition stable: where a country has EPU, stop at its last EPU month
    # rather than letting the final months silently fall back to GPR alone.
    last_epu = epu.groupby("country")["date"].max()
    df = df[df["date"] <= df["country"].map(last_epu).fillna(epu["date"].max())]
    df["log_epu"] = np.log(df["epu"])
    df["log_gpr"] = np.log(df["gpr"])
    comps = ["log_epu", "log_gpr"]

    for c in comps:
        df[c + "_z"] = df.groupby("country")[c].transform(lambda s: _within_z(s, expanding=False))
        df[c + "_zrt"] = df.groupby("country")[c].transform(lambda s: _within_z(s, expanding=True))

    both = df[[c + "_z" for c in comps]].dropna()
    pca = PCA(n_components=1).fit(both.values)
    w = pca.components_[0]
    w = w * np.sign(w.sum())  # higher index = higher risk
    w = w / np.abs(w).sum()
    weights = pd.Series(w, index=comps, name="pca_weight")

    def combine(suffix: str) -> pd.Series:
        z = df[[c + suffix for c in comps]]
        num = (z * w).sum(axis=1, min_count=1)
        den = z.notna().mul(np.abs(w)).sum(axis=1)  # countries with only GPR (e.g. ZAF) use GPR alone
        return num / den.replace(0, np.nan)

    df["pri"] = combine("_z")
    df["pri_rt"] = combine("_zrt")

    def ar1_innovation(s: pd.Series) -> pd.Series:
        lag = s.shift(1)
        ok = s.notna() & lag.notna()
        rho = np.polyfit(lag[ok], s[ok], 1)[0] if ok.sum() > 24 else 0.0
        return s - rho * lag

    df["pri_shock"] = df.groupby("country")["pri"].transform(ar1_innovation)
    df["pri_shock"] = df.groupby("country")["pri_shock"].transform(lambda s: (s - s.mean()) / s.std())
    out = df.set_index(["country", "date"])[["epu", "gpr", "pri", "pri_rt", "pri_shock"]]
    return out, weights
