import fs from 'node:fs';
import crypto from 'node:crypto';
fs.mkdirSync('data/raw/weather_grid',{recursive:true});
const original=JSON.parse(fs.readFileSync('config/weather_points.json'));
const key=(lat,lon)=>`${Math.round((lat+90)/0.5)}:${Math.round((lon+180)/0.625)}`;
const existing=new Map(original.filter(p=>fs.existsSync(`data/raw/weather/${p.id}_2014_2024.json`)).map(p=>[key(p.latitude,p.longitude),`data/raw/weather/${p.id}_2014_2024.json`]));
const grid=[];
// Buffer around mainland Mekong Delta; offshore/neighbouring cells retained raw for later masking.
for(let latitude=8.5;latitude<=11;latitude+=0.5)for(let longitude=104.375;longitude<=106.875;longitude+=0.625){
 const id=`grid_${latitude.toFixed(3)}_${longitude.toFixed(3)}`;
 grid.push({id,latitude,longitude,cell_key:key(latitude,longitude),region:'mekong_bbox_unmasked',reuse_file:existing.get(key(latitude,longitude))||null});
}
fs.writeFileSync('config/weather_grid.json',JSON.stringify({source:'https://power.larc.nasa.gov/docs/services/',resolution_degrees:[0.5,0.625],boundary_mask_applied:false,points:grid},null,2));
for(const p of grid){
 if(p.reuse_file){console.log(`reuse ${p.id}`);continue;}
 const file=`data/raw/weather_grid/${p.id}_2014_2024.json`;
 if(fs.existsSync(file))continue;
 const url='https://power.larc.nasa.gov/api/temporal/daily/point?'+new URLSearchParams({parameters:'T2M,T2M_MAX,T2M_MIN,PRECTOTCORR,RH2M,WS2M',community:'AG',latitude:p.latitude,longitude:p.longitude,start:'20140101',end:'20241231',format:'JSON','time-standard':'LST'});
 for(let attempt=1;attempt<=3;attempt++){
  try{const r=await fetch(url,{signal:AbortSignal.timeout(90000)});if(!r.ok)throw Error(`HTTP ${r.status}`);const bytes=Buffer.from(await r.arrayBuffer());if(!JSON.parse(bytes).properties?.parameter)throw Error('No parameter payload');fs.writeFileSync(file,bytes);fs.appendFileSync('data/raw/weather_grid_log.jsonl',JSON.stringify({...p,url,file,ok:true,retrieved_at:new Date().toISOString(),bytes:bytes.length,sha256:crypto.createHash('sha256').update(bytes).digest('hex')})+'\n');console.log(`downloaded ${p.id}`);break;}catch(e){if(attempt===3)fs.appendFileSync('data/raw/weather_grid_log.jsonl',JSON.stringify({...p,url,ok:false,error:e.message})+'\n');await new Promise(r=>setTimeout(r,1500*attempt));}
 }
 await new Promise(r=>setTimeout(r,800));
}
