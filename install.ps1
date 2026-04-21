# mentat Windows installer
# Usage:
#   Fresh install from GitHub:  irm https://raw.githubusercontent.com/nty203/mentat/master/install.ps1 | iex
#   Install from local repo:    .\install.ps1 -Local

param(
    [switch]$Local,
    [string]$InstallDir = "$env:LOCALAPPDATA\mentat",
    [string]$BinDir = "$env:USERPROFILE\.local\bin"
)

$ErrorActionPreference = "Stop"
$REPO = "nty203/mentat"
$SCRIPT_DIR = if ($MyInvocation.MyCommand.Path) { Split-Path -Parent $MyInvocation.MyCommand.Path } else { $PWD.Path }

Write-Host "mentat installer" -ForegroundColor Cyan
Write-Host ""

# ── Step 1: uv ────────────────────────────────────────────────────────────────
function Find-Uv {
    $uv = Get-Command uv -ErrorAction SilentlyContinue
    if ($uv) { return $uv.Source }
    $candidates = @(
        "$env:LOCALAPPDATA\Programs\uv\uv.exe",
        "$env:USERPROFILE\.cargo\bin\uv.exe",
        "$env:USERPROFILE\.local\bin\uv.exe"
    )
    # also search winget install location (dynamic path)
    Get-ChildItem "$env:LOCALAPPDATA\Microsoft\WinGet\Packages\astral-sh.uv_*\uv.exe" -ErrorAction SilentlyContinue |
        Select-Object -First 1 | ForEach-Object { $candidates += $_.FullName }
    foreach ($c in $candidates) {
        if (Test-Path $c) { return $c }
    }
    return $null
}

$uv = Find-Uv
if (-not $uv) {
    Write-Host "[1/5] Installing uv..." -ForegroundColor Blue
    try {
        winget install --id astral-sh.uv -e --accept-package-agreements --accept-source-agreements --silent
        $env:PATH = [System.Environment]::GetEnvironmentVariable("PATH","Machine") + ";" +
                    [System.Environment]::GetEnvironmentVariable("PATH","User")
        $uv = Find-Uv
    } catch {}
}

if (-not $uv) {
    Write-Host "  uv not found. Installing via PowerShell..." -ForegroundColor Yellow
    $uvInstaller = "$env:TEMP\uv-installer.ps1"
    Invoke-WebRequest "https://astral.sh/uv/install.ps1" -OutFile $uvInstaller
    & powershell -ExecutionPolicy Bypass -File $uvInstaller
    $env:PATH = "$env:USERPROFILE\.cargo\bin;" + $env:PATH
    $uv = Find-Uv
}

if (-not $uv) {
    Write-Host "Error: uv installation failed. Install manually: https://docs.astral.sh/uv/" -ForegroundColor Red
    exit 1
}
Write-Host "[1/5] uv found." -ForegroundColor Green

# ── git 체크 ──────────────────────────────────────────────────────────────────
if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    Write-Host ""
    Write-Host "Error: git not found." -ForegroundColor Red
    Write-Host "  Fix: Install git from https://git-scm.com then re-run this installer."
    exit 1
}

# ── Step 2: Python 3.12 ───────────────────────────────────────────────────────
Write-Host "[2/5] Ensuring Python 3.12..." -ForegroundColor Blue
$prevPref = $ErrorActionPreference
$ErrorActionPreference = "Continue"
& $uv python install 3.12 2>&1 | Where-Object { $_ -notmatch "^$" } | Out-Null
$ErrorActionPreference = $prevPref
Write-Host "[2/5] Python 3.12 ready." -ForegroundColor Green

# ── Step 3: Clone or update ───────────────────────────────────────────────────
Write-Host "[3/5] Setting up repo..." -ForegroundColor Blue
if ($Local) {
    $InstallDir = $SCRIPT_DIR
    Write-Host "  Using local directory: $InstallDir" -ForegroundColor Cyan
} elseif (Test-Path "$InstallDir\.git") {
    Write-Host "  Updating existing install at $InstallDir..."
    & git -C $InstallDir fetch --depth 1 origin
    $result = & git -C $InstallDir reset --hard origin/master 2>&1
    if ($LASTEXITCODE -ne 0) {
        & git -C $InstallDir reset --hard origin/main
    }
} else {
    Write-Host "  Cloning to $InstallDir..."
    New-Item -ItemType Directory -Force -Path (Split-Path $InstallDir) | Out-Null
    & git clone --depth 1 "https://github.com/$REPO.git" $InstallDir
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Error: git clone failed." -ForegroundColor Red
        exit 1
    }
}
Write-Host "[3/5] Repo ready." -ForegroundColor Green

