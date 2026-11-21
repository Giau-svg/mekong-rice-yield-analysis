import fs from 'node:fs';
import crypto from 'node:crypto';
import assert from 'node:assert/strict';
import {parseHTML} from '../tmp/html-runtime/node_modules/linkedom/worker.js';
import {writeCSV} from './lib/csv.mjs';

// Raw extraction of official rice crop calendar directives & progress evidence.
// Keeps original verbatim Vietnamese sowing/harvest descriptions without inferring
// exact annual provincial start_date/end_date (which belongs to cleaning + sensitivity analysis).

const specs = JSON.parse(fs.readFileSync('config/calendar_capture.json', 'utf8'));
const catalog = JSON.parse(fs.readFileSync('data/catalog/source_catalog.json', 'utf8'));

const rows = [];
for (const spec of specs) {
  const bytes = fs.readFileSync(spec.source_file);
  const sha = crypto.createHash('sha256').update(bytes).digest('hex');
  const source = catalog.find(r => r.local === spec.source_file);
  assert(source, `Missing source_catalog entry for ${spec.source_file}`);

  let text;
  if (spec.block !== undefined) {
    const idxFile = `data/raw/html_text/${sha.slice(0, 20)}.json`;
    assert(fs.existsSync(idxFile), `Missing html_text index ${idxFile}`);
    const doc = JSON.parse(fs.readFileSync(idxFile, 'utf8'));
    text = doc.blocks.find(b => b.block === spec.block)?.text;
  } else {
    const {document} = parseHTML(bytes.toString('utf8'));
    for (const n of document.querySelectorAll('script,style')) n.remove();
    text = document.body.textContent.replace(/\s+/g, ' ');
  }
  assert(text, `Empty extracted text for ${spec.calendar_record_id}`);
  const normText = text.replace(/\s+/g, ' ');
  const start = normText.indexOf(spec.start_marker);
  assert(start >= 0, `Missing start_marker "${spec.start_marker}" in ${spec.source_file} (${spec.calendar_record_id})`);
  const excerpt = normText.slice(start, start + 650);
  assert(
    excerpt.includes(spec.evidence_substring),
    `Missing evidence_substring "${spec.evidence_substring}" in ${spec.calendar_record_id}; excerpt=${excerpt.slice(0, 250)}`
  );

  rows.push({
    calendar_record_id: spec.calendar_record_id,
    calendar_level: spec.calendar_level,
    cropping_system_raw: spec.cropping_system_raw,
    subregion_or_province_raw: spec.subregion_or_province_raw,
    season_reference: spec.season_reference,
    year_scope_raw: spec.year_scope_raw,
    sowing_window_raw: spec.sowing_window_raw,
    harvest_or_duration_raw: spec.harvest_or_duration_raw,
    issuing_agency: spec.issuing_agency,
    source_file: spec.source_file,
    source_url: source.url,
    source_sha256: sha,
    source_block: spec.block ?? '',
    source_excerpt_raw: excerpt,
    capture_status: 'raw_official_calendar_directive_not_annual_observed_dates'
  });
}

assert.equal(new Set(rows.map(r => r.calendar_record_id)).size, rows.length);
writeCSV('data/raw/season_calendar_raw.csv', rows);

const status = {
  generated_at: new Date().toISOString(),
  captured_calendar_records: rows.length,
  distinct_source_files: new Set(rows.map(r => r.source_file)).size,
  seasons_covered: [...new Set(rows.map(r => r.season_reference))],
  levels_breakdown: Object.fromEntries(
    [...new Set(rows.map(r => r.calendar_level))].map(l => [l, rows.filter(r => r.calendar_level === l).length])
  ),
  annual_provincial_observed_dates_complete: false,
  note: 'Raw official regional/subregional calendar directives & progress reports extracted verbatim. Exact cleaning window construction and +-10/15-day sensitivity testing occur in the Cleaning/Preparation stage.'
};
fs.writeFileSync('docs/calendar_capture_status.json', JSON.stringify(status, null, 2));
console.log(JSON.stringify(status, null, 2));
