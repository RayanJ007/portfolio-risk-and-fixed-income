"""Explicit public downloads and auditable, immutable local snapshots."""

from datetime import datetime, timezone, timedelta
from hashlib import sha256
from io import StringIO
from pathlib import Path
import json

import numpy as np
import pandas as pd
import requests

TENORS = (1, 2, 5, 10, 30)
TICKERS = {"XIU.TO": ("CAD", "EQ_CA"), "SPY": ("USD", "EQ_US"), "TLT": ("USD", "ETF_US")}
FED_URL = "https://www.federalreserve.gov/data/yield-curve-tables/feds200628.csv"
BOC_URL = "https://www.bankofcanada.ca/stats/results/csv"
FRED_URL = "https://fred.stlouisfed.org/graph/fredgraph.csv"


def validate_series(frame, columns, start, end, lower=None, upper=None):
    """Reject malformed series before sorting or discarding missing observations."""
    if frame.empty or not {"date", *columns} <= set(frame.columns):
        raise ValueError("Missing source observations or columns")
    dates = pd.to_datetime(frame.date, format="%Y-%m-%d", errors="raise")
    if dates.isna().any() or dates.duplicated().any() or not dates.is_monotonic_increasing:
        raise ValueError("Duplicate, missing or non-monotonic source dates")
    today = datetime.now(timezone.utc).date().isoformat()
    if (frame.date < start).any() or (frame.date > min(end, today)).any():
        raise ValueError("Source observations outside requested date range or in future")
    values = frame[columns].apply(pd.to_numeric, errors="raise")
    if np.isinf(values.to_numpy()).any():
        raise ValueError("Infinite source value")
    observed = values.to_numpy()[values.notna().to_numpy()]
    if (
        not len(observed)
        or (lower is not None and np.any(observed < lower))
        or (upper is not None and np.any(observed > upper))
    ):
        raise ValueError("Unexpected source units or value range")
    return frame.assign(**{c: values[c] for c in columns})


def parse_zero_curve(text, currency, start, end):
    if currency == "USD":
        lines = text.splitlines()
        header = next((i for i, s in enumerate(lines) if s.startswith("Date,")), None)
        if header is None or "Continuously Compounded,SVENYXX" not in text:
            raise ValueError("Unexpected Federal Reserve zero-curve format")
        frame = pd.read_csv(StringIO("\n".join(lines[header:])), na_values=["NA"])
        mapping = {f"SVENY{t:02d}": str(t) for t in TENORS}
        scale = 0.01
    elif currency == "CAD":
        frame = pd.read_csv(StringIO(text), skipinitialspace=True, na_values=["na", "NA"])
        mapping = {f"ZC{t * 100}YR": str(t) for t in TENORS}
        scale = 1.0
    else:
        raise ValueError("Unsupported zero-curve currency")
    frame = frame.rename(columns={"Date": "date", **mapping})[["date", *mapping.values()]]
    # The Fed endpoint returns its full archive; preserve only the requested research window.
    frame = frame.loc[frame.date.between(start, end)].copy()
    frame[list(mapping.values())] *= scale
    return validate_series(frame, list(mapping.values()), start, end, -0.10, 0.30)


def parse_boc_fx(payload, start, end):
    detail = payload.get("seriesDetail", {}).get("FXUSDCAD", {})
    if detail.get("label") != "USD/CAD":
        raise ValueError("Unexpected Bank of Canada FX quote direction")
    rows = [
        {"date": r["d"], "rate": float(r["FXUSDCAD"]["v"])}
        for r in payload["observations"]
        if "FXUSDCAD" in r
    ]
    return validate_series(pd.DataFrame(rows), ["rate"], start, end, 0.5, 2.5)


def parse_spread(text, start, end):
    frame = pd.read_csv(StringIO(text), na_values=["."]).rename(
        columns={"observation_date": "date", "BAMLC0A0CM": "spread"}
    )
    frame["spread"] = pd.to_numeric(frame.spread, errors="raise") / 100
    return validate_series(frame, ["spread"], start, end, 0, 0.30)


def read_manifest(directory):
    directory = Path(directory)
    manifest = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
    if manifest["status"] != "COMPLETE":
        raise ValueError("Incomplete source snapshot; inspect manifest.json")
    for name, expected in manifest["checksums"].items():
        if Path(name).name != name:
            raise ValueError("Invalid manifest filename")
        if sha256((directory / name).read_bytes()).hexdigest() != expected:
            raise ValueError(f"Snapshot checksum mismatch: {name}")
    return manifest


