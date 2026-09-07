import numpy as np
import pandas as pd

from src.database.repository import read_table, settled_positions, insert_frame
from src.pricing.bonds import cash_flows, yield_to_maturity, bond_analytics
from src.pricing.options import black_scholes


def latest_rows(frame, keys, as_of_date, max_age=2):
    rows = frame.loc[frame['date'] <= as_of_date].sort_values('date').groupby(keys, as_index=False).tail(1)
    if rows.empty:
        raise ValueError('Missing dated observations')
    ages = np.busday_count(rows['date'].to_numpy(dtype='datetime64[D]'), np.datetime64(as_of_date, 'D'))
    if np.any(ages > max_age):
        raise ValueError('Stale observations')
    return rows


def market_state(connection, as_of_date, base_currency='CAD', max_age=2):
    factors = latest_rows(read_table(connection,'factor_levels'), ['factor'], as_of_date, max_age)
    state = factors.set_index('factor')['level'].copy()
    kinds = factors.set_index('factor')['kind'].to_dict()
    master = read_table(connection,'security_master')
    prices = latest_rows(read_table(connection,'market_prices'), ['security_id'], as_of_date, max_age).set_index('security_id')
    for row in master.loc[master['security_type'].isin(['equity','etf'])].itertuples():
        if row.security_id not in prices.index:
            raise ValueError(f'Missing price: {row.security_id}')
        state[row.price_factor] = prices.loc[row.security_id,'price']
    fx = read_table(connection,'fx_rates')
    fx = latest_rows(fx.loc[fx['base_currency']==base_currency], ['currency'], as_of_date, max_age).set_index('currency')
    for currency in set(master.currency) - {base_currency}:
        if currency not in fx.index:
            raise ValueError(f'Missing FX: {currency}')
        state[f'FX_{currency}'] = fx.loc[currency,'rate']
    curves = latest_rows(read_table(connection,'yield_curve'), ['curve_name','tenor'], as_of_date, max_age)
    for row in curves.itertuples():
        state[f'{row.curve_name}_{row.tenor:g}'] = row.rate
    if not np.isfinite(state).all() or not set(state.index) <= set(kinds):
        raise ValueError('Missing factor mapping or invalid state')
    return state.sort_index(), kinds


def shocked_states(state, changes, kinds):
    if set(changes.columns) != set(state.index) or not np.isfinite(changes).all().all():
        raise ValueError('Shocks must match the finite factor universe')
    result = changes.loc[:,state.index].copy()
    for name in state.index:
        if kinds[name] == 'log':
            result[name] = state[name] * np.exp(result[name])
        elif kinds[name] == 'absolute':
            result[name] += state[name]
        else:
            raise ValueError('Unknown shock convention')
    return result


def curve_inputs(states, curve_name, times):
    names = [n for n in states.columns if n.startswith(curve_name+'_')]
    names.sort(key=lambda n: float(n.rsplit('_',1)[1]))
    tenors = np.array([float(n.rsplit('_',1)[1]) for n in names])
    if len(tenors) < 2:
        raise ValueError(f'Missing curve: {curve_name}')
    weights = np.array([np.interp(times,tenors,basis) for basis in np.eye(len(tenors))])
    return states[names].to_numpy() @ weights


def unit_values(master, states, as_of_date, base_currency='CAD', local=False):
    """Vectorized full repricing; output currency per security unit (option multiplier included)."""
    if isinstance(states, pd.Series):
        states = states.to_frame().T
    if not np.isfinite(states.to_numpy()).all():
        raise ValueError('Invalid factor levels')
    values = {}
    for row in master.itertuples():
        if row.security_type in ('equity','etf'):
            price = states[row.price_factor].to_numpy()
            if np.any(price<=0):
                raise ValueError('Price must be positive')
        elif row.security_type == 'cash':
            price = np.ones(len(states))
        elif row.security_type == 'bond':
            frequency = int(row.coupon_frequency)
            times, flows, _ = cash_flows(as_of_date,row.maturity_date,row.coupon_rate,frequency,row.face_value)
            maturity = pd.Timestamp(row.maturity_date)
            dates = [maturity-pd.DateOffset(months=12//frequency*k) for k in reversed(range(len(times)))]
            if maturity.is_month_end:
                dates = [d+pd.offsets.MonthEnd(0) for d in dates]
            years = np.array([(d-pd.Timestamp(as_of_date)).days/365 for d in dates])
            rates = curve_inputs(states,row.curve_name,years)
            spread = states[row.spread_factor].to_numpy()[:,None] if pd.notna(row.spread_factor) else 0.
            price = np.exp(-(rates+spread)*years) @ flows
        elif row.security_type == 'option':
            time = (pd.Timestamp(row.maturity_date)-pd.Timestamp(as_of_date)).days/365
            if time < 0:
                raise ValueError('Expired option requires settlement')
            rate = curve_inputs(states,row.curve_name,[max(time,1/365)])[:,0]
            # Gaussian vol shocks can cross zero. Floor explicitly at one vol basis point.
            vol = np.maximum(states[row.volatility_factor].to_numpy(), .0001)
            price = black_scholes(states[row.underlying_factor],row.strike,time,rate,vol,row.dividend_yield,row.option_type)
        else:
            raise ValueError('Unsupported security type')
        fx = 1. if local or row.currency==base_currency else states[f'FX_{row.currency}'].to_numpy()
        if np.any(np.asarray(fx)<=0):
            raise ValueError('FX must be positive')
        values[row.security_id] = np.asarray(price)*row.multiplier*fx
    result = pd.DataFrame(values, index=states.index)
    if not np.isfinite(result).all().all():
        raise ValueError('Nonfinite valuation')
    return result


def value_positions(connection, portfolio_id, as_of_date, state, base_currency='CAD', persist=False):
    master = read_table(connection,'security_master')
    holdings = settled_positions(connection,portfolio_id,as_of_date)
    positions = holdings.merge(master,on='security_id',how='left',validate='one_to_one')
    prices = unit_values(master,state,as_of_date,base_currency,local=True).iloc[0]
    values = unit_values(master,state,as_of_date,base_currency).iloc[0]
    positions['market_price'] = positions.security_id.map(prices)/positions.multiplier
    positions['fx_rate'] = positions.currency.map(lambda c: 1 if c==base_currency else state[f'FX_{c}'])
    positions['market_value'] = positions.quantity*positions.security_id.map(values)
    nav = positions.market_value.sum()
    if nav <= 0:
        raise ValueError('NAV must be positive for portfolio weights')
    positions['weight'] = positions.market_value/nav
    positions['as_of_date'], positions['portfolio_id'] = as_of_date, portfolio_id
    if persist:
        columns = ['as_of_date','portfolio_id','security_id','quantity','book_cost','market_price','fx_rate','market_value']
        with connection:
            connection.execute('DELETE FROM positions WHERE as_of_date=? AND portfolio_id=?',(as_of_date,portfolio_id))
            insert_frame(connection,'positions',positions[columns])
    return positions


def fixed_income_analytics(positions, as_of_date):
    rows = []
    for row in positions.loc[positions.security_type=='bond'].itertuples():
        args = (as_of_date,row.maturity_date,row.coupon_rate,int(row.coupon_frequency),row.face_value)
        ytm = yield_to_maturity(row.market_price,*args)
        metrics = bond_analytics(ytm,*args)
        metrics.update(security_id=row.security_id,market_value=row.market_value,
                       position_dv01=metrics['dv01']*row.quantity*row.multiplier*row.fx_rate)
        rows.append(metrics)
    return pd.DataFrame(rows)
