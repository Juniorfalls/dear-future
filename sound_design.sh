#!/usr/bin/env bash
#
# sound_design.sh — reproducible build of the horror teaser for
# "The End of the Corridor": grade the 9 AnimateDiff clips, then synthesise
# and mix a drone / riser / stinger bed over the picture.
#
# Everything is derived from committed inputs:
#   out/video/NN-*.mp4              (generate_video_free.py --all)
#   remotion/public/audio/bg_music.mp3
# No sample libraries and no network access are required.
#
# Usage
#   ./sound_design.sh                 # grade + sound + mux -> out/video/end-of-the-corridor-teaser.mp4
#   ./sound_design.sh --click         # add a 2 kHz transient layer to the stinger
#   ./sound_design.sh --click --web   # same, but crf 20 + light grain -> ~6 MB web cut
#   ./sound_design.sh --web           # -> out/video/end-of-the-corridor-teaser-web.mp4
#   ./sound_design.sh --crf 22 --grain 1                    # manual quality control
#   ./sound_design.sh --out /tmp/t.mp4
#   ./sound_design.sh --reuse-graded out/video/graded.mp4   # skip the 1m concat/grade stage
#   ./sound_design.sh --keep-work     # leave the intermediate wavs for inspection
#
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CLIP_DIR="${CLIP_DIR:-$ROOT/out/video}"
BED="${BED:-$ROOT/remotion/public/audio/bg_music.mp3}"
OUT=""
REUSE_GRADED=""
CLICK=0
KEEP_WORK=0
WEB=0
CRF=17
GRAIN=5          # noise=alls=N, the film-grain strength baked into the grade

while [ $# -gt 0 ]; do
  case "$1" in
    --click)        CLICK=1 ;;
    --web)          WEB=1; CRF=20; GRAIN=2 ;;
    --crf)          CRF="$2"; shift ;;
    --grain)        GRAIN="$2"; shift ;;
    --keep-work)    KEEP_WORK=1 ;;
    --out)          OUT="$2"; shift ;;
    --reuse-graded) REUSE_GRADED="$2"; shift ;;
    -h|--help)      sed -n '2,20p' "${BASH_SOURCE[0]}" | sed 's/^# \?//'; exit 0 ;;
    *) echo "unknown argument: $1" >&2; exit 2 ;;
  esac
  shift
done

# Default target names the variant, so the 16 MB master is never overwritten
# by a web render (or vice versa).
if [ -z "$OUT" ]; then
  OUT="$CLIP_DIR/end-of-the-corridor-teaser"
  [ "$WEB" = 1 ] && OUT+="-web"
  OUT+=".mp4"
fi

# Lighter grain has to be re-baked, so reusing a graded master would defeat --web.
if [ "$WEB" = 1 ] && [ -n "$REUSE_GRADED" ]; then
  echo '[sound] --web ignores --reuse-graded (grain is baked into the grade)' >&2
  REUSE_GRADED=""
fi

# --- shot boundaries (each generated clip is exactly 3.000 s = 24f @ 8fps) ---
DUR=27
HIT_AT=21.6      # 0.6 s into shot 8 (the raised arm)
RISER_AT=19.4    # builds through shot 7 and lands on the hit
# ffmpeg adelay wants integer milliseconds
HIT_MS=21600
RISER_MS=19400
DRONE_OUT=17.2   # drone starts dying at the top of shot 7
HOLE_OUT=20.4    # pad stays ducked until just before the hit

log() { printf '[sound] %s\n' "$*"; }
die() { printf '[sound] ERROR: %s\n' "$*" >&2; exit 1; }

command -v ffmpeg >/dev/null || die "ffmpeg not on PATH"
command -v ffprobe >/dev/null || die "ffprobe not on PATH"
[ -f "$BED" ] || die "missing music bed: $BED"

WORK="$(mktemp -d)"
cleanup() { [ "$KEEP_WORK" = 1 ] && log "work dir kept: $WORK" || rm -rf "$WORK"; }
trap cleanup EXIT

