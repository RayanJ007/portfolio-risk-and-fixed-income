"""Build a hypothetical portfolio from a verified public-market snapshot."""

from hashlib import sha256
from pathlib import Path
import json

import numpy as np
import pandas as pd
import yaml

from src.data.market_data import TICKERS, TENORS, read_manifest
from src.portfolio.positions import unit_values
from src.portfolio.returns import factor_changes


def prepare_portfolio(raw_directory, root="data/processed"):
    manifest = read_manifest(raw_directory)
    raw_directory = Path(raw_directory)
    frames = {p.stem: pd.read_csv(p) for p in raw_directory.glob("*.csv")}
    sources = {s["name"]: s for s in manifest["sources"]}
    marks, factors, curves = [], [], []

    def provenance(name):
        return dict(source=sources[name]["url"], retrieval_timestamp=sources[name]["retrieved_at"])

    def factor(name, dates, values, kind, source):
        factors.append(
            pd.DataFrame(
                dict(date=dates, factor=name, level=values, kind=kind, **provenance(source))
            ).dropna()
        )

    for ticker, (_, name) in TICKERS.items():
        frame = frames[ticker]
        marks.append(
            pd.DataFrame(
                dict(
                    date=frame.date,
                    security_id=ticker,
                    price=frame.Close,
                    adjusted_price=frame["Adj Close"],
                    **provenance(ticker),
                )
            ).dropna()
        )
        factor(name, frame.date, frame["Adj Close"], "log", ticker)
    fx = frames["fx"].assign(currency="USD", base_currency="CAD", **provenance("fx")).dropna()
    factor("FX_USD", fx.date, fx.rate, "log", "fx")
    factor("VOL_US", frames["VIX"].date, frames["VIX"].Close / 100, "absolute", "VIX")
    factor("SPREAD_US", frames["spread"].date, frames["spread"].spread, "absolute", "spread")
    for currency in ("CAD", "USD"):
        frame = frames[currency]
        for t in TENORS:
            curves.append(
                pd.DataFrame(
                    dict(
                        date=frame.date,
                        curve_name=currency,
                        tenor=t,
                        rate=frame[str(t)],
                        **provenance(currency),
                    )
                ).dropna()
            )
            factor(f"{currency}_{t}", frame.date, frame[str(t)], "absolute", currency)
    factors = pd.concat(factors, ignore_index=True).sort_values(["factor", "date"])
    levels = factors.pivot(index="date", columns="factor", values="level")
    common = levels.dropna().index
    if len(common) < 254:
        raise ValueError("Insufficient common public history")
    # Require consecutive weekdays for the two-date daily P&L comparison as well.
    pairs = [(a, b) for a, b in zip(common[:-1], common[1:]) if np.busday_count(a, b) == 1]
    if not pairs:
        raise ValueError("No consecutive common valuation dates")
    prior, date = pairs[-1]
    kinds = factors.groupby("factor").kind.first().to_dict()
    for day in (prior, date):
        factor_changes(levels, kinds, day, window=252, minimum=252)

    master = make_security_master(sources)
    market_prices = pd.concat(marks, ignore_index=True)
    trades = make_trades(master, frames, levels, market_prices, prior, date)
    tables = dict(
        portfolios=pd.DataFrame([dict(portfolio_id="PUBLIC_DEMO", base_currency="CAD")]),
        security_master=master,
        trades=trades,
        market_prices=market_prices,
        fx_rates=fx,
        yield_curve=pd.concat(curves, ignore_index=True),
        factor_levels=factors,
    )
    directory = Path(root) / raw_directory.name
    directory.mkdir(parents=True, exist_ok=False)
    for name, frame in tables.items():
        frame.to_csv(directory / f"{name}.csv", index=False)
    manifest = dict(
        manifest,
        raw_directory=raw_directory.as_posix(),
        as_of_date=date,
        prior_date=prior,
        portfolio_label="Hypothetical portfolio using public historical market data",
        contract_assumptions="Hypothetical bond terms; European SPY call, strike 800, expiry 2027-08-31, assumed dividend yield 1.2%; VIX proxy",
        checksums={p.name: sha256(p.read_bytes()).hexdigest() for p in directory.glob("*.csv")},
    )
    (directory / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    config = dict(
        portfolio_id="PUBLIC_DEMO",
        base_currency="CAD",
        as_of_date=date,
        prior_date=prior,
        window=252,
        minimum_history=252,
        confidence_levels=[0.95, 0.99],
        horizon_days=1,
        simulations=10000,
        seed=42,
        max_stale_business_days=2,
        annual_risk_free_rate=0.03,
        database=f"data/public_{raw_directory.name}.db",
        input_directory=directory.as_posix(),
    )
    (directory / "portfolio.yaml").write_text(
        yaml.safe_dump(config, sort_keys=False), encoding="utf-8"
    )
    return directory


def make_security_master(sources):
    """Real ETF metadata and explicit hypothetical contract terms."""
    securities = []
    for ticker, (currency, name) in TICKERS.items():
        info = sources[ticker]["security_metadata"]
        securities.append(
            dict(
                security_id=ticker,
                ticker=ticker,
                name=info["longName"] or info["shortName"],
                security_type="etf",
                asset_class="Equity" if ticker != "TLT" else "Fixed income ETF",
                currency=currency,
                sector="Broad market" if ticker != "TLT" else "Government",
                country="CA" if currency == "CAD" else "US",
                price_factor=name,
            )
        )
    securities += [
        dict(
            security_id="HYP_CAD_GOV",
            ticker="HYP-CAD-GOV",
            name="Hypothetical CAD government bond",
            security_type="bond",
            asset_class="Government bond",
            currency="CAD",
            sector="Government",
            country="CA",
            maturity_date="2031-08-31",
            coupon_rate=0.035,
            coupon_frequency=2,
            face_value=100,
            curve_name="CAD",
        ),
        dict(
            security_id="HYP_US_IG",
            ticker="HYP-US-IG",
            name="Hypothetical USD investment-grade bond",
            security_type="bond",
            asset_class="Corporate bond",
            currency="USD",
            sector="Broad corporate",
            country="US",
            maturity_date="2033-08-31",
            coupon_rate=0.05,
            coupon_frequency=2,
            face_value=100,
            curve_name="USD",
            spread_factor="SPREAD_US",
        ),
        dict(
            security_id="HYP_SPY_CALL",
            ticker="HYP-SPY-CALL",
            name="Hypothetical European SPY call",
            security_type="option",
            asset_class="Option",
            currency="USD",
            sector="Broad market",
            country="US",
            maturity_date="2027-08-31",
            strike=800,
            option_type="call",
            underlying_factor="EQ_US",
            volatility_factor="VOL_US",
            curve_name="USD",
            dividend_yield=0.012,
            multiplier=100,
        ),
        dict(
            security_id="CAD_CASH",
            ticker="CAD",
            name="CAD cash",
            security_type="cash",
            asset_class="Cash",
            currency="CAD",
            sector="Cash",
            country="CA",
        ),
        dict(
            security_id="USD_CASH",
            ticker="USD",
            name="USD cash",
            security_type="cash",
            asset_class="Cash",
            currency="USD",
            sector="Cash",
            country="US",
        ),
    ]
    master = pd.DataFrame(securities)
    master["multiplier"] = master.multiplier.fillna(1)
    master["dividend_yield"] = master.dividend_yield.fillna(0)
    master["allow_short"], master["benchmark"], master["credit_rating"] = 0, "EQ_CA", None
    return master


def make_trades(master, frames, levels, market_prices, prior, date):
    """Opening holdings, funded rebalance and income across the two-date interval."""
    if (master.maturity_date.dropna() <= date).any():
        raise ValueError("Hypothetical contracts matured; update portfolio terms explicitly")
    state = levels.loc[prior].copy()
    for ticker, (_, name) in TICKERS.items():
        state[name] = market_prices.loc[
            (market_prices.security_id == ticker) & (market_prices.date == prior), "price"
        ].iloc[0]
    prices = unit_values(master, state, prior, local=True).iloc[0]
    quantities = {
        "XIU.TO": 450000,
        "SPY": 30000,
        "TLT": 70000,
        "HYP_CAD_GOV": 220000,
        "HYP_US_IG": 100000,
        "HYP_SPY_CALL": 100,
        "CAD_CASH": 6000000,
        "USD_CASH": 2000000,
    }
    trades = [
        dict(
            trade_id=f"HYP-OPEN-{row.security_id}",
            portfolio_id="PUBLIC_DEMO",
            security_id=row.security_id,
            trade_date=prior,
            settlement_date=prior,
            quantity=quantities[row.security_id],
            price=float(prices[row.security_id] / row.multiplier),
            currency=row.currency,
            trade_type="opening",
        )
        for row in master.itertuples()
    ]
    buy_price = float(
        market_prices.query("security_id == 'XIU.TO' and date == @date").price.iloc[0]
    )
    for sid, qty, price in [("XIU.TO", 1000, buy_price), ("CAD_CASH", -1000 * buy_price, 1)]:
        trades.append(
            dict(
                trade_id=f"HYP-REBAL-{sid}",
                portfolio_id="PUBLIC_DEMO",
                security_id=sid,
                trade_date=date,
                settlement_date=date,
                quantity=qty,
                price=price,
                currency="CAD",
                trade_type="trade",
            )
        )
    # Book actual published distributions and hypothetical bond coupons across the comparison interval.
    for ticker, (currency, _) in TICKERS.items():
        distributions = frames[ticker].loc[
            frames[ticker].date.between(prior, date, inclusive="right")
        ]
        if (distributions.get("Stock Splits", pd.Series(0, index=distributions.index)) != 0).any():
            raise ValueError("Split across valuation dates requires explicit position adjustment")
        for row in distributions.itertuples():
            amount = float(getattr(row, "Dividends", 0)) * quantities[ticker]
            if amount:
                trades.append(
                    dict(
                        trade_id=f"HYP-DIV-{ticker}-{row.date}",
                        portfolio_id="PUBLIC_DEMO",
                        security_id=f"{currency}_CASH",
                        trade_date=row.date,
                        settlement_date=row.date,
                        quantity=amount,
                        price=1,
                        currency=currency,
                        trade_type="income",
                    )
                )
    for row in master.loc[master.security_type == "bond"].itertuples():
        payment = pd.Timestamp(row.maturity_date)
        while payment > pd.Timestamp(prior):
            if payment <= pd.Timestamp(date):
                day = payment.strftime("%Y-%m-%d")
                trades.append(
                    dict(
                        trade_id=f"HYP-COUPON-{row.security_id}-{day}",
                        portfolio_id="PUBLIC_DEMO",
                        security_id=f"{row.currency}_CASH",
                        trade_date=day,
                        settlement_date=day,
                        quantity=quantities[row.security_id]
                        * row.face_value
                        * row.coupon_rate
                        / row.coupon_frequency,
                        price=1,
                        currency=row.currency,
                        trade_type="income",
                    )
                )
            payment -= pd.DateOffset(months=6)
            payment += pd.offsets.MonthEnd(0)
    return pd.DataFrame(trades)
