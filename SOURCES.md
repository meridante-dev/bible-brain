# Sources — verified provenance & license record

Every dataset admitted to Bible-Brain must be **Public Domain / CC0 / CC-BY / CC-BY-SA**
(unknown or NonCommercial/NoDerivs/"used with permission" = **refuse**), per
[CONSTITUTION.md](CONSTITUTION.md). Licenses below were verified by fetching the actual repo /
license page on **2026-07-20** (URL cited per source). This file is the standing record; a
source is only wired into `pipeline/` after it appears here as **ADMIT**.

## In use now

| Layer | Source | License | Where |
|---|---|---|---|
| Tanakh text (He + JPS 1917 En) | Sefaria, via `~/torah-brain` | Public Domain | upstream substrate |
| NT text (WEB) | getBible, via `~/new-testament` | Public Domain | upstream substrate |
| Cross-references | OpenBible.info | CC-BY | via `~/new-testament` |
| **Word layer (Strong's + morph + gloss)** | **STEPBible TAHOT + TAGNT** | **CC BY 4.0** | `pipeline/fetch_words.py` |

### STEPBible-Data — the word/token layer ⭐

- **License: CC BY 4.0.** Verified at <https://github.com/STEPBible/STEPBible-Data> (baked into
  every filename: `…STEPBible.org CC BY.txt`). Attribution required: **"STEP Bible" →
  www.STEPBible.org**. Their README also *requests* (not a license restriction) that reusers
  point others to github.com/STEPBible rather than re-host the data.
- **Compliance stance:** we honor both the license and the request — `fetch_words.py`
  **downloads at build time into `data/cache/` (gitignored), never commits or redistributes
  the data**, and records the attribution in every row (`source`, `license`) and in the index.
- **Files** (`Translators Amalgamated OT+NT/`): TAHOT `Gen-Deu`, `Jos-Est`, `Job-Sng`,
  `Isa-Mal` (Hebrew) + TAGNT `Mat-Jhn`, `Act-Rev` (Greek).
- **Format:** UTF-8 TSV, long header then one row per word, keyed `Book.Ch.Vs#pos=type`.
  Carries disambiguated Strong's, morphology (Greek Robinson-based; Hebrew OSHB-style with
  prefixes/suffixes split), transliteration, and an English gloss (from the Berean, PD).
  OT uses Hebrew versification → lines up natively with the Sefaria Tanakh.

## Verified & admitted — queued for later phases

| Source | License | Purpose | Note |
|---|---|---|---|
| OSHB / morphhb | CC BY 4.0 (+ PD text) | alt Hebrew morphology | OSIS XML |
| Nestle 1904 (`/morph`) | CC0 (+ PD text) | Greek NT source-text witness | 7-field TSV; **confirm per-subdir license** |
| RP Byzantine + Scrivener TR 1894 | Public Domain | KJV/Byzantine-tradition Greek witness | `github.com/byztxt` |
| SBLGNT | **CC BY 4.0** (relicensed from its old EULA) | critical Greek text | attribution string per sblgnt.com |
| MACULA Hebrew + Greek (Clear-Bible) | CC BY 4.0 | syntax trees, semantic domains, alignment | **exclude MARBLE word-sense fields** ("used w/ permission") |
| unfoldingWord UHB + UGNT | CC BY-SA 4.0 | translation↔original alignment | **share-alike is viral** — derivatives must stay BY-SA |
| Rahlfs LXX **text** (clean PD transcription) | Public Domain | the Septuagint (inter-testament hinge) | text only |
| TSK cross-references (OpenBible.info) | Public Domain | ~340k extra cross-refs | use original TSK, **not** TSKe |
| Strong's (openscriptures / morphgnt) | PD text + CC0/CC-BY markup | lexicon join by Strong's # | |
| BDB Hebrew (openscriptures/HebrewLexicon) | PD text + CC BY 4.0 markup | Hebrew lexicon | |
| Thayer's Greek | Public Domain | Greek lexicon | no single canonical repo |
| Abbott-Smith Greek | Public Domain | Greek lexicon | TEI XML |
| Dodson Greek | **Public Domain** (not CC-BY) | Greek lexicon | CSV + TEI |

## Refused

| Source | Why |
|---|---|
| **CATSS / CCAT morphological LXX** (incl. the `eliranwong/LXX-Rahlfs-1935` repackaging) | **CC BY-NC-SA + signed user declaration** — NonCommercial + registration wall fails the gate. The Rahlfs *text* is fine (PD); the *morphology* is the licensing problem, so a tagged LXX must be sourced clean or tagged in-house. |
| Rahlfs-**Hanhart** 2006 revision | Copyright Deutsche Bibelgesellschaft. |
| Enhanced/Expanded TSK (TSKe, ~800k) | Separately copyrighted derivative. |
| KJV (as noted in `~/new-testament`) | Source declared GPL; not admitted. |
