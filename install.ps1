# observent installer - detects installed providers and wires up each one.
# Usage: .\install.ps1 [-ProjectDir <path>] [-DryRun]
[CmdletBinding()]
param(
    [string]$ProjectDir = $PWD.Path,
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"
$RepoDir = $PSScriptRoot
$ObserventHome = if ($env:OBSERVENT_HOME) { $env:OBSERVENT_HOME } else { Join-Path $env:LOCALAPPDATA "observent" }

function Invoke-Step {
    param([scriptblock]$Action, [string]$Label)
    if ($DryRun) { Write-Host "[dry-run] $Label" } else { & $Action }
}

# Write the canonical cross-tool AGENTS.md into the project (substituting
# ${OBSERVENT_HOME}). Idempotent - several providers read AGENTS.md natively,
# so the first one to need it writes it and the rest are no-ops.
$script:AgentsWritten = $false
function Write-AgentsMd {
    if ($script:AgentsWritten) { Write-Host "    -> AGENTS.md already written this run"; return }
    $content = (Get-Content "$RepoDir\AGENTS.md" -Raw) -replace '\$\{OBSERVENT_HOME\}', $ObserventHome
    $out = Join-Path $ProjectDir "AGENTS.md"
    Invoke-Step { Set-Content -Path $out -Value $content -Encoding utf8 } "write $out"
    Write-Host "    [ok] AGENTS.md -> $out"
    $script:AgentsWritten = $true
}

Write-Host "observent installer"
Write-Host "  Repo:         $RepoDir"
Write-Host "  OBSERVENT_HOME: $ObserventHome"
Write-Host "  Project:      $ProjectDir"
if ($DryRun) { Write-Host "  Mode:         dry-run" }
Write-Host ""

# --- 1. Copy core skill files to OBSERVENT_HOME ---
Invoke-Step { New-Item -ItemType Directory -Force -Path $ObserventHome | Out-Null } "mkdir $ObserventHome"
Invoke-Step { Copy-Item -Recurse -Force "$RepoDir\skills\observent\*" "$ObserventHome\" } "cp skills/observent -> $ObserventHome"
Write-Host "[ok] Skill files -> $ObserventHome"

# --- 2. Detect providers ---
$ProviderJson = python "$RepoDir\scripts\detect_providers.py" | ConvertFrom-Json
$Installed = @()

function Is-Installed([string]$Id) {
    return $ProviderJson.providers.$Id.installed -eq $true
}

# --- 3. Claude Code ---
if (Is-Installed "claude_code") {
    Write-Host "  Detected: Claude Code"
    if (-not (Get-Command claude -ErrorAction SilentlyContinue)) {
        Write-Host "    -> ~/.claude found but 'claude' not on PATH - skipping plugin install"
    } else {
        $alreadyInstalled = $false
        try { $alreadyInstalled = (claude plugin list 2>$null) -match "observent" } catch {}
        if ($alreadyInstalled) {
            Write-Host "    -> already installed - skipping"
        } elseif ($DryRun) {
            Write-Host "[dry-run] claude plugin install HemachandranD/observent (fallback: claude plugin install $RepoDir)"
        } else {
            # Prefer the marketplace form (self-contained, supports `claude
            # plugin update`, survives deleting this clone). Fall back to the
            # local repo path only if it fails - e.g. offline.
            $marketplaceOk = $false
            try { claude plugin install HemachandranD/observent; $marketplaceOk = $? } catch { $marketplaceOk = $false }
            if ($marketplaceOk) {
                Write-Host "    [ok] Claude Code plugin installed (marketplace)"
            } else {
                Write-Host "    -> marketplace install failed - falling back to local path"
                claude plugin install $RepoDir
                Write-Host "    [ok] Claude Code plugin installed (local path)"
            }
        }
        $Installed += "Claude Code"
    }
}

# --- 4. Google Antigravity (CLI + IDE) ---
if (Is-Installed "antigravity") {
    Write-Host "  Detected: Google Antigravity"
    # AGENTS.md in the project is read by both the Antigravity CLI and the
    # desktop IDE.
    Write-AgentsMd
    if (Get-Command antigravity -ErrorAction SilentlyContinue) {
        Invoke-Step { antigravity extensions install $RepoDir } "antigravity extensions install $RepoDir"
        Write-Host "    [ok] Antigravity extension installed"
    } else {
        Write-Host "    -> 'antigravity' not on PATH - skipped extension install (AGENTS.md still applies)"
    }
    $Installed += "Antigravity"
}

# --- 5. Providers that read the project-root AGENTS.md natively ---
# Codex (CLI + IDE), Windsurf, and GitHub Copilot (IDE + CLI) all consume the
# project-root AGENTS.md directly - no per-tool file. One helper, one AGENTS.md
# (written once via the idempotent Write-AgentsMd).
function Add-AgentsNative([string]$Id, [string]$Label) {
    if (Is-Installed $Id) {
        Write-Host "  Detected: $Label"
        Write-AgentsMd
        $script:Installed += $Label
    }
}
Add-AgentsNative "codex"    "Codex (CLI + IDE)"
Add-AgentsNative "windsurf" "Windsurf"
Add-AgentsNative "copilot"  "GitHub Copilot"

# --- 6. Tools needing their own scoped rule file (Cursor / Cline) ---
# Thin pointers to ${OBSERVENT_HOME}/SKILL.md, not duplicated bodies:
#   * Cursor - keeps its `globs: **/*.py` auto-attach scoping.
#   * Cline  - does not auto-read project-root AGENTS.md, so it needs a rule file.
function Install-Rule([string]$Provider, [string]$Src, [string]$DstDir, [string]$DstFile) {
    $dstPath = Join-Path $ProjectDir $DstDir
    Invoke-Step { New-Item -ItemType Directory -Force -Path $dstPath | Out-Null } "mkdir $dstPath"
    $content = Get-Content "$RepoDir\$Src" -Raw
    $content = $content -replace '\$\{OBSERVENT_HOME\}', $ObserventHome
    $outFile = Join-Path $dstPath $DstFile
    Invoke-Step { Set-Content -Path $outFile -Value $content -Encoding utf8 } "write $outFile"
    Write-Host "    [ok] $Provider rule -> $outFile"
    $script:Installed += $Provider
}

if (Is-Installed "cursor") {
    Write-Host "  Detected: Cursor"
    Install-Rule "Cursor" ".cursor\rules\observent.mdc" ".cursor\rules" "observent.mdc"
}

if (Is-Installed "cline") {
    Write-Host "  Detected: Cline"
    Install-Rule "Cline" ".clinerules\observent.md" ".clinerules" "observent.md"
}

# --- 7. Persist OBSERVENT_HOME in user environment ---
if (-not $DryRun) {
    [System.Environment]::SetEnvironmentVariable("OBSERVENT_HOME", $ObserventHome, "User")
    Write-Host "  [ok] OBSERVENT_HOME set in user environment (restart terminal to apply)"
}

# --- 8. Summary ---
Write-Host ""
if ($Installed.Count -gt 0) {
    Write-Host "observent installed for: $($Installed -join ', ')"
    Write-Host "  Scripts: $ObserventHome\scripts\"
} else {
    Write-Host "No supported providers were detected."
    Write-Host "Install Claude Code, Antigravity, GitHub Copilot, Codex, Cursor, Windsurf, or Cline, then re-run."
}
