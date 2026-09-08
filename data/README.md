# Data and import contract

`sample/` contains fictional instruments, holdings and seeded synthetic market history. Every market row identifies itself as synthetic. `raw/boc_usdcad.csv` and the accompanying raw JSON contain actual Bank of Canada USD/CAD observations downloaded on September 7, 2026. The CSV includes the request URL and retrieval timestamp. The [Valet API documentation](https://www.bankofcanada.ca/valet/docs/) is the source reference. Real observations are never fabricated or filled to match the demo calendar.

Run `python main.py demo` for a fully reproducible synthetic example, or `python main.py mixed-demo` to combine the archived real FX with synthetic other markets. The mixed run uses `data/mixed_risk.db`, `data/mixed_sample/` and `outputs/mixed/`; it does not overwrite the synthetic database. Run `python main.py fetch-fx` to refresh the raw archive from the public API, when networking is available. Existing demo databases are reused, not silently reimported after CSV changes. To test different inputs, choose a new database path.

## Import a portfolio

Prepare the following seven CSVs in one directory; use the sample files for exact headers and `sql/schema.sql` for column constraints. Imports are atomic and append-only; duplicate keys fail rather than overwrite history.

| File | Key / required meaning |
|---|---|
| `portfolios.csv` | Unique `portfolio_id`, three-letter `base_currency` |
| `security_master.csv` | Unique `security_id`, type, currency, classification, multiplier, and applicable bond/option/factor terms |
| `trades.csv` | Unique ID, portfolio/security, trade and settlement dates, signed quantity, local execution price, currency, type |
| `market_prices.csv` | Date/security key; positive unadjusted and adjusted prices, source, retrieval timestamp |
| `fx_rates.csv` | Date/currency/base key; base units per foreign unit, source, timestamp |
| `yield_curve.csv` | Date/curve/tenor key; tenor in years, continuous zero rate decimal, source, timestamp |
| `factor_levels.csv` | Date/factor key; numeric level, `log` or `absolute` kind, source, timestamp |

```powershell
python main.py import --input data/my_import --database data/my_portfolio.db
python main.py run --config config/my_portfolio.yaml --database data/my_portfolio.db --output outputs/my_portfolio
```

Copy `config/portfolio.yaml` to your own config and set portfolio ID, dates, currency and calibration settings. Source paths are relative to the repository root. Use ISO dates and decimal yields/volatilities; do not put `%` or currency symbols in numeric fields. Blank bond/option-only fields are SQL NULL for other instruments. A bond quantity of 10,000 with face 100 represents 1 million face, not 10,000 face. An option quantity is contracts and its execution price is per underlying share.

Trade quantities are signed. `trade` entries require offsetting cash entries in the same currency/date; the system checks their net execution value. `opening` records establish holdings/capital. `external` identifies contributions/withdrawals. `income` identifies coupons/dividends/interest paid into cash. Closing bonds/options at maturity and booking proceeds are explicit ledger actions. A trade's settlement must not precede its trade date. Add securities before their trades within an import.

Factor naming is part of the simple model contract:

- `EQ_*`, `ETF_*`: positive price levels and log changes; match the adjusted return series. Current valuation takes the unadjusted quote.
- `FX_USD`: CAD per USD, with log changes. The reporting workflow currently supports CAD base currency and CAD/USD holdings.
- `CAD_<tenor>`, `USD_<tenor>`: continuous zero-rate decimals; e.g. `CAD_5`; absolute changes. Each mapped tenor must also exist in `yield_curve`.
- `SPREAD_*`: continuous credit spread decimals and absolute changes.
- `VOL_*`: annual implied-volatility decimals and absolute changes.

Use at least two increasing tenors per curve. Public benchmark bond yields are **not** zero rates: bootstrap a zero curve or explicitly import suitable externally sourced zero rates before populating this table. Do not silently use par yields as zero yields. Align price, FX and zero-curve factor observations with their source tables. Underlying spot and strike units must match for options; adjusted equity history may need a separately mapped actual-spot factor.

No automatic download is supplied for individual bond prices, zero curves or licensed equity feeds. The validated CSV path supports real externally sourced observations with provenance. Gaps remain missing. Complete common daily changes and dated valuation inputs are required; critical omissions block a risk run.

Raw duplicate/missing-map diagnostics can be inspected with `src.controls.data_quality.quality_checks(tables, date)` before SQL insertion. Database constraints provide a second line of defence. `sql/sample_queries.sql` shows exposure, missing-price, stale-quote, maturity, credit-rating and reconciliation queries; bind its named date parameters.
