#!/usr/bin/env python3
"""
Data Lock — combines DNSE + vnstock data into a single verified JSON lock file.
All downstream agents MUST read from this file, not invent numbers.

Usage:
  PYTHONPATH="" .venv/bin/python3 scripts/data_lock.py FPT
  PYTHONPATH="" .venv/bin/python3 scripts/data_lock.py FPT --lock-dir data/
"""

import sys, json, os, subprocess, time
from datetime import datetime

SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VENV_PY = os.path.join(SKILL_DIR, ".venv/bin/python3")

def run_script(script_name, ticker):
    """Run a script and parse its JSON output (skipping vnstock banner)."""
    env = os.environ.copy()
    env["PYTHONPATH"] = ""
    r = subprocess.run(
        [VENV_PY, os.path.join(SKILL_DIR, "scripts", script_name), ticker],
        capture_output=True, text=True, env=env, timeout=60
    )
    out = r.stdout + r.stderr
    idx = out.index("{")
    return json.loads(out[idx:])

def assess_status(data, field):
    """Determine data_status for a field."""
    if data is None:
        return "missing"
    if isinstance(data, dict) and "error" in data:
        return "error"
    if isinstance(data, (list, dict)) and len(data) == 0:
        return "missing"
    return "real"

def main():
    ticker = sys.argv[1].upper() if len(sys.argv) > 1 else None
    if not ticker:
        print(json.dumps({"error": "Usage: data_lock.py TICKER [--lock-dir PATH]"}))
        sys.exit(1)

    lock_dir = next((sys.argv[i+1] for i, a in enumerate(sys.argv) if a == "--lock-dir"), "data")

    # Step 1a: Fetch market data
    try:
        market = run_script("dnse_fetch.py", ticker)
    except Exception as e:
        market = {"error": str(e), "ticker": ticker}

    # Step 1b: Fetch fundamentals
    try:
        fund = run_script("fundamentals_fetch.py", ticker)
    except Exception as e:
        fund = {"error": str(e), "ticker": ticker}

    # Build lock with data_status for every group
    today = datetime.now().strftime("%Y-%m-%d")
    lock = {
        "meta": {
            "ticker": ticker,
            "date": today,
            "generated_at": datetime.now().isoformat(),
            "version": "1.0",
            "source_scripts": ["dnse_fetch.py", "fundamentals_fetch.py"]
        },
        "price": {
            "data_status": assess_status(market, "closePrice"),
            "close": market.get("closePrice"),
            "open": None,
            "high": None,
            "low": None,
            "ceiling": None,
            "floor": None,
            "basic": None,
        },
        "ohlc_history": {
            "data_status": assess_status(market, "ohlcHistory"),
            "days": len(market.get("ohlcHistory", [])),
            "data": market.get("ohlcHistory", [])
        },
        "orderbook": {
            "data_status": assess_status(market, "latestQuotes"),
            "bids": [],
            "offers": [],
            "bid_volume": 0,
            "offer_volume": 0
        },
        "foreign_trading": {
            "data_status": assess_status(market, "foreignTrading"),
            "data": market.get("foreignTrading", {})
        },
        "secdef": {
            "data_status": assess_status(market, "secDef"),
            "basic_price": None,
            "ceiling": None,
            "floor": None,
            "exchange": None,
            "indexes": []
        },
        "fundamentals": {
            "data_status": assess_status(fund, "metrics"),
            "metrics": {},
            "income_yearly": {},
            "income_quarterly": {},
            "company": {}
        }
    }

    # Populate price from latest OHLC
    if lock["ohlc_history"]["data"]:
        latest = lock["ohlc_history"]["data"][-1]
        lock["price"]["open"] = latest.get("o")
        lock["price"]["high"] = latest.get("h")
        lock["price"]["low"] = latest.get("l")
        # close already set from closePrice

    # Populate secdef
    secdefs = market.get("secDef", [])
    if secdefs:
        sd = secdefs[0]
        lock["secdef"]["basic_price"] = sd.get("basicPrice")
        lock["secdef"]["ceiling"] = sd.get("ceilingPrice")
        lock["secdef"]["floor"] = sd.get("floorPrice")
        lock["secdef"]["exchange"] = sd.get("marketId")

    # Populate orderbook
    quotes = market.get("latestQuotes", {}).get("quotes", [])
    if quotes:
        q = quotes[0]
        lock["orderbook"]["bids"] = q.get("bid", [])
        lock["orderbook"]["offers"] = q.get("offer", [])
        lock["orderbook"]["bid_volume"] = sum(b.get("quantity", 0) for b in q.get("bid", []))
        lock["orderbook"]["offer_volume"] = sum(o.get("quantity", 0) for o in q.get("offer", []))

    # Populate instruments
    instruments = market.get("instruments", {}).get("data", [])
    if instruments:
        lock["secdef"]["indexes"] = instruments[0].get("indexName", [])
        lock["fundamentals"]["company"] = {
            "name": instruments[0].get("shortName", ""),
            "full_name": instruments[0].get("name", ""),
            "exchange": instruments[0].get("marketId", ""),
            "listed": instruments[0].get("listedDate", ""),
            "industry": instruments[0].get("symbolType", ""),
            "indexes": instruments[0].get("indexName", []),
        }

    # Populate fundamentals (if available)
    if fund.get("metrics") and "error" not in str(fund.get("metrics")):
        lock["fundamentals"]["metrics"] = fund.get("metrics", {})
    if fund.get("income_yearly") and "error" not in str(fund.get("income_yearly")):
        lock["fundamentals"]["income_yearly"] = fund.get("income_yearly", {})
    if fund.get("income_quarterly") and "error" not in str(fund.get("income_quarterly")):
        lock["fundamentals"]["income_quarterly"] = fund.get("income_quarterly", {})
    if fund.get("company") and "error" not in str(fund.get("company")):
        lock["fundamentals"]["company"].update(fund.get("company", {}))

    # Data status summary
    statuses = [
        lock["price"]["data_status"],
        lock["ohlc_history"]["data_status"],
        lock["fundamentals"]["data_status"],
        lock["foreign_trading"]["data_status"],
    ]
    lock["meta"]["overall_data_quality"] = "full" if all(s == "real" for s in statuses) else \
        "partial" if any(s == "real" for s in statuses) else "none"

    # Write lock file
    os.makedirs(os.path.join(SKILL_DIR, lock_dir), exist_ok=True)
    lock_path = os.path.join(SKILL_DIR, lock_dir, f".lock_{ticker}.json")
    with open(lock_path, "w") as f:
        json.dump(lock, f, ensure_ascii=False, indent=2, default=str)

    # Print summary to stdout so pipeline can log it
    print(json.dumps({
        "status": "ok",
        "ticker": ticker,
        "lock_file": lock_path,
        "overall_data_quality": lock["meta"]["overall_data_quality"],
        "checks": {
            "price": lock["price"]["data_status"],
            "ohlc": lock["ohlc_history"]["data_status"],
            "fundamentals": lock["fundamentals"]["data_status"],
            "foreign": lock["foreign_trading"]["data_status"],
        }
    }, ensure_ascii=False))

if __name__ == "__main__":
    main()
