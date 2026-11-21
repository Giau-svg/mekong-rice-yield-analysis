import fs from 'node:fs';
import crypto from 'node:crypto';
import assert from 'node:assert/strict';

// Transcription of complete five-column rows only. Short rows remain unresolved,
// because plain PDF text cannot establish the position of blank source cells.
const sources=[
 {file:'data/raw/nso_yearbook_2019.pdf',years:[2015,2016,2017,2018,2019],pages:[[519,521,523],[525,527,529],[530,531,532],[534,536,538]]},
 {file:'data/raw/crawl/3f7d6bac74a52cc224c7.pdf',years:[2020,2021,2022,2023,2024],pages:[[599,601,603],[605,607,609],[610,611,612],[614,616,618]]}
];
const provinces=['Long An','Tiền Giang','Bến Tre','Trà Vinh','Vĩnh Long','Đồng Tháp','An Giang','Kiên Giang','Cần Thơ','Hậu Giang','Sóc Trăng','Bạc Liêu','Cà Mau'];
const categories=['Lúa cả năm','Lúa đông xuân','Lúa hè thu và thu đông','Lúa mùa'];
const metrics=[['area','Nghìn ha'],['yield','Tạ/ha'],['production','Nghìn tấn']];
const rows=[],rawRows=[],issues=[];
// This reference match is an explicit index only: the extracted name is retained.
const reference=s=>provinces.find(p=>p.replaceAll(' ','')===s.replaceAll(' ',''));
for(const source of sources){
 const sha=crypto.createHash('sha256').update(fs.readFileSync(source.file)).digest('hex');
 const index=JSON.parse(fs.readFileSync(`data/raw/pdf_text/${sha.slice(0,20)}.json`));
 for(let c=0;c<categories.length;c++){
  const tables=[];
  for(let m=0;m<metrics.length;m++){
   const page=source.pages[c][m],text=index.pages.find(p=>p.page===page)?.text;
   assert(text,`Missing page ${page}`);
   assert(source.years.every(y=>text.includes(String(y))),`Year header mismatch ${page}`);
   const table=new Map();
   for(const line of text.split('\n')){
    const match=line.trim().match(/^(.+?)\s+((?:[\d.,]+|[-–]|\.{3})(?:\s+(?:[\d.,]+|[-–]|\.{3}))*)\s*$/);
    if(!match)continue;
    const province=reference(match[1].trim());if(!province)continue;
    const record={province_reference:province,province_label_raw:match[1].trim(),category_raw:categories[c],metric:metrics[m][0],unit_raw:metrics[m][1],year_columns:source.years,raw_values:match[2].trim().split(/\s+/),raw_line:line,source_file:source.file,source_url:index.source_url,source_sha256:sha,pdf_page:page};
    assert(!table.has(province),`Duplicate row ${province} ${page}`);
    table.set(province,record);rawRows.push(record);
    if(record.raw_values.length!==5){
     if(source.years[0]===2015&&c===1&&province==='Cà Mau'&&record.raw_values.length===2){
      // Visually checked source pages 525, 527, 529: values occupy 2017 and 2019.
      table.set(province,{...record,raw_values:['','',record.raw_values[0],'',record.raw_values[1]],position_review:'visual_source_pages_525_527_529'});
      issues.push({...record,status:'visually_positioned_2017_2019_other_year_cells_blank_in_source'});
     }else issues.push({...record,status:'short_row_requires_coordinate_or_visual_capture'});
    }
   }
   for(const province of provinces)if(!table.has(province))issues.push({province_reference:province,category_raw:categories[c],metric:metrics[m][0],source_file:source.file,pdf_page:page,status:'province_row_not_listed_on_source_page'});
   tables.push(table);
  }
  for(const province of provinces){
   const parts=tables.map(t=>t.get(province));
   if(!parts.every(p=>p?.raw_values.length===5))continue;
   for(let y=0;y<5;y++){
    if(!parts.every(p=>p.raw_values[y]!==''))continue;
    const r={province_reference:province,year_raw:String(source.years[y]),year_label_raw:y===4?`Sơ bộ / Prel. ${source.years[y]}`:String(source.years[y]),category_raw:categories[c],season_scope:c===2?'combined_he_thu_thu_dong':c===0?'annual_total':'source_season',source_file:source.file,source_url:index.source_url,source_sha256:sha};
    parts.forEach((p,m)=>{const k=metrics[m][0];r[`${k}_raw`]=p.raw_values[y];r[`${k}_unit_raw`]=p.unit_raw;r[`${k}_province_label_raw`]=p.province_label_raw;r[`pdf_page_${k}`]=p.pdf_page;});
    rows.push(r);
   }
  }
 }
}
const fields=Object.keys(rows[0]),cell=v=>'"'+String(v??'').replaceAll('"','""')+'"';
fs.writeFileSync('data/raw/nso_rice_province_tables.csv','\uFEFF'+[fields,...rows.map(r=>fields.map(k=>r[k]))].map(r=>r.map(cell).join(',')).join('\n')+'\n');
fs.writeFileSync('data/raw/nso_rice_table_rows.jsonl',rawRows.map(r=>JSON.stringify(r)).join('\n')+'\n');
fs.writeFileSync('data/catalog/nso_rice_capture_issues.json',JSON.stringify(issues,null,2));
const status={captured_rows:rows.length,source_table_rows:rawRows.length,provinces:provinces.length,years:'2015–2024',category_counts:Object.fromEntries(categories.map(c=>[c,rows.filter(r=>r.category_raw===c).length])),unresolved_or_omitted_source_rows:issues.length,numeric_normalization_performed:false,unit_conversion_performed:false,imputation_performed:false,combined_seasons_split:false,model_ready:false};
fs.writeFileSync('docs/nso_capture_status.json',JSON.stringify(status,null,2));console.log(JSON.stringify(status,null,2));
