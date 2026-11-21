import fs from 'node:fs';
export function readCSV(file){
 const s=fs.readFileSync(file,'utf8').replace(/^\uFEFF/,''),rows=[];let row=[],value='',quoted=false;
 for(let i=0;i<s.length;i++){
  const ch=s[i];
  if(ch==='"'){if(quoted&&s[i+1]==='"'){value+='"';i++;}else quoted=!quoted;}
  else if(ch===','&&!quoted){row.push(value);value='';}
  else if((ch==='\r'||ch==='\n')&&!quoted){if(ch==='\r'&&s[i+1]==='\n')i++;row.push(value);rows.push(row);row=[];value='';}
  else value+=ch;
 }
 if(quoted)throw Error(`Unclosed CSV quote ${file}`);
 if(value||row.length){row.push(value);rows.push(row);}
 const header=rows.shift();return rows.filter(r=>r.some(v=>v!=='')).map(r=>Object.fromEntries(header.map((h,i)=>[h,r[i]??''])));
}
export function writeCSV(file,rows,fields=Object.keys(rows[0]||{})){
 const cell=v=>'"'+String(v??'').replaceAll('"','""')+'"';
 fs.writeFileSync(file,'\uFEFF'+[fields,...rows.map(r=>fields.map(k=>r[k]))].map(r=>r.map(cell).join(',')).join('\n')+'\n');
}
