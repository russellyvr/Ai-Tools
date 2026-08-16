<#
.SYNOPSIS
    Installs the "route-tune" skill for GitHub Copilot CLI (Windows, PowerShell 7+).

.DESCRIPTION
    Copies skill\route-tune from this package into the Copilot CLI skills
    folder ($HOME\.copilot\skills\route-tune by default).

    PREREQUISITE: the model-routing deployment (companion package) must be
    installed first — route-tune is the tuner for that deployment and needs
    <home>\routing\analyze_routing.py and targets.json to exist. This script
    checks and warns, but does not install them.

    Design & security notes:
      - Requires PowerShell 7+ and runs entirely as the current user.
        NO administrator rights are required or requested.
      - Makes NO network calls, downloads nothing, and executes nothing —
        it only copies documented text files.
      - Never touches settings.json, copilot-instructions.md, or the routing
        assets; it only writes inside the target skill folder. (The skill
        itself edits pins only within bounded, logged, reversible limits —
        see SKILL.md.)
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

$SkillName = 'route-tune'
$Source    = Join-Path $PSScriptRoot 'skill' $SkillName
$Target    = Join-Path $CopilotHome 'skills' $SkillName

# --- Preflight ----------------------------------------------------------------
if (-not (Test-Path (Join-Path $Source 'SKILL.md'))) {
    throw "Package is incomplete: '$Source\SKILL.md' not found. Run this script from the extracted package root."
}
foreach ($dep in @((Join-Path $CopilotHome 'routing' 'analyze_routing.py'),
                   (Join-Path $CopilotHome 'routing' 'targets.json'))) {
    if (-not (Test-Path $dep)) {
        Write-Warning "Prerequisite missing: $dep`n         Install the companion model-routing package first - route-tune cannot run without it."
    }
}

# --- Backup any existing installation -------------------------------------------
if (Test-Path $Target) {
    $backup = "$Target.bak-$(Get-Date -Format 'yyyyMMdd-HHmmss')"
    if ($PSCmdlet.ShouldProcess($Target, "Back up existing skill to $backup")) {
        Move-Item -LiteralPath $Target -Destination $backup
        Write-Host "Backed up existing installation to: $backup"
    }
}

# --- Install ---------------------------------------------------------------------
if ($PSCmdlet.ShouldProcess($Target, 'Install route-tune skill')) {
    New-Item -ItemType Directory -Path (Split-Path $Target) -Force | Out-Null
    Copy-Item -LiteralPath $Source -Destination $Target -Recurse
    if (-not (Test-Path (Join-Path $Target 'SKILL.md'))) {
        throw 'Installation verification failed: SKILL.md missing at target.'
    }
    Write-Host ''
    Write-Host "Installed: $Target" -ForegroundColor Green
    Write-Host ''
    Write-Host 'Next steps:'
    Write-Host '  1. Ensure the model-routing deployment is installed (analyzer + targets).'
    Write-Host '  2. Restart any running GitHub Copilot CLI session.'
    Write-Host '  3. Run an interactive review:      /route-tune'
    Write-Host '     Or apply the recommendation:    /route-tune go'
    Write-Host '  4. Optional: schedule a weekly analyzer run (Task Scheduler) so'
    Write-Host '     the KPI report is always fresh, e.g. weekly:'
    Write-Host '       python "$HOME\.copilot\routing\analyze_routing.py"'
}
