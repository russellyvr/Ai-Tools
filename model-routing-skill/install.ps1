<#
.SYNOPSIS
    Installs the deterministic model-routing deployment for GitHub Copilot CLI
    (Windows, PowerShell 7+): KPI analyzer, targets, and the full specification.

.DESCRIPTION
    Copies from this package into the Copilot CLI home ($HOME\.copilot by default):
      routing\analyze_routing.py  ->  <home>\routing\
      routing\targets.json        ->  <home>\routing\   (never overwritten if present)
      instructions\model-routing.md -> <home>\instructions\

    Design & security notes:
      - Requires PowerShell 7+ and runs entirely as the current user.
        NO administrator rights are required or requested.
      - Makes NO network calls, downloads nothing, and executes nothing —
        it only copies documented text files. The analyzer itself is a
        standard-library-only Python script you can read before running.
      - DELIBERATELY never edits settings.json or copilot-instructions.md:
        model pins and the inline routing rubric change your agent's behavior,
        so those two steps stay manual and are printed at the end.
      - Your existing targets.json (your KPI targets) is never overwritten;
        the packaged copy is written alongside as targets.json.new instead.
      - Idempotent and backup-first; supports -WhatIf / -Confirm.

.PARAMETER CopilotHome
    The Copilot CLI home directory. Defaults to "$HOME\.copilot".

.EXAMPLE
    pwsh -File .\install.ps1
.EXAMPLE
    pwsh -File .\install.ps1 -WhatIf         # preview, change nothing
#>
#Requires -Version 7.0
[CmdletBinding(SupportsShouldProcess)]
param(
    [ValidateNotNullOrEmpty()]
    [string]$CopilotHome = (Join-Path $HOME '.copilot')
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$RoutingSrc = Join-Path $PSScriptRoot 'routing'
$SpecSrc    = Join-Path $PSScriptRoot 'instructions' 'model-routing.md'
$RoutingDst = Join-Path $CopilotHome 'routing'
$SpecDst    = Join-Path $CopilotHome 'instructions' 'model-routing.md'

# --- Preflight ---------------------------------------------------------------
foreach ($f in @((Join-Path $RoutingSrc 'analyze_routing.py'),
                 (Join-Path $RoutingSrc 'targets.json'), $SpecSrc)) {
    if (-not (Test-Path $f)) {
        throw "Package is incomplete: '$f' not found. Run this script from the extracted package root."
    }
}
if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Warning 'python was not found on PATH. The analyzer needs Python 3.9+; install it before running the analyzer.'
}

function Install-FileSafe {
    [CmdletBinding(SupportsShouldProcess)]
    param([string]$Src, [string]$Dst, [switch]$NeverOverwrite)
    $dir = Split-Path $Dst
    if ((Test-Path $Dst) -and $NeverOverwrite) {
        $alt = "$Dst.new"
        if ($PSCmdlet.ShouldProcess($alt, "Write packaged copy alongside existing file (kept: $Dst)")) {
            Copy-Item -LiteralPath $Src -Destination $alt -Force
            Write-Host "Kept your existing $(Split-Path -Leaf $Dst); packaged version saved as $(Split-Path -Leaf $alt)"
        }
        return
    }
    if (Test-Path $Dst) {
        $backup = "$Dst.bak-$(Get-Date -Format 'yyyyMMdd-HHmmss')"
        if ($PSCmdlet.ShouldProcess($Dst, "Back up to $backup")) {
            Copy-Item -LiteralPath $Dst -Destination $backup
        }
    }
    if ($PSCmdlet.ShouldProcess($Dst, 'Install')) {
        New-Item -ItemType Directory -Path $dir -Force | Out-Null
        Copy-Item -LiteralPath $Src -Destination $Dst -Force
        Write-Host "Installed: $Dst"
    }
}

# --- Install -----------------------------------------------------------------
Install-FileSafe (Join-Path $RoutingSrc 'analyze_routing.py') (Join-Path $RoutingDst 'analyze_routing.py')
Install-FileSafe (Join-Path $RoutingSrc 'targets.json')       (Join-Path $RoutingDst 'targets.json') -NeverOverwrite
Install-FileSafe $SpecSrc $SpecDst

Write-Host ''
Write-Host 'Files installed.' -ForegroundColor Green
Write-Host ''
Write-Host 'Manual steps (deliberately NOT automated - these change agent behavior):' -ForegroundColor Yellow
Write-Host '  1. Pin your sub-agents in ~\.copilot\settings.json -> "subagents": { "agents": { ... } }'
Write-Host '     explore/task = a cheap ECONOMY model at low effort;'
Write-Host '     code-review/research = a STANDARD model at medium effort.'
Write-Host '  2. Paste the compact 7-row routing table (see README or the spec)'
Write-Host '     into ~\.copilot\copilot-instructions.md so it is injected every turn.'
Write-Host '  3. Edit tier_patterns in ~\.copilot\routing\targets.json to match'
Write-Host '     the model names visible in YOUR session.'
Write-Host '  4. Test the analyzer:  python "$HOME\.copilot\routing\analyze_routing.py"'
Write-Host '  5. Optional: install the companion route-tune skill for the'
Write-Host '     self-tuning feedback loop.'
