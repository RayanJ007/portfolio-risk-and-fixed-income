# Daily portfolio risk report

As of 2026-08-31 | Base CAD | One-day horizon

**Contains synthetic teaching data.** Calibration: 2025-09-12 to 2026-08-31, 252 synchronized observations. Sample covariance (ddof=1); zero drift. Monte Carlo: 10,000 simulations, seed 42. Positive VaR/ES denote losses; positive P&L denotes gains.

## Portfolio summary

NAV: **101,390,516 CAD**. Prior NAV (2026-08-28): 101,660,737. Flow-adjusted daily P&L: **-270,221**. External flows: 0. Coupon receipts must be entered as cash income trades.

| asset_class | market_value |
| --- | --- |
| Cash | 9,305,000.00 |
| Corporate bond | 12,171,761.64 |
| Equity | 48,900,000.00 |
| Fixed income ETF | 8,398,000.00 |
| Government bond | 22,330,903.00 |
| Option | 284,851.22 |

## One-day VaR and Expected Shortfall

Historical and Monte Carlo use full instrument repricing. Parametric uses local factor sensitivities and a Gaussian distribution. Confidence is a decimal (0.99 = 99%).

| method | confidence | horizon_days | base_currency | var | es |
| --- | --- | --- | --- | --- | --- |
| Historical | 0.95 | 1 | CAD | 959,458.93 | 1,072,168.03 |
| Parametric | 0.95 | 1 | CAD | 958,039.73 | 1,201,420.47 |
| Monte Carlo | 0.95 | 1 | CAD | 963,859.78 | 1,192,800.37 |
| Historical | 0.99 | 1 | CAD | 1,171,692.79 | 1,221,790.71 |
| Parametric | 0.99 | 1 | CAD | 1,354,973.87 | 1,552,345.49 |
| Monte Carlo | 0.99 | 1 | CAD | 1,340,380.59 | 1,522,803.13 |

## Top contributors to 99% parametric VaR

Marginal VaR is CAD per added security unit. Component VaR is CAD; negative contributions are hedges.

| security_id | component_var | marginal_var | standalone_var |
| --- | --- | --- | --- |
| US_EQ | 737,688.74 | 10.54 | 820,430.41 |
| CA_EQ | 492,735.00 | 1.96 | 643,435.32 |
| US_CALL | 50,041.14 | 500.41 | 58,946.76 |
| US_ETF | 44,014.54 | 0.68 | 146,285.35 |
| CA_GOV | 19,847.35 | 0.09 | 117,232.90 |
| USD_CASH | 8,742.14 | 0.00 | 30,260.69 |
| CA_CORP | 1,904.97 | 0.02 | 93,688.70 |
| CAD_CASH | 0.00 | 0.00 | 0.00 |

Diversification benefit versus standalone VaRs: 555,306 CAD.

## Fixed income

Duration in years, convexity in years squared, yield in decimals. Position DV01 is CAD per 1 bp nominal-YTM bump; curve shocks use continuous zero rates.

| security_id | ytm | modified_duration | convexity | position_dv01 |
| --- | --- | --- | --- | --- |
| CA_CORP | 0.05 | 5.86 | 40.66 | 7,133.61 |
| CA_GOV | 0.03 | 4.56 | 24.06 | 10,185.72 |

## Stress testing

| scenario | pnl | new_nav |
| --- | --- | --- |
| Credit crisis | -14,342,802.57 | 87,047,713.29 |
| Inflation | -14,074,139.80 | 87,316,376.07 |
| Equity crash | -13,868,787.04 | 87,521,728.83 |
| Recession | -9,681,921.74 | 91,708,594.13 |
| Custom | -6,245,601.24 | 95,144,914.63 |

## Yield curves

| scenario | security_id | pnl | linear_pnl | nonlinear_difference |
| --- | --- | --- | --- | --- |
| Parallel +100 bp | CA_GOV | -1,010,389.47 | -1,035,137.53 | 24,748.05 |
| Parallel +100 bp | CA_CORP | -706,950.34 | -730,544.47 | 23,594.13 |
| Parallel -100 bp | CA_GOV | 1,060,712.59 | 1,035,137.53 | 25,575.07 |
| Parallel -100 bp | CA_CORP | 755,232.96 | 730,544.47 | 24,688.49 |
| Bear steepener | CA_GOV | -426,671.59 | -431,073.05 | 4,401.46 |
| Bear steepener | CA_CORP | -353,223.30 | -359,212.33 | 5,989.03 |
| Bull flattener | CA_GOV | 365,289.07 | 362,157.58 | 3,131.49 |
| Bull flattener | CA_CORP | 292,488.24 | 288,581.84 | 3,906.40 |

## Why did 99% parametric VaR change?

1,368,222 → 1,354,974 CAD; change **-13,248 CAD**. Average forward/reverse replacement paths; interactions allocated within drivers. This allocation is model-based, not causal.

| driver | allocated_change | standalone_change |
| --- | --- | --- |
| Positions / trades | 1,978.32 | 1,994.56 |
| Market prices | -11,218.94 | -11,254.77 |
| FX levels | 3,102.25 | 3,121.61 |
| Rates / spreads | -64.27 | -65.45 |
| Option volatility levels | 427.67 | 393.67 |
| Equity / ETF volatility | -4,102.62 | -4,114.22 |
| FX volatility | 76.26 | 76.49 |
| Rate / spread volatility | 16.74 | 16.78 |
| Other factor volatility | 14.18 | 14.56 |
| Correlation | -3,429.51 | -3,437.49 |
| Valuation date / roll | -47.92 | -44.52 |

Interaction effect relative to standalone changes: 50.94 CAD (already allocated within drivers, do not add twice). Numerical residual: 0.00000000 CAD.

## Hypothetical performance diagnostics

Frozen-current-exposure hypothetical daily scenario returns; these are scenario replay statistics, not realized investment performance. Annualization: 252 days; annual risk-free rate 3.0%.

| metric | value |
| --- | --- |
| cumulative_return | 0.07 |
| annualized_return | 0.07 |
| volatility | 0.09 |
| sharpe | 0.47 |
| max_drawdown | -0.06 |
| observations | 252.00 |
| beta | 0.40 |
| tracking_error | 0.12 |
| information_ratio | 0.44 |

## Data quality and key alerts

| severity | count |
| --- | --- |
| PASS | 20 |
| WARN | 1 |

| severity | description |
| --- | --- |
| WARN | Contains explicitly synthetic teaching data |

Volatility-floor activations in Monte Carlo: 0. No history is forward-filled. Holiday/missing-day gaps exclude both adjacent changes. See `reports/risk_methodology.md` for assumptions and limits.
