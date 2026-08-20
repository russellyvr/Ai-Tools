# ingest.ps1 — thin Windows launcher for evidence-ingest (corpus mode).
# Usage: .\ingest.ps1 <evidence_ingest args...>
# Example: .\ingest.ps1 run --input C:\in --work C:\work --output C:\out --no-ocr
#
# Launcher-only extra (Ring 1, never passed to Python): `run ... --clean`
#   After a successful `run`, the launcher re-verifies the output
#   (`verify --output O`) and, only if verify passes, deletes the staging
#   work folder EXCEPT `_improve\` (the self-improvement issue log is kept).
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$py = Get-Command python -ErrorAction SilentlyContinue
if (-not $py) { Write-Error "python not found on PATH (3.11+ required)"; exit 5 }
$ver = & python -c "import sys; print(sys.version_info >= (3,11))"
if ($ver -ne "True") { Write-Error "Python 3.11+ required"; exit 5 }

# Intercept launcher-only --clean flag (valid only with the `run` command).
$clean = $false
$fwd = @()
foreach ($a in $args) {
    if ($a -eq '--clean') { $clean = $true } else { $fwd += $a }
}
if ($clean -and ($fwd.Count -eq 0 -or $fwd[0] -ne 'run')) {
    [Console]::Error.WriteLine("--clean is only supported with the 'run' command"); exit 2
}

# Resolve --output and --work (work defaults to '<output>-work' beside it).
$outDir = $null; $workDir = $null
for ($i = 0; $i -lt $fwd.Count - 1; $i++) {
    if ($fwd[$i] -eq '--output') { $outDir = $fwd[$i + 1] }
    if ($fwd[$i] -eq '--work')   { $workDir = $fwd[$i + 1] }
}
if ($clean -and -not $outDir) { [Console]::Error.WriteLine("--clean requires --output"); exit 2 }
if ($clean -and -not $workDir) { $workDir = "$outDir-work" }

Push-Location $root
try {
    & python -m evidence_ingest @fwd
    $rc = $LASTEXITCODE
    if ($rc -ne 0 -or -not $clean) { exit $rc }

    # Gate cleanup on a fresh full verify of the published output.
    & python -m evidence_ingest verify --output $outDir
    if ($LASTEXITCODE -ne 0) {
        Write-Warning "verify failed (exit $LASTEXITCODE) — work folder retained: $workDir"
        exit $LASTEXITCODE
    }
    if (Test-Path $workDir) {
        Get-ChildItem -LiteralPath $workDir -Force |
            Where-Object { $_.Name -ne '_improve' } |
            Remove-Item -Recurse -Force
        Write-Host "cleaned work folder (kept _improve): $workDir"
    }
    exit 0
} finally {
    Pop-Location
}
