import fs from 'node:fs';
import assert from 'node:assert/strict';
import {readCSV, writeCSV} from './lib/csv.mjs';

// Stage 4: Seasonal Hydro-Meteorological Feature Aggregation & Clean Dataset Joining
// Joins cleaned rice tables (Tier 1 3-season track, Tier 2 13-province Mekong Delta track,
// and 7-row External OOD supplemental geographic check) with:
//   - Cleaned area-weighted zonal daily weather (NASA POWER 2014–2024)
//   - Cleaned official subregional crop calendar windows (plus ±10/±15-day shifts)
//   - Official NOAA PSL Oceanic Niño Index (ONI, 3-month running mean)
//
// Physical & Agronomic Features Added (strictly causal/pre-harvest, zero future leakage):
//   - vpd_mean_kpa: Vapor Pressure Deficit via Magnus-Tetens equation
//   - max_consecutive_dry_days: Longest consecutive dry spell (<1 mm/day) in season
//   - pre_season_rain_90d_mm: Cumulative rainfall in the 90 days strictly prior to window_start_date
//   - oni_pre_season: NOAA ONI index (Nov t-1 for DX; Mar t for HT / HT+TD; Jun t for TD)

fs.mkdirSync('data/processed', {recursive: true});

const addDaysISO = (isoStr, deltaDays) => {
  const [y, m, d] = isoStr.split('-').map(Number);
  const dt = new Date(Date.UTC(y, m - 1, d + deltaDays));
  return `${dt.getUTCFullYear()}-${String(dt.getUTCMonth() + 1).padStart(2, '0')}-${String(dt.getUTCDate()).padStart(2, '0')}`;
};

// Parse NOAA PSL ONI (12 monthly columns per year: month 1..12)
const loadONI = path => {
  const text = fs.readFileSync(path, 'utf8');
  const map = new Map();
  for (const line of text.split(/\r?\n/)) {
    const parts = line.trim().split(/\s+/);
    if (parts.length !== 13 || !/^\d{4}$/.test(parts[0])) continue;
    const yr = Number(parts[0]);
    for (let m = 1; m <= 12; m++) {
      const val = Number(parts[m]);
      if (Number.isFinite(val) && val > -50) map.set(`${yr}-${m}`, val);
    }
  }
  return map;
};

const oniMap = loadONI('data/raw/climate/noaa_psl_oni.data');
const getPreSeasonONI = (harvestYear, season) => {
  // Strictly prior to main grain-filling / harvest (zero leakage):
  //   dong_xuan -> Nov (OND) of harvestYear - 1 (sets dry-season El Nino / salinity risk)
  //   he_thu / he_thu_thu_dong_combined -> Mar (FMA) of harvestYear
  //   thu_dong -> Jun (MJJ) of harvestYear
  const key = season === 'dong_xuan'
    ? `${harvestYear - 1}-11`
    : season === 'thu_dong'
      ? `${harvestYear}-6`
      : `${harvestYear}-3`;
  const val = oniMap.get(key);
  assert(Number.isFinite(val), `Missing NOAA ONI for ${key} (${season} ${harvestYear})`);
  return Number(val.toFixed(2));
};

const loadDailyIndex = csvPath => {
  const rows = readCSV(csvPath);
  const byProv = new Map();
  for (const r of rows) {
    let arr = byProv.get(r.province_id);
    if (!arr) {
      arr = [];
      byProv.set(r.province_id, arr);
    }
    arr.push({
      date: r.date,
      T2M: Number(r.T2M),
      T2M_MAX: Number(r.T2M_MAX),
      T2M_MIN: Number(r.T2M_MIN),
      PRECTOTCORR: Number(r.PRECTOTCORR),
      RH2M: Number(r.RH2M),
      WS2M: Number(r.WS2M),
      grid_cells_used: Number(r.grid_cells_used)
    });
  }
  for (const arr of byProv.values()) arr.sort((a, b) => a.date.localeCompare(b.date));
  return byProv;
};

const calcVPD = (tC, rhPct) => {
  // Saturation vapor pressure (kPa) via FAO-56 / Magnus-Tetens formula
  const es = 0.6108 * Math.exp((17.27 * tC) / (tC + 237.3));
  return Math.max(0, es * (1 - rhPct / 100));
};

