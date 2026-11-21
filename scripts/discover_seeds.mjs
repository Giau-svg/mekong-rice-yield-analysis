import fs from 'node:fs';
const file='config/crawl_seeds.json';
const seeds=JSON.parse(fs.readFileSync(file));
const s=fs.readFileSync('data/raw/nso_localities.html','utf8');
const urls=[...s.matchAll(/href=["']([^"']+)/g)].map(x=>x[1].replaceAll('&amp;','&'));
const regional=/long-an|tien-giang|ben-tre|tra-vinh|vinh-long|dong-thap|an-giang|kien-giang|can-tho|hau-giang|soc-trang|bac-lieu|ca-mau/i;
seeds.push(...urls.filter(x=>regional.test(x)).map(x=>new URL(x,'https://www.nso.gov.vn').href),'https://thongkevinhlong.nso.gov.vn/','https://thongkecamau.nso.gov.vn/','https://cucthongke.tayninh.gov.vn/');
fs.writeFileSync(file,JSON.stringify([...new Set(seeds)],null,2));
console.log(JSON.stringify(seeds.slice(18),null,2));
