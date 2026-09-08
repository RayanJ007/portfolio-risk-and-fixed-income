"""European Black–Scholes. Vega per 1.00 vol; theta per year; rates continuous."""

import numpy as np
from scipy.special import ndtr


def black_scholes(spot, strike, time, rate, volatility, dividend=0.0, option_type="call"):
    spot, volatility, rate = np.broadcast_arrays(
        np.asarray(spot, float), np.asarray(volatility, float), np.asarray(rate, float)
    )
    if option_type not in ("call", "put") or strike <= 0 or time < 0:
        raise ValueError("Invalid option terms")
    if (
        not np.isfinite(spot).all()
        or not np.isfinite(volatility).all()
        or not np.isfinite(rate).all()
        or not np.isfinite([strike, time, dividend]).all()
    ):
        raise ValueError("Nonfinite option input")
    if np.any(spot <= 0) or np.any(volatility < 0):
        raise ValueError("Invalid spot or volatility")
    sign = 1 if option_type == "call" else -1
    if time == 0:
        return np.maximum(sign * (spot - strike), 0.0)
    safe_vol = np.maximum(volatility, 1e-15)
    d1 = (np.log(spot / strike) + (rate - dividend + 0.5 * safe_vol**2) * time) / (
        safe_vol * np.sqrt(time)
    )
    d2 = d1 - safe_vol * np.sqrt(time)
    result = sign * (
        spot * np.exp(-dividend * time) * ndtr(sign * d1)
        - strike * np.exp(-rate * time) * ndtr(sign * d2)
    )
    deterministic = np.maximum(
        sign * (spot * np.exp(-dividend * time) - strike * np.exp(-rate * time)), 0.0
    )
    return np.where(volatility == 0, deterministic, result)


def option_greeks(spot, strike, time, rate, volatility, dividend=0.0, option_type="call"):
    price = float(black_scholes(spot, strike, time, rate, volatility, dividend, option_type))
    if time <= 0 or volatility <= 0:
        raise ValueError("Greeks require positive time and volatility")
    d1 = (np.log(spot / strike) + (rate - dividend + 0.5 * volatility**2) * time) / (
        volatility * np.sqrt(time)
    )
    d2 = d1 - volatility * np.sqrt(time)
    density = np.exp(-0.5 * d1 * d1) / np.sqrt(2 * np.pi)
    sign = 1 if option_type == "call" else -1
    delta = sign * np.exp(-dividend * time) * ndtr(sign * d1)
    gamma = np.exp(-dividend * time) * density / (spot * volatility * np.sqrt(time))
    vega = spot * np.exp(-dividend * time) * density * np.sqrt(time)
    theta = (
        -spot * np.exp(-dividend * time) * density * volatility / (2 * np.sqrt(time))
        - sign * rate * strike * np.exp(-rate * time) * ndtr(sign * d2)
        + sign * dividend * spot * np.exp(-dividend * time) * ndtr(sign * d1)
    )
    return dict(price=price, delta=delta, gamma=gamma, vega=vega, theta=theta)
