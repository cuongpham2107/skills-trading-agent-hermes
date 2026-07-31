#!/usr/bin/env python3
"""
Fetch financial fundamentals + company info for a ticker via vnstock 4.0+ API.
MUST be run with PYTHONPATH="" + .venv/bin/python3 (brew Python 3.14 + vnstock 4.0.5).

Usage:
  PYTHONPATH="" .venv/bin/python3 fundamentals_fetch.py FPT              # summary
  PYTHONPATH="" .venv/bin/python3 fundamentals_fetch.py FPT --mode full  # full
"""

import sys, json, os

# CRITICAL: Hermes sets PYTHONPATH to its own venv (Python 3.11 site-packages),
# which shadows this venv's numpy. Clear it before any imports.
for key in list(os.environ.keys()):
    if key == "PYTHONPATH":
        del os.environ[key]

# Suppress vnstock's ad banner to stderr so stdout stays clean JSON
import io
_real_stdout = sys.stdout
sys.stdout = io.StringIO()

SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VENV_DIR = os.path.join(SKILL_DIR, ".venv")

if sys.prefix != VENV_DIR and not sys.prefix.startswith(VENV_DIR):
    print(json.dumps({"error": f"Must use {VENV_DIR}/bin/python3"}))
    sys.exit(1)

try:
    from vnstock import Fundamental, Reference
except ImportError as e:
    sys.stdout = _real_stdout
    print(json.dumps({"error": f"Import failed: {e}"}))
    sys.exit(1)

# Restore stdout now that vnstock ads are done
sys.stdout = _real_stdout


def safe_get(row, key):
    """Get a value from a row, handling NaN."""
    val = row.get(key)
    if val is None:
        return None
    try:
        if str(val) == 'nan':
            return None
        return float(val)
    except (ValueError, TypeError):
        return val


def extract_metrics(ratio_df):
    """Extract key financial metrics from ratio DataFrame."""
    m = {}
    item_map = {
        "trailing_eps": "eps",
        "book_value_per_share_bvps": "bvps",
        "pe_ratio": "pe",
        "pb_ratio": "pb",
        "roe_trailling": "roe",
        "roa_trailling": "roa",
        "gross_margin": "gross_margin",
        "net_margin": "net_margin",
        "debt_to_equity": "de_ratio",
        "debt_to_assets": "debt_to_assets",
        "interest_coverage": "interest_coverage",
        "short_term_ratio": "current_ratio",
        "quick_ratio": "quick_ratio",
        "cash_ratio": "cash_ratio",
        "dividend_yield": "dividend_yield",
        "beta": "beta",
        "ebit_margin": "ebit_margin",
        "total_asset_turnover": "asset_turnover",
        "equity_to_assets": "equity_to_assets",
    }
    for _, row in ratio_df.iterrows():
        iid = row.get("item_id", "")
        val = safe_get(row, "2026-Q2")
        if iid in item_map and val is not None:
            m[item_map[iid]] = round(val, 2)

    return m


def extract_income(df, prefix="q"):
    """Extract key P&L items."""
    items = {}
    item_map = {
        "revenue": "revenue",
        "gross_profit": "gross_profit",
        "operating_profit": "operating_profit",
        "profit_before_tax": "profit_before_tax",
        "net_profit": "net_profit",
    }
    # Determine available columns
    cols = [c for c in df.columns if c not in ("item", "item_id", "item_en", "unit")]
    for _, row in df.iterrows():
        iid = row.get("item_id", "")
        if iid in item_map:
            for col in cols[:4]:  # max 4 periods
                val = safe_get(row, col)
                if val is not None:
                    items[f"{item_map[iid]}_{col}"] = round(val, 0)

    # Calculate QoQ growth
    if "revenue_2026-Q2" in items and "revenue_2026-Q1" in items and items["revenue_2026-Q1"] > 0:
        items["revenue_qoq_pct"] = round((items["revenue_2026-Q2"] - items["revenue_2026-Q1"]) / items["revenue_2026-Q1"] * 100, 1)
    if "net_profit_2026-Q2" in items and "net_profit_2026-Q1" in items and items["net_profit_2026-Q1"] > 0:
        items["profit_qoq_pct"] = round((items["net_profit_2026-Q2"] - items["net_profit_2026-Q1"]) / items["net_profit_2026-Q1"] * 100, 1)

    return items


