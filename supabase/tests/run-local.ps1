param(
    [string]$PostgresBin = 'C:\Program Files\PostgreSQL\18\bin',
    [int]$Port = 55439
)

$ErrorActionPreference = 'Stop'
$clusterPath = Join-Path ([System.IO.Path]::GetTempPath()) ('akses-db-test-' + [guid]::NewGuid())
$started = $false

function Invoke-PostgresTool([string]$Name, [string[]]$Arguments) {
    & (Join-Path $PostgresBin ($Name + '.exe')) @Arguments
    if ($LASTEXITCODE -ne 0) { throw "$Name failed with exit code $LASTEXITCODE" }
}

try {
    Invoke-PostgresTool 'initdb' @('-D', $clusterPath, '-U', 'postgres', '-A', 'trust', '--no-locale', '--no-sync', '-E', 'UTF8')
    Invoke-PostgresTool 'pg_ctl' @('-D', $clusterPath, '-l', (Join-Path $clusterPath 'server.log'), '-o', "-h 127.0.0.1 -p $Port", '-w', 'start')
    $started = $true
    $connectionArgs = @('-X', '-h', '127.0.0.1', '-p', "$Port", '-U', 'postgres', '-d', 'postgres', '-v', 'ON_ERROR_STOP=1')
    Invoke-PostgresTool 'psql' ($connectionArgs + @('-f', (Join-Path $PSScriptRoot 'roles.sql')))
    foreach ($migration in (Get-ChildItem (Join-Path $PSScriptRoot '../migrations/*.sql') | Sort-Object Name)) {
        Invoke-PostgresTool 'psql' ($connectionArgs + @('--single-transaction', '-f', $migration.FullName))
    }
    foreach ($checkFile in @('building_foundation.sql', 'place_evidence.sql', 'barrier_reports.sql', 'report_votes.sql', 'clearance_observations.sql', 'clearance_votes.sql', 'report_history.sql', 'contributor_state.sql', 'community_read_views.sql', 'place_detail_records.sql', 'community_records.sql')) {
        Invoke-PostgresTool 'psql' ($connectionArgs + @('-f', (Join-Path $PSScriptRoot $checkFile)))
    }
    $seedPython = Join-Path $PSScriptRoot '../../backend/.venv/Scripts/python.exe'
    & $seedPython (Join-Path $PSScriptRoot '../../seed/tests/test_import_places.py')
    if ($LASTEXITCODE -ne 0) { throw 'Seed validation tests failed' }
    & $seedPython (Join-Path $PSScriptRoot '../../seed/tests/verify_postgres.py') --pg-bin $PostgresBin --port $Port
    if ($LASTEXITCODE -ne 0) { throw 'Seed PostgreSQL integration checks failed' }
    & $seedPython (Join-Path $PSScriptRoot 'verify_place_records.py') --pg-bin $PostgresBin --port $Port
    if ($LASTEXITCODE -ne 0) { throw 'Place record backend integration checks failed' }
    & $seedPython (Join-Path $PSScriptRoot 'verify_community_records.py') --pg-bin $PostgresBin --port $Port
    if ($LASTEXITCODE -ne 0) { throw 'Community record backend integration checks failed' }
} finally {
    if ($started) {
        Invoke-PostgresTool 'pg_ctl' @('-D', $clusterPath, '-m', 'fast', '-w', 'stop')
    }
    # Retain the unique temporary directory for failure diagnosis. No shared DB is used.
    Write-Host "Disposable cluster files: $clusterPath"
}
