#!/usr/bin/env python3
"""Bible-Brain MCP server — the metabrain as infrastructure.

Read-only tools over the whole canon: the unified verse corpus (Tanakh + NT), the
original-language word layer (Strong's + morphology), the lexicon, the Septuagint, the
cross-reference apparatus, and the authored Messianic threads. Any MCP client (Claude
Code, Claude Desktop, a downstream project) plugs in and queries the pool as tools.

Discipline inherited from CONSTITUTION.md — the two layers are NEVER blurred:
  - CORPUS content (verse text, cross-references, words, lexicon, LXX) is faithful,
    license-clean data, returned with version + license attribution;
  - INTERPRETIVE content (the Messianic reading: prophecy→fulfillment, type, threads,
    word-grounding) is returned only under an explicit `interpretive` key carrying the
    label below — the community's confession, graded and grounded, never neutral fact.

Register:  claude mcp add bible-brain -- python3 /Users/joaoamaral/Bible-Brain/mcp-server/server.py
Selftest:  python3 mcp-server/server.py --selftest
"""
import re
import sys
from pathlib import Path

import duckdb
from mcp.server.fastmcp import FastMCP

ROOT = Path(__file__).resolve().parent.parent
D = ROOT / "data"

INTERPRETIVE_LABEL = (
    "The Messianic/Christian community's confession about the text — graded and grounded "
    "in Scripture, but interpretation, not neutral corpus data. Never present it as "
    "something the Tanakh substrate or Judaism affirms."
)

con = duckdb.connect()
LAYERS = {}
for name in ("verses", "words", "lexicon", "lxx", "bridge", "interpretive", "interp_words"):
    p = D / f"{name}.parquet"
    if p.exists():
        con.execute(f"CREATE VIEW {name} AS SELECT * FROM '{p}'")
        LAYERS[name] = True

mcp = FastMCP(
    "bible-brain",
    instructions=(
        "The Messianic metabrain: the whole of Scripture (Tanakh + New Testament) as one "
        "canon — original-language words with Strong's + morphology, a lexicon, the "
        "Septuagint, the cross-reference apparatus, and authored Messianic threads. "
        "CORPUS fields are faithful license-clean data (cite version + license). "
        "INTERPRETIVE fields are returned under an explicit `interpretive` key and are the "
        "community's graded confession — never present them as neutral fact or as something "
        "Judaism affirms. Refs look like 'Isaiah 7:14' (Tanakh uses Sefaria names, e.g. "
        "'II Samuel', 'Psalms', 'Song of Songs')."
    ),
)


def _rows(sql, params=None):
    cur = con.execute(sql, params or [])
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, r)) for r in cur.fetchall()]


def _one(sql, params=None):
    r = _rows(sql, params)
    return r[0] if r else None


def _chapter(ref):
    return ref.rsplit(":", 1)[0] if ":" in ref else ref


@mcp.tool()
def verse(ref: str) -> dict:
    """A verse's text plus its corpus cross-references (both directions) and the
    Messianic threads touching it. Corpus vs. interpretive are returned separately."""
    v = _one("SELECT ref, canon, chapter, verse, text_en, text_orig, orig_lang, "
             "version, license FROM verses WHERE ref = ?", [ref])
    if not v:
        return {"error": f"'{ref}' is not in the corpus."}
    cites = _rows("SELECT to_ref, to_canon, votes FROM bridge WHERE from_ref = ? AND resolved "
                  "ORDER BY votes DESC LIMIT 12", [ref]) if "bridge" in LAYERS else []
    cited_by = _rows("SELECT from_ref, from_canon, votes FROM bridge WHERE to_ref = ? AND "
                     "resolved ORDER BY votes DESC LIMIT 12", [ref]) if "bridge" in LAYERS else []
    ch = _chapter(ref)
    threads = _rows("SELECT DISTINCT id, category, confidence, title FROM interpretive WHERE "
                    "from_ref = ? OR to_ref = ? OR regexp_replace(from_ref,':\\d+$','') = ? OR "
                    "regexp_replace(to_ref,':\\d+$','') = ? ORDER BY confidence",
                    [ref, ref, ch, ch]) if "interpretive" in LAYERS else []
    return {
        "corpus": {**v, "cites": cites, "cited_by": cited_by},
        "interpretive": {"_label": INTERPRETIVE_LABEL, "threads": threads},
    }


