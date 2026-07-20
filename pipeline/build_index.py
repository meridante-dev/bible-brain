#!/usr/bin/env python3
"""Build the committed, human-readable index of the Messianic layer.

The parquet data is gitignored (bulk, regenerable); this markdown is the committed
face of the brain — the authored interpretive threads, grouped and graded, each with
its Tanakh anchor, its NT fulfillment, and its basis. Regenerate after editing the
YAML so the committed index tracks the layer.

Writes index/messianic-threads.md and index/MANIFEST.md.

Run:  python3 pipeline/build_index.py    (after build_interpretive.py)
"""
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parent.parent
D = ROOT / "data"
IDX = ROOT / "index"
IDX.mkdir(exist_ok=True)

CAT_TITLE = {
    "messianic-prophecy": "Messianic prophecy — the NT declares these fulfilled",
    "type": "Type & foreshadow — the shadow and its substance",
    "thematic-thread": "Thematic threads — one promise across the whole canon",
}
CONF_NOTE = {
    "high": "the NT itself cites this text",
    "medium": "clear NT allusion / near-universal reading",
    "graded": "a classical typological reading, offered as such",
}


def main():
    con = duckdb.connect()
    con.execute(f"CREATE VIEW i AS SELECT * FROM '{D / 'interpretive.parquet'}'")
    con.execute(f"CREATE VIEW v AS SELECT * FROM '{D / 'verses.parquet'}'")
    iw = D / "interp_words.parquet"
    has_iw = iw.exists()
    if has_iw:
        con.execute(f"CREATE VIEW iw AS SELECT * FROM '{iw}'")

    threads = con.sql("""
        SELECT id, category, confidence, title,
               any_value(basis) basis, any_value(note) note
        FROM i GROUP BY id, category, confidence, title
        ORDER BY category, confidence, id""").fetchall()

    lines = ["# The Messianic threads — Bible-Brain\n",
             "The authored interpretive layer: the Tanakh and the New Testament read as one",
             "story. Each thread is the community's confession, graded by how the New Testament",
             "itself grounds it, and always distinct from the corpus text beneath it (see",
             "[CONSTITUTION.md](../CONSTITUTION.md)). Refs link Tanakh anchor → NT fulfillment.\n"]

    by_cat = {}
    for t in threads:
        by_cat.setdefault(t[1], []).append(t)

    for cat in ("messianic-prophecy", "type", "thematic-thread"):
        if cat not in by_cat:
            continue
        lines.append(f"\n## {CAT_TITLE[cat]}\n")
        for tid, _, conf, title, basis, note in by_cat[cat]:
            pairs = con.sql(f"""SELECT DISTINCT from_range, to_range FROM i
                                WHERE id = '{tid}'""").fetchall()
            tk = sorted({p[0] for p in pairs})
            nt = sorted({p[1] for p in pairs})
            lines.append(f"### {title}")
            lines.append(f"*{note}*  \n**Confidence — {conf}** ({CONF_NOTE[conf]})  ")
            lines.append(f"**Tanakh:** {', '.join(tk)} → **NT:** {', '.join(nt)}  ")
            lines.append(f"**Basis:** {basis}  ")
            if has_iw:
                words = con.sql(f"""SELECT lang, strongs, lemma, translit, gloss
                                    FROM iw WHERE id = '{tid}' ORDER BY lang DESC""").fetchall()
                if words:
                    parts = [f"{lemma} ({translit}, {strongs}, “{gloss}”)"
                             for lang, strongs, lemma, translit, gloss in words]
                    lines.append(f"**Key words:** {' · '.join(parts)}")
            lines.append("")

    (IDX / "messianic-threads.md").write_text("\n".join(lines))

    # Manifest
    counts = con.sql("""SELECT category, count(DISTINCT id) threads, count(*) edges
                        FROM i GROUP BY category ORDER BY category""").fetchall()
    nv = con.sql("SELECT canon, count(*) FROM v GROUP BY canon ORDER BY min(ord)").fetchall()
    man = ["# Bible-Brain — manifest\n", "Compiled from the two upstream substrates.\n",
           "## Corpus (read-only from substrates)\n"]
    for canon, n in nv:
        man.append(f"- {canon}: **{n:,}** verses")
    man.append("\n## Interpretive layer (authored here)\n")
    for cat, thr, edg in counts:
        man.append(f"- {cat}: **{thr}** threads → {edg} edges")
    man.append("\n## License posture\n")
    man.append("- Tanakh: Ta'amei Hamikra (Hebrew) + JPS 1917 (English) — **Public Domain**")
    man.append("- New Testament: World English Bible — **Public Domain**")
    man.append("- Cross-references: OpenBible.info — **CC-BY** (attribution: www.openbible.info)")
    man.append("- Interpretive layer: authored in this repo; every edge carries a graded basis.")
    (IDX / "MANIFEST.md").write_text("\n".join(man))

    print(f"→ index/messianic-threads.md ({len(threads)} threads)")
    print("→ index/MANIFEST.md")


if __name__ == "__main__":
    main()
