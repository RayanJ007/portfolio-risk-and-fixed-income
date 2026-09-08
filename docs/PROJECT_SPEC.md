# CODEX BUILD SPECIFICATION
# Project 2: Institutional Portfolio Risk & Fixed-Income Analytics Engine

## 1. Objective

Build a recruiter-ready **institutional market-risk and financial-engineering platform** that models a multi-asset investment portfolio and answers:

> **What risks is this portfolio exposed to, what is driving changes in risk, and how would the portfolio behave under historical and hypothetical market shocks?**

This is not a generic stock-price predictor.

The project should resemble a simplified version of the analytics workflow used by:
- Pension funds
- Asset managers
- Treasury / capital-markets teams
- Investment-risk teams
- Financial-risk departments
- Public debt-management organizations
- Banks and insurers

The project must demonstrate:
- Portfolio construction and position handling
- Market-data ingestion
- SQL-based data organization
- Fixed-income pricing
- Yield / duration / convexity / DV01
- Portfolio performance metrics
- Historical VaR
- Parametric VaR
- Monte Carlo VaR
- Expected Shortfall
- Marginal / Component risk contribution
- Stress testing
- Yield-curve scenarios
- Risk-change attribution
- Trade and market-data quality controls
- Python
- SQL
- Excel
- Power BI or Streamlit
- Optional VBA

The finished repository should be appropriate for roles in:
- Risk analytics
- Market risk
- Financial risk
- Asset management
- Portfolio analytics
- Financial engineering
- Treasury
- Quantitative finance
- Investment operations / middle office

---

# 2. Codex Operating Instructions

Act as:
1. an institutional risk analyst,
2. a financial-engineering developer,
3. and a data engineer.

Do not stop after creating files or skeletons.

Implement the complete core workflow and validate the results.

### General rules
- Make sensible assumptions without repeatedly requesting user input.
- Document all assumptions.
- Never fabricate real historical market data.
- If live-market retrieval is unavailable, provide a documented local-data import path.
- Keep positions, security master, trades, market data, calculations, and reports separated.
- Store structured data in SQL.
- Build modular Python code.
- Write tests for core pricing and risk formulas.
- Prioritize transparent financial calculations.
- Avoid unnecessary black-box libraries for concepts that should be demonstrable.
- QuantLib may be used for validation or advanced extensions, but core bond mathematics should be implemented directly first.
- Avoid look-ahead bias.
- Ensure calculations use internally consistent units, dates, currencies, and return conventions.
- The system must be reproducible from a clean environment.

Before coding:
1. Create `PLAN.md`
2. Create implementation phases
3. Create a TODO checklist
4. Build sequentially
5. Keep the checklist updated

---

# 3. Core Business Question

The platform should be able to answer questions such as:

- What is the current portfolio market value?
- What assets and risk factors dominate the portfolio?
- What is the one-day 95% and 99% VaR?
- What is Expected Shortfall?
- Which positions contribute most to risk?
- How does portfolio risk change when interest rates move?
- What happens under a recession, inflation shock, credit crisis, or equity crash?
- How much does each bond lose if yields rise by 1 bp?
- Why is today's VaR different from yesterday's?
- Are any prices stale, trades missing, or data fields invalid?

---

# 4. Portfolio Design

Create a configurable sample institutional portfolio.

Recommended notional portfolio value:

```text
CAD 100,000,000
```

Include multiple asset/risk types.

Example allocation:

```text
Canadian Equities
US Equities
Canadian Government Bonds
Canadian Corporate Bonds
US Treasury / Fixed Income ETF
Cash
USD FX Exposure
One vanilla option position
Optional interest-rate swap
```

The exact instruments should remain configurable.

Create files such as:

```yaml
portfolio:
  base_currency: CAD
  as_of_date: YYYY-MM-DD
```

and structured position data containing:
- Security ID
- Ticker
- Asset class
- Currency
- Quantity
- Price
- Market value
- Portfolio
- Sector
- Country
- Duration if fixed income
- Credit rating if available
- Benchmark
- Risk-factor mapping

