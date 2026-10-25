"""Data loading: market prices, EPU, and GPR, with local caching and a synthetic mode."""

from __future__ import annotations

import os

import numpy as np
import pandas as pd

from . import config


def _cache_path(name: str) -> str:
    os.makedirs(config.CACHE_DIR, exist_ok=True)
    return os.path.join(config.CACHE_DIR, name)


# --- Market data -----------------------------------------------------------------
def load_prices(start: str = config.START, end: str | None = config.END, refresh: bool = False) -> pd.DataFrame:
    """Daily adjusted close for the country ETFs and the benchmark, columns = country codes + 'BENCH'."""
    path = _cache_path("prices.csv")
    if os.path.exists(path) and not refresh:
        return pd.read_csv(path, index_col=0, parse_dates=True)

    import yfinance as yf

    tickers = {code: spec[1] for code, spec in config.COUNTRIES.items()}
    tickers["BENCH"] = config.BENCHMARK
    raw = yf.download(list(tickers.values()), start=start, end=end, auto_adjust=True, progress=False)["Close"]
    prices = raw.rename(columns={v: k for k, v in tickers.items()})[list(tickers.keys())]
    prices = prices.dropna(how="all")
    prices.to_csv(path)
    return prices


def load_fx(start: str = config.START, end: str | None = config.END, refresh: bool = False) -> pd.DataFrame:
    """Daily exchange rates, local currency per U.S. dollar; columns are country codes (USA = 1)."""
    path = _cache_path("fx.csv")
    if os.path.exists(path) and not refresh:
        return pd.read_csv(path, index_col=0, parse_dates=True)

    import yfinance as yf

    tickers = sorted(set(config.FX_TICKERS.values()))
    raw = yf.download(tickers, start=start, end=end, auto_adjust=False, progress=False)["Close"]
    fx = pd.DataFrame({c: raw[t] for c, t in config.FX_TICKERS.items()})
    fx["USA"] = 1.0
    fx = fx[list(config.COUNTRIES)].dropna(how="all")
    fx.to_csv(path)
    return fx


# --- Political-risk data ------------------------------------------------------------
def _read_source(url: str, local_name: str, **kwargs) -> pd.DataFrame:
    """Read a source spreadsheet: a manually saved copy in data/raw first, then a CSV cache, then the URL."""
    local = os.path.join(config.RAW_DIR, local_name)
    if os.path.exists(local):
        return pd.read_excel(local, **kwargs)
    cached = os.path.join(config.RAW_DIR, os.path.splitext(local_name)[0] + ".csv")
    if os.path.exists(cached):
        return pd.read_csv(cached)
    df = pd.read_excel(url, **kwargs)
    os.makedirs(config.RAW_DIR, exist_ok=True)
    df.to_csv(cached, index=False)  # pandas cannot write legacy .xls, so cache as CSV
    return df


def load_epu() -> pd.DataFrame:
    """Monthly Economic Policy Uncertainty by country (long format: date, country, epu)."""
    df = _read_source(config.EPU_URL, "All_Country_Data.xlsx")
    df = df[pd.to_numeric(df["Year"], errors="coerce").notna()].copy()
    df["date"] = pd.to_datetime(dict(year=df["Year"].astype(int), month=df["Month"].astype(int), day=1))
    rows = []
    for code, spec in config.COUNTRIES.items():
        col = spec[3]
        if col and col in df.columns:
            rows.append(pd.DataFrame({"date": df["date"], "country": code, "epu": pd.to_numeric(df[col], errors="coerce")}))
    return pd.concat(rows, ignore_index=True).dropna()


def load_gpr() -> pd.DataFrame:
    """Monthly country-specific Geopolitical Risk index (long format: date, country, gpr)."""
    df = _read_source(config.GPR_URL, "data_gpr_export.xls").copy()
    df["date"] = pd.to_datetime(df["month"]).dt.to_period("M").dt.to_timestamp()
    rows = []
    for code, spec in config.COUNTRIES.items():
        col = spec[4]
        if col in df.columns:
            rows.append(pd.DataFrame({"date": df["date"], "country": code, "gpr": pd.to_numeric(df[col], errors="coerce")}))
    return pd.concat(rows, ignore_index=True).dropna()


# --- Synthetic data (for tests and offline demos) ----------------------------------------
def synthetic_dataset(seed: int = 7, start: str = "2008-04-01", end: str = "2025-06-30",
                      pri_return_effect: float = -0.02):
    """Generate prices, EPU and GPR with a known political-risk effect built in.

    A one-standard-deviation political-risk shock lowers the country's next-month
    excess return by `pri_return_effect` and raises its volatility; listed events
    carry a negative abnormal return. Used to check that the pipeline recovers
    effects of the right sign. Never used to report results.
    """
    rng = np.random.default_rng(seed)
    days = pd.bdate_range(start, end)
    months = pd.date_range(days[0].to_period("M").to_timestamp(), days[-1], freq="MS")
    codes = list(config.COUNTRIES)

    # Monthly political-risk factor per country: persistent AR(1) with occasional spikes.
    pri = pd.DataFrame(index=months, columns=codes, dtype=float)
    for c in codes:
        x = np.zeros(len(months))
        for t in range(1, len(months)):
            x[t] = 0.85 * x[t - 1] + rng.normal(0, 1) + (rng.random() < 0.03) * rng.normal(3, 1)
        pri[c] = x
    shock = pri - 0.85 * pri.shift(1)
    shock = (shock - shock.mean()) / shock.std()

    epu = pd.concat([pd.DataFrame({"date": months, "country": c,
                                   "epu": np.exp(4.5 + 0.3 * pri[c].values + rng.normal(0, 0.15, len(months)))})
                     for c in codes if config.COUNTRIES[c][3]], ignore_index=True)
    gpr = pd.concat([pd.DataFrame({"date": months, "country": c,
                                   "gpr": np.exp(0.0 + 0.3 * pri[c].values + rng.normal(0, 0.2, len(months)))})
                     for c in codes], ignore_index=True)

    # Daily returns: market factor + country beta + political-risk effects.
    mkt = rng.normal(0.0003, 0.011, len(days))
    month_of_day = days.to_period("M").to_timestamp()
    prices = {"BENCH": 100 * np.exp(np.cumsum(mkt))}
    event_days = {(e.country, pd.Timestamp(e.date)) for e in config.EVENTS}
    for c in codes:
        beta = rng.uniform(0.8, 1.3)
        lag_shock = shock[c].shift(1).reindex(month_of_day).fillna(0).values
        vol = 0.008 * np.exp(0.15 * np.clip(lag_shock, -2, 4))
        drift = pri_return_effect / 21 * lag_shock
        r = beta * mkt + drift + rng.normal(0, 1, len(days)) * vol
        for i, d in enumerate(days):
            if (c, d) in event_days:
                r[i] -= 0.02
        prices[c] = 100 * np.exp(np.cumsum(r))
    prices = pd.DataFrame(prices, index=days)[codes + ["BENCH"]]
    return prices, epu, gpr


def synthetic_fx(index: pd.DatetimeIndex, seed: int = 11) -> pd.DataFrame:
    """Random-walk exchange rates (local per USD) for offline runs and tests."""
    rng = np.random.default_rng(seed)
    fx = {c: np.exp(np.cumsum(rng.normal(0, 0.005, len(index)))) for c in config.COUNTRIES}
    fx["USA"] = np.ones(len(index))
    return pd.DataFrame(fx, index=index)