# ---------------------------------------------------------------- stage 1: grade
GRADED="$WORK/graded.mp4"
if [ -n "$REUSE_GRADED" ]; then
  [ -f "$REUSE_GRADED" ] || die "--reuse-graded file not found: $REUSE_GRADED"
  GRADED="$REUSE_GRADED"
  log "stage 1/4: reusing graded picture $GRADED"
else
  log "stage 1/4: concatenating + grading the clips"
  mapfile -t CLIPS < <(find "$CLIP_DIR" -maxdepth 1 -name '[0-9][0-9]-*.mp4' \
                         ! -name '*teaser*' | sort)
  [ "${#CLIPS[@]}" -eq 9 ] || die "expected 9 clips in $CLIP_DIR, found ${#CLIPS[@]}"
  : > "$WORK/concat.txt"
  for clip in "${CLIPS[@]}"; do printf "file '%s'\n" "$clip" >> "$WORK/concat.txt"; done

  # crush blacks -> cold teal shadows -> contrast -> vignette -> grain -> fades
  ffmpeg -y -hide_banner -loglevel error \
    -f concat -safe 0 -i "$WORK/concat.txt" \
    -filter_complex "[0:v]curves=all='0/0 0.09/0.02 0.30/0.34 0.65/0.80 1/1',\
colorbalance=rs=-0.04:bs=0.12:rm=-0.02:bm=0.03:rh=0.01:bh=-0.02,\
eq=contrast=1.12:saturation=0.82:brightness=-0.01,\
vignette=angle=PI/4.2,noise=alls=$GRAIN:allf=t+u,\
fade=t=in:st=0:d=0.7,fade=t=out:st=26.3:d=0.7,format=yuv420p[v]" \
    -map "[v]" -an -c:v libx264 -preset slow -crf $CRF "$GRADED"
fi

# ------------------------------------------------------- stage 2: synthesise fx
log "stage 2/4: synthesising drone, riser and stinger"
# Drone: detuned sub sines (beating) + brown noise, swelling then dying at shot 7.
ffmpeg -y -hide_banner -loglevel error \
  -f lavfi -i "sine=frequency=41:sample_rate=48000:duration=$DUR" \
  -f lavfi -i "sine=frequency=42.7:sample_rate=48000:duration=$DUR" \
  -f lavfi -i "sine=frequency=61.9:sample_rate=48000:duration=$DUR" \
  -f lavfi -i "sine=frequency=82.4:sample_rate=48000:duration=$DUR" \
  -f lavfi -i "anoisesrc=color=brown:sample_rate=48000:duration=$DUR:amplitude=0.35" \
  -filter_complex "[0:a]volume=0.55[a0];[1:a]volume=0.45[a1];[2:a]volume=0.20[a2];\
[3:a]volume=0.10[a3];[4:a]lowpass=f=200,volume=0.55[a4];\
[a0][a1][a2][a3][a4]amix=inputs=5:normalize=0,\
volume='0.32+0.42*min(t/16,1)':eval=frame,\
afade=t=in:st=0:d=2.5,afade=t=out:st=17.5:d=3.5,\
aformat=channel_layouts=stereo,alimiter=limit=0.9" \
  -ar 48000 "$WORK/drone.wav"

# Stinger: 72 -> 32 Hz sine sweep with exponential decay + noise transient + room echo.
ffmpeg -y -hide_banner -loglevel error \
  -f lavfi -i "aevalsrc='0.85*exp(-4.2*t)*sin(2*PI*(72*t-110*t*t))':d=2.0:s=48000" \
  -f lavfi -i "anoisesrc=color=white:sample_rate=48000:duration=0.18:amplitude=0.9" \
  -filter_complex "[1:a]lowpass=f=2600,afade=t=out:st=0.005:d=0.17,volume=0.85[n];\
[0:a][n]amix=inputs=2:normalize=0,aecho=0.85:0.75:70|150|290:0.35|0.22|0.12,\
aformat=channel_layouts=stereo,alimiter=limit=0.95" \
  -ar 48000 "$WORK/hit.wav"

