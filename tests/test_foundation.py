from pathlib import Path

import yaml


def test_configuration():
    config = yaml.safe_load(Path("config/portfolio.yaml").read_text())
    assert config["simulations"] >= 10000
    assert config["horizon_days"] == 1
    assert config["base_currency"] == "CAD"
