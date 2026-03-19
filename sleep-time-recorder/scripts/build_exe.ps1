param(
    [ValidateSet("OneFolder", "OneFile")]
    [string]$Mode = "OneFolder",
    [string]$PythonPath = ".\\.venv\\Scripts\\python.exe"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

if (!(Test-Path $PythonPath)) {
    throw "Python executable not found: $PythonPath"
}

Write-Host "Using python: $PythonPath"
& $PythonPath -m pip install -r requirements-dev.txt

if (Test-Path ".\\build") { Remove-Item ".\\build" -Recurse -Force }
if (Test-Path ".\\dist") { Remove-Item ".\\dist" -Recurse -Force }

$pyInstallerArgs = @(
    "--noconfirm",
    "--clean",
    "--name", "SleepTimeRecorder",
    "--windowed",
    "--add-data", "config;config",
    "--add-data", "src\\sleep_tracker\\resources\\qss;src\\sleep_tracker\\resources\\qss",
    "--add-data", "src\\sleep_tracker\\resources\\icons;src\\sleep_tracker\\resources\\icons",
    "main.py"
)

$iconPath = "src\\sleep_tracker\\resources\\icons\\app.ico"
if (Test-Path $iconPath) {
    $pyInstallerArgs = @("--icon", $iconPath) + $pyInstallerArgs
}

if ($Mode -eq "OneFile") {
    $pyInstallerArgs = @("--onefile") + $pyInstallerArgs
}

Write-Host "Running PyInstaller ($Mode)..."
& $PythonPath -m PyInstaller @pyInstallerArgs

Write-Host ""
Write-Host "Build completed."
if ($Mode -eq "OneFile") {
    Write-Host "Executable: .\\dist\\SleepTimeRecorder.exe"
} else {
    Write-Host "Executable: .\\dist\\SleepTimeRecorder\\SleepTimeRecorder.exe"
}
