import fs from 'node:fs';
import crypto from 'node:crypto';
fs.mkdirSync('data/raw/weather',{recursive:true});
// Acquisition points only; these coordinates are not provincial spatial averages.
const points=[['long_an',10.75,106.25],['tien_giang',10.45,106.35],['ben_tre',10.1,106.4],['tra_vinh',9.8,106.3],['vinh_long',10.1,105.95],['dong_thap',10.6,105.6],['an_giang',10.5,105.15],['kien_giang',10.0,105.1],['can_tho',10.1,105.6],['hau_giang',9.75,105.65],['soc_trang',9.6,105.95],['bac_lieu',9.3,105.6],['ca_mau',9.15,105.15]];
fs.writeFileSync('config/weather_points.json',JSON.stringify(points.map(([id,latitude,longitude])=>({id,latitude,longitude,role:'acquisition_point_not_provincial_average'})),null,2));
const parameters='T2M,T2M_MAX,T2M_MIN,PRECTOTCORR,RH2M,WS2M,ALLSKY_SFC_SW_DWN';
for(const [id,latitude,longitude]of points){
 const file=`data/raw/weather/${id}_2014_2024.json`;
 if(fs.existsSync(file)){console.log(`cached ${id}`);continue;}
 const url='https://power.larc.nasa.gov/api/temporal/daily/point?'+new URLSearchParams({parameters,community:'AG',latitude,longitude,start:'20140101',end:'20241231',format:'JSON','time-standard':'LST'});
 let success=false;
 for(let attempt=1;attempt<=3;attempt++){
 try{const res=await fetch(url,{signal:AbortSignal.timeout(90000)});if(!res.ok)throw Error(`HTTP ${res.status}`);const bytes=Buffer.from(await res.arrayBuffer());const data=JSON.parse(bytes);if(!data.properties?.parameter)throw Error('No daily parameter payload');fs.writeFileSync(file,bytes);fs.appendFileSync('data/raw/weather_log.jsonl',JSON.stringify({id,url,file,latitude,longitude,start:'20140101',end:'20241231',retrieved_at:new Date().toISOString(),bytes:bytes.length,sha256:crypto.createHash('sha256').update(bytes).digest('hex'),ok:true})+'\n');success=true;console.log(`downloaded ${id} ${bytes.length} bytes`);break;}catch(e){if(attempt===3)fs.appendFileSync('data/raw/weather_log.jsonl',JSON.stringify({id,url,ok:false,error:e.message,retrieved_at:new Date().toISOString()})+'\n');await new Promise(r=>setTimeout(r,attempt*1500));}
 }
 if(!success)console.log(`failed ${id}`);
 await new Promise(r=>setTimeout(r,700));
}