@mcp.tool()
def interlinear(ref: str) -> dict:
    """A verse word-by-word in the original: surface, transliteration, gloss, Strong's,
    morphology (STEPBible, CC BY 4.0)."""
    if "words" not in LAYERS:
        return {"error": "word layer not built"}
    v = _one("SELECT canon, text_en FROM verses WHERE ref = ?", [ref])
    if not v:
        return {"error": f"'{ref}' is not in the corpus."}
    words = _rows("SELECT word_pos, surface, translit, gloss, strongs, morph FROM words "
                  "WHERE ref = ? ORDER BY word_pos", [ref])
    return {"ref": ref, "canon": v["canon"], "text": v["text_en"], "words": words,
            "source": "STEPBible TAHOT/TAGNT (CC BY 4.0)"}


@mcp.tool()
def concordance(term: str, limit: int = 40) -> dict:
    """Every occurrence of a Strong's number (e.g. 'H5959') or a lemma/transliteration
    across the whole canon, with a verse list."""
    if "words" not in LAYERS:
        return {"error": "word layer not built"}
    t = term.strip()
    if t[:1] in "GgHh" and t[1:].rstrip("abAB").isdigit():
        where, params = "upper(strongs) = upper(?)", [t]
    else:
        where = "lower(lemma) = lower(?) OR lower(translit) LIKE lower(?) OR lower(gloss) LIKE lower(?)"
        params = [t, f"%{t}%", f"%{t}%"]
    cand = _rows(f"SELECT strongs, count(*) c FROM words WHERE ({where}) AND strongs <> '' "
                 f"GROUP BY strongs ORDER BY c DESC LIMIT 3", params)
    out = []
    for c in cand:
        s = c["strongs"]
        head = _one("SELECT any_value(lemma) lemma, any_value(gloss) gloss, count(*) hits, "
                    "count(DISTINCT ref) verses, count(DISTINCT canon) canons FROM words "
                    "WHERE strongs = ?", [s])
        refs = _rows("SELECT w.ref, w.canon FROM words w JOIN verses v ON v.ref = w.ref "
                     "WHERE w.strongs = ? GROUP BY w.ref, w.canon ORDER BY min(v.ord) LIMIT ?",
                     [s, limit])
        out.append({"strongs": s, **head, "spans_both_testaments": head["canons"] == 2,
                    "occurrences": refs})
    return {"term": term, "results": out}


@mcp.tool()
def define(term: str) -> dict:
    """The lexicon entry for a Strong's number (or a lemma/transliteration): lemma,
    transliteration, gloss, and definition (BDB / Abbott-Smith, PD)."""
    if "lexicon" not in LAYERS:
        return {"error": "lexicon layer not built"}
    t = term.strip()
    if t[:1] in "GgHh" and t[1:].rstrip("abAB").isdigit():
        where, params = "upper(strongs) = upper(?)", [t]
    else:
        where = "lower(translit) = lower(?) OR lower(gloss) = lower(?)"
        params = [t, t]
    rows = _rows(f"SELECT strongs, lang, lemma, translit, gloss, definition FROM lexicon "
                 f"WHERE {where} LIMIT 5", params)
    for r in rows:
        if "words" in LAYERS:
            n = _one("SELECT count(*) hits, count(DISTINCT ref) verses FROM words WHERE "
                     "strongs = ?", [r["strongs"]])
            r["occurrences"] = n
    return {"term": term, "entries": rows, "source": "STEPBible TBESH/TBESG (CC BY 4.0)"}


