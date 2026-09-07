"""Two-path averaged counterfactual VaR attribution, with explicit interaction evidence."""
from copy import deepcopy

import numpy as np
import pandas as pd

from src.risk.engine import sensitivities,parametric_risk


def covariance_parts(covariance):
    values=covariance.to_numpy()
    vol=np.sqrt(np.maximum(np.diag(values),0))
    denom=np.outer(vol,vol)
    correlation=np.divide(values,denom,out=np.zeros_like(values),where=denom>0)
    np.fill_diagonal(correlation,1.)
    return pd.Series(vol,index=covariance.index),pd.DataFrame(correlation,index=covariance.index,columns=covariance.index)


def economic_blocks(quantities,state,covariance,as_of_date):
    vol,correlation=covariance_parts(covariance.loc[state.index,state.index])
    price=[n for n in state.index if n.startswith(('EQ_','ETF_'))]
    fx=[n for n in state.index if n.startswith('FX_')]
    rates=[n for n in state.index if n.startswith(('CAD_','USD_','SPREAD_'))]
    other=[n for n in state.index if n not in price+fx+rates]
    return {'Positions / trades':quantities.copy(),'Market prices':state[price].copy(),
            'FX levels':state[fx].copy(),'Rates / spreads':state[rates].copy(),
            'Option volatility levels':state[other].copy(),
            'Equity / ETF volatility':vol[price].copy(),'FX volatility':vol[fx].copy(),
            'Rate / spread volatility':vol[rates].copy(),'Other factor volatility':vol[other].copy(),
            'Correlation':correlation.copy(),'Valuation date / roll':as_of_date}


def risk_from_blocks(master,kinds,blocks,base_currency='CAD',confidence=.99):
    state=pd.concat([blocks[n] for n in ('Market prices','FX levels','Rates / spreads','Option volatility levels')]).sort_index()
    vol=pd.concat([blocks[n] for n in ('Equity / ETF volatility','FX volatility','Rate / spread volatility','Other factor volatility')]).reindex(state.index)
    correlation=blocks['Correlation'].loc[state.index,state.index]
    covariance=correlation.to_numpy()*np.outer(vol,vol)
    derivatives=sensitivities(master,state,kinds,blocks['Valuation date / roll'],base_currency)
    q=blocks['Positions / trades'].reindex(derivatives.index,fill_value=0)
    return parametric_risk(q.to_numpy()@derivatives.to_numpy(),covariance,confidence)['var']


def attribute_change(before,after,evaluate):
    if list(before)!=list(after):
        raise ValueError('Attribution blocks must match')
    names=list(before)
    old,new=evaluate(before),evaluate(after)
    allocations={name:0. for name in names}
    for order in (names,names[::-1]):
        current=deepcopy(before)
        previous=old
        for name in order:
            current[name]=deepcopy(after[name])
            risk=evaluate(current)
            allocations[name]+=(risk-previous)/2
            previous=risk
    rows=[]
    for name in names:
        current=deepcopy(before)
        current[name]=deepcopy(after[name])
        rows.append(dict(driver=name,allocated_change=allocations[name],standalone_change=evaluate(current)-old))
    result=pd.DataFrame(rows)
    residual=new-old-result.allocated_change.sum()
    interactions=new-old-result.standalone_change.sum()
    return dict(prior_var=old,current_var=new,change=new-old,drivers=result,
                interaction_vs_standalone=interactions,residual=residual,
                methodology='Average forward/reverse replacement paths; interactions allocated within drivers')
