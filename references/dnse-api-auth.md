# DNSE API Authentication Details

## Working Auth Format (tested 2026-07-30)

DNSE docs hiển thị header mới (`X-API-Key`, `X-Aux-Date`, date format `+0000`) nhưng API thực tế vẫn dùng format cũ.

### Headers
```
X-Api-Key: <api_key>
Date: Mon, 30 Jul 2026 19:42:05 GMT    ← GMT format, NOT +0000
X-Signature: Signature keyId="<key>",algorithm="hmac-sha256",headers="(request-target) date",signature="<sig>",nonce="<nonce>"
version: 2026-05-07
Accept: application/json
```

### Signing String
```
(request-target): get <path_without_query_string>
date: Mon, 30 Jul 2026 19:42:05 GMT
nonce: <random_hex>
```

### CRITICAL: Strip query string from signing path

Endpoints WITH query params (OHLC, trades, foreign, instruments) sẽ fail OA-400 nếu query string bị include trong signing path.

```python
# WRONG
path = "/price/ohlc?symbol=HPG&type=STOCK&resolution=1D&from=...&to=..."
signing = f"(request-target): get {path}\n..."

# CORRECT
sign_path = path.split("?")[0]  # "/price/ohlc"
signing = f"(request-target): get {sign_path}\n..."
```

### Signature Encoding

HMAC-SHA256 → Base64 → URL-encode special chars:
- `+` → `%2B`
- `/` → `%2F`  
- `=` → `%3D`

### Rate Limits (observed)
- foreignTrading: max ~30 days range (beyond that: "range exceeds maximum time range")
- OHLC: 90 days OK
- Other endpoints: no observed limit

### Endpoints tested working
- GET /price/{ticker}/close → closePrice
- GET /price/ohlc?symbol=&type=STOCK&resolution=1D&from=&to= → OHLC candles
- GET /price/{ticker}/trades/latest?boardId=G1 → latest trades
- GET /price/{ticker}/quotes/latest → bid/ask
- GET /price/{ticker}/foreign-trading?from=&to= (max 30D) → NĐTNN
- GET /price/{ticker}/secdef → trần/sàn/tham chiếu
- GET /instruments?symbol=&limit=1 → thông tin công cụ
