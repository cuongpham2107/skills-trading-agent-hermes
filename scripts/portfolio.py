#!/usr/bin/env python3
"""
Portfolio & Analysis Journal Manager for DNSE Stock Analysis.

Usage:
  python3 portfolio.py log_analysis --ticker HPG --date 2026-07-30 ...
  python3 portfolio.py add_position --ticker HPG --buy-date 2026-07-30 --buy-price 24.8 --quantity 1000
  python3 portfolio.py close_position --ticker HPG --sell-date 2026-08-15 --sell-price 26.5
  python3 portfolio.py status
  python3 portfolio.py daily_check
  python3 portfolio.py review --ticker HPG --days 30
  python3 portfolio.py stats
"""

import sqlite3, json, sys, os, argparse, csv
from datetime import datetime, date, timedelta

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "trading.db")

def get_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS positions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticker TEXT NOT NULL,
            buy_date TEXT NOT NULL,
            buy_price REAL NOT NULL,
            quantity INTEGER NOT NULL,
            status TEXT NOT NULL DEFAULT 'open',
            sell_date TEXT,
            sell_price REAL,
            realized_pnl REAL,
            notes TEXT,
            created_at TEXT DEFAULT (datetime('now', 'localtime'))
        );
        CREATE TABLE IF NOT EXISTS analysis_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticker TEXT NOT NULL,
            date TEXT NOT NULL,
            close_price REAL,
            rating TEXT,
            action TEXT,
            target_price REAL,
            stop_loss REAL,
            confidence REAL,
            bull_case TEXT,
            bear_case TEXT,
            key_news TEXT,
            final_recommendation TEXT,
            created_at TEXT DEFAULT (datetime('now', 'localtime'))
        );
        CREATE TABLE IF NOT EXISTS outcome_review (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            analysis_id INTEGER REFERENCES analysis_log(id),
            review_date TEXT NOT NULL,
            days_later INTEGER,
            actual_price REAL,
            price_change_pct REAL,
            was_correct TEXT,
            notes TEXT,
            created_at TEXT DEFAULT (datetime('now', 'localtime'))
        );
        CREATE INDEX IF NOT EXISTS idx_analysis_ticker_date ON analysis_log(ticker, date);
        CREATE INDEX IF NOT EXISTS idx_positions_status ON positions(status);

        -- Reference data: all VN stock symbols with industry (from vnstock)
        CREATE TABLE IF NOT EXISTS reference_symbols (
            symbol TEXT PRIMARY KEY,
            company_name TEXT,
            industry_l2 TEXT,
            industry_l3 TEXT,
            industry_l4 TEXT,
            com_type_code TEXT,
            icb_code2 TEXT,
            icb_code4 TEXT
        );

        -- Wishlist: stocks user is interested in but hasn't bought yet
        CREATE TABLE IF NOT EXISTS wishlist (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticker TEXT NOT NULL UNIQUE,
            added_date TEXT NOT NULL,
            target_buy_price REAL,
            notes TEXT,
            priority TEXT DEFAULT 'medium',
            created_at TEXT DEFAULT (datetime('now', 'localtime'))
        );
        CREATE INDEX IF NOT EXISTS idx_wishlist_ticker ON wishlist(ticker);
    """)
    conn.commit()
    conn.close()

def cmd_log_analysis(args):
    init_db()
    conn = get_db()
    conn.execute("""
        INSERT INTO analysis_log (ticker, date, close_price, rating, action, 
            target_price, stop_loss, confidence, bull_case, bear_case, key_news, final_recommendation)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        args.ticker.upper(), args.date, args.close_price, args.rating, args.action,
        args.target_price, args.stop_loss, args.confidence,
        args.bull_case, args.bear_case, args.key_news, args.recommendation
    ))
    conn.commit()
    analysis_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    conn.close()

    journal_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "journal")
    os.makedirs(journal_dir, exist_ok=True)
    journal_path = os.path.join(journal_dir, f"{args.date}_{args.ticker.upper()}.md")
    with open(journal_path, "w") as f:
        f.write(f"# {args.ticker.upper()} — {args.date}\n\n")
        f.write(f"**Gia dong cua:** {args.close_price}\n")
        f.write(f"**Rating:** {args.rating} | **Action:** {args.action}\n")
        f.write(f"**Target:** {args.target_price} | **Stop-loss:** {args.stop_loss}\n")
        f.write(f"**Confidence:** {args.confidence}\n\n")
        f.write(f"## Bull Case\n{args.bull_case}\n\n")
        f.write(f"## Bear Case\n{args.bear_case}\n\n")
        f.write(f"## Key News\n{args.key_news}\n\n")
        f.write(f"## Final Recommendation\n{args.recommendation}\n")

    print(json.dumps({"status": "ok", "analysis_id": analysis_id, "journal": journal_path}))

