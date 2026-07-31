# vnstock 4.0+ API Quick Reference

## Setup (verified 2026-07-31)

```bash
# Brew Python 3.14 required (system Python 3.9 too old for vnstock >=4.0)
/opt/homebrew/bin/python3 -m venv .venv
.venv/bin/pip install vnstock pandas requests
```

## API Usage

```python
from vnstock import Fundamental
fun = Fundamental()

# Financial ratios (P/E, P/B, ROE, ROA, EPS, BVPS, +50 indicators)
df = fun.equity("FPT").ratio()
# Key columns: item, item_id, 2026-Q2, 2025-Q4, 2026-Q1, 2025-Q4_1
# Key item_ids:
#   trailing_eps          -> EPS 4 quý gần nhất
#   book_value_per_share_bvps -> BVPS
#   price_to_earnings_ratio   -> P/E
#   price_to_book_ratio       -> P/B
#   return_on_equity          -> ROE
#   return_on_assets          -> ROA

# Income statement
df = fun.equity("FPT").income_statement(period='quarter')
# Key columns: item, item_id, 2026-Q2, 2026-Q1
# Key item_ids: revenue, gross_profit, operating_profit, net_profit, profit_before_tax

# Balance sheet
df = fun.equity("FPT").balance_sheet(period='quarter')

# Cash flow
df = fun.equity("FPT").cash_flow(period='quarter')
```

## Key differences v3 → v4

| Old (v3) | New (v4) |
|----------|----------|
| `vnstock.Fundamental()` | `from vnstock import Fundamental` |
| `fa.equity(symbol="FPT")` | `fun.equity("FPT")` (keyword arg removed) |
| `.ratios(period='year')` | `.ratio()` (name changed, no period param) |
| `vnstock.Reference()` | No longer exists in v4 |
| Installed via `--break-system-packages` | Dedicated `.venv` with brew Python |

## Limits

- Community edition: 4 reporting periods (free, sufficient for basic analysis)
- API key from vnstocks.com increases rate limits but not required
- Some fields (e.g. `price_to_earnings_ratio`, `price_to_book_ratio`) may be NaN for certain tickers — compute manually: P/E = price / EPS, P/B = price / BVPS
