param(
    [string]$TaskName = "MacroHub Daily Data Update",
    [string]$Time = "02:00",
    [switch]$ForceRefresh,
    [switch]$SkipBenchmark
)

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectDir = Split-Path -Parent $ScriptDir
$UpdateScript = Join-Path $ScriptDir "scheduled_update.py"

$ArgsList = @()
$ArgsList += "`"$UpdateScript`""
if ($ForceRefresh) {
    $ArgsList += "--force-refresh"
}
if ($SkipBenchmark) {
    $ArgsList += "--skip-benchmark"
}

$Action = New-ScheduledTaskAction `
    -Execute "python" `
    -Argument ($ArgsList -join " ") `
    -WorkingDirectory $ProjectDir

$Trigger = New-ScheduledTaskTrigger -Daily -At $Time
$Settings = New-ScheduledTaskSettingsSet `
    -StartWhenAvailable `
    -AllowStartIfOnBatteries `
    -ExecutionTimeLimit (New-TimeSpan -Hours 2)

Register-ScheduledTask `
    -TaskName $TaskName `
    -Action $Action `
    -Trigger $Trigger `
    -Settings $Settings `
    -Description "Refresh MacroHub macro data, quality reports and performance reports." `
    -Force

Write-Host "Registered task: $TaskName"
Write-Host "Project: $ProjectDir"
Write-Host "Schedule: daily at $Time"
