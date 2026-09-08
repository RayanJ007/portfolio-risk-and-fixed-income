"""Rebuild the short, exploratory teaching notebooks."""

from pathlib import Path
import nbformat as nbf

setup = """from pathlib import Path
import sys
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

root = Path.cwd()
if not (root / "src").exists():
    root = root.parent
sys.path.insert(0, str(root))
"""
notebooks = {
    "01_portfolio_overview": [
        (
            "markdown",
            "# Portfolio overview\nRun `python main.py demo` first. This notebook explores the saved **synthetic** portfolio, in CAD. Quantities are settlement-date holdings. Changing a notebook variable does not change the SQL ledger.",
        ),
        ("code", setup),
        (
            "code",
            """positions = pd.read_csv(root / "outputs/positions.csv")
positions[["security_id", "currency", "quantity", "market_value", "weight"]]
""",
        ),
        (
            "code",
            """allocation = positions.groupby("asset_class").market_value.sum().sort_values()
(allocation / 1e6).plot.barh(title="Exposure by asset class (CAD millions)")
plt.xlabel("CAD millions")
assert np.isclose(positions.weight.sum(), 1)
""",
        ),
        (
            "markdown",
            "Compare market value with face amount for the bonds, and with notional underlying exposure for the option. Why is the option's market-value weight an incomplete description of its risk?",
        ),
    ],
    "02_fixed_income": [
        (
            "markdown",
            "# Bond price, duration and convexity\nRegular semiannual coupons. Nominal yields are decimals. The price is dirty; settlement is on a coupon date, so accrued interest is zero.",
        ),
        (
            "code",
            setup
            + "\nfrom src.pricing.bonds import bond_price, bond_analytics, yield_to_maturity\n",
        ),
        (
            "code",
            """terms = ("2026-08-31", "2036-08-31", 0.04, 2, 100)
metrics = bond_analytics(0.05, *terms)
pd.Series(metrics)
""",
        ),
        (
            "code",
            """yields = np.linspace(0.01, 0.09, 80)
full = np.array([bond_price(y, *terms) for y in yields])
dy = yields - 0.05
linear = metrics["dirty_price"] * (1 - metrics["modified_duration"] * dy)
quadratic = linear + 0.5 * metrics["dirty_price"] * metrics["convexity"] * dy**2
plt.plot(yields * 100, full, label="Full price")
plt.plot(yields * 100, linear, "--", label="Duration")
plt.plot(yields * 100, quadratic, ":", label="Duration + convexity")
plt.xlabel("Nominal YTM (%)")
plt.ylabel("Local price per 100 face")
plt.legend()
assert np.isclose(yield_to_maturity(metrics["dirty_price"], *terms), 0.05)
""",
        ),
        (
            "markdown",
            "Try a 30-year maturity or a zero coupon. Explain why positive convexity makes the price/yield relationship curved. Compare the DV01 duration estimate with the symmetric full-price bump.",
        ),
    ],
    "03_var_analysis": [
        (
            "markdown",
            "# VaR and tail severity\nThe saved Monte Carlo distribution fully reprices the synthetic portfolio. One-day risk, positive P&L for gains, positive VaR/ES for losses. The seed and estimation window are in the daily report.",
        ),
        ("code", setup + "\nfrom src.risk.engine import tail_risk\n"),
        (
            "code",
            """pnl = pd.read_csv(root / "outputs/mc_pnl.csv").pnl
pd.DataFrame([dict(confidence=a, **tail_risk(pnl, a)) for a in [0.95, 0.99]])
""",
        ),
        (
            "code",
            """risk = tail_risk(pnl, 0.99)
(pnl / 1e6).hist(bins=60)
plt.axvline(-risk["var"] / 1e6, color="red", label="99% VaR threshold")
plt.xlabel("One-day P&L (CAD millions)")
plt.ylabel("Simulations")
plt.legend()
parts = pd.read_csv(root / "outputs/contributions.csv")
parts[["security_id", "component_var", "marginal_var", "standalone_var"]]
""",
        ),
        (
            "markdown",
            "Why does ES exceed VaR? What would change if the return distribution had fatter tails? Component VaR reconciles to the parametric estimate, not to this nonlinear Monte Carlo quantile.",
        ),
    ],
    "04_stress_testing": [
        (
            "markdown",
            "# Stress and risk-change attribution\nScenario shocks are assumptions, not forecasts or probabilities. All P&L is CAD and reflects full repricing. The attribution bridge compares 99% one-day parametric VaR.",
        ),
        ("code", setup),
        (
            "code",
            """stress = pd.read_csv(root / "outputs/stress.csv")
totals = stress.groupby("scenario").pnl.sum().sort_values()
(totals / 1e6).plot.barh(title="Stress P&L (CAD millions)")
plt.xlabel("CAD millions")
""",
        ),
        (
            "code",
            """curve = pd.read_csv(root / "outputs/curves.csv")
curve.groupby("scenario")[["pnl", "linear_pnl", "nonlinear_difference"]].sum()
""",
        ),
        (
            "code",
            """attribution = pd.read_csv(root / "outputs/attribution.csv")
attribution.set_index("driver")[["allocated_change", "standalone_change"]]
""",
        ),
        (
            "markdown",
            "Explain why USD appreciation may offset losses on a US equity holding. In attribution, compare the average-path allocation with changing each driver alone. Their difference reflects interactions; it is not a second independent risk charge.",
        ),
    ],
}
output = Path(__file__).resolve().parents[1] / "notebooks"
output.mkdir(exist_ok=True)
for name, cells in notebooks.items():
    book = nbf.v4.new_notebook()
    book.metadata.kernelspec = dict(display_name="Python 3", language="python", name="python3")
    book.cells = [
        nbf.v4.new_markdown_cell(text) if kind == "markdown" else nbf.v4.new_code_cell(text)
        for kind, text in cells
    ]
    nbf.write(book, output / f"{name}.ipynb")
