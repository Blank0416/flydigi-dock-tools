<#
.SYNOPSIS
  Log every "surprise removal" of a Flydigi device (vendor id 37D7), with the
  gap since the previous one.

.DESCRIPTION
  Windows writes one Kernel-PnP event 1010 per surprise removal, which is what a
  Flydigi pad does every time it sleeps. Use this to prove a fix worked: run it
  before and after, and compare.

.EXAMPLE
  powershell -ExecutionPolicy Bypass -File watch_drops.ps1 -Minutes 30
#>
param(
    [string]$Log = "drops.log",
    [double]$Minutes = 30.0,
    [int]$PollSeconds = 20
)

$end = (Get-Date).AddMinutes($Minutes)
$header = "=== Flydigi surprise removals, watching until $($end.ToString('HH:mm:ss')) ==="
$header
Add-Content -Path $Log -Value $header -Encoding UTF8

$since = Get-Date
$last = $null
$count = 0

while ((Get-Date) -lt $end) {
    $events = Get-WinEvent -LogName 'Microsoft-Windows-Kernel-PnP/Device Management' -MaxEvents 300 -ErrorAction SilentlyContinue |
        Where-Object { $_.Id -eq 1010 -and $_.Message -match 'VID_37D7' -and $_.TimeCreated -gt $since } |
        Sort-Object TimeCreated

    foreach ($e in $events) {
        if ($last) {
            $gap = [math]::Round(($e.TimeCreated - $last).TotalSeconds)
        } else {
            $gap = 0
        }
        $line = "$($e.TimeCreated.ToString('yyyy-MM-dd HH:mm:ss'))  +$($gap)s"
        $line
        Add-Content -Path $Log -Value $line -Encoding UTF8
        $last = $e.TimeCreated
        $since = $e.TimeCreated
        $count++
    }
    Start-Sleep -Seconds $PollSeconds
}

$footer = "=== done: $count removal(s) in $Minutes minute(s) ==="
$footer
Add-Content -Path $Log -Value $footer -Encoding UTF8
