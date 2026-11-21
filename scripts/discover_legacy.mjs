import fs from 'node:fs';
const logs=fs.readFileSync('data/raw/crawl_log.jsonl','utf8').trim().split('\n').map(JSON.parse);
const lib=logs.find(r=>r.ok&&r.url==='https://lib.ctu.edu.vn/index.php/manual-open-learning-materials/94-resources');
const html=fs.readFileSync(lib.local,'utf8');
const region=/An Giang|Bến Tre|Cần Thơ|Hậu Giang|Long An|Sóc Trăng/;
const seeds=[];
for(const row of html.matchAll(/<tr\b[^>]*>[\s\S]*?<\/tr>/gi))if(region.test(row[0]))for(const a of row[0].matchAll(/href=["']([^"']+)/g))if(/gov\.vn/.test(a[1]))seeds.push(new URL(a[1].replaceAll('&amp;','&'),lib.url).href);
fs.writeFileSync('config/legacy_seeds.json',JSON.stringify([...new Set(seeds)],null,2));
console.log(JSON.stringify(seeds,null,2));
