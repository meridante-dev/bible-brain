#!/usr/bin/env python3
"""Query Bible-Brain with ZERO dependencies — Python standard library only.

This is the offline / hand-anywhere query tool. It reads data/bible-brain.sqlite using
the built-in `sqlite3` module — no pip, no duckdb, no internet. (For the parquet/duckdb
version with identical commands, see pipeline/query_brain.py.)

  python3 query.py stats
  python3 query.py verse "Isaiah 53:5"
  python3 query.py quotation "Isaiah 7:14"      # MT Hebrew · LXX Greek · citing NT verses
  python3 query.py interlinear "Isaiah 7:14"     # the verse word-by-word in the original
  python3 query.py concordance H5959             # every occurrence across the canon
  python3 query.py define G3933                  # the lexicon entry
  python3 query.py thread virgin-birth           # a Messianic thread, its words + LXX hinge
  python3 query.py threads
  python3 query.py search Immanuel
"""
import sqlite3
import sys
from pathlib import Path

DB = Path(__file__).resolve().parent / "data" / "bible-brain.sqlite"
if not DB.exists():
    sys.exit("Missing data/bible-brain.sqlite — run pipeline/export_sqlite.py, or use a "
             "bundle that includes it.")
con = sqlite3.connect(DB)
con.row_factory = sqlite3.Row


def q(sql, p=()):
    return con.execute(sql, p).fetchall()


def _chapter(ref):
    return ref.rsplit(":", 1)[0] if ":" in ref else ref


def stats(*_):
    print("\n=== Bible-Brain ===")
    for r in q("SELECT canon, count(*) n FROM verses GROUP BY canon ORDER BY min(ord)"):
        print(f"  {r['canon']:<7} {r['n']:>6,} verses")
    w = q("SELECT count(*) t, count(DISTINCT strongs) s FROM words")[0]
    print(f"  words   {w['t']:>6,} ({w['s']:,} distinct Strong's)")
    for t, label in [("lexicon", "lexicon entries"), ("lxx", "LXX verses"),
                     ("bridge", "cross-references")]:
        print(f"  {label:<16} {q(f'SELECT count(*) n FROM {t}')[0]['n']:>7,}")
    print(f"  Messianic threads {q('SELECT count(DISTINCT id) n FROM interpretive')[0]['n']:>4}")


def verse(ref):
    v = q("SELECT canon, text_en, text_orig FROM verses WHERE ref=?", (ref,))
    if not v:
        print(f"'{ref}' is not in the corpus."); return
    v = v[0]
    print(f"\n=== {ref}  [{v['canon']} · corpus] ===\n{v['text_en']}")
    print("\n--- corpus cross-references ---")
    for r in q("SELECT '→ '||to_ref other, votes v FROM bridge WHERE from_ref=? AND resolved=1 "
               "UNION ALL SELECT '← '||from_ref, votes FROM bridge WHERE to_ref=? AND resolved=1 "
               "ORDER BY v DESC LIMIT 10", (ref, ref)):
        print(f"  {r['other']:<22} (votes {r['v']})")
    ch = _chapter(ref)
    seen, out = set(), []
    for r in q("SELECT DISTINCT id, confidence, title, from_ref, to_ref FROM interpretive"):
        if (r['from_ref'] == ref or r['to_ref'] == ref
                or _chapter(r['from_ref']) == ch or _chapter(r['to_ref']) == ch):
            if r['id'] not in seen:
                seen.add(r['id']); out.append(r)
    if out:
        print("\n--- Messianic threads touching this passage [interpretive] ---")
        for r in out:
            print(f"  • {r['title']}  ({r['confidence']}) — {r['id']}")


def quotation(ref):
    v = q("SELECT canon, text_en, text_orig FROM verses WHERE ref=?", (ref,))
    if not v:
        print(f"'{ref}' is not in the corpus."); return
    v = v[0]
    if v['canon'] != 'Tanakh':
        print(f"'{ref}' is {v['canon']}; quotation view expects a Tanakh verse."); return
    print(f"\n=== {ref} — the three witnesses ===\n")
    print(f"  MT  (Hebrew)   {v['text_orig'] or ''}")
    print(f"      (English)  {v['text_en']}")
    lx = q("SELECT text_lxx, lxx_ref FROM lxx WHERE ref=?", (ref,))
    if lx:
        note = f"  [LXX {lx[0]['lxx_ref']}]" if lx[0]['lxx_ref'] != ref else ""
        print(f"  LXX (Greek)    {lx[0]['text_lxx']}{note}")
    print("\n  NT verses that cite this:")
    for r in q("SELECT from_ref, votes FROM bridge WHERE to_ref=? AND resolved=1 "
               "ORDER BY votes DESC LIMIT 8", (ref,)):
        t = q("SELECT text_en FROM verses WHERE ref=?", (r['from_ref'],))
        print(f"    → {r['from_ref']:<18} {(t[0]['text_en'] if t else '')[:88]}")
    th = q("SELECT DISTINCT id, confidence, title FROM interpretive WHERE from_ref=?", (ref,))
    if th:
        print("\n  Messianic thread(s) [interpretive]:")
        for r in th:
            print(f"    • {r['title']}  ({r['confidence']}) — {r['id']}")


def interlinear(ref):
    v = q("SELECT canon, text_en FROM verses WHERE ref=?", (ref,))
    if not v:
        print(f"'{ref}' is not in the corpus."); return
    print(f"\n=== {ref}  [{v[0]['canon']}] word-by-word ===\n{v[0]['text_en']}\n")
    print(f"  {'#':>3}  {'surface':<16} {'translit':<16} {'gloss':<22} {'Strong':<8} morph")
    for r in q("SELECT word_pos, surface, translit, gloss, strongs, morph FROM words "
               "WHERE ref=? ORDER BY word_pos", (ref,)):
        print(f"  {r['word_pos']:>3}  {r['surface']:<16} {r['translit']:<16} "
              f"{(r['gloss'] or '')[:22]:<22} {r['strongs']:<8} {r['morph']}")


