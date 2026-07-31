# DNSE API Authentication — Debugging Notes

Session: 2026-07-30, debugging OA-400 errors on OHLC/trades/foreign endpoints.

## Working auth format (confirmed)

Headers:
  X-Api-Key: <API_KEY>
  Date: Mon, 28 Jul 2026 12:00:00 GMT
  X-Signature: Signature keyId="<API_KEY>",algorithm="hmac-sha256",headers="(request-target) date",signature="<ENCODED_SIG>",nonce="<NONCE>"
  version: 2026-05-07

Signing string:
  (request-target): get /price/ohlc
  date: Mon, 28 Jul 2026 12:00:00 GMT
  nonce: abc123...

## Critical: query params in signing path

WRONG (causes OA-400):
  path = "/price/ohlc?symbol=HPG&type=STOCK&resolution=1D&from=123&to=456"
  signing = "(request-target): get {path}\ndate:...\nnonce:..."

CORRECT:
  sign_path = path.split("?")[0]  # "/price/ohlc"
  signing = "(request-target): get {sign_path}\ndate:...\nnonce:..."
  # But use FULL path for the HTTP request URL

## New docs format (DOES NOT WORK)

The docs at developers.dnse.com.vn show X-API-Key + X-Aux-Date with +0000 format.
Tested both — OA-400 on ALL endpoints. Old format (X-Api-Key + Date GMT) works.

## foreign-trading range limit

Max ~30 days. 60 or 90 days returns "range exceeds maximum time range".
