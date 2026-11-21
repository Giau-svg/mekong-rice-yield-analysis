import fs from 'node:fs';
import assert from 'node:assert/strict';
import {readCSV, writeCSV} from './lib/csv.mjs';

// Stage 3: Clean Crop Calendar Construction + Mandatory Sensitivity Shifts (±10, ±15 days)
// Grounded directly in data/raw/season_calendar_raw.csv (official MARD/DCP regional & subregional
// directives + ~100-105 day short-duration rice growth cycle in Mekong Delta).
// Transparently tagged as Tier B (official subregional framework) — NOT claimed as field-level observed dates.

fs.mkdirSync('data/interim', {recursive: true});

const rawCal = readCSV('data/raw/season_calendar_raw.csv');
const byId = new Map(rawCal.map(r => [r.calendar_record_id, r]));
for (const req of ['MARD_DCP_3CROP_DX', 'MARD_DCP_3CROP_HT', 'MARD_DCP_3CROP_TD', 'MARD_HT2020_SUBREGIONS', 'MARD_DX2014_2015_COASTAL', 'NAEC_VARIETY_DURATION_REF']) {
  assert(byId.has(req), `Missing required official raw calendar record: ${req}`);
}

// Subregional ecological grouping directly aligned with MARD/DCP directives (MARD_HT2020_SUBREGIONS & MARD_DX2014_2015_*)
const PROVINCE_SUBREGION = [
  ['an_giang', 'An Giang', 'upstream_alluvial_3crop'],
  ['dong_thap', 'Đồng Tháp', 'upstream_alluvial_3crop'],
  ['can_tho', 'Cần Thơ', 'upstream_alluvial_3crop'],
  ['kien_giang', 'Kiên Giang', 'upstream_alluvial_3crop'],
  ['vinh_long', 'Vĩnh Long', 'middle_south_ql1'],
  ['tien_giang', 'Tiền Giang', 'middle_south_ql1'],
  ['hau_giang', 'Hậu Giang', 'middle_south_ql1'],
  ['soc_trang', 'Sóc Trăng', 'middle_south_ql1'],
  ['long_an', 'Long An', 'middle_south_ql1'],
  ['ben_tre', 'Bến Tre', 'coastal_salinity_prone'],
  ['tra_vinh', 'Trà Vinh', 'coastal_salinity_prone'],
  ['bac_lieu', 'Bạc Liêu', 'coastal_salinity_prone'],
  ['ca_mau', 'Cà Mau', 'coastal_salinity_prone']
];

// Primary growing windows (sowing peak -> main harvest end, ~107–123 days covering 100–105d cycle + staggered sowing)
// Dong Xuan spans harvest_year - 1 -> harvest_year (startYearOffset = -1).
const SUBREGION_WINDOWS = {
  upstream_alluvial_3crop: {
    dong_xuan: {startYOff: -1, startMD: '11-15', endYOff: 0, endMD: '03-15', refs: 'MARD_DCP_3CROP_DX;MARD_DX2014_2015_ALLUVIAL;MARD_DX2018_2019_SUMMARY;NAEC_VARIETY_DURATION_REF'},
    he_thu: {startYOff: 0, startMD: '04-15', endYOff: 0, endMD: '07-31', refs: 'MARD_DCP_3CROP_HT;MARD_HT2019_SUBREGIONS;MARD_HT2020_SUBREGIONS;NAEC_VARIETY_DURATION_REF'},
    thu_dong: {startYOff: 0, startMD: '07-25', endYOff: 0, endMD: '11-15', refs: 'MARD_DCP_3CROP_TD;MARD_TD2024_HARVEST_REF;NAEC_VARIETY_DURATION_REF'},
    he_thu_thu_dong_combined: {startYOff: 0, startMD: '04-15', endYOff: 0, endMD: '11-15', refs: 'MARD_DCP_3CROP_HT;MARD_DCP_3CROP_TD;MARD_HT2020_SUBREGIONS'}
  },
  middle_south_ql1: {
    dong_xuan: {startYOff: -1, startMD: '11-10', endYOff: 0, endMD: '03-10', refs: 'MARD_DCP_3CROP_DX;MARD_DX2014_2015_ALLUVIAL;MARD_DX2018_2019_SUMMARY;NAEC_VARIETY_DURATION_REF'},
    he_thu: {startYOff: 0, startMD: '05-01', endYOff: 0, endMD: '08-15', refs: 'MARD_HT2019_SUBREGIONS;MARD_HT2020_SUBREGIONS;NAEC_VARIETY_DURATION_REF'},
    thu_dong: {startYOff: 0, startMD: '08-01', endYOff: 0, endMD: '11-20', refs: 'MARD_DCP_3CROP_TD;VL_TD2024_PROGRESS;NAEC_VARIETY_DURATION_REF'},
    he_thu_thu_dong_combined: {startYOff: 0, startMD: '05-01', endYOff: 0, endMD: '11-20', refs: 'MARD_HT2019_SUBREGIONS;MARD_HT2020_SUBREGIONS;MARD_DCP_3CROP_TD'}
  },
  coastal_salinity_prone: {
    dong_xuan: {startYOff: -1, startMD: '10-25', endYOff: 0, endMD: '02-25', refs: 'MARD_DX2014_2015_COASTAL;MARD_DX2018_2019_SUMMARY;CM_DX_YEAR_CONVENTION;NAEC_VARIETY_DURATION_REF'},
    he_thu: {startYOff: 0, startMD: '05-15', endYOff: 0, endMD: '08-31', refs: 'MARD_DCP_2CROP_HT;MARD_HT2019_SUBREGIONS;MARD_HT2020_SUBREGIONS;NAEC_VARIETY_DURATION_REF'},
    thu_dong: {startYOff: 0, startMD: '08-01', endYOff: 0, endMD: '11-20', refs: 'MARD_DCP_3CROP_TD;NAEC_VARIETY_DURATION_REF'},
    he_thu_thu_dong_combined: {startYOff: 0, startMD: '05-15', endYOff: 0, endMD: '11-20', refs: 'MARD_DCP_2CROP_HT;MARD_HT2020_SUBREGIONS;MARD_DCP_3CROP_TD'}
  }
};

