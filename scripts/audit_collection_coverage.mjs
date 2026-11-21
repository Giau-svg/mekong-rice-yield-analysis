import fs from 'node:fs';
import assert from 'node:assert/strict';
import {readCSV,writeCSV} from './lib/csv.mjs';
const provinces=['Long An','Tiền Giang','Bến Tre','Trà Vinh','Vĩnh Long','Đồng Tháp','An Giang','Kiên Giang','Cần Thơ','Hậu Giang','Sóc Trăng','Bạc Liêu','Cà Mau'];
const seasons=['Lúa đông xuân','Lúa hè thu','Lúa thu đông'];
const local=readCSV('data/raw/rice_captured_main_seasons.csv');
const nso=readCSV('data/raw/nso_rice_province_tables.csv');
const reports=fs.existsSync('data/raw/rice_report_season_values.csv')?readCSV('data/raw/rice_report_season_values.csv'):[];
const evidence=[...local.map(r=>({...r,province_reference:r.province_raw,category_raw:r.season_or_category_raw})),...nso.filter(r=>seasons.includes(r.category_raw)),...reports.filter(r=>r.season_scope==='single_reported_season')];
const rows=[];
for(const province of provinces)for(let year=2015;year<=2024;year++)for(const season of seasons){
 const matches=evidence.filter(r=>r.province_reference===province&&r.year_raw===String(year)&&r.category_raw===season);
 const combined=nso.filter(r=>r.province_reference===province&&r.year_raw===String(year)&&r.season_scope==='combined_he_thu_thu_dong');
 rows.push({province_reference:province,harvest_year_reference:year,season_reference:season,collection_status:matches.length?'separate_season_values_captured':season!=='Lúa đông xuân'&&combined.length?'combined_source_only_separate_season_not_acquired':'source_cell_blank_requires_other_source',source_record_count:matches.length,source_files:JSON.stringify([...new Set(matches.map(r=>r.source_file))]),source_urls:JSON.stringify([...new Set(matches.map(r=>r.source_url))]),combined_reference_files:season!=='Lúa đông xuân'?JSON.stringify(combined.map(r=>r.source_file)):'[]',calendar_status:'annual_province_calendar_not_verified',cleaned_or_model_ready:false});
}
assert.equal(rows.length,390);assert.equal(new Set(rows.map(r=>[r.province_reference,r.harvest_year_reference,r.season_reference].join('|'))).size,390);
writeCSV('data/catalog/rice_collection_coverage.csv',rows);
writeCSV('data/catalog/rice_collection_gaps.csv',rows.filter(r=>r.collection_status!=='separate_season_values_captured'));
const byProvince=provinces.map(p=>({province:p,separate_season_cells:rows.filter(r=>r.province_reference===p&&r.source_record_count>0).length,reference_cells:30}));
const calendar=readCSV('data/raw/calendar/sacks_all_data_with_climate.csv');
const vietnamRice=calendar.filter(r=>/viet\s*nam/i.test(r.Location)&&/^rice$/i.test(r.Crop));
writeCSV('data/catalog/calendar_vietnam_rice_reference.csv',vietnamRice,Object.keys(calendar[0]));
const ocr=fs.existsSync('data/raw/ocr_text')?fs.readdirSync('data/raw/ocr_text').filter(f=>f.endsWith('.json')).map(f=>JSON.parse(fs.readFileSync(`data/raw/ocr_text/${f}`))):[];
const status={generated_at:new Date().toISOString(),reference_cells:390,separate_season_cells_with_source_values:rows.filter(r=>r.source_record_count>0).length,source_records_including_overlapping_versions:evidence.length,unresolved_cells:rows.filter(r=>!r.source_record_count).length,by_province:byProvince,ocr_documents:ocr.length,ocr_pages:ocr.reduce((s,d)=>s+d.pages.length,0),sacks_vietnam_rice_reference_rows:vietnamRice.length,calendar_caveat:'Historical reference only; no validation of annual province-season calendars for 2015–2024',riceatlas_status:'Metadata acquired; file download requires repository guestbook response',collection_complete_for_requested_scope:false,cleaning_performed:false,notes:['390 is an audit grid, not an assertion all seasons occur everywhere','Combined Hè Thu–Thu Đông never assigned to either separate season','Source blank cells do not establish zero area or absence of cultivation','Counts refer to acquired and positioned source values, not reconciled or cleaned observations']};
fs.writeFileSync('docs/collection_coverage_audit.json',JSON.stringify(status,null,2));console.log(JSON.stringify(status,null,2));
