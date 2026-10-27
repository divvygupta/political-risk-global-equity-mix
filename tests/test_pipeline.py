import numpy as np
import pandas as pd
import pytest

from political_risk import allocation, data, econometrics, events, index


@pytest.fixture(scope="module")
def synth():
    prices, epu, gpr = data.synthetic_dataset(seed=3)
    pri, pca = index.build_pri(epu, gpr)
    panel = econometrics.monthly_panel(prices, pri)
    return prices, epu, gpr, pri, pca, panel


def test_pca_weights_positive_and_normalised(synth):
    pca = synth[4]
    assert (pca > 0).all()
    assert pca.abs().sum() == pytest.approx(1.0)


def test_real_time_index_has_no_look_ahead(synth):
    """Appending future data must not change any past value of pri_rt."""
    _, epu, gpr, pri, _, _ = synth
    cutoff = pd.Timestamp("2016-12-01")
    pri_cut, _ = index.build_pri(epu[epu.date <= cutoff], gpr[gpr.date <= cutoff])
    a = pri_cut["pri_rt"].dropna()
    b = pri.loc[a.index, "pri_rt"]
    # PCA weights are a full-sample estimate; rescaling by them is the only allowed difference.
    corr = np.corrcoef(a, b)[0, 1]
    assert corr > 0.999


def test_tilt_weights_sum_to_one_and_use_lagged_signal(synth):
    panel = synth[5]
    pri_rt = panel["pri_rt"].unstack("country")
    w = allocation.tilt_weights(pri_rt)
    assert np.allclose(w.sum(axis=1), 1.0)
    # Changing the final month's PRI must not change that month's weights.
    shocked = pri_rt.copy()
    shocked.iloc[-1] = shocked.iloc[-1][::-1].values
    w2 = allocation.tilt_weights(shocked)
    pd.testing.assert_series_equal(w.iloc[-1], w2.iloc[-1])


def test_local_projection_recovers_planted_effect(synth):
    lp = econometrics.local_projections(synth[5], horizons=3)
    r = lp[(lp.outcome == "xret") & (lp.h == 3)].iloc[0]
    assert r.beta < 0 and r.pval < 0.05
    assert r.beta == pytest.approx(-0.02, abs=0.01)


def test_event_study_detects_planted_event_returns():
    prices, _, _ = data.synthetic_dataset(seed=5)
    per_event, summary, _ = events.event_study(prices)
    assert len(per_event) >= 25
    assert summary.loc["All events", "mean CAR [-1,+1]"] == pytest.approx(-0.02, abs=0.01)


def test_event_study_null_when_no_event_effect():
    rng = np.random.default_rng(0)
    days = pd.bdate_range("2008-01-01", "2025-06-30")
    mkt = rng.normal(0, 0.01, len(days))
    prices = pd.DataFrame({"BENCH": 100 * np.exp(np.cumsum(mkt))}, index=days)
    for c in ["USA", "GBR", "DEU", "JPN", "FRA", "CAN", "AUS", "IND", "BRA", "ZAF"]:
        prices[c] = 100 * np.exp(np.cumsum(mkt + rng.normal(0, 0.008, len(days))))
    _, summary, _ = events.event_study(prices)
    assert abs(summary.loc["All events", "mean CAR [0,+5]"]) < 0.01


def test_panel_var_shapes(synth):
    var = econometrics.panel_var(synth[5], p=2, horizons=6, n_boot=20)
    assert var["irf"].shape == (7, 3, 3)
    assert (var["lo"] <= var["hi"]).all()


# --- Scenarios -------------------------------------------------------------------------
from political_risk import scenarios  # noqa: E402


def test_scenario_shocks_non_negative(synth):
    shocks = scenarios.scenario_shocks(synth[3])
    assert (shocks.values >= 0).all()
    assert shocks.loc["Emerging-market governance shock"].drop(["BRA", "ZAF"]).eq(0).all()


def test_cad_decomposition_adds_up(synth):
    prices = synth[0]
    fx = data.synthetic_fx(prices.index)
    a = scenarios.analogue_outcomes(prices, fx)
    total = np.log1p(a["local equity"]) + np.log1p(a["currency vs CAD"])
    assert np.allclose(total, np.log1p(a["CAD-investor return"]))
    can = a[a.country == "CAN"]
    assert np.allclose(can["currency vs CAD"], 0)


