#!/usr/bin/env python3
"""The word/token layer — every verse broken into its Hebrew/Greek words.

Source: STEPBible-Data (Tyndale House Cambridge), TAHOT (Hebrew OT) + TAGNT (Greek NT),
CC BY 4.0. See SOURCES.md. We DOWNLOAD at build time into data/cache/ (gitignored) and
never re-host the data — honoring both the CC-BY licence and STEPBible's request to point
reusers to github.com/STEPBible. Attribution is carried on every row.

Each word row is keyed to a verse `ref` in the SAME vocabulary as data/verses.parquet, so
the token layer sits directly beneath the corpus. Carries: original surface, transliteration,
gloss, disambiguated Strong's number, morphology, lemma. This is what lets the brain link
any verse to its original language, and any Strong's number to every place it occurs across
the whole canon (see `query_brain.py concordance`).

Writes data/words.parquet:
  ref, canon, book, chapter, verse, word_pos, word_type, surface, translit, gloss,
  strongs, strongs_full, morph, lemma, version, license, source, layer(='corpus')

Run:  python3 pipeline/fetch_words.py       (after ingest_corpus.py)
"""
import re
import sys
import urllib.parse
import urllib.request
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / "data" / "cache"
CACHE.mkdir(parents=True, exist_ok=True)
VERSES = ROOT / "data" / "verses.parquet"
OUT = ROOT / "data" / "words.parquet"

RAW = ("https://raw.githubusercontent.com/STEPBible/STEPBible-Data/master/"
       "Translators%20Amalgamated%20OT+NT/")
FILES = {
    "TAHOT": ["TAHOT Gen-Deu - Translators Amalgamated Hebrew OT - STEPBible.org CC BY.txt",
              "TAHOT Jos-Est - Translators Amalgamated Hebrew OT - STEPBible.org CC BY.txt",
              "TAHOT Job-Sng - Translators Amalgamated Hebrew OT - STEPBible.org CC BY.txt",
              "TAHOT Isa-Mal - Translators Amalgamated Hebrew OT - STEPBible.org CC BY.txt"],
    "TAGNT": ["TAGNT Mat-Jhn - Translators Amalgamated Greek NT - STEPBible.org CC-BY.txt",
              "TAGNT Act-Rev - Translators Amalgamated Greek NT - STEPBible.org CC-BY.txt"],
}
LICENSE = "CC BY 4.0"
SOURCE = "STEPBible.org (Tyndale House Cambridge)"

# STEPBible book codes -> corpus book names. OT names match Sefaria (~/torah-brain);
# NT names match the WEB corpus (~/new-testament). Unmapped codes are reported, not dropped.
BOOKS = {
    # Torah
    "Gen": "Genesis", "Exo": "Exodus", "Lev": "Leviticus", "Num": "Numbers",
    "Deu": "Deuteronomy",
    # Nevi'im / Ketuvim
    "Jos": "Joshua", "Jdg": "Judges", "Rut": "Ruth",
    "1Sa": "I Samuel", "2Sa": "II Samuel", "1Ki": "I Kings", "2Ki": "II Kings",
    "1Ch": "I Chronicles", "2Ch": "II Chronicles", "Ezr": "Ezra", "Neh": "Nehemiah",
    "Est": "Esther", "Job": "Job", "Psa": "Psalms", "Pro": "Proverbs",
    "Ecc": "Ecclesiastes", "Sng": "Song of Songs", "Isa": "Isaiah", "Jer": "Jeremiah",
    "Lam": "Lamentations", "Ezk": "Ezekiel", "Dan": "Daniel", "Hos": "Hosea",
    "Jol": "Joel", "Amo": "Amos", "Oba": "Obadiah", "Jon": "Jonah", "Mic": "Micah",
    "Nam": "Nahum", "Hab": "Habakkuk", "Zep": "Zephaniah", "Hag": "Haggai",
    "Zec": "Zechariah", "Mal": "Malachi",
    # NT
    "Mat": "Matthew", "Mrk": "Mark", "Luk": "Luke", "Jhn": "John", "Act": "Acts",
    "Rom": "Romans", "1Co": "1 Corinthians", "2Co": "2 Corinthians", "Gal": "Galatians",
    "Eph": "Ephesians", "Php": "Philippians", "Col": "Colossians",
    "1Th": "1 Thessalonians", "2Th": "2 Thessalonians", "1Ti": "1 Timothy",
    "2Ti": "2 Timothy", "Tit": "Titus", "Phm": "Philemon", "Heb": "Hebrews",
    "Jas": "James", "1Pe": "1 Peter", "2Pe": "2 Peter", "1Jn": "1 John",
    "2Jn": "2 John", "3Jn": "3 John", "Jud": "Jude", "Rev": "Revelation",
}

# A per-word data row starts with e.g. "Gen.1.6#01=L" or "Mat.1.3#08=NKO".
ROW = re.compile(r"^([A-Za-z0-9]{2,4})\.(\d+)\.(\d+)#(\d+)=(\S+)\t(.*)$")
GREEK_SURFACE = re.compile(r"^(\S+)\s*\(([^)]*)\)")   # "Ζάρα (Zara)" -> word, translit
BRACED_H = re.compile(r"\{(H\d+[A-Za-z]?)\}")          # main Hebrew Strong's in {}
H_NUM = re.compile(r"H\d+[A-Za-z]?")
G_HEAD = re.compile(r"^(G\d+[A-Za-z]?)=?(.*)$")


