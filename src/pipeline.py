from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4
import json

import numpy as np
import pandas as pd
import yaml

from src.database.connection import ROOT
from src.database.repository import read_table,insert_frame
from src.data.imports import INPUT_TABLES
from src.controls.data_quality import quality_checks
from src.portfolio.positions import market_state,value_positions,fixed_income_analytics
from src.portfolio.returns import factor_changes,performance_metrics
from src.risk.engine import calculate_risk,sample_covariance
from src.stress.scenarios import stress_results,curve_scenarios
from src.attribution.risk_change import economic_blocks,risk_from_blocks,attribute_change


def load_config(path=None):
    config=yaml.safe_load(Path(path or ROOT/'config/portfolio.yaml').read_text())
    if config['horizon_days']!=1 or config['simulations']<10000:
        raise ValueError('Use one-day horizon and at least 10,000 simulations')
    if config['prior_date']>=config['as_of_date']:
        raise ValueError('Prior date must precede current date')
    if not 2<=config['minimum_history']<=config['window']:
        raise ValueError('Invalid history window')
    return config


def run_portfolio(connection,config):
    date,prior=config['as_of_date'],config['prior_date']
    portfolio,currency=config['portfolio_id'],config['base_currency']
    tables={name:read_table(connection,name) for name in INPUT_TABLES}
    selected=tables['portfolios'].loc[tables['portfolios'].portfolio_id==portfolio]
    if len(selected)!=1 or selected.base_currency.iloc[0]!=currency:
        raise ValueError('Portfolio/base currency does not match database')
    run_id=str(uuid4())
    metadata=dict(config,run_id=run_id,loss_convention='Positive loss, floored at zero',
                  return_method='Log price/FX changes; absolute zero-rate/spread/volatility changes',
                  covariance='Synchronized sample covariance, ddof=1',drift='Zero',
                  source_label='Contains synthetic teaching data' if tables['factor_levels'].source.str.contains('SYNTHETIC').any() else 'Imported observations',
                  risk_timing='Instantaneous one-business-day calibrated shocks; no carry or time passage')
    sources=tables['factor_levels'].source
    if sources.str.contains('SYNTHETIC').any() and (~sources.str.contains('SYNTHETIC')).any():
        metadata['source_label']='Mixed: real Bank of Canada FX; synthetic other markets and holdings'
    with connection:
        insert_frame(connection,'risk_runs',pd.DataFrame([dict(run_id=run_id,as_of_date=date,portfolio_id=portfolio,
                     created_at=datetime.now(timezone.utc).isoformat(),metadata=json.dumps(metadata))]))
    quality=[]
    for day in (prior,date):
        checks=quality_checks(tables,day,portfolio,currency,config['max_stale_business_days'],config['minimum_history'])
        checks['record']=day+': '+checks.record
        quality.append(checks)
    quality=pd.concat(quality,ignore_index=True)
    if (quality.severity=='FAIL').any():
        with connection:
            insert_frame(connection,'quality_results',quality.assign(run_id=run_id))
        raise ValueError(f'Data quality FAIL; exceptions stored for run {run_id}')
    state,kinds=market_state(connection,date,currency,config['max_stale_business_days'])
    old_state,_=market_state(connection,prior,currency,config['max_stale_business_days'])
    master=tables['security_master']
    positions=value_positions(connection,portfolio,date,state,currency,persist=True)
    old_positions=value_positions(connection,portfolio,prior,old_state,currency,persist=True)
    q=positions.set_index('security_id').quantity
    old_q=old_positions.set_index('security_id').quantity
    levels=tables['factor_levels'].pivot(index='date',columns='factor',values='level')
    changes=factor_changes(levels,kinds,date,config['window'],config['minimum_history']).loc[:,state.index]
    old_changes=factor_changes(levels,kinds,prior,config['window'],config['minimum_history']).loc[:,state.index]
    risk=calculate_risk(master,q,state,kinds,changes,date,currency,config['simulations'],config['seed'],config['confidence_levels'])
    before=economic_blocks(old_q,old_state,sample_covariance(old_changes),prior)
    after=economic_blocks(q,state,risk['covariance'],date)
    attribution=attribute_change(before,after,lambda blocks:risk_from_blocks(master,kinds,blocks,currency))
    scenarios=yaml.safe_load((ROOT/'config/scenarios.yaml').read_text())
    stress=stress_results(master,q,state,kinds,date,scenarios,currency)
    curves=curve_scenarios(master,q,state,kinds,date,currency)
    quality=quality_checks(tables,date,portfolio,currency,config['max_stale_business_days'],config['minimum_history'],positions)
    if (quality.severity=='FAIL').any():
        with connection:
            insert_frame(connection,'quality_results',quality.assign(run_id=run_id))
        raise ValueError('Post-valuation reconciliation FAIL')
    nav=float(positions.market_value.sum()); old_nav=float(old_positions.market_value.sum())
    external=tables['trades'].loc[(tables['trades'].portfolio_id==portfolio)&(tables['trades'].settlement_date>prior)&
                                  (tables['trades'].settlement_date<=date)&tables['trades'].trade_type.isin(['external','opening'])]
    flows=sum(r.quantity*r.price*(1 if r.currency==currency else state[f'FX_{r.currency}']) for r in external.itertuples())
    # This is a frozen-current-exposure scenario series, not a realized backtest.
    scenario_returns=risk['historical_pnl']/nav
    benchmark=np.expm1(changes['EQ_CA']) if 'EQ_CA' in changes else None
    metrics=performance_metrics(scenario_returns,benchmark,config['annual_risk_free_rate'])
    metadata.update(window_start=str(changes.index.min().date()),window_end=str(changes.index.max().date()),
                    observations=len(changes),volatility_floor_hits=risk['vol_floor_count'],
                    performance_basis='Frozen-current-exposure hypothetical daily scenario returns')
    with connection:
        connection.execute('UPDATE risk_runs SET metadata=? WHERE run_id=?',(json.dumps(metadata),run_id))
        results=risk['summary'].melt(id_vars=['method','confidence','horizon_days','base_currency'],value_vars=['var','es'],var_name='measure',value_name='value')
        insert_frame(connection,'risk_results',results.assign(run_id=run_id))
        insert_frame(connection,'quality_results',quality.assign(run_id=run_id))
    contributions=risk['contributions'].merge(master[['security_id','asset_class','currency','sector']],on='security_id')
    return dict(metadata=metadata,nav=nav,prior_nav=old_nav,daily_pnl=nav-old_nav-flows,external_flows=flows,
                positions=positions,prior_positions=old_positions,fixed_income=fixed_income_analytics(positions,date),
                risk=risk,contributions=contributions,stress=stress,curves=curves,attribution=attribution,
                quality=quality,performance=metrics,scenario_returns=scenario_returns,tables=tables,
                state=state,kinds=kinds,master=master,quantities=q)
