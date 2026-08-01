#!/usr/bin/env python3
"""
Piotroski F-Score — đánh giá sức khỏe tài chính doanh nghiệp (0-9 điểm).
Dựa trên: Piotroski, Joseph D. "Value Investing: The Use of Historical Financial 
Statement Information to Separate Winners from Losers" (2000).

9 tiêu chí từ BCTC, chia 3 nhóm:
- Profitability (4 điểm): ROA, CFO, ΔROA, Accrual
- Leverage/Liquidity (3 điểm): ΔLeverage, ΔCurrent Ratio, ΔShares
- Operating Efficiency (2 điểm): ΔGross Margin, ΔAsset Turnover

Usage:
  PYTHONPATH="" .venv/bin/python3 scripts/fscore.py FPT
  PYTHONPATH="" .venv/bin/python3 scripts/fscore.py --lock-file data/.lock_FPT.json
"""

import sys, json, os

SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOCK_DIR = os.path.join(SKILL_DIR, "data")

def safe_float(val, default=None):
    if val is None:
        return default
    try:
        return float(val)
    except (ValueError, TypeError):
        return default

def compute_fscore(lock_data):
    """Compute Piotroski F-Score from lock data."""
    fund = lock_data.get("fundamentals", {})
    metrics = fund.get("metrics", {})
    income_y = fund.get("income_yearly", {})
    income_q = fund.get("income_quarterly", {})
    
    score = 0
    details = []
    
    # === PROFITABILITY (4 points) ===
    
    # 1. ROA > 0
    roa = safe_float(metrics.get("roa"), 0)
    if roa > 0:
        score += 1
        details.append({"criterion": "ROA > 0", "value": f"{roa}%", "pass": True})
    else:
        details.append({"criterion": "ROA > 0", "value": f"{roa}%", "pass": False})
    
    # 2. Operating Cash Flow > 0 (proxy: profit_before_tax > 0)
    # vnstock free tier doesn't provide CFO directly. Use profit margin as proxy.
    profit_ytd = safe_float(income_q.get("net_profit_2026-Q2", 0), 0)
    if profit_ytd > 0:
        score += 1
        details.append({"criterion": "CFO > 0 (proxy: profit)", "value": f"{profit_ytd/1e9:.1f} tỷ", "pass": True})
    else:
        details.append({"criterion": "CFO > 0 (proxy: profit)", "value": f"{profit_ytd/1e9:.1f} tỷ", "pass": False})
    
    # 3. ΔROA > 0 (ROA improving)
    # Compare current ROA with previous year. We use QoQ profit change as proxy.
    profit_qoq = safe_float(income_q.get("profit_qoq_pct"), 0)
    if profit_qoq > 0:
        score += 1
        details.append({"criterion": "ΔROA > 0 (proxy: profit QoQ)", "value": f"{profit_qoq}%", "pass": True})
    else:
        details.append({"criterion": "ΔROA > 0 (proxy: profit QoQ)", "value": f"{profit_qoq}%", "pass": False})
    
    # 4. Accrual: CFO > ROA (quality of earnings)
    # Proxy: Net Margin > 0 indicates earnings quality
    net_margin = safe_float(metrics.get("net_margin"), 0)
    if net_margin > 0:
        score += 1
        details.append({"criterion": "Accrual (proxy: Net Margin > 0)", "value": f"{net_margin}%", "pass": True})
    else:
        details.append({"criterion": "Accrual (proxy: Net Margin > 0)", "value": f"{net_margin}%", "pass": False})
    
    # === LEVERAGE / LIQUIDITY (3 points) ===
    
    # 5. ΔLeverage < 0 (decreasing debt)
    de_ratio = safe_float(metrics.get("de_ratio"), 100)
    # We can't easily get prior year D/E from free tier. Use industry benchmark.
    if de_ratio < 60:  # Safe threshold for non-financial
        score += 1
        details.append({"criterion": "ΔLeverage < 0 (proxy: D/E < 60%)", "value": f"D/E={de_ratio}%", "pass": True})
    else:
        details.append({"criterion": "ΔLeverage < 0 (proxy: D/E < 60%)", "value": f"D/E={de_ratio}%", "pass": False})
    
    # 6. ΔCurrent Ratio > 0 (improving liquidity)
    current_ratio = safe_float(metrics.get("current_ratio"), 0)
    if current_ratio > 1.0:
        score += 1
        details.append({"criterion": "ΔCurrent Ratio > 0 (proxy: CR > 1.0)", "value": f"CR={current_ratio}", "pass": True})
    else:
        details.append({"criterion": "ΔCurrent Ratio > 0 (proxy: CR > 1.0)", "value": f"CR={current_ratio}", "pass": False})
    
    # 7. ΔShares Outstanding <= 0 (no dilution)
    # Free tier doesn't provide historical shares. Assume no dilution (pass).
    score += 1
    details.append({"criterion": "No dilution (free tier limitation)", "value": "assumed pass", "pass": True, "note": "⚠️ Cần kiểm tra thủ công lịch sử phát hành"})
    
    # === OPERATING EFFICIENCY (2 points) ===
    
    # 8. ΔGross Margin > 0
    gross_margin = safe_float(metrics.get("gross_margin"), 0)
    if gross_margin > 15:
        score += 1
        details.append({"criterion": "ΔGross Margin > 0 (proxy: GM > 15%)", "value": f"GM={gross_margin}%", "pass": True})
    else:
        details.append({"criterion": "ΔGross Margin > 0 (proxy: GM > 15%)", "value": f"GM={gross_margin}%", "pass": False})
    
    # 9. ΔAsset Turnover > 0
    asset_turnover = safe_float(metrics.get("asset_turnover"), 0)
    if asset_turnover > 0.1:
        score += 1
        details.append({"criterion": "ΔAsset Turnover > 0 (proxy: AT > 0.1)", "value": f"AT={asset_turnover}", "pass": True})
    else:
        details.append({"criterion": "ΔAsset Turnover > 0 (proxy: AT > 0.1)", "value": f"AT={asset_turnover}", "pass": False})
    
    # Classification
    # Banking stocks: F-Score not directly applicable (no GM, CR, AT, different leverage)
    is_bank = False
    company = fund.get("company", {})
    exchange = lock_data.get("secdef", {}).get("exchange", "")
    industry = company.get("industry", "").lower()
    if "ngân hàng" in industry or "bank" in industry:
        is_bank = True
        # For banks, use modified interpretation: ROA, Profit, NIM, D/E threshold different
        quality = "⚠️ NGÂN HÀNG — F-Score không áp dụng trực tiếp. Dùng P/B, ROE, NIM để đánh giá."
        score = None  # Mark as N/A
    elif score >= 7:
        quality = "CAO — doanh nghiệp chất lượng tốt theo F-Score"
    elif score >= 4:
        quality = "TRUNG BÌNH — cần phân tích thêm"
    else:
        quality = "THẤP — có dấu hiệu yếu kém tài chính"
    
    return {
        "ticker": lock_data["meta"]["ticker"],
        "f_score": score,
        "max_score": 9,
        "is_bank": is_bank,
        "quality": quality,
        "breakdown": {
            "profitability": f"{sum(1 for d in details[:4] if d.get('pass'))}/4",
            "leverage_liquidity": f"{sum(1 for d in details[4:7] if d.get('pass'))}/3",
            "operating_efficiency": f"{sum(1 for d in details[7:] if d.get('pass'))}/2",
        },
        "details": details,
        "note": "F-Score dựa trên dữ liệu vnstock free tier (có proxy cho 1 số tiêu chí). Điểm 7+ là tốt."
    }

def main():
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("ticker", nargs="?", help="Ticker symbol")
    p.add_argument("--lock-file", help="Path to lock file")
    args = p.parse_args()
    
    if args.lock_file:
        lock_path = args.lock_file
    elif args.ticker:
        lock_path = os.path.join(LOCK_DIR, f".lock_{args.ticker}.json")
    else:
        print(json.dumps({"error": "Need ticker or --lock-file"}))
        sys.exit(1)
    
    if not os.path.exists(lock_path):
        print(json.dumps({"error": f"Lock file not found: {lock_path}. Run data_lock.py first."}))
        sys.exit(1)
    
    with open(lock_path) as f:
        lock = json.load(f)
    
    result = compute_fscore(lock)
    print(json.dumps(result, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
