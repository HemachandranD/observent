# bigboss uninstaller — removes BIGBOSS_HOME and project-scoped adapter files.
# Usage: .\uninstall.ps1 [-ProjectDir <path>] [-DryRun]
[CmdletBinding()]
param(
    [string]$ProjectDir = $PWD.Path,
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"
$BigbossHome = if ($env:BIGBOSS_HOME) { $env:BIGBOSS_HOME } else { Join-Path $env:LOCALAPPDATA "bigboss" }

function Invoke-Step {
    param([scriptblock]$Action, [string]$Label)
    if ($DryRun) { Write-Host "[dry-run] $Label" } else { & $Action }
}

Write-Host "bigboss uninstaller"
if ($DryRun) { Write-Host "  Mode: dry-run" }
Write-Host ""

# Remove BIGBOSS_HOME
if (Test-Path $BigbossHome) {
    Invoke-Step { Remove-Item -Recurse -Force $BigbossHome } "rm -rf $BigbossHome"
    Write-Host "✓ Removed $BigbossHome"
} else {
    Write-Host "  $BigbossHome not found — skipping"
}

# Remove project-scoped adapter files
foreach ($rel in @(".cursor\rules\bigboss.mdc", ".windsurf\rules\bigboss.md", ".clinerules\bigboss.md")) {
    $target = Join-Path $ProjectDir $rel
    if (Test-Path $target) {
        Invoke-Step { Remove-Item -Force $target } "rm $target"
        Write-Host "✓ Removed $target"
    }
}

# Remove BIGBOSS_HOME from user environment
if (-not $DryRun) {
    [System.Environment]::SetEnvironmentVariable("BIGBOSS_HOME", $null, "User")
    Write-Host "✓ Removed BIGBOSS_HOME from user environment"
}

Write-Host ""
Write-Host "bigboss uninstalled."
Write-Host "Note: Claude Code plugin and Gemini extension must be removed via their own CLIs:"
Write-Host "  claude plugin remove bigboss"
Write-Host "  gemini extensions uninstall bigboss"
