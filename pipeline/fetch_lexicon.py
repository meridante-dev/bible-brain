#!/usr/bin/env python3
"""The lexicon layer — every Strong's number gets a definition.

Source: STEPBible TBESH (Hebrew) + TBESG (Greek) brief lexicons, CC BY 4.0 (see
SOURCES.md). Chosen deliberately: they are keyed to the SAME disambiguated Strong's
numbers (dStrong: H5959, G3933, G2264G, H0430G…) that the word layer already uses, so
the join words↔lexicon is exact — no cross-numbering mismatch. Hebrew defs derive from
BDB, Greek from Abbott-Smith (both PD), edited to the extended Strong's.

Downloaded at build into data/cache/ (gitignored, never re-hosted), same as fetch_words.

Writes data/lexicon.parquet:
  strongs(dStrong, the join key), estrong, lang, lemma, translit, morph_class,
  gloss, definition, source, license, layer(='lexicon')

Run:  python3 pipeline/fetch_lexicon.py        (after fetch_words.py, to report coverage)
"""
import re
import urllib.parse
import urllib.request
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / "data" / "cache"
CACHE.mkdir(parents=True, exist_ok=True)
WORDS = ROOT / "data" / "words.parquet"
OUT = ROOT / "data" / "lexicon.parquet"

RAW = ("https://raw.githubusercontent.com/STEPBible/STEPBible-Data/master/Lexicons/")
FILES = {
    "Hebrew": "TBESH - Translators Brief lexicon of Extended Strongs for Hebrew - STEPBible.org CC BY.txt",
    "Greek":  "TBESG - Translators Brief lexicon of Extended Strongs for Greek - STEPBible.org CC BY.txt",
}
LICENSE = "CC BY 4.0"
SOURCE = "STEPBible.org TBESH/TBESG (BDB + Abbott-Smith, PD)"

DSTRONG = re.compile(r"^([GH]\d{1,5}[A-Za-z]?)")
TAG = re.compile(r"<[^>]+>")
REF = re.compile(r"<ref[^>]*>|</ref>")


def download(fname):
    dest = CACHE / fname
    if not (dest.exists() and dest.stat().st_size > 0):
        print(f"  ↓ {fname[:38]}… ", end="", flush=True)
        urllib.request.urlretrieve(RAW + urllib.parse.quote(fname), dest)
        print(f"{dest.stat().st_size // 1024:,} KB")
    return dest


def clean(html):
    if not html:
        return ""
    s = html.replace("<br>", "; ").replace("<BR>", "; ").replace("<BR />", "; ")
    s = s.replace("<br />", "; ")
    s = REF.sub("", s)
    s = TAG.sub("", s)
    s = re.sub(r"\s*;\s*(;\s*)+", "; ", s)          # collapse repeated separators
    return re.sub(r"\s+", " ", s).strip(" ;")


def main():
    rows = []
    for lang, fname in FILES.items():
        path = download(fname)
        with path.open(encoding="utf-8") as fh:
            for line in fh:
                if not (line[:1] in "GH" and "\t" in line):
                    continue
                c = line.rstrip("\n").split("\t")
                if len(c) < 7:
                    continue
                m = DSTRONG.match(c[1].strip())
                if not m:
                    continue
                dstrong = m.group(1)
                estrong = c[0].strip()
                lemma, translit, morph_class = c[3].strip(), c[4].strip(), c[5].strip()
                gloss = c[6].strip()
                definition = clean("\t".join(c[7:]).strip()) if len(c) > 7 else ""
                rows.append((dstrong, estrong, lang, lemma, translit, morph_class,
                             gloss, definition, SOURCE, LICENSE, "lexicon"))

    con = duckdb.connect()
    con.execute("""CREATE TABLE lexicon(
        strongs VARCHAR, estrong VARCHAR, lang VARCHAR, lemma VARCHAR, translit VARCHAR,
        morph_class VARCHAR, gloss VARCHAR, definition VARCHAR,
        source VARCHAR, license VARCHAR, layer VARCHAR)""")
    con.executemany("INSERT INTO lexicon VALUES (" + ",".join("?" * 11) + ")", rows)
    # Keep one row per dStrong (first wins) so the join is 1:1.
    con.execute("""CREATE TABLE lex1 AS
        SELECT * FROM (SELECT *, row_number() OVER (PARTITION BY strongs) rn FROM lexicon)
        WHERE rn = 1""")
    con.execute("ALTER TABLE lex1 DROP COLUMN rn")
    con.execute(f"COPY lex1 TO '{OUT}' (FORMAT parquet)")

    n = con.sql("SELECT count(*) FROM lex1").fetchone()[0]
    print(f"\n→ data/lexicon.parquet: {n:,} Strong's entries")
    for lang, c in con.sql("SELECT lang, count(*) FROM lex1 GROUP BY lang ORDER BY lang").fetchall():
        print(f"    {lang:<7} {c:>6,} entries")

    # Coverage: how many distinct Strong's used in the word layer have a definition?
    if WORDS.exists():
        con.execute(f"CREATE VIEW w AS SELECT * FROM '{WORDS}'")
        cov = con.sql("""
            SELECT canon,
                   count(DISTINCT strongs) used,
                   count(DISTINCT CASE WHEN strongs IN (SELECT strongs FROM lex1)
                                       THEN strongs END) covered
            FROM w WHERE strongs <> '' GROUP BY canon ORDER BY canon""").fetchall()
        print("  coverage of the word layer:")
        for canon, used, covered in cov:
            pct = 100 * covered / used if used else 0
            print(f"    {canon:<7} {covered:,}/{used:,} distinct Strong's defined ({pct:.1f}%)")


if __name__ == "__main__":
    main()
