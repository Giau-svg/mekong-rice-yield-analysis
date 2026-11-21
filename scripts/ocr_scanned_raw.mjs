import fs from 'node:fs';
import crypto from 'node:crypto';
import {createCanvas} from '../tmp/pdf-runtime/node_modules/@napi-rs/canvas/index.js';
import {getDocument} from '../tmp/pdf-runtime/node_modules/pdfjs-dist/legacy/build/pdf.mjs';
import {createWorker} from '../tmp/ocr-runtime/node_modules/tesseract.js/src/index.js';

fs.mkdirSync('tmp/ocr-cache',{recursive:true});
fs.mkdirSync('data/raw/ocr_text',{recursive:true});
const catalog=JSON.parse(fs.readFileSync('data/catalog/source_catalog.json'));
const reviews=fs.existsSync('config/source_review_overrides.json')?JSON.parse(fs.readFileSync('config/source_review_overrides.json')):{};
const docs=fs.readdirSync('data/raw/pdf_text').filter(f=>f.endsWith('.json')).map(f=>JSON.parse(fs.readFileSync(`data/raw/pdf_text/${f}`))).filter(d=>d.text_characters<Math.max(100,d.page_count*25)&&reviews[d.source_file]?.use_for_target_observations!==false);
const worker=await createWorker('vie+eng',1,{cachePath:'tmp/ocr-cache'});
try{
 for(const doc of docs){
  const output=`data/raw/ocr_text/${doc.source_sha256.slice(0,20)}.json`;
  if(fs.existsSync(output))continue;
  const task=getDocument({data:new Uint8Array(fs.readFileSync(doc.source_file)),useSystemFonts:true,isEvalSupported:false,verbosity:0});
  const pdf=await task.promise,pages=[];
  for(let n=1;n<=pdf.numPages;n++){
   const page=await pdf.getPage(n),viewport=page.getViewport({scale:2.2});
   const canvas=createCanvas(Math.ceil(viewport.width),Math.ceil(viewport.height));
   await page.render({canvasContext:canvas.getContext('2d'),viewport}).promise;
   const png=canvas.toBuffer('image/png'),result=await worker.recognize(png);
   pages.push({page:n,text:result.data.text,confidence:result.data.confidence,render_sha256:crypto.createHash('sha256').update(png).digest('hex')});
   console.log(JSON.stringify({file:doc.source_file,page:n,pages:pdf.numPages,confidence:result.data.confidence}));page.cleanup();
  }
  fs.writeFileSync(output,JSON.stringify({source_file:doc.source_file,source_url:doc.source_url,source_sha256:doc.source_sha256,extraction:'Tesseract.js 6 vie+eng; raster scale 2.2; uncorrected machine transcription',numeric_review_status:'not_verified_do_not_use_as_validated_observations',pages},null,2));
  await task.destroy();
 }
}finally{await worker.terminate();}
