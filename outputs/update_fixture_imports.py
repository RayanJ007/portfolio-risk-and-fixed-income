from pathlib import Path
for path in Path('tests').glob('test_*.py'):
    text = path.read_text().replace('from src.data.sample import', 'from tests.fixtures.synthetic import')
    text = text.replace('load_config()', 'load_config("tests/fixtures/portfolio.yaml")')
    text = text.replace('data/raw/boc_usdcad.csv', 'tests/fixtures/boc_usdcad.csv')
    path.write_text(text)
p = Path('tests/fixtures/synthetic.py')
p.write_text(p.read_text().replace('directory="data/sample"', 'directory'))
p = Path('config/portfolio.yaml')
p.write_text(p.read_text().replace('data\\processed\\', 'data/processed/'))
p = Path('src/data/portfolio_data.py')
p.write_text(p.read_text().replace('input_directory=str(directory)', 'input_directory=directory.as_posix()').replace('raw_directory=str(raw_directory)', 'raw_directory=raw_directory.as_posix()'))
