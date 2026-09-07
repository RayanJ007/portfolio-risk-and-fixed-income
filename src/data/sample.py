"""Deterministic fictional instruments and synthetic market observations, not real quotes."""
from pathlib import Path

import numpy as np
import pandas as pd

SOURCE = 'SYNTHETIC: seeded teaching dataset; not observed market data'
STAMP = '2026-09-01T00:00:00+00:00'
TENORS = (1, 2, 5, 10, 30)


def sample_tables():
    dates = pd.bdate_range('2025-01-02', '2026-08-31').strftime('%Y-%m-%d')
    rng = np.random.default_rng(17)
    common = rng.normal(size=(len(dates), 3))
    factors = {'EQ_CA': (100., .011, 'log'), 'EQ_US': (250., .014, 'log'),
               'ETF_US': (95., .004, 'log'), 'FX_USD': (1.36, .005, 'log'),
               'SPREAD_CA': (.015, .0003, 'absolute'), 'VOL_US': (.24, .006, 'absolute')}
    for curve in ('CAD', 'USD'):
        for tenor in TENORS:
            factors[f'{curve}_{tenor}'] = (.03 + .0003 * tenor, .0005, 'absolute')
    levels, factor_rows = {}, []
    for name, (last, scale, kind) in factors.items():
        driver = common[:, 0] if name.startswith('EQ') else common[:, 1]
        if name.startswith(('CAD_', 'USD_')):
            driver = common[:, 2]
        changes = scale * (.7 * driver + np.sqrt(.51) * rng.normal(size=len(dates)))
        path = np.cumsum(changes)
        values = last * np.exp(path - path[-1]) if kind == 'log' else last + path - path[-1]
        if name == 'VOL_US':
            values = np.maximum(values, .08)
        levels[name] = values
        factor_rows.extend({'date': d, 'factor': name, 'level': float(v), 'kind': kind,
                            'source': SOURCE, 'retrieval_timestamp': STAMP} for d, v in zip(dates, values))
    securities = [
        dict(security_id='CA_EQ', ticker='DEMO-CA', name='Canadian equity basket', security_type='equity', asset_class='Equity', currency='CAD', sector='Broad market', country='CA', price_factor='EQ_CA'),
        dict(security_id='US_EQ', ticker='DEMO-US', name='US equity basket', security_type='equity', asset_class='Equity', currency='USD', sector='Broad market', country='US', price_factor='EQ_US'),
        dict(security_id='US_ETF', ticker='DEMO-T', name='US Treasury ETF proxy', security_type='etf', asset_class='Fixed income ETF', currency='USD', sector='Government', country='US', price_factor='ETF_US'),
        dict(security_id='CA_GOV', ticker='DEMO-GOV', name='Canadian government bond', security_type='bond', asset_class='Government bond', currency='CAD', sector='Government', country='CA', maturity_date='2031-08-31', coupon_rate=.035, coupon_frequency=2, face_value=100, curve_name='CAD', credit_rating='AAA'),
        dict(security_id='CA_CORP', ticker='DEMO-CORP', name='Canadian corporate bond', security_type='bond', asset_class='Corporate bond', currency='CAD', sector='Financials', country='CA', maturity_date='2033-08-31', coupon_rate=.05, coupon_frequency=2, face_value=100, curve_name='CAD', spread_factor='SPREAD_CA', credit_rating='A'),
        dict(security_id='US_CALL', ticker='DEMO-CALL', name='European US basket call', security_type='option', asset_class='Option', currency='USD', sector='Broad market', country='US', maturity_date='2027-08-31', strike=260, option_type='call', underlying_factor='EQ_US', volatility_factor='VOL_US', curve_name='USD', dividend_yield=.015, multiplier=100),
        dict(security_id='CAD_CASH', ticker='CAD', name='CAD cash', security_type='cash', asset_class='Cash', currency='CAD', sector='Cash', country='CA'),
        dict(security_id='USD_CASH', ticker='USD', name='USD cash', security_type='cash', asset_class='Cash', currency='USD', sector='Cash', country='US')]
    master = pd.DataFrame(securities)
    master['multiplier'] = master['multiplier'].fillna(1)
    master['allow_short'] = 0
    master['dividend_yield'] = master['dividend_yield'].fillna(0)
    master['benchmark'] = 'EQ_CA'
    quantities = {'CA_EQ': 250000, 'US_EQ': 70000, 'US_ETF': 65000,
                  'CA_GOV': 220000, 'CA_CORP': 120000, 'US_CALL': 100,
                  'CAD_CASH': 6000000, 'USD_CASH': 2000000}
    trades = []
    for i, row in enumerate(securities):
        sid = row['security_id']
        price = levels[row['price_factor']][0] if row.get('price_factor') else (100 if row['security_type'] == 'bond' else 1)
        trades.append(dict(trade_id=f'OPEN-{i}', portfolio_id='DEMO', security_id=sid,
                           trade_date=dates[0], settlement_date=dates[0], quantity=quantities[sid],
                           price=price, currency=row['currency'], trade_type='opening'))
    # An explicitly funded current-day buy provides a meaningful position attribution.
    for sid, qty, price in [('CA_EQ', 1000, 100), ('CAD_CASH', -100000, 1)]:
        trades.append(dict(trade_id=f'REBAL-{sid}', portfolio_id='DEMO', security_id=sid,
                           trade_date=dates[-1], settlement_date=dates[-1], quantity=qty,
                           price=price, currency='CAD', trade_type='trade'))
    # Both bonds pay coupons on the valuation date. Record cash receipts explicitly.
    trades.append(dict(trade_id='COUPONS-20260831',portfolio_id='DEMO',security_id='CAD_CASH',
                       trade_date=dates[-1],settlement_date=dates[-1],quantity=685000.,price=1.,
                       currency='CAD',trade_type='income'))
    marks = []
    for row in securities:
        if row.get('price_factor'):
            for d, p in zip(dates, levels[row['price_factor']]):
                marks.append(dict(date=d, security_id=row['security_id'], price=p, adjusted_price=p,
                                  source=SOURCE, retrieval_timestamp=STAMP))
    curves = [dict(date=d, curve_name=c, tenor=t, rate=levels[f'{c}_{t}'][i],
                   source=SOURCE, retrieval_timestamp=STAMP)
              for i, d in enumerate(dates) for c in ('CAD', 'USD') for t in TENORS]
    fx = [dict(date=d, currency='USD', base_currency='CAD', rate=v,
               source=SOURCE, retrieval_timestamp=STAMP) for d, v in zip(dates, levels['FX_USD'])]
    return {'portfolios': pd.DataFrame([{'portfolio_id': 'DEMO', 'base_currency': 'CAD'}]),
            'security_master': master, 'trades': pd.DataFrame(trades),
            'market_prices': pd.DataFrame(marks), 'fx_rates': pd.DataFrame(fx),
            'yield_curve': pd.DataFrame(curves), 'factor_levels': pd.DataFrame(factor_rows)}


def write_sample(directory='data/sample',real_fx_path=None):
    output = Path(directory)
    output.mkdir(parents=True, exist_ok=True)
    tables=sample_tables()
    if real_fx_path is not None:
        fx=pd.read_csv(real_fx_path)
        if fx.empty or not fx.rate.gt(0).all() or fx.date.duplicated().any() or not fx.currency.eq('USD').all() or not fx.base_currency.eq('CAD').all():
            raise ValueError('Invalid real USD/CAD import')
        if fx.source.str.contains('SYNTHETIC').any():
            raise ValueError('Real FX import contains synthetic provenance')
        tables['fx_rates']=fx
        factors=tables['factor_levels']
        imported=fx.rename(columns={'rate':'level'}).assign(factor='FX_USD',kind='log')
        tables['factor_levels']=pd.concat([factors.loc[factors.factor!='FX_USD'],imported[factors.columns]],ignore_index=True)
    for name, frame in tables.items():
        frame.to_csv(output / f'{name}.csv', index=False)
