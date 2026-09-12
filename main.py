"""Refresh explicitly; ordinary portfolio and dashboard runs use cached observations."""

import argparse
from pathlib import Path
import json

from src.data.imports import import_directory
from src.data.market_data import read_manifest, refresh_market_data
from src.data.portfolio_data import prepare_portfolio
from src.database.connection import connect
from src.pipeline import load_config, run_portfolio
from src.reporting.daily_report import export_reports


def main():
    parser = argparse.ArgumentParser(description="Portfolio risk engine")
    parser.add_argument("command", choices=["refresh", "prepare", "demo", "run", "import", "excel"])
    parser.add_argument("--config", default="config/portfolio.yaml")
    parser.add_argument("--database")
    parser.add_argument("--input", help="Input CSV directory, or raw snapshot for prepare")
    parser.add_argument("--output", default="outputs")
    parser.add_argument("--data-root", default="data/processed", help="New prepared snapshot root")
    parser.add_argument("--start", default="2023-09-01")
    parser.add_argument("--end", default="2026-08-31", help="Inclusive historical download cutoff")
    parser.add_argument("--excel", action="store_true")
    args = parser.parse_args()
    if args.command in ("refresh", "prepare"):
        raw = refresh_market_data(args.start, args.end) if args.command == "refresh" else args.input
        if not raw:
            parser.error("prepare requires --input pointing to a raw snapshot")
        folder = prepare_portfolio(raw, root=args.data_root)
        Path(args.config).write_text((folder / "portfolio.yaml").read_text(), encoding="utf-8")
        print(f"Prepared {folder}; configuration updated. Run python main.py demo --excel")
        return
    config = load_config(args.config)
    if args.database:
        config["database"] = args.database
    if args.command == "excel":
        from src.reporting.excel_export import export_excel

        print(export_excel(Path(args.output) / "risk_report.json"))
        return
    inputs = args.input or config.get("input_directory", "data/processed")
    connection = connect(config["database"])
    try:
        if args.command == "import":
            import_directory(connection, inputs)
            print("CSV import complete")
            return
        if args.command == "demo":
            expected = read_manifest(inputs)
            if not connection.execute("SELECT COUNT(*) FROM trades").fetchone()[0]:
                import_directory(connection, inputs)
            stored = connection.execute("SELECT manifest FROM data_snapshot WHERE id=1").fetchone()
            if not stored or json.loads(stored[0])["checksums"] != expected["checksums"]:
                raise ValueError(
                    "Database snapshot differs from inputs; choose a new database path"
                )
        result = run_portfolio(connection, config)
        report = export_reports(result, args.output)
        from src.reporting.charts import export_charts

        export_charts(result, Path(args.output) / "charts")
        if args.excel:
            from src.reporting.excel_export import export_excel

            export_excel(report)
        print(f"NAV {result['nav']:,.2f} {config['base_currency']}; report: {report}")
        print(result["risk"]["summary"].to_string(index=False))
    finally:
        connection.close()


if __name__ == "__main__":
    main()
