import fs from 'node:fs/promises';
import path from 'node:path';
import { createRequire } from 'node:module';
import { pathToFileURL } from 'node:url';

const resolver = createRequire(path.join(process.env.ARTIFACT_MODULES, '_resolver.cjs'));
const { Workbook, SpreadsheetFile } = await import(pathToFileURL(resolver.resolve('@oai/artifact-tool')).href);
const [reportPath, outputPath, renderFlag] = process.argv.slice(2);
const data = JSON.parse(await fs.readFile(reportPath, 'utf8'));
const wb = Workbook.create();
const names = ['Cover','Portfolio Summary','VaR','Expected Shortfall','Fixed Income','Risk Contribution','Stress Tests','Yield Curve','Risk Attribution','Data Quality','Positions','Trades','Security Master','Market Data','Daily Report','Checks'];
const sheets = Object.fromEntries(names.map(n => [n, wb.worksheets.add(n)]));
const navy = '#263D5A', light = '#EDF2F7';
const money = '#,##0;(#,##0);"—"';
const decimal = '#,##0.00;(#,##0.00);"—"';
function col(n) { let s=''; for(n++;n;n=Math.floor((n-1)/26)) s=String.fromCharCode(65+(n-1)%26)+s; return s; }
function table(name, title, columns, rows, widths=[]) {
  const sheet=sheets[name], last=col(columns.length-1), end=5+Math.max(rows.length,1);
  sheet.showGridLines=false;
  sheet.getRange(`A1:${last}${end}`).format.font={name:'Arial',size:10,color:navy};
  sheet.getRange('A2').values=[[title]];
  sheet.getRange('A2').format.font={name:'Arial',size:15,bold:true,color:navy};
  sheet.getRange('A3').values=[[`${data.metadata.as_of_date} · ${data.metadata.base_currency} · ${data.metadata.source_label}`]];
  sheet.getRange(`A5:${last}5`).values=[columns];
  sheet.getRange(`A5:${last}5`).format={fill:navy,font:{bold:true,color:'#FFFFFF'},rowHeight:34,wrapText:true,verticalAlignment:'center'};
  if(rows.length) sheet.getRange(`A6:${last}${end}`).values=rows;
  sheet.getRange(`A6:${last}${end}`).setNumberFormat(decimal);
  sheet.getRange(`A6:${last}${end}`).format.rowHeight=22;
  for(let c=0;c<columns.length;c++) sheet.getRange(`${col(c)}1:${col(c)}${end}`).format.columnWidth=widths[c]||20;
  if(rows.length>15) sheet.freezePanes.freezeRows(5);
  if(rows.length) sheet.tables.add(`A5:${last}${end}`,true,name.replaceAll(' ','')+'Table');
  return sheet;
}
const p=data.positions;
table('Cover','Institutional portfolio risk', ['Report','Value'],[
  ['Portfolio',data.metadata.portfolio_id],['As of',new Date(data.metadata.as_of_date)],
  ['Base currency',data.metadata.base_currency],['Data',data.metadata.source_label],
  ['One-day risk horizon','95% and 99% confidence'],['Calibration observations',data.metadata.observations],
  ['Refresh','python main.py demo --excel'],['Risk snapshots','Re-run Python after changing holdings or market data']
],[32,78]);
sheets.Cover.getRange('B7').setNumberFormat('yyyy-mm-dd');
const positions=table('Positions','Position valuation (CAD)',
 ['Security','Quantity','Local price','Multiplier','FX to CAD','Market value','Weight','Asset class','Currency'],
 p.map(r=>[r.security_id,r.quantity,r.market_price,r.multiplier,r.fx_rate,null,null,null,r.currency]),[20,18,18,16,17,22,15,26,15]);
for(let i=6;i<6+p.length;i++) {
  positions.getRange(`F${i}:H${i}`).formulas=[[
    `=B${i}*C${i}*D${i}*E${i}`,`=F${i}/SUM($F$6:$F$${5+p.length})`,
    `=XLOOKUP(A${i},'Security Master'!$A$6:$A$${5+data.inputs.security_master.length},'Security Master'!$D$6:$D$${5+data.inputs.security_master.length},"Unmapped",0)`]];
}
positions.getRange(`G6:G${5+p.length}`).setNumberFormat('0.0%');
positions.getRange(`B6:E${5+p.length}`).format.font.color='#215CC4';
positions.getRange(`H6:H${5+p.length}`).format.font.color='#26805E';
const classes=[...new Set(p.map(r=>r.asset_class))];
const summary=table('Portfolio Summary','Portfolio summary', ['Measure','CAD'],
 [['Net asset value',null],['Prior NAV',data.prior_nav],['External flows',data.external_flows],['Flow-adjusted daily P&L',null],...classes.map(c=>[c,null])],[34,23]);
