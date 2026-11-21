$ErrorActionPreference='Stop'
Set-Location (Split-Path $PSScriptRoot -Parent)
New-Item -ItemType Directory -Force data/raw/seed_files | Out-Null
$sources=Get-Content -Raw config/crawl_seeds.json | ConvertFrom-Json
foreach ($url in $sources) {
 if ($url -notmatch '\.(pdf|xlsx?|csv|docx?)(\?|$)') { continue }
 $sha=[System.Security.Cryptography.SHA256]::Create()
 $id=([BitConverter]::ToString($sha.ComputeHash([Text.Encoding]::UTF8.GetBytes($url)))).Replace('-','').ToLower().Substring(0,20)
 $ext=[IO.Path]::GetExtension(([uri]$url).AbsolutePath)
 $file="data/raw/seed_files/$id$ext"
 if (Test-Path -LiteralPath $file) { continue }
 try {
  $curlArgs=@('-f','-sS','-L','--connect-timeout','10','--max-time','180','--retry','1','--output',"$file.part")
  if (([uri]$url).Host -eq 'www.nso.gov.vn') { $curlArgs+=@('--resolve','www.nso.gov.vn:443:160.25.148.3') }
  $curlArgs+=$url
  & curl.exe @curlArgs
  if ($LASTEXITCODE -ne 0) { throw "curl exit $LASTEXITCODE" }
  Move-Item -LiteralPath "$file.part" -Destination $file
  $item=Get-Item -LiteralPath $file
  $entry=@{url=$url;local=$file;bytes=$item.Length;sha256=(Get-FileHash -LiteralPath $file -Algorithm SHA256).Hash.ToLower();retrieved_at=[DateTime]::UtcNow.ToString('o');ok=$true}
  Write-Output "OK $url $($item.Length)"
 } catch {
  $entry=@{url=$url;ok=$false;error=$_.Exception.Message;retrieved_at=[DateTime]::UtcNow.ToString('o')}
  Write-Output "FAIL $url"
 }
 $entry | ConvertTo-Json -Compress | Add-Content -Encoding UTF8 data/raw/seed_download_log.jsonl
}
