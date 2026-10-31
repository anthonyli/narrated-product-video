#!/usr/bin/env sh
# Official process-start ONNX Runtime telemetry opt-out; no network-policy changes.
set -eu
SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
ENTRY=local_voice.py
if [ "${1:-}" = "--segments" ]; then ENTRY=local_voice_segments.py; shift; fi
export ORT_DISABLE_TELEMETRY=1
export HF_HUB_OFFLINE=1
export TRANSFORMERS_OFFLINE=1
exec "${PYTHON:-python3}" "$SCRIPT_DIR/$ENTRY" "$@"
