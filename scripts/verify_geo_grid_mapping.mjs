import fs from 'node:fs';
import crypto from 'node:crypto';
import assert from 'node:assert/strict';
import {writeCSV} from './lib/csv.mjs';

// Spatial verification and overlap inventory between GADM v4.1 Vietnam Level-1 (pre-2025 13 Mekong provinces)
// and the 30-cell NASA POWER MERRA-2 0.5° x 0.625° grid (config/weather_grid.json).
// Does NOT clean or aggregate weather values; produces the raw spatial overlap catalog required as input for Cleaning.

const geoPath = 'data/raw/geo/gadm41_VNM_1.json';
const geoBytes = fs.readFileSync(geoPath);
const geoSha = crypto.createHash('sha256').update(geoBytes).digest('hex');
const geo = JSON.parse(geoBytes.toString('utf8'));
assert.equal(geo.type, 'FeatureCollection');
assert.equal(geo.features.length, 63, 'Expected 63 pre-2025 Vietnam provinces in GADM v4.1');

const mekongMap = [
  ['long_an', 'Long An', 'LongAn'],
  ['tien_giang', 'Tiền Giang', 'TiềnGiang'],
  ['ben_tre', 'Bến Tre', 'BếnTre'],
  ['tra_vinh', 'Trà Vinh', 'TràVinh'],
  ['vinh_long', 'Vĩnh Long', 'VĩnhLong'],
  ['dong_thap', 'Đồng Tháp', 'ĐồngTháp'],
  ['an_giang', 'An Giang', 'AnGiang'],
  ['kien_giang', 'Kiên Giang', 'KiênGiang'],
  ['can_tho', 'Cần Thơ', 'CầnThơ'],
  ['hau_giang', 'Hậu Giang', 'HậuGiang'],
  ['soc_trang', 'Sóc Trăng', 'SócTrăng'],
  ['bac_lieu', 'Bạc Liêu', 'BạcLiêu'],
  ['ca_mau', 'Cà Mau', 'CàMau']
];

const pointInRing = (lon, lat, ring) => {
  let inside = false;
  for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) {
    const [xi, yi] = ring[i];
    const [xj, yj] = ring[j];
    const intersect = (yi > lat) !== (yj > lat) && lon < ((xj - xi) * (lat - yi)) / (yj - yi) + xi;
    if (intersect) inside = !inside;
  }
  return inside;
};

const pointInPolygon = (lon, lat, coords) => {
  if (!pointInRing(lon, lat, coords[0])) return false;
  for (let h = 1; h < coords.length; h++) {
    if (pointInRing(lon, lat, coords[h])) return false;
  }
  return true;
};

const pointInFeature = (lon, lat, geom) => {
  if (geom.type === 'Polygon') return pointInPolygon(lon, lat, geom.coordinates);
  if (geom.type === 'MultiPolygon') return geom.coordinates.some(poly => pointInPolygon(lon, lat, poly));
  return false;
};

const bboxOfGeom = geom => {
  let minLon = Infinity, maxLon = -Infinity, minLat = Infinity, maxLat = -Infinity;
  const walk = arr => {
    if (typeof arr[0] === 'number') {
      if (arr[0] < minLon) minLon = arr[0];
      if (arr[0] > maxLon) maxLon = arr[0];
      if (arr[1] < minLat) minLat = arr[1];
      if (arr[1] > maxLat) maxLat = arr[1];
    } else for (const sub of arr) walk(sub);
  };
  walk(geom.coordinates);
  return {minLon, maxLon, minLat, maxLat};
};

const provinces = mekongMap.map(([province_id, province, gadm_name]) => {
  const feat = geo.features.find(f => f.properties?.NAME_1 === gadm_name);
  assert(feat, `Missing GADM feature for ${province} (${gadm_name})`);
  return {province_id, province, gadm_name, geometry: feat.geometry, bbox: bboxOfGeom(feat.geometry)};
});
assert.equal(provinces.length, 13);

const grid = JSON.parse(fs.readFileSync('config/weather_grid.json', 'utf8'));
const [dLat, dLon] = grid.resolution_degrees; // 0.5, 0.625
const N = 20; // 20 x 20 = 400 regular sub-samples per MERRA-2 grid cell

const overlapRows = [];
const provinceTotals = new Map(provinces.map(p => [p.province_id, 0]));
const cellInMekong = new Map();

