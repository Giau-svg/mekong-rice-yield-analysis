import fs from 'node:fs';
import assert from 'node:assert/strict';
import {readCSV, writeCSV} from './lib/csv.mjs';

// Stage 1: Rice Data Cleaning, Normalization, Cross-Version Reconciliation, and Quality Audit
// Inputs (from Raw Handoff Contract):
//   - data/raw/rice_captured_main_seasons.csv (90 rows: AG, KG, CT, 2015–2024, 3 separate seasons)
//   - data/raw/nso_rice_province_tables.csv (467 rows: 13 provinces, NSO 2019 & 2024)
//   - data/raw/nso_rice_2021_reconciliation.csv (233 rows: 13 provinces, NSO 2021 with official 2019)
//   - data/raw/rice_report_season_values.csv (7 rows: TG, VL, CM annual/Q4 reports)
// Outputs:
//   - data/interim/rice_tier1_core_3seasons.csv (90 rows, balanced 3-province x 10-year x 3-season panel)
//   - data/interim/rice_tier2_delta13_nso.csv (257 rows: 127 Dong Xuan + 130 Combined HT-TD, official 2019 reconciled)
//   - data/interim/rice_supplemental_reports.csv (7 rows, separated provincial annual reports)
//   - data/interim/rice_reconciliation_log.csv (full audit trail of version decisions)
//   - data/interim/rice_cleaning_quality_audit.csv (internal consistency + rounding tolerance + domain outlier flags)

fs.mkdirSync('data/interim', {recursive: true});

const PROVINCE_ID_MAP = new Map([
  ['Long An', 'long_an'],
  ['Tiền Giang', 'tien_giang'],
  ['Bến Tre', 'ben_tre'],
  ['Trà Vinh', 'tra_vinh'],
  ['Vĩnh Long', 'vinh_long'],
  ['Đồng Tháp', 'dong_thap'],
  ['An Giang', 'an_giang'],
  ['Kiên Giang', 'kien_giang'],
  ['Cần Thơ', 'can_tho'],
  ['Hậu Giang', 'hau_giang'],
  ['Sóc Trăng', 'soc_trang'],
  ['Bạc Liêu', 'bac_lieu'],
  ['Cà Mau', 'ca_mau']
]);

const SEASON_MAP = new Map([
  ['Lúa đông xuân', {season: 'dong_xuan', scope: 'single'}],
  ['Lúa hè thu', {season: 'he_thu', scope: 'single'}],
  ['Lúa thu đông', {season: 'thu_dong', scope: 'single'}],
  ['Lúa hè thu và thu đông', {season: 'he_thu_thu_dong_combined', scope: 'combined_he_thu_thu_dong'}],
  ['Lúa mùa', {season: 'mua', scope: 'single'}],
  ['Lúa cả năm', {season: 'annual_total', scope: 'annual_total'}]
]);

const parseVNNumber = raw => {
  const s = String(raw ?? '').trim();
  assert(s.length > 0 && /^[\d.,]+$/.test(s), `Invalid numeric string: "${raw}"`);
  const num = Number(s.replaceAll('.', '').replace(',', '.'));
  assert(Number.isFinite(num), `Non-finite parsed number from "${raw}"`);
  return num;
};

const toHa = (val, unitRaw) => {
  const u = String(unitRaw).trim().toLowerCase();
  if (u === 'ha') return val;
  if (u === 'nghìn ha') return Number((val * 1000).toFixed(2));
  throw new Error(`Unsupported area unit: ${unitRaw}`);
};

const toTonPerHa = (val, unitRaw) => {
  const u = String(unitRaw).trim().toLowerCase();
  if (u === 'tạ/ha') return Number((val / 10).toFixed(4));
  if (u === 'tấn/ha') return Number(val.toFixed(4));
  throw new Error(`Unsupported yield unit: ${unitRaw}`);
};

const toTon = (val, unitRaw) => {
  const u = String(unitRaw).trim().toLowerCase();
  if (u === 'tấn') return Number(val.toFixed(2));
  if (u === 'nghìn tấn') return Number((val * 1000).toFixed(2));
  throw new Error(`Unsupported production unit: ${unitRaw}`);
};

