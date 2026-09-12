from pathlib import Path
import json

import numpy as np
import pandas as pd


def records(frame):
    return json.loads(frame.to_json(orient="records", date_format="iso"))


def markdown_table(frame):
    header = "| " + " | ".join(map(str, frame.columns)) + " |"
    separator = "| " + " | ".join("---" for _ in frame.columns) + " |"
    rows = []
    for row in frame.itertuples(index=False, name=None):
        rows.append(
            "| "
            + " | ".join(
                f"{x:,.2f}" if isinstance(x, (float, np.floating)) else str(x).replace("|", "/")
                for x in row
            )
            + " |"
        )
    return "\n".join([header, separator] + rows)


def export_reports(result, directory="outputs"):
    output = Path(directory)
    output.mkdir(parents=True, exist_ok=True)
    meta = result["metadata"]
    risk = result["risk"]
    attr = result["attribution"]
    tables = {
        key: result[key]
        for key in (
            "positions",
            "prior_positions",
            "fixed_income",
            "contributions",
            "stress",
            "curves",
            "quality",
        )
    }
    tables.update(
        risk_summary=risk["summary"],
        attribution=attr["drivers"],
        historical_pnl=risk["historical_pnl"].rename("pnl").rename_axis("date").reset_index(),
        mc_pnl=risk["mc_pnl"].rename("pnl").to_frame(),
        covariance=risk["covariance"].rename_axis("factor").reset_index(),
    )
    for name, frame in tables.items():
        frame.to_csv(output / f"{name}.csv", index=False)
    payload = {
        key: result[key]
        for key in ("metadata", "nav", "prior_nav", "daily_pnl", "external_flows", "performance")
    }
    payload.update({name: records(frame) for name, frame in tables.items()})
    payload["attribution_summary"] = {k: v for k, v in attr.items() if k != "drivers"}
    payload["inputs"] = {name: records(frame) for name, frame in result["tables"].items()}
    (output / "risk_report.json").write_text(
        json.dumps(payload, indent=2, allow_nan=False), encoding="utf-8"
    )
    allocation = result["positions"].groupby("asset_class", as_index=False).market_value.sum()
    stress = result["stress"].groupby("scenario", as_index=False).pnl.sum().sort_values("pnl")
    stress["new_nav"] = result["nav"] + stress.pnl
    alerts = result["quality"].loc[
        result["quality"].severity != "PASS", ["severity", "description"]
    ]
    text = f"""# Daily portfolio risk report

As of {meta['as_of_date']} | Base {meta['base_currency']} | One-day horizon

**{meta['source_label']}.** Calibration: {meta['window_start']} to {meta['window_end']}, {meta['observations']} synchronized observations. Sample covariance (ddof=1); zero drift. Monte Carlo: {meta['simulations']:,} simulations, seed {meta['seed']}. Positive VaR/ES denote losses; positive P&L denotes gains.

## Portfolio summary

NAV: **{result['nav']:,.0f} {meta['base_currency']}**. Prior NAV ({meta['prior_date']}): {result['prior_nav']:,.0f}. Flow-adjusted daily P&L: **{result['daily_pnl']:,.0f}**. External flows: {result['external_flows']:,.0f}. Coupon receipts must be entered as cash income trades.

{markdown_table(allocation)}

## One-day VaR and Expected Shortfall

Historical and Monte Carlo use full instrument repricing. Parametric uses local factor sensitivities and a Gaussian distribution. Confidence is a decimal (0.99 = 99%).

{markdown_table(risk['summary'])}

## Top contributors to 99% parametric VaR

Marginal VaR is CAD per added security unit. Component VaR is CAD; negative contributions are hedges.

{markdown_table(result['contributions'].sort_values('component_var',ascending=False)[['security_id','component_var','marginal_var','standalone_var']])}

Diversification benefit versus standalone VaRs: {result['contributions'].standalone_var.sum()-result['contributions'].component_var.sum():,.0f} CAD.

## Fixed income

Duration in years, convexity in years squared, yield in decimals. Position DV01 is CAD per 1 bp nominal-YTM bump; curve shocks use continuous zero rates.

{markdown_table(result['fixed_income'][['security_id','ytm','modified_duration','convexity','position_dv01']])}

## Stress testing

{markdown_table(stress)}

## Yield curves

{markdown_table(result['curves'])}

## Why did 99% parametric VaR change?

{attr['prior_var']:,.0f} → {attr['current_var']:,.0f} CAD; change **{attr['change']:,.0f} CAD**. {attr['methodology']}. This allocation is model-based, not causal.

{markdown_table(attr['drivers'])}

Interaction effect relative to standalone changes: {attr['interaction_vs_standalone']:,.2f} CAD (already allocated within drivers, do not add twice). Numerical residual: {attr['residual']:,.8f} CAD.

## Hypothetical performance diagnostics

{meta['performance_basis']}; these are scenario replay statistics, not realized investment performance. Annualization: 252 days; annual risk-free rate {meta['annual_risk_free_rate']:.1%}.

{markdown_table(pd.DataFrame(result['performance'].items(),columns=['metric','value']))}

## Data quality and key alerts

{markdown_table(result['quality'].groupby('severity').size().rename('count').reset_index())}

{markdown_table(alerts)}

Volatility-floor activations in Monte Carlo: {meta['volatility_floor_hits']}. No history is forward-filled. Holiday/missing-day gaps exclude both adjacent changes. See `reports/risk_methodology.md` for assumptions and limits.
"""
    if meta.get("data_sources"):
        sources = pd.DataFrame(meta["data_sources"])
        text += "\n## Public source snapshot\n\n"
        text += f"Retrieved {meta['snapshot_retrieved_at']}. Source status applies to this cached snapshot.\n\n"
        text += markdown_table(sources[["name", "series_id", "last_date", "units", "status"]])
        text += "\n\n" + meta["contract_assumptions"] + ".\n\n"
        text += "\n".join("- " + note for note in meta["source_warnings"]) + "\n"
    (output / "daily_risk_report.md").write_text(text, encoding="utf-8")
    return output / "risk_report.json"
