#!/usr/bin/env python3
"""Compile the authored Messianic layer (interpretive/*.yaml) into edges.

Each YAML entry becomes one or more Tanakh→NT interpretive edges (every tanakh ref ×
every nt ref), carrying the entry's category, confidence, basis and title. This is the
INTERPRETIVE layer — kept in its own file, never merged into bridge.parquet.

Crucially, every ref is validated against data/verses.parquet. A typo or a book-name
mismatch is a hard error, not a silent dangling edge: the interpretive layer's honesty
depends on it actually pointing at real Scripture.

Writes data/interpretive.parquet:
  id, category, title, from_ref(Tanakh), to_ref(NT), confidence, basis, note,
  layer(='interpretive')

Run:  python3 pipeline/build_interpretive.py    (after ingest_corpus.py)
"""
import re
import sys
from pathlib import Path

import duckdb
import yaml

# "Isaiah 53:1-12" -> anchor "Isaiah 53:1" (must exist in corpus), label kept for display.
# The corpus is verse-level; a range edge is anchored on its first verse.
_RANGE = re.compile(r"^(.+ \d+):(\d+)-\d+$")


def anchor_of(ref):
    m = _RANGE.match(ref.strip())
    return f"{m.group(1)}:{m.group(2)}" if m else ref.strip()

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "interpretive"
VERSES = ROOT / "data" / "verses.parquet"
OUT = ROOT / "data" / "interpretive.parquet"

VALID_CATEGORIES = {"messianic-prophecy", "type", "thematic-thread"}
VALID_CONFIDENCE = {"high", "medium", "graded"}


def load_entries():
    entries = []
    for f in sorted(SRC.glob("*.yaml")):
        doc = yaml.safe_load(f.read_text()) or {}
        entries += doc.get("prophecies", [])
    return entries


def main():
    if not VERSES.exists():
        raise SystemExit("Missing data/verses.parquet — run ingest_corpus.py first.")
    con = duckdb.connect()
    known = {r[0] for r in con.sql(f"SELECT ref FROM '{VERSES}'").fetchall()}
    canon = dict(con.sql(f"SELECT ref, canon FROM '{VERSES}'").fetchall())

    entries = load_entries()
    rows, errors = [], []
    for e in entries:
        eid = e.get("id", "<no-id>")
        if e.get("category") not in VALID_CATEGORIES:
            errors.append(f"{eid}: bad category {e.get('category')!r}")
        if e.get("confidence") not in VALID_CONFIDENCE:
            errors.append(f"{eid}: bad confidence {e.get('confidence')!r}")
        if not e.get("basis"):
            errors.append(f"{eid}: missing basis (interpretive edges require a basis)")
        tk = [(r, anchor_of(r)) for r in (e.get("tanakh", []) or [])]
        nt = [(r, anchor_of(r)) for r in (e.get("nt", []) or [])]
        for label, a in tk + nt:
            if a not in known:
                errors.append(f"{eid}: ref not in corpus: {label!r} (anchor {a!r})")
        # Orientation check: tanakh anchors should be Tanakh, nt should be NT.
        for label, a in tk:
            if a in canon and canon[a] != "Tanakh":
                errors.append(f"{eid}: '{label}' is {canon[a]}, expected Tanakh anchor")
        for label, a in nt:
            if a in canon and canon[a] != "NT":
                errors.append(f"{eid}: '{label}' is {canon[a]}, expected NT fulfillment")
        for tk_label, a in tk:
            for nt_label, b in nt:
                rows.append((eid, e["category"], e.get("title", ""),
                             a, tk_label, b, nt_label,
                             e["confidence"], e["basis"], e.get("note", ""),
                             "interpretive"))

    if errors:
        print("✗ interpretive layer has errors (nothing written):", file=sys.stderr)
        for err in errors:
            print("   -", err, file=sys.stderr)
        sys.exit(1)

    con.execute("""CREATE TABLE interp(
        id VARCHAR, category VARCHAR, title VARCHAR,
        from_ref VARCHAR, from_range VARCHAR, to_ref VARCHAR, to_range VARCHAR,
        confidence VARCHAR, basis VARCHAR, note VARCHAR, layer VARCHAR)""")
    con.executemany("INSERT INTO interp VALUES (?,?,?,?,?,?,?,?,?,?,?)", rows)
    con.execute(f"COPY interp TO '{OUT}' (FORMAT parquet)")

    print(f"→ data/interpretive.parquet: {len(rows):,} edges from "
          f"{len(entries)} authored threads")
    for cat, n, thr in con.sql("""
            SELECT category, count(*) edges, count(DISTINCT id) threads
            FROM interp GROUP BY category ORDER BY category""").fetchall():
        print(f"    {cat:<18} {thr:>2} threads → {n:>3} edges")
    for conf, n in con.sql("SELECT confidence, count(*) FROM interp "
                           "GROUP BY confidence ORDER BY confidence").fetchall():
        print(f"    confidence {conf:<8} {n:>3} edges")


if __name__ == "__main__":
    main()
