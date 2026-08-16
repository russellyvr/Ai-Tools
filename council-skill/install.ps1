<#
.SYNOPSIS
    Installs the "council" skill for GitHub Copilot CLI (Windows, PowerShell 7+).

.DESCRIPTION
    Copies skill/council from this package into the Copilot CLI skills folder
    ($HOME\.copilot\skills\council by default).

    Design & security notes:
      - Requires PowerShell 7+ and runs entirely as the current user.
        NO administrator rights are required or requested.
      - Makes NO network calls, downloads nothing, and executes nothing
        from the package — it only copies documented text files.
      - Never touches settings.json, copilot-instructions.md, or any other
        configuration; it only writes inside the target skill folder.
      - Idempotent: safe to re-run. An existing installation is backed up to
        a timestamped sibling folder before being replaced.
      - Supports -WhatIf / -Confirm via ShouldProcess.

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

$SkillName = 'council'
$Source    = Join-Path $PSScriptRoot 'skill' $SkillName
$Target    = Join-Path $CopilotHome 'skills' $SkillName

# --- Preflight: validate the package before touching anything -------------
if (-not (Test-Path (Join-Path $Source 'SKILL.md'))) {
    throw "Package is incomplete: '$Source\SKILL.md' not found. Run this script from the extracted package root."
}
foreach ($ref in 'prompts.md', 'rubric.md', 'output-template.md') {
    if (-not (Test-Path (Join-Path $Source 'references' $ref))) {
        throw "Package is incomplete: references\$ref is missing."
    }
}

# --- Backup any existing installation --------------------------------------
if (Test-Path $Target) {
    $backup = "$Target.bak-$(Get-Date -Format 'yyyyMMdd-HHmmss')"
    if ($PSCmdlet.ShouldProcess($Target, "Back up existing skill to $backup")) {
        Move-Item -LiteralPath $Target -Destination $backup
        Write-Host "Backed up existing installation to: $backup"
    }
}

# --- Install ----------------------------------------------------------------
if ($PSCmdlet.ShouldProcess($Target, 'Install council skill')) {
    New-Item -ItemType Directory -Path (Split-Path $Target) -Force | Out-Null
    Copy-Item -LiteralPath $Source -Destination $Target -Recurse
    # Verify the copy landed intact.
    if (-not (Test-Path (Join-Path $Target 'SKILL.md'))) {
        throw 'Installation verification failed: SKILL.md missing at target.'
    }
    Write-Host ''
    Write-Host "Installed: $Target" -ForegroundColor Green
    Write-Host ''
    Write-Host 'Next steps:'
    Write-Host '  1. Restart any running GitHub Copilot CLI session.'
    Write-Host '  2. Invoke the skill:  /council <your question or decision>'
    Write-Host '  3. If your model list differs from the shipped roster'
    Write-Host '     (Claude Fable 5 / Gemini 3.1 Pro / GPT-5.6 Sol), edit the'
    Write-Host "     roster table in $Target\SKILL.md."
}