const aggregateWindow = (dailySeries, startDate, endDate, expectedDays) => {
  const slice = dailySeries.filter(d => d.date >= startDate && d.date <= endDate);
  assert.equal(
    slice.length,
    expectedDays,
    `Weather window day mismatch for ${startDate}..${endDate}: got ${slice.length}, expected ${expectedDays}`
  );
  const preStart = addDaysISO(startDate, -90);
  const preEnd = addDaysISO(startDate, -1);
  const preSlice = dailySeries.filter(d => d.date >= preStart && d.date <= preEnd);
  assert.equal(
    preSlice.length,
    90,
    `Pre-season 90-day weather mismatch for ${preStart}..${preEnd}: got ${preSlice.length}`
  );

  const n = slice.length;
  let sumT2m = 0, sumTmax = 0, sumTmin = 0, peakTmax = -Infinity;
  let sumRain = 0, sumRh = 0, sumWs = 0, sumVpd = 0;
  let hotDays35 = 0, dryDays1 = 0, dryDays2 = 0, heavyRain20 = 0;
  let curDry = 0, maxDryStreak = 0;

  for (const d of slice) {
    sumT2m += d.T2M;
    sumTmax += d.T2M_MAX;
    sumTmin += d.T2M_MIN;
    if (d.T2M_MAX > peakTmax) peakTmax = d.T2M_MAX;
    sumRain += d.PRECTOTCORR;
    sumRh += d.RH2M;
    sumWs += d.WS2M;
    sumVpd += calcVPD(d.T2M, d.RH2M);
    if (d.T2M_MAX > 35) hotDays35++;
    if (d.PRECTOTCORR < 1) {
      dryDays1++;
      curDry++;
      if (curDry > maxDryStreak) maxDryStreak = curDry;
    } else {
      curDry = 0;
    }
    if (d.PRECTOTCORR < 2) dryDays2++;
    if (d.PRECTOTCORR >= 20) heavyRain20++;
  }

  const preRain90d = preSlice.reduce((s, d) => s + d.PRECTOTCORR, 0);

  return {
    window_days: n,
    grid_cells_used: slice[0].grid_cells_used,
    t2m_mean_c: Number((sumT2m / n).toFixed(3)),
    t2m_max_mean_c: Number((sumTmax / n).toFixed(3)),
    t2m_max_peak_c: Number(peakTmax.toFixed(3)),
    t2m_min_mean_c: Number((sumTmin / n).toFixed(3)),
    precip_total_mm: Number(sumRain.toFixed(2)),
    precip_mean_mm_day: Number((sumRain / n).toFixed(3)),
    rh2m_mean_pct: Number((sumRh / n).toFixed(3)),
    ws2m_mean_ms: Number((sumWs / n).toFixed(3)),
    vpd_mean_kpa: Number((sumVpd / n).toFixed(4)),
    hot_days_gt35c: hotDays35,
    dry_days_lt1mm: dryDays1,
    dry_days_lt2mm: dryDays2,
    max_consecutive_dry_days: maxDryStreak,
    heavy_rain_days_gt20mm: heavyRain20,
    pre_season_rain_90d_mm: Number(preRain90d.toFixed(2))
  };
};

const tier1Rice = readCSV('data/interim/rice_tier1_core_3seasons.csv');
const tier2Rice = readCSV('data/interim/rice_tier2_delta13_nso.csv');
const suppRice = readCSV('data/interim/rice_supplemental_reports.csv');
const calShifts = readCSV('data/interim/season_calendar_sensitivity_shifts.csv');
const zonalDaily = loadDailyIndex('data/interim/weather_daily_province_zonal.csv');
const singleDaily = loadDailyIndex('data/interim/weather_daily_province_single_point.csv');

const calMap = new Map(
  calShifts.map(r => [`${r.province_id}|${r.harvest_year}|${r.season}|${r.shift_days}`, r])
);

const joinRecords = (riceRows, dailyByProv, spatialMethod, shiftDays = 0) => {
  const joined = [];
  for (const r of riceRows) {
    const calKey = `${r.province_id}|${r.harvest_year}|${r.season}|${shiftDays}`;
    const cal = calMap.get(calKey);
    assert(cal, `Missing calendar window for ${calKey}`);
    const daily = dailyByProv.get(r.province_id);
    assert(daily, `Missing daily weather for ${r.province_id}`);

    const feat = aggregateWindow(daily, cal.start_date, cal.end_date, Number(cal.expected_window_days));
    const oniPre = getPreSeasonONI(Number(r.harvest_year), r.season);

    joined.push({
      dataset_tier: r.dataset_tier,
      province_id: r.province_id,
      province: r.province,
      ecological_subregion: cal.ecological_subregion,
      harvest_year: Number(r.harvest_year),
      season: r.season,
      season_scope: r.season_scope,
      time_split: r.time_split,
      // Target variable
      yield_t_ha: Number(r.yield_t_ha),
      // Descriptors only (MUST NOT be used as features in yield prediction)
      area_ha: Number(r.area_ha),
      production_t: Number(r.production_t),
      // Calendar & spatial metadata
      spatial_method: spatialMethod,
      calendar_tier: cal.calendar_tier,
      calendar_shift_days: shiftDays,
      window_start_date: cal.start_date,
      window_end_date: cal.end_date,
      cross_calendar_year: cal.cross_calendar_year,
      ...feat,
      oni_pre_season: oniPre,
      // Quality & provenance metadata
      revision_status: r.revision_status,
      source_tier: r.source_tier,
      formula_check_status: r.formula_check_status,
      domain_outlier_flag: r.domain_outlier_flag,
      source_file: r.source_file,
      source_sha256: r.source_sha256,
      source_locator: r.source_locator
    });
  }
  return joined;
};

