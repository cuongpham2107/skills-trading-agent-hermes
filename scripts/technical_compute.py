#!/usr/bin/env python3
"""
Technical Compute — calculates ALL technical indicators using the `ta` library.
LLM only narrates meaning, never calculates numbers.

Uses: ta (Technical Analysis Library) — 130+ indicators, pure Python, no numba.

Usage:
  PYTHONPATH="" .venv/bin/python3 scripts/technical_compute.py --ticker FPT
  PYTHONPATH="" .venv/bin/python3 scripts/technical_compute.py --lock-file data/.lock_FPT.json
"""

import sys, json, os, math
import pandas as pd
import ta

SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOCK_DIR = os.path.join(SKILL_DIR, "data")


def find_support_resistance(highs, lows, current_price, window=2):
    """Find nearest support and resistance levels from swing points."""
    supports = []
    resistances = []
    h = list(highs)
    l = list(lows)
    for i in range(window, len(h) - window):
        if all(l[i] <= l[i+j] for j in range(-window, window+1)):
            supports.append(l[i])
        if all(h[i] >= h[i+j] for j in range(-window, window+1)):
            resistances.append(h[i])
    supports = sorted(set(round(s, 2) for s in supports if s < current_price), reverse=True)[:3]
    resistances = sorted(set(round(r, 2) for r in resistances if r > current_price))[:3]
    return supports, resistances


def volume_analysis(volumes, closes):
    """Analyze volume patterns."""
    v = list(volumes)
    c = list(closes)
    if len(v) < 20:
        return {"avg_20d": None, "avg_5d": None, "trend": "unknown", "ratio": None}
    avg20 = round(sum(v[-20:]) / 20, 0)
    avg5 = round(sum(v[-5:]) / 5, 0) if len(v) >= 5 else None
    ratio = round(avg5 / avg20, 2) if avg5 and avg20 else None
    if ratio and ratio > 1.5:
        trend = "increasing"
    elif ratio and ratio < 0.5:
        trend = "decreasing"
    else:
        trend = "stable"
    up_vol = sum(v[i] for i in range(1, len(v)) if c[i] > c[i-1])
    down_vol = sum(v[i] for i in range(1, len(v)) if c[i] < c[i-1])
    ud_ratio = round(up_vol / down_vol, 2) if down_vol > 0 else None
    return {"avg_20d": avg20, "avg_5d": avg5, "trend": trend, "ratio_vs_20d": ratio, "up_down_ratio": ud_ratio}