# ── Step 4: uv sync ───────────────────────────────────────────────────────────
Write-Host "[4/5] Installing dependencies..." -ForegroundColor Blue
Push-Location $InstallDir
try {
    & $uv sync --python 3.12
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Error: uv sync failed." -ForegroundColor Red
        exit 1
    }
} finally {
    Pop-Location
}
Write-Host "[4/5] Dependencies installed." -ForegroundColor Green

# ── Step 5: mentat.cmd wrapper ────────────────────────────────────────────────
Write-Host "[5/5] Creating mentat command..." -ForegroundColor Blue
New-Item -ItemType Directory -Force -Path $BinDir | Out-Null

$wrapper = @"
@echo off
chcp 65001 > nul
set MENTAT_INSTALL_DIR=$InstallDir
"$InstallDir\.venv\Scripts\python.exe" -m mentat.cli.main %*
"@
Set-Content -Path "$BinDir\mentat.cmd" -Value $wrapper -Encoding ASCII

$psWrapper = @"
`$env:MENTAT_INSTALL_DIR = "$InstallDir"
& "$InstallDir\.venv\Scripts\python.exe" -m mentat.cli.main @args
"@
Set-Content -Path "$BinDir\mentat.ps1" -Value $psWrapper -Encoding UTF8

Write-Host "[5/5] Created $BinDir\mentat.cmd" -ForegroundColor Green

# ── PATH: registry (permanent) ────────────────────────────────────────────────
$userPath = [System.Environment]::GetEnvironmentVariable("PATH", "User")
if ($userPath -notlike "*$BinDir*") {
    [System.Environment]::SetEnvironmentVariable("PATH", "$BinDir;$userPath", "User")
}
# Apply to current session immediately
if ($env:PATH -notlike "*$BinDir*") {
    $env:PATH = "$BinDir;$env:PATH"
}

# ── PATH: PowerShell profile (persists across sessions) ──────────────────────
$profileLine = "`$env:PATH = `"$BinDir;`$env:PATH`"  # mentat"
$needsProfile = $true
if (Test-Path $PROFILE) {
    $content = Get-Content $PROFILE -Raw -ErrorAction SilentlyContinue
    if ($content -like "*$BinDir*") { $needsProfile = $false }
}
if ($needsProfile) {
    $profileDir = Split-Path $PROFILE
    if (-not (Test-Path $profileDir)) { New-Item -ItemType Directory -Force -Path $profileDir | Out-Null }
    if (-not (Test-Path $PROFILE)) { New-Item -ItemType File -Path $PROFILE -Force | Out-Null }
    Add-Content $PROFILE "`n$profileLine"
}

# ── Broadcast PATH change to running processes ────────────────────────────────
try {
    Add-Type -TypeDefinition @'
using System;
using System.Runtime.InteropServices;
public class WinEnv {
    [DllImport("user32.dll", SetLastError=true, CharSet=CharSet.Auto)]
    public static extern IntPtr SendMessageTimeout(
        IntPtr hWnd, uint Msg, UIntPtr wParam, string lParam,
        uint fuFlags, uint uTimeout, out UIntPtr lpdwResult);
}
'@ -ErrorAction SilentlyContinue
    $result = [UIntPtr]::Zero
    [WinEnv]::SendMessageTimeout([IntPtr]0xFFFF, 0x001A, [UIntPtr]::Zero, "Environment", 2, 1000, [ref]$result) | Out-Null
} catch {}

Write-Host ""
Write-Host "mentat installed successfully!" -ForegroundColor Green
Write-Host ""
Write-Host "Get started (works in this terminal right now):"
Write-Host "  mentat bootstrap       # scan projects"
Write-Host "  mentat serve           # open web UI"
Write-Host "  mentat update          # update to latest version"
