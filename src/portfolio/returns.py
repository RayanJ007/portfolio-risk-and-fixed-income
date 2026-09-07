import numpy as np
import pandas as pd


def factor_changes(levels, kinds, as_of_date, window=252, minimum=100):
    if levels.index.has_duplicates or levels.columns.has_duplicates:
        raise ValueError('Duplicate factor observations')
    levels = levels.sort_index().loc[:as_of_date].copy()
    if set(levels.columns) != set(kinds):
        raise ValueError('Factor mapping mismatch')
    # Reindex to weekdays before differencing: no multiday move disguised as one-day return.
    levels.index = pd.to_datetime(levels.index)
    levels = levels.reindex(pd.bdate_range(levels.index.min(),pd.Timestamp(as_of_date)))
    for name,kind in kinds.items():
        if kind == 'log':
            if (levels[name].dropna()<=0).any():
                raise ValueError('Log factors must be positive')
            levels[name] = np.log(levels[name])
        elif kind != 'absolute':
            raise ValueError('Unknown factor kind')
    changes = levels.diff().dropna(how='any').tail(window)
    if len(changes) < minimum or not np.isfinite(changes).all().all():
        raise ValueError('Insufficient finite common return history')
    return changes


def simple_returns(prices):
    if not np.isfinite(prices.dropna()).all().all() or (prices.dropna()<=0).any().any():
        raise ValueError('Invalid price history')
    return prices.pct_change(fill_method=None)


def performance_metrics(returns, benchmark=None, annual_risk_free=.03, periods=252):
    r = pd.Series(returns).dropna()
    if len(r)<2 or not np.isfinite(r).all() or (r<=-1).any() or annual_risk_free<=-1:
        raise ValueError('Invalid performance history')
    wealth = (1+r).cumprod()
    peak = wealth.cummax().clip(lower=1.)
    vol = r.std(ddof=1)*np.sqrt(periods)
    rf_daily = (1+annual_risk_free)**(1/periods)-1
    result = dict(cumulative_return=wealth.iloc[-1]-1, annualized_return=wealth.iloc[-1]**(periods/len(r))-1,
                  volatility=vol, sharpe=(r.mean()-rf_daily)*periods/vol if vol>0 else np.nan,
                  max_drawdown=float((wealth/peak-1).min()), observations=len(r))
    if benchmark is not None:
        aligned = pd.concat([r.rename('portfolio'),pd.Series(benchmark).rename('benchmark')],axis=1).dropna()
        if len(aligned)<2 or not np.isfinite(aligned).all().all():
            raise ValueError('Insufficient benchmark overlap')
        covariance = aligned.cov(ddof=1)
        active = aligned.portfolio-aligned.benchmark
        tracking = active.std(ddof=1)*np.sqrt(periods)
        result.update(beta=covariance.iloc[0,1]/covariance.iloc[1,1] if covariance.iloc[1,1]>0 else np.nan,
                      tracking_error=tracking, information_ratio=active.mean()*periods/tracking if tracking>0 else np.nan)
    return result
