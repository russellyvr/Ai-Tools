#!/bin/sh
# Demo: full gated ingest of the synthetic sample corpus (no OCR).
set -e
root="$(cd "$(dirname "$0")" && pwd)"
proj="$(dirname "$root")"
cd "$proj"
rm -rf "$root/out"
python3 -m evidence_ingest run --input "$root/input" --work "$root/out/work" \
    --output "$root/out/corpus" --no-ocr