// 1. Track B: Separate 3-Season Core Dataset (90 rows)
const tier1Clean = joinRecords(tier1Rice, zonalDaily, 'gadm_area_weighted_zonal_mean', 0);
assert.equal(tier1Clean.length, 90);
writeCSV('data/processed/tier1_core_3seasons_model_ready.csv', tier1Clean);

// 2. Track A1: Full 13-Province Mekong Delta Dong Xuan Dataset (127 rows)
const tier2DxClean = joinRecords(
  tier2Rice.filter(r => r.season === 'dong_xuan'),
  zonalDaily,
  'gadm_area_weighted_zonal_mean',
  0
);
assert.equal(tier2DxClean.length, 127);
writeCSV('data/processed/tier2_delta13_dong_xuan_model_ready.csv', tier2DxClean);

// 3. Track A2: Full 13-Province Mekong Delta Combined HT-TD Dataset (130 rows)
const tier2CombClean = joinRecords(
  tier2Rice.filter(r => r.season === 'he_thu_thu_dong_combined'),
  zonalDaily,
  'gadm_area_weighted_zonal_mean',
  0
);
assert.equal(tier2CombClean.length, 130);
writeCSV('data/processed/tier2_delta13_combined_ht_td_model_ready.csv', tier2CombClean);

// 4. External Geographic OOD Stress-Test Dataset (7 supplemental rows: Tien Giang, Vinh Long, Ca Mau)
const oodClean = joinRecords(suppRice, zonalDaily, 'gadm_area_weighted_zonal_mean', 0);
assert.equal(oodClean.length, 7);
writeCSV('data/processed/external_ood_7rows_supplemental.csv', oodClean);

// 5. Sensitivity Dataset for Track B (6 configurations x 90 rows = 540 rows)
const sensitivityConfigs = [
  ['zonal_shift_0', zonalDaily, 'gadm_area_weighted_zonal_mean', 0],
  ['zonal_shift_-15', zonalDaily, 'gadm_area_weighted_zonal_mean', -15],
  ['zonal_shift_-10', zonalDaily, 'gadm_area_weighted_zonal_mean', -10],
  ['zonal_shift_+10', zonalDaily, 'gadm_area_weighted_zonal_mean', 10],
  ['zonal_shift_+15', zonalDaily, 'gadm_area_weighted_zonal_mean', 15],
  ['single_point_shift_0', singleDaily, 'single_acquisition_point', 0]
];
const sensRows = [];
for (const [scenarioId, dailyMap, method, shift] of sensitivityConfigs) {
  const part = joinRecords(tier1Rice, dailyMap, method, shift).map(r => ({
    sensitivity_scenario: scenarioId,
    ...r
  }));
  sensRows.push(...part);
}
assert.equal(sensRows.length, 90 * 6);
writeCSV('data/processed/tier1_sensitivity_calendar_and_spatial.csv', sensRows);

const summary = {
  generated_at: new Date().toISOString(),
  outputs: {
    tier1_core_3seasons_model_ready: tier1Clean.length,
    tier2_delta13_dong_xuan_model_ready: tier2DxClean.length,
    tier2_delta13_combined_ht_td_model_ready: tier2CombClean.length,
    external_ood_7rows_supplemental: oodClean.length,
    tier1_sensitivity_calendar_and_spatial: sensRows.length
  },
  hydro_meteo_features_added: [
    'vpd_mean_kpa (Magnus-Tetens atmospheric evaporative demand)',
    'max_consecutive_dry_days (<1 mm/day dry spell streak)',
    'pre_season_rain_90d_mm (90-day pre-sowing cumulative rainfall)',
    'oni_pre_season (NOAA PSL Oceanic Nino Index prior to crop harvest)'
  ],
  time_split_counts_tier1: {
    train_2015_2020: tier1Clean.filter(r => r.time_split === 'train').length,
    val_2021_2022: tier1Clean.filter(r => r.time_split === 'val').length,
    test_2023_2024: tier1Clean.filter(r => r.time_split === 'test').length
  },
  time_split_counts_tier2_dx: {
    train_2015_2020: tier2DxClean.filter(r => r.time_split === 'train').length,
    val_2021_2022: tier2DxClean.filter(r => r.time_split === 'val').length,
    test_2023_2024: tier2DxClean.filter(r => r.time_split === 'test').length
  }
};
fs.writeFileSync('docs/processed_datasets_status.json', JSON.stringify(summary, null, 2));
console.log(JSON.stringify(summary, null, 2));
