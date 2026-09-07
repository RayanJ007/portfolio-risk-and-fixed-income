PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS portfolios (
    portfolio_id TEXT PRIMARY KEY, base_currency TEXT NOT NULL CHECK(length(base_currency)=3)
);
CREATE TABLE IF NOT EXISTS security_master (
    security_id TEXT PRIMARY KEY, ticker TEXT NOT NULL, name TEXT NOT NULL,
    security_type TEXT NOT NULL CHECK(security_type IN ('equity','etf','bond','cash','option')),
    asset_class TEXT NOT NULL, currency TEXT NOT NULL, sector TEXT NOT NULL,
    country TEXT NOT NULL, benchmark TEXT, credit_rating TEXT,
    maturity_date TEXT, coupon_rate REAL, coupon_frequency INTEGER, face_value REAL,
    price_factor TEXT, curve_name TEXT, spread_factor TEXT,
    underlying_factor TEXT, strike REAL, option_type TEXT, volatility_factor TEXT,
    dividend_yield REAL DEFAULT 0, multiplier REAL NOT NULL DEFAULT 1 CHECK(multiplier>0),
    allow_short INTEGER NOT NULL DEFAULT 0 CHECK(allow_short IN (0,1))
);
CREATE TABLE IF NOT EXISTS trades (
    trade_id TEXT PRIMARY KEY, portfolio_id TEXT NOT NULL REFERENCES portfolios,
    security_id TEXT NOT NULL REFERENCES security_master, trade_date TEXT NOT NULL,
    settlement_date TEXT NOT NULL CHECK(settlement_date>=trade_date),
    quantity REAL NOT NULL CHECK(quantity<>0), price REAL NOT NULL CHECK(price>=0),
    currency TEXT NOT NULL, trade_type TEXT NOT NULL DEFAULT 'trade'
);
CREATE TABLE IF NOT EXISTS market_prices (
    date TEXT NOT NULL, security_id TEXT NOT NULL REFERENCES security_master,
    price REAL NOT NULL CHECK(price>0), adjusted_price REAL NOT NULL CHECK(adjusted_price>0),
    source TEXT NOT NULL, retrieval_timestamp TEXT NOT NULL,
    PRIMARY KEY(date, security_id)
);
CREATE TABLE IF NOT EXISTS fx_rates (
    date TEXT NOT NULL, currency TEXT NOT NULL, base_currency TEXT NOT NULL,
    rate REAL NOT NULL CHECK(rate>0), source TEXT NOT NULL, retrieval_timestamp TEXT NOT NULL,
    PRIMARY KEY(date,currency,base_currency)
);
CREATE TABLE IF NOT EXISTS yield_curve (
    date TEXT NOT NULL, curve_name TEXT NOT NULL, tenor REAL NOT NULL CHECK(tenor>0),
    rate REAL NOT NULL, source TEXT NOT NULL, retrieval_timestamp TEXT NOT NULL,
    PRIMARY KEY(date,curve_name,tenor)
);
CREATE TABLE IF NOT EXISTS factor_levels (
    date TEXT NOT NULL, factor TEXT NOT NULL, level REAL NOT NULL,
    kind TEXT NOT NULL CHECK(kind IN ('log','absolute')), source TEXT NOT NULL,
    retrieval_timestamp TEXT NOT NULL, PRIMARY KEY(date,factor)
);
CREATE TABLE IF NOT EXISTS positions (
    as_of_date TEXT NOT NULL, portfolio_id TEXT NOT NULL REFERENCES portfolios,
    security_id TEXT NOT NULL REFERENCES security_master, quantity REAL NOT NULL,
    book_cost REAL NOT NULL, market_price REAL NOT NULL, fx_rate REAL NOT NULL CHECK(fx_rate>0),
    market_value REAL NOT NULL, PRIMARY KEY(as_of_date,portfolio_id,security_id)
);
CREATE TABLE IF NOT EXISTS risk_runs (
    run_id TEXT PRIMARY KEY, as_of_date TEXT NOT NULL, portfolio_id TEXT NOT NULL REFERENCES portfolios,
    created_at TEXT NOT NULL, metadata TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS risk_results (
    run_id TEXT NOT NULL REFERENCES risk_runs, method TEXT NOT NULL, measure TEXT NOT NULL,
    confidence REAL NOT NULL CHECK(confidence>0 AND confidence<1),
    horizon_days INTEGER NOT NULL CHECK(horizon_days=1), base_currency TEXT NOT NULL,
    value REAL NOT NULL, PRIMARY KEY(run_id,method,measure,confidence,horizon_days)
);
CREATE TABLE IF NOT EXISTS quality_results (
    run_id TEXT NOT NULL REFERENCES risk_runs, check_id TEXT NOT NULL,
    severity TEXT NOT NULL CHECK(severity IN ('PASS','WARN','FAIL')), record TEXT NOT NULL,
    description TEXT NOT NULL, action TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_trades_settlement ON trades(portfolio_id,settlement_date);
