# Validation record

Validated on September 8, 2026, Windows, Python 3.13.9. Exact clean-environment package versions are recorded in `requirements-lock.txt`.

## Reproducibility

- Created a new `.venv` without inheriting system packages.
- Installed the project from `requirements.txt` using the package registry.
- Ran `.venv\Scripts\python.exe -m pytest -q`: **36 passed**.
- Ran `.venv\Scripts\python.exe -m pip check`: no broken requirements.
- Ran the demo with a fresh database and newly generated CSVs in `outputs/clean_validation/`: NAV CAD 101,390,515.87 and the same rounded VaR/ES results as the baseline.
- Ran both `demo` and `mixed-demo` successfully with no FAIL controls.
- Parsed all source/dashboard Python modules and ran `git diff --check`.
- Validated the four notebook files and executed every code cell against generated demo outputs.

## Financial checks

The automated suite includes independent bond prices, negative-yield YTM round trips, accrued interest, month-end scheduling, derivative checks for DV01 and convexity, option put-call parity and Greeks, future-data cutoffs and missing-day returns, covariance positive-semidefiniteness, Monte Carlo seed/correlation recovery, fractional empirical ES, VaR scaling, marginal/Euler contribution reconciliation, negative hedge contributions, full-repricing stress signs, attribution interactions and endpoint reconciliation, average acquisition cost after sales, option multipliers, and raw/SQL operational exceptions.

The baseline uses 10,000 Monte Carlo simulations with seed 42, 252 synchronized daily observations, CAD base currency and a one-day instantaneous risk horizon. A separate 100,000-draw test checks that simulated correlation and covariance recover their specified inputs within sampling tolerances. The sample position ledger includes the bonds' August 31 coupon receipts, avoiding a false P&L loss on the payment date.

## Reporting checks

Streamlit AppTest exercises all six pages and the interactive custom scenario. The local app was also inspected visually in the browser, including readable KPI values, holdings and the risk-change waterfall. Screenshots in `docs/images/` are captures of the working app, not mockups.

The 16-sheet Excel workbook was exported with the artifact runtime. NAV, component VaR, attribution and position weights pass independent checks. A temporary quantity change updated NAV before the original input was restored. The formula scan found no errors; saved formulas, the allocation chart, table structure, number formats and freeze panes were checked. All sheet previews were visually reviewed; the saved workbook was reopened and its allocation chart rendered successfully. These checks do not claim automation of the native Microsoft Excel application.

## Supported environment and limitations

Python installation, analytics, tests and dashboard are independently reproducible with the declared Python dependencies. Excel regeneration additionally requires the documented Codex artifact Node runtime; opening the delivered `.xlsx` does not. The workbook has formula-linked valuation summaries and Python risk snapshots, not a second Monte Carlo engine.

The portfolio and most market factors are synthetic. Actual Bank of Canada FX observations are archived with provenance and are used in the separate mixed-data run. Neither dataset is presented as a fully real historical portfolio. The supported reporting base is CAD, with CAD/USD holdings. Other methodology limitations are listed in `risk_methodology.md`; no optional swap, VBA, regulatory capital or realized strategy-backtest functionality is claimed.