for (const cell of grid.points) {
  const latMin = cell.latitude - dLat / 2;
  const latMax = cell.latitude + dLat / 2;
  const lonMin = cell.longitude - dLon / 2;
  const lonMax = cell.longitude + dLon / 2;
  const weatherFile = cell.reuse_file || `data/raw/weather_grid/${cell.id}_2014_2024.json`;
  assert(fs.existsSync(weatherFile), `Missing weather JSON for ${cell.id}: ${weatherFile}`);

  // Pre-filter provinces whose bbox overlaps this cell
  const candidates = provinces.filter(
    p => p.bbox.maxLon >= lonMin && p.bbox.minLon <= lonMax && p.bbox.maxLat >= latMin && p.bbox.minLat <= latMax
  );
  const hitCounts = new Map(candidates.map(p => [p.province_id, 0]));

  if (candidates.length > 0) {
    for (let iy = 0; iy < N; iy++) {
      const lat = latMin + ((iy + 0.5) / N) * dLat;
      for (let ix = 0; ix < N; ix++) {
        const lon = lonMin + ((ix + 0.5) / N) * dLon;
        for (const p of candidates) {
          if (lon < p.bbox.minLon || lon > p.bbox.maxLon || lat < p.bbox.minLat || lat > p.bbox.maxLat) continue;
          if (pointInFeature(lon, lat, p.geometry)) {
            hitCounts.set(p.province_id, hitCounts.get(p.province_id) + 1);
            break; // Disjoint provinces
          }
        }
      }
    }
  }

  let anyHit = false;
  for (const p of candidates) {
    const hits = hitCounts.get(p.province_id);
    if (hits > 0) {
      anyHit = true;
      provinceTotals.set(p.province_id, provinceTotals.get(p.province_id) + hits);
      overlapRows.push({
        province_id: p.province_id,
        province: p.province,
        gadm_name_1: p.gadm_name,
        grid_id: cell.id,
        cell_key: cell.cell_key,
        cell_center_lat: cell.latitude,
        cell_center_lon: cell.longitude,
        weather_source_file: weatherFile,
        subgrid_hits: hits,
        subgrid_total_per_cell: N * N,
        cell_area_fraction: Number((hits / (N * N)).toFixed(4)),
        province_weight_placeholder: ''
      });
    }
  }
  cellInMekong.set(cell.id, anyHit);
}

// Compute normalized province-level area weights across overlapping MERRA-2 cells
for (const r of overlapRows) {
  const totalHits = provinceTotals.get(r.province_id);
  r.province_weight_placeholder = Number((r.subgrid_hits / totalHits).toFixed(6));
}

// Assertions: all 13 Mekong provinces must be covered and weights sum to ~1
const byProvince = provinces.map(p => {
  const pRows = overlapRows.filter(r => r.province_id === p.province_id);
  assert(pRows.length >= 1, `Province ${p.province} has zero overlapping MERRA-2 cells`);
  const sumW = pRows.reduce((s, r) => s + r.province_weight_placeholder, 0);
  assert(Math.abs(sumW - 1) < 1e-4, `Weights for ${p.province} do not sum to 1: ${sumW}`);
  return {
    province_id: p.province_id,
    province: p.province,
    overlapping_grid_cells: pRows.length,
    cell_keys: pRows.map(r => r.cell_key)
  };
});

// Check whether every province now gets a distinct cell/weight fingerprint
const fingerprints = new Map();
for (const p of provinces) {
  const fp = overlapRows
    .filter(r => r.province_id === p.province_id)
    .map(r => `${r.cell_key}:${r.province_weight_placeholder}`)
    .sort()
    .join('|');
  (fingerprints.get(fp) || fingerprints.set(fp, []).get(fp)).push(p.province_id);
}
const duplicateFingerprints = [...fingerprints.values()].filter(v => v.length > 1);
assert.equal(duplicateFingerprints.length, 0, `Duplicate province spatial weights detected: ${JSON.stringify(duplicateFingerprints)}`);

const outRows = overlapRows.map(({province_weight_placeholder, ...rest}) => ({
  ...rest,
  province_area_weight: province_weight_placeholder,
  boundary_source_file: geoPath,
  boundary_source_sha256: geoSha
}));
writeCSV('data/catalog/weather_grid_province_overlap.csv', outRows);

const offMekongCells = [...cellInMekong.entries()].filter(([, inside]) => !inside).map(([id]) => id);
const status = {
  generated_at: new Date().toISOString(),
  boundary_file: geoPath,
  boundary_sha256: geoSha,
  total_vietnam_provinces_in_boundary: geo.features.length,
  mekong_provinces_matched: provinces.length,
  total_weather_grid_cells: grid.points.length,
  cells_overlapping_mekong_delta: grid.points.length - offMekongCells.length,
  cells_outside_mekong_or_offshore: offMekongCells.length,
  offshore_or_outside_cell_ids: offMekongCells,
  province_grid_overlap_rows: outRows.length,
  distinct_province_weight_profiles: fingerprints.size,
  by_province: byProvince,
  cleaning_or_weather_aggregation_performed: false
};
fs.writeFileSync('docs/geo_grid_mapping_status.json', JSON.stringify(status, null, 2));
console.log(JSON.stringify(status, null, 2));
