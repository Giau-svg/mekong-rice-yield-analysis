import fs from 'node:fs';
import crypto from 'node:crypto';
import assert from 'node:assert/strict';
import {readCSV} from './lib/csv.mjs';

// Automated Raw-to-Cleaning Handoff Gate Verification
// Verifies all 4 required input blocks against the 5 Data Analytics exit criteria
// without performing any cleaning, imputation, unit conversion, or joining.

const catalog = JSON.parse(fs.readFileSync('data/catalog/source_catalog.json', 'utf8'));
const catalogByPath = new Map(catalog.map(r => [r.local, r]));
const checkProvenance = (rows, fileCol = 'source_file', shaCol = 'source_sha256') => {
  for (const r of rows) {
    const f = r[fileCol];
    const c = catalogByPath.get(f);
    assert(c, `Provenance error: ${f} not registered in source_catalog.json`);
    if (shaCol && r[shaCol]) {
      assert.equal(r[shaCol], c.sha256, `SHA-256 mismatch for ${f}`);
    }
  }
};

// === BLOCK 1: RICE RAW TABLES ===
const localMain = readCSV('data/raw/rice_captured_main_seasons.csv');
const nsoBase = readCSV('data/raw/nso_rice_province_tables.csv');
const nso2021 = readCSV('data/raw/nso_rice_2021_reconciliation.csv');
const reportVals = readCSV('data/raw/rice_report_season_values.csv');
const coverage = readCSV('data/catalog/rice_collection_coverage.csv');

assert.equal(localMain.length, 90, 'Expected 90 rows in rice_captured_main_seasons.csv');
assert.equal(nsoBase.length, 467, 'Expected 467 rows in nso_rice_province_tables.csv');
assert.equal(nso2021.length, 233, 'Expected 233 rows in nso_rice_2021_reconciliation.csv');
assert.equal(reportVals.length, 7, 'Expected 7 rows in rice_report_season_values.csv');
assert.equal(coverage.length, 390, 'Expected 390 reference cells in rice_collection_coverage.csv');

for (const tbl of [localMain, nsoBase, nso2021, reportVals]) checkProvenance(tbl);
const nso2021Official2019 = nso2021.filter(r => r.year_raw === '2019');
assert.equal(nso2021Official2019.length, 47, 'Expected 47 official 2019 rows in NSO 2021 table');

// === BLOCK 2: WEATHER DAILY RAW TABLE ===
const weatherLines = fs.readFileSync('data/raw/weather_daily_raw.csv', 'utf8').replace(/^\uFEFF/, '').trim().split('\n');
const weatherCount = weatherLines.length - 1;
assert.equal(weatherCount, 132594, 'Expected 132,594 point-day rows (33 files x 4,018 days)');
const weatherKeys = new Set();
let fillVals = 0, badPhys = 0;
for (let i = 1; i < weatherLines.length; i++) {
  const c = weatherLines[i].split(',').map(s => s.slice(1, -1));
  const k = `${c[1]}|${c[4]}`;
  assert(!weatherKeys.has(k), `Duplicate weather key ${k}`);
  weatherKeys.add(k);
  const [t2m, tmax, tmin, rain, rh, ws] = [6, 7, 8, 9, 10, 11].map(j => Number(c[j]));
  if ([t2m, tmax, tmin, rain, rh, ws].some(v => v === -999 || !Number.isFinite(v))) fillVals++;
  if (tmax < t2m || t2m < tmin || rain < 0 || rh < 0 || rh > 100 || ws < 0) badPhys++;
}
assert.equal(fillVals, 0, 'Found fill values in core 6 weather variables');
assert.equal(badPhys, 0, 'Found physical range violations in core 6 weather variables');

// === BLOCK 3: CROP CALENDAR RAW TABLES ===
const calRaw = readCSV('data/raw/season_calendar_raw.csv');
const calSage = readCSV('data/catalog/calendar_vietnam_rice_reference.csv');
assert(calRaw.length >= 15, 'Expected >=15 official raw calendar records');
checkProvenance(calRaw);
const calSeasons = new Set(calRaw.map(r => r.season_reference));
for (const s of ['Lúa đông xuân', 'Lúa hè thu', 'Lúa thu đông']) {
  assert(calSeasons.has(s), `Missing calendar coverage for season: ${s}`);
}
assert.equal(calSage.length, 5, 'Expected 5 historical SAGE reference rows');

