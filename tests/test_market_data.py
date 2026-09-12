"""Offline adapter tests; small numbers below are deliberate test inputs, not market quotes."""

from hashlib import sha256
from pathlib import Path
import json

import numpy as np
import pandas as pd
import pytest

from src.data.market_data import (
    parse_boc_fx,
    parse_spread,
    parse_zero_curve,
    read_manifest,
    validate_series,
    refresh_market_data,
)
from src.data.imports import import_directory
from src.data.portfolio_data import prepare_portfolio
from src.database.connection import connect
from src.pipeline import load_config, run_portfolio
from src.portfolio.positions import market_state
from src.portfolio.returns import factor_changes
from src.controls.data_quality import quality_checks
from tests.fixtures.synthetic import sample_tables


def test_source_unit_conversions_and_missing_days():
    cad = "Date, ZC100YR, ZC200YR, ZC500YR, ZC1000YR, ZC3000YR,\n2025-01-02, .02, .03, .04, .05, .06,\n2025-01-03, na, na, na, na, na,\n"
    fed = "Zero-coupon yield,Continuously Compounded,SVENYXX\nDate,SVENY01,SVENY02,SVENY05,SVENY10,SVENY30\n2025-01-02,2,3,4,5,6\n2025-01-03,NA,NA,NA,NA,NA\n"
    a = parse_zero_curve(cad, "CAD", "2025-01-01", "2025-01-03")
    b = parse_zero_curve(fed, "USD", "2025-01-01", "2025-01-03")
    pd.testing.assert_frame_equal(a, b)
    assert a["5"].iloc[0] == 0.04
    assert pd.isna(a["5"].iloc[1])
    spread = parse_spread(
        "observation_date,BAMLC0A0CM\n2025-01-02,1.2\n2025-01-03,.\n", "2025-01-01", "2025-01-03"
    )
    assert spread.spread.iloc[0] == 0.012
    assert pd.isna(spread.spread.iloc[1])
    with pytest.raises(ValueError, match="format"):
        parse_zero_curve(fed.replace("Continuously", "Annually"), "USD", "2025-01-01", "2025-01-03")


def test_official_fx_direction_and_missing_quotes():
    payload = {
        "seriesDetail": {"FXUSDCAD": {"label": "USD/CAD"}},
        "observations": [{"d": "2025-01-02", "FXUSDCAD": {"v": "1.4"}}, {"d": "2025-01-03"}],
    }
    frame = parse_boc_fx(payload, "2025-01-01", "2025-01-03")
    assert len(frame) == 1 and frame.rate.iloc[0] == 1.4
    payload["seriesDetail"]["FXUSDCAD"]["label"] = "CAD/USD"
    with pytest.raises(ValueError, match="direction"):
        parse_boc_fx(payload, "2025-01-01", "2025-01-03")


@pytest.mark.parametrize(
    "dates,values",
    [
        (["2025-01-02", "2025-01-02"], [0.03, 0.04]),
        (["2025-01-03", "2025-01-02"], [0.03, 0.04]),
        (["2025-01-02", "2099-01-03"], [0.03, 0.04]),
        (["2025-01-02", "2025-01-03"], [3, 4]),
        (["2025-01-02", "2025-01-03"], [np.inf, 0.04]),
    ],
)
def test_reject_bad_source_inputs(dates, values):
    with pytest.raises(ValueError):
        validate_series(
            pd.DataFrame({"date": dates, "rate": values}),
            ["rate"],
            "2025-01-01",
            "2099-01-04",
            -0.1,
            0.3,
        )


def test_failed_fetch_records_source_without_fallback(tmp_path, monkeypatch):
    import yfinance

    class FailedTicker:
        def __init__(self, ticker):
            pass

        def history(self, **kwargs):
            raise ConnectionError("test source outage")

    monkeypatch.setattr(yfinance, "Ticker", FailedTicker)
    with pytest.raises(ValueError, match="Yahoo XIU.TO"):
        refresh_market_data("2025-01-01", "2025-02-01", tmp_path)
    path = next(tmp_path.glob("*/manifest.json"))
    manifest = json.loads(path.read_text())
    assert manifest["status"] == "FAILED"
    assert manifest["checksums"] == {}
    with pytest.raises(ValueError, match="Incomplete"):
        read_manifest(path.parent)


