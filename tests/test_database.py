import sqlite3

import pytest

from tests.fixtures.synthetic import write_sample
from src.data.imports import import_directory
from src.database.connection import connect
from src.database.repository import settled_positions


def test_import_and_settlement_cutoff(tmp_path):
    write_sample(tmp_path)
    connection = connect(":memory:")
    import_directory(connection, tmp_path)
    old = settled_positions(connection, "DEMO", "2026-08-28").set_index("security_id")
    new = settled_positions(connection, "DEMO", "2026-08-31").set_index("security_id")
    assert new.loc["CA_EQ", "quantity"] - old.loc["CA_EQ", "quantity"] == 1000
    assert new.loc["CAD_CASH", "quantity"] - old.loc["CAD_CASH", "quantity"] == 585000
    with pytest.raises(sqlite3.IntegrityError):
        import_directory(connection, tmp_path)
    assert connection.execute("SELECT COUNT(*) FROM trades").fetchone()[0] == 11


def test_atomic_import(tmp_path):
    write_sample(tmp_path)
    (tmp_path / "factor_levels.csv").unlink()
    connection = connect(":memory:")
    with pytest.raises(ValueError, match="Missing import"):
        import_directory(connection, tmp_path)
    assert connection.execute("SELECT COUNT(*) FROM security_master").fetchone()[0] == 0
