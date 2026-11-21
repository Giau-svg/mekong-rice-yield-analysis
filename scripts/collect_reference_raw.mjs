import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import {execFileSync} from 'node:child_process';
for(const source of JSON.parse(fs.readFileSync('config/reference_sources.json'))){
 fs.mkdirSync(path.dirname(source.file),{recursive:true});
 try{
  if(!fs.existsSync(source.file)){
   execFileSync('curl.exe',['-f','-sS','-L','--retry','2','--connect-timeout','10','--max-time','90','--output',source.file+'.part',source.url],{windowsHide:true,timeout:100000});
   const bytes=fs.readFileSync(source.file+'.part');if(!bytes.length)throw Error('Empty response');fs.renameSync(source.file+'.part',source.file);
  }
  const bytes=fs.readFileSync(source.file),record={...source,local:source.file,bytes:bytes.length,sha256:crypto.createHash('sha256').update(bytes).digest('hex'),ok:true,retrieved_at:new Date().toISOString()};
  fs.appendFileSync('data/raw/reference_acquisition_log.jsonl',JSON.stringify(record)+'\n');console.log(JSON.stringify({file:source.file,bytes:bytes.length}));
 }catch(e){fs.appendFileSync('data/raw/reference_acquisition_log.jsonl',JSON.stringify({...source,ok:false,error:e.message,retrieved_at:new Date().toISOString()})+'\n');console.error(source.url,e.message);}
}
