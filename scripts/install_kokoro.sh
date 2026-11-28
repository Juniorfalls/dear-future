#!/usr/bin/env bash
# Install the Kokoro-82M voice engine into .venv-voice and expose
# `kokoro-tts-tool` on the venv's PATH.
#
#   scripts/install_kokoro.sh          # create venv, install, download the model
#   scripts/install_kokoro.sh --no-init
#
# The PyPI package `kokoro-tts-tool` does not exist; this project ships its own
# equivalent CLI (scripts/kokoro_tts_tool.py) on top of `kokoro-onnx`, which
# runs the official Kokoro-82M v1.0 ONNX export on CPU.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV="$ROOT/.venv-voice"
PY="$VENV/bin/python"

echo "[install] venv -> $VENV"
[ -d "$VENV" ] || python3 -m venv "$VENV"
"$PY" -m pip install --quiet --upgrade pip

echo "[install] kokoro-onnx + soundfile"
"$PY" -m pip install --quiet kokoro-onnx soundfile numpy

# editable shim: `kokoro-tts-tool` on the venv PATH
cat > "$VENV/bin/kokoro-tts-tool" <<EOF
#!/usr/bin/env bash
exec "$PY" "$ROOT/scripts/kokoro_tts_tool.py" "\$@"
EOF
chmod +x "$VENV/bin/kokoro-tts-tool"
echo "[install] shim -> $VENV/bin/kokoro-tts-tool"

if [ "${1:-}" != "--no-init" ]; then
  echo "[install] downloading the Kokoro-82M model"
  "$VENV/bin/kokoro-tts-tool" init
fi

echo "[install] done. Try: $VENV/bin/kokoro-tts-tool voices"
