import fs from 'node:fs';
import crypto from 'node:crypto';
import path from 'node:path';
import {execFile} from 'node:child_process';
import {promisify} from 'node:util';
const exec=promisify(execFile);
const root='data/raw/crawl';
fs.mkdirSync(root,{recursive:true});
const logPath='data/raw/crawl_log.jsonl';
const past=fs.existsSync(logPath)?fs.readFileSync(logPath,'utf8').trim().split('\n').filter(Boolean).map(x=>JSON.parse(x)):[];
const done=new Set(past.filter(r=>r.ok).map(r=>r.url));
const seeds=JSON.parse(fs.readFileSync(process.env.CRAWL_SEEDS||'config/crawl_seeds.json','utf8'));
const queued=new Set();const queue=[];
const max=Number(process.env.CRAWL_MAX||350);
const depthLimit=Number(process.env.CRAWL_DEPTH||3);
const extraHosts=new Set(['siwrp.org.vn','sotay.ispae.vn','nongnghiep.nsvl.com.vn','baovinhlong.com.vn','vietbooks.info','thuvienso.net','lib.ctu.edu.vn','drive.usercontent.google.com','thuvienthongke.com','www.niengiamthongke.net']);
const dnsCache=new Map([['www.nso.gov.vn','160.25.148.3'],['thongkedongthap.nso.gov.vn','118.70.216.41'],['thongkecantho.nso.gov.vn','118.70.216.41'],['thongkevinhlong.nso.gov.vn','118.70.216.41'],['thongkecamau.nso.gov.vn','118.70.216.41']]);
const fold=s=>s.normalize('NFD').replace(/[\u0300-\u036f]/g,'').replaceAll('đ','d').replaceAll('Đ','D').toLowerCase();
const topic=s=>/nien.?giam|thong.?ke|kinh.?te|xa.?hoi|nong.?nghiep|lua|san.?xuat|bao.?cao|an.?pham|niên.?giám|thống.?kê/.test(fold(s));
function add(url,depth=0,parent='',label=''){
 try {const u=new URL(url);u.hash='';if(!['http:','https:'].includes(u.protocol))return;
 if(process.env.CRAWL_SCOPE==='rice-gap'){
  const scope=fold(decodeURIComponent(u.href)+' '+label);
  let reason='';
  if(/thongkehue|thongketuyenquang|haiduong|haiphong|caobang|congan\.camau|quangninh/.test(u.hostname))reason='unrelated_portal_for_gap_collection';
  if(u.hostname==='www.agi.gov.vn'&&!/lua|rice|nien.?giam/.test(scope))reason='general_bibliography_not_rice_dataset';
  if(u.hostname==='thitruongnongsan.gov.vn'&&/ca.?phe|rau.?qua|2026/.test(scope))reason='other_crop_or_outside_target_reference_period';
  if(u.hostname==='lmhtx.angiang.gov.vn'&&!/lua|thuy.?loi|han.?man|xam.?nhap.?man|bien.?doi.?khi.?hau|nien.?giam/.test(scope))reason='non_rice_related_article';
  if(reason){fs.mkdirSync('data/catalog',{recursive:true});fs.appendFileSync('data/catalog/discovery_scope_exclusions.jsonl',JSON.stringify({url:u.href,parent,label,reason})+'\n');return;}
 }
 if(u.hostname==='ctk.angiang.gov.vn'&&u.protocol==='http:')u.protocol='https:';
 if(!/(?:gov\.vn)$/.test(u.hostname)&&!extraHosts.has(u.hostname))return;
 if(/dang-nhap|login|logout|mailto|javascript|\.jpg|\.png|\.css|\.gif|\.mp4|\.zip/i.test(u.href))return;
 if(/\.js(?:\?|$)/i.test(u.href)&&!u.pathname.includes('/json/tintuc'))return;
 const key=u.href;if(queued.has(key))return;queued.add(key);queue.push({url:key,depth,parent,label});}catch{}
}
if(process.env.CRAWL_RESUME==='1'&&fs.existsSync('data/raw/crawl_pending.json')){
 for(const j of JSON.parse(fs.readFileSync('data/raw/crawl_pending.json','utf8')))add(j.url,j.depth,j.parent,j.label);
}else seeds.sort((a,b)=>Number(/\.pdf$/i.test(a))-Number(/\.pdf$/i.test(b))).forEach(u=>add(u));
const log=r=>fs.appendFileSync(logPath,JSON.stringify(r)+'\n');
let count=0;
async function get(job){
 const id=crypto.createHash('sha256').update(job.url).digest('hex').slice(0,20);
 let ext=path.extname(new URL(job.url).pathname).toLowerCase();if(!['.pdf','.xlsx','.xls','.csv','.doc','.docx'].includes(ext))ext='.html';
 if(new URL(job.url).hostname==='drive.usercontent.google.com')ext='.pdf';
 const local=`${root}/${id}${ext}`;
 let bytes,contentType='',resolvedURL=job.url,transportVerification='system_tls_validation';
 try{
  if(done.has(job.url)&&fs.existsSync(local)){bytes=fs.readFileSync(local);}
  else {
   let finalURL=job.url;
   const hostname=new URL(job.url).hostname;
   const args=['-f','-sS','-L','--connect-timeout','10','--max-time',ext==='.pdf'?'300':'45','--output',local+'.part','--write-out','%{url_effective}\n%{content_type}'];
   if(fs.existsSync(local+'.part')&&fs.statSync(local+'.part').size>0&&ext==='.pdf')args.push('--continue-at','-');
   if(dnsCache.has(hostname))args.push('--resolve',`${hostname}:443:${dnsCache.get(hostname)}`);
   args.push(job.url);
   try {const result=await exec('curl.exe',args,{windowsHide:true,timeout:310000,maxBuffer:1024*1024});const [effective,type]=result.stdout.trim().split('\n');if(effective)resolvedURL=effective;contentType=type||'';finalURL=resolvedURL;}
   catch(e){
    if(args.includes('--continue-at')&&/curl: \((33|36)\)/.test(e.stderr||'')){const i=args.indexOf('--continue-at');args.splice(i,2);await exec('curl.exe',args,{windowsHide:true,timeout:310000,maxBuffer:1024*1024});}else throw e;
   }
   bytes=fs.readFileSync(local+'.part');fs.unlinkSync(local+'.part');
   if(!bytes.length)throw Error('Empty response');
   fs.writeFileSync(local,bytes);
   log({...job,ok:true,local,bytes:bytes.length,content_type:contentType,transport_verification:transportVerification,sha256:crypto.createHash('sha256').update(bytes).digest('hex'),retrieved_at:new Date().toISOString(),final_url:finalURL});
  }
  if(ext!=='.html'||job.depth>=depthLimit)return;
  const html=bytes.toString('utf8');
  const baseHref=html.match(/<base[^>]+href=["']([^"']+)/i)?.[1];
  let documentBase=resolvedURL;try{if(baseHref)documentBase=new URL(baseHref,resolvedURL).href;}catch{}
  const title=html.match(/<title[^>]*>([\s\S]*?)<\/title>/i)?.[1]||'';
  if(new URL(job.url).hostname==='thongkevinhlong.nso.gov.vn'&&/bac kan/.test(fold(title))&&!/vinh long/.test(fold(title))){
   fs.mkdirSync('data/catalog',{recursive:true});fs.appendFileSync('data/catalog/source_scope_warnings.jsonl',JSON.stringify({url:job.url,local,observed_title:title,warning:'Portal serves Bac Kan content; do not infer Vinh Long coverage or follow this portal',checked_at:new Date().toISOString()})+'\n');return;
  }
  if(/ctk\.angiang\.gov\.vn\/json\/tintuc\//.test(job.url))for(const m of html.matchAll(/['"]link['"]\s*:\s*['"]([^'"]+)/g)){
   if(/nien-giam|nien_giam|niengiam/i.test(m[1]))add(m[1],job.depth+1,job.url,'Public yearbook category payload');
  }
  const ag=job.url.match(/ctk\.angiang\.gov\.vn\/trang\/TinTuc\/\d+\/(\d+)/i);
  if(ag)add(`https://ctk.angiang.gov.vn/json/tintucchitiet/TinChiTiet_${ag[1]}.js`,job.depth+1,job.url,'Public article payload');
  for(const m of html.matchAll(/(?:href|src|data-src)\s*=\s*["']([^"']+)["']/gi)){
   const raw=m[1].replaceAll('&amp;','&').replaceAll('&#038;','&');let u;try{u=new URL(raw,documentBase);}catch{continue;}
   const publicDrive=u.href.match(/^https:\/\/drive\.google\.com\/file\/d\/([\w-]+)/);
   if(publicDrive){if(/nien.?giam/i.test(fold(title)))add(`https://drive.usercontent.google.com/download?id=${publicDrive[1]}&export=download&confirm=t`,job.depth+1,job.url,title);continue;}
   const context=html.slice(Math.max(0,m.index-120),m.index+500).replace(/<[^>]*>/g,' ').replace(/\s+/g,' ').trim();
   const attachment=/\.(pdf|xlsx?|csv|docx?)(?:$|\?)/i.test(u.href);
   if(u.hostname==='vietbooks.info'&&!attachment&&!(/\/threads\/nien-giam/.test(u.pathname)&&/long-an|tien-giang|ben-tre|tra-vinh|vinh-long|dong-thap|an-giang|kien-giang|can-tho|hau-giang|soc-trang|bac-lieu|ca-mau/.test(u.pathname)&&/20(?:1[4-9]|2[0-4])/.test(u.pathname)))continue;
   const same=u.hostname===new URL(job.url).hostname;
   if(!attachment){
    if(u.hostname==='www.nso.gov.vn'&&!(/px-web/.test(u.pathname)&&/pxid=(?:V06|PLV06)/.test(u.search)))continue;
    if(u.hostname!=='www.nso.gov.vn'&&!/nien-giam|niengiam|tinh-hinh-kinh-te|tin-tuc|TinTuc|download_file|json\/tintuc|ChiTiet|baocao/i.test(u.pathname))continue;
   }
   if(/202[5-9]|203\d/.test(context)&&!attachment&&!/nien.?giam/i.test(fold(context)))continue;
   if(attachment&&(topic(context+' '+title+' '+u.href)||job.depth>0))add(u.href,job.depth+1,job.url,context.slice(0,300));
   else if(same&&topic(context+' '+u.pathname)&&!attachment)add(u.href,job.depth+1,job.url,context.slice(0,300));
  }
 }catch(e){log({...job,ok:false,error:e.message,retrieved_at:new Date().toISOString()});}
}
// Three workers, each pauses between requests; bounded discovery, no authentication.
async function worker(){while(queue.length&&count<max){const job=queue.shift();count++;await get(job);if(count%20===0)console.log(JSON.stringify({requests:count,queued:queue.length}));await new Promise(r=>setTimeout(r,400));}}
await Promise.all([worker(),worker(),worker()]);
fs.writeFileSync('data/raw/crawl_pending.json',JSON.stringify(queue,null,2));
console.log(JSON.stringify({visited:count,pending:queue.length}));