def cmd_add_position(args):
    init_db()
    conn = get_db()
    conn.execute("""
        INSERT INTO positions (ticker, buy_date, buy_price, quantity, status)
        VALUES (?, ?, ?, ?, 'open')
    """, (args.ticker.upper(), args.buy_date, args.buy_price, args.quantity))
    conn.commit()
    pos_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    conn.close()
    print(json.dumps({"status": "ok", "position_id": pos_id,
        "ticker": args.ticker.upper(), "buy_price": args.buy_price,
        "quantity": args.quantity, "total_invested": args.buy_price * args.quantity}))

def cmd_close_position(args):
    init_db()
    conn = get_db()
    row = conn.execute(
        "SELECT id, buy_price, quantity FROM positions WHERE ticker=? AND status='open' ORDER BY buy_date DESC LIMIT 1",
        (args.ticker.upper(),)
    ).fetchone()
    if not row:
        print(json.dumps({"error": f"No open position for {args.ticker}"}))
        conn.close()
        return
    pos_id, buy_price, quantity = row
    realized_pnl = (args.sell_price - buy_price) * quantity
    pnl_pct = ((args.sell_price - buy_price) / buy_price) * 100
    conn.execute("""
        UPDATE positions SET status='closed', sell_date=?, sell_price=?, realized_pnl=?
        WHERE id=?
    """, (args.sell_date, args.sell_price, round(realized_pnl, 2), pos_id))
    conn.commit()
    conn.close()
    print(json.dumps({
        "status": "ok", "position_id": pos_id, "ticker": args.ticker.upper(),
        "buy_price": buy_price, "sell_price": args.sell_price, "quantity": quantity,
        "realized_pnl": round(realized_pnl, 2), "pnl_pct": round(pnl_pct, 2)
    }))

def cmd_status(args):
    init_db()
    conn = get_db()
    rows = conn.execute("""
        SELECT id, ticker, buy_date, buy_price, quantity, notes FROM positions WHERE status='open' ORDER BY buy_date DESC
    """).fetchall()
    conn.close()
    if not rows:
        print("Danh muc trong - chua co vi the nao dang mo.")
        return
    lines = ["DANH MUC HIEN TAI:", ""]
    total_invested = 0
    for r in rows:
        invested = r["buy_price"] * r["quantity"]
        total_invested += invested
        lines.append(f"  {r['ticker']} - mua {r['buy_date']} | {r['quantity']} cp x {r['buy_price']:,.0f}d = {invested:,.0f}d")
        if r["notes"]:
            lines.append(f"    Ghi chu: {r['notes']}")
    lines.append("")
    lines.append(f"  Tong dau tu: {total_invested:,.0f}d")
    print("\n".join(lines))

def cmd_daily_check(args):
    init_db()
    conn = get_db()
    rows = conn.execute("""
        SELECT id, ticker, buy_date, buy_price, quantity FROM positions WHERE status='open' ORDER BY buy_date
    """).fetchall()
    conn.close()
    if not rows:
        print(json.dumps({"status": "ok", "positions": [], "message": "No open positions"}))
        return
    today = date.today().isoformat()
    positions = [{"id": r["id"], "ticker": r["ticker"], "buy_date": r["buy_date"],
        "buy_price": r["buy_price"], "quantity": r["quantity"],
        "invested": r["buy_price"] * r["quantity"], "check_date": today} for r in rows]
    print(json.dumps({"status": "ok", "positions": positions}))

