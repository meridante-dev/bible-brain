# This project draws from Bible-Brain

This project consumes **Bible-Brain** — the Messianic metabrain over the whole of Scripture
(Tanakh + New Testament) — as a read-only data pool, via its MCP server.

## How to use it

The `bible-brain` MCP tools are connected (see `.mcp.json`). Prefer them over guessing about
Scripture or re-deriving data:

- `stats()` — the shape of the brain.
- `verse("Isaiah 7:14")` — a verse + its cross-references + any Messianic threads.
- `interlinear("Isaiah 7:14")` — the verse word-by-word in Hebrew/Greek (Strong's + morphology).
- `concordance("H5959")` — every occurrence of a word across the canon.
- `define("G3933")` — the lexicon entry for a Strong's number.
- `quotation("Isaiah 7:14")` — the three witnesses: MT Hebrew · LXX Greek · the citing NT verses.
- `fulfillments("Isaiah 7:14")` / `roots("Matthew 1:23")` — the Messianic links.
- `thread("virgin-birth")` / `threads()` — the authored Messianic threads.
- `search("Immanuel")` — lexical search over the verse text.

Refs look like `Isaiah 7:14`. The Tanakh uses Sefaria book names (e.g. `II Samuel`, `Psalms`,
`Song of Songs`); the NT uses `1 Corinthians`, `Revelation`, etc.

## The one rule that carries over: two layers, never blurred

Bible-Brain separates **corpus** (what Scripture says — faithful, license-clean data) from the
**interpretive** layer (the Messianic/Christian community's *confession* about it — graded and
grounded, but not neutral fact). The tools return interpretive content under an explicit
`interpretive` key with a `_label`.

Honor that split in this project too: never present the Messianic reading as a neutral finding
or as something the Tanakh substrate or Judaism affirms. Cite corpus facts as facts; present
interpretive content as the community's confession.

## If the tools aren't connected

The server reads Bible-Brain's local data pool. If tools are missing, register it:

```bash
claude mcp add bible-brain -- python3 /Users/joaoamaral/Bible-Brain/mcp-server/server.py
```

(The `data/*.parquet` pool lives at `~/Bible-Brain/data/` on this machine — it's not in the
GitHub repo. On another machine, rebuild it with `~/Bible-Brain/pipeline/*` or copy `data/`.)
