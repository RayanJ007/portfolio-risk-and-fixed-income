import pandas as pd

TABLES = ('portfolios', 'security_master', 'trades', 'market_prices', 'fx_rates',
          'yield_curve', 'factor_levels', 'positions', 'risk_runs', 'risk_results', 'quality_results')


def read_table(connection, table):
    if table not in TABLES:
        raise ValueError('Unknown table')
    return pd.read_sql_query(f'SELECT * FROM {table}', connection)


def insert_frame(connection, table, frame):
    """Insert without replacing schema, checks or foreign keys. Caller owns transaction."""
    if table not in TABLES:
        raise ValueError('Unknown table')
    allowed = {row[1] for row in connection.execute(f'PRAGMA table_info({table})')}
    if not set(frame.columns) <= allowed:
        raise ValueError(f'Unknown columns for {table}')
    columns = ','.join(f'"{col}"' for col in frame.columns)
    placeholders = ','.join('?' for _ in frame.columns)
    rows = frame.astype(object).where(frame.notna(), None).itertuples(index=False, name=None)
    connection.executemany(f'INSERT INTO {table} ({columns}) VALUES ({placeholders})', rows)


def settled_positions(connection, portfolio_id, as_of_date):
    return pd.read_sql_query('''
        SELECT security_id,SUM(quantity) AS quantity,SUM(quantity*price) AS book_cost
        FROM trades WHERE portfolio_id=? AND settlement_date<=? AND trade_date<=?
        GROUP BY security_id HAVING ABS(SUM(quantity))>1e-10
        ORDER BY security_id''', connection, params=(portfolio_id, as_of_date, as_of_date))
