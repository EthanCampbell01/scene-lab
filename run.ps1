param(
  [Parameter(Mandatory=$true)][string]$Brief,
  [string]$Variant = "default",
  [ValidateSet("ollama","openrouter")][string]$Provider = "ollama",
  [int]$Port = 5173
)

$ErrorActionPreference = "Stop"

$sceneKit = Join-Path $PSScriptRoot "scene-kit"

Write-Host "Generating scene and launching previewer..." -ForegroundColor Cyan

python (Join-Path $sceneKit "pipeline.py") `
  --brief "$Brief" `
  --variant "$Variant" `
  --provider "$Provider" `
  --serve `
  --port $Port
