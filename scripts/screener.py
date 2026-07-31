#!/usr/bin/env python3
"""
Stock screener — quick scan a universe of tickers, compute composite scores,
and return ranked results. Uses vnstock 4.0 Fundamental API.

Usage:
  PYTHONPATH="" .venv/bin/python3 screener.py VN30          # VN30 stocks
  PYTHONPATH="" .venv/bin/python3 screener.py VN100         # VN100 stocks
  PYTHONPATH="" .venv/bin/python3 screener.py NGANH "Ngân hàng"  # by industry
  PYTHONPATH="" .venv/bin/python3 screener.py LIST TCB,VIB,FPT   # custom list
  PYTHONPATH="" .venv/bin/python3 screener.py VN30 --limit 5     # top 5 only
"""

import sys, json, os, time

# CRITICAL: clear PYTHONPATH to avoid numpy conflict with hermes-agent venv
for key in list(os.environ.keys()):
    if key == "PYTHONPATH":
        del os.environ[key]

SKILL_DIR = os.path.dirname(os.path.abspath(__file__))
VENV_DIR = os.path.join(SKILL_DIR, "..", ".venv")

try:
    from vnstock import Fundamental, Reference
except ImportError as e:
    print(json.dumps({"error": f"Import failed: {e}"}))
    sys.exit(1)


# ── VN30 ticker list (hardcoded — most efficient) ──────────────
VN30 = [
    "ACB", "BCM", "BID", "BVH", "CTG", "FPT", "GAS", "GVR", "HDB", "HPG",
    "MBB", "MSN", "MWG", "PLX", "POW", "SAB", "SHB", "SSI", "STB", "TCB",
    "TPB", "VCB", "VHM", "VIB", "VIC", "VJC", "VNM", "VPB", "VRE", "SSB"
]


def get_tickers(universe, arg=None):
    """Resolve universe name to a list of tickers."""
    if universe.upper() == "VN30":
        return VN30
    elif universe.upper() == "VN100":
        try:
            ref = Reference()
            df = ref.equity.list_by_index("VN100")
            if df is not None and not df.empty:
                return list(df["symbol"])[:100]
        except Exception:
            pass
        return VN30  # fallback
    elif universe.upper() == "NGANH" and arg:
        try:
            ref = Reference()
            df = ref.equity.list_by_industry()
            if df is not None and not df.empty:
                # Filter by industry name (fuzzy match)
                mask = df["icb_name"].str.contains(arg, case=False, na=False)
                return list(df[mask]["symbol"])[:50]
        except Exception:
            pass
        return []
    elif universe.upper() == "LIST" and arg:
        return [t.strip().upper() for t in arg.split(",") if t.strip()]
    elif universe.upper() == "HOSE":
        try:
            ref = Reference()
            df = ref.equity.list_by_exchange("HOSE")
            if df is not None and not df.empty:
                return list(df["symbol"])[:400]
        except Exception:
            pass
        return VN30
    else:
        # Assume it's a ticker or comma-separated list
        return [t.strip().upper() for t in universe.split(",") if t.strip()]


def safe_get(row, key):
    val = row.get(key)
    if val is None or str(val) == 'nan':
        return None
    try:
        return float(val)
    except (ValueError, TypeError):
        return None


def score_ticker(fun, ticker):
    """Fetch ratio data for a ticker and compute composite score."""
    try:
        df = fun.equity(ticker).ratio()
    except Exception:
        return None

    metrics = {}
    for _, row in df.iterrows():
        iid = row.get("item_id", "")
        val = safe_get(row, "2026-Q2")
        if val is None:
            continue
        if iid == "trailing_eps":
            metrics["eps"] = val
        elif iid == "pe_ratio":
            metrics["pe"] = val
        elif iid == "pb_ratio":
            metrics["pb"] = val
        elif iid == "roe_trailling":
            metrics["roe"] = val
        elif iid == "roa_trailling":
            metrics["roa"] = val
        elif iid == "net_margin":
            metrics["net_margin"] = val
        elif iid == "gross_margin":
            metrics["gross_margin"] = val
        elif iid == "debt_to_equity":
            metrics["de_ratio"] = val

    if "eps" not in metrics or "roe" not in metrics:
        return None

    return {
        "ticker": ticker,
        "eps": metrics.get("eps", 0),
        "pe": metrics.get("pe", 999),
        "pb": metrics.get("pb", 99),
        "roe": metrics.get("roe", 0),
        "roa": metrics.get("roa", 0),
        "net_margin": metrics.get("net_margin", 0),
        "gross_margin": metrics.get("gross_margin", 0),
        "de_ratio": metrics.get("de_ratio", 0),
    }


def compute_scores(results):
    """Normalize and compute composite scores."""
    if not results:
        return []

    # Get max values for normalization
    valid = [r for r in results if r["pe"] > 0 and r["pe"] < 999]
    if not valid:
        return results

    max_roe = max(r["roe"] for r in valid)
    max_pe = max(r["pe"] for r in valid)
    max_pb = max(r["pb"] for r in valid if r["pb"] > 0)

    for r in valid:
        # P/E score: lower is better (inverted)
        pe_score = max(0, (1 - r["pe"] / max_pe)) * 35

        # ROE score: higher is better
        roe_score = min(30, (r["roe"] / max(max_roe, 1)) * 30)

        # P/B score: lower is better
        pb_score = max(0, (1 - r["pb"] / max(max_pb, 1))) * 15

        # Growth/Quality score (net_margin + roa)
        quality_score = min(20, (r.get("net_margin", 0) / 30) * 10 + (r.get("roa", 0) / 15) * 10)

        r["score"] = round(pe_score + roe_score + pb_score + quality_score, 1)
        r["pe_score"] = round(pe_score, 1)
        r["roe_score"] = round(roe_score, 1)
        r["quality_score"] = round(quality_score, 1)

    valid.sort(key=lambda x: x["score"], reverse=True)
    return valid


def main():
    universe = sys.argv[1] if len(sys.argv) > 1 else "VN30"
    arg = sys.argv[2] if len(sys.argv) > 2 and not sys.argv[2].startswith("--") else None
    limit = 10
    for i, a in enumerate(sys.argv):
        if a == "--limit" and i + 1 < len(sys.argv):
            limit = int(sys.argv[i + 1])

    tickers = get_tickers(universe, arg)
    if not tickers:
        print(json.dumps({"error": f"No tickers found for {universe} {arg or ''}"}))
        sys.exit(1)

    fun = Fundamental()
    results = []
    errors = []

    # Rate limit: free tier = 20 req/min → 3.5s between requests
    DELAY = 3.5  # seconds between requests

    for i, ticker in enumerate(tickers):
        if i > 0:
            time.sleep(DELAY)
        r = score_ticker(fun, ticker)
        if r:
            results.append(r)
        else:
            errors.append(ticker)

    scored = compute_scores(results)
    top = scored[:limit]

    print(json.dumps({
        "universe": universe,
        "total_scanned": len(tickers),
        "scored": len(results),
        "errors": len(errors),
        "error_tickers": errors[:10],
        "top": top,
    }, ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    main()
