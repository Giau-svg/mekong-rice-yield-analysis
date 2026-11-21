import fs from 'node:fs';
import crypto from 'node:crypto';
import path from 'node:path';
const readLog=file=>fs.existsSync(file)?fs.readFileSync(file,'utf8').replace(/^\uFEFF/,'').trim().split('\n').filter(Boolean).map(l=>JSON.parse(l.replace(/^\uFEFF/,''))):[];
const logs=['data/raw/crawl_log.jsonl','data/raw/seed_download_log.jsonl','data/raw/weather_log.jsonl','data/raw/weather_grid_log.jsonl','data/raw/reference_acquisition_log.jsonl','data/raw/calendar_acquisition_log.jsonl','data/raw/geo_acquisition_log.jsonl','data/raw/climate_acquisition_log.jsonl'].flatMap(readLog);
const manual=[
 ['data/raw/calendar/riceatlas_metadata.json','https://dataverse.harvard.edu/api/datasets/:persistentId/?persistentId=doi:10.7910/DVN/JE6R2R'],
 ['data/raw/crawl/3f7d6bac74a52cc224c7.pdf','https://www.nso.gov.vn/wp-content/uploads/2026/01/NG-TONG-CUC-2024_OKIN_Final.pdf'],
 ['data/raw/nso_yearbook_2019.pdf','https://www.nso.gov.vn/wp-content/uploads/2020/09/Nien-giam-thong-ke-day-du-2019.pdf'],
 ['data/raw/kien_giang_yearbook_2024.pdf','https://ctk.angiang.gov.vn/Documents/TinTuc/NG%20Kien%20Giang%202024%20KG.pdf'],
 ['data/raw/long_an_indicators_2019_2023.xlsx','https://www.nso.gov.vn/wp-content/uploads/2025/05/51.-Long-an.xlsx'],
 ['data/raw/tien_giang_2024.html','https://thongkedongthap.nso.gov.vn/tin-tuc/140'],
 ['data/raw/nso_localities.html','https://www.nso.gov.vn/chuyen-muc-dia-phuong/'],
 ['data/raw/nso_pxweb_rice.html','https://www.nso.gov.vn/px-web-2?pxid=V0612'],
 ['data/raw/angiang_yearbook_2024_detail.js','https://ctk.angiang.gov.vn/json/tintucchitiet/TinChiTiet_4240.js'],
];
for(const [local,url]of manual)if(fs.existsSync(local))logs.push({url,local,ok:true,retrieved_at:null});
const downloaded=new Map();
for(const r of logs)if(r.ok&&fs.existsSync(r.local||r.file||''))downloaded.set(r.local||r.file,r);
const escape=x=>'"'+String(x??'').replaceAll('"','""')+'"';
function csv(file,rows,fields){fs.writeFileSync(file,'\uFEFF'+[fields,...rows.map(r=>fields.map(k=>r[k]))].map(r=>r.map(escape).join(',')).join('\n')+'\n');}
const records=[];
const reviewOverrides=fs.existsSync('config/source_review_overrides.json')?JSON.parse(fs.readFileSync('config/source_review_overrides.json')):{};
for(const [local,r]of downloaded){
 const b=fs.readFileSync(local),start=b.subarray(0,100).toString('latin1'),tail=b.subarray(-2048).toString('latin1');
 const pdf=start.startsWith('%PDF-'),xlsx=b.subarray(0,2).toString()==='PK'&&local.endsWith('.xlsx');
 const format=pdf?'pdf':xlsx?'xlsx':local.endsWith('.json')?'json':/\.(csv|tsv|tab)$/.test(local)?'delimited_text':local.endsWith('.xls')?'xls':local.endsWith('.txt')?'text':'html_or_script';
 const integrity=pdf?(tail.includes('%%EOF')?'pdf_header_and_eof_present':'incomplete_pdf'):xlsx?'zip_signature_present':format==='json'?'json_payload':'saved_response';
 const label=pdf||xlsx?(r.label&&/drive.usercontent/.test(r.url)?r.label:decodeURIComponent(new URL(r.url).pathname.split('/').at(-1))):b.toString('utf8').match(/<title[^>]*>([\s\S]*?)<\/title>/i)?.[1]?.replace(/\s+/g,' ')||r.id||path.basename(local);
 const host=new URL(r.url).hostname;
 let group=/power.larc.nasa.gov/.test(host)?'nasa_weather':/(?:nso|gso)\.gov\.vn/.test(host)?'official_statistics':/mpi.gov.vn/.test(host)?'government_report_mirror':/siwrp|ispae/.test(host)?'research_institute':/thitruongnongsan/.test(host)?'agricultural_market_report':/baovinhlong/.test(host)?'local_press':'local_government_or_agriculture';
 if(/vietbooks|drive.usercontent|thuvienso.net|lib.ctu.edu.vn/.test(host))group='public_library_or_mirror';
 if(/sage-public-files|dataverse.harvard|api.figshare/.test(host))group='research_reference_calendar';
 if(local.startsWith('data/raw/calendar/')&&/khuyennongvn\.gov\.vn/.test(host))group='official_calendar_directive';
 if(/geodata\.ucdavis\.edu/.test(host))group='reference_administrative_boundary';
 if(/\.noaa\.gov/.test(host))group='reference_climate_index';
 if(host==='thuvienphapluat.vn')group='public_legal_document_mirror';
 const htmlText=format==='html_or_script'?b.toString('utf8'):'';
 const acquisition_status=local.endsWith('.pdf')&&!pdf?'expected_pdf_not_received':/\/preview\//.test(r.url)?'public_preview_only':/thongkevinhlong/.test(host)&&/BẮC KẠN|Bắc Kạn/.test(label)?'portal_province_mismatch':/nien-giam/.test(r.url)&&/no-download/.test(htmlText)?'declared_attachment_disabled':'saved_raw_source';
 records.push({local,url:r.url,source_group:group,label,format,acquisition_status,bytes:b.length,sha256:crypto.createHash('sha256').update(b).digest('hex'),retrieved_at:r.retrieved_at||'',integrity,transport_verification:r.transport_verification||'see_acquisition_log',discovered_from:r.parent||'',period_and_geography_status:'not_yet_extracted_or_verified',content_review_status:reviewOverrides[local]?.content_review_status||'not_reviewed',content_review_evidence:reviewOverrides[local]?.review_evidence||''});
}
records.sort((a,b)=>a.source_group.localeCompare(b.source_group)||a.url.localeCompare(b.url));
fs.mkdirSync('data/catalog',{recursive:true});
csv('data/catalog/source_catalog.csv',records,Object.keys(records[0]));
csv('data/catalog/acquisition_issues.csv',records.filter(r=>r.acquisition_status!=='saved_raw_source'),Object.keys(records[0]));
fs.writeFileSync('data/catalog/source_catalog.json',JSON.stringify(records,null,2));
const succeededURLs=new Set(records.map(r=>r.url));
const failed=new Map();for(const r of logs)if(!r.ok&&!succeededURLs.has(r.url))failed.set(r.url,{url:r.url,error:r.error,retrieved_at:r.retrieved_at||''});
csv('data/catalog/unavailable_sources.csv',[...failed.values()],['url','error','retrieved_at']);
const weather=records.filter(r=>r.source_group==='nasa_weather');
const report=[];let dayRows=0,valueCount=0;
const exportFile='data/raw/weather_daily_raw.csv';
const fd=fs.openSync(exportFile,'w');
const fields=['source_file','point_id','latitude','longitude','date_yyyymmdd','time_standard','T2M','T2M_MAX','T2M_MIN','PRECTOTCORR','RH2M','WS2M','ALLSKY_SFC_SW_DWN'];
fs.writeSync(fd,'\uFEFF'+fields.map(escape).join(',')+'\n');
for(const r of weather){
 const d=JSON.parse(fs.readFileSync(r.local)),p=d.properties.parameter;
 const dates=Object.keys(p.T2M||{}).sort();const point=path.basename(r.local).replace('_2014_2024.json','');
 let fill=0;for(const v of Object.values(p))for(const x of Object.values(v)){valueCount++;if(x===d.header.fill_value)fill++;}
 const daysExpected=4018;
 report.push({file:r.local,point_id:point,start:dates[0],end:dates.at(-1),days:dates.length,expected_days:daysExpected,parameter_count:Object.keys(p).length,fill_value_count:fill,time_standard:d.header.time_standard});
 const [lon,lat]=d.geometry.coordinates;
 let chunk='';for(const date of dates){const row=[r.local,point,lat,lon,date,d.header.time_standard,...fields.slice(6).map(k=>p[k]?.[date]??'')];chunk+=row.map(escape).join(',')+'\n';dayRows++;}fs.writeSync(fd,chunk);
}
fs.closeSync(fd);
csv('data/catalog/weather_inventory.csv',report,['file','point_id','start','end','days','expected_days','parameter_count','fill_value_count','time_standard']);
const grid=JSON.parse(fs.readFileSync('config/weather_grid.json'));
const gridAvailable=grid.points.filter(p=>fs.existsSync(p.reuse_file||`data/raw/weather_grid/${p.id}_2014_2024.json`)).length;
const summary={generated_at:new Date().toISOString(),stage:'raw_acquisition_only',saved_source_files:records.length,unique_content_hashes:new Set(records.map(r=>r.sha256)).size,pdf_files:records.filter(r=>r.format==='pdf'&&r.integrity!=='incomplete_pdf').length,incomplete_pdf_files:records.filter(r=>r.integrity==='incomplete_pdf').map(r=>r.local),xlsx_files:records.filter(r=>r.format==='xlsx').length,source_groups:Object.fromEntries([...new Set(records.map(r=>r.source_group))].map(g=>[g,records.filter(r=>r.source_group===g).length])),total_bytes:records.reduce((s,r)=>s+r.bytes,0),weather_source_files:weather.length,weather_raw_point_days:dayRows,weather_raw_parameter_values:valueCount,weather_bbox_grid_cells:grid.points.length,weather_bbox_available_cells:gridAvailable,weather_bbox_masked:false,weather_files_with_unexpected_day_count:report.filter(r=>r.days!==r.expected_days).map(r=>r.file),unavailable_urls:failed.size,rice_three_season_coverage:'not_yet_verified_do_not_infer_from_document_count',cleaning_performed:false};
summary.distinct_pdf_contents=new Set(records.filter(r=>r.format==='pdf'&&r.integrity!=='incomplete_pdf').map(r=>r.sha256)).size;
summary.distinct_xlsx_contents=new Set(records.filter(r=>r.format==='xlsx').map(r=>r.sha256)).size;
summary.expected_pdf_not_received=records.filter(r=>r.acquisition_status==='expected_pdf_not_received').length;
summary.preview_only_files=records.filter(r=>r.acquisition_status==='public_preview_only').length;
fs.writeFileSync('docs/raw_collection_status.json',JSON.stringify(summary,null,2));
console.log(JSON.stringify(summary,null,2));
