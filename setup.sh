#!/usr/bin/env bash
# Set up Deep-Live-Cam for real-time face swap on Apple Silicon (CoreML).
#
#   ./setup.sh                 # base install
#   ./setup.sh --with-gpen256  # also fetch the GPEN-256 face enhancer (optional, ~75.72MB)
#
# What it does:
#   1. brew: python@3.14, python-tk@3.14, ffmpeg
#   2. fetch Deep-Live-Cam at a pinned, tested commit into ./Deep-Live-Cam
#   3. create ./Deep-Live-Cam/venv and install requirements
#   4. download models with curl and verify their byte sizes
#
# Why curl for models: the app's built-in downloader verifies TLS against the certifi
# bundle only, which fails behind networks that use a custom root CA. curl uses the
# macOS system trust store. TLS verification is never disabled.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
DLC_DIR="$ROOT/Deep-Live-Cam"
DLC_REPO="https://github.com/hacksider/Deep-Live-Cam.git"
DLC_COMMIT="08896a51c9a6198f50dc9f7508acf39fc460c8f1"   # 2026-11-08, tested on M4 Pro
PY="python3.14"
HF="https://huggingface.co/hacksider/deep-live-cam/resolve/main"
WITH_GPEN256=0

for arg in "$@"; do
  case "$arg" in
    --with-gpen256) WITH_GPEN256=1 ;;
    -h|--help) sed -n '2,15p' "$0"; exit 0 ;;
    *) echo "unknown option: $arg" >&2; exit 2 ;;
  esac
done

if [[ "$(uname -s)" != "Darwin" || "$(uname -m)" != "arm64" ]]; then
  echo "This script targets Apple Silicon macOS. See Deep-Live-Cam's README for other platforms." >&2
  exit 1
fi

step() { printf '\n==> %s\n' "$*"; }

# 1. system deps -------------------------------------------------------------
step "brew dependencies"
command -v brew >/dev/null || { echo "Homebrew is required: https://brew.sh" >&2; exit 1; }
for pkg in python@3.14 python-tk@3.14 ffmpeg; do
  brew list --versions "$pkg" >/dev/null 2>&1 || brew install "$pkg"
done
"$PY" -c "import tkinter" || { echo "tkinter missing: brew reinstall python-tk@3.14" >&2; exit 1; }

# 2. Deep-Live-Cam at pinned commit -------------------------------------------
step "Deep-Live-Cam @ ${DLC_COMMIT:0:7}"
if [[ ! -d "$DLC_DIR/.git" ]]; then
  git init -q "$DLC_DIR"
  git -C "$DLC_DIR" remote add origin "$DLC_REPO"
fi
if [[ "$(git -C "$DLC_DIR" rev-parse HEAD 2>/dev/null || true)" != "$DLC_COMMIT" ]]; then
  git -C "$DLC_DIR" fetch -q --depth 1 origin "$DLC_COMMIT"
  git -C "$DLC_DIR" checkout -q --detach "$DLC_COMMIT"
fi

# 3. Python env ---------------------------------------------------------------
step "virtualenv + requirements"
[[ -x "$DLC_DIR/venv/bin/python" ]] || "$PY" -m venv "$DLC_DIR/venv"
"$DLC_DIR/venv/bin/python" -m pip install -q --upgrade pip
"$DLC_DIR/venv/bin/pip" install -q -r "$DLC_DIR/requirements.txt"
"$DLC_DIR/venv/bin/python" -c "import onnxruntime as o; p=o.get_available_providers(); assert 'CoreMLExecutionProvider' in p, p; print('CoreML OK:', p)"

# 4. models -------------------------------------------------------------------
# fetch <url> <dest> <expected_bytes>
fetch() {
  local url="$1" dest="$2" size="$3" got
  mkdir -p "$(dirname "$dest")"
  if [[ -f "$dest" && "$(stat -f%z "$dest")" == "$size" ]]; then
    echo "  ok (cached)  $(basename "$dest")"; return
  fi
  curl -sS -L --fail --retry 3 -C - -o "$dest" "$url"
  got="$(stat -f%z "$dest")"
  if [[ "$got" != "$size" ]]; then
    echo "  size mismatch for $dest: got $got, expected $size" >&2; exit 1
  fi
  echo "  ok           $(basename "$dest")"
}

step "models"
fetch "$HF/inswapper_128_fp16.onnx" "$DLC_DIR/models/inswapper_128_fp16.onnx" 277680638

BUFFALO="$HOME/.insightface/models/buffalo_l"
fetch "$HF/buffalo_l/buffalo_l/1k3d68.onnx"    "$BUFFALO/1k3d68.onnx"    143607619
fetch "$HF/buffalo_l/buffalo_l/2d106det.onnx"  "$BUFFALO/2d106det.onnx"  5030888
fetch "$HF/buffalo_l/buffalo_l/det_10g.onnx"   "$BUFFALO/det_10g.onnx"   16923827
fetch "$HF/buffalo_l/buffalo_l/genderage.onnx" "$BUFFALO/genderage.onnx" 1322532
fetch "$HF/buffalo_l/buffalo_l/w600k_r50.onnx" "$BUFFALO/w600k_r50.onnx" 174383860

if [[ "$WITH_GPEN256" == 1 ]]; then
  fetch "$HF/GPEN-BFR-256.onnx" "$DLC_DIR/models/GPEN-BFR-256.onnx" 75715262
fi

step "done"
echo "Start the UI with: ./run.sh"
