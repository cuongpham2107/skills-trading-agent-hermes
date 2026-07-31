#!/usr/bin/env python3
"""
Technical Compute — calculates ALL technical indicators from OHLC data.
LLM only narrates meaning, never calculates numbers.

Usage:
  PYTHONPATH="" python3 scripts/technical_compute.py --lock-file data/.lock_FPT.json
  PYTHONPATH="" python3 scripts/technical_compute.py --ticker FPT --lock-dir data/
"""

import sys, json, os, math

SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def sma(data, period):
    """Simple Moving Average."""
    if len(data) < period:
        return None
    return round(sum(data[-period:]) / period, 2)

def ema(data, period):
    """Exponential Moving Average."""
    if len(data) < period:
        return None
    k = 2 / (period + 1)
    ema_val = sum(data[:period]) / period
    for val in data[period:]:
        ema_val = val * k + ema_val * (1 - k)
    return round(ema_val, 2)

def rsi(closes, period=14):
    """Relative Strength Index."""
    if len(closes) < period + 1:
        return None
    gains = []
    losses = []
    for i in range(1, len(closes)):
        diff = closes[i] - closes[i-1]
        gains.append(diff if diff > 0 else 0)
        losses.append(abs(diff) if diff < 0 else 0)
    avg_gain = sum(gains[-period:]) / period
    avg_loss = sum(losses[-period:]) / period
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return round(100 - 100 / (1 + rs), 2)

def macd(closes, fast=12, slow=26, signal=9):
    """MACD line, signal line, histogram."""
    if len(closes) < slow + signal:
        return None, None, None
    ema_fast = closes[0]
    ema_slow = closes[0]
    macd_vals = []
    for i, c in enumerate(closes):
        ema_fast = c * (2/(fast+1)) + ema_fast * (1 - 2/(fast+1))
        ema_slow = c * (2/(slow+1)) + ema_slow * (1 - 2/(slow+1))
        macd_vals.append(ema_fast - ema_slow)
    signal_vals = []
    sig = sum(macd_vals[:signal]) / signal
    for v in macd_vals[signal-1:]:
        sig = v * (2/(signal+1)) + sig * (1 - 2/(signal+1))
        signal_vals.append(sig)
    macd_line = round(macd_vals[-1], 4)
    signal_line = round(signal_vals[-1], 4)
    histogram = round(macd_line - signal_line, 4)
    return macd_line, signal_line, histogram

def atr(highs, lows, closes, period=14):
    """Average True Range."""
    if len(closes) < period + 1:
        return None
    tr_vals = []
    for i in range(1, len(closes)):
        tr = max(highs[i] - lows[i], abs(highs[i] - closes[i-1]), abs(lows[i] - closes[i-1]))
        tr_vals.append(tr)
    return round(sum(tr_vals[-period:]) / period, 2)

def bollinger_bands(closes, period=20, std_dev=2):
    """Bollinger Bands: middle, upper, lower."""
    if len(closes) < period:
        return None, None, None
    mid = sum(closes[-period:]) / period
    variance = sum((c - mid) ** 2 for c in closes[-period:]) / period
    std = math.sqrt(variance)
    return round(mid, 2), round(mid + std_dev * std, 2), round(mid - std_dev * std, 2)

def adx(highs, lows, closes, period=14):
    """Average Directional Index."""
    if len(closes) < period * 2:
        return None
    tr_vals = []
    plus_dm = []
    minus_dm = []
    for i in range(1, len(closes)):
        tr = max(highs[i] - lows[i], abs(highs[i] - closes[i-1]), abs(lows[i] - closes[i-1]))
        tr_vals.append(tr)
        up = highs[i] - highs[i-1]
        down = lows[i-1] - lows[i]
        plus_dm.append(up if up > down and up > 0 else 0)
        minus_dm.append(down if down > up and down > 0 else 0)
    atr14 = sum(tr_vals[-period:]) / period if tr_vals else 0
    if atr14 == 0:
        return None
    plus_di = (sum(plus_dm[-period:]) / period) / atr14 * 100
    minus_di = (sum(minus_dm[-period:]) / period) / atr14 * 100
    dx = abs(plus_di - minus_di) / (plus_di + minus_di) * 100 if (plus_di + minus_di) != 0 else 0
    # Approximate ADX as DX for simplicity
    return round(dx, 2)

def find_support_resistance(closes, highs, lows, current_price):
    """Find nearest support and resistance levels from swing points."""
    supports = []
    resistances = []
    for i in range(2, len(lows) - 2):
        if lows[i] < lows[i-1] and lows[i] < lows[i-2] and lows[i] < lows[i+1] and lows[i] < lows[i+2]:
            supports.append(lows[i])
        if highs[i] > highs[i-1] and highs[i] > highs[i-2] and highs[i] > highs[i+1] and highs[i] > highs[i+2]:
            resistances.append(highs[i])
    supports = sorted(set(round(s, 2) for s in supports if s < current_price), reverse=True)[:3]
    resistances = sorted(set(round(r, 2) for r in resistances if r > current_price))[:3]
    return supports, resistances

