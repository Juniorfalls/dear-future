#!/usr/bin/env bash
# Alternative mix stage for a rendered Dear Future episode.
#
# `sound_design.sh` is the canonical, self-contained teaser build (grade +
# synthesised drone/riser/stinger). This script is the other half of the
# job: it takes a picture that is already graded and gives it a mix that hits
# a delivery spec. It needs the installed ffmpeg skill (see README, "FFmpeg
# skill"); sound_design.sh does not.
#
# Sits between the render (compile_horror_episode.py / openfilm) and delivery:
# the picture is stream-copied the whole way, only audio is touched.
#
#   1. mix    - fold the music/drone bed under the existing voice track and
#               duck it so narration stays intelligible
#   2. normalise - two-pass EBU R128 loudness to a delivery target
#   3. verify - pre-delivery spec check (size, codec, loudness, true peak)
#
# Everything goes through the project ffmpeg skill scripts, so the ffmpeg
# version is the pinned local one in tools/bin/.
#
# Usage:
#   ./sound_design_mix.sh 12th-street-ep01.mp4
#   ./sound_design_mix.sh out/ep01.mp4 --music horror_openfilm_test/assets/drone.wav
#   ./sound_design_mix.sh out/ep01.mp4 --music bed.wav --music-volume 0.18 --duck
#   ./sound_design_mix.sh out/ep01.mp4 --no-music --lufs -16 --out out/ep01_final.mp4
#
# Exit codes: 0 ok, 1 usage/missing file, 2 a stage failed, 3 verify failed.

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_SCRIPTS="$ROOT/.pi/skills/ffmpeg-skill/scripts"

# Prefer the pinned ffmpeg/ffprobe shipped with the repo.
if [ -x "$ROOT/tools/bin/ffmpeg" ]; then
  export PATH="$ROOT/tools/bin:$PATH"
fi

die() {
  echo "sound_design_mix: $*" >&2
  exit "${2:-1}"
}

usage() {
  sed -n '2,25p' "$0" | sed 's/^# \{0,1\}//'
  exit "${1:-0}"
}

# ---------------------------------------------------------------- arguments
INPUT=""
MUSIC=""
MUSIC_VOLUME="0.24"
DUCK="--duck"
DUCK_AMOUNT="6"
OUTPUT=""
LUFS="-14"
TP="-1"
LRA="11"
PLATFORM=""
FADE_IN="0.4"
FADE_OUT="1.2"
DENOISE=""
VOICE=""
CHECK="1"
DRY_RUN=""
REST=()

while [ $# -gt 0 ]; do
  case "$1" in
    -h|--help) usage 0 ;;
    --music) MUSIC="${2:?--music needs a file}"; shift 2 ;;
    --music-volume) MUSIC_VOLUME="${2:?--music-volume needs a value}"; shift 2 ;;
    --no-music) MUSIC=""; shift ;;
    --no-duck) DUCK=""; shift ;;
    --duck-amount) DUCK_AMOUNT="${2:?}"; shift 2 ;;
    --lufs) LUFS="${2:?}"; shift 2 ;;
    --tp) TP="${2:?}"; shift 2 ;;
    --lra) LRA="${2:?}"; shift 2 ;;
    --fade-in) FADE_IN="${2:?}"; shift 2 ;;
    --fade-out) FADE_OUT="${2:?}"; shift 2 ;;
    --denoise) DENOISE="--denoise"; shift ;;
    --voice) VOICE="${2:?}"; shift 2 ;;
    --platform) PLATFORM="${2:?}"; shift 2 ;;
    --no-check) CHECK=""; shift ;;
    --out|-o) OUTPUT="${2:?--out needs a file}"; shift 2 ;;
    --dry-run) DRY_RUN="--dry-run"; shift ;;
    --) shift; REST=("$@"); break ;;
    -*) die "unknown option: $1" 1 ;;
    *) [[ -z "$INPUT" ]] && INPUT="$1" || REST+=("$1"); shift ;;
  esac
done

[ -n "$INPUT" ] || die "no input video given; try --help" 1
[ -f "$INPUT" ] || die "no such file: $INPUT" 1
[ -d "$SKILL_SCRIPTS" ] || die "ffmpeg skill not found at $SKILL_SCRIPTS" 1

command -v ffmpeg >/dev/null 2>&1 || die "ffmpeg not on PATH" 1
command -v ffprobe >/dev/null 2>&1 || die "ffprobe not on PATH" 1

