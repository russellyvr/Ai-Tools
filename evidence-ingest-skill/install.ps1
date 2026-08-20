<#
.SYNOPSIS
    Installs the "evidence-ingest" skill (Windows, PowerShell 7+).

.DESCRIPTION
    Copies skill\evidence-ingest from this package into the skills folder of
    the CLI you choose:
        .\install.ps1 -Claude     ->  $HOME\.claude\skills\evidence-ingest
        .\install.ps1 -Copilot    ->  $HOME\.copilot\skills\evidence-ingest
    Override the CLI home with $env:CLAUDE_HOME / $env:COPILOT_HOME.

    Design & security notes:
      - Runs entirely as the current user. No elevation required or requested.
      - Makes NO network calls, downloads nothing, executes nothing from the
        package - it only copies documented text files.
      - Never touches settings or any other configuration; it only writes
        inside the target skill folder.
      - Idempotent: safe to re-run. An existing installation is backed up to
        a timestamped sibling folder before being replaced.
      - Supports -WhatIf / -Confirm.

    After installing, provision the tool's virtualenv once (see README.md):
        cd <target>\tool
        py -3 -m venv .venv
        .venv\Scripts\pip install "pydantic>=2.5,<3" python-docx openpyxl
#>
[CmdletBinding(SupportsShouldProcess)]
param(
    [switch]$Claude,
    [switch]$Copilot
)
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

if (-not ($Claude -xor $Copilot)) {
    Write-Error 'Pick exactly one target: -Claude or -Copilot'
    exit 2
}

$SkillName = 'evidence-ingest'
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$Source    = Join-Path $ScriptDir "skill\$SkillName"

if ($Claude) {
    $CliHome = if ($env:CLAUDE_HOME) { $env:CLAUDE_HOME } else { Join-Path $HOME '.claude' }
} else {
    $CliHome = if ($env:COPILOT_HOME) { $env:COPILOT_HOME } else { Join-Path $HOME '.copilot' }
}
$Target = Join-Path $CliHome "skills\$SkillName"

# --- Preflight: validate the package before touching anything ---------------
if (-not (Test-Path (Join-Path $Source 'SKILL.md'))) {
    Write-Error "'$Source\SKILL.md' not found. Run this script from the extracted package root."
    exit 1
}
foreach ($f in 'tool\ingest.ps1', 'tool\evidence_ingest\__init__.py',
               'tool\evidence_ingest\cli.py', 'tool\demo\run-demo.ps1') {
    if (-not (Test-Path (Join-Path $Source $f))) {
        Write-Error "package is incomplete: $f is missing."
        exit 1
    }
}

# --- Backup any existing installation ----------------------------------------
if (Test-Path $Target) {
    $Backup = "$Target.bak-$(Get-Date -Format yyyyMMdd-HHmmss)"
    if ($PSCmdlet.ShouldProcess($Target, "Back up to $Backup")) {
        Move-Item -Path $Target -Destination $Backup
        Write-Host "Backed up existing installation to: $Backup"
    }
}

# --- Install -------------------------------------------------------------------
if ($PSCmdlet.ShouldProcess($Target, "Install skill from $Source")) {
    New-Item -ItemType Directory -Force -Path (Split-Path -Parent $Target) | Out-Null
    Copy-Item -Path $Source -Destination $Target -Recurse

    if (-not (Test-Path (Join-Path $Target 'SKILL.md'))) {
        Write-Error 'installation verification failed: SKILL.md missing at target.'
        exit 1
    }

    Write-Host ''
    Write-Host "Installed: $Target"
    Write-Host ''
    Write-Host 'Next steps:'
    Write-Host '  1. Provision the tool virtualenv (one time):'
    Write-Host "       cd `"$Target\tool`"; py -3 -m venv .venv"
    Write-Host '       .venv\Scripts\pip install "pydantic>=2.5,<3" python-docx openpyxl'
    Write-Host '  2. Restart any running CLI session so it picks up the skill.'
    Write-Host '  3. Smoke-test without OCR or network:'
    Write-Host "       pwsh -File `"$Target\tool\demo\run-demo.ps1`""
}
