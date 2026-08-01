# 🏦 VNStock AI Analyst

> Multi-agent AI pipeline phân tích cổ phiếu Việt Nam — mô phỏng quy trình của một quỹ đầu tư chuyên nghiệp.

## Triết lý

```
Không hỏi: "MACD cắt lên chưa?"
    Mà hỏi: "Đây có phải doanh nghiệp tốt ở mức giá hiện tại không?"
```

**Fundamental-first.** Technical chỉ để timing, không phải để quyết định.
Mọi con số do Python script tính — LLM chỉ diễn giải. Chống bịa dữ liệu từ gốc.

## Tính năng

| Chế độ | Trigger | Kết quả |
|--------|---------|---------|
| **Phân tích 1 mã** | `phân tích FPT` | Investment Thesis 8 bước |
| **So sánh nhiều mã** | `so sánh FPT với TCB` | Pipeline song song + bảng so sánh |
| **Stock Screener** | `nên mua mã nào` | Quét VN30 → xếp hạng → user chọn → deep dive |
| **Check danh mục** | `check danh mục` | P&L từng vị thế |
| **Review dài hạn** | `đánh giá lại FPT sau 30 ngày` | So sánh dự đoán vs thực tế |
| **Quick price** | `FPT giá bao nhiêu` | Fetch giá + volume (không phân tích) |

## Pipeline 8 bước (v3.2)

```
Step 0: DATA LOCK — khóa dữ liệu đầu vào (anti-hallucination)
├── dnse_fetch.py → OHLC, quotes, secDef
└── fundamentals_fetch.py → P/E, P/B, ROE, KQKD

Step 1: TECHNICAL COMPUTE — tính chỉ báo bằng Python
└── RSI, MACD, SMA, ATR, BB, support/resistance (LLM chỉ diễn giải)

Step 2: NEWS & SENTIMENT (song song)
├── News Agent: "Chuyện gì vừa xảy ra?"
└── Sentiment Agent: "Mọi người nghĩ gì?"

Step 3: FUNDAMENTAL + MACRO + VN-SPECIFIC (song song)
├── Fundamental Analyst: Doanh nghiệp tốt? Giá hợp lý?
├── Macro Analyst + TF-IDF RAG: tra cứu knowledge base
└── VN-Specific: NĐTNN, cổ tức, sector rotation

Step 4: BULL vs BEAR DEBATE (song song)

Step 5: JUDGE + RESEARCH MANAGER
├── Judge: phân xử Bull vs Bear dựa trên bằng chứng
└── Research Manager: RATING (có ràng buộc anti-hallucination)

Step 6: TECHNICAL + RISK + TRADER (song song)
├── Technical: timing (chỉ diễn giải số từ Step 1)
├── Risk: 6 loại rủi ro + hard-cap 20%/mã
└── Trader: kế hoạch giao dịch cụ thể

Step 7: REFLECTION — học từ lịch sử phân tích

Step 8: INVESTMENT THESIS + HẬU KIỂM
└── Tổng hợp → post-validation → lưu DB + journal
```

## Đầu ra mẫu

```
📊 LUẬN ĐIỂM ĐẦU TƯ — FPT | 31/07/2026 | Giá: 67.0

🏢 DOANH NGHIỆP
FPT — CTCP FPT | HOSE | VN30, VN100 | Công nghệ

💰 SỨC KHỎE TÀI CHÍNH (từ Data Lock)
P/E: 11.1x (ngành: 15-25) | P/B: 2.66x | ROE: 27.3%
Revenue 2025: 70,113 tỷ | Net Profit: 11,232 tỷ
Tăng trưởng LN YoY: +19.1% | QoQ: -2.9%

📈 KỸ THUẬT (từ Technical Compute)
RSI: 39.4 | MACD: -1.73 | SMA20: 67.6 | Support: 64.7

🎯 KHUYẾN NGHỊ
Rating: HOLD | Confidence: Trung bình (định tính)
Entry: 64.7-67.0 | Target: 71.8 | Stop: 64.7
Tỷ trọng: 15-20% | Timeframe: Trung hạn
```

## Data Sources

