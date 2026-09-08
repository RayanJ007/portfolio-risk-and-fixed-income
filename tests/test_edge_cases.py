import numpy as np
import pandas as pd
import pytest

from src.data.sample import sample_tables, write_sample
from src.data.imports import import_directory
from src.database.connection import connect
from src.database.repository import settled_positions, insert_frame
from src.controls.data_quality import quality_checks
from src.portfolio.returns import factor_changes
from src.portfolio.positions import market_state, unit_values, shocked_states
from src.pricing.bonds import curve_price
from src.risk.engine import tail_risk, risk_contributions, parametric_risk


def test_average_cost_on_sales_and_option_multiplier(tmp_path):
    write_sample(tmp_path)
    db = connect(":memory:")
    import_directory(db, tmp_path)
    with db:
        insert_frame(
            db,
            "trades",
            pd.DataFrame(
                [
                    dict(
                        trade_id="SALE",
                        portfolio_id="DEMO",
                        security_id="CA_EQ",
                        trade_date="2026-09-01",
                        settlement_date="2026-09-01",
                        quantity=-1000,
                        price=120,
                        currency="CAD",
                    )
                ]
            ),
        )
    old = settled_positions(db, "DEMO", "2026-08-31").set_index("security_id")
    new = settled_positions(db, "DEMO", "2026-09-01").set_index("security_id")
    assert new.loc["CA_EQ", "book_cost"] == pytest.approx(
        old.loc["CA_EQ", "book_cost"] * 250000 / 251000
    )
    assert old.loc["US_CALL", "book_cost"] == 100 * 1 * 100


def test_controls_for_missing_mapping_tenor_and_convention():
    tables = sample_tables()
    tables["security_master"].loc[0, "price_factor"] = None
    tables["yield_curve"] = tables["yield_curve"].loc[
        ~((tables["yield_curve"].curve_name == "CAD") & (tables["yield_curve"].tenor == 10))
    ]
    tables["factor_levels"].loc[0, "kind"] = "absolute"
    checks = quality_checks(tables, "2026-08-31")
    assert {"CLASSIFICATION", "CURVE_DATA", "FACTOR_CONSISTENCY"} <= set(
        checks.loc[checks.severity == "FAIL", "check_id"]
    )


def test_future_history_cannot_change_earlier_calibration():
    index = pd.bdate_range("2026-01-01", periods=20)
    data = pd.DataFrame({"p": np.linspace(90, 110, 20)}, index=index)
    before = factor_changes(data, {"p": "log"}, "2026-01-15", minimum=2)
    data.loc[data.index > "2026-01-15", "p"] = 100000
    pd.testing.assert_frame_equal(
        before, factor_changes(data, {"p": "log"}, "2026-01-15", minimum=2)
    )


def test_hedge_negative_component_and_zero_net_risk():
    cov = pd.DataFrame([[0.01]], index=["x"], columns=["x"])
    unit = pd.DataFrame([[1.0], [1.0]], index=["long", "short"], columns=["x"])
    parts = risk_contributions(unit, pd.Series({"long": 100, "short": -50}), cov)
    assert parts.component_var.iloc[1] < 0
    assert parts.component_var.sum() == pytest.approx(parametric_risk([50], cov)["var"])
    flat = risk_contributions(unit, pd.Series({"long": 100, "short": -100}), cov)
    assert np.allclose(flat.component_var, 0)


def test_tail_ties_and_small_sample():
    assert tail_risk([-10, -10, -2, -1], 0.75) == {"var": 10.0, "es": 10.0}
    assert tail_risk([-4, 2], 0.99) == {"var": 4.0, "es": 4.0}


def test_curve_vector_pricer_matches_independent_scalar():
    tables = sample_tables()
    f = tables["factor_levels"]
    state = f.loc[f.date == "2026-08-31"].set_index("factor").level
    master = tables["security_master"]
    bond = master.loc[master.security_id == "CA_CORP"]
    value = unit_values(bond, state, "2026-08-31").iloc[0, 0]
    reference = curve_price(
        "2026-08-31",
        "2033-08-31",
        0.05,
        [1, 2, 5, 10, 30],
        [state[f"CAD_{t}"] for t in [1, 2, 5, 10, 30]],
        spread=state.SPREAD_CA,
    )
    assert value == pytest.approx(reference)


def test_real_fx_import_preserves_observations(tmp_path):
    write_sample(tmp_path, real_fx_path="data/raw/boc_usdcad.csv")
    actual = pd.read_csv("data/raw/boc_usdcad.csv")
    imported = pd.read_csv(tmp_path / "fx_rates.csv")
    pd.testing.assert_frame_equal(actual, imported)
    factors = pd.read_csv(tmp_path / "factor_levels.csv").query("factor=='FX_USD'")
    assert np.allclose(factors.level, actual.rate)
    assert not factors.source.str.contains("SYNTHETIC").any()


def test_unfunded_purchase_is_a_control_failure():
    tables = sample_tables()
    tables["trades"] = tables["trades"].loc[tables["trades"].trade_id != "REBAL-CAD_CASH"]
    checks = quality_checks(tables, "2026-08-31")
    assert "CASH_RECON" in set(checks.loc[checks.severity == "FAIL", "check_id"])
