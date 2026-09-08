from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import plotly.graph_objects as go


def attribution_figure(attribution):
    drivers = attribution["drivers"]
    return go.Figure(
        go.Waterfall(
            x=drivers.driver.to_list() + ["Total change"],
            y=drivers.allocated_change.to_list() + [0],
            measure=["relative"] * len(drivers) + ["total"],
            increasing={"marker": {"color": "#B34B43"}},
            decreasing={"marker": {"color": "#31866D"}},
            totals={"marker": {"color": "#263D5A"}},
        )
    ).update_layout(
        title="Drivers of the change in 99% one-day parametric VaR",
        yaxis_title="Cumulative change (CAD)",
        template="plotly_white",
        height=480,
        margin=dict(b=140),
        xaxis_tickangle=-35,
    )


def export_charts(result, directory):
    output = Path(directory)
    output.mkdir(parents=True, exist_ok=True)
    figure = attribution_figure(result["attribution"])
    figure.write_html(output / "risk_attribution.html", include_plotlyjs=True)
    fig, ax = plt.subplots(figsize=(11, 4.8))
    values = result["risk"]["mc_pnl"] / 1e6
    ax.hist(values, bins=70, color="#304D70", alpha=0.9)
    var = (
        result["risk"]["summary"].query("method=='Monte Carlo' and confidence==0.99")["var"].iloc[0]
        / 1e6
    )
    ax.axvline(-var, color="#B34B43", label=f"99% VaR: CAD {var:.2f}m")
    ax.set(
        xlabel="One-day P&L (CAD millions)",
        ylabel="Simulation count",
        title=f"{result['metadata']['as_of_date']} Monte Carlo full-repricing P&L\n{result['metadata']['source_label']}",
    )
    ax.legend()
    fig.tight_layout()
    fig.savefig(output / "pnl_distribution.png", dpi=160)
    plt.close(fig)
    attr = result["attribution"]
    d = attr["drivers"]
    fig, ax = plt.subplots(figsize=(12, 6))
    previous = 0.0
    labels = d.driver.to_list() + ["Total change"]
    for i, row in enumerate(d.itertuples()):
        value = row.allocated_change / 1e3
        ax.bar(
            i,
            abs(value),
            bottom=min(previous, previous + value),
            color="#B34B43" if value >= 0 else "#31866D",
        )
        previous += value
    ax.bar(len(labels) - 1, attr["change"] / 1e3, color="#263D5A")
    ax.axhline(0, color="#A0A0A0", linewidth=0.6)
    ax.set_xticks(range(len(labels)), labels, rotation=45, ha="right")
    ax.set(
        ylabel="Cumulative change (CAD thousands)",
        title=f"{result['metadata']['prior_date']} to {result['metadata']['as_of_date']}: 99% one-day parametric VaR change\nInteractions already allocated within drivers",
    )
    fig.tight_layout()
    fig.savefig(output / "risk_attribution.png", dpi=160)
    plt.close(fig)