def volume_analysis(volumes, closes):
    """Analyze volume patterns."""
    if not volumes or len(volumes) < 20:
        return {"avg_20d": None, "avg_5d": None, "trend": "unknown", "ratio": None}
    avg20 = round(sum(volumes[-20:]) / 20, 0)
    avg5 = round(sum(volumes[-5:]) / 5, 0) if len(volumes) >= 5 else None
    ratio = round(avg5 / avg20, 2) if avg5 and avg20 else None
    if ratio and ratio > 1.5:
        trend = "increasing"
    elif ratio and ratio < 0.5:
        trend = "decreasing"
    else:
        trend = "stable"
    # Up/down volume ratio
    up_vol = sum(volumes[i] for i in range(1, len(volumes)) if closes[i] > closes[i-1])
    down_vol = sum(volumes[i] for i in range(1, len(volumes)) if closes[i] < closes[i-1])
    ud_ratio = round(up_vol / down_vol, 2) if down_vol > 0 else None
    return {"avg_20d": avg20, "avg_5d": avg5, "trend": trend, "ratio_vs_20d": ratio, "up_down_ratio": ud_ratio}

def compute_all(lock_data):
    """Compute all technical indicators from lock data."""
    ohlc = lock_data.get("ohlc_history", {}).get("data", [])
    if not ohlc or len(ohlc) < 30:
        return {"error": "Not enough OHLC data (need >=30 bars)", "bars": len(ohlc)}

    closes = [b["c"] for b in ohlc]
    highs = [b["h"] for b in ohlc]
    lows = [b["l"] for b in ohlc]
    opens = [b["o"] for b in ohlc]
    volumes = [b["v"] for b in ohlc]
    current = closes[-1]

    supports, resistances = find_support_resistance(closes, highs, lows, current)
    vol = volume_analysis(volumes, closes)

    return {
        "generated_at": lock_data.get("meta", {}).get("generated_at", ""),
        "ticker": lock_data["meta"]["ticker"],
        "current_price": current,
        "trend": {
            "sma20": sma(closes, 20),
            "sma50": sma(closes, 50) if len(closes) >= 50 else None,
            "ema20": ema(closes, 20),
            "trend_vs_sma20": "above" if current > (sma(closes, 20) or current) else "below",
            "trend_vs_sma50": "above" if len(closes) >= 50 and current > (sma(closes, 50) or current) else "below" if len(closes) >= 50 else "unknown",
            "price_vs_20d_high": round((current - max(closes[-20:])) / max(closes[-20:]) * 100, 1) if closes[-20:] else None,
            "price_vs_20d_low": round((current - min(closes[-20:])) / min(closes[-20:]) * 100, 1) if closes[-20:] else None,
        },
        "momentum": {
            "rsi14": rsi(closes, 14),
            "macd": macd(closes)[0],
            "macd_signal": macd(closes)[1],
            "macd_histogram": macd(closes)[2],
            "adx14": adx(highs, lows, closes, 14),
        },
        "volatility": {
            "atr14": atr(highs, lows, closes, 14),
            "bollinger_upper": bollinger_bands(closes)[1],
            "bollinger_middle": bollinger_bands(closes)[0],
            "bollinger_lower": bollinger_bands(closes)[2],
            "atr_pct": round((atr(highs, lows, closes, 14) or 0) / current * 100, 1) if current else None,
        },
        "support_resistance": {
            "supports": supports,
            "resistances": resistances,
            "nearest_support": supports[0] if supports else None,
            "nearest_resistance": resistances[0] if resistances else None,
        },
        "volume": vol,
        "change": {
            "from_peak_65d": round((current - max(closes)) / max(closes) * 100, 1),
            "from_trough_65d": round((current - min(closes)) / min(closes) * 100, 1),
            "change_1d": round((closes[-1] - closes[-2]) / closes[-2] * 100, 1) if len(closes) >= 2 else None,
            "change_5d": round((closes[-1] - closes[-6]) / closes[-6] * 100, 1) if len(closes) >= 6 else None,
            "change_20d": round((closes[-1] - closes[-21]) / closes[-21] * 100, 1) if len(closes) >= 21 else None,
        }
    }

def main():
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--lock-file", help="Path to lock JSON file")
    p.add_argument("--ticker", help="Ticker symbol (auto-finds lock file)")
    p.add_argument("--lock-dir", default="data", help="Lock directory")
    args = p.parse_args()

    if args.lock_file:
        lock_path = args.lock_file
    elif args.ticker:
        lock_path = os.path.join(SKILL_DIR, args.lock_dir, f".lock_{args.ticker}.json")
    else:
        print(json.dumps({"error": "Need --lock-file or --ticker"}))
        sys.exit(1)

    if not os.path.exists(lock_path):
        print(json.dumps({"error": f"Lock file not found: {lock_path}. Run data_lock.py first."}))
        sys.exit(1)

    with open(lock_path) as f:
        lock = json.load(f)

    result = compute_all(lock)
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))

if __name__ == "__main__":
    main()
