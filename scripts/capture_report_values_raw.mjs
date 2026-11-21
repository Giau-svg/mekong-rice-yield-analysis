import fs from 'node:fs';
import crypto from 'node:crypto';
import assert from 'node:assert/strict';
import {parseHTML} from '../tmp/html-runtime/node_modules/linkedom/worker.js';
import {writeCSV} from './lib/csv.mjs';
const specs=JSON.parse(fs.readFileSync('config/rice_report_capture.json'));
const catalog=JSON.parse(fs.readFileSync('data/catalog/source_catalog.json'));
const rows=[];
for(const spec of specs){
 const bytes=fs.readFileSync(spec.source_file),sha=crypto.createHash('sha256').update(bytes).digest('hex');
 const source=catalog.find(r=>r.local===spec.source_file);assert(source);
 let text;
 if(spec.block){const doc=JSON.parse(fs.readFileSync(`data/raw/html_text/${sha.slice(0,20)}.json`));text=doc.blocks.find(b=>b.block===spec.block)?.text;}
 else{const {document}=parseHTML(bytes.toString('utf8'));for(const n of document.querySelectorAll('script,style'))n.remove();text=document.body.textContent;}
 assert(text);const start=text.indexOf(spec.start_marker);assert(start>=0,`Missing marker ${spec.source_file}`);
 const excerpt=text.slice(start,start+2200);
 for(const k of ['area_raw','yield_raw','production_raw'])assert(excerpt.includes(spec[k]),`Missing ${k} in scoped source section ${spec.source_file}`);
 rows.push({...spec,area_unit_raw:spec.area_unit_raw||'ha',yield_unit_raw:spec.yield_unit_raw||'tạ/ha',production_unit_raw:spec.production_unit_raw||'tấn',season_scope:'single_reported_season',source_url:source.url,source_sha256:sha,source_excerpt_raw:excerpt,report_value_status:'reported_in_annual_report_revision_not_reconciled',capture_status:'source_transcription_not_cleaned'});
}
writeCSV('data/raw/rice_report_season_values.csv',rows);
console.log(JSON.stringify({raw_report_rows:rows.length}));
