# Institutional portfolio risk platform — implementation plan

Source of truth: `PROJECT_2_INSTITUTIONAL_RISK_CODEX_SPEC.md`, read in full from the supplied Downloads file on 2026-09-07. The repository initially contained only an empty `main.py` and no commits or repository instructions.

## Architecture

CSV / public-source market data + trades + security master → SQLite → dated positions → instrument pricing → portfolio analytics → factor risk → stress / curves → risk-change attribution → controls → daily Markdown report, Excel workbook, Streamlit dashboard.

Use readable functions in `src/` packages, pandas/NumPy/SciPy, SQLite's standard Python driver, YAML configuration, Plotly and Streamlit. No service framework or ORM. One shared full-repricing function prices equities, ETFs, cash, fixed-rate bonds and European options in CAD under a factor state. SQL stores raw observations, dated position snapshots, curves, trades, risk runs and exceptions. Reports consume saved calculations; they do not implement independent risk mathematics.

## Phases, dependencies and commit milestones

| Phase | Deliverables and dependency | Meaningful commit |
|---|---|---|
| 0 | This plan, configuration and reproducible package foundation | `chore: initialize institutional risk platform` |
| 1 | Schema, security master, trades, market/FX/curve data, import validation, deterministic labelled demo; depends on 0 | `feat: add security master and portfolio data pipeline` |
| 2 | Manual bond cash flows, clean/dirty price, YTM, duration, DV01, convexity; equity/FX and option Greeks; depends on 1 | `feat: build fixed income pricing and rate risk analytics` |
| 3 | Dated valuation, exposures, return history and benchmark metrics; depends on 2 | `feat: add portfolio valuation and performance analytics` |
| 4 | Historical, parametric and correlated Monte Carlo VaR/ES, Euler contributions; depends on 3 | `feat: implement portfolio VaR expected shortfall and contributions` |
| 5 | Full-repricing stress, key-rate curves, defensible two-date attribution, operational controls; depends on 4 | `feat: add stress attribution and operational risk controls` |
| 6 | Integrated daily run, persisted results, Markdown, Excel, dashboard and charts; depends on validated 1–5 | `feat: build daily risk reporting Excel model and dashboard` |
| 7 | Adversarial financial tests, reproducibility, methodology, exploratory notebooks and recruiter README/screenshots; depends on 6 | `test: validate integrated risk platform and document methodology` |

Each phase runs its relevant tests, resolves material failures, records evidence below and commits the coherent milestone. No phase is complete from execution alone.

## Module dependencies

`database` owns connections/schema and parameterized reads/writes. `data` owns source adapters, import contracts and sample generation. `pricing` depends only on scientific Python. `portfolio` combines database and pricing; `risk` accepts aligned finite factor changes and a pricing callback. `stress` reuses pricing. `attribution` reuses the parametric risk estimator and explicit economic state blocks. `controls` inspects both incoming tables and stored valuations. `reporting` and `dashboard` consume the same integrated run. Core modules never import dashboard code.

## Relational data model

- `portfolios`: ID, base currency; `security_master`: ID, type, currency, classification, bond terms, option terms and factor mappings.
- `trades`: unique ID, portfolio/security foreign keys, trade/settlement dates, signed quantity, local price, currency. Positions use settlement-date accounting; opening holdings are explicit trades.
- `positions`: composite date/portfolio/security key, quantity, local model price, FX conversion, base market value and book cost. Cash trades explicitly fund purchases; flows are not inferred as investment returns.
- `market_prices`: date/security key, unadjusted valuation price, adjusted return price, source and retrieved-at metadata.
- `fx_rates`: date/currency/base key, base-currency units per one foreign unit, provenance.
- `yield_curve`: date/curve/tenor key, decimal continuously compounded zero rate, provenance. Linear interpolation, flat endpoint extrapolation explicitly disclosed.
- `factor_levels`: date/factor key, level, kind (log-return or absolute change), source. Explicit price, FX, zero-rate, spread and option-volatility factors.
- `risk_results`: date/portfolio/method/confidence/horizon/run identity, currency, estimate, window, seed and assumptions. `quality_results`: run/check/severity/record/message/action.
- Foreign keys, checks and uniqueness constraints; transactional imports. Duplicate or unmapped raw trades are diagnosed before database insertion. SQL views: latest holdings and asset/currency/sector exposures, stale prices and trade completeness. Queries also demonstrate reconciliation, missing prices, credit ratings and near maturities.

## Financial methodology and conventions

