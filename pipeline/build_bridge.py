#!/usr/bin/env python3
"""Build the unified cross-reference apparatus (corpus layer).

Source: ~/new-testament/data/nt_crossrefs.parquet (OpenBible.info, CC-BY) — the NT's
own citations, anchored on NT verses, pointing at NT and at the Hebrew scriptures.

We relabel `to_testament` OT → 'Tanakh' and NT → 'NT' so the bridge speaks the same
canon vocabulary as verses.parquet, and we validate how many endpoints actually
resolve to a verse in the unified corpus (book-name drift between OpenBible and
Sefaria is expected on a handful of books; we report it rather than hide it).

Writes data/bridge.parquet:
  from_ref, from_book, from_canon, to_ref, to_range, to_canon, votes,
  source, license, layer(='corpus'), resolved(bool)

Run:  python3 pipeline/build_bridge.py    (after ingest_corpus.py)
"""
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parent.parent
NT_XREF = Path.home() / "new-testament" / "data" / "nt_crossrefs.parquet"
VERSES = ROOT / "data" / "verses.parquet"
OUT = ROOT / "data" / "bridge.parquet"


def main():
    for p in (NT_XREF, VERSES):
        if not p.exists():
            raise SystemExit(f"Missing input: {p}\n(run ingest_corpus.py first, and "
                             "ensure the NT substrate is built)")
    con = duckdb.connect()
    con.execute(f"""
        CREATE TABLE bridge AS
        SELECT
            x.from_ref, x.from_book, 'NT' AS from_canon,
            x.to_ref, x.to_range,
            CASE x.to_testament WHEN 'OT' THEN 'Tanakh' ELSE 'NT' END AS to_canon,
            x.votes, x.source, x.license, 'corpus' AS layer,
            (v.ref IS NOT NULL) AS resolved
        FROM '{NT_XREF}' x
        LEFT JOIN '{VERSES}' v ON v.ref = x.to_ref
    """)
    con.execute(f"COPY bridge TO '{OUT}' (FORMAT parquet)")

    tot = con.sql("SELECT count(*) FROM bridge").fetchone()[0]
    by_canon = con.sql("""
        SELECT to_canon, count(*) n,
               sum(CASE WHEN resolved THEN 1 ELSE 0 END) res
        FROM bridge GROUP BY to_canon ORDER BY to_canon""").fetchall()
    print(f"→ data/bridge.parquet: {tot:,} cross-references")
    for canon, n, res in by_canon:
        pct = 100 * res / n if n else 0
        print(f"    NT → {canon:<7} {n:>7,}   {res:>7,} resolve to a verse ({pct:.1f}%)")
    # Surface the book-name drift so it can be fixed deliberately, not silently.
    unresolved = con.sql("""
        SELECT split_part(to_ref, ' ', 1) AS book, count(*) n
        FROM bridge WHERE NOT resolved
        GROUP BY 1 ORDER BY n DESC LIMIT 12""").fetchall()
    if unresolved:
        print("  unresolved endpoints by book (name drift vs. Sefaria — review):")
        for book, n in unresolved:
            print(f"    {book:<20} {n:>6,}")


if __name__ == "__main__":
    main()
