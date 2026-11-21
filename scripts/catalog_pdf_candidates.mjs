import fs from 'node:fs';
const catalog=JSON.parse(fs.readFileSync('data/catalog/source_catalog.json'));
const byHash=new Map(catalog.map(r=>[r.sha256,r]));
const documents=[],pages=[];
const rawFd=fs.openSync('data/raw/rice_candidate_pages.jsonl','w');
for(const file of fs.readdirSync('data/raw/pdf_text').filter(x=>x.endsWith('.json'))){
 const indexFile=`data/raw/pdf_text/${file}`,d=JSON.parse(fs.readFileSync(indexFile,'utf8')),source=byHash.get(d.source_sha256);
 const preview=source?.acquisition_status==='public_preview_only';
 const subject=/Ca(?:%20|\s)phe|cà phê|rau quả|VnSAT_Ca|VnSAT_Rau/i.test(d.source_url)?'other_crop_report':/nien.?giam|niengiam|NGTK|Nien-giam|Sach-63-tinh/i.test(d.source_url+' '+(source?.label||''))?'statistical_yearbook_or_provincial_compendium':'report_or_other_document';
 documents.push({source_file:d.source_file,source_url:d.source_url,text_index_file:indexFile,page_count:d.page_count,text_characters:d.text_characters,rice_candidate_pages:d.rice_candidate_pages.length,needs_ocr:d.text_characters<Math.max(100,d.page_count*25),preview_only:preview,subject_hint:subject,review_status:'automatic_candidate_index_not_verified_numeric_dataset'});
 for(const hit of d.rice_candidate_pages){
  const page=d.pages.find(p=>p.page===hit.page);
  const f=page.text.normalize('NFD').replace(/[\u0300-\u036f]/g,'').replaceAll('đ','d').toLowerCase();
  const combined=/he\s+thu\s+(?:va|[-–])\s+thu\s+dong/.test(f);
  const row={source_file:d.source_file,source_url:d.source_url,pdf_page:hit.page,text_index_file:indexFile,provinces_mentioned:hit.provinces_mentioned.join('|'),years_mentioned:hit.years_mentioned.join('|'),seasons_mentioned:hit.seasons_mentioned.join('|'),possible_combined_he_thu_thu_dong:combined,subject_hint:subject,preview_only:preview,status:'candidate_requires_page_review'};
  pages.push(row);
  fs.writeSync(rawFd,JSON.stringify({...row,raw_extracted_text:page.text})+'\n');
 }
}
fs.closeSync(rawFd);
const cell=x=>'"'+String(x??'').replaceAll('"','""')+'"';
function csv(file,rows){if(!rows.length)return;const fields=Object.keys(rows[0]);fs.writeFileSync(file,'\uFEFF'+[fields,...rows.map(r=>fields.map(k=>r[k]))].map(r=>r.map(cell).join(',')).join('\n')+'\n');}
csv('data/catalog/pdf_document_inventory.csv',documents);
csv('data/catalog/rice_source_pages.csv',pages);
const status={indexed_unique_pdfs:documents.length,indexed_pages:documents.reduce((s,r)=>s+r.page_count,0),documents_with_rice_candidate_pages:documents.filter(r=>r.rice_candidate_pages>0).length,rice_candidate_pages:pages.length,possible_combined_season_pages:pages.filter(r=>r.possible_combined_he_thu_thu_dong).length,documents_needing_ocr:documents.filter(r=>r.needs_ocr).length,preview_documents:documents.filter(r=>r.preview_only).length,numeric_observations_extracted:0,cleaning_performed:false,statement:'Keyword index only; mentions do not establish province-year-season data coverage'};
fs.writeFileSync('docs/pdf_index_status.json',JSON.stringify(status,null,2));
console.log(JSON.stringify(status,null,2));
