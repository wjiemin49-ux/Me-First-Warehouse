function Write-Heartbeat {
  param(
    [string]$RootDir,
    [string]$Status = "alive"
  )
  $runtimeDir = Join-Path $RootDir "runtime"
  $heartbeat = Join-Path $runtimeDir "heartbeat.json"
  if (!(Test-Path $runtimeDir)) { New-Item -ItemType Directory -Path $runtimeDir | Out-Null }
  $payload = @{
    timestamp = [DateTime]::UtcNow.ToString("o")
    status = $Status
  } | ConvertTo-Json
  Set-Content -Path $heartbeat -Value $payload -Encoding UTF8
}