const addDaysISO = (isoStr, deltaDays) => {
  const [y, m, d] = isoStr.split('-').map(Number);
  const dt = new Date(Date.UTC(y, m - 1, d + deltaDays));
  const yy = dt.getUTCFullYear();
  const mm = String(dt.getUTCMonth() + 1).padStart(2, '0');
  const dd = String(dt.getUTCDate()).padStart(2, '0');
  return `${yy}-${mm}-${dd}`;
};

const daysInclusive = (startISO, endISO) => {
  const s = Date.parse(startISO + 'T00:00:00Z');
  const e = Date.parse(endISO + 'T00:00:00Z');
  return Math.round((e - s) / 86400000) + 1;
};

const SHIFTS = [0, -15, -10, 10, 15];
const primaryRows = [];
const sensitivityRows = [];

for (const [province_id, province, subregion] of PROVINCE_SUBREGION) {
  const winMap = SUBREGION_WINDOWS[subregion];
  for (let harvest_year = 2015; harvest_year <= 2024; harvest_year++) {
    for (const [season, spec] of Object.entries(winMap)) {
      const baseStart = `${harvest_year + spec.startYOff}-${spec.startMD}`;
      const baseEnd = `${harvest_year + spec.endYOff}-${spec.endMD}`;
      const baseDur = daysInclusive(baseStart, baseEnd);
      assert(baseStart >= '2014-01-01' && baseEnd <= '2024-12-31', `Date out of 2014-2024 weather range: ${baseStart}..${baseEnd}`);
      assert(baseDur >= 95 && baseDur <= 225, `Unexpected season window length ${baseDur} for ${province_id} ${season}`);

      const sourceUrls = [...new Set(spec.refs.split(';').map(id => byId.get(id).source_url))].join(' | ');
      const tier = season === 'he_thu_thu_dong_combined' ? 'B_official_subregional_combined_window' : 'B_official_subregional_framework';

      for (const shift of SHIFTS) {
        const sDate = addDaysISO(baseStart, shift);
        const eDate = addDaysISO(baseEnd, shift);
        assert(sDate >= '2014-01-01' && eDate <= '2024-12-31', `Shifted date out of 2014-2024 weather range: ${sDate}..${eDate}`);
        const rec = {
          province_id,
          province,
          ecological_subregion: subregion,
          harvest_year,
          season,
          shift_days: shift,
          start_date: sDate,
          end_date: eDate,
          expected_window_days: daysInclusive(sDate, eDate),
          cross_calendar_year: sDate.slice(0, 4) !== eDate.slice(0, 4),
          calendar_tier: tier,
          calendar_record_ids: spec.refs,
          calendar_source_urls: sourceUrls
        };
        sensitivityRows.push(rec);
        if (shift === 0) primaryRows.push(rec);
      }
    }
  }
}

assert.equal(primaryRows.length, 13 * 10 * 4);
assert.equal(sensitivityRows.length, 13 * 10 * 4 * SHIFTS.length);

writeCSV('data/interim/season_calendar_clean.csv', primaryRows);
writeCSV('data/interim/season_calendar_sensitivity_shifts.csv', sensitivityRows);

// Also update config/season_calendar.csv to reflect the cleaned primary Tier B calendar (replacing old 3-row pilot stub)
writeCSV(
  'config/season_calendar.csv',
  primaryRows.filter(r => r.season !== 'he_thu_thu_dong_combined').map(r => ({
    province_id: r.province_id,
    harvest_year: r.harvest_year,
    season: r.season,
    start_date: r.start_date,
    end_date: r.end_date,
    calendar_source_url: r.calendar_source_urls,
    verification_status: r.calendar_tier
  }))
);

const status = {
  generated_at: new Date().toISOString(),
  provinces: 13,
  years: '2015–2024',
  primary_calendar_rows: primaryRows.length,
  sensitivity_calendar_rows: sensitivityRows.length,
  sensitivity_shifts_days: SHIFTS,
  subregion_counts: Object.fromEntries(
    ['upstream_alluvial_3crop', 'middle_south_ql1', 'coastal_salinity_prone'].map(s => [
      s,
      PROVINCE_SUBREGION.filter(([, , r]) => r === s).map(([, p]) => p)
    ])
  ),
  calendar_tier_note: 'Tier B official MARD/DCP subregional frameworks with ~100-105d growth cycle; NOT field-level annual observed dates. Mandatory ±10/±15-day sensitivity testing enabled.'
};
fs.writeFileSync('docs/calendar_cleaning_status.json', JSON.stringify(status, null, 2));
console.log(JSON.stringify(status, null, 2));