def refresh_market_data(start, end, root="data/raw/public"):
    """Download a new snapshot. A failed refresh never replaces a working dataset."""
    import yfinance as yf

    if (
        pd.Timestamp(start) >= pd.Timestamp(end)
        or end >= datetime.now(timezone.utc).date().isoformat()
    ):
        raise ValueError("Request a completed historical period ending before today")
    stamp = datetime.now(timezone.utc).isoformat()
    directory = Path(root) / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    directory.mkdir(parents=True, exist_ok=False)
    manifest = dict(
        status="FETCHING",
        start=start,
        end=end,
        retrieved_at=stamp,
        sources=[],
        checksums={},
        warnings=[],
    )

    def save(name, frame, url, series, units, transformation, **extra):
        frame.to_csv(directory / f"{name}.csv", index=False)
        manifest["sources"].append(
            dict(
                name=name,
                url=url,
                series_id=series,
                units=units,
                transformation=transformation,
                retrieved_at=stamp,
                first_date=frame.date.min(),
                last_date=frame.dropna().date.max(),
                rows=len(frame),
                status="OK",
                **extra,
            )
        )

    source = "initialization"
    try:
        for ticker in [*TICKERS, "^VIX"]:
            source = f"Yahoo {ticker}"
            obj = yf.Ticker(ticker)
            history = obj.history(
                start=start,
                end=(datetime.fromisoformat(end) + timedelta(days=1)).strftime("%Y-%m-%d"),
                auto_adjust=False,
                actions=True,
            )
            if history.empty:
                raise ValueError(f"No history returned for {ticker}")
            history.index = history.index.tz_localize(None)
            frame = history.reset_index().rename(columns={"Date": "date"})
            frame["date"] = frame.date.dt.strftime("%Y-%m-%d")
            columns = ["Close", "Adj Close"] if ticker != "^VIX" else ["Close"]
            frame = validate_series(frame, columns, start, end, 0.00001)
            details = obj.history_metadata
            meta = {
                k: details.get(k)
                for k in (
                    "symbol",
                    "longName",
                    "shortName",
                    "currency",
                    "instrumentType",
                    "exchangeName",
                )
            }
            if ticker in TICKERS and (
                meta["currency"] != TICKERS[ticker][0] or meta["instrumentType"] != "ETF"
            ):
                raise ValueError(f"Unexpected security metadata for {ticker}")
            save(
                ticker.replace("^", ""),
                frame,
                f"https://finance.yahoo.com/quote/{ticker}/history/",
                ticker,
                "index points" if ticker == "^VIX" else meta["currency"] + " per share",
                (
                    "VIX / 100: annual volatility proxy"
                    if ticker == "^VIX"
                    else "Close for valuation; log adjusted-close ratios for shocks"
                ),
                security_metadata=meta,
            )
        source = "Bank of Canada FXUSDCAD"
        response = requests.get(
            "https://www.bankofcanada.ca/valet/observations/FXUSDCAD/json",
            params={"start_date": start, "end_date": end},
            timeout=45,
        )
        response.raise_for_status()
        save(
            "fx",
            parse_boc_fx(response.json(), start, end),
            response.url,
            "FXUSDCAD",
            "CAD per USD",
            "Identity; log changes",
        )
        source = "Bank of Canada zero curve"
        response = requests.get(
            BOC_URL,
            params={
                "lookupPage": "lookup_yield_curve.php",
                "startRange": "1986-01-01",
                "searchRange": "",
                "dFrom": start,
                "dTo": end,
            },
            timeout=45,
        )
        response.raise_for_status()
        save(
            "CAD",
            parse_zero_curve(response.text, "CAD", start, end),
            response.url,
            "ZC100YR,ZC200YR,ZC500YR,ZC1000YR,ZC3000YR",
            "continuous annual decimal",
            "Published fitted zero yields; selected observed nodes, no scaling",
        )
        source = "Federal Reserve GSW zero curve"
        response = requests.get(FED_URL, timeout=60)
        response.raise_for_status()
        save(
            "USD",
            parse_zero_curve(response.text, "USD", start, end),
            response.url,
            "SVENY01,SVENY02,SVENY05,SVENY10,SVENY30",
            "continuous annual decimal",
            "Published fitted zero yields in percent / 100",
        )
        source = "FRED BAMLC0A0CM"
        response = requests.get(
            FRED_URL, params={"id": "BAMLC0A0CM", "cosd": start, "coed": end}, timeout=45
        )
        response.raise_for_status()
        save(
            "spread",
            parse_spread(response.text, start, end),
            response.url,
            "BAMLC0A0CM",
            "annual spread decimal",
            "Percent / 100; index OAS used as a flat continuous spread proxy",
        )
        manifest["warnings"] = [
            "BoC curves have a publication lag; valuation is retrospective, not an as-published trading backtest.",
            "FRED ICE data may supply only three years and has redistribution restrictions.",
            "VIX is a 30-day S&P 500 volatility proxy, not the SPY contract's implied volatility.",
            "Current option-chain IV is deliberately excluded from historical valuation to avoid look-ahead.",
        ]
        manifest["status"] = "COMPLETE"
    except Exception as error:
        manifest["status"] = "FAILED"
        manifest["error"] = f"{source}: {error}"
        raise ValueError(
            f"Source retrieval failed: {source}. See {directory}/manifest.json"
        ) from error
    finally:
        manifest["checksums"] = {
            p.name: sha256(p.read_bytes()).hexdigest() for p in directory.glob("*.csv")
        }
        (directory / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return directory
