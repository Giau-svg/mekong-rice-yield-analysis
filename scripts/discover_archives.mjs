import fs from 'node:fs';
const rows=fs.readFileSync('data/raw/crawl_log.jsonl','utf8').trim().split('\n').map(JSON.parse).filter(r=>r.ok&&r.local.endsWith('.html'));
const seeds=new Set(['https://webtctk.gso.gov.vn/nien-giam-thong-ke','https://www.nso.gov.vn/wp-content/uploads/2019/10/Nien-giam-2018-1.pdf','https://ctk.angiang.gov.vn/Documents/TinTuc/Sach%20NGTK%20AN%20GIANG%202024%20(B%C3%B4ng%202_OKIN%201.8.25).pdf']);
for(const r of rows){const html=fs.readFileSync(r.local,'utf8');for(const m of html.matchAll(/href\s*=\s*["']([^"']+)["']/gi)){
 const u=new URL(m[1].replaceAll('&amp;','&').replaceAll('&#038;','&'),r.url).href;
 const ctx=html.slice(m.index,m.index+500).replace(/<[^>]*>/g,' ');
 if(/nien-giam|niengiam|lúa|lua|\.pdf|\.xlsx?/i.test(u+' '+ctx)&&!u.includes('javascript:')){
  if(!/www.nso.gov.vn/.test(u)||/lúa|lua|2018/.test(ctx+' '+u))seeds.add(u);
 }
}}
const selected=[...seeds].filter(u=>/nien-giam|px-web|\.pdf|download_file/.test(u));
fs.writeFileSync('config/archive_seeds.json',JSON.stringify(selected,null,2));
console.log(JSON.stringify({archive_seeds:selected.length}));