if [ -n "$MUSIC" ]; then
  [ -f "$MUSIC" ] || die "no such music file: $MUSIC" 1
fi

IN_DIR="$(cd "$(dirname "$INPUT")" && pwd)"
IN_NAME="$(basename "${INPUT%.*}")"
if [ -z "$OUTPUT" ]; then
  OUTPUT="$IN_DIR/${IN_NAME}_final.mp4"
fi
OUT_DIR="$(cd "$(dirname "$OUTPUT")" 2>/dev/null && pwd || true)"
mkdir -p "$(dirname "$OUTPUT")"

PY="$(command -v python3)"
SCRIPT="$SKILL_SCRIPTS"

step() { printf '\n== %s\n' "$*"; }

run() {
  printf '   $ %s\n' "$*"
  if [ -z "$DRY_RUN" ]; then
    "$@" || die "step failed: $*" 2
  fi
}

# ------------------------------------------------------------------- 0 plan
step "0/3 plan"
printf '   input    %s\n' "$INPUT"
printf '   output   %s\n' "$OUTPUT"
if [ -n "$MUSIC" ]; then
  printf '   bed      %s at volume %s%s\n' "$MUSIC" "$MUSIC_VOLUME" \
    "$([ -n "$DUCK" ] && echo ", ducked by ${DUCK_AMOUNT}dB" || echo ", no ducking")"
else
  printf '   bed      none (voice-only mix)\n'
fi
printf '   loudness %s LUFS, %s dBTP, LRA %s\n' "$LUFS" "$TP" "$LRA"
"$PY" "$SCRIPT/probe.py" "$INPUT" --json-brief 2>/dev/null || true

# Stream duration + audio-presence sanity check before touching anything.
if command -v ffprobe >/dev/null 2>&1; then
  HAS_AUDIO="$(ffprobe -v error -select_streams a -show_entries stream=index \
    -of csv=p=0 "$INPUT" | head -1)"
  [ -n "$HAS_AUDIO" ] || die "input has no audio stream: $INPUT" 2
fi

# ------------------------------------------------------- 1 mix the bed + voice
MIXED="$(mktemp -t df-mix-XXXXXX).mp4"
trap 'rm -f "$MIXED"' EXIT

step "1/3 mix"
if [ -n "$MUSIC" ]; then
  MIX_ARGS=("$INPUT" --music "$MUSIC" --music-volume "$MUSIC_VOLUME"
            --music-loop --fade-in "$FADE_IN" --music-fade-out "$FADE_OUT"
            -o "$MIXED" --overwrite)
  [ -n "$DUCK" ] && MIX_ARGS+=(--duck --duck-amount "$DUCK_AMOUNT")
  [ -n "$DENOISE" ] && MIX_ARGS+=("$DENOISE")
  [ -n "$VOICE" ] && MIX_ARGS+=(--voice "$VOICE")
  run "$PY" "$SCRIPT/audio.py" "${MIX_ARGS[@]}"
else
  MIX_ARGS=("$INPUT" --fade-in "$FADE_IN" --fade-out "$FADE_OUT"
            -o "$MIXED" --overwrite)
  [ -n "$DENOISE" ] && MIX_ARGS+=("$DENOISE")
  [ -n "$VOICE" ] && MIX_ARGS+=(--voice "$VOICE")
  run "$PY" "$SCRIPT/audio.py" "${MIX_ARGS[@]}"
fi
[ -n "$DRY_RUN" ] && MIXED="$INPUT"

# ------------------------------------------------------------ 2 normalise
step "2/3 loudness"
run "$PY" "$SCRIPT/loudness.py" "$MIXED" -I "$LUFS" --tp "$TP" --lra "$LRA" \
  -o "$OUTPUT" --overwrite

# -------------------------------------------------------------- 3 verify
step "3/3 verify"
if [ -n "$CHECK" ]; then
  CHECK_ARGS=("$OUTPUT" --lufs "$LUFS" --tp "$TP")
  [ -n "$PLATFORM" ] && CHECK_ARGS+=(--platform "$PLATFORM")
  printf '   $ %s %s\n' "$PY" "$SCRIPT/check.py" "${CHECK_ARGS[*]}"
  if [ -z "$DRY_RUN" ]; then
    if ! "$PY" "$SCRIPT/check.py" "${CHECK_ARGS[@]}"; then
      echo "sound_design_mix: delivery check failed for $OUTPUT" >&2
      exit 3
    fi
  fi
fi

step "done"
printf '   %s\n' "$OUTPUT"