def extract_company(comp):
    """Extract company info from Reference.company(ticker)."""
    try:
        df = comp.info()
        if df is not None and not df.empty:
            row = df.iloc[0]
            return {
                "name": str(row.get("symbol", "")),
                "exchange": str(row.get("exchange", "")),
                "listing_date": str(row.get("listing_date", "")),
                "charter_capital": safe_get(row, "charter_capital"),
                "employees": safe_get(row, "number_of_employees"),
                "ceo": str(row.get("ceo_name", "")),
                "ceo_position": str(row.get("ceo_position", "")),
                "auditor": str(row.get("auditor", "")),
                "website": str(row.get("website", "")),
                "business_model": str(row.get("business_model", ""))[:500],
                "outstanding_shares": safe_get(row, "outstanding_shares"),
                "free_float_pct": safe_get(row, "free_float_percentage"),
            }
    except Exception as e:
        return {"error": str(e)}

    return {"error": "No company info"}


def extract_events(comp):
    """Extract corporate events."""
    try:
        df = comp.events()
        if df is not None and not df.empty:
            return df.head(10).to_dict(orient="records")
    except Exception:
        pass
    return []


def main():
    ticker = sys.argv[1].upper() if len(sys.argv) > 1 else None
    mode = "summary"
    for i, arg in enumerate(sys.argv[2:], 2):
        if arg == "--mode" and i < len(sys.argv):
            mode = sys.argv[i + 1]
        elif arg.startswith("--mode="):
            mode = arg.split("=")[1]

    if not ticker:
        print(json.dumps({"error": "Usage: fundamentals_fetch.py TICKER [--mode=summary|full]"}))
        sys.exit(1)

    try:
        fun = Fundamental()
        ref = Reference()
        comp = ref.company(ticker)
    except Exception as e:
        print(json.dumps({"error": f"Init failed: {e}"}))
        sys.exit(1)

    result = {"ticker": ticker, "mode": mode}

    # Company info
    result["company"] = extract_company(comp)
    result["events"] = extract_events(comp)

    # Financial ratios
    try:
        ratio_df = fun.equity(ticker).ratio()
        result["metrics"] = extract_metrics(ratio_df)
    except Exception as e:
        result["metrics"] = {"error": str(e)}

    # Income statement (yearly for trend analysis + quarterly for recent)
    try:
        inc_df_year = fun.equity(ticker).income_statement(period="year")
        result["income_yearly"] = extract_income(inc_df_year, prefix="year")
        if mode == "full":
            result["raw_income_yearly"] = inc_df_year.to_dict(orient="records")[:15]
    except Exception as e:
        result["income_yearly"] = {"error": str(e)}

    try:
        inc_df_q = fun.equity(ticker).income_statement(period="quarter")
        result["income_quarterly"] = extract_income(inc_df_q, prefix="q")
        if mode == "full":
            result["raw_income_quarterly"] = inc_df_q.to_dict(orient="records")[:15]
    except Exception as e:
        result["income_quarterly"] = {"error": str(e)}

    # Balance sheet (full mode only)
    if mode == "full":
        try:
            bs_df = fun.equity(ticker).balance_sheet(period="quarter")
            result["balance_sheet"] = bs_df.to_dict(orient="records")[:15]
        except Exception as e:
            result["balance_sheet"] = {"error": str(e)}

        try:
            cf_df = fun.equity(ticker).cash_flow(period="quarter")
            result["cash_flow"] = cf_df.to_dict(orient="records")[:15]
        except Exception as e:
            result["cash_flow"] = {"error": str(e)}

    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    main()
