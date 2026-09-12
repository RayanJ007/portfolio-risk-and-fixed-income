import fs from 'node:fs/promises';
import {FileBlob,SpreadsheetFile} from '@oai/artifact-tool';
const wb=await SpreadsheetFile.importXlsx(await FileBlob.load('models/risk_reporting_model.xlsx'));
console.log((await wb.inspect({kind:'sheet',include:'id,name',maxChars:2500})).ndjson);
const p=wb.worksheets.getItem('Positions'), s=wb.worksheets.getItem('Portfolio Summary');
const before=s.getRange('B6').values[0][0], q=p.getRange('B6').values[0][0];
p.getRange('B6').values=[[q+1]];
const after=s.getRange('B6').values[0][0];
if(Math.abs(after-before-1)>.01)throw Error('Quantity sensitivity failed');
p.getRange('B6').values=[[q]];wb.recalculate();
console.log((await wb.inspect({kind:'table',range:'Checks!A5:D9',include:'values,formulas',tableMaxRows:5,tableMaxCols:4,maxChars:2500})).ndjson);
console.log((await wb.inspect({kind:'match',searchTerm:'#REF!|#DIV/0!|#VALUE!|#NAME\\?|#NUM!',options:{useRegex:true,maxResults:10},maxChars:1000})).ndjson);
await fs.mkdir('outputs/polish_previews',{recursive:true});
const names=['Cover','Portfolio Summary','VaR','Expected Shortfall','Fixed Income','Risk Contribution','Stress Tests','Yield Curve','Risk Attribution','Data Quality','Positions','Trades','Security Master','Market Data','Daily Report','Checks'];
for(const name of names){
 const range=name==='Portfolio Summary'?'A1:M23':name==='Daily Report'?'A1:B17':name==='Cover'?'A1:B15':name==='Checks'?'A1:G12':name==='Risk Attribution'?'A1:F18':'A1:I18';
 const image=await wb.render({sheetName:name,range,scale:1,format:'png'});
 await fs.writeFile(`outputs/polish_previews/${name.replaceAll(' ','_')}.png`,new Uint8Array(await image.arrayBuffer()));
}