@mcp.tool()
def quotation(ref: str) -> dict:
    """The inter-testament hinge: one Tanakh verse in its three witnesses — MT Hebrew,
    LXX Greek, and the NT verses that cite it — plus any Messianic thread."""
    v = _one("SELECT canon, text_en, text_orig FROM verses WHERE ref = ?", [ref])
    if not v:
        return {"error": f"'{ref}' is not in the corpus."}
    if v["canon"] != "Tanakh":
        return {"error": f"'{ref}' is {v['canon']}; quotation view expects a Tanakh verse. "
                         f"Use fulfillments()/roots() instead."}
    lx = _one("SELECT text_lxx, lxx_ref FROM lxx WHERE ref = ?", [ref]) if "lxx" in LAYERS else None
    citers = _rows("SELECT from_ref, votes FROM bridge WHERE to_ref = ? AND resolved "
                   "ORDER BY votes DESC LIMIT 10", [ref]) if "bridge" in LAYERS else []
    for c in citers:
        t = _one("SELECT text_en FROM verses WHERE ref = ?", [c["from_ref"]])
        c["text"] = t["text_en"] if t else ""
    threads = _rows("SELECT DISTINCT id, confidence, title FROM interpretive WHERE from_ref = ?",
                    [ref]) if "interpretive" in LAYERS else []
    return {
        "corpus": {
            "ref": ref,
            "MT_hebrew": v["text_orig"], "MT_english": v["text_en"],
            "LXX_greek": lx["text_lxx"] if lx else None,
            "LXX_ref": lx["lxx_ref"] if lx and lx["lxx_ref"] != ref else None,
            "NT_citations": citers,
        },
        "interpretive": {"_label": INTERPRETIVE_LABEL, "threads": threads},
    }


@mcp.tool()
def fulfillments(tanakh_ref: str) -> dict:
    """[interpretive] The NT fulfillments the Messianic layer draws from a Tanakh verse."""
    if "interpretive" not in LAYERS:
        return {"error": "interpretive layer not built"}
    rows = _rows("SELECT to_ref AS nt_ref, category, confidence, title, basis FROM interpretive "
                 "WHERE from_ref = ? ORDER BY confidence", [tanakh_ref])
    return {"_label": INTERPRETIVE_LABEL, "tanakh_ref": tanakh_ref, "fulfillments": rows}


@mcp.tool()
def roots(nt_ref: str) -> dict:
    """[interpretive] The Tanakh roots the Messianic layer draws behind a NT verse."""
    if "interpretive" not in LAYERS:
        return {"error": "interpretive layer not built"}
    rows = _rows("SELECT from_ref AS tanakh_ref, category, confidence, title, basis FROM "
                 "interpretive WHERE to_ref = ? ORDER BY confidence", [nt_ref])
    return {"_label": INTERPRETIVE_LABEL, "nt_ref": nt_ref, "roots": rows}


@mcp.tool()
def thread(id: str) -> dict:
    """[interpretive] One Messianic thread in full: its verses, the pivotal Hebrew/Greek
    words that carry it, and whether the LXX already reads the NT's Greek word."""
    if "interpretive" not in LAYERS:
        return {"error": "interpretive layer not built"}
    head = _one("SELECT any_value(category) category, any_value(confidence) confidence, "
                "any_value(title) title, any_value(basis) basis, any_value(note) note FROM "
                "interpretive WHERE id = ?", [id])
    if not head:
        return {"error": f"no thread '{id}'"}
    pairs = _rows("SELECT DISTINCT from_range, to_range FROM interpretive WHERE id = ?", [id])
    words = _rows("SELECT lang, strongs, lemma, translit, gloss FROM interp_words WHERE id = ? "
                  "ORDER BY lang DESC", [id]) if "interp_words" in LAYERS else []
    hinge = None
    if "lxx" in LAYERS:
        anchors = {p["from_range"].split(":")[0] + ":" + p["from_range"].split(":")[1].split("-")[0]
                   for p in pairs}
        for w in words:
            if w["lang"] == "Greek" and w["lemma"]:
                for a in anchors:
                    lx = _one("SELECT text_lxx FROM lxx WHERE ref = ?", [a])
                    if lx and w["lemma"][:4] in lx["text_lxx"]:
                        hinge = {"lxx_ref": a, "lemma": w["lemma"]}
                        break
    return {"_label": INTERPRETIVE_LABEL, "id": id, **head,
            "links": pairs, "key_words": words, "lxx_hinge": hinge}