def cmd_review(args):
    init_db()
    conn = get_db()
    ticker = args.ticker.upper()
    days = args.days
    target_date = (date.today() - timedelta(days=days)).isoformat()
    row = conn.execute("""
        SELECT id, date, close_price, rating, action, target_price, stop_loss,
               confidence, bull_case, bear_case, final_recommendation
        FROM analysis_log WHERE ticker=? AND date <= ? ORDER BY date DESC LIMIT 1
    """, (ticker, target_date)).fetchone()
    if not row:
        print(f"Khong tim thay phan tich nao cho {ticker} truoc {target_date}")
        conn.close()
        return
    print(f"DANH GIA PHAN TICH {ticker} - {row['date']} (+{days} ngay)")
    print()
    print(f"Du doan goc: Rating {row['rating']} | Action {row['action']}")
    print(f"Gia luc phan tich: {row['close_price']}")
    print(f"Target: {row['target_price']} | Stop-loss: {row['stop_loss']}")
    print(f"Confidence: {row['confidence']}")
    print()
    print(f"Bull case: {row['bull_case']}")
    print(f"Bear case: {row['bear_case']}")
    print()
    print(f"Chay dnse_fetch.py {ticker} de lay gia hien tai va so sanh.")
    conn.close()

def cmd_import_symbols(args):
    init_db()
    csv_path = args.csv or os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "symbols_by_industries.csv")
    if not os.path.exists(csv_path):
        print(json.dumps({"error": f"CSV not found: {csv_path}"}))
        return
    conn = get_db()
    count = 0
    with open(csv_path, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            conn.execute("""
                INSERT OR REPLACE INTO reference_symbols (symbol, company_name, industry_l2, industry_l3, industry_l4, com_type_code, icb_code2, icb_code4)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (row["symbol"].strip(), row["organ_name"].strip(),
                  row.get("icb_name2", "").strip(), row.get("icb_name3", "").strip(),
                  row.get("icb_name4", "").strip(), row.get("com_type_code", "").strip(),
                  row.get("icb_code2", "").strip(), row.get("icb_code4", "").strip()))
            count += 1
    conn.commit()
    conn.close()
    print(json.dumps({"status": "ok", "imported": count}))

def cmd_wishlist(args):
    init_db()
    conn = get_db()
    rows = conn.execute("SELECT ticker, added_date, target_buy_price, notes, priority FROM wishlist ORDER BY priority, added_date").fetchall()
    conn.close()
    if not rows:
        print("Wishlist trong.")
        return
    for r in rows:
        target = f" - target {r['target_buy_price']:,.0f}d" if r['target_buy_price'] > 0 else ""
        notes = f" | {r['notes']}" if r['notes'] else ""
        print(f"  [{r['priority']}] {r['ticker']}{target} | them {r['added_date']}{notes}")

def cmd_wishlist_add(args):
    init_db()
    conn = get_db()
    try:
        conn.execute("INSERT INTO wishlist (ticker, added_date, target_buy_price, notes, priority) VALUES (?, ?, ?, ?, ?)",
            (args.ticker.upper(), date.today().isoformat(), args.target_price, args.notes, args.priority))
        conn.commit()
        print(json.dumps({"status": "ok", "ticker": args.ticker.upper()}))
    except sqlite3.IntegrityError:
        print(json.dumps({"error": f"{args.ticker} da co trong wishlist"}))
    conn.close()

def cmd_wishlist_remove(args):
    init_db()
    conn = get_db()
    conn.execute("DELETE FROM wishlist WHERE ticker=?", (args.ticker.upper(),))
    conn.commit()
    conn.close()
    print(json.dumps({"status": "ok", "ticker": args.ticker.upper()}))

def cmd_symbol_info(args):
    init_db()
    conn = get_db()
    row = conn.execute("SELECT * FROM reference_symbols WHERE symbol=?", (args.ticker.upper(),)).fetchone()
    conn.close()
    if not row:
        # Try importing first
        print(json.dumps({"error": f"{args.ticker} not in DB. Run 'import_symbols' first."}))
        return
    print(json.dumps({
        "symbol": row["symbol"], "company": row["company_name"],
        "industry_l2": row["industry_l2"], "industry_l3": row["industry_l3"],
        "industry_l4": row["industry_l4"], "com_type": row["com_type_code"]
    }, ensure_ascii=False))

def cmd_search_by_industry(args):
    init_db()
    conn = get_db()
    kw = f"%{args.keyword}%"
    rows = conn.execute("""
        SELECT symbol, company_name, industry_l4 FROM reference_symbols
        WHERE industry_l2 LIKE ? OR industry_l3 LIKE ? OR industry_l4 LIKE ? OR company_name LIKE ?
        ORDER BY symbol LIMIT 30
    """, (kw, kw, kw, kw)).fetchall()
    conn.close()
    if not rows:
        print(f"Khong tim thay ma nao lien quan '{args.keyword}'. Thu 'import_symbols' truoc.")
        return
    for r in rows:
        print(f"  {r['symbol']} - {r['company_name']} [{r['industry_l4']}]")

def cmd_stats(args):
    init_db()
    conn = get_db()
    total_analyses = conn.execute("SELECT COUNT(*) FROM analysis_log").fetchone()[0]
    total_reviews = conn.execute("SELECT COUNT(*) FROM outcome_review").fetchone()[0]
    correct = conn.execute("SELECT COUNT(*) FROM outcome_review WHERE was_correct='yes'").fetchone()[0]
    closed = conn.execute("SELECT COUNT(*), SUM(realized_pnl) FROM positions WHERE status='closed'").fetchone()
    open_pos = conn.execute("SELECT COUNT(*), SUM(buy_price * quantity) FROM positions WHERE status='open'").fetchone()
    accuracy = (correct / total_reviews * 100) if total_reviews > 0 else 0
    lines = ["THONG KE HE THONG", ""]
    lines.append(f"Tong so phan tich: {total_analyses}")
    lines.append(f"Da review: {total_reviews}")
    if total_reviews > 0:
        lines.append(f"Du doan dung: {correct}/{total_reviews} ({accuracy:.0f}%)")
    else:
        lines.append("Chua co review nao")
    lines.append("")
    lines.append(f"Vi the da dong: {closed[0]} lenh | P&L: {closed[1] or 0:,.0f}d")
    lines.append(f"Vi the dang mo: {open_pos[0]} lenh | Dau tu: {open_pos[1] or 0:,.0f}d")
    print("\n".join(lines))
    conn.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Portfolio Manager")
    sub = parser.add_subparsers(dest="command")

    p = sub.add_parser("log_analysis")
    p.add_argument("--ticker", required=True)
    p.add_argument("--date", required=True)
    p.add_argument("--close-price", type=float, required=True)
    p.add_argument("--rating", required=True)
    p.add_argument("--action", required=True)
    p.add_argument("--target-price", type=float, required=True)
    p.add_argument("--stop-loss", type=float, required=True)
    p.add_argument("--confidence", type=float, required=True)
    p.add_argument("--bull-case", default="")
    p.add_argument("--bear-case", default="")
    p.add_argument("--key-news", default="[]")
    p.add_argument("--recommendation", default="")

    p = sub.add_parser("add_position")
    p.add_argument("--ticker", required=True)
    p.add_argument("--buy-date", required=True)
    p.add_argument("--buy-price", type=float, required=True)
    p.add_argument("--quantity", type=int, required=True)

    p = sub.add_parser("close_position")
    p.add_argument("--ticker", required=True)
    p.add_argument("--sell-date", required=True)
    p.add_argument("--sell-price", type=float, required=True)

    sub.add_parser("status")
    sub.add_parser("daily_check")
    p = sub.add_parser("review")
    p.add_argument("--ticker", required=True)
    p.add_argument("--days", type=int, required=True)
    sub.add_parser("stats")

    # -- import_symbols --
    p = sub.add_parser("import_symbols")
    p.add_argument("--csv", default="")

    # -- wishlist --
    sub.add_parser("wishlist")
    p = sub.add_parser("wishlist_add")
    p.add_argument("--ticker", required=True)
    p.add_argument("--target-price", type=float, default=0)
    p.add_argument("--notes", default="")
    p.add_argument("--priority", default="medium")

    p = sub.add_parser("wishlist_remove")
    p.add_argument("--ticker", required=True)

    # -- symbol_info --
    p = sub.add_parser("symbol_info")
    p.add_argument("--ticker", required=True)

    # -- search_by_industry --
    p = sub.add_parser("search_by_industry")
    p.add_argument("--keyword", required=True)

    args = parser.parse_args()
    cmds = {
        "log_analysis": cmd_log_analysis,
        "add_position": cmd_add_position,
        "close_position": cmd_close_position,
        "status": cmd_status,
        "daily_check": cmd_daily_check,
        "review": cmd_review,
        "stats": cmd_stats,
        "import_symbols": cmd_import_symbols,
        "wishlist": cmd_wishlist,
        "wishlist_add": cmd_wishlist_add,
        "wishlist_remove": cmd_wishlist_remove,
        "symbol_info": cmd_symbol_info,
        "search_by_industry": cmd_search_by_industry,
    }
    if args.command in cmds:
        cmds[args.command](args)
    else:
        parser.print_help()
