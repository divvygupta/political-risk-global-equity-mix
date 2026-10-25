"""Event study: market-model abnormal returns against a global benchmark."""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats

from .config import EVENTS

WINDOWS = {"[-1,+1]": (-1, 1), "[0,+5]": (0, 5), "[0,+10]": (0, 10)}


def event_study(prices: pd.DataFrame, events=EVENTS, est=(-250, -30), windows=WINDOWS) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Estimate abnormal returns around each event.

    Normal returns come from a market model, fitted on the estimation window,
    of the country ETF's daily log return on the global benchmark's. This
    removes moves common to all markets, which the original mean-adjusted
    model did not.

    Returns:
        per_event: CAR, its own t-stat, and standardised CAR for each window and event
        summary: for each window, the mean CAR across events with the BMP
            standardised cross-sectional test (Boehmer, Musumeci and Poulsen, 1991),
            overall and by event type
        paths: daily cumulative abnormal returns from -10 to +10, for plotting
    """
    r = np.log(prices).diff()
    rows, paths = [], {}
    for e in events:
        if e.country not in r.columns:
            continue
        s = r[[e.country, "BENCH"]].dropna()
        pos = s.index.searchsorted(pd.Timestamp(e.date))  # first trading day on or after the date
        if pos - abs(est[0]) < 0 or pos + 10 >= len(s):
            continue
        est_slice = s.iloc[pos + est[0]: pos + est[1]]
        beta, alpha = np.polyfit(est_slice["BENCH"], est_slice[e.country], 1)
        resid_sd = (est_slice[e.country] - alpha - beta * est_slice["BENCH"]).std(ddof=2)
        win = s.iloc[pos - 10: pos + 11]
        ar = win[e.country] - alpha - beta * win["BENCH"]
        ar.index = range(-10, 11)
        paths[f"{e.country}: {e.name}"] = ar.loc[-10:].cumsum() - ar.loc[-10:-1].sum()
        row = {"country": e.country, "event": e.name, "kind": e.kind, "date": s.index[pos].date(),
               "beta": beta}
        for label, (a, b) in windows.items():
            car = ar.loc[a:b].sum()
            n = b - a + 1
            t = car / (resid_sd * np.sqrt(n))
            row[f"CAR {label}"] = car
            row[f"t {label}"] = t
            row[f"p {label}"] = 2 * (1 - stats.t.cdf(abs(t), df=len(est_slice) - 2))
            row[f"SCAR {label}"] = t
        rows.append(row)
    per_event = pd.DataFrame(rows)

    def bmp(df):
        out = {}
        for label in windows:
            scar = df[f"SCAR {label}"]
            n = len(scar)
            t = scar.mean() / (scar.std(ddof=1) / np.sqrt(n)) if n > 1 else np.nan
            out[f"mean CAR {label}"] = df[f"CAR {label}"].mean()
            out[f"BMP t {label}"] = t
            out[f"BMP p {label}"] = 2 * (1 - stats.t.cdf(abs(t), df=n - 1)) if n > 1 else np.nan
        out["n_events"] = len(df)
        return pd.Series(out)

    summary = pd.concat({"All events": bmp(per_event)}, axis=1).T
    by_kind = per_event.groupby("kind").apply(bmp)
    summary = pd.concat([summary, by_kind])
    return per_event, summary, pd.DataFrame(paths)
