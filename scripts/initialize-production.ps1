[CmdletBinding()]
param(
    [Parameter(Mandatory)]
    [ValidatePattern("^https://[A-Za-z0-9.-]+(?::[0-9]+)?$")]
    [string]$AllowedOrigin,

    [switch]$Force
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
$environmentPath = Join-Path $projectRoot ".env"

if ((Test-Path -LiteralPath $environmentPath) -and -not $Force) {
    throw ".env already exists. Refusing to overwrite production secrets without -Force."
}

$clipboard = Get-Clipboard -Raw
$tokenMatch = [regex]::Match(
    $clipboard,
    "(?:--token\s+|service\s+install\s+)(?<token>eyJ[A-Za-z0-9._-]+)"
)
if (-not $tokenMatch.Success) {
    throw "The clipboard does not contain a Cloudflare Tunnel connector command."
}

$passwordBytes = New-Object byte[] 32
[Security.Cryptography.RandomNumberGenerator]::Fill($passwordBytes)
$postgresPassword = [Convert]::ToHexString($passwordBytes).ToLowerInvariant()

$secretBytes = New-Object byte[] 32
[Security.Cryptography.RandomNumberGenerator]::Fill($secretBytes)
$sessionSecret = [Convert]::ToHexString($secretBytes).ToLowerInvariant()

do {
    $parentPin = [Security.Cryptography.RandomNumberGenerator]::GetInt32(1000, 10000).ToString()
} while ($parentPin -eq "2468")

$lines = @(
    "APP_NAME=Kids Chores API"
    "APP_ENV=production"
    "API_DOCS_ENABLED=false"
    "POSTGRES_USER=kids_chores"
    "POSTGRES_PASSWORD=$postgresPassword"
    "POSTGRES_DB=kids_chores"
    "DATABASE_URL=postgresql+psycopg://kids_chores:$postgresPassword@localhost:5433/kids_chores"
    "HOUSEHOLD_TIMEZONE=America/New_York"
    "PARENT_PIN=$parentPin"
    "SESSION_SECRET=$sessionSecret"
    "PARENT_SESSION_SECONDS=43200"
    "ALLOWED_ORIGIN=$AllowedOrigin"
    "CLOUDFLARE_TUNNEL_TOKEN=$($tokenMatch.Groups['token'].Value)"
)

Set-Content -LiteralPath $environmentPath -Value $lines -Encoding utf8NoBOM
Write-Output "Created ignored production .env with generated database, session, and parent credentials."
Write-Output "The generated parent PIN is stored only in .env and was not printed."
