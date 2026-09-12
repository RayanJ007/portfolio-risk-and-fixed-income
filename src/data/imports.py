from datetime import datetime, timezone
from pathlib import Path
import json

import numpy as np
import pandas as pd
import requests

from src.database.repository import insert_frame
from src.data.market_data import read_manifest

INPUT_TABLES = (
    "portfolios",
    "security_master",
    "trades",
    "market_prices",
    "fx_rates",
    "yield_curve",
    "factor_levels",
)


def import_directory(connection, directory):
    """All-or-nothing CSV import. Duplicate keys and foreign keys are errors."""
    manifest_path = Path(directory) / "manifest.json"
    manifest = read_manifest(directory) if manifest_path.exists() else None
    if manifest and set(manifest["checksums"]) != {f"{t}.csv" for t in INPUT_TABLES}:
        raise ValueError("Manifest must cover all seven input tables")
    with connection:
        for table in INPUT_TABLES:
            path = Path(directory) / f"{table}.csv"
            if not path.exists():
                raise ValueError(f"Missing import file: {path.name}")
            frame = pd.read_csv(path)
            for col in ("date", "trade_date", "settlement_date", "maturity_date"):
                if col in frame:
                    dates = frame[col].dropna()
                    parsed = pd.to_datetime(dates, format="%Y-%m-%d", errors="raise")
                    if not parsed.dt.strftime("%Y-%m-%d").eq(dates).all():
                        raise ValueError(f"Use ISO dates: {col}")
            numeric = frame.select_dtypes(include="number")
            if np.isinf(numeric.to_numpy()).any():
                raise ValueError("Infinite numeric input")
            if "date" in frame:
                if frame.date.gt(datetime.now(timezone.utc).date().isoformat()).any():
                    raise ValueError("Future market observation")
                keys = {
                    "market_prices": ["security_id"],
                    "fx_rates": ["currency", "base_currency"],
                    "yield_curve": ["curve_name", "tenor"],
                    "factor_levels": ["factor"],
                }[table]
                for _, group in frame.groupby(keys):
                    if not group.date.is_monotonic_increasing:
                        raise ValueError(f"Non-monotonic dates: {table}")
            insert_frame(connection, table, frame)
        if manifest:
            connection.execute("INSERT INTO data_snapshot VALUES (1, ?)", (json.dumps(manifest),))


def fetch_boc_fx(start, end, output_directory):
    """Archive official USD/CAD observations; never substitute synthetic observations."""
    url = "https://www.bankofcanada.ca/valet/observations/FXUSDCAD/json"
    response = requests.get(url, params={"start_date": start, "end_date": end}, timeout=30)
    response.raise_for_status()
    payload = response.json()
    stamp = datetime.now(timezone.utc).isoformat()
    rows = [
        {
            "date": item["d"],
            "currency": "USD",
            "base_currency": "CAD",
            "rate": float(item["FXUSDCAD"]["v"]),
            "source": response.url,
            "retrieval_timestamp": stamp,
        }
        for item in payload["observations"]
        if "FXUSDCAD" in item
    ]
    frame = pd.DataFrame(rows)
    if frame.empty or not frame["rate"].gt(0).all():
        raise ValueError("No valid Bank of Canada observations")
    output = Path(output_directory)
    output.mkdir(parents=True, exist_ok=True)
    (output / "boc_usdcad_raw.json").write_text(response.text, encoding="utf-8")
    frame.to_csv(output / "boc_usdcad.csv", index=False)
    return frame
