# observent installer — detects installed providers and wires up each one.
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

Write-Host "observent installer"
Write-Host "  Repo:         $RepoDir"
Write-Host "  OBSERVENT_HOME: $ObserventHome"
Write-Host "  Project:      $ProjectDir"
if ($DryRun) { Write-Host "  Mode:         dry-run" }
Write-Host ""

# ── 1. Copy core skill files to OBSERVENT_HOME ──────────────────────────────────
Invoke-Step { New-Item -ItemType Directory -Force -Path $ObserventHome | Out-Null } "mkdir $ObserventHome"
Invoke-Step { Copy-Item -Recurse -Force "$RepoDir\skills\observent\*" "$ObserventHome\" } "cp skills/observent → $ObserventHome"
Write-Host "✓ Skill files → $ObserventHome"

# ── 2. Detect providers ────────────────────────────────────────────────────────
$ProviderJson = python "$RepoDir\scripts\detect_providers.py" | ConvertFrom-Json
$Installed = @()

function Is-Installed([string]$Id) {
    return $ProviderJson.providers.$Id.installed -eq $true
}

# ── 3. Claude Code ─────────────────────────────────────────────────────────────
if (Is-Installed "claude_code") {
    Write-Host "  Detected: Claude Code"
    if (-not (Get-Command claude -ErrorAction SilentlyContinue)) {
        Write-Host "    ↳ ~/.claude found but 'claude' not on PATH — skipping plugin install"
    } else {
        $alreadyInstalled = $false
        try { $alreadyInstalled = (claude plugin list 2>$null) -match "observent" } catch {}
        if ($alreadyInstalled) {
            Write-Host "    ↳ already installed — skipping"
        } else {
            Invoke-Step { claude plugin install $RepoDir } "claude plugin install $RepoDir"
            Write-Host "    ✓ Claude Code plugin installed"
        }
        $Installed += "Claude Code"
    }
}

# ── 4. Gemini CLI ──────────────────────────────────────────────────────────────
if (Is-Installed "gemini") {
    Write-Host "  Detected: Gemini CLI"
    if (-not (Get-Command gemini -ErrorAction SilentlyContinue)) {
        Write-Host "    ↳ ~/.gemini found but 'gemini' not on PATH — skipping extension install"
    } else {
        Invoke-Step { gemini extensions install $RepoDir } "gemini extensions install $RepoDir"
        Write-Host "    ✓ Gemini extension installed"
        $Installed += "Gemini CLI"
    }
}

# ── 5. OpenAI Codex CLI ───────────────────────────────────────────────────────
if (Is-Installed "codex") {
    Write-Host "  Detected: OpenAI Codex CLI"
    $CodexExt = Join-Path $env:USERPROFILE ".codex\extensions\observent"
    Invoke-Step { New-Item -ItemType Directory -Force -Path $CodexExt | Out-Null } "mkdir $CodexExt"
    Invoke-Step { Copy-Item -Recurse -Force "$RepoDir\.codex\*" "$CodexExt\" } "cp .codex → $CodexExt"
    Write-Host "    ✓ Codex extension → $CodexExt"
    $Installed += "Codex CLI"
}

# ── 6. Project-scoped adapters ─────────────────────────────────────────────────
function Install-Rule([string]$Provider, [string]$Src, [string]$DstDir, [string]$DstFile) {
    $dstPath = Join-Path $ProjectDir $DstDir
    Invoke-Step { New-Item -ItemType Directory -Force -Path $dstPath | Out-Null } "mkdir $dstPath"
    $content = Get-Content "$RepoDir\$Src" -Raw
    $content = $content -replace '\$\{OBSERVENT_HOME\}', $ObserventHome
    $outFile = Join-Path $dstPath $DstFile
    Invoke-Step { Set-Content -Path $outFile -Value $content -Encoding utf8 } "write $outFile"
    Write-Host "    ✓ $Provider rule → $outFile"
    $script:Installed += $Provider
}

if (Is-Installed "cursor") {
    Write-Host "  Detected: Cursor"
    Install-Rule "Cursor" ".cursor\rules\observent.mdc" ".cursor\rules" "observent.mdc"
}

if (Is-Installed "windsurf") {
    Write-Host "  Detected: Windsurf"
    Install-Rule "Windsurf" ".windsurf\rules\observent.md" ".windsurf\rules" "observent.md"
}

if (Is-Installed "cline") {
    Write-Host "  Detected: Cline"
    Install-Rule "Cline" ".clinerules\observent.md" ".clinerules" "observent.md"
}

# ── 7. Persist OBSERVENT_HOME in user environment ────────────────────────────────
if (-not $DryRun) {
    [System.Environment]::SetEnvironmentVariable("OBSERVENT_HOME", $ObserventHome, "User")
    Write-Host "  ✓ OBSERVENT_HOME set in user environment (restart terminal to apply)"
}

# ── 8. Summary ─────────────────────────────────────────────────────────────────
Write-Host ""
if ($Installed.Count -gt 0) {
    Write-Host "observent installed for: $($Installed -join ', ')"
    Write-Host "  Scripts: $ObserventHome\scripts\"
} else {
    Write-Host "No supported providers were detected."
    Write-Host "Install Claude Code, Gemini CLI, Codex CLI, Cursor, Windsurf, or Cline, then re-run."
}