---

# 5. Suggested Repository Structure

```text
institutional-risk-engine/
│
├── README.md
├── PLAN.md
├── requirements.txt
├── .gitignore
├── config/
│   ├── portfolio.yaml
│   ├── scenarios.yaml
│   └── database.yaml
│
├── data/
│   ├── raw/
│   ├── processed/
│   ├── sample/
│   └── README.md
│
├── sql/
│   ├── schema.sql
│   ├── views.sql
│   └── sample_queries.sql
│
├── src/
│   ├── __init__.py
│   ├── data/
│   │   ├── market_data.py
│   │   ├── trades.py
│   │   ├── security_master.py
│   │   └── validation.py
│   ├── database/
│   │   ├── connection.py
│   │   ├── models.py
│   │   └── repository.py
│   ├── pricing/
│   │   ├── bonds.py
│   │   ├── equities.py
│   │   ├── options.py
│   │   ├── fx.py
│   │   └── swaps.py
│   ├── portfolio/
│   │   ├── positions.py
│   │   ├── returns.py
│   │   └── performance.py
│   ├── risk/
│   │   ├── var_historical.py
│   │   ├── var_parametric.py
│   │   ├── var_monte_carlo.py
│   │   ├── expected_shortfall.py
│   │   ├── risk_contribution.py
│   │   └── factor_risk.py
│   ├── stress/
│   │   ├── scenarios.py
│   │   ├── yield_curve.py
│   │   └── repricing.py
│   ├── attribution/
│   │   └── risk_change.py
│   ├── controls/
│   │   └── data_quality.py
│   ├── reporting/
│   │   ├── excel_export.py
│   │   ├── charts.py
│   │   └── daily_report.py
│   └── utils/
│       └── helpers.py
│
├── notebooks/
│   ├── 01_portfolio_overview.ipynb
│   ├── 02_fixed_income.ipynb
│   ├── 03_var_analysis.ipynb
│   └── 04_stress_testing.ipynb
│
├── dashboard/
│   └── app.py
│
├── models/
│   ├── risk_reporting_model.xlsx
│   └── vba/
│       ├── RefreshData.bas
│       └── ExportRiskReport.bas
│
├── reports/
│   └── risk_methodology.md
│
├── tests/
│   ├── test_bonds.py
│   ├── test_duration.py
│   ├── test_var.py
│   ├── test_stress.py
│   └── test_data_quality.py
│
└── outputs/
    ├── charts/
    ├── reports/
    └── tables/
```

---

# 6. Database Design

Use SQLite or PostgreSQL.

SQLite is acceptable for easy local execution.

Create tables similar to:

## `security_master`
- security_id
- ticker
- name
- asset_class
- security_type
- currency
- sector
- country
- maturity_date
- coupon_rate
- coupon_frequency
- face_value
- credit_rating
- benchmark

## `positions`
- as_of_date
- portfolio_id
- security_id
- quantity
- book_cost
- market_price
- market_value

## `trades`
- trade_id
- trade_date
- settlement_date
- security_id
- buy_sell
- quantity
- price
- currency
- portfolio_id

## `market_prices`
- date
- security_id
- price
- source
- retrieval_timestamp

## `fx_rates`
- date
- currency_pair
- rate

## `yield_curve`
- date
- curve_name
- tenor
- rate

## `risk_results`
- as_of_date
- portfolio_id
- risk_measure
- confidence_level
- horizon
- value

Create SQL views for:
- current portfolio
- exposure by asset class
- exposure by currency
- exposure by sector
- stale prices
- trade completeness

---

# 7. Market Data Pipeline

Acquire historical data for:
- Equity prices
- ETF prices
- FX
- Interest-rate / yield data where feasible
- Volatility if needed

Store retrieval metadata.

