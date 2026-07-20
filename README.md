# Bible-Brain — the Messianic metabrain

The whole of Scripture — the **Tanakh** and the **New Testament** — read as **one canon
telling one story**, for a Messianic and Christian community. Bible-Brain is the *downstream
bridge* that the two neutral corpus substrates were built to enable: it stands on both, reads
them read-only, and adds the interpretive layer they deliberately leave out.

> It is unapologetically Messianic in orientation, and scrupulously honest about it: you can
> always tell **what Scripture says** (the corpus) from **what the community confesses about
> it** (the interpretive layer). See [CONSTITUTION.md](CONSTITUTION.md).

## What's here

| | |
|---|---|
| **One canon** | **31,156 verses** — Tanakh (23,206, Hebrew + JPS 1917, PD) + NT (7,950, WEB, PD), one continuous `ord` from Genesis 1:1 to Revelation 22:21 |
| **Original languages** | **425,454 words** (STEPBible TAHOT+TAGNT, CC BY 4.0) — every verse word-by-word with Strong's + morphology + gloss; 16,494 distinct Strong's numbers → a canon-wide concordance |
| **Lexicon** | **22,717 Strong's entries** (STEPBible TBESH+TBESG = BDB + Abbott-Smith, CC BY 4.0) — every word gets a definition; covers 99.8% of the words used |
| **Septuagint** | **21,863 LXX verses** (Swete 1930, CC BY-SA) — the Greek OT the NT quotes; aligned to the Masoretic refs (96.5%) so you can set MT · LXX · NT side by side |
| **Corpus apparatus** | **114,595 cross-references** (OpenBible.info, CC-BY) — 84k NT↔NT, 30k NT→Tanakh, resolved against the unified corpus |
| **Messianic layer** | **24 authored threads → 63 edges** (prophecy→fulfillment, type→antitype, canon-spanning themes), each graded + source-grounded → [`index/messianic-threads.md`](index/messianic-threads.md) |
| **Word-grounded threads** | **12 pivotal words across 7 threads** — the Hebrew & Greek terms that carry each connection (*almah→parthenos*, *seh→amnos*, *nachash→ophis*…), each **validated** to occur in the thread's own verses, with the LXX bridge shown automatically |

## The two upstream substrates (read-only)

- **Torah Brain** (`~/torah-brain`) — the Tanakh (Sefaria). Supplies `tanakh.parquet` (Hebrew) + `tanakh_en.parquet` (JPS 1917).
- **New Testament corpus** (`~/new-testament`) — the NT, sourced independently. Supplies `nt.parquet` (WEB) + `nt_crossrefs.parquet` (OpenBible).

Bible-Brain never writes to either; it ingests their published parquet and records provenance.

## Build from the substrates

```bash
python3 pipeline/ingest_corpus.py       # both substrates -> data/verses.parquet (license-gated)
python3 pipeline/fetch_words.py         # STEPBible TAHOT+TAGNT -> data/words.parquet (word layer, CC-BY)
python3 pipeline/fetch_lexicon.py       # STEPBible TBESH+TBESG -> data/lexicon.parquet (definitions, CC-BY)
python3 pipeline/fetch_lxx.py           # Swete LXX -> data/lxx.parquet (Greek OT, MT-aligned, CC-BY-SA)
python3 pipeline/build_bridge.py        # NT crossrefs     -> data/bridge.parquet (canon-labelled)
python3 pipeline/build_interpretive.py  # interpretive/*.yaml -> data/interpretive.parquet (ref-validated)
python3 pipeline/build_index.py         # -> index/ (committed human-readable face)
```

Sources + their verified licenses are recorded in [SOURCES.md](SOURCES.md) (the gate: PD / CC0 / CC-BY / CC-BY-SA only).

## Visualize

```bash
python3 pipeline/build_viz.py           # -> viz/index.html (self-contained, no external assets)
```

