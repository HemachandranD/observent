# observent uninstaller - removes OBSERVENT_HOME and project-scoped adapter files.
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
    Write-Host "[ok] Removed $ObserventHome"
} else {
    Write-Host "  $ObserventHome not found - skipping"
}

# Remove the retired Codex CLI extension dir from older installs (Codex now
# reads the project-root AGENTS.md directly).
$CodexExt = Join-Path $env:USERPROFILE ".codex\extensions\observent"
if (Test-Path $CodexExt) {
    Invoke-Step { Remove-Item -Recurse -Force $CodexExt } "rm -rf $CodexExt"
    Write-Host "[ok] Removed $CodexExt"
}

# Remove project-scoped adapter files (the .windsurf / .github entries clean up
# artifacts written by older installs; current installs use AGENTS.md for those).
foreach ($rel in @(".cursor\rules\observent.mdc", ".windsurf\rules\observent.md", ".clinerules\observent.md", ".github\copilot-instructions.md", "AGENTS.md")) {
    $target = Join-Path $ProjectDir $rel
    if (Test-Path $target) {
        Invoke-Step { Remove-Item -Force $target } "rm $target"
        Write-Host "[ok] Removed $target"
    }
}

# Remove OBSERVENT_HOME from user environment
if (-not $DryRun) {
    [System.Environment]::SetEnvironmentVariable("OBSERVENT_HOME", $null, "User")
    Write-Host "[ok] Removed OBSERVENT_HOME from user environment"
}

Write-Host ""
Write-Host "observent uninstalled."
Write-Host "Note: Claude Code plugin and Antigravity extension must be removed via their own CLIs:"
Write-Host "  claude plugin remove observent"
Write-Host "  antigravity extensions uninstall observent"
