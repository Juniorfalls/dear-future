#!/usr/bin/env bash
# Convert the voice track to mono 16 kHz and run Rhubarb Lip Sync.
set -euo pipefail
cd "$(dirname "$0")/.."
FFMPEG="${FFMPEG:-ffmpeg}"
"$FFMPEG" -y -v error -i public/vo.mp3 -ar 16000 -ac 1 public/vo.wav
"../tools/rhubarb/Rhubarb-Lip-Sync-1.14.0-Linux/rhubarb" \
  -f json -o public/lipsync.json public/vo.wav
echo "wrote public/lipsync.json"
