# Validation record

The public snapshot was fetched on 2026-09-12 from Yahoo Finance (XIU.TO, SPY, TLT, ^VIX), Bank of Canada (FXUSDCAD and Canadian zero curves), Federal Reserve GSW (USD zero curves), and FRED BAMLC0A0CM (investment-grade OAS proxy). The cached valuation uses 2026-08-25 and 2026-08-26 with 252 synchronized daily observations and 10,000 Monte Carlo scenarios.

`python -m pytest -q` passes all 49 tests. The suite covers direct bond pricing/YTM/duration/DV01/convexity, option Greeks, portfolio valuation and settlement, covariance, historical/parametric/Monte Carlo VaR, Expected Shortfall, Euler contributions, stress and curve scenarios, attribution, controls, source parsing and units, failed-source behavior, cache checksums, the public-data integration run, dashboard pages, and workbook formulas.

The generated public-data run produced CAD 110,459,484.49 NAV. 99% one-day VaR was CAD 1,043,864.75 historical, CAD 1,028,740.69 parametric, and CAD 1,000,385.01 Monte Carlo. Component VaR reconciled to parametric VaR; ES exceeded VaR; +100 bp curve shocks lost money on both hypothetical bonds; and the equity-crash scenario produced negative P&L for XIU.TO and SPY.

The Excel workbook has 16 sheets, four independent checks marked PASS, and no formula errors. A saved workbook render was inspected for the Cover, Daily Report, Portfolio Summary, Risk Attribution, and Checks sheets. The Streamlit dashboard was opened locally and verified to show the public-data label, cached as-of date, real tickers, holdings, source status, and attribution chart.

Two Canadian 1Y/2Y rate moves remain WARN outliers and are retained because they are source observations, not silently removed data. The USD corporate spread is an index-level proxy; VIX is not contract-specific implied volatility; bond and European SPY call terms are hypothetical; and public feeds can be revised. CSV caches are excluded from Git and a fresh checkout must run an explicit refresh.
