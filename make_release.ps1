param(
  [string]$OutDir = "dist",
  [string]$ZipName = "M7_Phase3_SharpReady_v1.0.2.zip"
)

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $root

New-Item -Force -ItemType Directory $OutDir | Out-Null
$zip = Join-Path $OutDir $ZipName

# Exclude the .git folder and caches
$items = Get-ChildItem -Force | Where-Object {
  $_.Name -notin @("dist",".git") -and $_.Name -notmatch "__pycache__"
}
if (Test-Path $zip) { Remove-Item $zip -Force }

$items | Compress-Archive -DestinationPath $zip -Force
Write-Host "Created $zip"
