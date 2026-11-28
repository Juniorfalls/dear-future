#!/usr/bin/env bash
# Render the whole five-animal documentary: per animal, load the script into
# animal.json, speak it with Kokoro, then render the landscape cut. Finally the
# intro/outro cards and the stitched master.
#
#   scripts/render_series.sh                 # all five + cards + stitch
#   scripts/render_series.sh 2 3             # just animals 2 and 3
#   scripts/render_series.sh --cards-only    # intro/outro + stitch from out/
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PY="$ROOT/.venv-voice/bin/python"
OUT="$ROOT/remotion/out"
CARDS_ONLY=0
RANKS=()
for arg in "$@"; do
  case "$arg" in
    --cards-only) CARDS_ONLY=1 ;;
    *) RANKS+=("$arg") ;;
  esac
done
[ ${#RANKS[@]} -eq 0 ] && RANKS=(1 2 3 4 5)

mkdir -p "$OUT"
cd "$ROOT/remotion"

if [ "$CARDS_ONLY" -eq 0 ]; then
  for rank in "${RANKS[@]}"; do
    echo "=== animal $rank: script ==="
    "$PY" ../scripts/generate_animal_script.py --provider none --apply "$rank"
    echo "=== animal $rank: voice (kokoro) ==="
    "$PY" ../scripts/generate_voiceover.py
    echo "=== animal $rank: render ==="
    npx remotion render AnimalScene "out/animal-$rank.mp4" --crf=16 --concurrency=1
  done
fi

echo "=== cards ==="
npx remotion render SeriesIntro "$OUT/intro.mp4" --crf=16 --concurrency=1
npx remotion render SeriesOutro "$OUT/outro.mp4" --crf=16 --concurrency=1

echo "=== stitch ==="
"$ROOT/scripts/stitch_series.sh"
