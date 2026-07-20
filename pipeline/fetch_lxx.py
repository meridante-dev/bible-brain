#!/usr/bin/env python3
"""The Septuagint layer — the Greek Old Testament, the hinge between the testaments.

The NT usually quotes the Hebrew scriptures from the GREEK Septuagint, not the Masoretic
Hebrew. This layer lets the brain set the three witnesses side by side (MT Hebrew · LXX
Greek · NT Greek) and show *why* a quotation matches — e.g. Isaiah 7:14 reads עַלְמָה
(almah) in Hebrew but ἡ παρθένος (parthenos) in the LXX, which is the word Matthew 1:23
quotes.

Source: Swete's Septuagint (1930), via github.com/nathans/lxx-swete — text CC BY-SA 4.0
(SHARE-ALIKE is viral: a redistributed derivative of THIS table must stay BY-SA; kept in
its own parquet and gitignored). Underlying Swete text is Public Domain. See SOURCES.md.
No clean-licensed *word-tagged* LXX exists (CATSS morphology is NonCommercial — refused),
so this is verse-level Greek text; word-level LXX tagging is a later, separate phase.

We align the LXX to the Tanakh's Masoretic references so it joins verses.parquet:
  - most books: ref is identical
  - Psalms: the LXX numbering is shifted; we map LXX→MT for the clean 10–112 range
    (covers Ps 16, 22, 110, 118 — the messianic psalms). Combined/split psalms (9, 113–117,
    146–147) and Jeremiah's reordered chapters are left LXX-native and reported, not faked.

Writes data/lxx.parquet:
  ref(MT-aligned), lxx_ref(native), book, chapter, verse, text_lxx,
  version, license, source, layer(='corpus'), resolved

Run:  python3 pipeline/fetch_lxx.py         (after ingest_corpus.py)
"""
import json
import urllib.request
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / "data" / "cache" / "lxx-swete"
CACHE.mkdir(parents=True, exist_ok=True)
VERSES = ROOT / "data" / "verses.parquet"
OUT = ROOT / "data" / "lxx.parquet"

API = "https://api.github.com/repos/nathans/lxx-swete/contents/data"
LICENSE = "CC BY-SA 4.0"
SOURCE = "Swete LXX 1930 (github.com/nathans/lxx-swete; text Public Domain)"

# Swete file number -> Tanakh (Sefaria) book name. Protocanonical books only — the
# deuterocanonical books (Judith, Tobit, Maccabees, Wisdom, Sirach, Baruch, …) and the
# Greek recensions of Esdras/Esther/Daniel-additions have no Masoretic counterpart to
# align to, so they are deliberately not ingested here.
LXX_BOOKS = {
    "01": "Genesis", "02": "Exodus", "03": "Leviticus", "04": "Numbers",
    "05": "Deuteronomy", "06": "Joshua", "08": "Judges", "10": "Ruth",
    "11": "I Samuel", "12": "II Samuel", "13": "I Kings", "14": "II Kings",
    "15": "I Chronicles", "16": "II Chronicles", "27": "Psalms", "29": "Proverbs",
    "31": "Song of Songs", "32": "Job", "36": "Hosea", "37": "Amos", "38": "Micah",
    "39": "Joel", "40": "Obadiah", "41": "Jonah", "42": "Nahum", "43": "Habakkuk",
    "44": "Zephaniah", "45": "Haggai", "46": "Zechariah", "47": "Malachi",
    "48": "Isaiah", "49": "Jeremiah", "51": "Lamentations", "53": "Ezekiel",
    "57": "Daniel",
}


def psalm_lxx_to_mt(ch):
    # LXX 1–8 = MT 1–8; LXX 10–112 = MT 11–113 (+1). Combined psalms left native.
    if ch <= 8:
        return ch
    if 10 <= ch <= 112:
        return ch + 1
    return ch  # 9, 113–117, 146–147: LXX-native (reported, not faked)


def list_files():
    with urllib.request.urlopen(API) as r:
        return json.load(r)


def download(name, url):
    dest = CACHE / name
    if not (dest.exists() and dest.stat().st_size > 0):
        urllib.request.urlretrieve(url, dest)
    return dest


def parse_book(path, book):
    """Group one-word-per-line rows into verses, preserving word order."""
    verses = {}          # (mt_ch, vs) -> [words], and remember native ch
    native = {}
    order = []
    for line in path.open(encoding="utf-8"):
        line = line.rstrip("\n")
        if not line or " " not in line:
            continue
        ref, word = line.split(" ", 1)
        parts = ref.split(".")
        if len(parts) < 3:
            continue
        try:
            ch, vs = int(parts[-2]), int(parts[-1])
        except ValueError:
            continue
        if vs == 0:                       # headings / superscription markers
            continue
        mt_ch = psalm_lxx_to_mt(ch) if book == "Psalms" else ch
        key = (mt_ch, vs)
        if key not in verses:
            verses[key] = []
            native[key] = ch
            order.append(key)
        verses[key].append(word)
    return [(mt_ch, vs, native[(mt_ch, vs)], " ".join(verses[(mt_ch, vs)]))
            for (mt_ch, vs) in order]


def main():
    if not VERSES.exists():
        raise SystemExit("Missing data/verses.parquet — run ingest_corpus.py first.")
    files = list_files()
    rows = []
    print("  downloading + parsing Swete LXX books…")
    for f in files:
        num = f["name"][:2]
        book = LXX_BOOKS.get(num)
        if not book:
            continue
        path = download(f["name"], f["download_url"])
        for mt_ch, vs, lxx_ch, text in parse_book(path, book):
            ref = f"{book} {mt_ch}:{vs}"
            lxx_ref = f"{book} {lxx_ch}:{vs}"
            rows.append((ref, lxx_ref, book, mt_ch, vs, text,
                         "Swete LXX 1930", LICENSE, SOURCE, "corpus"))

    con = duckdb.connect()
    con.execute("""CREATE TABLE lxx(
        ref VARCHAR, lxx_ref VARCHAR, book VARCHAR, chapter INT, verse INT,
        text_lxx VARCHAR, version VARCHAR, license VARCHAR, source VARCHAR, layer VARCHAR)""")
    con.executemany("INSERT INTO lxx VALUES (" + ",".join("?" * 10) + ")", rows)
    con.execute(f"CREATE VIEW v AS SELECT * FROM '{VERSES}'")
    con.execute("ALTER TABLE lxx ADD COLUMN resolved BOOLEAN")
    con.execute("UPDATE lxx SET resolved = (ref IN (SELECT ref FROM v WHERE canon='Tanakh'))")
    con.execute(f"COPY lxx TO '{OUT}' (FORMAT parquet)")

    tot, res, books = con.sql(
        "SELECT count(*), sum(CASE WHEN resolved THEN 1 ELSE 0 END), "
        "count(DISTINCT book) FROM lxx").fetchone()
    pct = 100 * res / tot if tot else 0
    print(f"\n→ data/lxx.parquet: {tot:,} LXX verses across {books} books "
          f"({pct:.1f}% align to a Tanakh MT verse)")
    ur = con.sql("""SELECT book, count(*) n FROM lxx WHERE NOT resolved
                    GROUP BY book ORDER BY n DESC LIMIT 6""").fetchall()
    if ur:
        print("  LXX-native (versification diverges from MT — expected, not faked):")
        for b, n in ur:
            print(f"    {b:<14} {n:>5,} verses")


if __name__ == "__main__":
    main()
