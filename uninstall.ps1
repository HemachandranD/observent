# observent uninstaller — removes OBSERVENT_HOME and project-scoped adapter files.
# Usage: .\uninstall.ps1 [-ProjectDir <path>] [-DryRun]
[CmdletBinding()]
param(
    [string]$ProjectDir = $PWD.Path,
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"
$ObserventHome = if ($env:OBSERVENT_HOME) { $env:OBSERVENT_HOME } else { Join-Path $env:LOCALAPPDATA "observent" }

function Invoke-Step {
    param([scriptblock]$Action, [string]$Label)
    if ($DryRun) { Write-Host "[dry-run] $Label" } else { & $Action }
}

Write-Host "observent uninstaller"
if ($DryRun) { Write-Host "  Mode: dry-run" }
Write-Host ""

# Remove OBSERVENT_HOME
if (Test-Path $ObserventHome) {
    Invoke-Step { Remove-Item -Recurse -Force $ObserventHome } "rm -rf $ObserventHome"
    Write-Host "✓ Removed $ObserventHome"
} else {
    Write-Host "  $ObserventHome not found — skipping"
}

# Remove project-scoped adapter files
foreach ($rel in @(".cursor\rules\observent.mdc", ".windsurf\rules\observent.md", ".clinerules\observent.md")) {
    $target = Join-Path $ProjectDir $rel
    if (Test-Path $target) {
        Invoke-Step { Remove-Item -Force $target } "rm $target"
        Write-Host "✓ Removed $target"
    }
}

# Remove OBSERVENT_HOME from user environment
if (-not $DryRun) {
    [System.Environment]::SetEnvironmentVariable("OBSERVENT_HOME", $null, "User")
    Write-Host "✓ Removed OBSERVENT_HOME from user environment"
}

Write-Host ""
Write-Host "observent uninstalled."
Write-Host "Note: Claude Code plugin and Gemini extension must be removed via their own CLIs:"
Write-Host "  claude plugin remove observent"
Write-Host "  gemini extensions uninstall observent"