def concordance(term):
    t = term.strip()
    if t[:1] in "GgHh" and t[1:].rstrip("abAB").isdigit():
        where, p = "upper(strongs)=upper(?)", (t,)
    else:
        where = "lower(lemma)=lower(?) OR lower(translit) LIKE lower(?) OR lower(gloss) LIKE lower(?)"
        p = (t, f"%{t}%", f"%{t}%")
    cands = q(f"SELECT strongs, count(*) c FROM words WHERE ({where}) AND strongs<>'' "
              f"GROUP BY strongs ORDER BY c DESC LIMIT 3", p)
    print(f"\n=== concordance for '{term}' — across the whole canon ===")
    if not cands:
        print("  no occurrences."); return
    for c in cands:
        s = c['strongs']
        h = q("SELECT max(lemma) l, max(gloss) g, count(*) hits, count(DISTINCT ref) verses, "
              "count(DISTINCT canon) cn FROM words WHERE strongs=?", (s,))[0]
        span = "spans both Tanakh & NT" if h['cn'] == 2 else "one testament"
        print(f"\n  {s}  {h['l'] or ''}  “{h['g'] or ''}”  —  {h['hits']:,} occurrences "
              f"in {h['verses']:,} verses ({span})")
        for r in q("SELECT canon, count(*) hits, count(DISTINCT ref) verses, min(ref) a, "
                   "max(ref) b FROM words WHERE strongs=? GROUP BY canon", (s,)):
            print(f"     {r['canon']:<7} {r['hits']:>4} hits · {r['verses']:>4} verses "
                  f"· {r['a']} … {r['b']}")


def define(term):
    t = term.strip()
    if t[:1] in "GgHh" and t[1:].rstrip("abAB").isdigit():
        where, p = "upper(strongs)=upper(?)", (t,)
    else:
        where, p = "lower(translit)=lower(?) OR lower(gloss)=lower(?)", (t, t)
    rows = q(f"SELECT strongs, lang, lemma, translit, gloss, definition FROM lexicon "
             f"WHERE {where} LIMIT 5", p)
    if not rows:
        print(f"  no lexicon entry for '{term}'."); return
    for r in rows:
        print(f"\n=== {r['strongs']}  {r['lemma']}  ({r['translit']}, {r['lang']}) — "
              f"“{r['gloss']}” ===\n{r['definition']}")
        n = q("SELECT count(*) h, count(DISTINCT ref) v FROM words WHERE strongs=?", (r['strongs'],))[0]
        print(f"\noccurs {n['h']:,}× in {n['v']:,} verses")


def thread(tid):
    h = q("SELECT DISTINCT category, confidence, title, basis, note FROM interpretive WHERE id=?",
          (tid,))
    if not h:
        print(f"No thread '{tid}'. Try: query.py threads"); return
    h = h[0]
    print(f"\n=== {h['title']}  [{h['category']} · {h['confidence']}] ===\n{h['note']}\n"
          f"basis: {h['basis']}\n")
    seen = set()
    for r in q("SELECT DISTINCT from_ref, to_ref FROM interpretive WHERE id=?", (tid,)):
        for ref, side in ((r['from_ref'], "Tanakh"), (r['to_ref'], "NT")):
            if ref in seen:
                continue
            seen.add(ref)
            t = q("SELECT text_en FROM verses WHERE ref=?", (ref,))
            print(f"  [{side:<6}] {ref:<18} {(t[0]['text_en'] if t else '')[:120]}")
    kw = q("SELECT lang, strongs, lemma, translit, gloss FROM interp_words WHERE id=? "
           "ORDER BY lang DESC", (tid,))
    if kw:
        print("\n  the words that carry the connection [word-grounded]:")
        for r in kw:
            print(f"    [{r['lang']:<6}] {r['strongs']:<7} {r['lemma'] or ''} "
                  f"({r['translit'] or ''}) — “{r['gloss'] or ''}”")
        for r in kw:
            if r['lang'] == 'Greek' and r['lemma']:
                for a in q("SELECT DISTINCT from_ref FROM interpretive WHERE id=?", (tid,)):
                    lx = q("SELECT text_lxx FROM lxx WHERE ref=?", (a['from_ref'],))
                    if lx and r['lemma'][:4] in lx[0]['text_lxx']:
                        print(f"    ↳ the LXX of {a['from_ref']} already reads {r['lemma']} — "
                              f"the very word the NT quotes.")
                        break


def threads(*_):
    print("\n=== interpretive threads (the Messianic layer) ===")
    for r in q("SELECT id, category, confidence, title FROM interpretive "
               "GROUP BY id ORDER BY category, confidence, id"):
        print(f"  {r['confidence']:<7} {r['category']:<18} {r['id']:<28} {r['title']}")


def search(*words):
    phrase = " ".join(words)
    rows = q("SELECT ref, canon, text_en FROM verses WHERE lower(text_en) LIKE lower(?) "
             "ORDER BY ord LIMIT 20", (f"%{phrase}%",))
    print(f"\n=== '{phrase}' — {len(rows)} hits ===")
    for r in rows:
        print(f"  [{r['canon']:<6}] {r['ref']:<18} {r['text_en'][:100]}")


FNS = {"stats": stats, "verse": verse, "quotation": quotation, "interlinear": interlinear,
       "concordance": concordance, "define": define, "thread": thread, "threads": threads,
       "search": search}

if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] not in FNS:
        print(__doc__); sys.exit(0)
    FNS[sys.argv[1]](*sys.argv[2:])
