$ErrorActionPreference = 'Stop'
Set-Location (Split-Path $PSScriptRoot -Parent)
function Run-Node([string]$script) {
 & node $script
 if ($LASTEXITCODE -ne 0) { throw "Failed: $script" }
}
Run-Node 'scripts/collect_weather_raw.mjs'
Run-Node 'scripts/collect_weather_grid.mjs'
$env:CRAWL_RESUME='0'
$env:CRAWL_MAX='400'
$env:CRAWL_DEPTH='3'
foreach ($seed in @('config/crawl_seeds.json','config/archive_seeds.json','config/round2_seeds.json','config/targeted_archive_seeds.json','config/season_report_seeds.json','config/supplemental_discovery_seeds.json')) {
 $env:CRAWL_SEEDS=$seed
 Run-Node 'scripts/crawl_raw.mjs'
}
$env:CRAWL_SEEDS='config/multisource_seeds.json'
$env:CRAWL_DEPTH='1'
Run-Node 'scripts/crawl_raw.mjs'
foreach ($seed in @('config/gap_round_seeds.json','config/verified_report_seeds.json','config/calendar_report_seeds.json','config/systematic_gap_seeds.json')) {
 $env:CRAWL_SEEDS=$seed
 Run-Node 'scripts/crawl_raw.mjs'
}
Run-Node 'scripts/collect_reference_raw.mjs'
Run-Node 'scripts/collect_riceatlas_raw.mjs'
Run-Node 'scripts/inventory_raw.mjs'
if (Test-Path 'tmp/pdf-runtime/node_modules/pdfjs-dist') {
 Run-Node 'scripts/index_pdf_raw.mjs'
 Run-Node 'scripts/catalog_pdf_candidates.mjs'
 Run-Node 'scripts/capture_rice_tables_raw.mjs'
 Run-Node 'scripts/capture_nso_rice_raw.mjs'
}
if (Test-Path 'tmp/html-runtime/node_modules/linkedom') {
 Run-Node 'scripts/index_html_raw.mjs'
 Run-Node 'scripts/capture_report_values_raw.mjs'
}
if (Test-Path 'data/raw/nso_rice_province_tables.csv') { Run-Node 'scripts/audit_collection_coverage.mjs' }
if ((Test-Path 'docs/html_index_status.json') -and (Test-Path 'docs/collection_coverage_audit.json')) { Run-Node 'scripts/write_acquisition_report.mjs' }
Write-Output 'Acquisition run finished. Coverage completeness is reported separately in docs/collection_coverage_audit.json. No cleaning performed.'
