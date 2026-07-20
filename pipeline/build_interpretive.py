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
_RANGE = re.compile(r"^(.+ \d+):(\d+)-(\d+)$")


def anchor_of(ref):
    m = _RANGE.match(ref.strip())
    return f"{m.group(1)}:{m.group(2)}" if m else ref.strip()


def expand_refs(ref):
    """A ref or single-chapter range -> the list of verse refs it covers."""
    m = _RANGE.match(ref.strip())
    if not m:
        return [ref.strip()]
    book_ch, v1, v2 = m.group(1), int(m.group(2)), int(m.group(3))
    return [f"{book_ch}:{v}" for v in range(v1, v2 + 1)]


_BASE = re.compile(r"^([GH]\d+)")


def base(strongs):
    """STEPBible disambiguates Strong's (H2233H, G4151G); key_words name the base."""
    m = _BASE.match(strongs)
    return m.group(1) if m else strongs

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "interpretive"
VERSES = ROOT / "data" / "verses.parquet"
WORDS = ROOT / "data" / "words.parquet"
LEXICON = ROOT / "data" / "lexicon.parquet"
OUT = ROOT / "data" / "interpretive.parquet"
OUT_WORDS = ROOT / "data" / "interp_words.parquet"

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

    # Word layer for grounding key_words (ref -> set of Strong's). Optional but, when
    # present, key_words are VALIDATED: a pivotal word must actually occur in the thread's
    # own verses, so the word-grounding is a checked assertion, not a decoration.
    word_index = {}
    if WORDS.exists():
        for ref, strongs in con.sql(
                f"SELECT ref, strongs FROM '{WORDS}' WHERE strongs <> ''").fetchall():
            word_index.setdefault(ref, set()).add(base(strongs))

    entries = load_entries()
    rows, errors, kw_rows = [], [], []
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

        # Word-grounding: validate each pivotal Strong's occurs in the thread's own verses.
        kw = e.get("key_words") or {}
        tk_verses = {v for label, _ in tk for v in expand_refs(label)}
        nt_verses = {v for label, _ in nt for v in expand_refs(label)}
        for lang, side_verses, expect in [("Hebrew", tk_verses, "H"),
                                          ("Greek", nt_verses, "G")]:
            for strongs in (kw.get(lang.lower()) or []):
                if not strongs.startswith(expect):
                    errors.append(f"{eid}: {lang} key_word {strongs!r} should start '{expect}'")
                    continue
                if word_index:
                    hit = any(strongs in word_index.get(v, ()) for v in side_verses)
                    if not hit:
                        errors.append(
                            f"{eid}: key_word {strongs} not found in any {lang} verse "
                            f"of the thread ({sorted(side_verses)[:3]}…)")
                        continue
                kw_rows.append((eid, lang, strongs))

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

    # The word-grounding table: pivotal words per thread, enriched with lexicon lemma+gloss.
    # Lexicon is dStrong-keyed too, so match on the base number (first entry wins).
    lex_base = {}
    if LEXICON.exists():
        for s, lemma, translit, gloss in con.sql(
                f"SELECT strongs, lemma, translit, gloss FROM '{LEXICON}'").fetchall():
            lex_base.setdefault(base(s), (lemma, translit, gloss))
    iw_rows = [(eid, lang, strongs, *lex_base.get(strongs, (None, None, None)))
               for (eid, lang, strongs) in kw_rows]
    con.execute("""CREATE TABLE interp_words(
        id VARCHAR, lang VARCHAR, strongs VARCHAR,
        lemma VARCHAR, translit VARCHAR, gloss VARCHAR)""")
    if iw_rows:
        con.executemany("INSERT INTO interp_words VALUES (?,?,?,?,?,?)", iw_rows)
    con.execute(f"COPY interp_words TO '{OUT_WORDS}' (FORMAT parquet)")

    print(f"→ data/interpretive.parquet: {len(rows):,} edges from "
          f"{len(entries)} authored threads")
    print(f"→ data/interp_words.parquet: {len(kw_rows)} word-grounded pivots "
          f"across {len({r[0] for r in kw_rows})} threads")
    for cat, n, thr in con.sql("""
            SELECT category, count(*) edges, count(DISTINCT id) threads
            FROM interp GROUP BY category ORDER BY category""").fetchall():
        print(f"    {cat:<18} {thr:>2} threads → {n:>3} edges")
    for conf, n in con.sql("SELECT confidence, count(*) FROM interp "
                           "GROUP BY confidence ORDER BY confidence").fetchall():
        print(f"    confidence {conf:<8} {n:>3} edges")


if __name__ == "__main__":
    main()
