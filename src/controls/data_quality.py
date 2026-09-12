import numpy as np
import pandas as pd

from src.portfolio.returns import factor_changes

CHECKS = {
    "DUPLICATE_TRADE": "Remove duplicate trade identifiers",
    "SECURITY_MAPPING": "Add or correct the security-master record",
    "TRADE_TERMS": "Correct dates, signed quantity, price or currency",
    "CASH_RECON": "Enter the offsetting settled cash trade or classify an external flow",
    "BOND_TERMS": "Correct bond coupon, frequency, face or maturity",
    "OPTION_TERMS": "Correct option terms or settle expired contracts",
    "CLASSIFICATION": "Complete currency, asset class and risk-factor mappings",
    "MISSING_PRICE": "Import a valid current local price",
    "STALE_PRICE": "Refresh the market quote",
    "MISSING_FX": "Import base currency per foreign unit FX",
    "STALE_FX": "Refresh the FX observation",
    "MISSING_FACTOR": "Import required price, FX, curve, spread or volatility factors",
    "STALE_FACTOR": "Refresh factor levels",
    "CURVE_DATA": "Import a complete finite zero curve",
    "FACTOR_CONSISTENCY": "Reconcile factor levels with price, FX and curve sources",
    "RETURN_HISTORY": "Import sufficient synchronized daily observations",
    "OUTLIER": "Review the original observation and corporate actions",
    "SHORT_POSITION": "Correct position or explicitly permit shorting",
    "POSITION_RECON": "Reconcile settled trades and position quantities",
    "VALUE_RECON": "Reconcile quantity, multiplier, local price and FX",
    "DATA_PROVENANCE": "Use real imports for empirical market conclusions",
    "OBSERVATION_KEYS": "Correct duplicate or non-monotonic dated observations",
    "FUTURE_DATA": "Remove observations dated after today",
    "INPUT_UNITS": "Check annual decimal rates/volatility and CAD per USD convention",
}


