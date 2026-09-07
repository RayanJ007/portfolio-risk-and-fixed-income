import numpy as np
import pandas as pd

from src.risk.engine import scenario_pnl, sensitivities


def scenario_changes(state, scenario):
    allowed={'equity_return','etf_return','fx_return','rates_bp','spread_bp','volatility_change','factor_shocks'}
    if not set(scenario)<=allowed:
        raise ValueError('Unknown scenario field')
    changes=pd.Series(0.,index=state.index)
    prefixes={'equity_return':'EQ_','etf_return':'ETF_','fx_return':'FX_'}
    for field,prefix in prefixes.items():
        shock=scenario.get(field,0.)
        if not np.isfinite(shock) or shock<=-1:
            raise ValueError('Return shock must exceed -100%')
        changes.loc[changes.index.str.startswith(prefix)]=np.log1p(shock)
    for name in state.index:
        if name.startswith(('CAD_','USD_')):
            changes[name]=scenario.get('rates_bp',0)*.0001
        elif name.startswith('SPREAD_'):
            changes[name]=scenario.get('spread_bp',0)*.0001
        elif name.startswith('VOL_'):
            changes[name]=scenario.get('volatility_change',0)
    for name,value in scenario.get('factor_shocks',{}).items():
        if name not in state:
            raise ValueError(f'Unknown scenario factor: {name}')
        changes[name]=value
    if not np.isfinite(changes).all():
        raise ValueError('Nonfinite scenario')
    return changes.to_frame().T


def stress_results(master,quantities,state,kinds,as_of_date,scenarios,base_currency='CAD'):
    rows=[]
    for name,scenario in scenarios.items():
        pnl=scenario_pnl(master,quantities,state,scenario_changes(state,scenario),kinds,as_of_date,base_currency).iloc[0]
        for sid,value in pnl.items():
            rows.append(dict(scenario=name,security_id=sid,pnl=value))
    return pd.DataFrame(rows).merge(master[['security_id','asset_class','currency']],on='security_id',validate='many_to_one')


def curve_scenarios(master,quantities,state,kinds,as_of_date,base_currency='CAD',custom=None):
    """Tenor shocks in bp, with linear interpolation. Analytic sensitivity uses zero-rate coordinates."""
    curves={'Parallel +100 bp':{1:100,30:100},'Parallel -100 bp':{1:-100,30:-100},
            'Bear steepener':{1:25,30:150},'Bull flattener':{1:-25,30:-100}}
    if custom is not None:
        curves['Custom key rates']=custom
    bonds=master.loc[master.security_type=='bond']
    derivatives=sensitivities(bonds,state,kinds,as_of_date,base_currency)
    rows=[]
    for name,knots in curves.items():
        tenors=np.array(sorted(knots),float)
        bp=np.array([knots[t] for t in sorted(knots)],float)
        if len(tenors)<2 or (tenors<=0).any() or not np.isfinite(bp).all():
            raise ValueError('Invalid key-rate scenario')
        changes=pd.DataFrame(0.,index=[0],columns=state.index)
        for factor in state.index:
            if factor.startswith(('CAD_','USD_')):
                tenor=float(factor.rsplit('_',1)[1])
                changes[factor]=np.interp(tenor,tenors,bp)*.0001
        pnl=scenario_pnl(bonds,quantities,state,changes,kinds,as_of_date,base_currency).iloc[0]
        approx=derivatives @ changes.iloc[0]*quantities.reindex(derivatives.index,fill_value=0)
        for sid,value in pnl.items():
            rows.append(dict(scenario=name,security_id=sid,pnl=value,linear_pnl=approx[sid],
                             nonlinear_difference=value-approx[sid]))
    return pd.DataFrame(rows)
