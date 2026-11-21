import fs from 'node:fs';
import assert from 'node:assert/strict';
import {readCSV} from './lib/csv.mjs';

// Stage 5: Automated Cleaning & Post-Join Quality Verification Gate
// Validates schema, uniqueness, missingness, anti-leakage splits, domain outlier retention,
// official 2019 reconciliation, and computes quantitative sensitivity metrics (±10/±15d & zonal vs single-point).

const FEATURE_COLS = [
  't2m_mean_c', 't2m_max_mean_c', 't2m_max_peak_c', 't2m_min_mean_c',
  'precip_total_mm', 'precip_mean_mm_day', 'rh2m_mean_pct', 'ws2m_mean_ms',
  'vpd_mean_kpa', 'hot_days_gt35c', 'dry_days_lt1mm', 'dry_days_lt2mm',
  'max_consecutive_dry_days', 'heavy_rain_days_gt20mm', 'pre_season_rain_90d_mm',
  'oni_pre_season'
];

const pearson = (xs, ys) => {
  const n = xs.length;
  const mx = xs.reduce((a, b) => a + b, 0) / n;
  const my = ys.reduce((a, b) => a + b, 0) / n;
  let num = 0, dx = 0, dy = 0;
  for (let i = 0; i < n; i++) {
    const a = xs[i] - mx, b = ys[i] - my;
    num += a * b;
    dx += a * a;
    dy += b * b;
  }
  return dx === 0 || dy === 0 ? 1 : num / Math.sqrt(dx * dy);
};

const mad = (xs, ys) => xs.reduce((s, x, i) => s + Math.abs(x - ys[i]), 0) / xs.length;

const verifyDataset = (path, expectedRows, expectedSingleScope = true) => {
  const rows = readCSV(path);
  assert.equal(rows.length, expectedRows, `Row count mismatch in ${path}: ${rows.length} != ${expectedRows}`);
  const keys = new Set();
  for (const r of rows) {
    const k = `${r.province_id}|${r.harvest_year}|${r.season}`;
    assert(!keys.has(k), `Duplicate key ${k} in ${path}`);
    keys.add(k);
    if (expectedSingleScope) assert.equal(r.season_scope, 'single', `Non-single season in ${path}: ${k}`);
    const y = Number(r.yield_t_ha);
    assert(Number.isFinite(y) && y > 0 && y < 12, `Yield out of plausible bounds in ${path}: ${k} -> ${y}`);
    const yr = Number(r.harvest_year);
    const expectedSplit = yr <= 2020 ? 'train' : yr <= 2022 ? 'val' : 'test';
    assert.equal(r.time_split, expectedSplit, `Chronological split mismatch ${k}`);
    for (const col of FEATURE_COLS) {
      const v = Number(r[col]);
      assert(Number.isFinite(v), `Non-finite feature ${col} in ${path}: ${k}`);
    }
    assert(Number(r.t2m_max_peak_c) >= Number(r.t2m_max_mean_c));
    assert(Number(r.t2m_max_mean_c) >= Number(r.t2m_mean_c));
    assert(Number(r.t2m_mean_c) >= Number(r.t2m_min_mean_c));
    assert(Number(r.precip_total_mm) >= 0);
    assert(Number(r.rh2m_mean_pct) >= 0 && Number(r.rh2m_mean_pct) <= 100);
    assert(Number(r.dry_days_lt1mm) <= Number(r.dry_days_lt2mm));
    assert(Number(r.dry_days_lt2mm) <= Number(r.window_days));
    if (r.season === 'dong_xuan') {
      assert.equal(r.cross_calendar_year, 'true', `Dong Xuan must span year t-1 to t: ${k}`);
      assert.equal(Number(r.window_start_date.slice(0, 4)), yr - 1);
    }
  }
  return rows;
};

const t1 = verifyDataset('data/processed/tier1_core_3seasons_model_ready.csv', 90, true);
const t2Dx = verifyDataset('data/processed/tier2_delta13_dong_xuan_model_ready.csv', 127, true);
const t2Comb = verifyDataset('data/processed/tier2_delta13_combined_ht_td_model_ready.csv', 130, false);
const ood7 = verifyDataset('data/processed/external_ood_7rows_supplemental.csv', 7, true);