Requirements:
- No look-ahead bias
- Adjust corporate-action data consistently
- Clearly distinguish prices and returns
- Use business-day indexing
- Handle missing observations
- Document interpolation if used

If a live source cannot provide bond prices or curves, create an import format using real externally sourced CSV data.

Never silently fabricate missing market history.

---

# 8. Fixed-Income Pricing Engine

This is a major part of the project.

Implement the bond mathematics manually.

## 8.1 Bond price

For a plain fixed-rate bond:

```text
P = sum(CF_t / (1 + y/m)^(m*t))
```

Support:
- Face value
- Coupon rate
- Coupon frequency
- Settlement date
- Maturity date
- Yield
- Clean price / dirty price if practical
- Accrued interest if practical

## 8.2 Yield to Maturity

Solve numerically for YTM given price.

Use a robust root solver.

## 8.3 Macaulay Duration

Calculate weighted average cash-flow timing.

## 8.4 Modified Duration

```text
Modified Duration =
Macaulay Duration / (1 + y/m)
```

## 8.5 DV01

Calculate dollar price sensitivity to a 1 bp change in yield.

Support both:
- Duration approximation
- Full repricing check

## 8.6 Convexity

Calculate convexity.

Use it to improve price-change approximation:

```text
ΔP/P ≈ -D_mod × Δy + 0.5 × Convexity × (Δy)^2
```

Compare approximation against full repricing.

---

# 9. Optional Derivatives Module

Implement at least one vanilla derivative.

Recommended:
- European option using Black-Scholes

Inputs:
- Spot
- Strike
- Time to maturity
- Risk-free rate
- Volatility
- Dividend yield

Calculate:
- Price
- Delta
- Gamma
- Vega
- Theta

Optional:
- Interest-rate swap valuation

Keep derivative exposure small relative to the main portfolio.

---

# 10. Portfolio Analytics

Calculate:

## Exposure
- Market value
- Weight
- Asset-class exposure
- Currency exposure
- Sector exposure
- Geographic exposure

## Return metrics
- Daily returns
- Cumulative return
- Annualized return

## Risk metrics
- Volatility
- Beta
- Sharpe ratio
- Maximum drawdown
- Tracking error
- Information ratio if benchmark exists

Document annualization assumptions.

---

# 11. Historical VaR

Implement historical simulation VaR.

For each historical date:
1. Compute historical risk-factor/asset returns
2. Apply return shock to current portfolio exposures
3. Estimate portfolio P&L
4. Build empirical P&L distribution
5. Extract VaR percentile

Calculate:
- 95% VaR
- 99% VaR
- 1-day horizon

Optional:
- 10-day scaling with appropriate caveat

Display loss with a consistent sign convention.

Document the convention clearly.

---

# 12. Parametric VaR

Implement variance-covariance VaR.

Portfolio variance:

```text
σ_p² = w' Σ w
```

Portfolio volatility:

```text
σ_p = sqrt(w' Σ w)
```

VaR:

```text
VaR = z × σ_p × portfolio_value
```

Calculate:
- 95%
- 99%

Support:
- normal-return assumption
- covariance matrix

Document limitations:
- normality
- linearity
- unstable covariance
- tail risk

---

# 13. Monte Carlo VaR

Implement a Monte Carlo engine.

Required:
- Estimate expected returns or use zero-drift for short-horizon risk
- Estimate covariance matrix
- Generate correlated random shocks
- Use Cholesky decomposition or equivalent
- Simulate at least 10,000 scenarios by default
- Revalue portfolio
- Produce P&L distribution
- Calculate 95% and 99% VaR
- Calculate Expected Shortfall

Use a random seed for reproducibility.

For nonlinear instruments, reprice rather than applying only delta approximation where feasible.

---

# 14. Expected Shortfall

For confidence level α:

```text
ES = average loss conditional on loss exceeding VaR threshold
```

Calculate:
- Historical ES
- Monte Carlo ES

Explain why Expected Shortfall is useful:
VaR identifies a threshold; ES measures the average severity beyond that threshold.

