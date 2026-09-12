from pathlib import Path
import requests
import yfinance as yf

r = requests.get('https://www.bankofcanada.ca/stats/results/csv', params={'lookupPage':'lookup_yield_curve.php','startRange':'1986-01-01','searchRange':'','dFrom':'2023-09-01','dTo':'2026-08-31'}, timeout=40)
Path('outputs/boc_curve.csv').write_text(r.text, encoding='utf-8')
print(r.status_code, r.url, r.text[:2000], flush=True)
r = requests.get('https://www.bankofcanada.ca/wp-content/uploads/2010/02/wp04-48.pdf', timeout=40)
Path('outputs/boc_method.pdf').write_bytes(r.content)
print('method', r.status_code, flush=True)
try:
    options = yf.Ticker('SPY').options
    print('SPY expiries', options[:4], flush=True)
except Exception as e:
    print('option chain unavailable', repr(e), flush=True)