def download(fname):
    dest = CACHE / fname
    if dest.exists() and dest.stat().st_size > 0:
        return dest
    url = RAW + urllib.parse.quote(fname)
    print(f"  ↓ {fname[:40]}… ", end="", flush=True)
    urllib.request.urlretrieve(url, dest)
    print(f"{dest.stat().st_size // 1024:,} KB")
    return dest


def parse_greek(fields):
    # TAGNT row fields: [0]=Greek(translit) [1]=gloss [2]=Strong=morph [3]=lemma=gloss ...
    surface, translit = fields[0].strip(), ""
    m = GREEK_SURFACE.match(fields[0].strip())
    if m:
        surface, translit = m.group(1), m.group(2)
    gloss = fields[1].strip() if len(fields) > 1 else ""
    strongs, morph = "", ""
    if len(fields) > 2:
        gm = G_HEAD.match(fields[2].strip())
        if gm:
            strongs, morph = gm.group(1), gm.group(2)
    lemma = ""
    if len(fields) > 3 and "=" in fields[3]:
        lemma = fields[3].split("=", 1)[0].strip()
    return surface, translit, gloss, strongs, strongs, morph, lemma


def parse_hebrew(fields):
    # TAHOT row fields: [0]=Hebrew [1]=translit [2]=gloss [3]=dStrongs [4]=morph ...
    surface = fields[0].strip()
    translit = fields[1].strip() if len(fields) > 1 else ""
    gloss = fields[2].strip() if len(fields) > 2 else ""
    dstrong = fields[3].strip() if len(fields) > 3 else ""
    morph = fields[4].strip() if len(fields) > 4 else ""
    full = dstrong.replace("{", "").replace("}", "").split("\\")[0]  # drop trailing \H9016 etc
    m = BRACED_H.search(dstrong)
    if m:
        main = m.group(1)
    else:
        nums = H_NUM.findall(full)
        main = nums[-1] if nums else ""
    return surface, translit, gloss, main, full, morph, ""


def main():
    if not VERSES.exists():
        raise SystemExit("Missing data/verses.parquet — run ingest_corpus.py first.")

    rows, unmapped = [], {}
    for kind, files in FILES.items():
        canon = "Tanakh" if kind == "TAHOT" else "NT"
        version = f"STEP {kind}"
        parse = parse_hebrew if kind == "TAHOT" else parse_greek
        for fname in files:
            path = download(fname)
            with path.open(encoding="utf-8") as fh:
                for line in fh:
                    m = ROW.match(line.rstrip("\n"))
                    if not m:
                        continue
                    code, ch, vs, pos, wtype, rest = m.groups()
                    book = BOOKS.get(code)
                    if not book:
                        unmapped[code] = unmapped.get(code, 0) + 1
                        continue
                    fields = rest.split("\t")
                    surface, translit, gloss, strongs, sfull, morph, lemma = parse(fields)
                    ref = f"{book} {int(ch)}:{int(vs)}"
                    rows.append((ref, canon, book, int(ch), int(vs), int(pos), wtype,
                                 surface, translit, gloss, strongs, sfull, morph, lemma,
                                 version, LICENSE, SOURCE, "corpus"))

    con = duckdb.connect()
    con.execute("""CREATE TABLE words(
        ref VARCHAR, canon VARCHAR, book VARCHAR, chapter INT, verse INT,
        word_pos INT, word_type VARCHAR, surface VARCHAR, translit VARCHAR, gloss VARCHAR,
        strongs VARCHAR, strongs_full VARCHAR, morph VARCHAR, lemma VARCHAR,
        version VARCHAR, license VARCHAR, source VARCHAR, layer VARCHAR)""")
    con.executemany("INSERT INTO words VALUES (" + ",".join("?" * 18) + ")", rows)
    con.execute(f"CREATE VIEW v AS SELECT * FROM '{VERSES}'")
    con.execute("ALTER TABLE words ADD COLUMN resolved BOOLEAN")
    con.execute("UPDATE words SET resolved = (ref IN (SELECT ref FROM v))")
    con.execute(f"COPY words TO '{OUT}' (FORMAT parquet)")

    tot = con.sql("SELECT count(*) FROM words").fetchone()[0]
    print(f"\n→ data/words.parquet: {tot:,} words")
    for canon, n, res, verses, strongs in con.sql("""
            SELECT canon, count(*) n,
                   sum(CASE WHEN resolved THEN 1 ELSE 0 END) res,
                   count(DISTINCT ref) verses, count(DISTINCT strongs) strongs
            FROM words GROUP BY canon ORDER BY canon""").fetchall():
        pct = 100 * res / n if n else 0
        print(f"    {canon:<7} {n:>7,} words · {verses:>6,} verses · "
              f"{strongs:>5,} distinct Strong's · {pct:.1f}% resolve to a corpus verse")
    if unmapped:
        print("  ⚠ unmapped book codes (add to BOOKS):",
              ", ".join(f"{k}×{v}" for k, v in sorted(unmapped.items())))
    ur = con.sql("""SELECT split_part(ref,' ',1) b, count(*) n FROM words
                    WHERE NOT resolved GROUP BY 1 ORDER BY n DESC LIMIT 8""").fetchall()
    if ur:
        print("  unresolved refs by book (versification drift — review):",
              ", ".join(f"{b}×{n}" for b, n in ur))


if __name__ == "__main__":
    main()