A single-file explorer of the whole canon on one axis: the corpus cross-reference web drawn
as a faint underlay and the **Messianic threads as bold arcs on top** — the two layers made
visual. Each thread opens to its three witnesses (MT Hebrew · LXX Greek · NT) and the pivotal
words, with the LXX hinge highlighted. Open `viz/index.html` in any browser, or serve it:
`python3 -m http.server -d viz 4455`.

## Query — one canon, two layers, never blurred

```bash
python3 pipeline/query_brain.py stats
python3 pipeline/query_brain.py verse "Isaiah 53:5"       # text + who cites it + Messianic threads
python3 pipeline/query_brain.py interlinear "Isaiah 7:14" # the verse word-by-word in the original
python3 pipeline/query_brain.py concordance H5959         # every occurrence of a Strong's # (Gen→Rev)
python3 pipeline/query_brain.py concordance parthenos     # ...or by lemma / transliteration
python3 pipeline/query_brain.py define H5959              # the lexicon entry (BDB / Abbott-Smith)
python3 pipeline/query_brain.py quotation "Isaiah 7:14"   # MT Hebrew · LXX Greek · the NT verses that cite it
python3 pipeline/query_brain.py fulfills "Isaiah 7:14"    # NT fulfillments of a Tanakh promise
python3 pipeline/query_brain.py roots "Matthew 1:23"      # a NT verse's Tanakh roots
python3 pipeline/query_brain.py thread suffering-servant  # one thread, its refs + text
python3 pipeline/query_brain.py threads                   # all authored threads
```

## Growing the Messianic layer

The layer is **human-authored and committed** at [`interpretive/prophecies.yaml`](interpretive/prophecies.yaml).
To add a thread, append an entry (id, category, tanakh, nt, confidence, basis, note) and rerun
`build_interpretive.py`. The compiler **validates every ref against the corpus** and rejects
dangling or mis-oriented edges — so the confession always points at real Scripture. Confidence
discipline is load-bearing: `high` means the NT itself cites the text; don't inflate it.

Optionally add `key_words: { hebrew: [H####], greek: [G####] }` — the pivotal terms that carry
the connection. The compiler **validates that each word actually occurs in the thread's own
verses** (word-grounding is a checked assertion, not decoration) and joins the lexicon for
glosses. `query_brain.py thread <id>` then shows them and auto-detects when the LXX of the
Tanakh anchor already reads the NT's Greek word.

## Data model

- `verses.parquet` — `ref, book, canon, chapter, verse, text_en, text_orig, orig_lang, version, license, layer, ord`
- `words.parquet` — `ref, canon, book, chapter, verse, word_pos, word_type, surface, translit, gloss, strongs, strongs_full, morph, lemma, version, license, source, layer, resolved`
- `lexicon.parquet` — `strongs, estrong, lang, lemma, translit, morph_class, gloss, definition, source, license, layer` (join `words.strongs = lexicon.strongs`)
- `lxx.parquet` — `ref (MT-aligned), lxx_ref (native), book, chapter, verse, text_lxx, version, license, source, layer, resolved` (join `lxx.ref = verses.ref` for Tanakh)
- `bridge.parquet` — `from_ref, from_book, from_canon, to_ref, to_range, to_canon, votes, source, license, layer, resolved`
- `interpretive.parquet` — `id, category, title, from_ref, from_range, to_ref, to_range, confidence, basis, note, layer`
- `interp_words.parquet` — `id, lang, strongs, lemma, translit, gloss` (the pivotal words per thread; join `interp_words.id = interpretive.id`)

## Relationship to the substrates

Bible-Brain **bridges by its own confession** — exactly as both substrates' constitutions
foresaw. It never presents its Messianic reading as something the Tanakh substrate or Judaism
affirms; it reads the shared text and adds the community's confession, clearly marked as such.
The three projects are separate repositories and share no files.

## License posture (clean for reuse)

Everything admitted is **Public Domain or CC-BY**. The interpretive layer is authored here and
carries a graded basis on every edge. Attribute cross-references to www.openbible.info.
