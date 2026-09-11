# Risk methodology and financial conventions

This project is a teaching implementation of a daily market-risk workflow. It is not a regulatory capital model or a trading recommendation. Core pricing and risk calculations are visible in Python and NumPy; no financial pricing library substitutes for the bond mathematics.

## 1. Valuation, units and accounting

The default portfolio has approximately CAD 100 million across Canadian and US equity baskets, two Canadian fixed-rate bonds, a US Treasury ETF proxy, CAD and USD cash, and a small European call. Instruments and trades are configurable CSV inputs. All demo instruments are fictional, including the government and corporate bonds. Ratings and sector classifications in the demo are assumptions.

| Input or output | Unit and convention |
|---|---|
| Dates | ISO `YYYY-MM-DD`; position ownership follows settlement date |
| Quantity | Shares, bond units, cash currency units or option contracts; signed |
| Bond face | Local currency per bond unit; demo face is 100 |
| Market price | Local currency per share/bond or per option underlying share |
| Option multiplier | 100 underlying shares per demo contract |
| FX | Base currency per one foreign unit; e.g. 1.36 CAD per USD |
| Yield, zero rate, spread | Annual decimal; 5% = 0.05 |
| Volatility | Annual decimal in option pricing; daily factor volatility in covariance |
| Basis point | 0.0001 absolute annual rate; 100 bp = 0.01 |
| NAV, P&L, VaR, ES | Portfolio base currency, CAD by default |
| P&L | Positive for gains; negative for losses |
| VaR / ES | Positive losses; estimates floored at zero |
| Marginal VaR | CAD per additional security unit, including multiplier |
| Component VaR | CAD; negative hedge contributions are retained |

Local value is quantity × price × multiplier. Base value additionally multiplies by FX. CAD cash is valued at one CAD per unit. Bond positions use dirty prices. `book_cost` is the remaining signed average acquisition cost in local currency, including the multiplier; it is not a tax-lot or realized-profit ledger. Same-day cost processing uses settlement date, trade date and trade ID as a deterministic order. Supply trade IDs in intended execution order if intraday cost-basis order matters.

SQL derives quantities from settled signed trades, including explicit opening holdings. Ordinary security trades need offsetting cash ledger entries in their currency. A cash-funding control checks the net execution amount by settlement date and currency. Opening holdings, external contributions/withdrawals, and income are separately classified. Coupons, dividends, principal repayments, option exercise and cash interest must be entered as cash/settlement transactions. They are not automatically posted. The demo explicitly records CAD 685,000 of bond coupons on August 31, 2026. Matured instruments still held fail controls and require settlement.

Daily P&L = current NAV − prior NAV − external flows between the two dates. External flows are converted at their settlement-date FX with the same staleness limit; no future FX is used. The default dates span Friday to Monday, so daily P&L contains calendar carry and the coupon receipts over that interval. Risk scenarios instead hold valuation time fixed: they measure market-shock P&L and exclude future carry/theta.

## 2. Market data, provenance and dates

