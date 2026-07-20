# Bible-Brain MCP server

The metabrain **as infrastructure** — a read-only MCP server over the whole canon so any
downstream project (or any Claude instance) can draw from the pool as tools, instead of
knowing the parquet internals. This is how a new project consumes Bible-Brain.

## Register (this machine)

```bash
claude mcp add bible-brain -- python3 /Users/joaoamaral/Bible-Brain/mcp-server/server.py
```

Then in any Claude Code session the `bible-brain` tools are available. (Claude Desktop: add
the same command to its MCP config.)

## Let a specific project draw from it (project-scoped)

Drop a `.mcp.json` into the new project's root — Claude Code auto-connects when you work there:

```json
{
  "mcpServers": {
    "bible-brain": {
      "command": "python3",
      "args": ["/Users/joaoamaral/Bible-Brain/mcp-server/server.py"]
    }
  }
}
```

A ready copy, plus a `CLAUDE.md` snippet telling the downstream agent how to use the brain,
is in [`../downstream-starter/`](../downstream-starter/).

## Tools

| Tool | Returns | Layer |
|---|---|---|
| `stats()` | the shape of the brain (verses per canon, layer sizes) | — |
| `verse(ref)` | text + version/license, corpus cross-refs (both directions), threads touching it | corpus + interpretive |
| `interlinear(ref)` | the verse word-by-word: surface, translit, gloss, Strong's, morphology | corpus |
| `concordance(term)` | every occurrence of a Strong's # / lemma across the canon, with a verse list | corpus |
| `define(term)` | the lexicon entry for a Strong's # (BDB / Abbott-Smith) | corpus |
| `quotation(ref)` | the three witnesses of a Tanakh verse — **MT · LXX · NT** — + citing NT verses | corpus + interpretive |
| `fulfillments(ref)` / `roots(ref)` | the Messianic links a Tanakh/NT verse participates in | interpretive |
| `thread(id)` | one Messianic thread: verses, pivotal Hebrew/Greek words, LXX hinge | interpretive |
| `threads()` | list all authored threads | interpretive |
| `search(phrase)` | lexical search over the English verse text | corpus |

## Discipline (inherited from CONSTITUTION.md)

The two layers are **never blurred**, and the server enforces it in its return shape:

- **Corpus** fields are faithful, license-clean data, returned with `version` + `license`.
- **Interpretive** content is returned only under an explicit `interpretive` key carrying a
  `_label`: *the community's confession, graded and grounded — never neutral fact, and never
  presented as something the Tanakh substrate or Judaism affirms.*

A downstream agent that respects the key/label keeps the honesty of the whole project.

## Test

```bash
python3 mcp-server/server.py --selftest
```

The selftest exercises every tool and asserts two load-bearing facts: the LXX of Isaiah 7:14
reads παρθένος, and the `virgin-birth` thread is word-grounded on H5959 (*almah*) with the LXX
hinge firing.

## Note — the data pool is local

The `data/*.parquet` files are gitignored (bulk, regenerable), so they are **not** in the
GitHub repo. This server reads them from `../data/` on this machine. To run the server on a
different machine, rebuild the data there (`pipeline/*`) or copy `data/` across.
