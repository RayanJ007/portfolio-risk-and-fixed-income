from pathlib import Path
import requests
from concurrent.futures import ThreadPoolExecutor

urls = {
    'boc_page': 'https://www.bankofcanada.ca/rates/interest-rates/bond-yield-curves/',
    'fed_page': 'https://www.federalreserve.gov/data/nominal-yield-curve.htm',
    'fred': 'https://fred.stlouisfed.org/graph/fredgraph.csv?id=BAMLC0A0CM&cosd=2023-09-01&coed=2026-08-31',
    'boc_fx': 'https://www.bankofcanada.ca/valet/observations/FXUSDCAD/json?start_date=2023-09-01&end_date=2026-08-31',
}
def fetch(item):
    name, url = item
    try:
        r = requests.get(url, timeout=40)
        Path(f'outputs/{name}.txt').write_text(r.text, encoding='utf-8')
        return name, r.status_code, len(r.content), r.text[:150]
    except Exception as e:
        return name, str(e)
print(list(ThreadPoolExecutor(4).map(fetch, urls.items())))
