#!/usr/bin/env bash
# Package Bible-Brain as a standalone, offline zip for another computer.
#
#   bash pipeline/make_bundle.sh            # STANDALONE (default): zero-install.
#       Ships the SQLite brain + query.py + the visualization + docs. Queryable with
#       nothing but Python (sqlite3 is stdlib) — no pip, no duckdb, no internet ever.
#
#   bash pipeline/make_bundle.sh --full     # adds the parquet pool + pipeline + MCP server,
#       for rebuilding or plugging into Claude as an MCP brain (those need pip: duckdb/mcp).
#
# Second arg = output dir (default: $HOME).
set -e
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
MODE="standalone"; OUT_DIR="$HOME"
for a in "$@"; do case "$a" in --full) MODE="full";; *) OUT_DIR="$a";; esac; done
cd "$ROOT"

if [ ! -f data/bible-brain.sqlite ]; then
  echo "Building the SQLite brain first…"; python3 pipeline/export_sqlite.py
fi

if [ "$MODE" = "full" ]; then
  ZIP="$OUT_DIR/bible-brain-full.zip"; rm -f "$ZIP"
  zip -r -q "$ZIP" . -x 'data/cache/*' -x '.git/*' -x '*/__pycache__/*' -x '__pycache__/*' \
      -x '*.pyc' -x '.DS_Store' -x '*/.DS_Store'
  DESC="everything: SQLite + parquet pool + pipeline + MCP server + viz"
else
  ZIP="$OUT_DIR/bible-brain-standalone.zip"; rm -f "$ZIP"
  # zero-install set only: the SQLite brain, the stdlib query tool, the viz, the docs.
  zip -q "$ZIP" \
      query.py index.html requirements.txt \
      README.md SETUP.md CONSTITUTION.md SOURCES.md \
      data/bible-brain.sqlite \
      viz/index.html \
      index/MANIFEST.md index/messianic-threads.md \
      interpretive/prophecies.yaml \
      install.sh
  DESC="zero-install: SQLite brain + query.py + viz + docs (no pip, no internet)"
fi

SIZE="$(du -h "$ZIP" | awk '{print $1}')"
echo "→ $ZIP  ($SIZE)"
echo "   $DESC"
echo
echo "On the other computer:"
echo "   unzip $(basename "$ZIP") -d bible-brain && cd bible-brain && bash install.sh"
[ "$MODE" = "standalone" ] && echo "   Then: python3 query.py quotation \"Isaiah 7:14\"   ·   open viz/index.html"
