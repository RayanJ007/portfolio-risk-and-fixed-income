from pathlib import Path
import requests
import yfinance as yf
import json

for ticker in ['XIU.TO', 'SPY', 'TLT', '^VIX']:
    try:
        obj = yf.Ticker(ticker)
        frame = obj.history(start='2023-09-01', end='2026-09-01', auto_adjust=False, raise_errors=True)
        frame.to_csv(Path('outputs') / (ticker.replace('^','') + '.csv'))
        meta = obj.history_metadata
        Path('outputs/' + ticker.replace('^','') + '_meta.json').write_text(json.dumps(meta, default=str))
        print(ticker, len(frame), frame.index.min(), frame.index.max(), meta.get('currency'), flush=True)
    except Exception as e:
        print(ticker, repr(e), flush=True)
url = 'https://www.federalreserve.gov/data/yield-curve-tables/feds200628.csv'
r = requests.get(url, timeout=45)
Path('outputs/fed.csv').write_text(r.text, encoding='utf-8')
print('fed', r.status_code, len(r.content), r.text[:1000], flush=True)
