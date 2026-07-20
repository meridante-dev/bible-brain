# Constitution — Bible-Brain

Bible-Brain is the **Messianic metabrain**: the whole of Scripture — the Tanakh (Hebrew
scriptures) **and** the New Testament (Brit Chadashah) — read as **one canon telling one
story**, for a Messianic and Christian community. It is the *downstream bridge project* that
the two neutral corpus substrates were built to enable but deliberately refused to be.

It stands on two upstream substrates and consumes them **read-only**:

- **Torah Brain** (`~/torah-brain`) — the Tanakh, sourced from Sefaria. Neutral corpus data.
- **New Testament corpus** (`~/new-testament`) — the NT, sourced independently. Neutral
  corpus data; its own CONSTITUTION names *this* project as the intended downstream bridge.

Neither substrate takes a theological position. **Bible-Brain does.** That interpretive stance
— the reason this project exists — is what the substrates leave out on purpose. This
constitution governs how that stance is held: honestly, traceably, and without ever corrupting
the corpus beneath it.

## The two layers (the central rule)

Everything in Bible-Brain is exactly one of two things, and the two are **never blurred**:

1. **The corpus layer — what Scripture says.** Verse text and the public cross-reference
   apparatus, ingested verbatim from the two substrates. Faithful, neutral, traceable. Bible-
   Brain **does not edit, fork-as-authoritative, or write back to** the substrates; it reads
   them and records provenance. Corpus rows carry `layer = "corpus"`.

2. **The interpretive layer — what the community confesses about what Scripture says.** The
   Messianic reading: prophecy → fulfillment, type → antitype, thematic threads, Yeshua-as-
   Messiah. This layer is the project's whole point, and it is held **openly as
   interpretation, not as corpus**. Every interpretive datum carries `layer = "interpretive"`,
   a `category`, a `confidence`, and a `basis` (the classical/public-domain source or the
   NT's own citation that grounds the claim). It is stored in its own namespace and never
   merged into the corpus cross-reference tables.

A reader (or a downstream app) can always tell the text of Scripture from the community's
confession about it. That separation is the honesty of the project.

## Firewall (non-negotiable)

1. **Corpus is upstream and read-only.** The substrates are the single source of truth for
   text and apparatus. Bible-Brain ingests them through `pipeline/` and never hand-edits
   corpus data, never writes into `~/torah-brain` or `~/new-testament`.
2. **License discipline carries over verbatim.** Only Public Domain / CC0 / CC-BY / CC-BY-SA
   material is admitted; unknown = refuse. Every row records its `version` + `license`. Today:
   Tanakh Hebrew (Ta'amei Hamikra, **PD**) + English (JPS 1917, **PD**) from Torah Brain; NT
   (WEB, **PD**) + cross-references (OpenBible.info, **CC-BY**, attributed) from the NT corpus.
3. **Interpretation is labelled, sourced, and graded — never asserted as fact.** No
   interpretive edge exists without a `basis` and a `confidence`. The brain distinguishes "the
   NT itself cites this" (high) from "a classical typological reading holds this" (graded
   lower) from an editorial thread. It presents the Messianic reading as the community's
   confession, grounded in the text — not as a neutral finding and not as proof.
4. **Faithful to the community, honest to the reader.** Bible-Brain is unapologetically
   Messianic/Christian in orientation — it reads the two testaments as one. It does **not**
   misrepresent the Jewish canon or the Torah Brain: it never presents its Messianic reading
   as something the Tanakh substrate or Judaism affirms. It bridges *by its own confession*,
   exactly as both substrates' constitutions foresaw.

## What lives here

| Path | What | Layer |
|---|---|---|
| `data/verses.parquet` | the unified canon: one row per verse, Tanakh + NT, with `canon`, text, version, license, `ord` (gitignored — bulk, regenerable) | corpus |
| `data/bridge.parquet` | the cross-reference apparatus unified across the canon (NT↔NT, NT→Tanakh), from OpenBible | corpus |
| `data/interpretive.parquet` | compiled Messianic layer: prophecy/type/thread edges with category, confidence, basis (gitignored) | interpretive |
| `interpretive/*.yaml` | **the human-authored, source-cited Messianic layer** — the committed heart of the project | interpretive |
| `pipeline/` | ingest + build + query scripts (the only way data enters) | — |
| `index/` | committed, human-readable index + book pages | — |

## Provenance

Created 2026-07-20 at the owner's direction as the Messianic metabrain over the Tanakh and the
New Testament. Its own repository (`~/Bible-Brain`), a sibling to `~/torah-brain` and
`~/new-testament`; it shares no files with either and only reads their published data.