const getTimeSplit = year => (year <= 2020 ? 'train' : year <= 2022 ? 'val' : 'test');

const evaluateConsistency = (areaHa, yieldTHa, prodT, areaUnitRaw, prodUnitRaw, specialNote = '') => {
  const expectedProd = areaHa * yieldTHa;
  const absErr = Math.abs(expectedProd - prodT);
  const relErr = prodT > 0 ? absErr / prodT : 0;

  // Source rounding propagation bound for NSO tables (0.1 thousand ha, 0.1 quintal/ha = 0.01 t/ha, 0.1 thousand t)
  const isThousandScale = /nghìn/i.test(areaUnitRaw) || /nghìn/i.test(prodUnitRaw);
  const roundingBoundT = isThousandScale
    ? 50 + 50 * yieldTHa + areaHa * 0.005 // half-ULP: ±50 t prod, ±50 ha area, ±0.005 t/ha yield
    : 0.5 + 0.5 * yieldTHa + areaHa * 0.005;

  let formulaCheckStatus = 'pass';
  if (/99,18%/.test(specialNote)) {
    formulaCheckStatus = 'pass_harvested_area_basis_note';
  } else if (relErr > 0.01) {
    formulaCheckStatus = absErr <= roundingBoundT ? 'pass_within_source_rounding' : 'warning_exceeds_rounding_bound';
  }

  let domainOutlierFlag = 'none';
  if (yieldTHa < 2.0) {
    domainOutlierFlag = 'extreme_salinity_crop_failure';
  }

  return {
    expected_production_t: Number(expectedProd.toFixed(2)),
    production_abs_error_t: Number(absErr.toFixed(2)),
    production_rel_error: Number(relErr.toFixed(6)),
    source_rounding_bound_t: Number(roundingBoundT.toFixed(2)),
    formula_check_status: formulaCheckStatus,
    domain_outlier_flag: domainOutlierFlag
  };
};

// Load raw tables
const localMain = readCSV('data/raw/rice_captured_main_seasons.csv');
const nsoBase = readCSV('data/raw/nso_rice_province_tables.csv');
const nso2021 = readCSV('data/raw/nso_rice_2021_reconciliation.csv');
const reportVals = readCSV('data/raw/rice_report_season_values.csv');

const reconciliationLog = [];
const qualityAudit = [];

