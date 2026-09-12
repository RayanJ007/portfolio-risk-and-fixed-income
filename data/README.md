# Public data and import contract

The portfolio is hypothetical; its equity/ETF, FX, rates, spread and volatility histories come from public sources. No source failure falls back to generated prices. Synthetic market histories live only in `tests/fixtures/synthetic.py`.

## Sources and units

| File in raw snapshot | Source / identifier | Normalization and purpose |
|---|---|---|
| `XIU.TO.csv`, `SPY.csv`, `TLT.csv` | [Yahoo via yfinance](https://ranaroussi.github.io/yfinance/reference/index.html) | `auto_adjust=False`; keep OHLC, Close, Adj Close, volume and actions. Local CAD or USD per share. Close values holdings; log adjusted-close changes calibrate shocks. |
| `fx.csv` | [Bank of Canada Valet](https://www.bankofcanada.ca/valet/docs/), FXUSDCAD | CAD per one USD; no inversion. |
| `CAD.csv` | [BoC zero curves](https://www.bankofcanada.ca/rates/interest-rates/bond-yield-curves/), ZC100YR/ZC200YR/ZC500YR/ZC1000YR/ZC3000YR | Fitted continuous zero rates, already annual decimals. Select published 1/2/5/10/30-year nodes. |
| `USD.csv` | [Federal Reserve GSW](https://www.federalreserve.gov/data/nominal-yield-curve.htm), SVENY01/02/05/10/30 | Fitted continuous zero rates: percent divided by 100. Par-yield fields are not used. |
| `spread.csv` | [FRED BAMLC0A0CM](https://fred.stlouisfed.org/series/BAMLC0A0CM) | ICE BofA US Corporate Index OAS, percent / 100. Flat continuous-spread proxy for the hypothetical USD IG bond, not an issuer quote. |
| `VIX.csv` | Yahoo ^VIX, [Cboe methodology](https://www.cboe.com/tradable_products/vix/) | VIX points / 100; annual volatility proxy. Neither SPY contract-specific IV nor a one-year volatility quote. |

Each timestamped `data/raw/public/` directory contains bounded, normalized source snapshots rather than a giant full-history archive. Its manifest records URL, source identifier, units, transformation, retrieval timestamp, first/last observation, source status and SHA-256 checksums. ETF descriptive names and currencies come from Yahoo metadata; sector/country groupings are analytical classifications. A FAILED manifest names the failing source. An earlier cache is never silently selected by a failed refresh.

The BoC curve is normally published with a two-week lag; the Fed curve is a research dataset subject to revisions and delays. The valuation dates are the latest consecutive complete common weekdays in the downloaded window. The first saved run uses August 25–26, 2026, with calibration July 11, 2025–August 26, 2026. History extends back to September 2023; FRED currently limits this ICE series to about three years. Observation dates are not historical publication timestamps: these are retrospective valuations, not as-published backtests.

## Download and run

```powershell
python main.py refresh --start 2023-09-01 --end 2026-08-31
python main.py demo --excel
streamlit run dashboard/app.py
```

`refresh` validates all required sources, writes a new raw snapshot, prepares seven SQL input CSVs under `data/processed/<snapshot>/`, and updates `config/portfolio.yaml` only after preparation succeeds. The configuration selects new database and input paths. `demo` imports that snapshot into its empty SQLite database, or reuses the matching database. It verifies the input checksums and database snapshot identity. `run` evaluates an already imported database. Neither command downloads data. The dashboard reads saved results, not external APIs.

Public CSV caches are excluded from Git because publicly accessible data is not automatically licensed for redistribution. In particular, review ICE/FRED and Yahoo usage terms before sharing underlying datasets. The saved workbook/report contains derived portfolio analytics and limited source observations. A fresh clone needs one successful refresh; after that, calculations and preparation work offline. Do not delete your raw snapshot if exact reproducibility matters: providers may revise history or roll the available window.

To rebuild cleaned inputs offline from a verified raw snapshot, use `python main.py prepare --input data/raw/public/<snapshot> --data-root data/rebuilt`. Select a new prepared root if the snapshot directory already exists. Existing snapshots are immutable: preparation refuses to overwrite them. Its `portfolio.yaml` can be passed with `--config` to restore that exact setup. Use `--database data/another.db` to rebuild SQL from the same prepared inputs without changing an existing database.

The contract dates in `src/data/portfolio_data.py` are intentionally explicit. Update matured hypothetical terms deliberately before refreshing beyond their expiry; the program will not silently roll holdings. The assumed European SPY call is strike 800, expiry 2027-08-31, multiplier 100 and dividend yield 1.2%. Current option-chain data cannot provide historical contract IV; VIX at each historical date is used instead.

## Relational inputs

`sql/schema.sql` defines the constraints. Imports are atomic and append-only; duplicate keys fail.

| Input CSV | Key / meaning |
|---|---|
| `portfolios.csv` | Portfolio ID and base currency |
| `security_master.csv` | Security ID, real ticker/name where applicable, type, currency, classifications, multipliers and applicable terms/factor mappings |
| `trades.csv` | Unique hypothetical ID, security/portfolio, trade and settlement dates, signed quantity, local price, currency and type |
| `market_prices.csv` | Date/security; positive Close and Adj Close, source URL and timestamp |
| `fx_rates.csv` | Date/currency/base; positive base currency per foreign unit |
| `yield_curve.csv` | Date/curve/tenor; tenor years and continuous annual zero-rate decimal |
| `factor_levels.csv` | Date/factor; numeric level, shock kind, URL and timestamp |

The `data_snapshot` SQLite table stores the imported manifest; risk-run metadata carries source summaries into reporting. Positions, trades, quality exceptions and calculated risk results remain relational tables. Use `sql/sample_queries.sql` for analytical queries.

```powershell
python main.py import --input data/my_import --database data/my_portfolio.db
python main.py run --config config/my_portfolio.yaml --database data/my_portfolio.db --output outputs/my_portfolio
```

Custom imports may omit a public-snapshot manifest; they are labelled imported observations rather than automatically claiming public provenance. Use ISO dates, decimal rates and no embedded percent/currency symbols. Blank instrument-specific fields mean SQL NULL. Observations must be ordered within each key. Future market observations, duplicate keys and non-finite numbers are rejected. Controls also check economic ranges, mapped curve tenors, FX direction fields, source consistency, missing/stale inputs and unexpected outliers. FX numerical bounds are a reasonableness check, not proof that an arbitrary supplied rate has not been inverted.

## Financial mappings and alignment

- `EQ_CA`: XIU.TO; `EQ_US`: SPY; `ETF_US`: TLT. Log adjusted-close changes approximate daily price shocks including distribution adjustments. Current option spot is SPY's actual Close in strike units, never the adjusted-price level.
- `FX_USD`: CAD per USD, logarithmic changes.
- `CAD_<tenor>` / `USD_<tenor>`: continuous zero-rate decimals, absolute changes. Missing nodes are not invented. Pricing interpolates between the published nodes and holds endpoint rates flat.
- `SPREAD_US`: index spread decimal; absolute changes.
- `VOL_US`: VIX/100 annual volatility proxy; absolute changes.

Weekday reindexing happens before differencing. Missing weekdays invalidate both adjacent changes; there is no historical forward-fill or disguised multi-day return. The real-data configuration requires 252 complete common changes at both valuation dates. Last-observation valuation is bounded to two weekdays, although the default dates use exact common quotes. Different exchanges and publication calendars reduce usable history.

Quantities mean ETF shares, face-100 bond units, cash currency units or option contracts. Local execution prices for options are per underlying share; the multiplier is applied separately. Opening holdings begin on the prior date, not at the beginning of the calibration history. The current-date XIU.TO purchase has an offsetting CAD cash entry. Coupons require explicit income postings; the builder books hypothetical bond coupons and ETF distributions across the comparison interval, treating published ex-date distributions as a simplified cash/receivable accrual. Splits across the interval block preparation until quantities are explicitly adjusted. No actual portfolio performance or investment-management history is represented.

## Tests

`python -m pytest -q` never calls a live source. Parser tests use small labelled deterministic inputs and mocked failures. The financial regression suite uses separate seeded fixtures. The cached-real integration test additionally rebuilds SQL and tests the complete public-data risk workflow when a local snapshot exists; it skips with an explanation on a fresh clone rather than downloading during a test.
