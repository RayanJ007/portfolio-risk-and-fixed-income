import numpy as np
import pandas as pd
import pytest

from src.risk.engine import (
    tail_risk,
    correlated_shocks,
    parametric_risk,
    risk_contributions,
    scenario_pnl,
)
from tests.fixtures.synthetic import sample_tables


def test_tail_convention_and_fractional_es():
    pnl = -np.arange(1, 11, dtype=float)
    result = tail_risk(pnl, 0.85)
    assert result["var"] == 9
    assert result["es"] == pytest.approx((10 + 0.5 * 9) / 1.5)
    assert tail_risk(pnl, 0.99)["var"] >= tail_risk(pnl, 0.95)["var"]
    assert tail_risk(np.ones(10)) == dict(var=0.0, es=0.0)
    with pytest.raises(ValueError):
        tail_risk([1, np.nan])


def test_covariance_mc_seed_and_correlation():
    covariance = np.array([[0.04, 0.012], [0.012, 0.01]])
    a = correlated_shocks(covariance, 100000, 42)
    assert np.array_equal(a, correlated_shocks(covariance, 100000, 42))
    assert np.corrcoef(a.T)[0, 1] == pytest.approx(0.6, abs=0.015)
    assert np.cov(a.T) == pytest.approx(covariance, rel=0.02)
    with pytest.raises(ValueError, match="positive semidefinite"):
        correlated_shocks([[1, 2], [2, 1]])
    assert np.allclose(correlated_shocks(np.zeros((2, 2))), 0)


def test_parametric_scaling_euler_and_marginal():
    covariance = pd.DataFrame([[0.04, 0.012], [0.012, 0.01]], index=["x", "y"], columns=["x", "y"])
    sensitivities = pd.DataFrame([[1, 0], [0, 1]], index=["A", "B"], columns=["x", "y"])
    q = pd.Series({"A": 100.0, "B": 200.0})
    base = parametric_risk(q, covariance)
    assert parametric_risk(q, 4 * covariance)["var"] == pytest.approx(2 * base["var"])
    assert base["var"] >= parametric_risk(q, covariance, 0.95)["var"]
    parts = risk_contributions(sensitivities, q, covariance)
    assert parts.component_var.sum() == pytest.approx(base["var"])
    h = 0.001
    up = q.copy()
    up["A"] += h
    assert (parametric_risk(up, covariance)["var"] - base["var"]) / h == pytest.approx(
        parts.marginal_var.iloc[0], rel=1e-5
    )
    assert parts.standalone_var.sum() >= parts.component_var.sum()


def test_full_option_repricing_is_nonlinear():
    tables = sample_tables()
    master = tables["security_master"]
    factors = tables["factor_levels"]
    state = factors.loc[factors.date == "2026-08-31"].set_index("factor").level
    kinds = factors.groupby("factor").kind.first().to_dict()
    changes = pd.DataFrame(0.0, index=[0, 1], columns=state.index)
    changes["EQ_US"] = [np.log(0.8), np.log(1.2)]
    pnl = scenario_pnl(master, pd.Series({"US_CALL": 1}), state, changes, kinds, "2026-08-31")
    assert pnl.US_CALL.iloc[0] < 0 < pnl.US_CALL.iloc[1]
    assert pnl.US_CALL.sum() > 0  # convex call under equal-sized up/down spot moves