summary.getRange('B6').formulas=[[`=SUM('Positions'!F6:F${5+p.length})`]];
summary.getRange('B9').formulas=[['=B6-B7-B8']];
for(let i=0;i<classes.length;i++) summary.getRange(`B${10+i}`).formulas=[[`=SUMIFS('Positions'!$F$6:$F$${5+p.length},'Positions'!$H$6:$H$${5+p.length},A${10+i})`]];
summary.getRange(`B6:B${9+classes.length}`).setNumberFormat(money);
const allocationChart=summary.charts.add('bar',summary.getRange(`A10:B${9+classes.length}`));
allocationChart.title='Asset allocation (CAD millions)'; allocationChart.setPosition('D5','L21'); allocationChart.hasLegend=false;
allocationChart.yAxis={numberFormatCode:'0.0,,"m"',numberFormatSourceLinked:false};
table('VaR','One-day Value at Risk', ['Method','Confidence','Horizon (days)','VaR (CAD)'],data.risk_summary.map(r=>[r.method,r.confidence,r.horizon_days,r.var]),[24,18,19,24]);
sheets.VaR.getRange('B6:B11').setNumberFormat('0%'); sheets.VaR.getRange('D6:D11').setNumberFormat(money);
table('Expected Shortfall','One-day Expected Shortfall', ['Method','Confidence','ES (CAD)'],data.risk_summary.map(r=>[r.method,r.confidence,r.es]),[24,18,24]);
sheets['Expected Shortfall'].getRange('B6:B11').setNumberFormat('0%');
table('Fixed Income','Fixed-income analytics', ['Security','Dirty price','Clean price','YTM','Macaulay (yr)','Modified (yr)','Convexity (yr²)','DV01 (CAD/bp)'],data.fixed_income.map(r=>[r.security_id,r.dirty_price,r.clean_price,r.ytm,r.macaulay_duration,r.modified_duration,r.convexity,r.position_dv01]),[20,18,18,15,20,20,22,23]);
sheets['Fixed Income'].getRange(`D6:D${5+data.fixed_income.length}`).setNumberFormat('0.00%');
table('Risk Contribution','99% parametric risk contribution', ['Security','Component VaR (CAD)','Marginal VaR (CAD/unit)','Standalone VaR (CAD)','Asset class','Currency','Sector'],data.contributions.map(r=>[r.security_id,r.component_var,r.marginal_var,r.standalone_var,r.asset_class,r.currency,r.sector]),[20,25,27,25,26,15,24]);
table('Stress Tests','Full-repricing stress P&L', ['Scenario','Security','Asset class','P&L (CAD)'],data.stress.map(r=>[r.scenario,r.security_id,r.asset_class,r.pnl]),[24,20,26,24]);
table('Yield Curve','Yield-curve scenario repricing', ['Scenario','Security','Full P&L (CAD)','Linear P&L (CAD)','Nonlinear difference'],data.curves.map(r=>[r.scenario,r.security_id,r.pnl,r.linear_pnl,r.nonlinear_difference]),[26,20,25,25,26]);
table('Risk Attribution','Change in 99% one-day parametric VaR', ['Driver','Allocated change (CAD)','Standalone change (CAD)'],data.attribution.map(r=>[r.driver,r.allocated_change,r.standalone_change]),[36,27,29]);
const attr=data.attribution_summary;
sheets['Risk Attribution'].getRange('E5:F9').values=[['Reconciliation','CAD'],['Prior VaR',attr.prior_var],['Current VaR',attr.current_var],['Interactions already allocated',attr.interaction_vs_standalone],['Numerical residual',attr.residual]];
sheets['Risk Attribution'].getRange('E5:E12').format.columnWidth=37;
sheets['Risk Attribution'].getRange('F5:F12').format.columnWidth=22;
sheets['Risk Attribution'].getRange('F6:F9').setNumberFormat(decimal);
table('Data Quality','Operational controls', ['Check','Severity','Record','Description','Action'],data.quality.map(r=>[r.check_id,r.severity,r.record,r.description,r.action]),[27,14,20,68,60]);
const qc=sheets['Data Quality'].getRange(`B6:B${5+data.quality.length}`);
qc.conditionalFormats.add('containsText',{text:'FAIL',format:{fill:'#FCE5E3',font:{color:'#A42525',bold:true}}});
qc.conditionalFormats.add('containsText',{text:'WARN',format:{fill:'#FFF0CC',font:{color:'#805C13'}}});
table('Trades','Trade and cash ledger', ['Trade ID','Security','Trade date','Settlement date','Quantity','Price','Currency','Type'],data.inputs.trades.map(r=>[r.trade_id,r.security_id,new Date(r.trade_date),new Date(r.settlement_date),r.quantity,r.price,r.currency,r.trade_type]),[29,20,19,21,22,18,15,18]);
sheets.Trades.getRange(`C6:D${5+data.inputs.trades.length}`).setNumberFormat('yyyy-mm-dd');
table('Security Master','Security master', ['Security','Name','Type','Asset class','Currency','Maturity','Coupon','Frequency','Face','Multiplier','Rating'],data.inputs.security_master.map(r=>[r.security_id,r.name,r.security_type,r.asset_class,r.currency,r.maturity_date?new Date(r.maturity_date):null,r.coupon_rate,r.coupon_frequency,r.face_value,r.multiplier,r.credit_rating]),[20,34,18,25,15,20,16,16,16,16,16]);
sheets['Security Master'].getRange(`F6:F${5+data.inputs.security_master.length}`).setNumberFormat('yyyy-mm-dd');
sheets['Security Master'].getRange(`G6:G${5+data.inputs.security_master.length}`).setNumberFormat('0.00%');
table('Market Data','Market observations and provenance', ['Date','Security','Local price','Adjusted price','Source','Retrieved at'],data.inputs.market_prices.map(r=>[new Date(r.date),r.security_id,r.price,r.adjusted_price,r.source,r.retrieval_timestamp]),[19,20,18,20,82,32]);
sheets['Market Data'].getRange(`A6:A${5+data.inputs.market_prices.length}`).setNumberFormat('yyyy-mm-dd');
table('Daily Report','Daily risk notes', ['Topic','Method / assumption'],[
 ['Calibration window',`${data.metadata.window_start} to ${data.metadata.window_end}`],
 ['Loss convention','Positive loss VaR/ES, positive gain P&L; values in CAD'],
 ['Historical / Monte Carlo','Full bond and option repricing; instantaneous shocks, no carry'],
 ['Covariance',data.metadata.covariance],['Simulations',data.metadata.simulations],['Random seed',data.metadata.seed],
 ['Performance',data.metadata.performance_basis],['Attribution',attr.methodology],
 ['Volatility floor hits',data.metadata.volatility_floor_hits],['Workbook refresh','Risk analytics are Python snapshots; rerun the CLI to refresh.'],
 ['Formula scope','NAV, allocations and checks recalculate from Positions; VaR requires a new Python run.']
],[27,110]);
table('Checks','Independent reconciliations', ['Check','Difference','Tolerance','Status'],[
 ['NAV versus Python',null,.01,null],['Component sum versus VaR',null,.01,null],['Attribution bridge',null,.01,null],['Position weights',null,1e-10,null]
],[35,24,20,18]);
const checks=sheets.Checks;
checks.getRange('F5:G7').values=[['Independent Python controls','Value'],['NAV',data.nav],['99% parametric VaR',data.risk_summary.find(r=>r.method==='Parametric'&&r.confidence===.99).var]];
checks.getRange('F5:F7').format.columnWidth=34; checks.getRange('G5:G7').format.columnWidth=24;
checks.getRange('B6:B9').formulas=[['=\'Portfolio Summary\'!B6-G6'],[`=SUM('Risk Contribution'!B6:B${5+data.contributions.length})-G7`],[`='Risk Attribution'!F7-'Risk Attribution'!F6-SUM('Risk Attribution'!B6:B${5+data.attribution.length})`],[`=SUM('Positions'!G6:G${5+p.length})-1`]];
checks.getRange('D6:D9').formulas=[6,7,8,9].map(r=>[`=IF(ABS(B${r})<=C${r},"PASS","FAIL")`]);
checks.getRange('B6:B9').setNumberFormat('0.00');
checks.getRange('D6:D9').conditionalFormats.add('containsText',{text:'FAIL',format:{fill:'#FCE5E3',font:{color:'#A42525',bold:true}}});

