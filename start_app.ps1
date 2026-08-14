$ErrorActionPreference = "Stop"

function Test-CommandExists {
  param([string]$CommandName)

  return $null -ne (Get-Command $CommandName -ErrorAction SilentlyContinue)
}

if (-not (Test-CommandExists "uv")) {
  Write-Error "Missing required command: uv"
}

if (-not (Test-CommandExists "pnpm")) {
  Write-Error "Missing required command: pnpm"
}

$repoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path

# Read backend .env.local LIVEKIT_URL if present
$envFile = "$repoRoot\backend\.env.local"
$isLocalLivekit = $false

if (Test-Path $envFile) {
  $envContent = Get-Content $envFile
  foreach ($line in $envContent) {
    if ($line -like "LIVEKIT_URL=*127.0.0.1*" -or $line -like "LIVEKIT_URL=*localhost*") {
      $isLocalLivekit = $true
    }
  }
}

if ($isLocalLivekit) {
  if (Test-Path "$repoRoot\livekit-server.exe") {
    Write-Host "Starting local LiveKit server on port 7880..."
    Start-Process powershell -ArgumentList "-NoExit", "-Command", "Set-Location '$repoRoot'; .\livekit-server.exe --dev"
  } elseif (Test-CommandExists "livekit-server") {
    Write-Host "Starting local LiveKit server..."
    Start-Process powershell -ArgumentList "-NoExit", "-Command", "Set-Location '$repoRoot'; livekit-server --dev"
  }
} else {
  Write-Host "Using configured LiveKit Cloud endpoint from .env.local"
}

Write-Host "Starting FinVoice Python Backend Agent (Stable Mode)..."
Start-Process powershell -ArgumentList "-NoExit", "-Command", "Set-Location '$repoRoot\backend'; uv run python src/agent.py start"

Write-Host "Starting FinVoice Next.js Frontend..."
Start-Process powershell -ArgumentList "-NoExit", "-Command", "Set-Location '$repoRoot\frontend'; pnpm dev"

Write-Host "=========================================================================="
Write-Host "FinVoice Application Started Successfully!"
Write-Host "Main Voice Agent Dashboard : http://localhost:3000"
Write-Host "Call Analytics Dashboard   : http://localhost:3000/analytics"
Write-Host "Human Escalations          : http://localhost:3000/escalations"
Write-Host "=========================================================================="
