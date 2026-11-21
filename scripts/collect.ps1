$ErrorActionPreference = 'Stop'
Set-Location (Split-Path $PSScriptRoot -Parent)
New-Item -ItemType Directory -Force data/raw | Out-Null
$sources = @{
 'tien_giang_2024.html' = 'https://thongkedongthap.nso.gov.vn/tin-tuc/140'
 'nasa_power_tien_giang_pilot_2024.json' = 'https://power.larc.nasa.gov/api/temporal/daily/point?parameters=T2M,T2M_MAX,PRECTOTCORR,RH2M&community=AG&longitude=106.35&latitude=10.45&start=20240101&end=20241231&format=JSON&time-standard=LST'
}
foreach ($name in $sources.Keys) {
 $destination = Join-Path 'data/raw' $name
 if (Test-Path -LiteralPath $destination) { continue }
 $success = $false
 for ($attempt=1; $attempt -le 3; $attempt++) {
  try {
   Invoke-WebRequest -UseBasicParsing -Uri $sources[$name] -OutFile "$destination.part" -TimeoutSec 60
   Move-Item -LiteralPath "$destination.part" -Destination $destination
   $success = $true
   break
  } catch { if ($attempt -eq 3) { throw }; Start-Sleep -Seconds (2*$attempt) }
 }
 if (-not $success) { throw "Download failed: $name" }
}
node scripts/build_dataset.mjs
if ($LASTEXITCODE -ne 0) { throw 'Dataset validation failed' }
