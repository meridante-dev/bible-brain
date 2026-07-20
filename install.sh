#!/usr/bin/env bash
# Bible-Brain — set up on this (target) machine. The standalone bundle needs NOTHING
# installed: query.py uses Python's built-in sqlite3, and viz/index.html opens in any
# browser. Safe to re-run.
set -e
ROOT="$(cd "$(dirname "$0")" && pwd)"
echo "== Bible-Brain @ $ROOT =="
command -v python3 >/dev/null || { echo "Python 3 not found — install it first."; exit 1; }

# --- The zero-install path: SQLite + stdlib. No pip, no internet. ---
if [ -f "$ROOT/data/bible-brain.sqlite" ]; then
  echo; echo "== offline smoke test (Python stdlib only, no pip) =="
  python3 "$ROOT/query.py" stats
  echo
  echo "== ready — nothing to install =="
  echo "Query:      python3 $ROOT/query.py quotation \"Isaiah 7:14\""
  echo "            python3 $ROOT/query.py thread virgin-birth   ·   python3 $ROOT/query.py --help"
  echo "Visualize:  open $ROOT/viz/index.html        # self-contained, works offline"
else
  echo "No data/bible-brain.sqlite here."
fi

# --- Optional power features (need pip; internet once) ---
if [ -f "$ROOT/mcp-server/server.py" ] && ls "$ROOT"/data/*.parquet >/dev/null 2>&1; then
  echo
  echo "== optional: use it as an MCP brain inside Claude (needs 'pip install duckdb mcp') =="
  echo "   claude mcp add bible-brain -- python3 $ROOT/mcp-server/server.py"
fi
