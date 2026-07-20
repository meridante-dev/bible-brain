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
| **Corpus apparatus** | **114,595 cross-references** (OpenBible.info, CC-BY) — 84k NT↔NT, 30k NT→Tanakh, resolved against the unified corpus |
| **Messianic layer** | **24 authored threads → 63 edges** (prophecy→fulfillment, type→antitype, canon-spanning themes), each graded + source-grounded → [`index/messianic-threads.md`](index/messianic-threads.md) |

## The two upstream substrates (read-only)

- **Torah Brain** (`~/torah-brain`) — the Tanakh (Sefaria). Supplies `tanakh.parquet` (Hebrew) + `tanakh_en.parquet` (JPS 1917).
- **New Testament corpus** (`~/new-testament`) — the NT, sourced independently. Supplies `nt.parquet` (WEB) + `nt_crossrefs.parquet` (OpenBible).

Bible-Brain never writes to either; it ingests their published parquet and records provenance.

## Build from the substrates

```bash
python3 pipeline/ingest_corpus.py       # both substrates -> data/verses.parquet (license-gated)
python3 pipeline/build_bridge.py        # NT crossrefs     -> data/bridge.parquet (canon-labelled)
python3 pipeline/build_interpretive.py  # interpretive/*.yaml -> data/interpretive.parquet (ref-validated)
python3 pipeline/build_index.py         # -> index/ (committed human-readable face)
```

## Query — one canon, two layers, never blurred

```bash
python3 pipeline/query_brain.py stats
python3 pipeline/query_brain.py verse "Isaiah 53:5"     # text + who cites it + Messianic threads
python3 pipeline/query_brain.py fulfills "Isaiah 7:14"   # NT fulfillments of a Tanakh promise
python3 pipeline/query_brain.py roots "Matthew 1:23"     # a NT verse's Tanakh roots
python3 pipeline/query_brain.py thread suffering-servant # one thread, its refs + text
python3 pipeline/query_brain.py threads                  # all authored threads
```

## Growing the Messianic layer

The layer is **human-authored and committed** at [`interpretive/prophecies.yaml`](interpretive/prophecies.yaml).
To add a thread, append an entry (id, category, tanakh, nt, confidence, basis, note) and rerun
`build_interpretive.py`. The compiler **validates every ref against the corpus** and rejects
dangling or mis-oriented edges — so the confession always points at real Scripture. Confidence
discipline is load-bearing: `high` means the NT itself cites the text; don't inflate it.

## Data model

- `verses.parquet` — `ref, book, canon, chapter, verse, text_en, text_orig, orig_lang, version, license, layer, ord`
- `bridge.parquet` — `from_ref, from_book, from_canon, to_ref, to_range, to_canon, votes, source, license, layer, resolved`
- `interpretive.parquet` — `id, category, title, from_ref, from_range, to_ref, to_range, confidence, basis, note, layer`

## Relationship to the substrates

Bible-Brain **bridges by its own confession** — exactly as both substrates' constitutions
foresaw. It never presents its Messianic reading as something the Tanakh substrate or Judaism
affirms; it reads the shared text and adds the community's confession, clearly marked as such.
The three projects are separate repositories and share no files.

## License posture (clean for reuse)

Everything admitted is **Public Domain or CC-BY**. The interpretive layer is authored here and
carries a graded basis on every edge. Attribute cross-references to www.openbible.info.
