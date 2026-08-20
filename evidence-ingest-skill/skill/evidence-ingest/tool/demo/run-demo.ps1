# Demo: full gated ingest of the synthetic sample corpus (no OCR).
# Run from anywhere; outputs land under demo\out.
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$proj = Split-Path -Parent $root
Push-Location $proj
try {
    $work = Join-Path $root "out\work"
    $corpus = Join-Path $root "out\corpus"
    if (Test-Path (Join-Path $root "out")) { Remove-Item (Join-Path $root "out") -Recurse -Force }
    python -m evidence_ingest run --input (Join-Path $root "input") --work $work --output $corpus --no-ocr
    exit $LASTEXITCODE
} finally {
    Pop-Location
}
