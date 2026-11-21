import fs from 'node:fs';
import path from 'node:path';
import assert from 'node:assert/strict';
import {readCSV, writeCSV} from './lib/csv.mjs';

// Stage 2: Weather Daily Cleaning & Area-Weighted Zonal Aggregation per Province
// Solves MERRA-2 0.5° x 0.625° duplicate-cell issue across small neighboring provinces
// by using GADM v4.1 area-overlap weights (data/catalog/weather_grid_province_overlap.csv).
// Also outputs cleaned 13-point provincial series strictly for spatial sensitivity comparison.

fs.mkdirSync('data/interim', {recursive: true});

const PARAMS = ['T2M', 'T2M_MAX', 'T2M_MIN', 'PRECTOTCORR', 'RH2M', 'WS2M'];
const overlap = readCSV('data/catalog/weather_grid_province_overlap.csv');
const weatherPoints = JSON.parse(fs.readFileSync('config/weather_points.json', 'utf8'));

// Load all needed weather JSON files once into memory
const neededFiles = new Set([
  ...overlap.map(r => r.weather_source_file),
  ...weatherPoints.map(p => `data/raw/weather/${p.id}_2014_2024.json`)
]);

const fileCache = new Map();
let referenceDates = null;

for (const file of neededFiles) {
  const raw = JSON.parse(fs.readFileSync(file, 'utf8'));
  const p = raw.properties.parameter;
  const fill = raw.header.fill_value;
  const dates = Object.keys(p.T2M).sort();
  assert.equal(dates.length, 4018, `Unexpected day count in ${file}: ${dates.length}`);
  assert.equal(dates[0], '20140101');
  assert.equal(dates.at(-1), '20241231');
  if (!referenceDates) referenceDates = dates;
  else assert.deepEqual(dates, referenceDates, `Date sequence mismatch in ${file}`);

  for (const k of PARAMS) {
    assert(p[k], `Missing parameter ${k} in ${file}`);
    for (const d of dates) {
      const v = p[k][d];
      assert(v !== fill && Number.isFinite(v), `Invalid value for ${k} on ${d} in ${file}`);
    }
  }
  fileCache.set(file, {
    parameter: p,
    time_standard: raw.header.time_standard,
    coords: raw.geometry.coordinates
  });
}

const isoDate = yyyymmdd => `${yyyymmdd.slice(0, 4)}-${yyyymmdd.slice(4, 6)}-${yyyymmdd.slice(6, 8)}`;

// Group overlap weights by province
const provinceList = [...new Set(overlap.map(r => r.province_id))];
assert.equal(provinceList.length, 13);

const zonalRows = [];
const provinceSignatures = new Map();

for (const provinceId of provinceList) {
  const weights = overlap.filter(r => r.province_id === provinceId).map(r => ({
    province: r.province,
    file: r.weather_source_file,
    w: Number(r.province_area_weight)
  }));
  const provinceName = weights[0].province;
  const sumW = weights.reduce((s, x) => s + x.w, 0);
  assert(Math.abs(sumW - 1) < 1e-4, `Weight sum error for ${provinceId}: ${sumW}`);

  const sigSamples = [];
  for (const d of referenceDates) {
    const vals = {};
    for (const k of PARAMS) {
      let acc = 0;
      for (const {file, w} of weights) {
        acc += w * fileCache.get(file).parameter[k][d];
      }
      vals[k] = Number(acc.toFixed(4));
    }
    // Physical sanity assertions after weighted averaging
    assert(vals.T2M_MAX >= vals.T2M && vals.T2M >= vals.T2M_MIN, `Temp order violation ${provinceId} ${d}`);
    assert(vals.PRECTOTCORR >= 0, `Negative rain ${provinceId} ${d}`);
    assert(vals.RH2M >= 0 && vals.RH2M <= 100, `RH out of bounds ${provinceId} ${d}`);
    assert(vals.WS2M >= 0, `Negative wind ${provinceId} ${d}`);

    if (d === '20240115' || d === '20240715') {
      sigSamples.push(`${vals.T2M},${vals.PRECTOTCORR},${vals.RH2M}`);
    }

    zonalRows.push({
      province_id: provinceId,
      province: provinceName,
      date: isoDate(d),
      time_standard: 'LST',
      spatial_method: 'gadm_area_weighted_zonal_mean',
      grid_cells_used: weights.length,
      T2M: vals.T2M,
      T2M_MAX: vals.T2M_MAX,
      T2M_MIN: vals.T2M_MIN,
      PRECTOTCORR: vals.PRECTOTCORR,
      RH2M: vals.RH2M,
      WS2M: vals.WS2M
    });
  }
  provinceSignatures.set(provinceId, sigSamples.join('|'));
}

assert.equal(zonalRows.length, 13 * 4018);
assert.equal(new Set(provinceSignatures.values()).size, 13, 'Expected all 13 provinces to have distinct zonal weather profiles');

// Also generate cleaned single-point provincial daily series for spatial sensitivity comparison
const singlePointRows = [];
for (const pt of weatherPoints) {
  const file = `data/raw/weather/${pt.id}_2014_2024.json`;
  const cached = fileCache.get(file);
  const provinceName = overlap.find(r => r.province_id === pt.id).province;
  for (const d of referenceDates) {
    const vals = {};
    for (const k of PARAMS) vals[k] = Number(cached.parameter[k][d].toFixed(4));
    singlePointRows.push({
      province_id: pt.id,
      province: provinceName,
      date: isoDate(d),
      time_standard: cached.time_standard,
      spatial_method: 'single_acquisition_point',
      grid_cells_used: 1,
      T2M: vals.T2M,
      T2M_MAX: vals.T2M_MAX,
      T2M_MIN: vals.T2M_MIN,
      PRECTOTCORR: vals.PRECTOTCORR,
      RH2M: vals.RH2M,
      WS2M: vals.WS2M
    });
  }
}
assert.equal(singlePointRows.length, 13 * 4018);

writeCSV('data/interim/weather_daily_province_zonal.csv', zonalRows);
writeCSV('data/interim/weather_daily_province_single_point.csv', singlePointRows);

const status = {
  generated_at: new Date().toISOString(),
  provinces: 13,
  date_start: '2014-01-01',
  date_end: '2024-12-31',
  days_per_province: 4018,
  zonal_rows: zonalRows.length,
  single_point_rows: singlePointRows.length,
  common_parameters: PARAMS,
  excluded_optional_parameter: 'ALLSKY_SFC_SW_DWN',
  distinct_zonal_province_profiles: new Set(provinceSignatures.values()).size,
  missing_values: 0,
  physical_violations: 0
};
fs.writeFileSync('docs/weather_cleaning_status.json', JSON.stringify(status, null, 2));
console.log(JSON.stringify(status, null, 2));
