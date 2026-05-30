$ErrorActionPreference = 'Stop'

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$TaskName = 'PriorityMail AI Worker'
$LogPath = Join-Path $ProjectRoot 'logs\worker.log'

$Task = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue

if (-not $Task) {
    Write-Host "Scheduled task '$TaskName' is not registered."
    exit 1
}

$TaskInfo = Get-ScheduledTaskInfo -TaskName $TaskName

Write-Host "Task: $($Task.TaskName)"
Write-Host "State: $($Task.State)"
Write-Host "Last run: $($TaskInfo.LastRunTime)"
Write-Host "Last result: $($TaskInfo.LastTaskResult)"
Write-Host "Next run: $($TaskInfo.NextRunTime)"

if (Test-Path $LogPath) {
    Write-Host ''
    Write-Host "Recent worker log:"
    Get-Content $LogPath -Tail 40
}
else {
    Write-Host ''
    Write-Host "No worker log found yet at $LogPath"
}