def test_snapshot_tampering_is_rejected(tmp_path):
    path = tmp_path / "prices.csv"
    path.write_text("date,price\n2025-01-02,100\n")
    (tmp_path / "manifest.json").write_text(
        json.dumps(
            {
                "status": "COMPLETE",
                "checksums": {"prices.csv": sha256(path.read_bytes()).hexdigest()},
            }
        )
    )
    read_manifest(tmp_path)
    path.write_text("date,price\n2025-01-02,1000\n")
    with pytest.raises(ValueError, match="checksum"):
        read_manifest(tmp_path)


def test_new_operational_controls():
    tables = sample_tables()
    tables["fx_rates"].loc[0, "base_currency"] = "USD"
    tables["yield_curve"].loc[0, "rate"] = 5
    tables["market_prices"].loc[0, "date"] = "2099-01-01"
    tables["market_prices"] = pd.concat([tables["market_prices"], tables["market_prices"].iloc[:1]])
    checks = quality_checks(tables, "2026-08-31")
    assert {"OBSERVATION_KEYS", "FUTURE_DATA", "INPUT_UNITS"} <= set(
        checks.loc[checks.severity == "FAIL", "check_id"]
    )


def test_public_snapshot_financial_behaviour(tmp_path):
    config = load_config()
    directory = Path(config["input_directory"])
    if not (directory / "factor_levels.csv").exists():
        pytest.skip(
            "Optional cached-real integration: run main.py refresh first; never downloads in tests"
        )
    manifest = read_manifest(directory)
    raw = Path(manifest["raw_directory"].replace("\\", "/"))
    if raw.exists():
        rebuilt = prepare_portfolio(raw, root=tmp_path / "rebuilt")
        assert read_manifest(rebuilt)["checksums"] == manifest["checksums"]
    db = connect(tmp_path / "public.db")
    try:
        import_directory(db, directory)
        config["database"] = str(tmp_path / "public.db")
        result = run_portfolio(db, config)
        assert result["metadata"]["observations"] == 252
        assert len(result["metadata"]["data_sources"]) == 8
        assert not (result["quality"].severity == "FAIL").any()
        assert not result["tables"]["factor_levels"].source.str.contains("SYNTHETIC").any()
        positions = result["positions"]
        assert result["nav"] == pytest.approx(
            (
                positions.quantity
                * positions.market_price
                * positions.multiplier
                * positions.fx_rate
            ).sum()
        )
        state, _ = market_state(db, config["as_of_date"])
        for sid, factor in [("SPY", "EQ_US"), ("XIU.TO", "EQ_CA"), ("TLT", "ETF_US")]:
            mark = positions.set_index("security_id").loc[sid]
            assert mark.market_price == state[factor]
        assert (result["fixed_income"].position_dv01 > 0).all()
        assert (result["curves"].query("scenario == 'Parallel +100 bp'").pnl < 0).all()
        crash = result["stress"].query("scenario == 'Equity crash' and asset_class == 'Equity'")
        assert len(crash) == 2 and (crash.pnl < 0).all()
        for _, group in result["risk"]["summary"].groupby("method"):
            assert group.sort_values("confidence")["var"].is_monotonic_increasing
            assert (group.es >= group["var"]).all()
        var = (
            result["risk"]["summary"]
            .query("method == 'Parametric' and confidence == .99")["var"]
            .iloc[0]
        )
        assert result["contributions"].component_var.sum() == pytest.approx(var)
        assert abs(result["attribution"]["residual"]) < 1e-7
        assert len(result["risk"]["mc_pnl"]) == 10000
        # Re-running the calculation must not fetch data or change a seeded distribution.
        repeat = run_portfolio(db, config)
        pd.testing.assert_series_equal(result["risk"]["mc_pnl"], repeat["risk"]["mc_pnl"])
        levels = result["tables"]["factor_levels"].pivot(
            index="date", columns="factor", values="level"
        )
        changes = factor_changes(levels, result["kinds"], config["as_of_date"], minimum=252)
        daily = levels.copy()
        daily.index = pd.to_datetime(daily.index)
        daily = daily.reindex(pd.bdate_range(daily.index.min(), config["as_of_date"]))
        for date in changes.index:
            assert daily.loc[[date, date - pd.offsets.BDay(1)]].notna().all().all()
    finally:
        db.close()