# Riser: pink noise breathing in through the hole, quadratic swell into the hit.
ffmpeg -y -hide_banner -loglevel error \
  -f lavfi -i "anoisesrc=color=pink:sample_rate=48000:duration=2.2:amplitude=0.7" \
  -af "highpass=f=700,volume='min(t/2.2,1)^2':eval=frame,\
afade=t=out:st=2.0:d=0.2,aformat=channel_layouts=stereo" \
  -ar 48000 "$WORK/riser.wav"

# Optional 2 kHz transient: the sub-only hit can feel thin on laptop speakers.
if [ "$CLICK" = 1 ]; then
  log "stage 2b: adding 2 kHz transient layer (--click)"
  ffmpeg -y -hide_banner -loglevel error \
    -f lavfi -i "anoisesrc=color=white:sample_rate=48000:duration=0.12:amplitude=0.6" \
    -af "bandpass=f=2200:width_type=h:w=1800,afade=t=out:st=0.006:d=0.11,\
volume=2.4,aformat=channel_layouts=stereo" \
    -ar 48000 "$WORK/click.wav"
fi

# -------------------------------------------------------------- stage 3: mix
log "stage 3/4: mixing (drone out at ${DRONE_OUT}s, hole to ${HOLE_OUT}s, hit at ${HIT_AT}s)"
INPUTS=(-i "$WORK/drone.wav" -i "$WORK/hit.wav" -i "$WORK/riser.wav" -i "$BED")
[ "$CLICK" = 1 ] && INPUTS+=(-i "$WORK/click.wav")

# Music pad: lowpassed, ducked hard through the hole so the riser has contrast.
FILTER="[3:a]atrim=0:$DUR,lowpass=f=3600,\
volume='0.30*(1-0.78*min(max((t-17.2)/0.4,0),1)*min(max((20.4-t)/0.4,0),1))':eval=frame,\
afade=t=in:st=0:d=2,afade=t=out:st=24.4:d=2.6,aresample=48000,\
aformat=channel_layouts=stereo[bed];\
[0:a]volume=1.45,afade=t=out:st=$DRONE_OUT:d=1.6[dr];\
[2:a]adelay=$RISER_MS|$RISER_MS[ris];\
[1:a]volume=1.4,adelay=$HIT_MS|$HIT_MS[hit];"

if [ "$CLICK" = 1 ]; then
  FILTER+="[4:a]adelay=$HIT_MS|$HIT_MS[clk];"
  MIX_IN="[dr][bed][ris][hit][clk]"
  MIX_N=5
else
  MIX_IN="[dr][bed][ris][hit]"
  MIX_N=4
fi
FILTER+="${MIX_IN}amix=inputs=$MIX_N:normalize=0:duration=longest,\
alimiter=limit=0.95:level=false,atrim=0:$DUR,afade=t=out:st=26.2:d=0.8"

ffmpeg -y -hide_banner -loglevel error "${INPUTS[@]}" \
  -filter_complex "$FILTER" -ar 48000 "$WORK/mix.wav"

# -------------------------------------------------------------- stage 4: mux
log "stage 4/4: muxing audio onto the graded picture (video stream copied)"
mkdir -p "$(dirname "$OUT")"
ffmpeg -y -hide_banner -loglevel error -i "$GRADED" -i "$WORK/mix.wav" \
  -map 0:v:0 -map 1:a:0 -c:v copy -c:a aac -b:a 160k -shortest \
  -movflags +faststart "$OUT.tmp.mp4"
mv "$OUT.tmp.mp4" "$OUT"

# ----------------------------------------------------------------- report
log "wrote $OUT"
ffprobe -v error -show_entries stream=codec_type,codec_name,width,height,nb_frames \
  -show_entries format=duration,size -of default=noprint_wrappers=1 "$OUT"
for seg in "2 10 drone" "18.3 1.0 hole" "$HIT_AT 1.0 stinger"; do
  set -- $seg
  printf '[sound] %-8s %ss+%ss  ' "$3" "$1" "$2"
  ffmpeg -hide_banner -ss "$1" -t "$2" -i "$OUT" -vn -af volumedetect -f null - 2>&1 \
    | grep -oE "mean_volume: [-0-9.]+ dB" | tr '\n' ' '
  echo
done
log "done"
