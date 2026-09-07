"""One-day zero-drift factor risk. P&L gains positive; reported losses nonnegative."""
import numpy as np
import pandas as pd
from scipy.stats import norm

from src.portfolio.positions import shocked_states, unit_values


def tail_risk(pnl, confidence=.99):
    """Inverse empirical CDF VaR; ES integrates exactly the worst (1-alpha) tail."""
    values = np.asarray(pnl,float)
    if values.ndim!=1 or len(values)<2 or not np.isfinite(values).all() or not 0<confidence<1:
        raise ValueError('Invalid P&L or confidence')
    losses = np.sort(-values)
    var = losses[int(np.ceil(confidence*len(losses)))-1]
    mass = (1-confidence)*len(losses)
    count = int(np.floor(mass))
    fraction = mass-count
    descending = losses[::-1]
    es = (descending[:count].sum()+fraction*descending[count])/mass
    return dict(var=max(float(var),0.),es=max(float(es),0.))


def validate_covariance(covariance):
    covariance = np.asarray(covariance,float)
    if covariance.ndim!=2 or covariance.shape[0]!=covariance.shape[1] or not np.isfinite(covariance).all():
        raise ValueError('Invalid covariance dimensions or values')
    scale = max(float(np.max(np.abs(covariance))),1e-20)
    if not np.allclose(covariance,covariance.T,atol=scale*1e-10,rtol=1e-10):
        raise ValueError('Covariance must be symmetric')
    eigenvalues,eigenvectors = np.linalg.eigh(covariance)
    if eigenvalues.min() < -scale*1e-10:
        raise ValueError('Covariance is not positive semidefinite')
    return np.maximum(eigenvalues,0),eigenvectors


def sample_covariance(changes):
    if len(changes)<2 or not np.isfinite(changes).all().all():
        raise ValueError('Insufficient finite calibration observations')
    covariance = changes.cov(ddof=1)
    validate_covariance(covariance)
    return covariance


def correlated_shocks(covariance, simulations=10000, seed=42):
    if not isinstance(simulations,int) or simulations<2:
        raise ValueError('At least two simulations required')
    eigenvalues,eigenvectors = validate_covariance(covariance)
    root = eigenvectors * np.sqrt(eigenvalues)
    random = np.random.default_rng(seed).standard_normal((simulations,len(eigenvalues)))
    return random @ root.T


def scenario_pnl(master, quantities, state, changes, kinds, as_of_date, base_currency='CAD'):
    initial = unit_values(master,state,as_of_date,base_currency).iloc[0]
    shocked = unit_values(master,shocked_states(state,changes,kinds),as_of_date,base_currency)
    q = quantities.reindex(initial.index,fill_value=0)
    if not np.isfinite(q).all():
        raise ValueError('Invalid quantities')
    return (shocked-initial)*q


def sensitivities(master, state, kinds, as_of_date, base_currency='CAD', step=1e-5):
    """Central derivative of unit value with respect to each factor shock coordinate."""
    if step<=0:
        raise ValueError('Derivative step must be positive')
    factors = list(state.index)
    plus = pd.DataFrame(np.eye(len(factors))*step,columns=factors)
    minus = -plus
    high = unit_values(master,shocked_states(state,plus,kinds),as_of_date,base_currency)
    low = unit_values(master,shocked_states(state,minus,kinds),as_of_date,base_currency)
    result = (high-low).T/(2*step)
    result.columns = factors
    return result


def parametric_risk(gradient, covariance, confidence=.99):
    if not 0<confidence<1:
        raise ValueError('Invalid confidence')
    validate_covariance(covariance)
    gradient = np.asarray(gradient,float)
    if gradient.ndim!=1 or len(gradient)!=len(covariance) or not np.isfinite(gradient).all():
        raise ValueError('Invalid sensitivity vector')
    sigma = float(np.sqrt(max(gradient @ np.asarray(covariance) @ gradient,0)))
    z = norm.ppf(confidence)
    return dict(var=max(z*sigma,0.),es=norm.pdf(z)/(1-confidence)*sigma,sigma=sigma)


def risk_contributions(unit_sensitivities, quantities, covariance, confidence=.99):
    if not .5<confidence<1:
        raise ValueError('Euler loss VaR requires confidence above 50%')
    covariance = covariance.loc[unit_sensitivities.columns,unit_sensitivities.columns]
    q = quantities.reindex(unit_sensitivities.index,fill_value=0).to_numpy()
    matrix = unit_sensitivities.to_numpy()
    g = q @ matrix
    risk = parametric_risk(g,covariance,confidence)
    marginal = norm.ppf(confidence)*(matrix @ covariance.to_numpy() @ g)/risk['sigma'] if risk['sigma']>0 else np.zeros(len(q))
    standalone = norm.ppf(confidence)*np.sqrt(np.maximum(np.einsum('ij,jk,ik->i',matrix,covariance,matrix),0))*np.abs(q)
    return pd.DataFrame({'security_id':unit_sensitivities.index,'quantity':q,
                         'marginal_var':marginal,'component_var':q*marginal,'standalone_var':standalone})


def calculate_risk(master, quantities, state, kinds, changes, as_of_date, base_currency='CAD', simulations=10000, seed=42, confidences=(.95,.99)):
    covariance = sample_covariance(changes.loc[:,state.index])
    derivatives = sensitivities(master,state,kinds,as_of_date,base_currency)
    g = quantities.reindex(derivatives.index,fill_value=0).to_numpy() @ derivatives.to_numpy()
    historical = scenario_pnl(master,quantities,state,changes,kinds,as_of_date,base_currency).sum(axis=1)
    shocks = pd.DataFrame(correlated_shocks(covariance,simulations,seed),columns=covariance.columns)
    mc = scenario_pnl(master,quantities,state,shocks,kinds,as_of_date,base_currency).sum(axis=1)
    rows = []
    for confidence in confidences:
        for method,metrics in [('Historical',tail_risk(historical,confidence)),
                               ('Parametric',parametric_risk(g,covariance,confidence)),
                               ('Monte Carlo',tail_risk(mc,confidence))]:
            rows.append(dict(method=method,confidence=confidence,horizon_days=1,base_currency=base_currency,
                             var=metrics['var'],es=metrics['es']))
    vol_factors = [n for n in state.index if n.startswith('VOL_')]
    vol_floor_count = sum(int((state[n]+shocks[n]<.0001).sum()) for n in vol_factors)
    return dict(summary=pd.DataFrame(rows),historical_pnl=historical,mc_pnl=mc,covariance=covariance,
                sensitivities=derivatives,contributions=risk_contributions(derivatives,quantities,covariance),
                vol_floor_count=vol_floor_count)
