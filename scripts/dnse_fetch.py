#!/usr/bin/env python3
"""Fetch stock data from DNSE OpenAPI. Usage: python3 dnse_fetch.py TICKER > output.json

Requires env: DNSE_API_KEY, DNSE_API_SECRET
Set in ~/.hermes/.env or export before running.
"""

import os, sys, json, hmac, hashlib, uuid, urllib.request, base64
from datetime import datetime, timedelta, timezone

API_BASE = "https://openapi.dnse.com.vn"

def die(msg):
    print(json.dumps({"error": msg}, ensure_ascii=False))
    sys.exit(1)

API_KEY = os.environ.get("DNSE_API_KEY")
API_SECRET = os.environ.get("DNSE_API_SECRET")
if not API_KEY or not API_SECRET:
    die("Missing DNSE_API_KEY or DNSE_API_SECRET env vars. Set in ~/.hermes/.env")

def sign(method, path):
    date = datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S GMT")
    nonce = uuid.uuid4().hex
    # Strip query string from path for signing (DNSE auth fails if query params included)
    sign_path = path.split("?")[0]
    signing = f"(request-target): {method.lower()} {sign_path}\ndate: {date}\nnonce: {nonce}"
    mac = hmac.new(API_SECRET.encode(), signing.encode(), hashlib.sha256)
    b64 = base64.b64encode(mac.digest()).decode()
    encoded = b64.replace("+", "%2B").replace("/", "%2F").replace("=", "%3D")
    sig_header = f'Signature keyId="{API_KEY}",algorithm="hmac-sha256",headers="(request-target) date",signature="{encoded}",nonce="{nonce}"'
    return date, sig_header

def fetch(path):
    date, sig = sign("GET", path)
    req = urllib.request.Request(f"{API_BASE}{path}")
    req.add_header("Accept", "application/json")
    req.add_header("X-Api-Key", API_KEY)
    req.add_header("X-Signature", sig)
    req.add_header("Date", date)
    req.add_header("version", "2026-05-07")
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        body = e.read().decode() if e.fp else ""
        raise Exception(f"HTTP {e.code}: {body}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        die("Usage: python3 dnse_fetch.py TICKER")
    
    ticker = sys.argv[1].upper()
    results = {"ticker": ticker, "date": datetime.now().strftime("%Y-%m-%d")}
    errors = []

    # 1. Close price
    try:
        r = fetch(f"/price/{ticker}/close")
        prices = r.get("prices", [])
        main = next((p for p in prices if p.get("boardId") == "G1" and p.get("closePrice", 0) > 0), None)
        if not main:
            main = next((p for p in prices if p.get("closePrice", 0) > 0), None)
        results["closePrice"] = main.get("closePrice", 0) if main else 0
    except Exception as e:
        results["closePrice"] = 0
        errors.append(f"close: {e}")

    # 2. OHLC (90 days)
    try:
        to_d = datetime.now()
        from_d = to_d - timedelta(days=90)
        from_ts = int(from_d.timestamp())
        to_ts = int(to_d.timestamp())
        r = fetch(f"/price/ohlc?symbol={ticker}&type=STOCK&resolution=1D&from={from_ts}&to={to_ts}")
        if r.get("t"):
            t, o, h, l, c, v = r["t"], r["o"], r["h"], r["l"], r["c"], r["v"]
            results["ohlcHistory"] = [
                {"t": t[i], "o": o[i], "h": h[i], "l": l[i], "c": c[i], "v": v[i]}
                for i in range(len(t))
            ]
        else:
            results["ohlcHistory"] = r.get("data", [])
    except Exception as e:
        results["ohlcHistory"] = []
        errors.append(f"ohlc: {e}")

    # 3. Latest trades
    try:
        r = fetch(f"/price/{ticker}/trades/latest?boardId=G1")
        results["latestTrades"] = r.get("data", r) if isinstance(r, dict) else r
    except Exception as e:
        results["latestTrades"] = []
        errors.append(f"trades: {e}")

    # 4. Latest quotes (bid/ask)
    try:
        r = fetch(f"/price/{ticker}/quotes/latest")
        results["latestQuotes"] = r
    except Exception as e:
        results["latestQuotes"] = {}
        errors.append(f"quotes: {e}")

    # 5. Foreign trading (30 days max per DNSE API limit)
    try:
        to_d = datetime.now()
        from_d = to_d - timedelta(days=30)
        from_ts = int(from_d.timestamp())
        to_ts = int(to_d.timestamp())
        r = fetch(f"/price/{ticker}/foreign-trading?from={from_ts}&to={to_ts}")
        results["foreignTrading"] = r
    except Exception as e:
        results["foreignTrading"] = {}
        errors.append(f"foreign: {e}")

    # 6. Secdef (trần/sàn/tham chiếu)
    try:
        r = fetch(f"/price/{ticker}/secdef")
        results["secDef"] = r
    except Exception as e:
        results["secDef"] = {}
        errors.append(f"secdef: {e}")

    # 7. Instruments
    try:
        r = fetch(f"/instruments?symbol={ticker}&limit=1")
        results["instruments"] = r
    except Exception as e:
        results["instruments"] = {}
        errors.append(f"instruments: {e}")

    if errors:
        results["_errors"] = errors

    print(json.dumps(results, ensure_ascii=False, indent=2))