def quality_checks(
    tables,
    as_of_date,
    portfolio_id="DEMO",
    base_currency="CAD",
    max_age=2,
    minimum_history=100,
    positions=None,
):
    issues = []

    def flag(check, record, description, severity="FAIL"):
        issues.append(
            dict(
                check_id=check,
                severity=severity,
                record=str(record),
                description=description,
                action=CHECKS[check],
            )
        )

    master = tables["security_master"]
    for table, keys in {
        "market_prices": ["security_id"],
        "fx_rates": ["currency", "base_currency"],
        "yield_curve": ["curve_name", "tenor"],
        "factor_levels": ["factor"],
    }.items():
        frame = tables[table]
        if frame.duplicated(["date", *keys]).any() or any(
            not group.date.is_monotonic_increasing for _, group in frame.groupby(keys)
        ):
            flag("OBSERVATION_KEYS", table, "Duplicate or non-monotonic observations")
        if frame.date.gt(pd.Timestamp.now(tz="UTC").date().isoformat()).any():
            flag("FUTURE_DATA", table, "Market observation dated in the future")
    rates = tables["yield_curve"].rate
    fx_inputs = tables["fx_rates"]
    absolute = tables["factor_levels"]
    rate_factors = absolute.loc[
        absolute.factor.str.startswith(("CAD_", "USD_", "SPREAD_")), "level"
    ]
    vol_factors = absolute.loc[absolute.factor.str.startswith("VOL_"), "level"]
    if (
        not rates.between(-0.10, 0.30).all()
        or not rate_factors.between(-0.10, 0.30).all()
        or not vol_factors.between(0.00001, 3).all()
    ):
        flag("INPUT_UNITS", "rates/volatility", "Unexpected decimal units or value range")
    if (
        not fx_inputs.currency.eq("USD").all()
        or not fx_inputs.base_currency.eq("CAD").all()
        or not fx_inputs.rate.between(0.5, 2.5).all()
    ):
        flag("INPUT_UNITS", "FX", "Expected CAD per USD; verify source series and quote direction")
    trades = tables["trades"].loc[tables["trades"].portfolio_id == portfolio_id]
    known = set(master.security_id)
    for sid in master.loc[master.security_id.duplicated(False), "security_id"]:
        flag("SECURITY_MAPPING", sid, "Duplicate security master")
    for tid in trades.loc[trades.trade_id.duplicated(False), "trade_id"].unique():
        flag("DUPLICATE_TRADE", tid, "Duplicate trade identifier")
    for row in trades.itertuples():
        if row.security_id not in known:
            flag("SECURITY_MAPPING", row.trade_id, f"Unknown security {row.security_id}")
            continue
        currency = master.loc[master.security_id == row.security_id, "currency"].iloc[0]
        try:
            valid_dates = pd.Timestamp(row.settlement_date) >= pd.Timestamp(row.trade_date)
        except (ValueError, TypeError):
            valid_dates = False
        if (
            not valid_dates
            or not np.isfinite([row.price, row.quantity]).all()
            or row.price < 0
            or row.quantity == 0
            or row.currency != currency
            or row.trade_type not in ("trade", "opening", "external", "income")
        ):
            flag("TRADE_TERMS", row.trade_id, "Invalid trade terms or currency mismatch")
    settled = trades.loc[(trades.settlement_date <= as_of_date) & (trades.trade_date <= as_of_date)]
    funded = settled.loc[settled.trade_type == "trade"].merge(
        master[["security_id", "multiplier"]], on="security_id", how="left"
    )
    funded["cash_effect"] = funded.quantity * funded.price * funded.multiplier
    for (day, currency), amount in (
        funded.groupby(["settlement_date", "currency"]).cash_effect.sum().items()
    ):
        if abs(amount) > 0.01:
            flag("CASH_RECON", f"{day} {currency}", f"Unfunded trade cash amount {amount:,.2f}")
    quantities = settled.groupby("security_id").quantity.sum()
    active = set(quantities.loc[quantities.abs() > 1e-10].index)
    if positions is not None:
        active |= set(positions.security_id)
    active_master = master.loc[master.security_id.isin(active)]
    for row in active_master.itertuples():
        if row.currency not in ("CAD", "USD") or pd.isna(row.asset_class) or not row.asset_class:
            flag(
                "CLASSIFICATION", row.security_id, "Missing classification or unsupported currency"
            )
        fields = {
            "equity": ["price_factor"],
            "etf": ["price_factor"],
            "bond": ["curve_name"],
            "option": ["curve_name", "underlying_factor", "volatility_factor"],
        }
        for field in fields.get(row.security_type, []):
            if pd.isna(getattr(row, field)) or not getattr(row, field):
                flag("CLASSIFICATION", row.security_id, f"Missing {field}")
        if row.security_type == "bond":
            try:
                valid = (
                    pd.Timestamp(row.maturity_date) > pd.Timestamp(as_of_date)
                    and np.isfinite([row.coupon_rate, row.face_value, row.coupon_frequency]).all()
                    and row.coupon_rate >= 0
                    and row.face_value > 0
                    and row.coupon_frequency in (1, 2, 4, 12)
                )
            except (ValueError, TypeError):
                valid = False
            if not valid:
                flag("BOND_TERMS", row.security_id, "Invalid or matured fixed-rate bond")
        if row.security_type == "option":
            try:
                valid = (
                    pd.Timestamp(row.maturity_date) > pd.Timestamp(as_of_date)
                    and row.strike > 0
                    and row.option_type in ("call", "put")
                    and row.multiplier > 0
                )
            except (ValueError, TypeError):
                valid = False
            if not valid:
                flag("OPTION_TERMS", row.security_id, "Invalid or expired option")
        if quantities.get(row.security_id, 0) < 0 and not row.allow_short:
            flag("SHORT_POSITION", row.security_id, "Short position is not allowed")

    def latest(frame, key, value, missing, stale):
        rows = frame.loc[(frame[key] == value) & (frame.date <= as_of_date)].sort_values("date")
        if rows.empty:
            flag(missing, value, "No observation on or before valuation date")
            return None
        last = rows.iloc[-1]
        if np.busday_count(np.datetime64(last.date, "D"), np.datetime64(as_of_date, "D")) > max_age:
            flag(stale, value, f"Last observation {last.date}")
        return last

    prices = tables["market_prices"]
    fx = tables["fx_rates"]
    factors = tables["factor_levels"]
    if (factors.groupby("factor").kind.nunique() > 1).any():
        flag(
            "FACTOR_CONSISTENCY", "factor history", "Factor shock convention changes within history"
        )
    current = {}
    for name in factors.factor.unique():
        rows = factors.loc[(factors.factor == name) & (factors.date <= as_of_date)].sort_values(
            "date"
        )
        if not rows.empty:
            current[name] = rows.iloc[-1]
    for row in active_master.loc[active_master.security_type.isin(["equity", "etf"])].itertuples():
        mark = latest(prices, "security_id", row.security_id, "MISSING_PRICE", "STALE_PRICE")
        if mark is not None:
            if not np.isfinite(mark.price) or mark.price <= 0:
                flag("MISSING_PRICE", row.security_id, "Nonpositive or invalid price")
            if row.price_factor in current and not np.isclose(
                current[row.price_factor].level, mark.adjusted_price, rtol=1e-8
            ):
                flag(
                    "FACTOR_CONSISTENCY",
                    row.security_id,
                    "Return factor differs from adjusted price",
                )
    for currency in set(active_master.currency) - {base_currency}:
        mark = latest(
            fx.loc[fx.base_currency == base_currency],
            "currency",
            currency,
            "MISSING_FX",
            "STALE_FX",
        )
        if mark is not None:
            if not np.isfinite(mark.rate) or mark.rate <= 0:
                flag("MISSING_FX", currency, "Nonpositive or invalid FX")
            if f"FX_{currency}" in current and not np.isclose(
                current[f"FX_{currency}"].level, mark.rate, rtol=1e-8
            ):
                flag("FACTOR_CONSISTENCY", currency, "FX factor differs from conversion rate")
    required = set()
    for col in ("price_factor", "spread_factor", "underlying_factor", "volatility_factor"):
        required.update(active_master[col].dropna())
    required.update(f"FX_{c}" for c in set(active_master.currency) - {base_currency})
    for curve in active_master.curve_name.dropna().unique():
        rows = tables["yield_curve"].loc[
            (tables["yield_curve"].curve_name == curve) & (tables["yield_curve"].date <= as_of_date)
        ]
        if rows.empty:
            flag("CURVE_DATA", curve, "Missing yield curve")
            continue
        rows = rows.sort_values("date").groupby("tenor").tail(1)
        expected = {name for name in current if name.startswith(curve + "_")}
        observed = {f"{curve}_{tenor:g}" for tenor in rows.tenor}
        if expected - observed:
            flag("CURVE_DATA", curve, "Curve table is missing mapped factor tenors")
        if (
            len(rows) < 2
            or not np.isfinite(rows[["tenor", "rate"]]).all().all()
            or (rows.tenor <= 0).any()
        ):
            flag("CURVE_DATA", curve, "Invalid curve points")
        for row in rows.itertuples():
            name = f"{curve}_{row.tenor:g}"
            required.add(name)
            if (
                np.busday_count(np.datetime64(row.date, "D"), np.datetime64(as_of_date, "D"))
                > max_age
            ):
                flag("CURVE_DATA", name, "Stale curve point")
            if name in current and not np.isclose(current[name].level, row.rate, rtol=1e-8):
                flag("FACTOR_CONSISTENCY", name, "Curve factor differs from zero rate")
    for name in required:
        row = latest(factors, "factor", name, "MISSING_FACTOR", "STALE_FACTOR")
        if row is not None and (
            not np.isfinite(row.level)
            or (row.kind == "log" and row.level <= 0)
            or (name.startswith("VOL_") and row.level <= 0)
        ):
            flag("MISSING_FACTOR", name, "Invalid factor level")
    try:
        kinds = factors.groupby("factor").kind.first().to_dict()
        levels = factors.pivot(index="date", columns="factor", values="level")
        changes = factor_changes(levels, kinds, as_of_date, minimum=minimum_history)
        # Use robust scale, plus an economic floor; do not mark ordinary tiny rate moves as outliers.
        med = changes.median()
        mad = (changes - med).abs().median() * 1.4826
        bounds = mad.clip(lower=1e-6) * 8
        for name in changes.columns:
            extreme = changes.index[(changes[name] - med[name]).abs() > bounds[name]]
            if len(extreme):
                dates = ", ".join(d.strftime("%Y-%m-%d") for d in extreme)
                flag(
                    "OUTLIER",
                    name,
                    f"Daily move exceeds eight robust standard deviations: {dates}",
                    "WARN",
                )
    except (ValueError, KeyError, TypeError):
        flag(
            "RETURN_HISTORY", "portfolio", "Missing, duplicate or insufficient synchronized history"
        )
    if positions is not None:
        actual = positions.set_index("security_id").quantity
        for sid in set(actual.index) | set(quantities.index):
            if not np.isclose(actual.get(sid, 0), quantities.get(sid, 0), atol=1e-6, rtol=0):
                flag("POSITION_RECON", sid, "Position does not reconcile to settled trades")
        for row in positions.itertuples():
            expected = row.quantity * row.market_price * row.multiplier * row.fx_rate
            if not np.isfinite(expected) or not np.isclose(
                row.market_value, expected, atol=0.01, rtol=1e-10
            ):
                flag(
                    "VALUE_RECON",
                    row.security_id,
                    "Market value differs from quantity x price x multiplier x FX",
                )
    if any(
        frame.get("source", pd.Series(dtype=str)).astype(str).str.contains("SYNTHETIC").any()
        for frame in tables.values()
    ):
        flag("DATA_PROVENANCE", "dataset", "Contains explicitly synthetic teaching data", "WARN")
    failed = {r["check_id"] for r in issues}
    issues.extend(
        dict(
            check_id=c,
            severity="PASS",
            record="portfolio",
            description="No exceptions in evaluated scope",
            action="",
        )
        for c in CHECKS
        if c not in failed
    )
    return pd.DataFrame(issues)