---

# 15. Risk Contribution

Implement:

## Component VaR
How much each position or risk bucket contributes to total VaR.

## Marginal VaR
Approximate change in total VaR from a small increase in a position.

Provide contribution by:
- Security
- Asset class
- Currency
- Sector where possible

Check:

```text
Sum(Component VaR) ≈ Portfolio VaR
```

for the methodology where this identity applies.

---

# 16. Stress Testing Engine

Build scenario-based full or approximate repricing.

Scenarios should live in:

`config/scenarios.yaml`

Create at least:

## Recession Shock
Example:
- Equities: -25%
- Corporate-credit spreads: +200 bp
- Government yields: -75 bp
- CAD depreciation: scenario-defined
- Implied volatility: higher

## Inflation Shock
Example:
- Rates: +150 bp
- Long-duration equities: negative shock
- Credit spreads: wider
- CAD movement: configurable

## Credit Crisis
Example:
- Equities: -35%
- Credit spreads: +400 bp
- Government yields: lower
- Volatility: sharply higher

## Equity Crash
Example:
- Equity indices: -30%
- Volatility: +major shock
- Credit spreads: wider

## User-Defined Scenario
Allow arbitrary shocks.

Output:
- Portfolio P&L
- P&L by asset class
- P&L by security
- Largest contributors
- New portfolio value

---

# 17. Yield-Curve Scenario Engine

Build fixed-income curve shocks.

At minimum:

### Parallel up
```text
+100 bp
```

### Parallel down
```text
-100 bp
```

### Bear steepener
Short and long rates move differently.

### Bull flattener
Short and long rates move differently.

### Custom key-rate shock
Optional but desirable.

For each scenario:
- Reprice bonds
- Calculate position P&L
- Calculate portfolio P&L
- Compare duration approximation vs full repricing

---

# 18. Risk-Change Attribution

This is a flagship feature.

The system must compare risk between two dates:

```text
Prior-day risk
vs
Current-day risk
```

Example:

```text
VaR yesterday: 2.85M
VaR today:     3.14M
Change:        +0.29M
```

Attribute the change to major drivers such as:
- New trades / position changes
- Equity volatility changes
- FX exposure
- Interest-rate volatility
- Correlation / covariance changes
- Market-price movement
- Diversification effects

A perfect exact attribution is not required if decomposition mathematics become extremely complex.

However:
- Use a defensible methodology
- Document residual / interaction effects
- Do not falsely claim exact attribution if it is approximate

Output a waterfall-style attribution chart.

---

# 19. Data-Quality & Operational Controls

Create an automated control framework.

Flag examples:

```text
Missing market price
Stale market price
Duplicate trade
Missing security master entry
Unknown currency
Missing FX rate
Invalid maturity date
Negative quantity where not allowed
Portfolio market-value mismatch
Position not mapped to asset class
Bond missing coupon / maturity
Missing return history
Outlier market move
```

Create a daily quality summary:

```text
PASS
WARN
FAIL
```

Provide:
- Check ID
- Severity
- Security / record
- Description
- Suggested action

This is an important institutional feature.

---

# 20. Trade Completeness

Build checks such as:
- Trade exists in trade table
- Settled trade appears in positions
- Position changes reconcile to trades where feasible
- New security has a security-master record
- Trade currency matches security definition
- Market data available for new positions

Create exceptions report.

---

# 21. Daily Risk Report

Generate a daily report in Markdown/HTML and optionally Excel.

Include:

## Portfolio Summary
- NAV
- Daily P&L
- Asset allocation

## Risk Summary
- Historical VaR
- Parametric VaR
- Monte Carlo VaR
- Expected Shortfall

## Top Risk Contributors

## Fixed-Income Risk
- Duration
- DV01
- Convexity

## Stress Results

## Risk Change Attribution

## Data Quality
- PASS/WARN/FAIL counts

## Key Alerts

Keep commentary concise and analyst-like.

---

# 22. Dashboard

