import fs from 'node:fs';
import assert from 'node:assert/strict';
import crypto from 'node:crypto';
const specs=JSON.parse(fs.readFileSync('config/rice_table_capture.json'));
const indexes=fs.readdirSync('data/raw/pdf_text').filter(f=>f.endsWith('.json')).map(f=>JSON.parse(fs.readFileSync(`data/raw/pdf_text/${f}`)));
const mainSeasons=new Set(['Lúa đông xuân','Lúa hè thu','Lúa thu đông']);
const records=[];
for(const spec of specs){
 const hash=crypto.createHash('sha256').update(fs.readFileSync(spec.source_file)).digest('hex');
 const index=indexes.find(d=>d.source_sha256===hash);
 assert(index,`Missing source text index: ${spec.source_file}`);
 function capture(pageNo){
  const page=index.pages.find(p=>p.page===pageNo);assert(page,`Missing page ${pageNo}`);
  // Capture only the source's absolute-value block. The growth-index block below is a separate table.
  const block=page.text.split(/Chỉ số phát triển|Index\s*\(Previous year/)[0];
  const rows=new Map();
  for(const m of block.matchAll(/(?:^|\n)\s*(Sơ bộ[^\n]*?)?\s*(20(?:1[5-9]|2[0-4]))\s+([^\n]+)/g)){
   const values=m[3].trim().split(/\s+/);
   assert.equal(values.length,spec.columns.length,`Column count mismatch: ${spec.province_raw} p${pageNo} ${m[2]}`);
   assert(values.every(v=>/^[\d.,]+$|^-$|^\.{3}$/.test(v)),`Unexpected raw cell on page ${pageNo}`);
   assert(!rows.has(m[2]),`Duplicate year inside source block ${pageNo}`);
   rows.set(m[2],{values,year_label_raw:(m[1]||'')+m[2]});
  }
  assert.equal(rows.size,10,`Expected ten source year rows on page ${pageNo}`);
  return rows;
 }
 const area=capture(spec.area_page),yieldRows=capture(spec.yield_page),production=capture(spec.production_page);
 for(let year=2015;year<=2024;year++)for(let col=0;col<spec.columns.length;col++){
  const key=String(year),a=area.get(key),y=yieldRows.get(key),p=production.get(key);
  assert.equal(a.year_label_raw,y.year_label_raw);assert.equal(y.year_label_raw,p.year_label_raw);
  records.push({province_raw:spec.province_raw,year_raw:key,year_label_raw:y.year_label_raw,season_or_category_raw:spec.columns[col],area_raw:a.values[col],area_unit_raw:'Ha',yield_raw:y.values[col],yield_unit_raw:'Tạ/ha',production_raw:p.values[col],production_unit_raw:'Tấn',source_file:spec.source_file,source_url:index.source_url,source_sha256:hash,pdf_page_area:spec.area_page,pdf_page_yield:spec.yield_page,pdf_page_production:spec.production_page,capture_status:'source_table_capture_not_cleaned'});
 }
}
const main=records.filter(r=>mainSeasons.has(r.season_or_category_raw));
assert.equal(main.length,90);
assert.equal(new Set(main.map(r=>[r.province_raw,r.year_raw,r.season_or_category_raw].join('|'))).size,90);
const cell=x=>'"'+String(x??'').replaceAll('"','""')+'"';
function csv(file,rows){const fields=Object.keys(rows[0]);fs.writeFileSync(file,'\uFEFF'+[fields,...rows.map(r=>fields.map(k=>r[k]))].map(r=>r.map(cell).join(',')).join('\n')+'\n');}
csv('data/raw/rice_captured_main_seasons.csv',main);
csv('data/raw/rice_captured_all_categories.csv',records);
fs.writeFileSync('docs/rice_capture_status.json',JSON.stringify({main_season_rows:main.length,all_category_rows:records.length,provinces:specs.map(s=>s.province_raw),years:'2015–2024',seasons:[...mainSeasons],numeric_normalization_performed:false,unit_conversion_performed:false,missing_imputation_performed:false,source_revision_selection_performed:false,weather_join_performed:false,model_ready:false},null,2));
console.log(JSON.stringify({main_season_rows:main.length,all_category_rows:records.length,provinces:specs.map(s=>s.province_raw)},null,2));
