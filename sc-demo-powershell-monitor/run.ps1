. "$PSScriptRoot\sdk\heartbeat.ps1"
$logFile = Join-Path $PSScriptRoot "logs\app.log"
if (!(Test-Path (Split-Path $logFile))) { New-Item -ItemType Directory -Path (Split-Path $logFile) | Out-Null }
while ($true) {
  Write-Heartbeat -RootDir $PSScriptRoot -Status "alive"
  Add-Content -Path $logFile -Value ("{0} [INFO] powershell demo alive" -f [DateTime]::UtcNow.ToString("o"))
  Write-Output "powershell demo alive"
  Start-Sleep -Seconds 15
}