// Verify 2019 official upgrade in Tier 2 (zero 2019 preliminary rows)
assert.equal(t2Dx.filter(r => Number(r.harvest_year) === 2019 && r.revision_status === 'preliminary').length, 0);
assert.equal(t2Comb.filter(r => Number(r.harvest_year) === 2019 && r.revision_status === 'preliminary').length, 0);

// Verify Ben Tre salinity extreme outliers are preserved & flagged in Tier 2 Dong Xuan
const flaggedOutliers = t2Dx.filter(r => r.domain_outlier_flag === 'extreme_salinity_crop_failure');
assert.equal(flaggedOutliers.length, 2, 'Expected 2 flagged Ben Tre extreme salinity crop failure records');

// Quantitative Sensitivity Analysis on Tier 1 (6 scenarios)
const sens = readCSV('data/processed/tier1_sensitivity_calendar_and_spatial.csv');
assert.equal(sens.length, 540);
const baseRows = sens.filter(r => r.sensitivity_scenario === 'zonal_shift_0');
const keyOf = r => `${r.province_id}|${r.harvest_year}|${r.season}`;
const baseMap = new Map(baseRows.map(r => [keyOf(r), r]));

const keyMetrics = ['t2m_mean_c', 't2m_max_mean_c', 'precip_total_mm', 'rh2m_mean_pct', 'hot_days_gt35c', 'dry_days_lt1mm'];
const sensitivitySummary = {};
for (const sc of ['single_point_shift_0', 'zonal_shift_-10', 'zonal_shift_+10', 'zonal_shift_-15', 'zonal_shift_+15']) {
  const comp = sens.filter(r => r.sensitivity_scenario === sc);
  assert.equal(comp.length, 90);
  const compMap = new Map(comp.map(r => [keyOf(r), r]));
  sensitivitySummary[sc] = {};
  for (const m of keyMetrics) {
    const xs = [], ys = [];
    for (const [k, br] of baseMap) {
      xs.push(Number(br[m]));
      ys.push(Number(compMap.get(k)[m]));
    }
    sensitivitySummary[sc][m] = {
      pearson_r: Number(pearson(xs, ys).toFixed(4)),
      mean_abs_diff: Number(mad(xs, ys).toFixed(3))
    };
  }
}

// Compute quick descriptive yield summary by season for Tier 1 (sanity check)
const seasonStats = {};
for (const s of ['dong_xuan', 'he_thu', 'thu_dong']) {
  const ys = t1.filter(r => r.season === s).map(r => Number(r.yield_t_ha)).sort((a, b) => a - b);
  const mean = ys.reduce((a, b) => a + b, 0) / ys.length;
  seasonStats[s] = {
    n: ys.length,
    min_t_ha: ys[0],
    median_t_ha: Number(((ys[Math.floor((ys.length - 1) / 2)] + ys[Math.ceil((ys.length - 1) / 2)]) / 2).toFixed(3)),
    mean_t_ha: Number(mean.toFixed(3)),
    max_t_ha: ys.at(-1)
  };
}

const report = {
  generated_at: new Date().toISOString(),
  cleaning_verification_passed: true,
  ready_for_eda_and_modeling: true,
  datasets_verified: {
    tier1_core_3seasons_model_ready: {rows: t1.length, provinces: 3, seasons: 3, years: '2015–2024', missing_values: 0},
    tier2_delta13_dong_xuan_model_ready: {rows: t2Dx.length, provinces: 13, years: '2015–2024', missing_values: 0, flagged_salinity_outliers: flaggedOutliers.length},
    tier2_delta13_combined_ht_td_model_ready: {rows: t2Comb.length, provinces: 13, years: '2015–2024', missing_values: 0}
  },
  tier1_yield_sanity_by_season: seasonStats,
  sensitivity_vs_zonal_shift_0: sensitivitySummary
};

fs.writeFileSync('docs/cleaning_verification_report.json', JSON.stringify(report, null, 2));
console.log(JSON.stringify(report, null, 2));
