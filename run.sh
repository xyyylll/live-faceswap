#!/usr/bin/env bash
# Launch the Deep-Live-Cam UI with CoreML and a 320 detection size.
# Extra arguments are passed through, e.g. ./run.sh --live-mirror
#
# Do NOT pass -s/-t/-o here: any of them switches Deep-Live-Cam into headless
# batch mode and the UI will not open. Pick the source face inside the UI.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT/Deep-Live-Cam"
for a in "$@"; do
  case "$a" in
    -s|--source|-t|--target|-o|--output)
      echo "run.sh: $a would start headless mode; select files in the UI instead." >&2; exit 2 ;;
  esac
done
exec ./venv/bin/python run.py --execution-provider coreml --det-size 320 "$@"
