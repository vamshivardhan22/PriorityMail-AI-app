$ErrorActionPreference = 'Stop'

$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

$LogDir = Join-Path $ProjectRoot 'logs'
New-Item -ItemType Directory -Path $LogDir -Force | Out-Null

$Timestamp = Get-Date -Format 'yyyy-MM-dd HH:mm:ss'
$LogPath = Join-Path $LogDir 'worker.log'

"[$Timestamp] Starting worker cycle." | Out-File -FilePath $LogPath -Append -Encoding utf8

try {
    $WorkerOutput = python worker.py --once 2>&1
    $ExitCode = $LASTEXITCODE
    $WorkerOutput | Write-Output
    $WorkerOutput | Out-File -FilePath $LogPath -Append -Encoding utf8

    if ($ExitCode -ne 0) {
        throw "worker.py exited with code $ExitCode"
    }

    "[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] Worker cycle completed." |
        Out-File -FilePath $LogPath -Append -Encoding utf8
}
catch {
    "[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] Worker cycle failed: $_" |
        Out-File -FilePath $LogPath -Append -Encoding utf8
    throw
}
