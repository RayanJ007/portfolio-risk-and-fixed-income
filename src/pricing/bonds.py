"""Regular fixed-rate bonds. Yields are decimals, prices are currency per face unit."""

import numpy as np
import pandas as pd
from scipy.optimize import brentq


def cash_flows(settlement, maturity, coupon_rate, frequency=2, face=100):
    """Actual/Actual coupon-period timing; settlement on coupon date excludes that coupon."""
    settlement, maturity = pd.Timestamp(settlement), pd.Timestamp(maturity)
    if pd.isna(settlement) or pd.isna(maturity) or settlement >= maturity:
        raise ValueError("Settlement must precede maturity")
    if (
        frequency not in (1, 2, 4, 12)
        or not np.isfinite([coupon_rate, face]).all()
        or coupon_rate < 0
        or face <= 0
    ):
        raise ValueError("Invalid bond terms")
    months = 12 // frequency
    dates = []
    for k in range(1201):
        date = maturity - pd.DateOffset(months=months * k)
        if maturity.is_month_end:
            date = date + pd.offsets.MonthEnd(0)
        if date <= settlement:
            previous = date
            break
        dates.append(date)
    else:
        raise ValueError("Bond schedule exceeds supported length")
    dates.reverse()
    fraction = (dates[0] - settlement).days / (dates[0] - previous).days
    periods = fraction + np.arange(len(dates))
    flows = np.full(len(dates), face * coupon_rate / frequency)
    flows[-1] += face
    accrued = face * coupon_rate / frequency * (1 - fraction)
    return periods / frequency, flows, float(accrued)


def bond_price(yield_rate, settlement, maturity, coupon_rate, frequency=2, face=100, clean=False):
    times, flows, accrued = cash_flows(settlement, maturity, coupon_rate, frequency, face)
    if not np.isfinite(yield_rate) or yield_rate <= -frequency:
        raise ValueError("Yield outside compounding domain")
    price = np.sum(flows / (1 + yield_rate / frequency) ** (frequency * times))
    return float(price - accrued if clean else price)


def yield_to_maturity(price, settlement, maturity, coupon_rate, frequency=2, face=100, clean=False):
    if not np.isfinite(price) or price <= 0:
        raise ValueError("Price must be positive")

    def error(y):
        return bond_price(y, settlement, maturity, coupon_rate, frequency, face, clean) - price

    # A finite lower bracket avoids overflow in long schedules, then approaches -m if needed.
    low, high = -0.5 * frequency, 1.0
    for _ in range(20):
        if error(low) > 0:
            break
        low = (low - frequency) / 2
    while error(high) > 0 and high < 1e6:
        high *= 2
    return float(brentq(error, low, high, xtol=1e-13))


def bond_analytics(yield_rate, settlement, maturity, coupon_rate, frequency=2, face=100):
    price = bond_price(yield_rate, settlement, maturity, coupon_rate, frequency, face)
    times, flows, accrued = cash_flows(settlement, maturity, coupon_rate, frequency, face)
    base = 1 + yield_rate / frequency
    present_values = flows / base ** (frequency * times)
    macaulay = float(times @ present_values / price)
    modified = macaulay / base
    convexity = float((times * (times + 1 / frequency)) @ present_values / (price * base**2))
    args = (settlement, maturity, coupon_rate, frequency, face)
    if yield_rate - 0.0001 <= -frequency:
        raise ValueError("Yield too close to boundary for DV01")
    dv01 = (bond_price(yield_rate - 0.0001, *args) - bond_price(yield_rate + 0.0001, *args)) / 2
    return dict(
        dirty_price=price,
        clean_price=price - accrued,
        accrued_interest=accrued,
        ytm=yield_rate,
        macaulay_duration=macaulay,
        modified_duration=modified,
        convexity=convexity,
        dv01=dv01,
        dv01_duration=price * modified * 0.0001,
    )


def curve_price(
    settlement, maturity, coupon_rate, tenors, zero_rates, spread=0.0, frequency=2, face=100
):
    """Continuous zero rates, linearly interpolated; constant endpoint extrapolation."""
    times, flows, _ = cash_flows(settlement, maturity, coupon_rate, frequency, face)
    tenors, rates = np.asarray(tenors, float), np.asarray(zero_rates, float)
    if (
        tenors.ndim != 1
        or len(tenors) < 2
        or len(rates) != len(tenors)
        or not np.all(np.diff(tenors) > 0)
    ):
        raise ValueError("Curve tenors must be strictly increasing")
    if not np.isfinite(rates).all() or not np.isfinite(spread):
        raise ValueError("Invalid curve rates")
    # Curve discount times use actual calendar days / 365, separate from coupon YTM timing.
    settlement, maturity = pd.Timestamp(settlement), pd.Timestamp(maturity)
    dates = []
    for k in reversed(range(len(times))):
        d = maturity - pd.DateOffset(months=12 // frequency * k)
        dates.append(d + pd.offsets.MonthEnd(0) if maturity.is_month_end else d)
    years = np.array([(d - settlement).days / 365 for d in dates])
    return float(flows @ np.exp(-(np.interp(years, tenors, rates) + spread) * years))
