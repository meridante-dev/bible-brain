#!/usr/bin/env bash
# Bible-Brain — set up on this (target) machine. Runs fully offline once the bundle
# includes data/. Safe to re-run.
set -e
ROOT="$(cd "$(dirname "$0")" && pwd)"
echo "== Bible-Brain @ $ROOT =="

# 1. Python + deps (duckdb to query, mcp to serve). No network needed for the data itself.
command -v python3 >/dev/null || { echo "Python 3 not found — install it first."; exit 1; }
python3 -c "import duckdb" 2>/dev/null || { echo "installing duckdb…"; pip3 install --quiet duckdb; }
python3 -c "import mcp"    2>/dev/null || { echo "installing mcp (for the server)…"; pip3 install --quiet mcp || echo "  (mcp optional — only needed for the MCP server)"; }

# 2. The data pool must be present (a proper bundle ships data/*.parquet).
if ! ls "$ROOT"/data/*.parquet >/dev/null 2>&1; then
  echo
  echo "!! No data/ pool found. This looks like a code-only checkout, not a bundle."
  echo "   Either copy a data/ folder here, or rebuild it (needs internet + the two"
  echo "   upstream substrates): python3 pipeline/ingest_corpus.py && … (see README)."
  exit 1
fi

# 3. Offline smoke test — proves the brain works here with no network.
echo; echo "== offline smoke test =="
python3 "$ROOT/pipeline/query_brain.py" stats

# 4. Next steps, with THIS machine's absolute paths filled in.
echo
echo "== ready =="
echo "Query:      python3 $ROOT/pipeline/query_brain.py quotation \"Isaiah 7:14\""
echo "Visualize:  open $ROOT/viz/index.html        # self-contained, works offline"
echo "MCP brain:  claude mcp add bible-brain -- python3 $ROOT/mcp-server/server.py"
echo "            (then restart your Claude session)"
echo
echo "To let one project draw from it, drop this .mcp.json into that project's root:"
cat <<JSON
{
  "mcpServers": {
    "bible-brain": { "command": "python3", "args": ["$ROOT/mcp-server/server.py"] }
  }
}
JSON
