param(
    [Parameter(Mandatory = $true)]
    [string]$ProjectRoot,

    [Parameter(Mandatory = $false)]
    [string]$PythonExecutable = "python"
)

$resolvedRoot = Resolve-Path $ProjectRoot
Push-Location $resolvedRoot
try {
    & $PythonExecutable -m self_growth_daily_briefing --project-root $resolvedRoot run --send
    exit $LASTEXITCODE
}
finally {
    Pop-Location
}
