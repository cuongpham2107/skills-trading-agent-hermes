#!/usr/bin/env python3
"""
Knowledge Query — TF-IDF + cosine similarity over knowledge base.
No external API, no GPU, no heavy deps. Just sklearn + numpy.

Usage:
  PYTHONPATH="" .venv/bin/python3 scripts/knowledge_query.py --ticker TCB --query "lãi suất NIM"
  PYTHONPATH="" .venv/bin/python3 scripts/knowledge_query.py --industry "ngân hàng" --top 5
"""

import sys, json, os, re, pickle
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KNOWLEDGE_DIR = os.path.join(SKILL_DIR, "knowledge")
INDEX_FILE = os.path.join(KNOWLEDGE_DIR, ".index", "tfidf_index.pkl")

TICKER_INDUSTRY = {}
TICKER_FILE = os.path.join(SKILL_DIR, "data", "symbols_by_industries.csv")
if os.path.exists(TICKER_FILE):
    with open(TICKER_FILE) as f:
        for line in f.readlines()[1:]:
            parts = line.strip().split(",")
            if len(parts) >= 2:
                TICKER_INDUSTRY[parts[0].strip().upper()] = parts[1].strip().lower()

def get_industry_context(ticker):
    """Get industry-related search terms from ticker."""
    if not ticker:
        return ""
    ticker = ticker.upper()
    industry = TICKER_INDUSTRY.get(ticker, "").lower()
    mapping = {
        "ngân hàng": "ngân hàng tín dụng lãi suất NIM CASA NPL room ngoại Basel",
        "công nghệ": "công nghệ outsourcing AI chuyển đổi số phần mềm viễn thông",
        "dệt may": "dệt may xuất khẩu đơn hàng nguyên liệu biên lợi nhuận",
        "thép": "thép HRC phôi giá thép xây dựng tôn mạ",
        "bất động sản": "bất động sản pháp lý dự án chu kỳ tín dụng",
        "bán lẻ": "bán lẻ tiêu dùng cửa hàng chuỗi doanh thu MWG PNJ",
        "năng lượng": "năng lượng điện dầu khí nhiệt điện thủy điện",
        "công nghiệp": "công nghiệp khu công nghiệp KCN logistics sản xuất",
    }
    for key, terms in mapping.items():
        if key in industry:
            return terms
    return ""

def main():
    import argparse
    
    p = argparse.ArgumentParser()
    p.add_argument("--ticker", help="Ticker symbol")
    p.add_argument("--industry", help="Industry name")
    p.add_argument("--query", default="", help="Search query")
    p.add_argument("--top", type=int, default=3)
    args = p.parse_args()
    
    if not os.path.exists(INDEX_FILE):
        print(json.dumps({"error": f"Index not found. Run knowledge_ingest.py first."}))
        sys.exit(1)
    
    with open(INDEX_FILE, "rb") as f:
        data = pickle.load(f)
    
    vectorizer = data["vectorizer"]
    tfidf_matrix = data["tfidf_matrix"]
    documents = data["documents"]
    metadatas = data["metadatas"]
    
    # Build query
    query_parts = [args.query]
    if args.ticker:
        ctx = get_industry_context(args.ticker)
        if ctx:
            query_parts.append(ctx)
    if args.industry:
        query_parts.append(args.industry)
    
    full_query = " ".join(q for q in query_parts if q).strip()
    if not full_query:
        full_query = "kinh tế vĩ mô thị trường chứng khoán Việt Nam"
    
    # Vectorize query and compute similarity
    query_vec = vectorizer.transform([full_query])
    sims = cosine_similarity(query_vec, tfidf_matrix)[0]
    
    # Get top-k unique sources
    top_indices = np.argsort(sims)[::-1]
    
    seen_sources = set()
    matches = []
    
    for idx in top_indices:
        if sims[idx] < 0.05:  # Relevance threshold
            break
        
        meta = metadatas[idx]
        source = meta["source"]
        
        if source in seen_sources:
            continue
        seen_sources.add(source)
        
        content = documents[idx]
        snippet = content[:700] if len(content) > 700 else content
        
        matches.append({
            "source": source,
            "relevance": round(float(sims[idx]), 3),
            "updated": meta.get("updated", "unknown"),
            "tags": meta.get("tags", ""),
            "content": snippet,
        })
        
        if len(matches) >= args.top:
            break
    
    print(json.dumps({
        "query": full_query,
        "ticker": args.ticker,
        "matches": matches,
        "index_size": data["num_chunks"],
        "built_at": data.get("built_at", "unknown"),
        "note": "Dùng nội dung này làm THAM KHẢO CÓ NGUỒN. CẤM bịa thêm số liệu."
    }, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
