[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
$environmentPath = Join-Path $projectRoot ".env"

if (-not (Test-Path -LiteralPath $environmentPath)) {
    throw ".env does not exist. Run initialize-production.ps1 first."
}

$settings = @{}
Get-Content -LiteralPath $environmentPath | ForEach-Object {
    if ($_ -match "^(?<name>[A-Z][A-Z0-9_]*)=(?<value>.*)$") {
        $settings[$Matches.name] = $Matches.value
    }
}

$user = $settings["POSTGRES_USER"]
$password = $settings["POSTGRES_PASSWORD"]
if ($user -notmatch "^[a-z_][a-z0-9_]*$" -or $password -notmatch "^[a-f0-9]{64}$") {
    throw "Production PostgreSQL credentials are missing or malformed."
}

$sql = "ALTER ROLE `"$user`" WITH PASSWORD '$password';"
$composePath = Join-Path $projectRoot "compose.production.yaml"
Push-Location $projectRoot
try {
    $sql | docker compose --env-file $environmentPath -f $composePath exec -T db psql -v ON_ERROR_STOP=1 -U $user -d postgres | Out-Null
    if ($LASTEXITCODE -ne 0) {
        throw "PostgreSQL password rotation failed."
    }
}
finally {
    Pop-Location
}

Write-Output "Rotated the Chores PostgreSQL role password without printing it."
