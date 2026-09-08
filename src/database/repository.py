import pandas as pd

TABLES = (
    "portfolios",
    "security_master",
    "trades",
    "market_prices",
    "fx_rates",
    "yield_curve",
    "factor_levels",
    "positions",
    "risk_runs",
    "risk_results",
    "quality_results",
)


def read_table(connection, table):
    if table not in TABLES:
        raise ValueError("Unknown table")
    return pd.read_sql_query(f"SELECT * FROM {table}", connection)


def insert_frame(connection, table, frame):
    """Insert without replacing schema, checks or foreign keys. Caller owns transaction."""
    if table not in TABLES:
        raise ValueError("Unknown table")
    allowed = {row[1] for row in connection.execute(f"PRAGMA table_info({table})")}
    if not set(frame.columns) <= allowed:
        raise ValueError(f"Unknown columns for {table}")
    columns = ",".join(f'"{col}"' for col in frame.columns)
    placeholders = ",".join("?" for _ in frame.columns)
    rows = frame.astype(object).where(frame.notna(), None).itertuples(index=False, name=None)
    connection.executemany(f"INSERT INTO {table} ({columns}) VALUES ({placeholders})", rows)


def settled_positions(connection, portfolio_id, as_of_date):
    positions = pd.read_sql_query(
        """
        SELECT security_id,SUM(quantity) AS quantity
        FROM trades WHERE portfolio_id=? AND settlement_date<=? AND trade_date<=?
        GROUP BY security_id HAVING ABS(SUM(quantity))>1e-10
        ORDER BY security_id""",
        connection,
        params=(portfolio_id, as_of_date, as_of_date),
    )
    trades = pd.read_sql_query(
        """
        SELECT t.*,s.multiplier FROM trades t JOIN security_master s USING(security_id)
        WHERE portfolio_id=? AND settlement_date<=? AND trade_date<=?
        ORDER BY settlement_date,trade_date,trade_id""",
        connection,
        params=(portfolio_id, as_of_date, as_of_date),
    )
    costs = {}
    for sid, group in trades.groupby("security_id"):
        quantity, cost = 0.0, 0.0
        for trade in group.itertuples():
            change = trade.quantity
            unit_cost = trade.price * trade.multiplier
            if quantity == 0 or quantity * change > 0:
                cost += change * unit_cost
            elif abs(change) <= abs(quantity):
                # Selling removes average acquisition cost, not the sale proceeds.
                cost += change * (cost / quantity)
            else:
                cost = (quantity + change) * unit_cost
            quantity += change
            if abs(quantity) < 1e-10:
                quantity, cost = 0.0, 0.0
        costs[sid] = cost
    positions["book_cost"] = positions.security_id.map(costs)
    return positions
