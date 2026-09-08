import numpy as np
import pandas as pd
import pytest

from src.data.sample import sample_tables
from src.stress.scenarios import stress_results, curve_scenarios
from src.attribution.risk_change import attribute_change
from src.controls.data_quality import quality_checks


def test_stress_curve_directions():
    tables = sample_tables()
    master = tables["security_master"]
    f = tables["factor_levels"]
    state = f.loc[f.date == "2026-08-31"].set_index("factor").level
    kinds = f.groupby("factor").kind.first().to_dict()
    q = tables["trades"].groupby("security_id").quantity.sum()
    stress = stress_results(
        master, q, state, kinds, "2026-08-31", {"Crash": {"equity_return": -0.3}}
    )
    assert (stress.loc[stress.asset_class == "Equity", "pnl"] < 0).all()
    curves = curve_scenarios(master, q, state, kinds, "2026-08-31")
    assert (curves.loc[curves.scenario == "Parallel +100 bp", "pnl"] < 0).all()
    assert (curves.loc[curves.scenario == "Parallel -100 bp", "pnl"] > 0).all()
    assert np.abs(curves.pnl - curves.linear_pnl).max() > 0


def test_attribution_interactions_are_explicit():
    before = {"position": 2.0, "volatility": 3.0}
    after = {"position": 4.0, "volatility": 5.0}
    result = attribute_change(before, after, lambda x: x["position"] * x["volatility"])
    assert result["change"] == 14
    assert result["drivers"].allocated_change.sum() == pytest.approx(14)
    assert result["interaction_vs_standalone"] == 4
    assert result["residual"] == 0
    assert result["drivers"].allocated_change.to_list() == [8, 6]
    only = attribute_change(
        before, {"position": 4.0, "volatility": 3.0}, lambda x: x["position"] * x["volatility"]
    )
    assert only["drivers"].allocated_change.to_list() == [6, 0]


def test_healthy_data_and_operational_exceptions():
    tables = sample_tables()
    good = quality_checks(tables, "2026-08-31")
    assert not (good.severity == "FAIL").any(), good.to_string()
    tables["market_prices"] = tables["market_prices"].loc[
        tables["market_prices"].security_id != "CA_EQ"
    ]
    tables["fx_rates"] = tables["fx_rates"].iloc[:0]
    tables["trades"] = pd.concat([tables["trades"], tables["trades"].iloc[:1]], ignore_index=True)
    tables["trades"].loc[1, "security_id"] = "UNKNOWN"
    tables["security_master"].loc[
        tables["security_master"].security_id == "CA_GOV", "coupon_rate"
    ] = -1
    bad = quality_checks(tables, "2026-08-31")
    failed = set(bad.loc[bad.severity == "FAIL", "check_id"])
    assert {
        "MISSING_PRICE",
        "MISSING_FX",
        "DUPLICATE_TRADE",
        "SECURITY_MAPPING",
        "BOND_TERMS",
    } <= failed


def test_stale_and_missing_history():
    tables = sample_tables()
    tables["market_prices"] = tables["market_prices"].loc[
        tables["market_prices"].date < "2026-08-15"
    ]
    tables["factor_levels"] = tables["factor_levels"].loc[
        tables["factor_levels"].date > "2026-08-01"
    ]
    results = quality_checks(tables, "2026-08-31")
    failed = set(results.loc[results.severity == "FAIL", "check_id"])
    assert {"STALE_PRICE", "RETURN_HISTORY"} <= failed
