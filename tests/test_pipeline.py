from pathlib import Path
import json

import numpy as np
import pandas as pd
import pytest

from src.data.imports import import_directory
from src.data.sample import write_sample
from src.database.connection import connect,ROOT
from src.pipeline import load_config,run_portfolio
from src.reporting.daily_report import export_reports
from src.controls.data_quality import quality_checks


@pytest.fixture(scope='module')
def daily_result(tmp_path_factory):
    folder=tmp_path_factory.mktemp('integrated')
    write_sample(folder/'input')
    connection=connect(folder/'test.db')
    import_directory(connection,folder/'input')
    config=load_config()
    config['database']=str(folder/'test.db')
    result=run_portfolio(connection,config)
    export_reports(result,folder/'reports')
    yield connection,result,folder
    connection.close()


def test_end_to_end_reconciliations(daily_result):
    connection,r,folder=daily_result
    assert connection.execute('SELECT COUNT(*) FROM risk_results').fetchone()[0]==12
    assert abs(r['nav']-r['positions'].market_value.sum())<.01
    assert r['attribution']['current_var']==pytest.approx(r['risk']['summary'].query("method=='Parametric' and confidence==.99")['var'].iloc[0])
    assert abs(r['attribution']['residual'])<1e-7
    assert not (r['quality'].severity=='FAIL').any()
    for _,group in r['risk']['summary'].groupby('method'):
        assert group.sort_values('confidence')['var'].is_monotonic_increasing
        assert (group.es>=group['var']).all()
    assert len(r['risk']['mc_pnl'])==10000
    report=json.loads((folder/'reports/risk_report.json').read_text())
    assert report['nav']==r['nav']
    assert 'synthetic' in report['metadata']['source_label']
    assert '95' in (folder/'reports/daily_risk_report.md').read_text()
    assert all(abs(row[-1])<1e-6 for row in connection.execute('SELECT * FROM trade_completeness'))


def test_post_valuation_controls(daily_result):
    _,r,_=daily_result
    positions=r['positions'].copy()
    positions.loc[0,'quantity']+=1
    positions.loc[1,'market_value']+=100
    positions=positions.iloc[:-1]
    quality=quality_checks(r['tables'],'2026-08-31',positions=positions)
    assert {'POSITION_RECON','VALUE_RECON'}<=set(quality.loc[quality.severity=='FAIL','check_id'])


def test_failures_persist_and_block_risk(tmp_path):
    write_sample(tmp_path)
    connection=connect(':memory:')
    import_directory(connection,tmp_path)
    connection.execute("DELETE FROM market_prices WHERE security_id='CA_EQ'")
    connection.commit()
    with pytest.raises(ValueError,match='Data quality FAIL'):
        run_portfolio(connection,load_config())
    assert connection.execute('SELECT COUNT(*) FROM risk_results').fetchone()[0]==0
    assert connection.execute("SELECT COUNT(*) FROM quality_results WHERE severity='FAIL'").fetchone()[0]>0


def test_dashboard_all_pages(daily_result):
    from streamlit.testing.v1 import AppTest
    _,_,folder=daily_result
    app=AppTest.from_file(str(ROOT/'dashboard/app.py'),default_timeout=30).run()
    app.text_input[0].set_value(str(folder/'reports')).run()
    assert not app.exception
    for page in ['Portfolio Overview','Market Risk','Fixed Income','Stress Testing','Risk Attribution','Data Quality']:
        app.sidebar.radio[0].set_value(page).run()
        assert not app.exception, (page,app.exception)
    app.sidebar.radio[0].set_value('Stress Testing').run()
    app.button[0].click().run()
    assert not app.exception


def test_coupon_receipt_ledger(daily_result):
    _,r,_=daily_result
    income=r['tables']['trades'].query("trade_type=='income'").quantity.sum()
    coupon=0
    for row in r['positions'].query("security_type=='bond'").itertuples():
        coupon+=row.quantity*row.face_value*row.coupon_rate/row.coupon_frequency
    assert income==pytest.approx(coupon)