Build a professional Streamlit dashboard.

Suggested pages:

## 1. Portfolio Overview
- NAV
- Allocation
- Performance
- Top holdings

## 2. Market Risk
- VaR comparison
- ES
- P&L distribution
- Risk contribution

## 3. Fixed Income
- Yield
- Duration
- DV01
- Convexity
- Curve-shock P&L

## 4. Stress Testing
- Scenario selector
- Portfolio P&L
- Contribution

## 5. Risk Attribution
- Today vs yesterday
- Driver decomposition

## 6. Data Quality
- Exceptions
- Stale data
- Missing records

Dashboard should be clean, not flashy.

---

# 23. Excel Risk Report

Generate:

`models/risk_reporting_model.xlsx`

Suggested sheets:

```text
Cover
Positions
Trades
Security Master
Market Data
Portfolio Summary
Fixed Income
VaR
Expected Shortfall
Risk Contribution
Stress Tests
Yield Curve
Risk Attribution
Data Quality
Daily Report
Checks
```

Use:
- PivotTables where practical
- XLOOKUP / formulas
- Conditional formatting for controls
- Professional number formats
- Clear historical/current dates

## Optional VBA

Include `.bas` scripts for:
- Refreshing imported data
- Running report export
- Clearing filters
- Scenario reset

VBA should not be required for core analytics.

---

# 24. SQL Demonstration

Create `sql/sample_queries.sql` demonstrating meaningful finance queries.

Examples:

### Exposure by asset class

```sql
SELECT
    sm.asset_class,
    SUM(p.market_value) AS exposure
FROM positions p
JOIN security_master sm
    ON p.security_id = sm.security_id
GROUP BY sm.asset_class;
```

Also include queries for:
- Currency exposure
- Largest holdings
- Stale market data
- New trades
- Bonds maturing within one year
- Credit-rating distribution
- Missing market prices
- Daily position reconciliation

---

# 25. README Requirements

The README should communicate value quickly.

Include:

1. Project title
2. One-sentence description
3. Business problem
4. Architecture diagram
5. Portfolio design
6. Risk methodologies
7. Fixed-income analytics
8. Stress testing
9. Risk attribution
10. Data-quality framework
11. Dashboard screenshots
12. Tech stack
13. How to run
14. Key findings
15. Methodology caveats
16. Repository structure

Suggested opening:

> A multi-asset institutional risk platform that ingests positions and market data, prices fixed-income instruments, calculates VaR and Expected Shortfall, runs stress scenarios, attributes changes in portfolio risk, and performs automated data-quality controls.

---

# 26. Methodology Documentation

Create:

`reports/risk_methodology.md`

Explain:

## Market risk
- VaR
- Expected Shortfall
- Confidence levels
- Horizon

## Fixed income
- Pricing
- Duration
- DV01
- Convexity

## Monte Carlo
- Return assumptions
- Correlation generation
- Simulation process

## Stress testing

## Risk contribution

## Risk attribution

## Limitations

Write so a finance student could use the document to learn the project later.

---

# 27. Testing Requirements

## Bond tests
- Zero-coupon bond price
- Par bond prices near par when coupon ≈ yield
- Price falls when yield rises
- Price rises when yield falls

## Duration
- Longer maturity generally increases duration, all else equal
- Higher yield generally lowers duration, all else equal
- DV01 direction is correct

## Convexity
- Convexity adjustment improves approximation for larger rate shocks

## VaR
- VaR non-negative under chosen loss convention
- 99% VaR >= 95% VaR for same methodology
- Higher volatility should generally increase VaR

## Monte Carlo
- Reproducible under fixed random seed
- Correlation structure approximately recovered with sufficient simulations

## Stress
- Equity crash produces negative equity P&L
- Rate increases reduce plain fixed-rate bond prices

## Controls
- Missing prices are detected
- Duplicate trades are detected
- Missing security mappings are detected

---

# 28. Risk-Methodology Rules

