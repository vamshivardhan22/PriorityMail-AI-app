param(
    [string]$TaskName = 'PriorityMail AI Worker',
    [int]$IntervalMinutes = 5
)

$ErrorActionPreference = 'Stop'

if ($IntervalMinutes -lt 1) {
    throw 'IntervalMinutes must be 1 or greater.'
}

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$WorkerScript = Join-Path $PSScriptRoot 'run_worker_once.ps1'

if (-not (Test-Path $WorkerScript)) {
    throw "Worker wrapper not found: $WorkerScript"
}

$Action = New-ScheduledTaskAction `
    -Execute 'powershell.exe' `
    -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$WorkerScript`"" `
    -WorkingDirectory $ProjectRoot

$Trigger = New-ScheduledTaskTrigger `
    -Once `
    -At (Get-Date).AddMinutes(1) `
    -RepetitionInterval (New-TimeSpan -Minutes $IntervalMinutes) `
    -RepetitionDuration (New-TimeSpan -Days 3650)

$Settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable

Register-ScheduledTask `
    -TaskName $TaskName `
    -Action $Action `
    -Trigger $Trigger `
    -Settings $Settings `
    -Description 'Runs one PriorityMail AI Gmail automation cycle on a recurring schedule.' `
    -Force

Write-Host "Registered '$TaskName' to run every $IntervalMinutes minute(s)."
