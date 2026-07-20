#!/usr/bin/env python3
"""Bible-Brain query — one canon, two layers, never blurred.

The whole point: read Scripture as one story (Genesis → Revelation) while always
being able to tell the CORPUS (what Scripture says) from the INTERPRETIVE layer
(what the community confesses about it).

Usage:
  python3 pipeline/query_brain.py verse "Isaiah 53:5"      # text + corpus refs + interpretive threads
  python3 pipeline/query_brain.py interlinear "Isaiah 7:14" # the verse word-by-word in the original
  python3 pipeline/query_brain.py concordance H5921         # every occurrence of a Strong's # across the canon
  python3 pipeline/query_brain.py concordance parthenos     # ...or search by lemma / transliteration
  python3 pipeline/query_brain.py define H5959              # the lexicon entry for a Strong's # (BDB/Abbott-Smith)
  python3 pipeline/query_brain.py fulfills "Isaiah 7:14"    # NT fulfillments of a Tanakh verse (interpretive)
  python3 pipeline/query_brain.py roots "Matthew 1:23"      # a NT verse's Tanakh roots (interpretive)
  python3 pipeline/query_brain.py thread virgin-birth       # one Messianic thread, its refs + text
  python3 pipeline/query_brain.py threads                   # list all interpretive threads
  python3 pipeline/query_brain.py stats                     # corpus + bridge + interpretive counts
"""
import sys
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parent.parent
D = ROOT / "data"
con = duckdb.connect()
for name, f in [("v", "verses"), ("b", "bridge"), ("i", "interpretive"), ("w", "words"),
                ("l", "lexicon")]:
    p = D / f"{f}.parquet"
    if p.exists():
        con.execute(f"CREATE VIEW {f} AS SELECT * FROM '{p}'")


def _text(ref):
    r = con.sql(f"SELECT canon, text_en FROM verses WHERE ref = '{ref}'").fetchone()
    return r if r else (None, None)


def _chapter(ref):
    # "Isaiah 53:5" -> "Isaiah 53" (book+chapter), for span-aware matching.
    return ref.rsplit(":", 1)[0] if ":" in ref else ref


def verse(ref):
    canon, text = _text(ref)
    if text is None:
        print(f"'{ref}' is not in the corpus."); return
    print(f"\n=== {ref}  [{canon} · corpus] ===\n{text}\n")
    # Bridge edges run NT→X. So show BOTH what this verse cites (outgoing, if NT) and
    # who cites this verse (incoming) — for a Tanakh verse, incoming is the whole point.
    print("--- corpus cross-references (OpenBible, CC-BY) ---")
    con.sql(f"""
        SELECT '→ cites' AS dir, to_ref AS other, to_canon AS side, votes
        FROM bridge WHERE from_ref = '{ref}' AND resolved
        UNION ALL
        SELECT '← cited by', from_ref, from_canon, votes
        FROM bridge WHERE to_ref = '{ref}' AND resolved
        ORDER BY votes DESC LIMIT 12""").show(max_width=120)
    # Interpretive: exact endpoint OR a thread whose anchor sits in this chapter
    # (so Isaiah 53:5 surfaces the Servant thread anchored at Isaiah 53:1).
    ch = _chapter(ref)
    print("--- interpretive threads touching this passage (the Messianic reading) ---")
    con.sql(f"""SELECT DISTINCT id, category, confidence, title FROM interpretive
                WHERE from_ref = '{ref}' OR to_ref = '{ref}'
                   OR regexp_replace(from_ref, ':\\d+$', '') = '{ch}'
                   OR regexp_replace(to_ref,   ':\\d+$', '') = '{ch}'
                ORDER BY confidence""").show(max_width=120)


def fulfills(tanakh_ref):
    print(f"\n=== NT fulfillments of {tanakh_ref}  [interpretive] ===")
    con.sql(f"""SELECT to_ref AS nt_ref, category, confidence, title, basis
                FROM interpretive WHERE from_ref = '{tanakh_ref}'
                ORDER BY confidence""").show(max_width=160)


def roots(nt_ref):
    print(f"\n=== Tanakh roots of {nt_ref}  [interpretive] ===")
    con.sql(f"""SELECT from_ref AS tanakh_ref, category, confidence, title, basis
                FROM interpretive WHERE to_ref = '{nt_ref}'
                ORDER BY confidence""").show(max_width=160)


def thread(tid):
    head = con.sql(f"""SELECT DISTINCT category, confidence, title, basis, note
                       FROM interpretive WHERE id = '{tid}'""").fetchone()
    if not head:
        print(f"No thread '{tid}'. Try: query_brain.py threads"); return
    cat, conf, title, basis, note = head
    print(f"\n=== {title}  [{cat} · {conf}] ===\n{note}\nbasis: {basis}\n")
    pairs = con.sql(f"""SELECT DISTINCT from_ref, to_ref FROM interpretive
                        WHERE id = '{tid}'""").fetchall()
    seen = set()
    for a, b in pairs:
        for ref, side in ((a, "Tanakh"), (b, "NT")):
            if ref in seen:
                continue
            seen.add(ref)
            _, t = _text(ref)
            t = (t or "")[:150]
            print(f"  [{side:<6}] {ref:<18} {t}")


def threads():
    print("\n=== interpretive threads (the authored Messianic layer) ===")
    con.sql("""SELECT id, category, confidence, title FROM interpretive
               GROUP BY id, category, confidence, title
               ORDER BY category, confidence, id""").show(max_width=160)


