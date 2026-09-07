"""Read saved daily analytics; custom stresses call the same Python repricer."""
from pathlib import Path
import sys
import json

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0,str(ROOT))

import pandas as pd
import plotly.express as px
import streamlit as st

from src.reporting.charts import attribution_figure

st.set_page_config(page_title='Institutional Portfolio Risk',page_icon='◈',layout='wide')
st.markdown('''<style>
.block-container {padding-top:2rem; max-width:1500px;}
[data-testid="stMetric"] {background:#f2f5f8; padding:18px; border-radius:6px; border-left:3px solid #375779;}
[data-testid="stMetric"] * {color:#203850 !important;}
h1,h2,h3 {color:#203850;}
</style>''',unsafe_allow_html=True)

st.sidebar.title('Portfolio Risk')
report_path=Path(st.sidebar.text_input('Report folder',str(ROOT/'outputs')))/'risk_report.json'
if not report_path.exists():
    st.info('Generate a report first: python main.py demo')
    st.stop()
try:
    data=json.loads(report_path.read_text(encoding='utf-8'))
except (ValueError,OSError) as error:
    st.error(f'Cannot read report: {error}')
    st.stop()
meta=data['metadata']
page=st.sidebar.radio('Analysis',['Portfolio Overview','Market Risk','Fixed Income','Stress Testing','Risk Attribution','Data Quality'])
st.sidebar.caption(f"{meta['portfolio_id']} · {meta['base_currency']}\n\nAs of {meta['as_of_date']}\n\nPrior {meta['prior_date']}")
st.sidebar.warning(meta['source_label'])
st.sidebar.download_button('Download daily report',(report_path.parent/'daily_risk_report.md').read_bytes(),'daily_risk_report.md')
st.title(page)
st.caption(f"{meta['as_of_date']}  |  {meta['base_currency']} base  |  One-day risk horizon  |  {meta['observations']} daily observations")
positions=pd.DataFrame(data['positions'])
risk=pd.DataFrame(data['risk_summary'])

if page=='Portfolio Overview':
    a,b,c=st.columns(3)
    a.metric('Net asset value',f"CAD {data['nav']/1e6:,.2f}m")
    b.metric('Flow-adjusted daily P&L',f"CAD {data['daily_pnl']:,.0f}")
    var99=risk.loc[(risk.method=='Parametric')&(risk.confidence==.99),'var'].iloc[0]
    c.metric('99% parametric VaR',f'CAD {var99/1e6:.2f}m')
    left,right=st.columns([1,1.4])
    group=left.selectbox('Exposure breakdown',['asset_class','currency','sector','country'])
    allocation=positions.groupby(group,as_index=False).market_value.sum()
    left.plotly_chart(px.bar(allocation,x='market_value',y=group,orientation='h',labels={'market_value':'Exposure (CAD)'},color_discrete_sequence=['#375779']),width='stretch')
    right.subheader('Current holdings')
    right.dataframe(positions[['security_id','currency','market_value','weight']].rename(columns={'security_id':'Security','currency':'Currency','market_value':'Market value (CAD)','weight':'Weight'}).style.format({'Market value (CAD)':'{:,.0f}','Weight':'{:.1%}'}),hide_index=True,width='stretch')
    st.subheader('Hypothetical return diagnostics')
    st.caption(meta['performance_basis']+'. This is not a realized performance backtest.')
    returns=pd.DataFrame(data['historical_pnl'])
    returns['wealth']=(1+returns.pnl/data['nav']).cumprod()
    st.plotly_chart(px.line(returns,x='date',y='wealth',labels={'wealth':'Scenario replay wealth (start = 1)'}),width='stretch')
    st.dataframe(pd.DataFrame(data['performance'].items(),columns=['Metric','Value']),hide_index=True)

elif page=='Market Risk':
    confidence=st.select_slider('Confidence',options=[.95,.99],format_func=lambda v:f'{v:.0%}')
    subset=risk.loc[risk.confidence==confidence]
    st.plotly_chart(px.bar(subset.melt(id_vars='method',value_vars=['var','es'],var_name='Measure',value_name='CAD'),x='method',y='CAD',color='Measure',barmode='group',color_discrete_sequence=['#375779','#77A6A0']),width='stretch')
    st.caption(f"Calibration: {meta['window_start']} to {meta['window_end']}. {meta['covariance']}. Zero drift. {meta['simulations']:,} Monte Carlo scenarios; seed {meta['seed']}.")
    pnl=pd.DataFrame(data['mc_pnl'])
    st.plotly_chart(px.histogram(pnl,x='pnl',nbins=70,labels={'pnl':'One-day Monte Carlo P&L (CAD)'},color_discrete_sequence=['#375779']),width='stretch')
    st.subheader('99% parametric VaR contributions')
    group=st.selectbox('Group contributions',['security_id','asset_class','currency','sector'])
    parts=pd.DataFrame(data['contributions'])
    totals=parts.groupby(group,as_index=False)[['component_var','standalone_var']].sum()
    st.plotly_chart(px.bar(totals,x=group,y='component_var',labels={'component_var':'Component VaR (CAD)'}),width='stretch')
    st.dataframe(parts,hide_index=True,width='stretch')
    st.caption('Marginal VaR is CAD per additional security unit. Negative component VaR denotes a hedge. Components sum to portfolio parametric VaR.')

