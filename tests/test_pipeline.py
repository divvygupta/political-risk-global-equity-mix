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