- Dates: ISO dates, settlement-date positions, no observations after valuation date. Daily risk uses trailing 252 synchronized business-day factor changes; never forward-fill history. Latest valuation quotes have a bounded business-day age; missing/stale critical inputs block an approved run.
- Money: CAD base by default, foreign FX quoted CAD per foreign unit. Quantity is units/contracts; bonds use face amount per unit, options explicit multiplier. Prices are local currency per unit; portfolio values and losses are base currency. Yields/volatilities/returns use decimals; 1 bp = 0.0001. P&L is positive for gains, VaR/ES are nonnegative loss statistics.
- Bonds: regular coupons generated backward from maturity, Actual/Actual coupon-period fractional timing, no irregular stubs/ex-coupon calendars. Dirty price is discounted remaining contractual cash flows, clean = dirty − accrued. Nominal annual YTM compounded at coupon frequency; root solve with valid negative-yield domain. Macaulay = PV-weighted years; modified = Macaulay/(1+y/m); convexity from analytic second derivative; positive long-position DV01 = [P(y−1bp)−P(y+1bp)]/2. Curves use continuous zero discounting plus constant spread, distinct from YTM quoting.
- Options: European Black–Scholes with dividend yield; transparent analytical Greeks, time ACT/365, fixed implied volatility in ordinary history unless a volatility factor is supplied; full repricing under shocks.
- Performance: simple returns, 252-day annualization, aligned benchmark, sample covariance (ddof=1). Clearly distinguish frozen-holdings hypothetical returns from realized portfolio performance. Report volatility, beta, Sharpe, drawdown, tracking error and information ratio with defined risk-free rate.
- Historical risk: apply each observed log-price/log-FX and absolute-rate/spread/volatility shock to today's state and fully reprice. One-day static instantaneous market shocks, no passage of time/carry. 95%/99% empirical inverse-CDF quantile; ES uses exactly the worst tail probability with fractional boundary weight.
- Parametric: zero-drift Gaussian factor changes, sample covariance, finite-difference instrument sensitivities. VaR = z sqrt(g'Σg); normal ES = φ(z)/(1−α) × sigma. Euler component VaR sums to total; marginal VaR is per additional security unit. Negative hedge contributions allowed.
- Monte Carlo: 10,000 simulations default, fixed seed, zero drift, sample covariance, symmetric eigen square root handles singular PSD matrices; reject materially indefinite matrices. Correlated log-price/FX and absolute rates/spreads/volatility, full instrument repricing, historical-tail estimator for VaR/ES. Any volatility-floor boundary disclosed. No unsupported multi-day square-root scaling.
- Stress: named recession, inflation, credit crisis, equity crash and custom YAML factor shocks; curve parallel up/down and tenor-dependent steepener/flattener. Full repricing with duration/delta approximation comparison.
- Attribution: compare two independent as-of calibrations. Replace positions, prices, FX, rate/spread levels, volatility-factor levels, calibrated factor volatilities, correlation and valuation date in explicit blocks. Average forward/reverse replacement paths to reduce ordering dependence; report interactions relative to one-at-a-time effects and numerical residual separately. This is a model-based allocation, not causal identification. Common instrument/factor universe includes zero quantities for entrants/exits.

## Validation requirements

Reject nonfinite or invalid inputs, future observations, unmapped securities/factors/currencies, unsupported bond terms, invalid covariance and insufficient history. Controls detect stale/missing prices and FX, duplicate trades, missing security master, invalid bond/option terms, currency mismatches, shorts where prohibited, position/trade and market-value reconciliation, missing history and outliers. Preserve exceptions in reports; do not quietly drop positions. Report valuation date, currency, confidence, horizon, window and methodology alongside risk.

## Testing strategy

Unit tests: independent zero/par bond benchmarks, negative yield and YTM round trips, accrued/clean/dirty consistency, price monotonicity, duration derivative, convexity improvement, option put-call parity/Greek finite differences. Portfolio tests: FX and position units, date cutoffs, missing history and annualization. Risk tests: finite inputs, confidence ordering, volatility scaling, exact weighted-tail ES, seeded MC reproducibility/correlation recovery, nonlinear repricing and component/marginal reconciliation. Institutional tests: stress signs, key-rate interpolation, attribution identity and isolated drivers, every material quality failure. Integration: temporary SQLite end-to-end run, report totals and SQL joins, workbook formulas/recalculation/render review, Streamlit AppTest, clean installation and documented CLI commands. Network tests are optional and never make offline tests flaky.

## Completion checklist and evidence

- [x] Specification fully read; repository inspected; plan created before implementation.
- [x] Phase 0: runnable package/configuration foundation.
- [x] Phase 1: relational database, meaningful SQL, market imports, security master, trades and labelled sample data.
- [ ] Phase 2: bond price, YTM, Macaulay/modified duration, DV01, convexity, option and FX valuation validated.
- [ ] Phase 3: portfolio values, exposures and return/performance calculations validated.
- [ ] Phase 4: historical/parametric/Monte Carlo VaR, ES and marginal/component risk validated.
- [ ] Phase 5: stress, yield curves, risk-change attribution, data/trade quality controls validated.
- [ ] Phase 6: daily report, professional Excel workbook, interactive dashboard and charts generated/verified.
- [ ] Phase 7: all tests pass, methodology and recruiter README complete, screenshots and clean-run verification.
- [ ] Definition of done: all specification section 30 requirements verified; no synthetic data represented as real.

## Progress log

Planning: no pre-existing implementation or Git history. Available Python 3.13 has NumPy, pandas, SciPy, pytest, Streamlit, Plotly and YAML. Next step: create the runnable package and database/data phase.



Phase 1: 3 tests pass, including atomic import rollback and settlement-date cutoffs. Generated labelled deterministic CSV inputs. Public-data adapter preserves source URL, timestamps and raw response.