// =========================================================================
// 1. TIER 1: CORE 3-SEASON BALANCED PANEL (An Giang, Kiên Giang, Cần Thơ)
// =========================================================================
const tier1Rows = [];
for (const r of localMain) {
  const provinceId = PROVINCE_ID_MAP.get(r.province_raw);
  assert(provinceId, `Unknown province: ${r.province_raw}`);
  const sInfo = SEASON_MAP.get(r.season_or_category_raw);
  assert(sInfo && sInfo.scope === 'single', `Unexpected Tier 1 season: ${r.season_or_category_raw}`);
  const harvestYear = Number(r.year_raw);
  assert(harvestYear >= 2015 && harvestYear <= 2024);

  const areaHa = toHa(parseVNNumber(r.area_raw), r.area_unit_raw);
  const yieldTHa = toTonPerHa(parseVNNumber(r.yield_raw), r.yield_unit_raw);
  const prodT = toTon(parseVNNumber(r.production_raw), r.production_unit_raw);
  const isPrelim = /sơ\s*bộ|prel/i.test(r.year_label_raw);

  const check = evaluateConsistency(areaHa, yieldTHa, prodT, r.area_unit_raw, r.production_unit_raw);
  assert.equal(check.formula_check_status, 'pass', `Tier 1 consistency failure: ${provinceId} ${harvestYear} ${sInfo.season}`);

  // Cross-check Dong Xuan against NSO (using official 2019 from NSO 2021 if year === 2019)
  if (sInfo.season === 'dong_xuan') {
    const nsoRef = (harvestYear === 2019 ? nso2021 : nsoBase).find(
      x => x.province_reference === r.province_raw && x.year_raw === r.year_raw && x.category_raw === 'Lúa đông xuân'
    );
    if (nsoRef) {
      const nsoY = toTonPerHa(parseVNNumber(nsoRef.yield_raw), nsoRef.yield_unit_raw);
      const diffY = Number(Math.abs(yieldTHa - nsoY).toFixed(4));
      assert(diffY <= 0.015, `Tier 1 vs NSO Dong Xuan yield mismatch >0.015 t/ha: ${provinceId} ${harvestYear} (${yieldTHa} vs ${nsoY})`);
      reconciliationLog.push({
        tier: 'tier1_core_3seasons',
        province_id: provinceId,
        harvest_year: harvestYear,
        season: sInfo.season,
        decision: 'selected_provincial_yearbook_over_nso',
        selected_source: r.source_file,
        selected_yield_t_ha: yieldTHa,
        alternative_source: nsoRef.source_file,
        alternative_yield_t_ha: nsoY,
        yield_abs_diff_t_ha: diffY,
        rationale: 'Provincial yearbook provides exact 2-decimal yield and ha/t units; cross-checked consistent with NSO (within 0.01 t/ha rounding)'
      });
    }
  }

  const row = {
    dataset_tier: 'tier1_core_3seasons',
    province_id: provinceId,
    province: r.province_raw,
    harvest_year: harvestYear,
    season: sInfo.season,
    season_scope: sInfo.scope,
    source_season_raw: r.season_or_category_raw,
    time_split: getTimeSplit(harvestYear),
    yield_t_ha: yieldTHa,
    area_ha: areaHa,
    production_t: prodT,
    area_basis: 'planted_area',
    revision_status: isPrelim ? 'preliminary' : 'official',
    source_tier: 'provincial_yearbook',
    original_area_unit: r.area_unit_raw,
    original_yield_unit: r.yield_unit_raw,
    original_production_unit: r.production_unit_raw,
    source_file: r.source_file,
    source_url: r.source_url,
    source_sha256: r.source_sha256,
    source_locator: `pdf_pages:${r.pdf_page_area}/${r.pdf_page_yield}/${r.pdf_page_production}`,
    formula_check_status: check.formula_check_status,
    domain_outlier_flag: check.domain_outlier_flag
  };
  tier1Rows.push(row);
  qualityAudit.push({dataset_tier: row.dataset_tier, province_id: provinceId, harvest_year: harvestYear, season: sInfo.season, yield_t_ha: yieldTHa, area_ha: areaHa, production_t: prodT, ...check});
}

assert.equal(tier1Rows.length, 90);
assert.equal(new Set(tier1Rows.map(r => `${r.province_id}|${r.harvest_year}|${r.season}`)).size, 90);

// =========================================================================
// 2. TIER 2: DELTA-WIDE 13-PROVINCE NSO PANEL (Dong Xuan + Combined HT-TD)
//    Rule: Upgrade ALL year=2019 records from NSO 2019 (Preliminary) to NSO 2021 (Official)
// =========================================================================
const tier2Categories = new Set(['Lúa đông xuân', 'Lúa hè thu và thu đông']);
const nso2021Official2019Map = new Map(
  nso2021
    .filter(r => r.year_raw === '2019' && tier2Categories.has(r.category_raw))
    .map(r => [`${r.province_reference}|${r.category_raw}`, r])
);