// Verify a representative input change propagates through NAV, then restore it.
wb.recalculate();
const initial=summary.getRange('B6').values[0][0];
const originalQuantity=positions.getRange('B6').values[0][0];
positions.getRange('B6').values=[[originalQuantity+1]];
const bumped=summary.getRange('B6').values[0][0];
if(!(bumped>initial)) throw new Error('NAV did not respond to quantity');
positions.getRange('B6').values=[[originalQuantity]];
wb.recalculate();
if(Math.abs(summary.getRange('B6').values[0][0]-data.nav)>.01) throw new Error('NAV reconciliation failed');
console.log((await wb.inspect({kind:'table',range:'Checks!A5:D9',include:'values,formulas',tableMaxRows:5,tableMaxCols:4})).ndjson);
console.log((await wb.inspect({kind:'match',searchTerm:'#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A|#NUM!|#NULL!',options:{useRegex:true,maxResults:30},summary:'Formula errors'})).ndjson);
if(renderFlag==='--render') {
  const previewDir=path.join(path.dirname(reportPath),'workbook_previews'); await fs.mkdir(previewDir,{recursive:true});
  for(const name of names) {
    const last=Math.min(name==='Portfolio Summary'?11:(name==='Checks'?6:Math.max(1,sheets[name].getUsedRange().values[4]?.length-1||1)),10);
    const preview=await wb.render({sheetName:name,...(name==='Portfolio Summary'?{autoCrop:'all'}:{range:`A1:${col(last)}18`}),scale:1.4,format:'png'});
    await fs.writeFile(path.join(previewDir,name.replaceAll(' ','_')+'.png'),new Uint8Array(await preview.arrayBuffer()));
  }
}
await (await SpreadsheetFile.exportXlsx(wb)).save(outputPath);
console.log(`Saved ${outputPath}`);
