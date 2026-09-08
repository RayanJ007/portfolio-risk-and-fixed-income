from pathlib import Path
import sqlite3

ROOT = Path(__file__).resolve().parents[2]


def connect(path="data/risk.db"):
    if str(path) != ":memory:":
        Path(path).parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    connection.execute("PRAGMA foreign_keys=ON")
    for name in ("schema.sql", "views.sql"):
        connection.executescript((ROOT / "sql" / name).read_text())
    return connection
