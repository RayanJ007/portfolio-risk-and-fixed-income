-- Latest exposures are already converted to the portfolio base currency.
SELECT * FROM exposure_by_asset_class;
SELECT * FROM exposure_by_currency;
SELECT ticker,market_value FROM current_portfolio ORDER BY ABS(market_value) DESC LIMIT 10;
SELECT * FROM stale_prices;
SELECT * FROM trades WHERE trade_date BETWEEN :start_date AND :as_of_date ORDER BY trade_date;
SELECT security_id,maturity_date FROM security_master
WHERE security_type='bond' AND maturity_date>:as_of_date AND maturity_date<=date(:as_of_date,'+1 year');
SELECT credit_rating,SUM(market_value) FROM current_portfolio
WHERE security_type='bond' GROUP BY credit_rating;
SELECT * FROM trade_completeness WHERE ABS(difference)>0.000001;
-- Missing marks: LEFT JOIN preserves exceptions, rather than losing holdings.
SELECT p.security_id FROM current_portfolio p LEFT JOIN market_prices m
ON p.security_id=m.security_id AND m.date=p.as_of_date
WHERE p.security_type IN ('equity','etf') AND m.price IS NULL;
-- Detect a settled holding absent from a snapshot (the reverse reconciliation).
SELECT t.portfolio_id,t.security_id,SUM(t.quantity) AS quantity
FROM trades t LEFT JOIN positions p ON t.portfolio_id=p.portfolio_id
AND t.security_id=p.security_id AND p.as_of_date=:as_of_date
WHERE t.settlement_date<=:as_of_date AND p.security_id IS NULL
GROUP BY t.portfolio_id,t.security_id HAVING ABS(SUM(t.quantity))>0.000001;
