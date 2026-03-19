param(
    [Parameter(Mandatory = $true, Position = 0)]
    [ValidateSet("preview", "run", "install-task", "list-sources", "send-test")]
    [string]$Action
)

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..")

switch ($Action) {
    "preview" {
        & python -m self_growth_daily_briefing --project-root $repoRoot preview
    }
    "run" {
        & python -m self_growth_daily_briefing --project-root $repoRoot run --send
    }
    "install-task" {
        & python -m self_growth_daily_briefing --project-root $repoRoot install-task --time 09:00
    }
    "list-sources" {
        & python -m self_growth_daily_briefing --project-root $repoRoot list-sources
    }
    "send-test" {
        & python -m self_growth_daily_briefing --project-root $repoRoot send-test
    }
}

exit $LASTEXITCODE
