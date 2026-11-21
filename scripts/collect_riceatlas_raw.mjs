import fs from 'node:fs';
import crypto from 'node:crypto';
import {execFileSync} from 'node:child_process';
fs.mkdirSync('data/raw/calendar',{recursive:true});
const metadataURL='https://dataverse.harvard.edu/api/datasets/:persistentId/?persistentId=doi:10.7910/DVN/JE6R2R';
const metadataFile='data/raw/calendar/riceatlas_metadata.json';
function download(url,file){execFileSync('curl.exe',['-f','-sS','-L','--retry','2','--connect-timeout','15','--max-time','300','--output',file+'.part',url],{windowsHide:true,timeout:310000});fs.renameSync(file+'.part',file);}
if(!fs.existsSync(metadataFile))download(metadataURL,metadataFile);
const metadata=JSON.parse(fs.readFileSync(metadataFile));
if(metadata.status!=='OK')throw Error('Dataverse metadata failed');
if(metadata.data.guestbookId){
 fs.writeFileSync('data/catalog/riceatlas_access_status.json',JSON.stringify({dataset_doi:'10.7910/DVN/JE6R2R',metadata_file:metadataFile,guestbook_id:metadata.data.guestbookId,status:'guestbook_response_required',files:metadata.data.latestVersion.files.map(e=>({id:e.dataFile.id,filename:e.dataFile.filename,restricted:e.restricted})),download_attempt_response:'HTTP 400: required Guestbook response for guestbookID 40',identity_form_submitted:false,files_downloaded:false},null,2));
 console.log('RiceAtlas metadata saved; repository guestbook response required. No form submitted.');
 process.exit(0);
}
for(const entry of metadata.data.latestVersion.files){
 const f=entry.dataFile;if(entry.restricted)continue;
 const file=`data/raw/calendar/${f.filename.replace(/[^a-zA-Z0-9_.-]/g,'_')}`,url=`https://dataverse.harvard.edu/api/access/datafile/${f.id}`;
 if(!fs.existsSync(file))download(url,file);
 const bytes=fs.readFileSync(file),record={url,local:file,bytes:bytes.length,sha256:crypto.createHash('sha256').update(bytes).digest('hex'),dataverse_file_id:f.id,dataverse_checksum:f.checksum,dataset_doi:'10.7910/DVN/JE6R2R',retrieved_at:new Date().toISOString(),scope:'reference_calendar_or_historical_production_not_year_specific_2015_2024',ok:true};
 if(f.checksum?.type==='MD5'&&/\.zip$/.test(f.filename)&&crypto.createHash('md5').update(bytes).digest('hex')!==f.checksum.value)throw Error(`Checksum mismatch ${file}`);
 fs.appendFileSync('data/raw/calendar_acquisition_log.jsonl',JSON.stringify(record)+'\n');console.log(JSON.stringify({file,bytes:bytes.length}));
}
