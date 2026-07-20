#!/usr/bin/env python3
"""Export the whole brain to a single SQLite file — the zero-install, offline format.

Parquet + duckdb is the build format; SQLite is the *handoff* format. sqlite3 is in the
Python standard library, so a recipient can query the brain with nothing installed (no pip,
no internet) — just Python, which macOS and Linux already ship. One portable file, also
openable by any SQLite tool or any language.

Reads data/*.parquet (via duckdb, at build time) -> writes data/bible-brain.sqlite with the
same tables + a few indexes for fast lookups.

Run:  python3 pipeline/export_sqlite.py        (after the build steps)
"""
import sqlite3
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parent.parent
D = ROOT / "data"
OUT = D / "bible-brain.sqlite"

TABLES = ["verses", "words", "lexicon", "lxx", "bridge", "interpretive", "interp_words"]
INDEXES = [
    ("verses", "ref"), ("verses", "canon"),
    ("words", "ref"), ("words", "strongs"),
    ("lexicon", "strongs"), ("lxx", "ref"),
    ("bridge", "from_ref"), ("bridge", "to_ref"),
    ("interpretive", "id"), ("interpretive", "from_ref"), ("interpretive", "to_ref"),
    ("interp_words", "id"),
]


def main():
    missing = [t for t in TABLES if not (D / f"{t}.parquet").exists()]
    if missing:
        raise SystemExit(f"Missing parquet for: {missing}. Run the build steps first.")

    if OUT.exists():
        OUT.unlink()
    con = duckdb.connect()
    sq = sqlite3.connect(OUT)
    for t in TABLES:
        rel = con.sql(f"SELECT * FROM '{D / (t + '.parquet')}'")
        cols = rel.columns
        rows = rel.fetchall()
        coldef = ", ".join(f'"{c}"' for c in cols)
        sq.execute(f'CREATE TABLE {t} ({coldef})')
        sq.executemany(f'INSERT INTO {t} VALUES ({",".join("?" * len(cols))})', rows)
        print(f"  {t:14} {len(rows):>7,} rows")
    for t, c in INDEXES:
        sq.execute(f'CREATE INDEX idx_{t}_{c} ON {t}("{c}")')
    sq.commit()
    sq.close()
    size = OUT.stat().st_size / 1_000_000
    print(f"→ data/bible-brain.sqlite ({size:.1f} MB) — query with Python stdlib, no pip")


if __name__ == "__main__":
    main()