@mcp.tool()
def threads() -> dict:
    """[interpretive] List all authored Messianic threads (id, category, confidence, title)."""
    if "interpretive" not in LAYERS:
        return {"error": "interpretive layer not built"}
    rows = _rows("SELECT id, category, confidence, title FROM interpretive GROUP BY id, "
                 "category, confidence, title ORDER BY category, confidence, id")
    return {"_label": INTERPRETIVE_LABEL, "threads": rows}


@mcp.tool()
def search(phrase: str, limit: int = 20) -> dict:
    """Lexical search over the English verse text of the whole canon."""
    p = phrase.replace("'", "''")
    rows = _rows("SELECT ref, canon, text_en FROM verses WHERE lower(text_en) LIKE lower(?) "
                 "ORDER BY ord LIMIT ?", [f"%{p}%", limit])
    return {"phrase": phrase, "hits": len(rows), "verses": rows}


@mcp.tool()
def stats() -> dict:
    """The shape of the brain: verse counts per canon, and each layer's size."""
    out = {"canons": _rows("SELECT canon, count(*) verses FROM verses GROUP BY canon "
                           "ORDER BY min(ord)")}
    if "words" in LAYERS:
        out["words"] = _one("SELECT count(*) total, count(DISTINCT strongs) distinct_strongs "
                            "FROM words")
    if "lexicon" in LAYERS:
        out["lexicon_entries"] = _one("SELECT count(*) n FROM lexicon")["n"]
    if "lxx" in LAYERS:
        out["lxx_verses"] = _one("SELECT count(*) n FROM lxx")["n"]
    if "bridge" in LAYERS:
        out["cross_references"] = _one("SELECT count(*) n FROM bridge")["n"]
    if "interpretive" in LAYERS:
        out["interpretive"] = {"_label": INTERPRETIVE_LABEL,
            "threads": _one("SELECT count(DISTINCT id) n FROM interpretive")["n"]}
    return out


def _selftest():
    checks = [
        ("stats", stats()),
        ("verse", verse("Isaiah 7:14")),
        ("interlinear", interlinear("Isaiah 7:14")),
        ("concordance", concordance("H5959")),
        ("define", define("G3933")),
        ("quotation", quotation("Isaiah 7:14")),
        ("thread", thread("virgin-birth")),
        ("search", search("Immanuel", 5)),
    ]
    ok = True
    for name, res in checks:
        bad = isinstance(res, dict) and res.get("error")
        print(f"[{'FAIL' if bad else ' ok '}] {name}: {str(res)[:130].replace(chr(10),' ')}")
        ok = ok and not bad
    # the hinge must fire: the LXX of Isaiah 7:14 reads parthenos
    q = quotation("Isaiah 7:14")
    hinge_ok = q["corpus"]["LXX_greek"] and "παρθέν" in q["corpus"]["LXX_greek"]
    print(f"[{' ok ' if hinge_ok else 'FAIL'}] LXX hinge: Isaiah 7:14 LXX reads parthenos")
    th = thread("virgin-birth")
    kw_ok = any(w["strongs"] == "H5959" for w in th["key_words"]) and th["lxx_hinge"]
    print(f"[{' ok ' if kw_ok else 'FAIL'}] virgin-birth grounded on H5959 + LXX hinge")
    sys.exit(0 if ok and hinge_ok and kw_ok else 1)


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        _selftest()
    else:
        mcp.run()
