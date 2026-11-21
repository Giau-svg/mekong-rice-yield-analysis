import fs from 'node:fs';
import crypto from 'node:crypto';
import {getDocument} from '../tmp/pdf-runtime/node_modules/pdfjs-dist/legacy/build/pdf.mjs';
const catalog=JSON.parse(fs.readFileSync('data/catalog/source_catalog.json'));
const unique=new Map();for(const r of catalog)if(r.format==='pdf'&&r.integrity!=='incomplete_pdf')unique.set(r.sha256,r);
fs.mkdirSync('data/raw/pdf_text',{recursive:true});
const fold=s=>s.normalize('NFD').replace(/[\u0300-\u036f]/g,'').replaceAll('đ','d').replaceAll('Đ','D').toLowerCase();
const provinces=['Long An','Tiền Giang','Bến Tre','Trà Vinh','Vĩnh Long','Đồng Tháp','An Giang','Kiên Giang','Cần Thơ','Hậu Giang','Sóc Trăng','Bạc Liêu','Cà Mau'];
let indexed=0;
for(const [hash,r]of unique){
 const output=`data/raw/pdf_text/${hash.slice(0,20)}.json`;
 if(fs.existsSync(output))continue;
 try{
  const task=getDocument({data:new Uint8Array(fs.readFileSync(r.local)),useSystemFonts:true,isEvalSupported:false,verbosity:0});
  const pdf=await task.promise;
  const pages=[];const hits=[];let chars=0;
  for(let i=1;i<=pdf.numPages;i++){
   const page=await pdf.getPage(i);const content=await page.getTextContent();
   let text='';for(const item of content.items)if('str'in item)text+=item.str+(item.hasEOL?'\n':' ');
   pages.push({page:i,text});chars+=text.length;
   const f=fold(text);
   if(/\blua\b|\bpaddy\b|rice yield/.test(f)&&/nang suat|san luong|dien tich|yield|production|planted area/.test(f)){
    pages.at(-1).text_items=content.items.filter(item=>'str'in item).map(item=>({str:item.str,x:item.transform[4],y:item.transform[5],width:item.width,height:item.height}));
    hits.push({page:i,provinces_mentioned:provinces.filter(p=>f.includes(fold(p))),years_mentioned:[...new Set(text.match(/\b20(?:1[4-9]|2[0-4])\b/g)||[])].sort(),seasons_mentioned:['dong xuan','he thu','thu dong','lua mua'].filter(x=>f.includes(x)),excerpt:text.slice(0,450)});
   }
   page.cleanup();
  }
  fs.writeFileSync(output,JSON.stringify({source_file:r.local,source_url:r.url,source_sha256:hash,extraction:'PDF.js text items; no OCR; no numerical normalization',page_count:pdf.numPages,text_characters:chars,rice_candidate_pages:hits,pages},null,2));
  fs.appendFileSync('data/raw/pdf_text_index_log.jsonl',JSON.stringify({source_file:r.local,source_url:r.url,output,page_count:pdf.numPages,text_characters:chars,rice_candidate_page_count:hits.length,needs_ocr:chars<Math.max(100,pdf.numPages*25),ok:true})+'\n');
  await task.destroy();indexed++;console.log(JSON.stringify({indexed,file:r.local,pages:pages.length,rice_candidates:hits.length}));
 }catch(e){fs.appendFileSync('data/raw/pdf_text_index_log.jsonl',JSON.stringify({source_file:r.local,source_url:r.url,ok:false,error:e.message})+'\n');}
}
