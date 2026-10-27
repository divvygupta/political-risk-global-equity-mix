"""Election surprises, leadership exits, and the event / exogenous / thematic risk taxonomy.

Three questions:

1. **Election surprises.** Do markets react more when the result goes against the polls? Each
   election is classed against its final polls (Upset, Big miss, As expected, Toss-up) and its
   reaction is measured in equities (abnormal return against ACWI) and in the currency.
2. **Leadership exits.** What happens when a head of government resigns or is pushed out, as with
   the UK's run of prime ministers since 2016?
3. **Risk taxonomy.** Political risks come in three kinds:
   - *Event risks* have a known date and an uncertain outcome (elections, referendums, scheduled
     votes and fiscal statements). Markets can price and hedge them in advance.
   - *Exogenous risks* arrive without warning (invasions, assassinations, sackings, sudden
     resignations, surprise policy announcements).
   - *Thematic risks* build over months or years (trade wars, Brexit, a debt crisis). They show up
     as drift and higher volatility, not as a one-day jump.

Event and exogenous risks use the same market-model event study as ``events.py``. Each reaction
is also standardised by the market's normal daily volatility, so a 2% move in Brazil and a 2% move
in Canada are not treated as equal. Thematic risks are measured over their full window.

Cameron's resignation (24 June 2016) and the collapse of Germany's coalition (6 November 2024) are
left out of the exits because they fell on the same day as the Brexit result and the U.S. election.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats

from .config import ELECTIONS, EVENT_RISK_OVERRIDES, EVENTS, LEADER_EXITS, THEMES

SURPRISE_ORDER = ["Upset", "Big miss", "Toss-up", "As expected"]
SURPRISES = ("Upset", "Big miss")
PRE, POST = 10, 10  # trading days used to measure volatility before and after the news


def _reaction(r: pd.DataFrame, lfx: pd.DataFrame | None, country: str, date: str, est=(-250, -30)) -> dict | None:
    """Market-model reaction of one market to one piece of news.

    ``r`` holds daily log returns (country columns and ``BENCH``); ``lfx`` the log of local currency
    per U.S. dollar, on the same dates. Returns None when there is not enough data around the date.
    """
    if country not in r.columns:
        return None
    s = r[[country, "BENCH"]].dropna()
    pos = s.index.searchsorted(pd.Timestamp(date))
    if pos + est[0] < 0 or pos + POST >= len(s):
        return None
    e = s.iloc[pos + est[0]: pos + est[1]]
    beta, alpha = np.polyfit(e["BENCH"], e[country], 1)
    sd = (e[country] - alpha - beta * e["BENCH"]).std(ddof=2)
    w = s.iloc[pos - PRE: pos + POST + 1]
    ar = pd.Series((w[country] - alpha - beta * w["BENCH"]).values, index=range(-PRE, POST + 1))
    car01, car010 = ar.loc[0:1].sum(), ar.loc[0:POST].sum()
    out = {
        "date": s.index[pos].date(), "beta": beta, "normal daily vol": sd,
        "CAR [0,+1]": car01, "SCAR [0,+1]": car01 / (sd * np.sqrt(2)),
        "CAR [0,+10]": car010,
        "vol before (x normal)": ar.loc[-PRE:-1].std(ddof=1) / sd,
        "vol after (x normal)": ar.loc[1:POST].std(ddof=1) / sd,
        "path": pd.concat([-ar.loc[-PRE:-1][::-1].cumsum()[::-1], ar.loc[0:POST].cumsum()]),
    }
    if lfx is not None and country in lfx.columns:
        f = lfx[country].reindex(s.index).ffill()
        fr = -f.diff()  # + = local currency strengthens against the U.S. dollar
        fsd = fr.iloc[pos + est[0]: pos + est[1]].std(ddof=1)
        move = -(f.iloc[pos + 1] - f.iloc[pos - 1])
        if fsd > 0:
            out["FX [0,+1]"], out["FX z [0,+1]"] = move, move / (fsd * np.sqrt(2))
        else:  # the U.S. dollar against itself
            out["FX [0,+1]"] = out["FX z [0,+1]"] = np.nan
    else:
        out["FX [0,+1]"] = out["FX z [0,+1]"] = np.nan
    return out


def _prep(prices: pd.DataFrame, fx: pd.DataFrame | None):
    r = np.log(prices).diff()
    lfx = np.log(fx.reindex(prices.index).ffill()) if fx is not None else None
    return r, lfx


def _study(prices, fx, items, extra) -> tuple[pd.DataFrame, pd.DataFrame]:
    r, lfx = _prep(prices, fx)
    rows, paths = [], {}
    for it in items:
        res = _reaction(r, lfx, it.country, it.date)
        if res is None:
            continue
        paths[(it.country, str(res["date"]))] = res.pop("path")
        rows.append({"country": it.country, "event": it.name, **extra(it), **res})
    return pd.DataFrame(rows), pd.DataFrame(paths)


def _diff_test(a: pd.Series, b: pd.Series) -> dict:
    a, b = a.dropna(), b.dropna()
    if len(a) < 2 or len(b) < 2:
        return {"diff": np.nan, "welch p": np.nan, "mann-whitney p": np.nan}
    return {"diff": a.mean() - b.mean(), "welch p": stats.ttest_ind(a, b, equal_var=False).pvalue,
            "mann-whitney p": stats.mannwhitneyu(a, b, alternative="two-sided").pvalue}


def election_study(prices: pd.DataFrame, fx: pd.DataFrame | None, elections=ELECTIONS):
    """Reaction to each election, and a comparison of surprises with expected results.

    Returns:
        per_election: reaction of each election's own market (equity and currency)
        by_class: average absolute reaction by surprise class
        tests: surprise (Upset or Big miss) vs. the rest, for absolute standardised reactions
        paths: cumulative abnormal returns from day -10 to +10
    """
    per, paths = _study(prices, fx, elections, lambda e: {"polls": e.polls, "surprise": e.surprise, "source": e.source})
    if per.empty:
        return per, pd.DataFrame(), pd.DataFrame(), paths
    per["|CAR [0,+1]|"] = per["CAR [0,+1]"].abs()
    per["|SCAR [0,+1]|"] = per["SCAR [0,+1]"].abs()
    per["|FX [0,+1]|"] = per["FX [0,+1]"].abs()
    per["|FX z [0,+1]|"] = per["FX z [0,+1]"].abs()
    g = per.groupby("surprise")
    by_class = pd.DataFrame({
        "n": g.size(),
        "mean |equity move|": g["|CAR [0,+1]|"].mean(),
        "mean |equity move| (x normal day)": g["|SCAR [0,+1]|"].mean(),
        "mean |currency move|": g["|FX [0,+1]|"].mean(),
        "mean |currency move| (x normal day)": g["|FX z [0,+1]|"].mean(),
        "share with significant equity move": g["|SCAR [0,+1]|"].apply(lambda s: (s > 1.96).mean()),
        "vol before (x normal)": g["vol before (x normal)"].mean(),
        "vol after (x normal)": g["vol after (x normal)"].mean(),
    }).reindex([c for c in SURPRISE_ORDER if c in g.groups])
    surprise = per["surprise"].isin(SURPRISES)
    expected = per["surprise"] == "As expected"
    tests = pd.DataFrame({
        f"{label}: surprise vs. {base}": _diff_test(per.loc[surprise, col], per.loc[mask, col])
        for label, col in [("Equity", "|SCAR [0,+1]|"), ("Currency", "|FX z [0,+1]|")]
        for base, mask in [("all others", ~surprise), ("as expected", expected)]
    }).T
    return per, by_class, tests, paths


def leader_exit_study(prices: pd.DataFrame, fx: pd.DataFrame | None, exits=LEADER_EXITS):
    """Reaction of each market to its head of government leaving office."""
    per, paths = _study(prices, fx, exits, lambda e: {"scheduled": e.scheduled})
    if not per.empty:
        per["|SCAR [0,+1]|"] = per["SCAR [0,+1]"].abs()
    return per, paths


EXPECTED, SURPRISE, EXOGENOUS = "Event risk: expected outcome", "Event risk: surprise outcome", "Exogenous risk"


def taxonomy_study(prices: pd.DataFrame, fx: pd.DataFrame | None, events=EVENTS, elections=ELECTIONS,
                   exits=LEADER_EXITS):
    """Compare event risks with exogenous risks, across every dated event in the project.

    Elections are event risks, split into surprises (Upset, Big miss) and the rest. Leader exits are
    exogenous unless they came from a scheduled vote. The original events are mapped by type.
    Duplicates (the same market and day) are counted once.

    Returns:
        per_event: one row per event with its class
        summary: average reaction by class
        aligned: average cumulative abnormal return path by class, each event signed so that its
            day 0 to +1 move is positive (shows whether the first move fades or keeps going)
    """
    r, lfx = _prep(prices, fx)
    items = []
    for e in elections:
        items.append((e.country, e.date, e.name, "Election", SURPRISE if e.surprise in SURPRISES else EXPECTED))
    for x in exits:
        items.append((x.country, x.date, x.name, "Leader exit", EXPECTED if x.scheduled else EXOGENOUS))
    for e in events:
        if e.kind == "election":  # already covered, with a surprise class, by ``elections``
            continue
        cls = EVENT_RISK_OVERRIDES.get((e.country, e.date), EXOGENOUS)
        items.append((e.country, e.date, e.name, e.kind.replace("_", " ").capitalize(), cls))
    rows, aligned, seen = [], {}, set()
    for country, date, name, source, cls in items:
        res = _reaction(r, lfx, country, date)
        if res is None or cls is None:
            continue
        key = (country, res["date"])
        if key in seen:
            continue
        seen.add(key)
        path = res.pop("path")
        sign = np.sign(res["CAR [0,+1]"]) or 1.0
        aligned[key] = (cls, path * sign)
        rows.append({"country": country, "event": name, "source": source, "risk class": cls, **res})
    per = pd.DataFrame(rows)
    per["|SCAR [0,+1]|"] = per["SCAR [0,+1]"].abs()
    per["|CAR [0,+1]|"] = per["CAR [0,+1]"].abs()
    # Share of the first two days' move still there after ten days (1 = no fade, 0 = fully reversed).
    per["kept after 10 days"] = (per["CAR [0,+10]"] / per["CAR [0,+1]"]).where(per["|SCAR [0,+1]|"] > 1)
    g = per.groupby("risk class")
    order = [EXPECTED, SURPRISE, EXOGENOUS]
    summary = pd.DataFrame({
        "n": g.size(),
        "mean |equity move|": g["|CAR [0,+1]|"].mean(),
        "mean |equity move| (x normal day)": g["|SCAR [0,+1]|"].mean(),
        "mean signed equity move": g["CAR [0,+1]"].mean(),
        "share with significant move": g["|SCAR [0,+1]|"].apply(lambda s: (s > 1.96).mean()),
        "vol before (x normal)": g["vol before (x normal)"].mean(),
        "vol after (x normal)": g["vol after (x normal)"].mean(),
        "median share of move kept after 10 days": g["kept after 10 days"].median(),
    }).reindex([c for c in order if c in g.groups])
    paths = pd.DataFrame({k: v[1] for k, v in aligned.items()})
    classes = pd.Series({k: v[0] for k, v in aligned.items()})
    aligned_mean = pd.DataFrame({c: paths.loc[:, classes[classes == c].index].mean(axis=1) for c in summary.index})
    aligned_se = pd.DataFrame({c: paths.loc[:, classes[classes == c].index].std(axis=1)
                               / np.sqrt((classes == c).sum()) for c in summary.index})
    summary.attrs["exogenous vs expected"] = _diff_test(per.loc[per["risk class"] == EXOGENOUS, "|SCAR [0,+1]|"],
                                                        per.loc[per["risk class"] == EXPECTED, "|SCAR [0,+1]|"])
    summary.attrs["surprise vs expected"] = _diff_test(per.loc[per["risk class"] == SURPRISE, "|SCAR [0,+1]|"],
                                                       per.loc[per["risk class"] == EXPECTED, "|SCAR [0,+1]|"])
    return per, summary, (aligned_mean, aligned_se)


def thematic_study(prices: pd.DataFrame, fx: pd.DataFrame | None, pri: pd.DataFrame | None = None, themes=THEMES,
                   lookback_days: int = 504):
    """How each slow-moving theme showed up in its most exposed markets.

    For each theme and market, over the theme window:
        relative return: performance against ACWI, in U.S. dollars
        currency: change in the local currency against the U.S. dollar (+ = stronger)
        excess vol (x prior): annualised volatility of daily returns relative to ACWI, divided by
            the same measure over the two years before the theme began
        max relative drawdown: deepest fall of performance against ACWI
        first-month share: share of the full-window relative move that happened in the first 21 days
        avg PRI: the country's average political-risk index over the window (full-sample z-score)

    Also returns each theme-market's relative-performance path, indexed by trading day.
    """
    lp = np.log(prices)
    rel = lp.drop(columns="BENCH").sub(lp["BENCH"], axis=0)
    xr = rel.diff()
    lfx = np.log(fx.reindex(prices.index).ffill()) if fx is not None else None
    pri_w = pri["pri"].unstack("country") if pri is not None else None
    rows, paths = [], {}
    for th in themes:
        a = pd.Timestamp(th.start)
        b = pd.Timestamp(th.end) if th.end else rel.index[-1]
        for c in th.countries:
            seg = rel.loc[a:b, c].dropna()
            if len(seg) < 42:
                continue
            base = rel[c].loc[:a].dropna()
            if len(base) < 2:
                continue
            start_level = base.iloc[-2] if base.index[-1] == seg.index[0] else base.iloc[-1]
            path = seg - start_level
            paths[(th.name, c)] = pd.Series(np.expm1(path.values), index=range(1, len(path) + 1))
            prior = xr[c].loc[:a].dropna().iloc[-lookback_days:-1]
            during = xr[c].loc[a:b].dropna()
            total = path.iloc[-1]
            first = path.iloc[min(20, len(path) - 1)]
            row = {
                "theme": th.name, "country": c, "start": seg.index[0].date(), "end": seg.index[-1].date(),
                "trading days": len(seg),
                "relative return": np.expm1(total),
                "relative return, annualised": np.expm1(total * 252 / len(seg)),
                "excess vol (x prior)": during.std() / prior.std() if len(prior) > 60 else np.nan,
                "max relative drawdown": np.expm1((path - path.cummax().clip(lower=0)).min()),
                "first-month share": first / total if abs(total) > 0.02 else np.nan,
            }
            if lfx is not None and c in lfx.columns:
                f = lfx[c].loc[:b].dropna()
                f0 = lfx[c].loc[:a - pd.Timedelta(days=1)].dropna()
                row["currency"] = np.expm1(-(f.iloc[-1] - f0.iloc[-1])) if len(f0) else np.nan
            else:
                row["currency"] = np.nan
            if pri_w is not None and c in pri_w.columns:
                row["avg PRI"] = pri_w[c].loc[a.to_period("M").to_timestamp():b].mean()
            rows.append(row)
    return pd.DataFrame(rows), pd.DataFrame(paths)
