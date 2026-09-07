from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import plotly.graph_objects as go


def attribution_figure(attribution):
    drivers=attribution['drivers']
    return go.Figure(go.Waterfall(x=['Prior VaR']+drivers.driver.to_list()+['Current VaR'],
                     y=[attribution['prior_var']]+drivers.allocated_change.to_list()+[0],
                     measure=['absolute']+['relative']*len(drivers)+['total'],
                     increasing={'marker':{'color':'#B34B43'}},decreasing={'marker':{'color':'#31866D'}},
                     totals={'marker':{'color':'#263D5A'}})).update_layout(title='Change in 99% one-day parametric VaR',yaxis_title='CAD',template='plotly_white')


def export_charts(result,directory):
    output=Path(directory); output.mkdir(parents=True,exist_ok=True)
    figure=attribution_figure(result['attribution'])
    figure.write_html(output/'risk_attribution.html',include_plotlyjs=True)
    fig,ax=plt.subplots(figsize=(11,4.8))
    values=result['risk']['mc_pnl']/1e6
    ax.hist(values,bins=70,color='#304D70',alpha=.9)
    var=result['risk']['summary'].query("method=='Monte Carlo' and confidence==0.99")['var'].iloc[0]/1e6
    ax.axvline(-var,color='#B34B43',label=f'99% VaR: CAD {var:.2f}m')
    ax.set(xlabel='One-day P&L (CAD millions)',ylabel='Simulation count',title='Monte Carlo full-repricing P&L — synthetic teaching portfolio')
    ax.legend(); fig.tight_layout(); fig.savefig(output/'pnl_distribution.png',dpi=160); plt.close(fig)
    attr=result['attribution']; d=attr['drivers']
    fig,ax=plt.subplots(figsize=(12,6))
    previous=attr['prior_var']/1e6
    ax.bar(0,previous,color='#263D5A')
    labels=['Prior VaR']+d.driver.to_list()+['Current VaR']
    for i,row in enumerate(d.itertuples(),1):
        value=row.allocated_change/1e6
        ax.bar(i,abs(value),bottom=min(previous,previous+value),color='#B34B43' if value>=0 else '#31866D')
        previous+=value
    ax.bar(len(labels)-1,attr['current_var']/1e6,color='#263D5A')
    ax.set_xticks(range(len(labels)),labels,rotation=45,ha='right')
    ax.set(ylabel='CAD millions',title='99% one-day parametric VaR attribution — interactions allocated within drivers')
    fig.tight_layout(); fig.savefig(output/'risk_attribution.png',dpi=160); plt.close(fig)
