"""Create a formula-linked workbook from saved Python analytics using XlsxWriter."""

from datetime import datetime
from pathlib import Path
import json
import math

import xlsxwriter


def export_excel(report_path, output_path="models/risk_reporting_model.xlsx"):
    data = json.loads(Path(report_path).read_text(encoding="utf-8"))
    output = Path(output_path).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    positions = data["positions"]
    master = data["inputs"]["security_master"]
    classes = {r["security_id"]: r["asset_class"] for r in master}
    if len(classes) != len(master) or not positions:
        raise ValueError("Duplicate master or empty portfolio")
    values = [r["quantity"] * r["market_price"] * r["multiplier"] * r["fx_rate"] for r in positions]
    nav = sum(values)
    if not all(math.isfinite(v) for v in values) or nav <= 0 or abs(nav - data["nav"]) > 0.01:
        raise ValueError("NAV reconciliation failed")
    meta, attr = data["metadata"], data["attribution_summary"]
    names = [
        "Cover",
        "Portfolio Summary",
        "VaR",
        "Expected Shortfall",
        "Fixed Income",
        "Risk Contribution",
        "Stress Tests",
        "Yield Curve",
        "Risk Attribution",
        "Data Quality",
        "Positions",
        "Trades",
        "Security Master",
        "Market Data",
        "Daily Report",
        "Checks",
    ]
    # Cached opening values support previews. Excel recalculates formulas on opening;
    # nonlinear risk values remain snapshots and require a fresh Python run.
    with xlsxwriter.Workbook(
        output, {"strings_to_formulas": False, "strings_to_urls": False}
    ) as wb:
        wb.set_properties({"title": "Portfolio Risk & Fixed-Income Analytics", "author": ""})
        wb.set_calc_mode("auto")
        sheets = {n: wb.add_worksheet(n) for n in names}
        base = {"font_name": "Arial", "font_size": 10, "font_color": "#263D5A"}
        normal = wb.add_format(base)
        wrapped = wb.add_format(dict(base, text_wrap=True, valign="top"))
        number = wb.add_format(dict(base, num_format='#,##0.00;(#,##0.00);"—"'))
        money = wb.add_format(dict(base, num_format='#,##0;(#,##0);"—"'))
        percent = wb.add_format(dict(base, num_format="0.00%"))
        date_format = wb.add_format(dict(base, num_format="yyyy-mm-dd"))
        title = wb.add_format(dict(base, bold=True, font_size=15))
        header = wb.add_format(
            dict(
                base,
                bold=True,
                font_color="white",
                bg_color="#263D5A",
                text_wrap=True,
                valign="vcenter",
            )
        )
        warning = wb.add_format({"bg_color": "#FFF0CC", "font_color": "#805C13"})
        failure = wb.add_format({"bg_color": "#FCE5E3", "font_color": "#A42525"})

        def table(name, heading, columns, rows, widths):
            sheet = sheets[name]
            sheet.hide_gridlines(2)
            sheet.set_default_row(22)
            sheet.set_landscape()
            sheet.fit_to_pages(1, 0)
            for col, width in enumerate(widths):
                sheet.set_column(col, col, width, normal)
            sheet.write("A2", heading, title)
            sheet.write(
                "A3",
                f"{meta['as_of_date']} · {meta['base_currency']} · {meta['source_label']}",
                normal,
            )
            sheet.set_row(4, 34)
            sheet.write_row(4, 0, columns, header)
            if rows:
                sheet.add_table(
                    4,
                    0,
                    4 + len(rows),
                    len(columns) - 1,
                    {
                        "name": name.replace(" ", "") + "Table",
                        "style": "Table Style Light 1",
                        "columns": [{"header": c, "header_format": header} for c in columns],
                    },
                )
            for i, row in enumerate(rows, 5):
                for j, value in enumerate(row):
                    fmt = (
                        date_format
                        if isinstance(value, datetime)
                        else number if isinstance(value, (int, float)) else normal
                    )
                    sheet.write(i, j, value, fmt)
                if name in ("Cover", "Daily Report"):
                    sheet.set_row(i, max(38, 15 * (1 + max(len(str(v)) // 95 for v in row))))
                    for j, value in enumerate(row):
                        if isinstance(value, str):
                            sheet.write(i, j, value, wrapped)
            if len(rows) > 15:
                sheet.freeze_panes(5, 0)
            return sheet

        table(
            "Cover",
            "Portfolio Risk & Fixed-Income Analytics",
            ["Report", "Value"],
            [
                ["Portfolio", meta["portfolio_id"]],
                ["As of", datetime.fromisoformat(meta["as_of_date"])],
                ["Base currency", meta["base_currency"]],
                ["Data", meta["source_label"]],
                ["Snapshot retrieved", meta.get("snapshot_retrieved_at", "Not supplied")],
                [
                    "One-day confidence levels",
                    ", ".join(f"{c:.0%}" for c in meta["confidence_levels"]),
                ],
                ["Calibration observations", meta["observations"]],
                ["Recalculate cached data", "python main.py demo --excel"],
                ["Refresh public sources", "python main.py refresh; then rerun cached calculation"],
                [
                    "Risk snapshots",
                    "Re-run Python after changing holdings or market data",
                ],
            ],
            [32, 78],
        )
        p = table(
            "Positions",
            "Position valuation (CAD)",
            [
                "Security",
                "Quantity",
                "Local price",
                "Multiplier",
                "FX to CAD",
                "Market value",
                "Weight",
                "Asset class",
                "Currency",
            ],
            [
                [
                    r["security_id"],
                    r["quantity"],
                    r["market_price"],
                    r["multiplier"],
                    r["fx_rate"],
                    None,
                    None,
                    None,
                    r["currency"],
                ]
                for r in positions
            ],
            [20, 18, 18, 16, 17, 22, 15, 26, 15],
        )
        end = 5 + len(positions)
        input_format = wb.add_format(dict(base, font_color="#215CC4", num_format="#,##0.00"))
        for i, (r, v) in enumerate(zip(positions, values), 6):
            p.write_row(
                i - 1,
                1,
                [r[k] for k in ("quantity", "market_price", "multiplier", "fx_rate")],
                input_format,
            )
            p.write_formula(f"F{i}", f"=B{i}*C{i}*D{i}*E{i}", money, v)
            p.write_formula(f"G{i}", f"=F{i}/SUM($F$6:$F${end})", percent, v / nav)
            p.write_formula(
                f"H{i}",
                f"=XLOOKUP(A{i},'Security Master'!$A$6:$A${5+len(master)},'Security Master'!$D$6:$D${5+len(master)},\"Unmapped\",0)",
                normal,
                classes[r["security_id"]],
            )
        groups = list(dict.fromkeys(classes[r["security_id"]] for r in positions))
        allocations = [
            sum(v for r, v in zip(positions, values) if classes[r["security_id"]] == c)
            for c in groups
        ]
        summary = table(
            "Portfolio Summary",
            "Portfolio summary",
            ["Measure", "CAD"],
            [
                ["Net asset value", None],
                ["Prior NAV", data["prior_nav"]],
                ["External flows", data["external_flows"]],
                ["Flow-adjusted daily P&L", None],
                *[[c, None] for c in groups],
            ],
            [34, 23],
        )
        summary.write_formula("B6", f"=SUM('Positions'!F6:F{end})", money, nav)
        summary.write_formula(
            "B9", "=B6-B7-B8", money, nav - data["prior_nav"] - data["external_flows"]
        )
        for i, v in enumerate(allocations, 10):
            summary.write_formula(
                f"B{i}",
                f"=SUMIFS('Positions'!$F$6:$F${end},'Positions'!$H$6:$H${end},A{i})",
                money,
                v,
            )
        chart = wb.add_chart({"type": "column"})
        chart.add_series(
            {
                "categories": ["Portfolio Summary", 9, 0, 8 + len(groups), 0],
                "values": ["Portfolio Summary", 9, 1, 8 + len(groups), 1],
                "categories_data": groups,
                "values_data": allocations,
                "fill": {"color": "#375779"},
            }
        )
        chart.set_title({"name": "Asset allocation (CAD millions)"})
        chart.set_y_axis({"num_format": '0.0,,"m"'})
        chart.set_legend({"none": True})
        summary.insert_chart("D5", chart, {"x_scale": 1.25, "y_scale": 1.15})
        layouts = [
            (
                "VaR",
                "One-day Value at Risk",
                "risk_summary",
                ["Method", "Confidence", "Horizon (days)", "VaR (CAD)"],
                ["method", "confidence", "horizon_days", "var"],
                [24, 18, 19, 24],
            ),
            (
                "Expected Shortfall",
                "One-day Expected Shortfall",
                "risk_summary",
                ["Method", "Confidence", "ES (CAD)"],
                ["method", "confidence", "es"],
                [24, 18, 24],
            ),
            (
                "Fixed Income",
                "Fixed-income analytics",
                "fixed_income",
                [
                    "Security",
                    "Dirty price",
                    "Clean price",
                    "YTM",
                    "Macaulay (yr)",
                    "Modified (yr)",
                    "Convexity (yr²)",
                    "DV01 (CAD/bp)",
                ],
                [
                    "security_id",
                    "dirty_price",
                    "clean_price",
                    "ytm",
                    "macaulay_duration",
                    "modified_duration",
                    "convexity",
                    "position_dv01",
                ],
                [20, 18, 18, 15, 20, 20, 22, 23],
            ),
            (
                "Risk Contribution",
                "99% parametric risk contribution",
                "contributions",
                [
                    "Security",
                    "Component VaR (CAD)",
                    "Marginal VaR (CAD/unit)",
                    "Standalone VaR (CAD)",
                    "Asset class",
                    "Currency",
                    "Sector",
                ],
                [
                    "security_id",
                    "component_var",
                    "marginal_var",
                    "standalone_var",
                    "asset_class",
                    "currency",
                    "sector",
                ],
                [20, 25, 27, 25, 26, 15, 24],
            ),
            (
                "Stress Tests",
                "Full-repricing stress P&L",
                "stress",
                ["Scenario", "Security", "Asset class", "P&L (CAD)"],
                ["scenario", "security_id", "asset_class", "pnl"],
                [24, 20, 26, 24],
            ),
            (
                "Yield Curve",
                "Yield-curve scenario repricing",
                "curves",
                [
                    "Scenario",
                    "Security",
                    "Full P&L (CAD)",
                    "Linear P&L (CAD)",
                    "Nonlinear difference",
                ],
                [
                    "scenario",
                    "security_id",
                    "pnl",
                    "linear_pnl",
                    "nonlinear_difference",
                ],
                [26, 20, 25, 25, 26],
            ),
            (
                "Risk Attribution",
                "Change in 99% one-day parametric VaR",
                "attribution",
                ["Driver", "Allocated change (CAD)", "Standalone change (CAD)"],
                ["driver", "allocated_change", "standalone_change"],
                [36, 27, 29],
            ),
            (
                "Data Quality",
                "Operational controls",
                "quality",
                ["Check", "Severity", "Record", "Description", "Action"],
                ["check_id", "severity", "record", "description", "action"],
                [27, 14, 20, 68, 60],
            ),
        ]
        for name, heading, key, columns, fields, widths in layouts:
            table(
                name,
                heading,
                columns,
                [[r.get(f) for f in fields] for r in data[key]],
                widths,
            )
            for i, r in enumerate(data[key], 5):
                for j, f in enumerate(fields):
                    if f in ("confidence", "ytm"):
                        sheets[name].write_number(i, j, r[f], percent)
        a = sheets["Risk Attribution"]
        a.set_column("E:E", 37, normal)
        a.set_column("F:F", 22, number)
        for i, row in enumerate(
            [
                ["Reconciliation", "CAD"],
                ["Prior VaR", attr["prior_var"]],
                ["Current VaR", attr["current_var"]],
                ["Interactions already allocated", attr["interaction_vs_standalone"]],
                ["Numerical residual", attr["residual"]],
            ],
            4,
        ):
            a.write_row(i, 4, row, header if i == 4 else number)
        for text, fmt in (("WARN", warning), ("FAIL", failure)):
            sheets["Data Quality"].conditional_format(
                f"B6:B{5+len(data['quality'])}",
                {
                    "type": "text",
                    "criteria": "containing",
                    "value": text,
                    "format": fmt,
                },
            )
        input_layouts = [
            (
                "Trades",
                "Trade and cash ledger",
                "trades",
                [
                    "Trade ID",
                    "Security",
                    "Trade date",
                    "Settlement date",
                    "Quantity",
                    "Price",
                    "Currency",
                    "Type",
                ],
                [
                    "trade_id",
                    "security_id",
                    "trade_date",
                    "settlement_date",
                    "quantity",
                    "price",
                    "currency",
                    "trade_type",
                ],
                [29, 20, 19, 21, 22, 18, 15, 18],
            ),
            (
                "Security Master",
                "Security master",
                "security_master",
                [
                    "Security",
                    "Name",
                    "Type",
                    "Asset class",
                    "Currency",
                    "Maturity",
                    "Coupon",
                    "Frequency",
                    "Face",
                    "Multiplier",
                    "Rating",
                ],
                [
                    "security_id",
                    "name",
                    "security_type",
                    "asset_class",
                    "currency",
                    "maturity_date",
                    "coupon_rate",
                    "coupon_frequency",
                    "face_value",
                    "multiplier",
                    "credit_rating",
                ],
                [20, 34, 18, 25, 15, 20, 16, 16, 16, 16, 16],
            ),
            (
                "Market Data",
                "Market observations and provenance",
                "market_prices",
                [
                    "Date",
                    "Security",
                    "Local price",
                    "Adjusted price",
                    "Source",
                    "Retrieved at",
                ],
                [
                    "date",
                    "security_id",
                    "price",
                    "adjusted_price",
                    "source",
                    "retrieval_timestamp",
                ],
                [19, 20, 18, 20, 82, 32],
            ),
        ]
        for name, heading, key, columns, fields, widths in input_layouts:
            rows = [
                [
                    (
                        datetime.fromisoformat(r[f])
                        if f in ("date", "trade_date", "settlement_date", "maturity_date")
                        and r.get(f)
                        else r.get(f)
                    )
                    for f in fields
                ]
                for r in data["inputs"][key]
            ]
            table(name, heading, columns, rows, widths)
        if meta.get("data_sources"):
            source_sheet = sheets["Market Data"]
            fields = [
                "name",
                "series_id",
                "last_date",
                "units",
                "transformation",
                "url",
                "retrieved_at",
            ]
            source_sheet.write_row(
                "H5",
                [
                    "Source",
                    "Series",
                    "Last observation",
                    "Units",
                    "Transformation",
                    "URL",
                    "Retrieved at",
                ],
                header,
            )
            for j, width in enumerate([18, 40, 18, 27, 65, 85, 32], 7):
                source_sheet.set_column(j, j, width, wrapped)
            for i, source in enumerate(meta["data_sources"], 5):
                source_sheet.set_row(i, 64)
                source_sheet.write_row(i, 7, [source[field] for field in fields], wrapped)
        for i, r in enumerate(master, 5):
            if r.get("coupon_rate") is not None:
                sheets["Security Master"].write_number(i, 6, r["coupon_rate"], percent)
        table(
            "Daily Report",
            "Daily risk notes",
            ["Topic", "Method / assumption"],
            [
                [
                    "Calibration window",
                    f"{meta['window_start']} to {meta['window_end']}",
                ],
                [
                    "Loss convention",
                    "Positive loss VaR/ES, positive gain P&L; values in CAD",
                ],
                [
                    "Historical / Monte Carlo",
                    "Full bond and option repricing; instantaneous shocks, no carry",
                ],
                ["Covariance", meta["covariance"]],
                ["Simulations", meta["simulations"]],
                ["Random seed", meta["seed"]],
                ["Performance", meta["performance_basis"]],
                ["Attribution", attr["methodology"]],
                ["Volatility floor hits", meta["volatility_floor_hits"]],
                ["Instrument terms", meta.get("contract_assumptions", "See security master")],
                ["Snapshot limitations", " ".join(meta.get("source_warnings", []))],
                [
                    "Workbook refresh",
                    "Risk analytics are Python snapshots; rerun the CLI to refresh.",
                ],
                [
                    "Formula scope",
                    "Excel recalculates NAV, allocations and checks; saved opening values are calculated during export.",
                ],
            ],
            [27, 110],
        )
        checks = table(
            "Checks",
            "Independent reconciliations",
            ["Check", "Difference", "Tolerance", "Status"],
            [
                [label, None, tol, None]
                for label, tol in [
                    ("NAV versus Python", 0.01),
                    ("Component sum versus VaR", 0.01),
                    ("Attribution bridge", 0.01),
                    ("Position weights", 1e-10),
                ]
            ],
            [35, 24, 20, 18],
        )
        var = next(
            r["var"]
            for r in data["risk_summary"]
            if r["method"] == "Parametric" and r["confidence"] == 0.99
        )
        checks.set_column("F:F", 34, normal)
        checks.set_column("G:G", 24, number)
        checks.write_row("F5", ["Independent Python controls", "Value"], header)
        checks.write_row("F6", ["NAV", data["nav"]], number)
        checks.write_row("F7", ["99% parametric VaR", var], number)
        differences = [
            nav - data["nav"],
            sum(r["component_var"] for r in data["contributions"]) - var,
            attr["current_var"]
            - attr["prior_var"]
            - sum(r["allocated_change"] for r in data["attribution"]),
            sum(v / nav for v in values) - 1,
        ]
        formulas = [
            "='Portfolio Summary'!B6-G6",
            f"=SUM('Risk Contribution'!B6:B{5+len(data['contributions'])})-G7",
            f"='Risk Attribution'!F7-'Risk Attribution'!F6-SUM('Risk Attribution'!B6:B{5+len(data['attribution'])})",
            f"=SUM('Positions'!G6:G{end})-1",
        ]
        for i, (formula, difference, tol) in enumerate(
            zip(formulas, differences, [0.01, 0.01, 0.01, 1e-10]), 6
        ):
            checks.write_formula(f"B{i}", formula, number, difference)
            checks.write_formula(
                f"D{i}",
                f'=IF(ABS(B{i})<=C{i},"PASS","FAIL")',
                normal,
                "PASS" if abs(difference) <= tol else "FAIL",
            )
        checks.conditional_format(
            "D6:D9",
            {
                "type": "text",
                "criteria": "containing",
                "value": "FAIL",
                "format": failure,
            },
        )
    return output
