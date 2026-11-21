import fs from 'node:fs';
import crypto from 'node:crypto';
import assert from 'node:assert/strict';
import {readCSV, writeCSV} from './lib/csv.mjs';

// Raw extraction from NSO Statistical Yearbook 2021 (Sach-Nien-giam-TK-2021.pdf)
// Purpose: provide official 2019 values (plus 2015, 2018, 2020, 2021 Prel.) for
// cross-version reconciliation against NSO 2019 (where 2019 was labeled Preliminary).
// Raw values and units are kept verbatim without cleaning or overwriting existing raw tables.

const source = {
  file: 'data/raw/crawl/209170160564dafbfc29.pdf',
  yearbook_edition: 'NSO_2021',
  years: [2015, 2018, 2019, 2020, 2021],
  pages: [
    [523, 525, 527], // Lúa cả năm
    [529, 531, 533], // Lúa đông xuân
    [534, 535, 536], // Lúa hè thu và thu đông
    [538, 540, 542]  // Lúa mùa
  ]
};

const provinces = [
  'Long An', 'Tiền Giang', 'Bến Tre', 'Trà Vinh', 'Vĩnh Long', 'Đồng Tháp',
  'An Giang', 'Kiên Giang', 'Cần Thơ', 'Hậu Giang', 'Sóc Trăng', 'Bạc Liêu', 'Cà Mau'
];
const categories = ['Lúa cả năm', 'Lúa đông xuân', 'Lúa hè thu và thu đông', 'Lúa mùa'];
const metrics = [['area', 'Nghìn ha'], ['yield', 'Tạ/ha'], ['production', 'Nghìn tấn']];
const reference = s => provinces.find(p => p.replaceAll(' ', '') === s.replaceAll(' ', ''));

const sha = crypto.createHash('sha256').update(fs.readFileSync(source.file)).digest('hex');
const index = JSON.parse(fs.readFileSync(`data/raw/pdf_text/${sha.slice(0, 20)}.json`, 'utf8'));

const rows = [];
const issues = [];

for (let c = 0; c < categories.length; c++) {
  const tables = [];
  for (let m = 0; m < metrics.length; m++) {
    const page = source.pages[c][m];
    const text = index.pages.find(p => p.page === page)?.text;
    assert(text, `Missing page ${page}`);
    for (const y of [2015, 2018, 2019, 2020]) {
      assert(text.includes(String(y)), `Year header mismatch on page ${page} for ${y}`);
    }
    const table = new Map();
    for (const line of text.split('\n')) {
      const match = line.trim().match(/^(.+?)\s+((?:[\d.,]+|[-–]|\.{3})(?:\s+(?:[\d.,]+|[-–]|\.{3}))*)\s*$/);
      if (!match) continue;
      const province = reference(match[1].trim());
      if (!province) continue;
      const record = {
        province_reference: province,
        province_label_raw: match[1].trim(),
        category_raw: categories[c],
        metric: metrics[m][0],
        unit_raw: metrics[m][1],
        raw_values: match[2].trim().split(/\s+/),
        source_file: source.file,
        source_url: index.source_url,
        source_sha256: sha,
        pdf_page: page
      };
      assert(!table.has(province), `Duplicate row ${province} p.${page}`);
      if (record.raw_values.length === 5) {
        table.set(province, record);
      } else if (c === 1 && province === 'Cà Mau' && record.raw_values.length === 3) {
        // Cà Mau 2015 and 2018 cells are blank in NSO sources (verified against NSO 2019 pages 525/527/529
        // and cross-checked with NSO 2024 for 2020); the 3 values belong to 2019, 2020, 2021.
        table.set(province, {
          ...record,
          raw_values: ['', '', record.raw_values[0], record.raw_values[1], record.raw_values[2]],
          position_review: 'cross_verified_against_nso2019_and_nso2024_blanks_2015_2018'
        });
        issues.push({...record, status: 'positioned_2019_2020_2021_blanks_2015_2018_verified'});
      } else {
        issues.push({...record, status: 'short_row_unresolved'});
      }
    }
    for (const province of provinces) {
      if (!table.has(province)) {
        issues.push({
          province_reference: province,
          category_raw: categories[c],
          metric: metrics[m][0],
          source_file: source.file,
          pdf_page: page,
          status: 'province_row_not_listed_on_source_page'
        });
      }
    }
    tables.push(table);
  }
  for (const province of provinces) {
    const parts = tables.map(t => t.get(province));
    if (!parts.every(p => p?.raw_values.length === 5)) continue;
    for (let y = 0; y < 5; y++) {
      if (!parts.every(p => p.raw_values[y] !== '')) continue;
      const r = {
        yearbook_edition: source.yearbook_edition,
        province_reference: province,
        year_raw: String(source.years[y]),
        year_label_raw: y === 4 ? 'Sơ bộ / Prel. 2021' : String(source.years[y]),
        category_raw: categories[c],
        season_scope: c === 2 ? 'combined_he_thu_thu_dong' : c === 0 ? 'annual_total' : 'source_season',
        source_file: source.file,
        source_url: index.source_url,
        source_sha256: sha
      };
      parts.forEach((p, m) => {
        const k = metrics[m][0];
        r[`${k}_raw`] = p.raw_values[y];
        r[`${k}_unit_raw`] = p.unit_raw;
        r[`${k}_province_label_raw`] = p.province_label_raw;
        r[`pdf_page_${k}`] = p.pdf_page;
      });
      rows.push(r);
    }
  }
}

writeCSV('data/raw/nso_rice_2021_reconciliation.csv', rows);

// Cross-check all 2019 rows (NGTK 2019 Preliminary vs NGTK 2021 Official)
const nsoBase = readCSV('data/raw/nso_rice_province_tables.csv');
const base2019 = nsoBase.filter(r => r.year_raw === '2019');
const off2019 = rows.filter(r => r.year_raw === '2019');
const diffs2019 = [];
for (const o of off2019) {
  const b = base2019.find(x => x.province_reference === o.province_reference && x.category_raw === o.category_raw);
  if (!b) {
    diffs2019.push({province: o.province_reference, category: o.category_raw, type: 'missing_in_nso2019'});
    continue;
  }
  const changed = ['area_raw', 'yield_raw', 'production_raw'].filter(k => b[k] !== o[k]);
  if (changed.length) {
    diffs2019.push({
      province: o.province_reference,
      category: o.category_raw,
      changed_fields: changed,
      nso2019_prelim: {area: b.area_raw, yield: b.yield_raw, production: b.production_raw},
      nso2021_official: {area: o.area_raw, yield: o.yield_raw, production: o.production_raw}
    });
  }
}

const status = {
  generated_at: new Date().toISOString(),
  source_file: source.file,
  source_sha256: sha,
  captured_rows: rows.length,
  rows_for_2019_official: off2019.length,
  compared_against_nso2019_prelim_rows: base2019.length,
  differences_between_2019_prelim_and_official: diffs2019.length,
  diff_details: diffs2019,
  issues_count: issues.length,
  numeric_normalization_performed: false,
  cleaning_performed: false
};
fs.writeFileSync('docs/nso_2021_reconciliation_status.json', JSON.stringify(status, null, 2));
console.log(JSON.stringify(status, null, 2));
