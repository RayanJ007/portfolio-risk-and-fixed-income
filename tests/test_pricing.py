import numpy as np
import pytest

from src.pricing.bonds import bond_price, yield_to_maturity, bond_analytics, cash_flows, curve_price
from src.pricing.options import black_scholes, option_greeks

ARGS = ("2026-08-31", "2031-08-31", 0.04, 2, 100)


def test_zero_and_par():
    assert bond_price(0.04, *ARGS) == pytest.approx(100)
    assert bond_price(0.05, ARGS[0], ARGS[1], 0) == pytest.approx(100 / 1.025**10)
    assert curve_price(*ARGS[:3], [1, 10], [0.04, 0.04]) > 0


@pytest.mark.parametrize("y", [-0.02, 0, 0.04, 0.18])
def test_ytm_round_trip(y):
    p = bond_price(y, *ARGS)
    assert yield_to_maturity(p, *ARGS) == pytest.approx(y, abs=1e-10)
    assert bond_price(y + 0.001, *ARGS) < p < bond_price(y - 0.001, *ARGS)


def test_duration_convexity():
    a = bond_analytics(0.05, *ARGS)
    assert a["dv01"] > 0
    assert a["dv01_duration"] == pytest.approx(a["dv01"], rel=1e-6)
    long = bond_analytics(0.05, ARGS[0], "2041-08-31", 0.04)
    assert long["modified_duration"] > a["modified_duration"]
    assert bond_analytics(0.10, *ARGS)["macaulay_duration"] < a["macaulay_duration"]
    change = bond_price(0.07, *ARGS) - a["dirty_price"]
    linear = -a["modified_duration"] * 0.02 * a["dirty_price"]
    quadratic = linear + 0.5 * a["convexity"] * 0.02**2 * a["dirty_price"]
    assert abs(quadratic - change) < abs(linear - change)
    h = 1e-4
    second = (
        bond_price(0.05 + h, *ARGS) - 2 * a["dirty_price"] + bond_price(0.05 - h, *ARGS)
    ) / h**2
    assert second / a["dirty_price"] == pytest.approx(a["convexity"], rel=1e-6)


def test_accrued_eom_and_invalid():
    args = ("2026-10-15", "2031-08-31", 0.04, 2, 100)
    times, flows, accrued = cash_flows(*args)
    assert 0 < accrued < 2
    assert np.all(np.diff(times) > 0)
    dirty, clean = bond_price(0.05, *args), bond_price(0.05, *args, clean=True)
    assert dirty - clean == pytest.approx(accrued)
    assert yield_to_maturity(clean, *args, clean=True) == pytest.approx(0.05)
    assert cash_flows("2026-02-28", "2027-08-31", 0.04)[2] == 0
    with pytest.raises(ValueError):
        bond_price(-2, *args)
    with pytest.raises(ValueError):
        bond_price(0.04, "2032-01-01", "2031-01-01", 0.04)


def test_option_parity_greeks():
    s, k, t, r, v, q = 100, 105, 1.2, 0.03, 0.25, 0.01
    call = black_scholes(s, k, t, r, v, q)
    put = black_scholes(s, k, t, r, v, q, "put")
    assert call - put == pytest.approx(s * np.exp(-q * t) - k * np.exp(-r * t))
    g = option_greeks(s, k, t, r, v, q)
    h = 0.001
    assert g["delta"] == pytest.approx(
        (black_scholes(s + h, k, t, r, v, q) - black_scholes(s - h, k, t, r, v, q)) / (2 * h),
        rel=1e-6,
    )
    assert g["gamma"] == pytest.approx(
        (black_scholes(s + h, k, t, r, v, q) - 2 * call + black_scholes(s - h, k, t, r, v, q))
        / h**2,
        rel=1e-5,
    )
    assert g["vega"] == pytest.approx(
        (black_scholes(s, k, t, r, v + h, q) - black_scholes(s, k, t, r, v - h, q)) / (2 * h),
        rel=1e-5,
    )
    assert g["theta"] == pytest.approx(
        -(black_scholes(s, k, t + h, r, v, q) - black_scholes(s, k, t - h, r, v, q)) / (2 * h),
        rel=1e-5,
    )
    assert black_scholes(100, 90, 0, 0.03, 0.2) == 10
    assert black_scholes(100, 90, 1, 0, 0) == 10