def stats():
    print("\n=== Bible-Brain ===")
    con.sql("""SELECT canon, count(*) verses FROM verses
               GROUP BY canon ORDER BY min(ord)""").show()
    if _has("bridge"):
        con.sql("""SELECT 'bridge (corpus xref)' AS layer, to_canon,
                          count(*) n, sum(CASE WHEN resolved THEN 1 ELSE 0 END) resolved
                   FROM bridge GROUP BY to_canon ORDER BY to_canon""").show()
    if _has("interpretive"):
        con.sql("""SELECT 'interpretive' AS layer, category,
                          count(DISTINCT id) threads, count(*) edges
                   FROM interpretive GROUP BY category ORDER BY category""").show()


def interlinear(ref):
    if not _has("words"):
        print("No word layer — run pipeline/fetch_words.py first."); return
    canon, text = _text(ref)
    if text is None:
        print(f"'{ref}' is not in the corpus."); return
    print(f"\n=== {ref}  [{canon}] word-by-word (STEPBible, CC BY 4.0) ===\n{text}\n")
    con.sql(f"""SELECT word_pos AS n, surface, translit, gloss, strongs, morph
                FROM words WHERE ref = '{ref}'
                ORDER BY word_pos""").show(max_width=140, max_rows=60)


def concordance(term):
    if not _has("words"):
        print("No word layer — run pipeline/fetch_words.py first."); return
    # Match a Strong's number (G/H####) exactly, else search lemma/transliteration.
    t = term.strip()
    if t[:1] in "GgHh" and t[1:].rstrip("abAB").isdigit():
        where = f"upper(strongs) = upper('{t}')"
        label = f"Strong's {t.upper()}"
    else:
        s = t.replace("'", "''")
        where = (f"lower(lemma) = lower('{s}') OR lower(translit) LIKE lower('%{s}%') "
                 f"OR lower(gloss) LIKE lower('%{s}%')")
        label = f"'{t}'"
    # Identify which Strong's number(s) the term picks out (ranked by how often it matches)...
    cands = [r[0] for r in con.sql(f"""SELECT strongs, count(*) c FROM words
                WHERE ({where}) AND strongs <> ''
                GROUP BY strongs ORDER BY c DESC LIMIT 5""").fetchall()]
    print(f"\n=== concordance for {label} — across the whole canon ===")
    if not cands:
        print("  no occurrences found."); return
    # ...then report AUTHORITATIVE stats for each Strong's number (over all its occurrences).
    for strongs in cands:
        lemma, gloss, hits, verses, canons = con.sql(f"""
            SELECT any_value(lemma), any_value(gloss), count(*),
                   count(DISTINCT ref), count(DISTINCT canon)
            FROM words WHERE strongs = '{strongs}'""").fetchone()
        span = "spans both Tanakh & NT" if canons == 2 else "one testament"
        print(f"\n  {strongs}  {lemma or ''}  “{gloss or ''}”  —  "
              f"{hits:,} occurrences in {verses:,} verses ({span})")
        if _has("lexicon"):
            d = con.sql(f"SELECT definition FROM lexicon WHERE strongs = '{strongs}'").fetchone()
            if d and d[0]:
                print(f"    def: {d[0][:200]}")
        con.sql(f"""SELECT canon, count(*) hits, count(DISTINCT ref) verses,
                           min(ref) first_ref, max(ref) last_ref
                    FROM words WHERE strongs = '{strongs}'
                    GROUP BY canon ORDER BY canon""").show(max_width=120)


def define(term):
    if not _has("lexicon"):
        print("No lexicon layer — run pipeline/fetch_lexicon.py first."); return
    t = term.strip()
    if t[:1] in "GgHh" and t[1:].rstrip("abAB").isdigit():
        where = f"upper(strongs) = upper('{t}')"
    else:
        s = t.replace("'", "''")
        where = f"lower(translit) = lower('{s}') OR lower(gloss) = lower('{s}')"
    rows = con.sql(f"""SELECT strongs, lang, lemma, translit, gloss, definition
                       FROM lexicon WHERE {where} LIMIT 5""").fetchall()
    if not rows:
        print(f"  no lexicon entry for '{term}'."); return
    for strongs, lang, lemma, translit, gloss, definition in rows:
        print(f"\n=== {strongs}  {lemma}  ({translit}, {lang})  —  “{gloss}” ===")
        print(f"{definition}")
        if _has("words"):
            n = con.sql(f"SELECT count(*), count(DISTINCT ref) FROM words "
                        f"WHERE strongs = '{strongs}'").fetchone()
            print(f"\noccurs {n[0]:,}× in {n[1]:,} verses  "
                  f"(→ query_brain.py concordance {strongs})")


def _has(name):
    return con.sql(f"SELECT count(*) FROM information_schema.tables "
                   f"WHERE table_name = '{name}'").fetchone()[0] > 0


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__); sys.exit(0)
    cmd, args = sys.argv[1], sys.argv[2:]
    fns = {"verse": verse, "interlinear": interlinear, "concordance": concordance,
           "define": define, "fulfills": fulfills, "roots": roots,
           "thread": thread, "threads": lambda: threads(),
           "stats": lambda: stats()}
    if cmd not in fns:
        print(__doc__); sys.exit(1)
    fns[cmd](*args) if args else fns[cmd]()
