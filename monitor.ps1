$ErrorActionPreference = "SilentlyContinue"
$uri = "http://127.0.0.1:9010/metrics"
$log = ".\logs\monitor.log"
New-Item -ItemType Directory -Path .\logs -Force | Out-Null

try {
  $m = Invoke-RestMethod -Uri $uri -Method Get -TimeoutSec 5
  $msg = "[{0}] ok={1} per_bet={2} settlement={3} summary={4}" -f (Get-Date -Format s), $m.ok, $m.per_bet_rows, $m.settlement_rows, $m.summary_rows
  if (-not $m.ok -or ($m.per_bet_rows -eq 0 -and $m.settlement_rows -eq 0 -and $m.summary_rows -eq 0)) {
    $msg = "WARN " + $msg
  } else {
    $msg = "INFO " + $msg
  }
} catch {
  $msg = "ERR  [{0}] cannot reach /metrics: {1}" -f (Get-Date -Format s), $_.Exception.Message
}
$msg | Add-Content -Path $log -Encoding UTF8
Write-Host $msg