elif page=='Fixed Income':
    fixed=pd.DataFrame(data['fixed_income'])
    a,b=st.columns(2)
    a.metric('Bond position DV01',f"CAD {fixed.position_dv01.sum():,.0f} / bp")
    b.metric('Value-weighted modified duration',f"{(fixed.modified_duration*fixed.market_value).sum()/fixed.market_value.sum():.2f} years")
    st.dataframe(fixed,hide_index=True,width='stretch')
    st.caption('YTM is nominal annual yield in decimals; duration in years, convexity in years². DV01 uses a symmetric nominal-YTM bump.')
    curves=pd.DataFrame(data['curves'])
    st.plotly_chart(px.bar(curves,x='scenario',y='pnl',color='security_id',barmode='group',labels={'pnl':'Full curve-repricing P&L (CAD)'}),width='stretch')
    st.dataframe(curves,hide_index=True,width='stretch')
    st.caption('Curve risk uses continuous zero rates. Linear P&L uses tenor-specific central sensitivities, with nonlinear differences shown explicitly.')

elif page=='Stress Testing':
    stress=pd.DataFrame(data['stress'])
    scenario=st.selectbox('Scenario',stress.scenario.unique())
    selected=stress.loc[stress.scenario==scenario]
    a,b=st.columns(2)
    a.metric('Scenario P&L',f"CAD {selected.pnl.sum():,.0f}")
    b.metric('Stressed NAV',f"CAD {data['nav']+selected.pnl.sum():,.0f}")
    st.plotly_chart(px.bar(selected,x='security_id',y='pnl',color='asset_class',labels={'pnl':'P&L (CAD)'}),width='stretch')
    st.dataframe(selected,hide_index=True,width='stretch')
    with st.expander('Run a custom full-repricing scenario'):
        equity=st.slider('Equity return (%)',-80,50,-20)
        rates=st.slider('Parallel yield change (bp)',-300,500,100)
        spread=st.slider('Credit spread change (bp)',-100,600,100)
        fx=st.slider('Foreign currency appreciation (%)',-30,40,0)
        vol=st.slider('Implied volatility change (percentage points)',-15,50,10)
        if st.button('Reprice custom scenario'):
            from src.stress.scenarios import stress_results
            from src.portfolio.positions import market_state
            from src.database.connection import connect
            connection=connect(ROOT/meta['database'])
            try:
                state,kinds=market_state(connection,meta['as_of_date'],meta['base_currency'])
                master=pd.DataFrame(data['inputs']['security_master'])
                result=stress_results(master,positions.set_index('security_id').quantity,state,kinds,meta['as_of_date'],
                    {'Interactive custom':dict(equity_return=equity/100,rates_bp=rates,spread_bp=spread,fx_return=fx/100,volatility_change=vol/100)},meta['base_currency'])
                st.metric('Custom P&L',f'CAD {result.pnl.sum():,.0f}')
                st.dataframe(result,hide_index=True,width='stretch')
            except (ValueError,KeyError) as error:
                st.error(str(error))
            finally:
                connection.close()

elif page=='Risk Attribution':
    attr=dict(data['attribution_summary'],drivers=pd.DataFrame(data['attribution']))
    a,b,c=st.columns(3)
    a.metric('Prior 99% VaR',f"CAD {attr['prior_var']:,.0f}")
    b.metric('Current 99% VaR',f"CAD {attr['current_var']:,.0f}")
    c.metric('Change',f"CAD {attr['change']:,.0f}")
    st.plotly_chart(attribution_figure(attr),width='stretch')
    st.dataframe(attr['drivers'],hide_index=True,width='stretch')
    st.caption(attr['methodology']+'. Model-based allocation, not causal identification.')
    st.write(f"Interaction effect relative to standalone changes: CAD {attr['interaction_vs_standalone']:,.2f}. Already allocated within drivers; do not add twice. Numerical residual: CAD {attr['residual']:.8f}.")

else:
    checks=pd.DataFrame(data['quality'])
    columns=st.columns(3)
    for column,severity in zip(columns,['PASS','WARN','FAIL']):
        column.metric(severity,int((checks.severity==severity).sum()))
    only_exceptions=st.checkbox('Show exceptions only',value=True)
    st.dataframe(checks.loc[checks.severity!='PASS'] if only_exceptions else checks,hide_index=True,width='stretch')
    st.caption('Missing critical inputs block risk calculation and persist exceptions in SQLite. PASS applies to the evaluated scope, not to future dates.')