| Source | Dữ liệu | Rate Limit |
|--------|---------|------------|
| **vnstock 4.0** | P/E, P/B, ROE, KQKD, company info | 20 req/phút (free) |
| **DNSE API** | OHLC, quotes, bid/ask, NĐTNN | Không giới hạn |
| **TF-IDF RAG** | Kiến thức vĩ mô/ngành (local, no API) | — |
| **Google News RSS** | Tin tức, sự kiện | Thường bị chặn |

## Cài đặt

```bash
# 1. Python 3.10+ (brew Python 3.14)
brew install python@3.14

# 2. Tạo venv + cài dependencies
/opt/homebrew/bin/python3 -m venv .venv
.venv/bin/pip install vnstock pandas requests pytz python-dateutil scikit-learn

# 3. Cấu hình DNSE API key (xem references/dnse-api-auth.md)

# 4. Build knowledge index (RAG)
PYTHONPATH="" .venv/bin/python3 scripts/knowledge_ingest.py
```

## Cấu trúc thư mục

```
vnstock-ai/
├── README.md
├── SKILL.md                      ← Logic + prompt cho AI agent
├── AGENTS.md                     ← Entry point đa nền tảng
├── SETUP.md                      ← Hướng dẫn setup máy mới
├── scripts/
│   ├── data_lock.py              ← Khóa dữ liệu đầu vào + data_status
│   ├── dnse_fetch.py             ← OHLC, quotes từ DNSE
│   ├── fundamentals_fetch.py     ← P/E, P/B, ROE từ vnstock
│   ├── technical_compute.py      ← Tính chỉ báo kỹ thuật (LLM chỉ diễn giải)
│   ├── knowledge_ingest.py       ← Chunk + TF-IDF index knowledge base
│   ├── knowledge_query.py        ← Semantic search kiến thức vĩ mô/ngành
│   ├── screener.py               ← Quét & xếp hạng cổ phiếu
│   └── portfolio.py              ← SQLite positions + journal
├── knowledge/                    ← RAG knowledge base
│   ├── _index.md
│   ├── macro/
│   ├── sector-frameworks/
│   └── historical-cases/
├── references/
│   ├── dnse-api-auth.md
│   └── vnstock-v4-api.md
├── prompts/
│   ├── analyst.md                ← System prompt cho Fundamental-first
│   ├── guardian.md               ← Cron agent: Portfolio Guardian
│   ├── scout.md                  ← Cron agent: Market Scout
│   └── auditor.md                ← Cron agent: Performance Auditor
├── data/
│   ├── trading.db
│   ├── symbols_by_industries.csv
│   └── .lock_{TICKER}.json       ← Data lock files (auto-generated)
├── journal/
└── .venv/
```

## Ví dụ nhanh

```bash
# Fetch fundamental + market data
PYTHONPATH="" .venv/bin/python3 scripts/data_lock.py FPT

# Tính chỉ báo kỹ thuật
PYTHONPATH="" .venv/bin/python3 scripts/technical_compute.py --ticker FPT

# Tra cứu kiến thức ngành
PYTHONPATH="" .venv/bin/python3 scripts/knowledge_query.py --ticker TCB --query "lãi suất NIM"

# Screener VN30
PYTHONPATH="" .venv/bin/python3 scripts/screener.py VN30 --limit 10

# Check portfolio
python3 scripts/portfolio.py status
```

## ⚠️ Lưu ý

- **Anti-hallucination**: Mọi con số do script Python tính. Data Lock ngăn agent bịa số. Hậu kiểm sau Step 8.
- **PYTHONPATH**: Hermes set PYTHONPATH vào Python 3.11 → xung đột numpy. Luôn dùng `PYTHONPATH=""`.
- **vnstock rate limit**: 20 req/phút free tier. Max 4 kỳ báo cáo.
- **Hard-cap position**: Tối đa 20%/mã. Confidence là ước lượng định tính.
- **Rating constraints**: Thiếu dữ liệu tài chính → tối đa HOLD.
- Phân tích chỉ mang tính tham khảo, không phải lời khuyên tài chính.

## License

MIT — tự do sử dụng, phân phối, chỉnh sửa.
