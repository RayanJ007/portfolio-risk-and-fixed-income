import numpy as np
import pandas as pd
import pytest

from src.data.sample import write_sample
from src.data.imports import import_directory
from src.database.connection import connect
from src.portfolio.positions import market_state,value_positions,fixed_income_analytics,shocked_states,unit_values
from src.database.repository import read_table
from src.portfolio.returns import factor_changes, performance_metrics, simple_returns


@pytest.fixture
def database(tmp_path):
    write_sample(tmp_path)
    connection=connect(':memory:')
    import_directory(connection,tmp_path)
    yield connection
    connection.close()


def test_valuation_fx_and_no_lookahead(database):
    state,kinds=market_state(database,'2026-08-31')
    p=value_positions(database,'DEMO','2026-08-31',state,persist=True).set_index('security_id')
    assert p.loc['US_EQ','market_value']==pytest.approx(70000*250*1.36)
    assert p.weight.sum()==pytest.approx(1)
    assert len(database.execute('SELECT * FROM current_portfolio').fetchall())==8
    before,_=market_state(database,'2026-08-28')
    assert before['EQ_US'] != state['EQ_US']
    bonds=fixed_income_analytics(p.reset_index(),'2026-08-31')
    assert (bonds.position_dv01>0).all()
    shocks=pd.DataFrame(0.,index=[0],columns=state.index)
    shocks['FX_USD']=np.log(1.1)
    master=read_table(database,'security_master')
    new=unit_values(master,shocked_states(state,shocks,kinds),'2026-08-31').iloc[0]
    old=unit_values(master,state,'2026-08-31').iloc[0]
    assert new.US_EQ/old.US_EQ==pytest.approx(1.1)
    assert new.CA_EQ==old.CA_EQ


def test_history_gaps_and_cutoff():
    levels=pd.DataFrame({'x':[100,110,np.nan,121,133.1,146.41]},index=pd.bdate_range('2026-01-01',periods=6))
    changes=factor_changes(levels,{'x':'log'},'2026-01-08',minimum=2)
    assert len(changes)==3
    assert np.allclose(changes.x,np.log(1.1))
    with pytest.raises(ValueError):
        factor_changes(levels,{'x':'log'},'2026-01-02',minimum=2)
    assert pd.isna(simple_returns(levels).iloc[3,0])


def test_performance_drawdown_beta():
    r=pd.Series([-.1,.05,.02,-.03])
    metrics=performance_metrics(r,r)
    assert metrics['beta']==pytest.approx(1)
    assert metrics['tracking_error']==0
    assert metrics['max_drawdown']==pytest.approx(-.1)
    assert metrics['volatility']==pytest.approx(r.std()*np.sqrt(252))
