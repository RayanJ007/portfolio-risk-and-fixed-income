# Daily portfolio risk report

As of 2026-08-26 | Base CAD | One-day horizon

**Hypothetical portfolio using public historical market data.** Calibration: 2025-07-11 to 2026-08-26, 252 synchronized observations. Sample covariance (ddof=1); zero drift. Monte Carlo: 10,000 simulations, seed 42. Positive VaR/ES denote losses; positive P&L denotes gains.

## Portfolio summary

NAV: **110,459,484 CAD**. Prior NAV (2026-08-25): 110,464,871. Flow-adjusted daily P&L: **-5,386**. External flows: 0. Coupon receipts must be entered as cash income trades.

| asset_class | market_value |
| --- | --- |
| Cash | 8,849,940.00 |
| Corporate bond | 13,923,827.08 |
| Equity | 56,429,288.88 |
| Fixed income ETF | 8,091,095.90 |
| Government bond | 22,591,899.44 |
| Option | 573,433.20 |

## One-day VaR and Expected Shortfall

Historical and Monte Carlo use full instrument repricing. Parametric uses local factor sensitivities and a Gaussian distribution. Confidence is a decimal (0.99 = 99%).

| method | confidence | horizon_days | base_currency | var | es |
| --- | --- | --- | --- | --- | --- |
| Historical | 0.95 | 1 | CAD | 694,695.09 | 944,900.02 |
| Parametric | 0.95 | 1 | CAD | 727,375.25 | 912,157.90 |
| Monte Carlo | 0.95 | 1 | CAD | 722,281.17 | 889,664.89 |
| Historical | 0.99 | 1 | CAD | 1,043,864.75 | 1,209,457.41 |
| Parametric | 0.99 | 1 | CAD | 1,028,740.69 | 1,178,591.71 |
| Monte Carlo | 0.99 | 1 | CAD | 1,000,385.01 | 1,131,507.49 |

## Top contributors to 99% parametric VaR

Marginal VaR is CAD per added security unit. Component VaR is CAD; negative contributions are hedges.

| security_id | component_var | marginal_var | standalone_var |
| --- | --- | --- | --- |
| SPY | 514,564.28 | 17.15 | 575,225.74 |
| XIU.TO | 354,931.77 | 0.79 | 428,529.39 |
| HYP_CAD_GOV | 62,292.18 | 0.28 | 103,831.33 |
| HYP_US_IG | 57,469.92 | 0.57 | 104,770.68 |
| TLT | 57,168.41 | 0.82 | 123,155.01 |
| USD_CASH | 2,895.33 | 0.00 | 15,770.74 |
| CAD_CASH | 0.00 | 0.00 | 0.00 |
| HYP_SPY_CALL | -20,581.20 | -205.81 | 87,745.80 |

Diversification benefit versus standalone VaRs: 410,288 CAD.

## Fixed income

Duration in years, convexity in years squared, yield in decimals. Position DV01 is CAD per 1 bp nominal-YTM bump; curve shocks use continuous zero rates.

| security_id | ytm | modified_duration | convexity | position_dv01 |
| --- | --- | --- | --- | --- |
| HYP_CAD_GOV | 0.03 | 4.49 | 23.74 | 10,151.33 |
| HYP_US_IG | 0.05 | 5.69 | 39.39 | 7,923.92 |

## Stress testing

| scenario | pnl | new_nav |
| --- | --- | --- |
| Inflation | -16,523,919.59 | 93,935,564.90 |
| Equity crash | -15,496,278.25 | 94,963,206.24 |
| Credit crisis | -15,398,506.64 | 95,060,977.85 |
| Recession | -10,371,350.91 | 100,088,133.58 |
| Custom | -7,311,572.01 | 103,147,912.48 |

## Yield curves