Do not:
- Call volatility "VaR"
- Mix returns and prices
- Mix percentage and decimal units
- Mix CAD and USD without FX conversion
- Use future data to estimate earlier risk
- Assume normal distributions without documenting the assumption
- Report VaR without confidence level and horizon
- Treat diversification effects as independent additive risks without justification
- Use duration alone for large nonlinear rate shocks when full repricing is available
- Hide missing data by forward-filling indefinitely

All outputs must state:
- As-of date
- Base currency
- Confidence level where relevant
- Horizon
- Methodology

---

# 29. Key Recruiter-Facing Features

The finished project should make the following immediately visible:

### Finance / Risk
- Bond pricing
- YTM
- Duration
- DV01
- Convexity
- VaR
- CVaR / Expected Shortfall
- Stress testing
- Portfolio risk contribution
- Risk-factor analysis
- Risk attribution

### Technical
- Python
- pandas
- NumPy
- SciPy
- SQL
- SQLite/PostgreSQL
- Streamlit
- Excel
- Optional VBA

### Operational Risk Analytics
- Trade completeness
- Market-data quality
- Daily risk reporting
- Exception reporting

---

# 30. Definition of Done

Do not consider the repository complete until:

- [ ] Portfolio data model exists
- [ ] SQL database works
- [ ] Security master works
- [ ] Market data pipeline works
- [ ] Position valuation works
- [ ] Bond-pricing engine works
- [ ] YTM works
- [ ] Duration works
- [ ] DV01 works
- [ ] Convexity works
- [ ] Portfolio analytics work
- [ ] Historical VaR works
- [ ] Parametric VaR works
- [ ] Monte Carlo VaR works
- [ ] Expected Shortfall works
- [ ] Risk contribution works
- [ ] Stress engine works
- [ ] Yield-curve scenarios work
- [ ] Risk-change attribution works
- [ ] Data-quality controls work
- [ ] Trade checks work
- [ ] Daily risk report works
- [ ] Excel report is generated
- [ ] Streamlit dashboard works
- [ ] Tests pass
- [ ] README is polished
- [ ] Methodology documentation exists
- [ ] No fabricated real-market data is present
- [ ] Project can run from documented commands

---

# 31. Build Order

### Phase 1 — Foundation
- Repo structure
- Config
- SQL schema
- Security master
- Positions
- Trades
- Market data

### Phase 2 — Pricing
- Equity / FX valuation
- Bond pricing
- YTM
- Duration
- DV01
- Convexity
- Optional derivative

### Phase 3 — Portfolio analytics
- Exposures
- Returns
- Volatility
- Beta
- Sharpe
- Drawdown

### Phase 4 — Risk
- Historical VaR
- Parametric VaR
- Monte Carlo VaR
- Expected Shortfall
- Risk contribution

### Phase 5 — Institutional analytics
- Stress testing
- Yield-curve scenarios
- Risk-change attribution
- Data-quality controls
- Trade completeness

### Phase 6 — Reporting
- Daily report
- Excel
- Streamlit
- Charts

### Phase 7 — Quality
- Tests
- README
- Methodology
- Final reproducibility check
- Refactoring

---

# 32. Final Codex Instruction

Build this as a **simplified institutional risk platform**, not as a collection of disconnected formulas.

The central workflow should be:

```text
Market Data + Trades + Security Master
                ↓
             SQL Layer
                ↓
        Current Positions
                ↓
            Pricing
                ↓
        Portfolio Analytics
                ↓
        Market Risk Engine
                ↓
   Stress / Curve / Attribution
                ↓
       Data Quality Controls
                ↓
     Daily Risk Report + Dashboard
```

The strongest parts of the project should be:
1. financial correctness,
2. risk methodology,
3. risk-change attribution,
4. fixed-income analytics,
5. data-quality / operational controls,
6. clear reporting.

The final result should be something the student can later study module-by-module and eventually explain in an interview from raw market data through portfolio-risk conclusions.