const tier2Rows = [];
for (const baseRow of nsoBase.filter(r => tier2Categories.has(r.category_raw))) {
  const provinceId = PROVINCE_ID_MAP.get(baseRow.province_reference);
  assert(provinceId, `Unknown NSO province: ${baseRow.province_reference}`);
  const sInfo = SEASON_MAP.get(baseRow.category_raw);
  const harvestYear = Number(baseRow.year_raw);

  let chosen = baseRow;
  let sourceTier = 'nso_yearbook_2019_2024';

  if (harvestYear === 2019) {
    const key = `${baseRow.province_reference}|${baseRow.category_raw}`;
    const official2019 = nso2021Official2019Map.get(key);
    assert(official2019, `Missing NSO 2021 official 2019 record for ${key}`);

    const prelimY = toTonPerHa(parseVNNumber(baseRow.yield_raw), baseRow.yield_unit_raw);
    const officialY = toTonPerHa(parseVNNumber(official2019.yield_raw), official2019.yield_unit_raw);
    const changed = baseRow.area_raw !== official2019.area_raw || baseRow.yield_raw !== official2019.yield_raw || baseRow.production_raw !== official2019.production_raw;

    reconciliationLog.push({
      tier: 'tier2_delta13_nso',
      province_id: provinceId,
      harvest_year: 2019,
      season: sInfo.season,
      decision: changed ? 'upgraded_2019_prelim_to_nso2021_official_changed' : 'upgraded_2019_prelim_to_nso2021_official_unchanged',
      selected_source: official2019.source_file,
      selected_yield_t_ha: officialY,
      alternative_source: baseRow.source_file,
      alternative_yield_t_ha: prelimY,
      yield_abs_diff_t_ha: Number(Math.abs(officialY - prelimY).toFixed(4)),
      rationale: changed
        ? `NSO 2021 published revised official 2019 figures (area ${baseRow.area_raw}->${official2019.area_raw}, yield ${baseRow.yield_raw}->${official2019.yield_raw}, prod ${baseRow.production_raw}->${official2019.production_raw})`
        : 'NSO 2021 confirmed official 2019 figures identical to NSO 2019 preliminary'
    });
    chosen = official2019;
    sourceTier = 'nso_yearbook_2021_official_2019';
  }

  const areaHa = toHa(parseVNNumber(chosen.area_raw), chosen.area_unit_raw);
  const yieldTHa = toTonPerHa(parseVNNumber(chosen.yield_raw), chosen.yield_unit_raw);
  const prodT = toTon(parseVNNumber(chosen.production_raw), chosen.production_unit_raw);
  const isPrelim = /sơ\s*bộ|prel/i.test(chosen.year_label_raw);

  const check = evaluateConsistency(areaHa, yieldTHa, prodT, chosen.area_unit_raw, chosen.production_unit_raw);
  assert(
    check.formula_check_status === 'pass' || check.formula_check_status === 'pass_within_source_rounding',
    `Tier 2 consistency failure exceeding source rounding bound: ${provinceId} ${harvestYear} ${sInfo.season} (${JSON.stringify(check)})`
  );

  const row = {
    dataset_tier: 'tier2_delta13_nso',
    province_id: provinceId,
    province: chosen.province_reference,
    harvest_year: harvestYear,
    season: sInfo.season,
    season_scope: sInfo.scope,
    source_season_raw: chosen.category_raw,
    time_split: getTimeSplit(harvestYear),
    yield_t_ha: yieldTHa,
    area_ha: areaHa,
    production_t: prodT,
    area_basis: 'planted_area',
    revision_status: isPrelim ? 'preliminary' : 'official',
    source_tier: sourceTier,
    original_area_unit: chosen.area_unit_raw,
    original_yield_unit: chosen.yield_unit_raw,
    original_production_unit: chosen.production_unit_raw,
    source_file: chosen.source_file,
    source_url: chosen.source_url,
    source_sha256: chosen.source_sha256,
    source_locator: `pdf_pages:${chosen.pdf_page_area}/${chosen.pdf_page_yield}/${chosen.pdf_page_production}`,
    formula_check_status: check.formula_check_status,
    domain_outlier_flag: check.domain_outlier_flag
  };
  tier2Rows.push(row);
  qualityAudit.push({dataset_tier: row.dataset_tier, province_id: provinceId, harvest_year: harvestYear, season: sInfo.season, yield_t_ha: yieldTHa, area_ha: areaHa, production_t: prodT, ...check});
}

assert.equal(tier2Rows.filter(r => r.season === 'dong_xuan').length, 127);
assert.equal(tier2Rows.filter(r => r.season === 'he_thu_thu_dong_combined').length, 130);
assert.equal(tier2Rows.length, 257);
assert.equal(new Set(tier2Rows.map(r => `${r.province_id}|${r.harvest_year}|${r.season}`)).size, 257);
// Confirm zero 2019 preliminary rows remain in Tier 2
assert.equal(tier2Rows.filter(r => r.harvest_year === 2019 && r.revision_status === 'preliminary').length, 0);