| scenario | security_id | pnl | linear_pnl | nonlinear_difference |
| --- | --- | --- | --- | --- |
| Parallel +100 bp | HYP_CAD_GOV | -1,007,135.99 | -1,031,864.10 | 24,728.11 |
| Parallel +100 bp | HYP_US_IG | -787,129.85 | -813,409.50 | 26,279.65 |
| Parallel -100 bp | HYP_CAD_GOV | 1,057,420.73 | 1,031,864.10 | 25,556.63 |
| Parallel -100 bp | HYP_US_IG | 840,909.66 | 813,409.50 | 27,500.17 |
| Bear steepener | HYP_CAD_GOV | -425,822.83 | -430,232.46 | 4,409.63 |
| Bear steepener | HYP_US_IG | -393,367.56 | -400,048.98 | 6,681.42 |
| Bull flattener | HYP_CAD_GOV | 364,460.97 | 361,325.89 | 3,135.08 |
| Bull flattener | HYP_US_IG | 325,726.75 | 321,370.34 | 4,356.41 |

## Why did 99% parametric VaR change?

1,029,756 → 1,028,741 CAD; change **-1,015 CAD**. Average forward/reverse replacement paths; interactions allocated within drivers. This allocation is model-based, not causal.

| driver | allocated_change | standalone_change |
| --- | --- | --- |
| Positions / trades | 791.12 | 795.40 |
| Market prices | -3,113.72 | -3,111.07 |
| FX levels | 1,630.14 | 1,629.88 |
| Rates / spreads | -112.77 | -113.03 |
| Option volatility levels | -174.14 | -174.57 |
| Equity / ETF volatility | -16.40 | -15.96 |
| FX volatility | 129.57 | 129.61 |
| Rate / spread volatility | 55.48 | 55.48 |
| Other factor volatility | -2.93 | -2.92 |
| Correlation | -248.13 | -247.59 |
| Valuation date / roll | 46.78 | 46.90 |

Interaction effect relative to standalone changes: -7.11 CAD (already allocated within drivers, do not add twice). Numerical residual: 0.00000000 CAD.

## Hypothetical performance diagnostics

Frozen-current-exposure hypothetical daily scenario returns; these are scenario replay statistics, not realized investment performance. Annualization: 252 days; annual risk-free rate 3.0%.

| metric | value |
| --- | --- |
| cumulative_return | 0.10 |
| annualized_return | 0.10 |
| volatility | 0.06 |
| sharpe | 1.08 |
| max_drawdown | -0.04 |
| observations | 252.00 |
| beta | 0.44 |
| tracking_error | 0.08 |
| information_ratio | -1.77 |

## Data quality and key alerts

| severity | count |
| --- | --- |
| PASS | 23 |
| WARN | 2 |

| severity | description |
| --- | --- |
| WARN | Daily move exceeds eight robust standard deviations: 2026-04-29 |
| WARN | Daily move exceeds eight robust standard deviations: 2025-08-15 |

Volatility-floor activations in Monte Carlo: 0. No history is forward-filled. Holiday/missing-day gaps exclude both adjacent changes. See `reports/risk_methodology.md` for assumptions and limits.

## Public source snapshot

Retrieved 2026-09-12T17:16:45.652815+00:00. Source status applies to this cached snapshot.

| name | series_id | last_date | units | status |
| --- | --- | --- | --- | --- |
| XIU.TO | XIU.TO | 2026-08-31 | CAD per share | OK |
| SPY | SPY | 2026-08-31 | USD per share | OK |
| TLT | TLT | 2026-08-31 | USD per share | OK |
| VIX | ^VIX | 2026-08-31 | index points | OK |
| fx | FXUSDCAD | 2026-08-31 | CAD per USD | OK |
| CAD | ZC100YR,ZC200YR,ZC500YR,ZC1000YR,ZC3000YR | 2026-08-26 | continuous annual decimal | OK |
| USD | SVENY01,SVENY02,SVENY05,SVENY10,SVENY30 | 2026-08-31 | continuous annual decimal | OK |
| spread | BAMLC0A0CM | 2026-08-31 | annual spread decimal | OK |

Hypothetical bond terms; European SPY call, strike 800, expiry 2027-08-31, assumed dividend yield 1.2%; VIX proxy.

- BoC curves have a publication lag; valuation is retrospective, not an as-published trading backtest.
- FRED ICE data may supply only three years and has redistribution restrictions.
- VIX is a 30-day S&P 500 volatility proxy, not the SPY contract's implied volatility.
- Current option-chain IV is deliberately excluded from historical valuation to avoid look-ahead.
