# Deploy Bible-Brain to another computer (and run it offline)

Bible-Brain is small and self-contained: the **whole pool is ~23 MB of parquet**, and the
tools (`query_brain.py`, the visualization, the MCP server) read that pool from local files
with **no internet**. Only the `fetch_*` rebuild scripts need the network — so if you ship the
already-built data, the target machine never has to go online.

There are two ways to move it. Pick by whether the target has internet + the two upstream
substrates.

## Option A — Portable bundle (recommended; fully offline) ✅

Ship the code **and** the built data as one archive. Nothing is fetched on arrival.

**On this machine:**
```bash
bash pipeline/make_bundle.sh            # -> ~/bible-brain-bundle.zip  (~23 MB)
```
Transfer the zip however you like — USB drive, AirDrop, a cloud folder, `scp`.

**On the other computer:**
```bash
unzip bible-brain-bundle.zip -d bible-brain
cd bible-brain
bash install.sh                          # installs deps, runs an OFFLINE smoke test,
                                         # prints the exact commands with local paths
```
`install.sh` needs the internet only to `pip install duckdb` (once). If the target already has
`duckdb` (and `mcp` for the server), the whole thing is **100% offline** — including the
visualization: just open `viz/index.html` in any browser.

The only per-machine detail is the **absolute path** in the MCP registration — `install.sh`
prints it filled in for that machine, e.g.:
```bash
claude mcp add bible-brain -- python3 /Users/you/bible-brain/mcp-server/server.py
```

## Option B — Clone + rebuild (needs internet + the substrates)

Use this only if you want the target to regenerate the data itself.

```bash
git clone https://github.com/meridante-dev/bible-brain.git
cd bible-brain
pip install -r requirements.txt
# Requires ~/torah-brain and ~/new-testament present, and internet (STEPBible, LXX):
python3 pipeline/ingest_corpus.py && python3 pipeline/fetch_words.py && \
python3 pipeline/fetch_lexicon.py && python3 pipeline/fetch_lxx.py && \
python3 pipeline/build_bridge.py && python3 pipeline/build_interpretive.py && \
python3 pipeline/build_index.py && python3 pipeline/build_viz.py
```
The GitHub repo carries the **code, docs, and viz only** — the `data/` pool is gitignored, so a
clone alone is not the brain until you rebuild it (or drop a `data/` folder in).

## What "offline" covers

| Capability | Offline? |
|---|---|
| `query_brain.py` (verse, interlinear, concordance, quotation, thread…) | ✅ reads local parquet |
| The visualization (`viz/index.html`) | ✅ self-contained, no external assets — even `file://` |
| The MCP server (`mcp-server/server.py`) | ✅ reads local parquet |
| Rebuilding data (`fetch_*`, `ingest`, `build_*`) | ❌ needs internet + the substrates |

So: **build once (online), then run anywhere (offline).** A bundle is a frozen brain.

## Keeping it in sync

The bundle is a snapshot. To refresh it after you add threads or new layers, rebuild here and
re-run `make_bundle.sh`, then re-transfer. Or, on a target that has internet + the substrates,
`git pull` and re-run the pipeline (Option B).