def test_zero_shock_leaves_var_unchanged(synth):
    prices, panel = synth[0], synth[5]
    fx = data.synthetic_fx(prices.index)
    var = econometrics.panel_var(panel, p=1, horizons=3, n_boot=5)
    zero = pd.DataFrame(0.0, index=["none"], columns=prices.columns.drop("BENCH"))
    _, port = scenarios.portfolio_risk(prices, fx, zero, var)
    assert port.loc["none", "VaR increase"] == pytest.approx(0, abs=1e-12)
    big = zero + 3
    _, port2 = scenarios.portfolio_risk(prices, fx, big.rename(index={"none": "big"}), var)
    assert port2.loc["big", "VaR increase"] > 0


# --- Election surprises, leader exits, risk taxonomy, themes -----------------------------------
from political_risk import config, surprises  # noqa: E402


def _null_market(seed=0, end="2026-10-30"):
    """Markets with no political effects at all: country = benchmark + independent noise."""
    rng = np.random.default_rng(seed)
    days = pd.bdate_range("2008-01-01", end)
    mkt = rng.normal(0, 0.01, len(days))
    prices = pd.DataFrame({"BENCH": 100 * np.exp(np.cumsum(mkt))}, index=days)
    fx = pd.DataFrame(index=days)
    for c in config.COUNTRIES:
        prices[c] = 100 * np.exp(np.cumsum(mkt + rng.normal(0, 0.008, len(days))))
        fx[c] = 1.0 if c == "USA" else np.exp(np.cumsum(rng.normal(0, 0.005, len(days))))
    return prices, fx


def _jump(df, country, date, size):
    """Permanent log jump of ``size`` in one column from the first trading day on or after ``date``."""
    pos = df.index.searchsorted(pd.Timestamp(date))
    df.iloc[pos:, df.columns.get_loc(country)] *= np.exp(size)


def test_election_study_recovers_planted_surprise_moves():
    prices, fx = _null_market(1)
    for e in config.ELECTIONS:
        if e.surprise in surprises.SURPRISES:
            _jump(prices, e.country, e.date, -0.06)
            if e.country != "USA":
                _jump(fx, e.country, e.date, 0.04)  # 4% more local currency per dollar = weaker currency
    per, by_class, tests, _ = surprises.election_study(prices, fx)
    assert len(per) == len(config.ELECTIONS)
    up = per[per.surprise.isin(surprises.SURPRISES)]
    assert up["CAR [0,+1]"].mean() == pytest.approx(-0.06, abs=0.01)
    assert (up["FX [0,+1]"].dropna() < 0).all()  # a weaker currency shows as a negative move
    assert by_class.loc["As expected", "mean |equity move|"] < 0.02
    assert tests.loc["Equity: surprise vs. as expected", "welch p"] < 0.01


def test_no_surprise_effect_in_null_market():
    prices, fx = _null_market(2)
    _, _, tests, _ = surprises.election_study(prices, fx)
    assert tests.loc["Equity: surprise vs. as expected", "welch p"] > 0.01


def test_taxonomy_counts_each_market_day_once_and_uses_three_classes():
    prices, fx = _null_market(3)
    per, summary, (mean, se) = surprises.taxonomy_study(prices, fx)
    assert not per.duplicated(["country", "date"]).any()
    assert set(per["risk class"]) <= {surprises.EXPECTED, surprises.SURPRISE, surprises.EXOGENOUS}
    # Turnbull's ouster and Abe's resignation are both in EVENTS and LEADER_EXITS but count once.
    for country, date in [("AUS", "2018-08-24"), ("JPN", "2020-08-28")]:
        assert ((per.country == country) & (per.date == pd.Timestamp(date).date())).sum() == 1
    assert summary["n"].sum() == len(per)
    assert (mean.loc[1] > 0).all()  # each event is signed so that its day 0 to +1 move is positive


def test_thematic_relative_return_matches_prices():
    prices, fx = _null_market(4)
    th = config.THEMES[3]  # Brexit negotiations, GBR
    out, paths = surprises.thematic_study(prices, fx, themes=[th])
    rel = np.log(prices["GBR"]) - np.log(prices["BENCH"])
    a = rel.loc[: pd.Timestamp(th.start) - pd.Timedelta(days=1)].iloc[-1]
    b = rel.loc[: pd.Timestamp(th.end)].iloc[-1]
    assert out.loc[0, "relative return"] == pytest.approx(np.expm1(b - a))
    assert paths[(th.name, "GBR")].iloc[-1] == pytest.approx(out.loc[0, "relative return"])
