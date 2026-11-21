import fs from 'node:fs';
import crypto from 'node:crypto';
import assert from 'node:assert/strict';

const writeCSV = (path, rows, fields = Object.keys(rows[0] ?? {})) => {
  const cell = x => '"' + String(x ?? '').replaceAll('"', '""') + '"';
  fs.writeFileSync(path, '\uFEFF' + [fields, ...rows.map(r => fields.map(k => r[k]))].map(r => r.map(cell).join(',')).join('\n') + '\n');
};
for (const d of ['data/interim','data/processed','docs']) fs.mkdirSync(d,{recursive:true});
const source_url = 'https://thongkedongthap.nso.gov.vn/tin-tuc/140';
const text = fs.readFileSync('data/raw/tien_giang_2024.html','utf8').replace(/<[^>]+>/g,' ').replace(/\s+/g,' ');
// Curated transcription, guarded against unexpected changes in downloaded source.
for (const value of ['44.883','70,2','315.030','62.885','57,5','361.553','12.562','56,0','70.297']) assert(text.includes(value), `Source no longer contains ${value}`);
const crops = [
  {season:'dong_xuan',source_season:'Đông Xuân 2023 - 2024',area_ha:44883,yield_t_ha:7.02,production_t:315030,season_scope:'single',locator:'Trồng trọt / Cây lúa / Vụ Đông Xuân 2023 - 2024'},
  {season:'he_thu',source_season:'Hè Thu 2024 (Xuân Hè và Hè Thu)',area_ha:62885,yield_t_ha:5.75,production_t:361553,season_scope:'xuan_he_plus_he_thu',locator:'Trồng trọt / Cây lúa / Vụ Hè Thu 2024'},
  {season:'thu_dong',source_season:'Thu Đông 2024',area_ha:12562,yield_t_ha:5.60,production_t:70297,season_scope:'single',locator:'Trồng trọt / Cây lúa / Vụ Thu Đông 2024'},
].map(r=>({province_id:'tien_giang',province:'Tiền Giang',harvest_year:2024,...r,source_id:'TG_2024',source_url,publication_date:'2025-01-03',source_status:'chinh_thuc_theo_doan_vu',original_yield_unit:'ta/ha',calendar_status:'unverified',eligible_for_model:false}));
assert.equal(new Set(crops.map(r=>`${r.province_id}/${r.harvest_year}/${r.season}`)).size,crops.length);
writeCSV('data/interim/rice_observations.csv',crops);
const quality = crops.map(r=>({...Object.fromEntries(['province_id','harvest_year','season'].map(k=>[k,r[k]])),production_relative_error:Math.abs(r.area_ha*r.yield_t_ha-r.production_t)/r.production_t,scope_ok:r.season_scope==='single',calendar_ok:false}));
assert(quality.every(r=>r.production_relative_error<0.01),'Production reconciliation exceeds 1%');
writeCSV('data/interim/rice_quality.csv',quality);
const rawPath='data/raw/nasa_power_tien_giang_pilot_2024.json';
const raw=JSON.parse(fs.readFileSync(rawPath,'utf8'));
const params=['T2M','T2M_MAX','PRECTOTCORR','RH2M'];
const p=raw.properties.parameter;
const daily=Object.keys(p.T2M).sort().map(date=>({point_id:'tien_giang_pilot',date:`${date.slice(0,4)}-${date.slice(4,6)}-${date.slice(6,8)}`,latitude:10.45,longitude:106.35,time_standard:raw.header.time_standard,...Object.fromEntries(params.map(k=>[k,p[k][date]===raw.header.fill_value?null:p[k][date]]))}));
assert.equal(daily.length,366);
assert.equal(daily[0].date,'2024-01-01'); assert.equal(daily.at(-1).date,'2024-12-31');
assert(daily.every(r=>params.every(k=>Number.isFinite(r[k]))));
assert(daily.every(r=>r.RH2M>=0&&r.RH2M<=100&&r.PRECTOTCORR>=0&&r.T2M_MAX>=r.T2M));
writeCSV('data/interim/weather_daily_pilot.csv',daily);
const provinces=['long_an','tien_giang','ben_tre','tra_vinh','vinh_long','dong_thap','an_giang','kien_giang','can_tho','hau_giang','soc_trang','bac_lieu','ca_mau'];
const inventory=provinces.flatMap(province_id=>Array.from({length:10},(_,i)=>2015+i).flatMap(harvest_year=>['dong_xuan','he_thu','thu_dong'].map(season=>{
const found=crops.find(r=>r.province_id===province_id&&r.harvest_year===harvest_year&&r.season===season);
return {province_id,harvest_year,season,collection_status:found?'collected':'not_collected',season_scope:found?.season_scope??'',calendar_status:'unverified',source_id:found?.source_id??''};
})));
writeCSV('data/interim/coverage_inventory.csv',inventory);
writeCSV('config/season_calendar.csv',crops.map(r=>({province_id:r.province_id,harvest_year:r.harvest_year,season:r.season,start_date:'',end_date:'',calendar_source_url:'',verification_status:'unverified'})));
const files=['data/raw/tien_giang_2024.html',rawPath];
fs.writeFileSync('data/raw/manifest.json',JSON.stringify({built_at:new Date().toISOString(),files:files.map(path=>({path,sha256:crypto.createHash('sha256').update(fs.readFileSync(path)).digest('hex')}))},null,2));
const summary={rice_rows:crops.length,single_season_rows:2,combined_season_rows:1,weather_days:daily.length,weather_missing_values:0,expected_inventory_cells:inventory.length,model_ready_rows:0,blockers:['Season calendars not verified','Hè Thu includes Xuân Hè','Pilot coordinate is not a provincial spatial average','Need 2014 weather for cross-year 2015 winter-spring seasons']};
fs.writeFileSync('docs/collection_status.json',JSON.stringify(summary,null,2));
console.log(JSON.stringify(summary,null,2));