`demo` uses seeded synthetic observations. `mixed-demo` replaces only USD/CAD with real Bank of Canada observations; other markets and holdings remain synthetic. Neither report is represented as an empirical real-portfolio backtest. The archived public series contains 416 actual USD/CAD observations from January 2, 2025 to August 31, 2026, with source URL, retrieval time and original JSON. The [Bank of Canada Valet API](https://www.bankofcanada.ca/valet/docs/) documents access to the observations. No network request is needed for the offline sample runs.

`market_prices.price` is the unadjusted valuation quote; `adjusted_price` is the consistent return-series input. Equity/ETF factor history must match adjusted prices. Current valuation uses the unadjusted quote. For real imports, use split-adjusted price returns consistently and separately book dividends and split-adjusted position quantities. Feeding a dividend-reinvested total-return series into the risk engine approximates short-horizon price shocks by total returns; disclose this choice, particularly around ex-dividend dates. Option underlying levels must be actual spot in the same strike units, not an arbitrarily rebased adjusted-price index. Supply a separate underlying factor if needed.

Historical estimation cuts off at the requested valuation date. Levels are reindexed to weekdays before differencing; a missing weekday invalidates that day's change and the following change. No missing history is forward-filled, and no multiday gap is silently treated as one day. This conservative common-weekday calendar does not implement exchange-specific holiday calendars. Valuation quotes use the last available observation on or before the date and a maximum age of two weekdays. Price, FX, factor and curve tables are reconciled. A known market holiday may therefore reduce the history sample or use a bounded previous quote.

The default calibration uses the last 252 complete, synchronized daily factor changes, requiring at least 100. Windows can extend beyond 252 calendar weekdays when observations are missing. Both start/end dates and observation count are reported. A 99% historical tail from 252 observations effectively has only 2.52 observations: tail estimates are noisy and should not be presented with spurious precision.

## 3. Bond cash flows, pricing and YTM

For face amount F, annual coupon c, coupon frequency m, annual nominal yield y, and remaining payment times tᵢ:

```text
Coupon = F × c / m
Pdirty(y) = Σ CFᵢ (1 + y/m)^(−m tᵢ)
Pclean = Pdirty − accrued interest
Accrued interest = coupon × elapsed fraction of the coupon period
```

The schedule is generated backwards from maturity and preserves month-end dates. Remaining fractional coupon periods use actual days divided by actual days in that coupon period, then subsequent periods are spaced by 1/m years. This is a regular-coupon Actual/Actual convention. Settlement on a payment date excludes that day's coupon; ownership cash is handled by the ledger. Annual, semiannual, quarterly and monthly coupons are supported. Irregular first/last coupons, business-day adjustments, ex-coupon rules, amortization and embedded options are outside scope. These simplifications can differ from a vendor's clean price.

YTM solves `P(y) − observed price = 0` with SciPy's Brent root solver. Negative yields are permitted within `y > −m`; brackets expand if necessary. The solver is numerical, but the cash-flow function is implemented directly. Clean-price YTM adds accrued interest implicitly through the same clean pricing function. Price/yield round trips and independent par/zero-coupon prices validate the solver.

## 4. Duration, DV01 and convexity

Let PVᵢ be the discounted cash flow under nominal YTM and P the dirty price:

```text
Macaulay duration = Σ tᵢ PVᵢ / P                          [years]
Modified duration = Macaulay / (1 + y/m)                 [years]
Convexity = Σ tᵢ(tᵢ + 1/m)PVᵢ / [P(1 + y/m)²]           [years²]
DV01duration = P × modified duration × 0.0001             [local currency/bp]
DV01reprice = [P(y − 0.0001) − P(y + 0.0001)] / 2         [local currency/bp]
ΔP / P ≈ −Dmodified Δy + 0.5 × convexity × Δy²
```

The reported long-bond DV01 is positive; a +1 bp yield change produces approximately −DV01 of P&L. Signed position DV01 multiplies by quantity, multiplier and FX. Convexity is the normalized second derivative, without a hidden factor of 1/2. Full repricing is used for large shocks; the Taylor approximation is shown only for comparison.

## 5. Zero curves and spread repricing

Portfolio bonds are valued from continuous zero curves rather than a single yield:

```text
Pcurve = Σ CFᵢ exp[−(z(tᵢ) + s)tᵢ]
```

Here curve times are actual calendar days / 365. Zero rates are linearly interpolated in tenor and held flat beyond the first/last knot. Corporate credit is a constant continuous spread added to each cash-flow zero rate. This is not a survival-probability/default model. YTM is subsequently solved from the curve-derived dirty price, so nominal YTM and continuously compounded zero rates must not be compared as identical quotes.

The curve engine supports ±100 bp parallel moves, a bear steepener (+25 bp at one year to +150 bp at 30 years), a bull flattener (−25 to −100 bp), and custom tenor/bp knots. Shocks interpolate in tenor. Full repricing is compared with the sum of tenor-specific central-difference sensitivities times the shocks. For nonparallel moves this is a key-rate linear approximation, not a single-duration estimate. Curve DV01 and nominal-YTM DV01 are related but not identical because compounding and timing differ.

## 6. European option

Black–Scholes prices a European call/put with continuous risk-free rate r, dividend yield q, implied volatility σ, spot S, strike K and ACT/365 time T:

```text
d₁ = [ln(S/K) + (r − q + σ²/2)T] / (σ√T)
d₂ = d₁ − σ√T
Call = S exp(−qT)N(d₁) − K exp(−rT)N(d₂)
Put  = K exp(−rT)N(−d₂) − S exp(−qT)N(−d₁)
```

Delta is per unit spot change; gamma per spot squared. Vega is per 1.00 absolute volatility change (divide by 100 for one percentage point). Theta is per year (divide by 365 for a calendar-day approximation). Greeks are per underlying share, before contract quantity/multiplier/FX. Tests compare them with finite differences and put-call parity.

Risk scenarios fully reprice the option using shocked spot, rates, FX and the volatility factor. Gaussian absolute volatility shocks are floored at 0.0001 to avoid negative model volatility; the number of Monte Carlo activations is reported. This floor changes the assumed distribution at the boundary. The model has no smile/skew, American exercise or stochastic-volatility dynamics.

## 7. Portfolio returns and covariance

The reusable return function calculates simple returns `Pₜ/Pₜ₋₁ − 1` without filling gaps. The report's historical series consists of current-exposure full-repricing scenario P&L divided by current NAV. It is labelled **hypothetical scenario replay**, not realized portfolio performance. Compounding this series illustrates the risk of today's exposures; it does not simulate historical trades, income reinvestment or changing holdings.

For daily simple returns rₜ and 252 trading days/year:

```text
Wealthₜ = ∏(1 + rₜ), including initial wealth 1 for drawdown
Annualized return = ending wealth^(252/n) − 1
Annualized volatility = sample standard deviation(r) × √252
Sharpe = mean(r − daily risk-free rate) × 252 / annualized volatility
Beta = sample covariance(portfolio, benchmark) / sample variance(benchmark)
Maximum drawdown = min(wealth/running peak − 1)
Tracking error = sample standard deviation(r − benchmark) × √252
Information ratio = mean(r − benchmark) × 252 / tracking error
```

The annual effective risk-free rate is converted by `(1+annual rate)^(1/252)−1`. Zero denominators produce unavailable ratios, not infinity. The configured demo benchmark is the Canadian equity factor. Benchmark observations are aligned by date.

Factor changes differ by financial type: equity/ETF and FX changes are logarithms of level ratios; zero rates, spreads and implied volatility use absolute decimal differences. Sample covariance uses synchronized observations and `ddof=1`. No pairwise-missing covariance or silently repaired correlation matrix is used. Mixed units are intentional: sensitivities are taken in matching factor coordinates, so `g′Σg` has CAD² units.

## 8. Historical VaR and Expected Shortfall

Each complete historical factor shock is applied to the current market state. Log factors transform by `current level × exp(shock)` and absolute factors by `current level + shock`. All holdings are repriced, with current quantities fixed. Portfolio P&L is shocked base value minus current base value. Loss L = −P&L.

At confidence α (95% or 99%), empirical VaR is the inverse empirical CDF: sorted ascending losses at one-based rank `ceil(nα)`. Reported VaR is `max(quantile, 0)`.

ES integrates the worst `(1−α)` probability mass. With losses sorted descending, let `m=n(1−α)`, `k=floor(m)`, `f=m−k`:

```text
ES = [sum of the k largest losses + f × next loss] / m
```

This fractional boundary definition handles discrete observations and ties without arbitrarily changing the tail size. It coincides with average loss beyond the VaR threshold for a continuous distribution. ES is also floored at zero. VaR gives a loss threshold; ES describes severity in the tail. [Acerbi and Tasche](https://arxiv.org/abs/cond-mat/0105191) discuss the coherent tail-average definition. These one-day 95%/99% estimates are not the regulatory stressed-ES/liquidity-horizon framework.

## 9. Parametric VaR and Euler contributions

Central finite differences give the base value sensitivity of one security unit to each factor shock. The default step is 0.00001 in that factor's coordinate. Let A be the security-by-factor matrix, q the security quantities and g = q′A:

```text
Portfolio variance = g′Σg
σP&L = √(g′Σg)
VaRα = Φ⁻¹(α) × σP&L
Normal ESα = φ(Φ⁻¹(α)) / (1−α) × σP&L
Marginal VaRᵢ = zα × [Aᵢ Σg] / σP&L
Component VaRᵢ = qᵢ × Marginal VaRᵢ
```

Euler homogeneity gives `Σ Component VaR = portfolio VaR` for this differentiable linear Gaussian model. Contributions can be aggregated by security, asset class, currency or sector. A negative contribution is a hedge and must not be removed. At zero net volatility the derivative is not uniquely defined; the implementation reports zero contributions by convention. Standalone VaRs ignore diversification; their sum minus portfolio VaR measures the standalone diversification benefit. Do not add this benefit to Euler contributions. Contributions are implemented for parametric VaR only, not asserted to reconcile to historical or nonlinear Monte Carlo VaR.

Assumptions: zero drift, Gaussian one-day factor changes, fixed sensitivities, and stable sample covariance. This approximation can understate optionality and tail dependence. Volatility is an input to VaR, not VaR itself.

## 10. Monte Carlo

The default is 10,000 simulations with seed 42 and zero factor drift. The symmetric eigen decomposition `Σ=QΛQ′` provides a square root `Q√Λ`; independent standard normal draws multiplied by its transpose recover the sample covariance. This supports singular positive-semidefinite covariance. Material negative eigenvalues or asymmetry are rejected; only tiny numerical negative eigenvalues are clipped to zero.

Correlated log-price/log-FX shocks keep prices positive. Rates, spreads and volatility use correlated Gaussian absolute changes. Each scenario produces a fully repriced security and portfolio P&L, then VaR and ES use the same empirical tail estimator as historical simulation. In a zero-log-drift model, expected simple return is slightly positive through the exponential/Jensen effect. There is no estimated risk premium and no claim of exactly zero expected P&L. Repeated calls with the same inputs/seed reproduce the scenarios; small floating-point changes across numerical library versions remain possible.

The engine intentionally supports one-day instantaneous market risk only. It does not silently apply square-root-of-time scaling to nonlinear instruments. Longer horizons require specifying factor dynamics, calendar carry, rebalancing and liquidity.

## 11. Stress testing

`config/scenarios.yaml` specifies recession, inflation, credit crisis, equity crash and custom shocks. Simple equity/FX shock decimals are transformed to log shocks; rates/spreads in bp are divided by 10,000. Implied-volatility shocks are absolute decimals: +0.15 is +15 percentage points. `factor_shocks` overrides individual factors using their native risk coordinates (log changes or absolute decimals).

Scenario P&L incorporates cross effects such as an equity fall combined with USD appreciation and fully reprices bonds/options. The Treasury ETF remains a price-return proxy rather than a look-through bond portfolio; its ETF price shock is explicit. Generic factor groups follow documented prefixes (`EQ_`, `ETF_`, `FX_`, `CAD_`, `USD_`, `SPREAD_`, `VOL_`). Scenarios are illustrative assumptions and have no estimated probability.

## 12. Two-date risk-change attribution

Both dates use independently cut-off return windows and market states. A common security universe includes zero quantities for entries/exits. The endpoint measure is 99% one-day parametric VaR. The economic blocks are:

1. Settled quantities/trades.
2. Market price levels.
3. FX levels.
4. Zero-rate and credit-spread levels.
5. Option implied-volatility levels.
6. Calibrated equity/ETF daily volatility.
7. Calibrated FX daily volatility.
8. Calibrated rate/spread daily volatility.
9. Other calibrated factor volatility.
10. Correlation.
11. Valuation date and calendar roll.

Covariance is decomposed as `diag(vol) × correlation × diag(vol)`. Replace prior blocks with current blocks sequentially, recording the incremental change in VaR after each replacement. Repeat in reverse order and average the two allocations. This reduces sensitivity to one arbitrary replacement order, but is not an all-permutations Shapley value. Recompute instrument sensitivities in each hybrid state.

The bridge reconciles algebraically, yet its economic allocations remain order/model dependent. The report separately evaluates each block changed alone. `interaction_vs_standalone = total change − sum(standalone changes)` shows the nonlinear interactions relative to that baseline. These interactions are already distributed in the averaged path contributions and must not be added again. `residual = total change − sum(allocated changes)` exposes numerical discrepancies instead of forcing a balancing driver. Hybrid states need not have occurred in markets; attribution is an explanation inside the chosen model, not a causal finding.

## 13. Controls, persistence and limitations

Controls run before risk estimation and after valuation. SQL keeps missing foreign keys and duplicate IDs from entering the relational database; the raw-frame control function can report such exceptions before import. Reports distinguish PASS, WARN and FAIL, with record, reason and action. FAIL blocks the risk result and stores exceptions in SQLite. Synthetic provenance and robust outliers are warnings. Position reconciliation checks both missing and excess holdings. Cash funding and value reconciliation are independent checks.

The daily report and dashboard consume the same calculated JSON/tables. SQL risk runs retain configuration, window, seed, source label, methodology and timestamp. Excel NAV/allocation/check formulas update from worksheet inputs; nonlinear risk measures are exported Python snapshots and require a new Python run. The workbook is not an independent financial pricing engine. Excel generation uses XlsxWriter from the declared Python dependencies. Formula opening values are cached during export, and Excel recalculates the live formulas on opening.

Known limits include: CAD/USD demonstration scope; no exchange-specific holiday calendars; no liquidity/transaction-cost model; no regulatory backtesting or stressed-calibration capital framework; no defaults, recovery, spread term structure, American options, volatility smile, swaps or automatic corporate-action ledger; hypothetical rather than realized multi-year performance; and noisy tails from a short estimation window. Imports require an internally consistent and sufficiently complete factor universe. The report must be rerun after a data change; a previously exported healthy report is not approval of newly modified database inputs.

## 14. Validation map

| Module | Evidence |
|---|---|
| Pricing | Independent zero/par prices, YTM round trips including negative yields, clean/dirty accrued interest, month-end schedule |
| Rate risk | Price/yield monotonicity, duration ordering, derivative DV01 and convexity; second-order approximation improves large-shock error |
| Options | Put-call parity, finite-difference delta/gamma/vega/theta, expiry/zero-vol limits |
| Returns / covariance | No fill across gaps, future-data exclusion, beta/drawdown identities, sample covariance validation |
| VaR / ES | Confidence ordering, volatility scaling, discrete fractional ES and ties, covariance recovery, seeded reproducibility |
| Contributions | Euler sum, marginal finite difference, negative hedge contribution, zero-net-risk convention |
| Stress / curves | Equity-crash sign, bond loss under rate rises, scalar versus vector curve price |
| Attribution | Isolated-driver and interaction examples, two-date endpoint and residual reconciliation |
| Operations | Missing/stale prices and FX, missing mappings/tenors, duplicate trades, invalid bonds, missing history, unfunded trades, position/value reconciliation |
| Reporting | Temporary-database end-to-end run, persisted failures, six dashboard pages/custom stress, Excel formulas and saved-sheet render review |