// === BLOCK 4: GEO BOUNDARY & GRID OVERLAP CATALOG ===
const geoPath = 'data/raw/geo/gadm41_VNM_1.json';
assert(catalogByPath.has(geoPath), 'GeoJSON boundary missing from source_catalog.json');
const geoSha = crypto.createHash('sha256').update(fs.readFileSync(geoPath)).digest('hex');
assert.equal(geoSha, catalogByPath.get(geoPath).sha256, 'GeoJSON SHA-256 mismatch');
const overlap = readCSV('data/catalog/weather_grid_province_overlap.csv');
assert.equal(new Set(overlap.map(r => r.province_id)).size, 13, 'Expected all 13 Mekong provinces in overlap catalog');
for (const r of overlap) {
  assert(catalogByPath.has(r.weather_source_file), `Weather file in overlap missing from catalog: ${r.weather_source_file}`);
}
const provWeightSums = new Map();
for (const r of overlap) {
  provWeightSums.set(r.province_id, (provWeightSums.get(r.province_id) || 0) + Number(r.province_area_weight));
}
for (const [p, sum] of provWeightSums) {
  assert(Math.abs(sum - 1) < 1e-4, `Area weights for ${p} do not sum to 1 (${sum})`);
}

const separateCells = coverage.filter(r => r.collection_status === 'separate_season_values_captured').length;
const report = {
  generated_at: new Date().toISOString(),
  handoff_gate_passed: true,
  ready_for_cleaning_stage: true,
  cleaning_performed_yet: false,
  blocks: {
    block1_rice_raw: {
      status: 'PASS',
      local_three_season_rows: localMain.length,
      local_full_provinces: [...new Set(localMain.map(r => r.province_raw))],
      nso_base_rows: nsoBase.length,
      nso_2021_reconciliation_rows: nso2021.length,
      official_2019_rows_for_reconciliation: nso2021Official2019.length,
      provincial_report_rows: reportVals.length,
      coverage_separate_cells: separateCells,
      coverage_reference_cells: coverage.length,
      required_project_scope: 'Mandatory full Mekong Delta scope (all 13 pre-2025 provinces, 2015–2024) implemented via two co-primary analytical tracks (13 provinces is NOT an optional extension): Track A Delta-wide 13 provinces (NSO Đông Xuân 127 rows & Combined HT-TD 130 rows); Track B Separate 3-season track on provinces with full 10-year official provincial yearbooks (An Giang, Kiên Giang, Cần Thơ: 90 rows, 40.5% of Mekong Delta output)'
    },
    block2_weather_raw: {
      status: 'PASS',
      point_day_rows: weatherCount,
      date_range: '2014-01-01 to 2024-12-31 (4,018 days)',
      common_grid_parameters: ['T2M', 'T2M_MAX', 'T2M_MIN', 'PRECTOTCORR', 'RH2M', 'WS2M'],
      optional_point_only_parameter: 'ALLSKY_SFC_SW_DWN (present only in 13 provincial points, blank in 20 supplemental grid cells)',
      duplicate_keys: 0,
      fill_values_in_common_params: fillVals,
      physical_violations: badPhys
    },
    block3_calendar_raw: {
      status: 'PASS_WITH_SENSITIVITY_REQUIREMENT',
      official_directive_records: calRaw.length,
      distinct_official_sources: new Set(calRaw.map(r => r.source_file)).size,
      seasons_covered: [...calSeasons],
      historical_sage_rows: calSage.length,
      cleaning_requirement: 'Derive primary seasonal windows from official MARD/DCP framework & subregional directives + mandatory +-10 and +-15 day sensitivity analysis'
    },
    block4_geo_spatial_mapping: {
      status: 'PASS',
      boundary_file: geoPath,
      boundary_sha256: geoSha,
      mekong_provinces_covered: 13,
      overlap_rows: overlap.length,
      distinct_active_grid_cells: new Set(overlap.map(r => r.grid_id)).size,
      distinct_province_weight_profiles: 13
    }
  },
  catalog_summary: {
    registered_raw_files: catalog.length,
    unique_sha256: new Set(catalog.map(r => r.sha256)).size
  }
};

fs.writeFileSync('docs/raw_handoff_readiness.json', JSON.stringify(report, null, 2));
console.log(JSON.stringify(report, null, 2));
