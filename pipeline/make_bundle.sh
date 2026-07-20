#!/usr/bin/env bash
# Package Bible-Brain as a self-contained, offline-ready bundle for another computer.
# Includes the code, docs, the visualization, AND the built data pool (data/*.parquet) —
# but NOT the 112MB rebuild cache, .git, or __pycache__. Everything the target needs to
# query, visualize, and serve the brain with zero internet.
#
# Run:  bash pipeline/make_bundle.sh  [output_dir]
set -e
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OUT_DIR="${1:-$HOME}"
STAMP="$(python3 -c 'import datetime,sys; sys.stdout.write("")' 2>/dev/null; echo)"
ZIP="$OUT_DIR/bible-brain-bundle.zip"

if ! ls "$ROOT"/data/*.parquet >/dev/null 2>&1; then
  echo "No data/*.parquet found — build the pool first (see README). Aborting."; exit 1
fi

rm -f "$ZIP"
cd "$ROOT"
# Include everything tracked-worthy + the parquet pool; exclude bulk cache and junk.
zip -r -q "$ZIP" . \
  -x 'data/cache/*' \
  -x '.git/*' \
  -x '*/__pycache__/*' -x '__pycache__/*' \
  -x '*.pyc' \
  -x '.DS_Store' -x '*/.DS_Store'

SIZE="$(du -h "$ZIP" | awk '{print $1}')"
echo "→ $ZIP  ($SIZE)"
echo "   contains: code + docs + viz/index.html + data/*.parquet (the pool)"
echo
echo "On the other computer:"
echo "   1. unzip bible-brain-bundle.zip -d bible-brain && cd bible-brain"
echo "   2. bash install.sh          # installs deps, offline smoke test, prints next steps"
echo "   Everything then runs with NO internet."
