# vnstock v4 API Migration Notes

## Installation

vnstock v4 can Python 3.10+ va nhieu dependencies. Tren macOS voi Homebrew Python, tao venv:

```bash
python3 -m venv .venv
.venv/bin/pip install vnstock
```

## No API Key Required

Guest mode: 20 req/min, khong can dang ky.

## API v3 to v4 Changes

Tat ca domain objects la methods nhan symbol parameter.

### Reference
```python
# v4 (correct)
ref.company(symbol='HPG').info()
ref.company(symbol='HPG').shareholders()
ref.company(symbol='HPG').insider_trading()
ref.company(symbol='HPG').news()
ref.company(symbol='HPG').events()
```

### Fundamental
```python
# v4 (correct)
fa.equity(symbol='HPG').balance_sheet(period='year')
fa.equity(symbol='HPG').income_statement(period='year')
fa.equity(symbol='HPG').cash_flow(period='year')
fa.equity(symbol='HPG').ratios(period='year')
```

## Working Endpoints
- profile: von dieu le, CEO, dia chi...
- ratios: 58 chi so (EPS, BVPS, P/E, ROE, ROA...)
