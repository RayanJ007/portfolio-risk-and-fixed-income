"""Run from the repository root: python main.py demo."""

import argparse
from pathlib import Path

from src.data.imports import import_directory, fetch_boc_fx
from src.data.sample import write_sample
from src.database.connection import connect
from src.pipeline import load_config, run_portfolio
from src.reporting.daily_report import export_reports


def main():
    parser = argparse.ArgumentParser(description="Institutional portfolio risk engine")
    parser.add_argument(
        "command", choices=["demo", "mixed-demo", "run", "import", "fetch-fx", "excel"]
    )
    parser.add_argument("--config")
    parser.add_argument("--database")
    parser.add_argument("--input", default="data/sample")
    parser.add_argument("--output", default="outputs")
    parser.add_argument("--excel", action="store_true")
    args = parser.parse_args()
    config = load_config(args.config)
    if args.database:
        config["database"] = args.database
    elif args.command == "mixed-demo":
        config["database"] = "data/mixed_risk.db"
    if args.command == "mixed-demo":
        if args.input == "data/sample":
            args.input = "data/mixed_sample"
        if args.output == "outputs":
            args.output = "outputs/mixed"
    if args.command == "fetch-fx":
        frame = fetch_boc_fx("2025-01-01", config["as_of_date"], "data/raw")
        print(f"Archived {len(frame)} real Bank of Canada observations")
        return
    if args.command == "excel":
        from src.reporting.excel_export import export_excel

        print(export_excel(Path(args.output) / "risk_report.json"))
        return
    connection = connect(config["database"])
    try:
        if args.command == "import":
            import_directory(connection, args.input)
            print("CSV import complete")
            return
        if args.command in ("demo", "mixed-demo"):
            if not connection.execute("SELECT COUNT(*) FROM trades").fetchone()[0]:
                write_sample(
                    args.input, "data/raw/boc_usdcad.csv" if args.command == "mixed-demo" else None
                )
                import_directory(connection, args.input)
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
