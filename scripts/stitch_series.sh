#!/usr/bin/env bash
# Concatenate intro + the five animal cuts + outro into one master file.
# Every segment is rendered by Remotion with identical parameters, so the
# concat demuxer can stream-copy them without re-encoding.
#
#   scripts/stitch_series.sh                       # -> out/impossible-superpowers.mp4
#   scripts/stitch_series.sh --out out/rough.mp4
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT="$ROOT/remotion/out"
TARGET="$OUT/impossible-superpowers.mp4"
[ "${1:-}" = "--out" ] && TARGET="$2"

COMPOSITOR="$ROOT/remotion/node_modules/@remotion/compositor-linux-x64-gnu"
FFMPEG="${FFMPEG:-$(command -v ffmpeg || echo "$COMPOSITOR/ffmpeg")}"
FFPROBE="${FFPROBE:-$(command -v ffprobe || echo "$COMPOSITOR/ffprobe")}"
if [ "$(dirname "$FFMPEG")" = "$COMPOSITOR" ]; then
  export LD_LIBRARY_PATH="$COMPOSITOR${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
fi

LIST="$(mktemp)"
SEGMENTS=("$OUT/intro.mp4")
for rank in 1 2 3 4 5; do SEGMENTS+=("$OUT/animal-$rank.mp4"); done
SEGMENTS+=("$OUT/outro.mp4")

for seg in "${SEGMENTS[@]}"; do
  [ -f "$seg" ] || { echo "[stitch] missing $seg" >&2; exit 1; }
  echo "file '$seg'" >> "$LIST"
done

"$FFMPEG" -y -v error -f concat -safe 0 -i "$LIST" -c copy -movflags +faststart "$TARGET"
rm -f "$LIST"

DUR=$("$FFPROBE" -v error -show_entries format=duration -of default=nw=1:nk=1 "$TARGET")
SIZE=$(du -h "$TARGET" | cut -f1)
echo "[stitch] $TARGET  ${DUR}s  ${SIZE}"
