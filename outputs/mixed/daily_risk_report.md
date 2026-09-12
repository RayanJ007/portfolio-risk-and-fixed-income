# Daily portfolio risk report

As of 2026-08-31 | Base CAD | One-day horizon

**Mixed: real Bank of Canada FX; synthetic other markets and holdings.** Calibration: 2025-08-12 to 2026-08-31, 252 synchronized observations. Sample covariance (ddof=1); zero drift. Monte Carlo: 10,000 simulations, seed 42. Positive VaR/ES denote losses; positive P&L denotes gains.

## Portfolio summary

NAV: **102,079,042 CAD**. Prior NAV (2026-08-28): 102,539,374. Flow-adjusted daily P&L: **-460,332**. External flows: 0. Coupon receipts must be entered as cash income trades.

| asset_class | market_value |
| --- | --- |
| Cash | 9,358,200.00 |
| Corporate bond | 12,171,761.64 |
| Equity | 49,365,500.00 |
| Fixed income ETF | 8,562,255.00 |
| Government bond | 22,330,903.00 |
| Option | 290,422.57 |

## One-day VaR and Expected Shortfall

Historical and Monte Carlo use full instrument repricing. Parametric uses local factor sensitivities and a Gaussian distribution. Confidence is a decimal (0.99 = 99%).

| method | confidence | horizon_days | base_currency | var | es |
| --- | --- | --- | --- | --- | --- |
| Historical | 0.95 | 1 | CAD | 926,116.40 | 1,033,338.51 |
| Parametric | 0.95 | 1 | CAD | 899,824.31 | 1,128,415.98 |
| Monte Carlo | 0.95 | 1 | CAD | 880,905.84 | 1,120,972.97 |
| Historical | 0.99 | 1 | CAD | 1,088,780.24 | 1,219,544.79 |
| Parametric | 0.99 | 1 | CAD | 1,272,638.69 | 1,458,016.99 |
| Monte Carlo | 0.99 | 1 | CAD | 1,261,988.11 | 1,447,269.76 |

## Top contributors to 99% parametric VaR

Marginal VaR is CAD per added security unit. Component VaR is CAD; negative contributions are hedges.

| security_id | component_var | marginal_var | standalone_var |
| --- | --- | --- | --- |
| US_EQ | 681,918.64 | 9.74 | 773,803.11 |
| CA_EQ | 496,015.40 | 1.98 | 636,456.10 |
| US_CALL | 47,680.00 | 476.80 | 57,700.79 |
| CA_GOV | 21,411.59 | 0.10 | 118,692.76 |
| US_ETF | 15,234.45 | 0.23 | 94,417.09 |
| CA_CORP | 8,257.78 | 0.07 | 94,115.25 |
| USD_CASH | 2,120.83 | 0.00 | 15,634.56 |
| CAD_CASH | 0.00 | 0.00 | 0.00 |

Diversification benefit versus standalone VaRs: 518,181 CAD.

## Fixed income

Duration in years, convexity in years squared, yield in decimals. Position DV01 is CAD per 1 bp nominal-YTM bump; curve shocks use continuous zero rates.

| security_id | ytm | modified_duration | convexity | position_dv01 |
| --- | --- | --- | --- | --- |
| CA_CORP | 0.05 | 5.86 | 40.66 | 7,133.61 |
| CA_GOV | 0.03 | 4.56 | 24.06 | 10,185.72 |

## Stress testing

| scenario | pnl | new_nav |
| --- | --- | --- |
| Credit crisis | -14,433,360.51 | 87,645,681.71 |
| Inflation | -14,198,826.05 | 87,880,216.17 |
| Equity crash | -13,980,714.94 | 88,098,327.28 |
| Recession | -9,746,878.18 | 92,332,164.04 |
| Custom | -6,294,837.05 | 95,784,205.17 |

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

1,280,580 → 1,272,639 CAD; change **-7,941 CAD**. Average forward/reverse replacement paths; interactions allocated within drivers. This allocation is model-based, not causal.

| driver | allocated_change | standalone_change |
| --- | --- | --- |
| Positions / trades | 1,979.20 | 1,983.24 |
| Market prices | -10,861.52 | -10,885.17 |
| FX levels | -1,191.23 | -1,197.26 |
| Rates / spreads | -85.11 | -84.20 |
| Option volatility levels | 391.03 | 357.43 |
| Equity / ETF volatility | 633.17 | 635.62 |
| FX volatility | -34.97 | -34.67 |
| Rate / spread volatility | 55.23 | 54.77 |
| Other factor volatility | 0.78 | 1.15 |
| Correlation | 1,214.92 | 1,221.27 |
| Valuation date / roll | -42.84 | -40.80 |

Interaction effect relative to standalone changes: 47.27 CAD (already allocated within drivers, do not add twice). Numerical residual: 0.00000000 CAD.

## Hypothetical performance diagnostics

Frozen-current-exposure hypothetical daily scenario returns; these are scenario replay statistics, not realized investment performance. Annualization: 252 days; annual risk-free rate 3.0%.

| metric | value |
| --- | --- |
| cumulative_return | 0.03 |
| annualized_return | 0.03 |
| volatility | 0.09 |
| sharpe | 0.07 |
| max_drawdown | -0.06 |
| observations | 252.00 |
| beta | 0.38 |
| tracking_error | 0.12 |
| information_ratio | 0.05 |

## Data quality and key alerts

| severity | count |
| --- | --- |
| PASS | 20 |
| WARN | 1 |

| severity | description |
| --- | --- |
| WARN | Contains explicitly synthetic teaching data |

Volatility-floor activations in Monte Carlo: 0. No history is forward-filled. Holiday/missing-day gaps exclude both adjacent changes. See `reports/risk_methodology.md` for assumptions and limits.
