CREATE VIEW IF NOT EXISTS current_portfolio AS
SELECT p.*, s.ticker,s.security_type,s.asset_class,s.currency,s.sector,s.country,s.credit_rating
FROM positions p JOIN security_master s USING(security_id)
WHERE p.as_of_date=(SELECT MAX(p2.as_of_date) FROM positions p2 WHERE p2.portfolio_id=p.portfolio_id);
CREATE VIEW IF NOT EXISTS exposure_by_asset_class AS
SELECT as_of_date,portfolio_id,asset_class,SUM(market_value) AS exposure
FROM current_portfolio GROUP BY as_of_date,portfolio_id,asset_class;
CREATE VIEW IF NOT EXISTS exposure_by_currency AS
SELECT as_of_date,portfolio_id,currency,SUM(market_value) AS exposure
FROM current_portfolio GROUP BY as_of_date,portfolio_id,currency;
CREATE VIEW IF NOT EXISTS exposure_by_sector AS
SELECT as_of_date,portfolio_id,sector,SUM(market_value) AS exposure
FROM current_portfolio GROUP BY as_of_date,portfolio_id,sector;
CREATE VIEW IF NOT EXISTS stale_prices AS
SELECT p.portfolio_id,p.as_of_date,p.security_id,MAX(m.date) AS last_price_date,
       julianday(p.as_of_date)-julianday(MAX(m.date)) AS calendar_days_old
FROM current_portfolio p LEFT JOIN market_prices m ON p.security_id=m.security_id AND m.date<=p.as_of_date
WHERE p.security_type IN ('equity','etf')
GROUP BY p.portfolio_id,p.as_of_date,p.security_id
HAVING last_price_date IS NULL OR calendar_days_old>3;
CREATE VIEW IF NOT EXISTS trade_completeness AS
SELECT p.as_of_date,p.portfolio_id,p.security_id,p.quantity,
       COALESCE(SUM(t.quantity),0) AS settled_quantity,
       p.quantity-COALESCE(SUM(t.quantity),0) AS difference
FROM positions p LEFT JOIN trades t ON p.portfolio_id=t.portfolio_id
AND p.security_id=t.security_id AND t.settlement_date<=p.as_of_date
GROUP BY p.as_of_date,p.portfolio_id,p.security_id;
