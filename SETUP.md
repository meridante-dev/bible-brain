# Deploy Bible-Brain to another computer (and run it offline)

Bible-Brain is small and self-contained: the **whole pool is ~23 MB of parquet**, and the
tools (`query_brain.py`, the visualization, the MCP server) read that pool from local files
with **no internet**. Only the `fetch_*` rebuild scripts need the network — so if you ship the
already-built data, the target machine never has to go online.

There are two ways to move it. Pick by whether the target has internet + the two upstream
substrates.

## Option A — Standalone bundle (recommended; zero-install, fully offline) ✅

Ships the brain as a single **SQLite file** + a **stdlib-only** query tool + the
visualization. The recipient needs **nothing installed** — `query.py` uses Python's built-in
`sqlite3` (no pip, no duckdb), and `viz/index.html` opens in any browser. No internet, ever.

**On this machine:**
```bash
bash pipeline/make_bundle.sh            # -> ~/bible-brain-standalone.zip  (~30 MB)
```
Transfer the zip however you like — USB drive, AirDrop, a cloud folder, `scp`.

**On the other computer** (nothing to install):
```bash
unzip bible-brain-standalone.zip -d bible-brain && cd bible-brain
bash install.sh                          # offline smoke test + prints the commands
python3 query.py quotation "Isaiah 7:14" # MT · LXX · NT, from Python stdlib alone
open viz/index.html                      # the visualization, self-contained
```

`query.py` covers `stats · verse · quotation · interlinear · concordance · define · thread ·
threads · search`. **Even lighter:** for someone who only wants to *look*, `viz/index.html` (64
KB) is a complete standalone by itself — double-click it, no unzip, no Python.

### Want the MCP server / rebuild ability too?

```bash
bash pipeline/make_bundle.sh --full     # -> ~/bible-brain-full.zip
```
The `--full` bundle also carries the parquet pool, the pipeline, and the MCP server. Those need
one `pip install duckdb mcp` (internet once) — use it if the target should plug into Claude as
an MCP brain or regenerate data. `install.sh` prints the `claude mcp add …` line with the
correct local path.

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
