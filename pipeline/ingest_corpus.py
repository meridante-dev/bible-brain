#!/usr/bin/env python3
"""Ingest the two upstream substrates into one unified canon table.

Reads (read-only) the published parquet of:
  - Torah Brain      ~/torah-brain/data/text/tanakh.parquet + tanakh_en.parquet  (PD)
  - New Testament     ~/new-testament/data/nt.parquet                            (PD)

Writes data/verses.parquet — the whole canon, one row per verse, Tanakh then NT,
with a single continuous `ord` so the brain can read Genesis 1:1 → Revelation 22:21
as one book. Corpus layer only; nothing interpretive here.

  columns: ref, book, canon, chapter, verse, text_en, text_orig, orig_lang,
           version, license, layer, ord

License gate: only Public Domain / CC0 / CC-BY(/-SA) rows are admitted; anything
else (unknown included) is refused, and the run reports what it dropped.

Run:  python3 pipeline/ingest_corpus.py
"""
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parent.parent
TORAH = Path.home() / "torah-brain" / "data" / "text"
NT = Path.home() / "new-testament" / "data"
OUT = ROOT / "data"
OUT.mkdir(parents=True, exist_ok=True)

TANAKH_HE = TORAH / "tanakh.parquet"
TANAKH_EN = TORAH / "tanakh_en.parquet"
NT_PARQUET = NT / "nt.parquet"

# The license gate — same discipline as both substrates. Unknown = refuse.
OK_LICENSES = ("Public Domain", "CC0", "CC-BY", "CC-BY-SA")


def _require(*paths):
    missing = [str(p) for p in paths if not p.exists()]
    if missing:
        raise SystemExit(
            "Missing upstream substrate data (run the substrate pipelines first):\n  "
            + "\n  ".join(missing)
        )


def main():
    _require(TANAKH_HE, TANAKH_EN, NT_PARQUET)
    con = duckdb.connect()
    def gate(col):
        return " OR ".join(f"{col} = '{l}'" for l in OK_LICENSES)
    lic = gate("license")

    # Tanakh: WEB-style English (JPS 1917) joined to the pointed Hebrew, one ord space.
    # NT: WEB text, its ord continued after the Tanakh.
    con.execute(f"""
        CREATE TABLE verses AS
        WITH tanakh AS (
            SELECT t.ref, t.book, 'Tanakh' AS canon, t.chapter, t.verse,
                   e.en          AS text_en,
                   t.he_pointed  AS text_orig,
                   'Hebrew'      AS orig_lang,
                   t.version, t.license, 'corpus' AS layer,
                   t.ord         AS src_ord
            FROM '{TANAKH_HE}' t
            LEFT JOIN '{TANAKH_EN}' e USING (ref)
            WHERE ({gate("t.license")})
        ),
        nt AS (
            SELECT ref, book, 'NT' AS canon, chapter, verse,
                   text          AS text_en,
                   NULL          AS text_orig,
                   'Greek'       AS orig_lang,      -- source-language witness: planned
                   version, license, 'corpus' AS layer,
                   ord           AS src_ord
            FROM '{NT_PARQUET}'
            WHERE ({lic})
        ),
        unified AS (
            SELECT *, 0 AS canon_ord FROM tanakh
            UNION ALL
            SELECT *, 1 AS canon_ord FROM nt
        )
        SELECT ref, book, canon, chapter, verse, text_en, text_orig, orig_lang,
               version, license, layer,
               row_number() OVER (ORDER BY canon_ord, src_ord) - 1 AS ord
        FROM unified
    """)

    con.execute(f"COPY verses TO '{OUT / 'verses.parquet'}' (FORMAT parquet)")

    # Report + license audit (what each source contributed, what got refused).
    tot = con.sql("SELECT count(*) FROM verses").fetchone()[0]
    by_canon = con.sql(
        "SELECT canon, count(*) n, min(ord) lo, max(ord) hi FROM verses "
        "GROUP BY canon ORDER BY lo").fetchall()
    raw_t = con.sql(f"SELECT count(*) FROM '{TANAKH_HE}'").fetchone()[0]
    raw_n = con.sql(f"SELECT count(*) FROM '{NT_PARQUET}'").fetchone()[0]

    print(f"→ data/verses.parquet: {tot:,} verses (one continuous canon)")
    for canon, n, lo, hi in by_canon:
        print(f"    {canon:<7} {n:>6,} verses   ord {lo:,}–{hi:,}")
    dropped = (raw_t + raw_n) - tot
    print(f"  license gate: admitted {tot:,} of {raw_t + raw_n:,} source rows"
          f" ({dropped:,} refused — unknown/non-permissive)")
    lics = con.sql("SELECT DISTINCT canon, version, license FROM verses "
                   "ORDER BY canon, version").fetchall()
    for canon, ver, l in lics:
        print(f"    [{l}] {canon}: {ver}")


if __name__ == "__main__":
    main()