def compute_all(lock_data):
    """Compute all technical indicators using ta library."""
    ohlc = lock_data.get("ohlc_history", {}).get("data", [])
    if not ohlc or len(ohlc) < 30:
        return {"error": "Not enough OHLC data (need >=30 bars)", "bars": len(ohlc)}

    df = pd.DataFrame(ohlc)
    df.columns = ['t', 'o', 'h', 'l', 'c', 'v']
    
    closes = df['c']
    highs = df['h']
    lows = df['l']
    volumes = df['v']
    current = float(closes.iloc[-1])

    # ---- ta library indicators ----
    # Momentum
    rsi_val = round(float(ta.momentum.RSIIndicator(closes).rsi().iloc[-1]), 2)
    
    macd_obj = ta.trend.MACD(closes)
    macd_line = round(float(macd_obj.macd().iloc[-1]), 4)
    macd_signal = round(float(macd_obj.macd_signal().iloc[-1]), 4)
    macd_hist = round(float(macd_obj.macd_diff().iloc[-1]), 4)
    
    # Trend
    sma20_obj = ta.trend.SMAIndicator(closes, 20)
    sma20 = round(float(sma20_obj.sma_indicator().iloc[-1]), 2)
    
    sma50 = None
    if len(closes) >= 50:
        sma50 = round(float(ta.trend.SMAIndicator(closes, 50).sma_indicator().iloc[-1]), 2)
    
    ema20 = round(float(ta.trend.EMAIndicator(closes, 20).ema_indicator().iloc[-1]), 2)
    
    # ADX
    adx_val = round(float(ta.trend.ADXIndicator(highs, lows, closes).adx().iloc[-1]), 2)
    
    # Volatility
    bb_obj = ta.volatility.BollingerBands(closes)
    bb_upper = round(float(bb_obj.bollinger_hband().iloc[-1]), 2)
    bb_mid = round(float(bb_obj.bollinger_mavg().iloc[-1]), 2)
    bb_lower = round(float(bb_obj.bollinger_lband().iloc[-1]), 2)
    
    atr_obj = ta.volatility.AverageTrueRange(highs, lows, closes)
    atr_val = round(float(atr_obj.average_true_range().iloc[-1]), 2)
    
    # -- Custom: support/resistance, volume, changes --
    supports, resistances = find_support_resistance(highs, lows, current)
    vol = volume_analysis(volumes, closes)
    
    cs = list(closes)
    
    # === B.3 Cross-check: compare TA trend vs actual 5D price action ===
    cross_check_warnings = []
    price_5d_change = round((cs[-1] - cs[-6]) / cs[-6] * 100, 1) if len(cs) >= 6 else None
    
    # Determine actual 5D trend from raw prices
    if price_5d_change is not None:
        rising_days = sum(1 for i in range(len(cs)-5, len(cs)) if cs[i] > cs[i-1])
        if rising_days >= 4 and price_5d_change > 2:
            actual_5d = "TĂNG"
        elif rising_days <= 1 and price_5d_change < -2:
            actual_5d = "GIẢM"
        else:
            actual_5d = "SIDEWAY"
    else:
        actual_5d = "unknown"
    
    # TA-based trend from SMA
    ta_trend = "TĂNG" if current > sma20 else "GIẢM"
    
    # Flag divergence
    if ta_trend == "TĂNG" and actual_5d == "GIẢM":
        cross_check_warnings.append(
            f"⚠️ DIVERGENCE: Technical trend='TĂNG' nhưng giá 5D thực tế {actual_5d} ({price_5d_change}%). Có thể false signal."
        )
    elif ta_trend == "GIẢM" and actual_5d == "TĂNG":
        cross_check_warnings.append(
            f"⚠️ DIVERGENCE: Technical trend='GIẢM' nhưng giá 5D thực tế {actual_5d} (+{price_5d_change}%). Có thể đang đảo chiều."
        )
    
    return {
        "generated_at": lock_data.get("meta", {}).get("generated_at", ""),
        "ticker": lock_data["meta"]["ticker"],
        "current_price": current,
        "library": "ta",
        "trend": {
            "sma20": sma20,
            "sma50": sma50,
            "ema20": ema20,
            "trend_vs_sma20": "above" if current > sma20 else "below",
            "trend_vs_sma50": "above" if sma50 and current > sma50 else "below" if sma50 else "unknown",
            "price_vs_20d_high": round((current - max(cs[-20:])) / max(cs[-20:]) * 100, 1) if cs[-20:] else None,
            "price_vs_20d_low": round((current - min(cs[-20:])) / min(cs[-20:]) * 100, 1) if cs[-20:] else None,
        },
        "momentum": {
            "rsi14": rsi_val,
            "macd": macd_line,
            "macd_signal": macd_signal,
            "macd_histogram": macd_hist,
            "adx14": adx_val,
        },
        "volatility": {
            "atr14": atr_val,
            "bollinger_upper": bb_upper,
            "bollinger_middle": bb_mid,
            "bollinger_lower": bb_lower,
            "atr_pct": round(atr_val / current * 100, 1) if current and atr_val else None,
        },
        "support_resistance": {
            "supports": supports,
            "resistances": resistances,
            "nearest_support": supports[0] if supports else None,
            "nearest_resistance": resistances[0] if resistances else None,
        },
        "volume": vol,
        "change": {
            "from_peak_65d": round((current - max(cs)) / max(cs) * 100, 1),
            "from_trough_65d": round((current - min(cs)) / min(cs) * 100, 1),
            "change_1d": round((cs[-1] - cs[-2]) / cs[-2] * 100, 1) if len(cs) >= 2 else None,
            "change_5d": price_5d_change,
            "change_20d": round((cs[-1] - cs[-21]) / cs[-21] * 100, 1) if len(cs) >= 21 else None,
        },
        "cross_check": {
            "ta_trend": ta_trend,
            "actual_5d_trend": actual_5d,
            "price_5d_change_pct": price_5d_change,
            "warnings": cross_check_warnings,
            "has_divergence": len(cross_check_warnings) > 0,
        }
    }


def main():
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--lock-file", help="Path to lock file")
    p.add_argument("--ticker", help="Ticker symbol (auto-finds lock file)")
    args = p.parse_args()

    if args.lock_file:
        lock_path = args.lock_file
    elif args.ticker:
        lock_path = os.path.join(LOCK_DIR, f".lock_{args.ticker}.json")
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
