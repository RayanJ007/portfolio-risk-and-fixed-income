from pathlib import Path
import json
from importlib.metadata import version
import pandas as pd

r = json.loads(Path('outputs/risk_report.json').read_text())
m = r['metadata']
summary = pd.DataFrame(r['risk_summary'])
stress = pd.DataFrame(r['stress']).groupby('scenario').pnl.sum()
print('crash', stress['Equity crash'], 'metadata', m['window_start'], m['window_end'], m['observations'])
p = Path('README.md')
s = p.read_text(encoding='utf-8')
s = s.replace('**Data note:** Holdings and most market histories are synthetic and reproducible. A separate mixed-data run uses archived real Bank of Canada USD/CAD observations while other markets remain synthetic. Generated VaR, P&L, stress losses and performance metrics are not realized portfolio results.', '**Data note:** This project evaluates a hypothetical multi-asset portfolio using public historical market data. XIU.TO, SPY and TLT prices come from Yahoo Finance; USD/CAD and Canadian zero curves from the Bank of Canada; US zero curves from the Federal Reserve; investment-grade spreads from FRED; and VIX from Yahoo. Holdings, trades, bond terms and the European SPY call contract are hypothetical. These are cached historical valuations, not live quotes or actual investment performance.')
s = s.replace('Generated synthetic demonstration as of August 31, 2026, using 252 synchronized daily observations and 10,000 Monte Carlo simulations with seed 42:', 'Public-data hypothetical portfolio as of August 26, 2026 (prior August 25), using 252 synchronized daily observations and 10,000 Monte Carlo simulations with seed 42. The Canadian zero-curve publication lag determines the valuation cutoff:')
s = s.replace('CAD 101.39 million', 'CAD 110.46 million').replace('CAD 1.355 million', 'CAD 1.029 million').replace('CAD 1.340 million', 'CAD 1.000 million').replace('CAD −13.87 million', f'CAD −{abs(stress["Equity crash"])/1e6:.2f} million')
s = s.replace('Requests, PyYAML', 'Requests, yfinance, PyYAML').replace('CSV imports, public FX adapter and labelled sample generator', 'Public downloads, verified snapshots and hypothetical holdings')
s = s.replace('Methodology, validation and sample report', 'Methodology, validation and sample report\ntests/fixtures/   Deterministic synthetic tests, separate from portfolio inputs')
s = s.replace('python main.py demo --excel\nstreamlit', 'python main.py refresh --start 2023-09-01 --end 2026-08-31\npython main.py demo --excel\nstreamlit')
s = s.replace('The sample runs offline after installation and writes reports to `outputs/`.', 'The first refresh requires internet access. Subsequent `demo` runs reuse the verified local snapshot without network access and write reports to `outputs/`. Public-feed CSV caches are excluded from Git; refresh them locally. Refresh failures name the source and preserve the previous working configuration. There is no random-data fallback.')
start = s.index('For the archived real-FX example')
end = s.index('\n## Validation', start)
s = s[:start] + 'See the [data instructions](data/README.md) for source identifiers, units, offline rebuilds, cache locations and import commands. Each successful refresh creates a new snapshot and database path. Install optional notebook tools with `python -m pip install -e ".[notebooks]"`. Exact validated package versions are in `requirements-lock.txt`.\n' + s[end:]
s = s.replace('The 38-test suite', 'The automated suite')
s = s.replace('Most data is synthetic. ', 'Holdings and contract terms are hypothetical. Public feeds are not equivalent to Bloomberg/Refinitiv. The USD corporate bond uses an index OAS proxy; the European call uses VIX rather than contract-specific IV. Published zero curves are fitted estimates and can be revised; this is not a historical as-published trading backtest. ')
insert = '''## Data sources

| Input | Public source / convention |
|---|---|
| XIU.TO, SPY, TLT | Yahoo Finance via yfinance; close for marks, adjusted close for return shocks |
| USD/CAD | [Bank of Canada Valet](https://www.bankofcanada.ca/valet/docs/), FXUSDCAD; CAD per USD |
| CAD zero curve | [Bank of Canada](https://www.bankofcanada.ca/rates/interest-rates/bond-yield-curves/), 1/2/5/10/30 years |
| USD zero curve | [Federal Reserve GSW](https://www.federalreserve.gov/data/nominal-yield-curve.htm), SVENY01/02/05/10/30 |
| USD investment-grade spread | [FRED BAMLC0A0CM](https://fred.stlouisfed.org/series/BAMLC0A0CM), index OAS proxy |
| Option volatility | Yahoo ^VIX; 30-day S&P 500 proxy, divided by 100 |
| Ownership and instrument terms | Hypothetical holdings/trades; hypothetical bonds and European SPY call |

'''
s = s.replace('## How it works', insert + '## How it works')
p.write_text(s, encoding='utf-8')
p = Path('reports/risk_methodology.md')
s = p.read_text(encoding='utf-8')
a = s.index('The default portfolio has')
b = s.index('\n\n| Input', a)
s = s[:a] + 'The default portfolio holds XIU.TO, SPY, TLT, a hypothetical CAD government bond, a hypothetical USD investment-grade bond, CAD/USD cash and a hypothetical European SPY call. All quantities and ledger entries are hypothetical. Bond terms and option terms are assumptions, not identified listed securities or actual holdings. No issuer-specific rating or CUSIP is invented.' + s[b:]
s = s.replace('The demo explicitly records CAD 685,000 of bond coupons on August 31, 2026.', 'Opening positions are established at the prior valuation date using model/market marks. A funded XIU.TO purchase occurs on the current date. Coupon income across the comparison interval is explicit; ETF distributions are booked on ex-date as a simplified dividend receivable treated as cash, not represented as actual settlement cash. There is no reconstructed multi-year ownership ledger.')
s = s.replace('The default dates span Friday to Monday, so daily P&L contains calendar carry and the coupon receipts over that interval.', 'The default dates are consecutive common weekdays; daily P&L includes calendar carry and any explicitly booked income over that interval.')
a = s.index('`demo` uses seeded')
b = s.index('\n\n`market_prices.price`', a)
s = s[:a] + '''`refresh` retrieves approximately three years of real public observations; `demo` imports/reuses the saved public snapshot offline. Yahoo/yfinance supplies ETF history and descriptive metadata, Bank of Canada supplies CAD per USD FX and fitted Canadian zero yields, Federal Reserve GSW supplies fitted USD zero yields, FRED supplies BAMLC0A0CM investment-grade OAS, and Yahoo supplies VIX. [Source identifiers, transformations and retrieval instructions](../data/README.md) are recorded alongside SHA-256 checksums. Normalized source snapshots retain missing observations; failed retrievals are recorded and never invoke random-data generation. Synthetic histories exist only in deterministic tests.

Canadian zero rates are published as decimals. The [BoC methodology, section 5.1](https://publications.gc.ca/collections/Collection/FB3-2-104-48E.pdf) defines continuous zero yields. USD SVENYxx fields are continuous yields in percent, divided by 100. Only published 1/2/5/10/30-year nodes enter the database; interpolation occurs in pricing. These are fitted market curves, not directly traded zero-coupon quotes. The existing ACT/365 pricing convention is retained as a modelling convention rather than a claim to reproduce every vendor day-count rule.

The historical valuation cutoff is the latest consecutive pair of common complete dates in the snapshot. BoC's publication lag limits the bundled report to August 26, 2026. All estimation and valuation levels are cut off at their economic observation dates, but current downloads can contain revisions and information published later than those dates. This is a retrospective risk study, not an as-published backtest: retrieval timestamps do not prove historical availability.

Index OAS is divided by 100 and applied as a flat continuous spread to the hypothetical USD investment-grade bond. This approximation does not reproduce a specific issuer or the index's cash flows. VIX/100 supplies annual volatility for the hypothetical European SPY call (strike USD 800, expiry August 31, 2027, multiplier 100, assumed dividend yield 1.2%). VIX is a 30-day S&P 500 volatility measure, not that contract's implied volatility. Current option-chain IV is deliberately excluded from an older valuation date; SPY listed options have American exercise and are not claimed to be exactly priced by this European model.''' + s[b:]
s = s.replace('requiring at least 100.', 'requiring all 252 in the public-data configuration (the generic engine and deterministic fixtures permit a lower configured minimum).')
s = s.replace('configured demo benchmark is the Canadian equity factor', 'configured benchmark is the XIU.TO adjusted-close factor')
p.write_text(s, encoding='utf-8')
for p in Path('notebooks').glob('*.ipynb'):
    n = json.loads(p.read_text(encoding='utf-8'))
    for c in n['cells']:
        c['source'] = [line.replace('synthetic portfolio', 'hypothetical portfolio using public market observations') for line in c['source']]
        if c['cell_type'] == 'code':
            c['outputs'] = []
            c['execution_count'] = None
    p.write_text(json.dumps(n, indent=1, ensure_ascii=False)+'\n', encoding='utf-8')
p = Path('requirements-lock.txt')
s = p.read_text().rstrip()+'\n'
for package in ['yfinance','beautifulsoup4','curl_cffi','lxml','multitasking','peewee','soupsieve','cffi','pycparser']:
    if package+'==' not in s:
        s += f'{package}=={version(package)}\n'
p.write_text(s)
