$ErrorActionPreference = 'Stop'

Write-Host '=== Step 0: Verify Raw-to-Cleaning Handoff Gate ==='
node scripts/verify_raw_handoff.mjs

Write-Host '=== Step 1: Clean & Reconcile Rice Data ==='
node scripts/clean_rice_data.mjs

Write-Host '=== Step 2: Clean Weather Daily (Area-Weighted Zonal Mean) ==='
node scripts/clean_weather_zonal.mjs

Write-Host '=== Step 3: Clean Season Calendar & Sensitivity Shifts ==='
node scripts/clean_season_calendar.mjs

Write-Host '=== Step 4: Build Processed Model-Ready & Sensitivity Datasets ==='
node scripts/build_clean_datasets.mjs

Write-Host '=== Step 5: Verify Cleaned Datasets ==='
node scripts/verify_cleaned_datasets.mjs

Write-Host '=== Cleaning Pipeline Completed & Verified (PASS) ==='
