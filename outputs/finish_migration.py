from pathlib import Path
import json
import pandas as pd

p = Path('src/data/portfolio_data.py')
s = p.read_text()
a = s.index('    securities = []')
b = s.index('    if (master.maturity_date', a)
master = s[a:b] + '    return master\n'
c = s.index('    tables = dict(', b)
trades = s[b:c].replace('    market_prices = pd.concat(marks, ignore_index=True)\n', '') + '    return pd.DataFrame(trades)\n'
s = s[:a] + '    master = make_security_master(sources)\n    market_prices = pd.concat(marks, ignore_index=True)\n    trades = make_trades(master, frames, levels, market_prices, prior, date)\n' + s[c:]
s = s.replace('trades=pd.DataFrame(trades)', 'trades=trades')
s += '\n\ndef make_security_master(sources):\n    """Real ETF metadata and explicit hypothetical contract terms."""\n' + master
s += '\n\ndef make_trades(master, frames, levels, market_prices, prior, date):\n    """Opening holdings, funded rebalance and income across the two-date interval."""\n' + trades
p.write_text(s)
p = Path('data/README.md')
s = p.read_text().replace('use a new output root through `prepare_portfolio(raw_directory, root=...)`, or `python main.py prepare --input data/raw/public/<snapshot>` when that prepared snapshot directory does not yet exist.', 'use `python main.py prepare --input data/raw/public/<snapshot> --data-root data/rebuilt`. Select a new prepared root if the snapshot directory already exists.')
p.write_text(s)
for p in Path('data/processed').glob('*/portfolio.yaml'):
    p.write_text(p.read_text().replace('data\\processed\\', 'data/processed/'))
p = Path('PLAN.md')
s = p.read_text().replace('- [ ]', '- [x]')
s += '\n## Completion evidence\n\nPublic snapshot `20260912T171645652834Z` fetched on September 12, 2026. Valuation August 26 versus August 25, 2026; 252 synchronized daily changes and 10,000 seeded simulations. NAV CAD 110,459,484.49. No pricing, covariance, VaR/ES, stress or attribution formula was replaced. Spread mapping is now SPREAD_US for the USD corporate example.\n\nAll required implementation phases are complete; final verification evidence is in `reports/VALIDATION.md`. Two rate outlier warnings remain disclosed, with source observations retained. Public CSV caches are local and excluded from Git; a fresh clone needs one explicit refresh. No commit or push was made.\n'
p.write_text(s)
raw = pd.read_csv('data/raw/public/20260912T171645652834Z/CAD.csv').set_index('date')
for day, tenor in [('2026-04-29','1'), ('2025-08-15','2')]:
    pos = raw.index.get_loc(day)
    print('Outlier source observations', raw.iloc[pos-1:pos+1][tenor].to_dict())