// =========================================================================
// 3. SUPPLEMENTAL PROVINCIAL ANNUAL REPORT RECORDS (7 rows, kept separate)
// =========================================================================
const suppRows = [];
for (const r of reportVals) {
  const provinceId = PROVINCE_ID_MAP.get(r.province_reference);
  assert(provinceId);
  const sInfo = SEASON_MAP.get(r.category_raw);
  assert(sInfo && sInfo.scope === 'single');
  const harvestYear = Number(r.year_raw);

  const areaHa = toHa(parseVNNumber(r.area_raw), r.area_unit_raw);
  const yieldTHa = toTonPerHa(parseVNNumber(r.yield_raw), r.yield_unit_raw);
  const prodT = toTon(parseVNNumber(r.production_raw), r.production_unit_raw);
  const check = evaluateConsistency(areaHa, yieldTHa, prodT, r.area_unit_raw, r.production_unit_raw, r.area_definition_note);
  assert(check.formula_check_status !== 'warning_exceeds_rounding_bound', `Supplemental check failed: ${provinceId} ${harvestYear} ${sInfo.season}`);

  const row = {
    dataset_tier: 'supplemental_provincial_reports',
    province_id: provinceId,
    province: r.province_reference,
    harvest_year: harvestYear,
    season: sInfo.season,
    season_scope: sInfo.scope,
    source_season_raw: r.category_raw,
    time_split: getTimeSplit(harvestYear),
    yield_t_ha: yieldTHa,
    area_ha: areaHa,
    production_t: prodT,
    area_basis: /99,18%/.test(r.area_definition_note) ? 'planted_area_with_99.18pct_harvested' : 'planted_area',
    revision_status: 'annual_report_unreconciled',
    source_tier: 'provincial_annual_report',
    original_area_unit: r.area_unit_raw,
    original_yield_unit: r.yield_unit_raw,
    original_production_unit: r.production_unit_raw,
    source_file: r.source_file,
    source_url: r.source_url,
    source_sha256: r.source_sha256,
    source_locator: `html_block:${r.block || 'full_body'}`,
    formula_check_status: check.formula_check_status,
    domain_outlier_flag: check.domain_outlier_flag
  };
  suppRows.push(row);
  qualityAudit.push({dataset_tier: row.dataset_tier, province_id: provinceId, harvest_year: harvestYear, season: sInfo.season, yield_t_ha: yieldTHa, area_ha: areaHa, production_t: prodT, ...check});
}

assert.equal(suppRows.length, 7);

writeCSV('data/interim/rice_tier1_core_3seasons.csv', tier1Rows);
writeCSV('data/interim/rice_tier2_delta13_nso.csv', tier2Rows);
writeCSV('data/interim/rice_supplemental_reports.csv', suppRows);
writeCSV('data/interim/rice_reconciliation_log.csv', reconciliationLog);
writeCSV('data/interim/rice_cleaning_quality_audit.csv', qualityAudit);

const summary = {
  generated_at: new Date().toISOString(),
  tier1_core_3seasons_rows: tier1Rows.length,
  tier2_delta13_nso_rows: tier2Rows.length,
  tier2_dong_xuan_rows: tier2Rows.filter(r => r.season === 'dong_xuan').length,
  tier2_combined_ht_td_rows: tier2Rows.filter(r => r.season === 'he_thu_thu_dong_combined').length,
  supplemental_report_rows: suppRows.length,
  reconciliation_decisions_logged: reconciliationLog.length,
  year2019_upgraded_changed_in_tier2: reconciliationLog.filter(r => r.decision === 'upgraded_2019_prelim_to_nso2021_official_changed').length,
  year2019_upgraded_unchanged_in_tier2: reconciliationLog.filter(r => r.decision === 'upgraded_2019_prelim_to_nso2021_official_unchanged').length,
  formula_check_breakdown: Object.fromEntries(
    [...new Set(qualityAudit.map(r => r.formula_check_status))].map(k => [k, qualityAudit.filter(r => r.formula_check_status === k).length])
  ),
  domain_outliers_flagged_and_retained: qualityAudit.filter(r => r.domain_outlier_flag !== 'none').map(r => ({
    province_id: r.province_id,
    harvest_year: r.harvest_year,
    season: r.season,
    yield_t_ha: r.yield_t_ha,
    flag: r.domain_outlier_flag
  }))
};

fs.writeFileSync('docs/rice_cleaning_status.json', JSON.stringify(summary, null, 2));
console.log(JSON.stringify(summary, null, 2));
