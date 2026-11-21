import fs from 'node:fs';
import {parseHTML} from '../tmp/html-runtime/node_modules/linkedom/worker.js';
import {writeCSV} from './lib/csv.mjs';
const catalog=JSON.parse(fs.readFileSync('data/catalog/source_catalog.json'));
fs.mkdirSync('data/raw/html_text',{recursive:true});
const sources=[],candidates=[],seen=new Set();
const fold=s=>s.normalize('NFD').replace(/[\u0300-\u036f]/g,'').replaceAll('đ','d').replaceAll('Đ','D').toLowerCase();
for(const source of catalog){
 if(source.format!=='html_or_script'||seen.has(source.sha256)||!/(?:gov\.vn)(?:\/|$)|thuvienphapluat\.vn\/van-ban\//.test(source.url)||source.acquisition_status!=='saved_raw_source')continue;
 const html=fs.readFileSync(source.local,'utf8');if(!/<html|<body/i.test(html))continue;
 seen.add(source.sha256);const output=`data/raw/html_text/${source.sha256.slice(0,20)}.json`;
 let doc;
 if(fs.existsSync(output))doc=JSON.parse(fs.readFileSync(output));
 if(doc?.extraction_version!==2){
  const {document}=parseHTML(html);
  for(const node of document.querySelectorAll('script,style,nav,header,footer,iframe,noscript,[hidden],[aria-hidden="true"]'))node.remove();
  for(const node of document.querySelectorAll('[style]'))if(/display\s*:\s*none|visibility\s*:\s*hidden/i.test(node.getAttribute('style')))node.remove();
  // Some portals have an empty <main> placeholder while the article is a sibling.
  const root=document.body;
  if(!root)continue;
  const blocks=[...root.querySelectorAll('h1,h2,h3,h4,p,tr,li')].map((n,i)=>({block:i+1,tag:n.tagName.toLowerCase(),text:n.tagName==='TR'?[...n.querySelectorAll('th,td')].map(c=>c.textContent).join('\t'):n.textContent})).filter(b=>b.text.trim());
  doc={extraction_version:2,source_file:source.local,source_url:source.url,source_sha256:source.sha256,extraction:'Public HTML DOM text; script/style/navigation/explicitly hidden elements excluded; no numeric normalization',blocks};
  fs.writeFileSync(output,JSON.stringify(doc,null,2));
 }
 const hits=doc.blocks.filter(b=>/\blua\b|\bpaddy\b/.test(fold(b.text))&&/nang suat|san luong|dien tich|yield|production/.test(fold(b.text)));
 sources.push({source_file:source.local,source_url:source.url,text_index_file:output,blocks:doc.blocks.length,rice_candidate_blocks:hits.length,review_status:'candidate_text_not_verified_numeric_observations'});
 for(const b of hits)candidates.push({source_file:source.local,source_url:source.url,source_sha256:source.sha256,...b});
}
writeCSV('data/catalog/html_document_inventory.csv',sources);
fs.writeFileSync('data/raw/html_rice_candidate_blocks.jsonl',candidates.map(r=>JSON.stringify(r)).join('\n')+'\n');
fs.writeFileSync('docs/html_index_status.json',JSON.stringify({documents:sources.length,rice_candidate_blocks:candidates.length,numeric_observations_verified:0,cleaning_performed:false},null,2));
console.log(JSON.stringify({documents:sources.length,rice_candidate_blocks:candidates.length}));
