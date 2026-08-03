---
name: dnse-stock-analysis
description: "Use when user asks to analyze/evaluate Vietnamese stocks. Fundamental-first 8-step pipeline: P/E, ROE, revenue → Investment Thesis. Portfolio tracking + journal."
version: 3.2.0
author: Hermes + Cuong
platforms: [macos, linux]
metadata:
  hermes:
    triggers:
      - "phân tích"
      - "đánh giá"
      - "chứng khoán"
      - "cổ phiếu"
      - "mã"
      - "nên mua"
      - "danh mục"
      - "portfolio"
      - "analyze"
      - "evaluate"
      - "stock"
      - "ticker"
      - "so sánh"
    tags: [finance, stock, vietnam, dnse, multi-agent, portfolio, journal, fundamental-first]
---

# DNSE Stock Analysis Pipeline v3.2 — Fund Manager Style

## 🚦 ĐÁNH GIÁ CÂU HỎI & RẼ NHÁNH (LÀM ĐẦU TIÊN)

Khi skill được load, **đánh giá intent của user trước**, sau đó rẽ nhánh:

```
User hỏi gì?
│
├── "phân tích FPT" / "đánh giá FPT" / "FPT có nên mua không"
│   └── Intent: PHÂN TÍCH 1 MÃ → Pipeline 8 bước (bên dưới)
│
├── "so sánh FPT với TCB" / "FPT hay TCB" / "nên mua mã nào"
│   └── Intent: SO SÁNH → Fetch data từng mã → so sánh bảng
│
├── "check danh mục" / "xem portfolio" / "danh mục của tôi"
│   └── Intent: CHECK PORTFOLIO → portfolio.py status
│
├── "đã mua 1000 FPT giá 65" / "mua thêm FPT"
│   └── Intent: THÊM VỊ THẾ → portfolio.py add_position
│
├── "đã bán FPT" / "bán hết FPT" / "chốt lời FPT"
│   └── Intent: ĐÓNG VỊ THẾ → portfolio.py close_position
│
├── "FPT giá bao nhiêu" / "FPT hôm nay thế nào"
│   └── Intent: GIÁ NHANH → dnse_fetch.py (không phân tích)
│
├── "room ngoại FPT" / "NĐTNN FPT mua bán"
│   └── Intent: DATA POINT → dnse_fetch.py → trả foreignTrading
│
├── "đánh giá lại FPT sau 30 ngày"
│   └── Intent: REVIEW → portfolio.py review
│
└── Không rõ intent
    └── Hỏi lại user: "Bạn muốn phân tích mã nào? Hay check danh mục?"

## Triết lý

```
1. Hiểu doanh nghiệp (Fundamental — CÓ MUA KHÔNG?)
        ↓
2. Hiểu thị trường (News + Sentiment — chuyện gì đang xảy ra?)
        ↓
3. Hiểu dòng tiền (Macro + NĐTNN — ai đang mua/bán?)
        ↓
4. Đánh giá rủi ro (Risk — mất gì nếu sai?)
        ↓
5. Chọn thời điểm (Technical — MUA LÚC NÀO?)
        ↓
6. Quyết định (Investment Thesis có lý do)
```

**Nguyên tắc cốt lõi:**
1. **Fundamental-first**: Báo cáo tài chính quyết định CÓ MUA KHÔNG. Kỹ thuật chỉ quyết định MUA LÚC NÀO.
2. **Investment Thesis, không phải tín hiệu**: Đầu ra là luận điểm đầu tư có lý do, không phải "Buy/Sell" đơn thuần.
3. **Dữ liệu thực, không suy đoán**: P/E, ROE, KQKD từ vnstock API. Giá/volume từ DNSE API. Không bịa số.
4. **Lưu kết luận mỗi lần phân tích** — để đối chiếu dài hạn, tránh hindsight bias.
5. **Portfolio tracking** — theo dõi P&L thực tế sau khi user mua/bán.

## Kiến trúc thư mục

```
~/.hermes/skills/finance/dnse-stock-analysis/
├── SKILL.md
├── scripts/
│   ├── data_lock.py              # Step 0: Khóa dữ liệu đầu vào + data_status
│   ├── dnse_fetch.py             # Fetch OHLC, quotes, secDef, NĐTNN từ DNSE API
│   ├── fundamentals_fetch.py     # Fetch P/E, P/B, ROE, KQKD từ vnstock
│   ├── fscore.py                 # Step 3a: Piotroski F-Score (0-9) — sức khỏe tài chính
│   ├── technical_compute.py      # Step 1: Tính chỉ báo kỹ thuật (dùng ta library)
│   ├── knowledge_ingest.py       # Chunk + TF-IDF index knowledge base
│   ├── knowledge_query.py        # Semantic search vĩ mô/ngành (TF-IDF)
│   ├── screener.py               # Screening danh sách mã
│   └── portfolio.py              # SQLite portfolio + journal + performance_report
├── knowledge/                    # RAG knowledge base (TF-IDF, index trong .index/)
│   ├── _index.md                 # Mục lục + từ khóa → router
│   ├── macro/                    # Kiến thức vĩ mô VN
│   ├── sector-frameworks/        # Khung phân tích theo ngành
│   └── historical-cases/         # Case study lịch sử thị trường
├── references/
│   ├── dnse-api-auth.md
│   ├── dnse-auth-debug.md
│   ├── vnstock-v4-api.md
│   └── vnstock-v4-api-quickref.md
├── data/
│   ├── trading.db
│   ├── symbols_by_industries.csv
│   └── .lock_{TICKER}.json       # Data lock files (auto-generated)
├── journal/
│   └── YYYY-MM-DD_TICKER.md
└── .venv/                        # Python 3.14 + vnstock 4.0.5
```

## Database Schema

```sql
-- Vị thế đang mở
CREATE TABLE IF NOT EXISTS positions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ticker TEXT NOT NULL, buy_date TEXT NOT NULL, buy_price REAL NOT NULL,
    quantity INTEGER NOT NULL, status TEXT NOT NULL DEFAULT 'open',
    sell_date TEXT, sell_price REAL, realized_pnl REAL, notes TEXT,
    created_at TEXT DEFAULT (datetime('now', 'localtime'))
);

-- Nhật ký phân tích
CREATE TABLE IF NOT EXISTS analysis_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ticker TEXT NOT NULL, date TEXT NOT NULL, close_price REAL,
    rating TEXT, action TEXT, target_price REAL, stop_loss REAL,
    confidence REAL, bull_case TEXT, bear_case TEXT, key_news TEXT,
    final_recommendation TEXT,
    created_at TEXT DEFAULT (datetime('now', 'localtime'))
);

-- Đối chiếu dự đoán vs thực tế
CREATE TABLE IF NOT EXISTS outcome_review (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    analysis_id INTEGER REFERENCES analysis_log(id),
    review_date TEXT NOT NULL, actual_price REAL, price_change_pct REAL,
    was_correct TEXT, notes TEXT,
    created_at TEXT DEFAULT (datetime('now', 'localtime'))
);
```

---

## PIPELINE 8 BƯỚC (v3.2)

### ⛓️ NGUYÊN TẮC CHỐNG BỊA DỮ LIỆU (áp dụng toàn pipeline)

1. **Data Lock**: Sau Step 1, mọi dữ liệu đầu vào bị KHÓA CỨNG trong file `.lock_{TICKER}.json`.
2. **Cấm tuyệt đối** điền số vào field có `"data_status": "missing"` hoặc `"error"` — chỉ được viết "không có dữ liệu".
3. **Mọi con số hiển thị** (P/E, ROE, RSI, target price...) PHẢI do script Python tính — LLM chỉ diễn giải ý nghĩa.
4. **Hậu kiểm (post-validation)**: Sau Step 8, quét Investment Thesis, đối chiếu từng con số với Data Lock — số nào không khớp/không có nguồn → gắn cảnh báo.

### Step 0: DATA LOCK — khóa dữ liệu đầu vào

```bash
PYTHONPATH="" .venv/bin/python3 scripts/data_lock.py {TICKER}
```

Script chạy `dnse_fetch.py` + `fundamentals_fetch.py`, gộp vào 1 JSON với `data_status` cho từng nhóm chỉ số.

**Output:** `data/.lock_{TICKER}.json` chứa:
- `price` (close, open, high, low, ceiling, floor) + data_status
- `ohlc_history` (65 ngày) + data_status
- `orderbook` (bids, offers, volume) + data_status
- `foreign_trading` + data_status
- `secdef` (basic_price, ceiling, floor, exchange, indexes)
- `fundamentals` (metrics, income_yearly, income_quarterly, company) + data_status
- `meta.overall_data_quality`: "full" | "partial" | "none"

> ⚠️ Nếu `overall_data_quality = "none"` → pipeline không tiếp tục. Báo user: "Không có đủ dữ liệu để phân tích {TICKER}."

### Step 1: TECHNICAL COMPUTE — tính toán chỉ báo bằng code

```bash
PYTHONPATH="" .venv/bin/python3 scripts/technical_compute.py --ticker {TICKER}
```

Script đọc OHLC từ Data Lock, tính TOÀN BỘ chỉ báo kỹ thuật bằng Python:

**Output JSON:** `trend` (SMA20, SMA50, EMA20, price vs 20D high/low), `momentum` (RSI14, MACD, ADX), `volatility` (ATR14, Bollinger Bands), `support_resistance` (swing points), `volume` (avg20d, avg5d, up/down ratio), `change` (1D, 5D, 20D, from peak/trough).

> LLM Technical Analyst CHỈ được diễn giải các con số này — KHÔNG được tự tính, tự làm tròn, hoặc bịa chỉ báo.

### Step 2: NEWS + SENTIMENT (2 agents song song)

**News Agent** — "Chuyện gì vừa xảy ra với {TICKER}?"

Search Google News RSS. Output JSON: `{keyEvents[], recentNews[], pendingCatalysts[], summary}`

**Sentiment Agent** — "Mọi người nghĩ gì về {TICKER}?"

Output JSON: `{retailSentiment, institutionalSentiment, narrativeStrength, divergenceFlag, summary}`

> ⚠️ Bắt buộc tách 2 loại output: `sentiment_from_news` (có tin thật) và `sentiment_inferred_from_price` (suy luận khi không có tin). Trong Investment Thesis, phần suy luận phải gắn nhãn: "⚠️ Suy luận từ price action (không có tin xác nhận)".

### Step 3: FUNDAMENTAL + MACRO + VN-SPECIFIC (3 agents song song)

**3a. Fundamental Analyst** — input: Data Lock fundamentals section + F-Score. Trả JSON: `{growthAnalysis, qualityAnalysis, valuationAnalysis, redFlags[], overallScore, summary}`

Trước khi chạy Fundamental Analyst, tính Piotroski F-Score:
```bash
PYTHONPATH="" .venv/bin/python3 scripts/fscore.py {TICKER}
```

F-Score (0-9) đo sức khỏe tài chính doanh nghiệp qua 3 nhóm: Profitability, Leverage/Liquidity, Operating Efficiency. Điểm 7+ = chất lượng cao. NGÂN HÀNG được miễn (dùng P/B, ROE thay thế).

**3b. Macro Analyst với RAG** — trước khi chạy prompt, fetch kiến thức từ knowledge base:

```bash
PYTHONPATH="" .venv/bin/python3 scripts/knowledge_query.py --ticker {TICKER} --query "lãi suất tín dụng ngành"
```

Output trả về đoạn trích + nguồn → inject vào prompt:

```
THAM KHẢO (có nguồn, không phải tự nhớ):
[Nguồn: sector-frameworks/banking.md] "..."
```

**Luật RAG:** Chỉ diễn giải từ đoạn trích. Nếu không có đoạn nào → ghi "Không có tài liệu tham khảo phù hợp trong knowledge base". Mọi câu dùng RAG phải trace về file nguồn.

**3c. VN-Specific Analyst** — input: Data Lock foreign_trading + orderbook + secdef. Trả JSON: `{foreignFlow, corporateActions, sectorRotation, liquidityAnalysis, summary}`

### Step 4: BULL / BEAR DEBATE (2 agents song song)

Mỗi agent trả JSON: `{argument, evidence[], confidence, summary}`

### Step 5: JUDGE + RESEARCH MANAGER (2 bước tách biệt)

**5a. Judge** — chỉ phân xử Bull vs Bear: bên nào có luận điểm mạnh hơn dựa TRÊN BẰNG CHỨNG TỪ DATA LOCK. Trả JSON: `{winner, reasoning, bull_strengths[], bear_strengths[]}`

**5b. Research Manager** — input: Judge verdict + toàn bộ data. Ra RATING (BUY/OVERWEIGHT/HOLD/UNDERWEIGHT/SELL) với ràng buộc:

- Nếu `fundamentals.data_status = "missing"` → rating tối đa HOLD
- Nếu Fundamental tốt nhưng Technical xấu → rating tối đa HOLD
- Confidence dùng rubric 3 mức: Thấp / Trung bình / Cao (theo tiêu chí: độ đầy đủ dữ liệu, có tin xác nhận, độ đồng thuận Bull/Bear)
- Ghi rõ trong output: "Confidence là ước lượng định tính, không phải xác suất thống kê từ backtest."

### Step 6: TECHNICAL + RISK + TRADER (3 agents song song)

**Technical Analyst** — input: Technical Compute JSON. CHỈ diễn giải, không tính toán.

**Risk Analyst** — đánh giá 6 loại rủi ro. Hard-cap position size: **tối đa 20%/mã** (code-level, không phụ thuộc agent).

Trước khi đề xuất, PHẢI đọc portfolio từ SQLite ngay tại thời điểm đó:
```bash
PYTHONPATH="" .venv/bin/python3 scripts/portfolio.py status
```

**Trader** — kế hoạch giao dịch: `{action, entryPoint, entryStrategy, targetPrice[], stopLoss, positionSize, timeframe, exitStrategy, riskRewardRatio}`

**Cross-check TA:** Đối chiếu kết luận trend của Technical Analyst với dữ liệu giá 5 phiên gần nhất từ Data Lock. Nếu mâu thuẫn → gắn cờ cảnh báo.

### Step 7: REFLECTION — học từ lịch sử (trước khi ra kết luận)

Tự động đọc các lần phân tích trước của {TICKER} từ SQLite:
```bash
PYTHONPATH="" .venv/bin/python3 scripts/portfolio.py review --ticker {TICKER} --days 90
```

Nếu có phân tích cũ → sinh đoạn "bài học":
```
BÀI HỌC TỪ LỊCH SỬ:
- {DATE}: Rating BUY @{PRICE}, target {TARGET}. Sau 30 ngày: {ACTUAL} → {ĐÚNG/SAI}
- ...
```

Inject vào prompt Portfolio Manager.

### Step 8: PORTFOLIO MANAGER — Investment Thesis + Hậu kiểm + LƯU

Main agent tổng hợp TOÀN BỘ pipeline thành Investment Thesis (format dưới đây).

**Hậu kiểm (post-validation) bắt buộc trước khi hiển thị:**
- Quét từng con số trong Investment Thesis
- Đối chiếu với Data Lock JSON
- Số nào không khớp → gắn `⚠️ CẢNH BÁO: số liệu "{VALUE}" không có trong Data Lock. Cần kiểm tra lại.`
- Số nào có data_status=missing → gạch ngang, ghi "không có dữ liệu"

Sau khi hậu kiểm pass → hiển thị Investment Thesis → lưu DB + journal.

---

## PHÂN TÍCH NHIỀU MÃ (so sánh)

Khi user hỏi 2+ mã cùng lúc, thêm bước SO SÁNH sau khi phân tích từng mã:

| Tiêu chí | MÃ 1 | MÃ 2 | MÃ 3 |
|----------|------|------|------|
| Giá | | | |
| P/E | | | |
| P/B | | | |
| ROE | | | |
| Rating | | | |
| Confidence | | | |
| R/R | | | |
| Risk Score | | | |
| **Xếp hạng** | | | |

+ Kết luận: "Nếu chọn 1 mã → {TOP_PICK}. Lý do: ..."

---

## PORTFOLIO TRACKING

```bash
# Thêm vị thế
PYTHONPATH="" .venv/bin/python3 scripts/portfolio.py add_position \
    --ticker HPG --buy-date 2026-07-30 --buy-price 24.8 --quantity 1000

# Đóng vị thế
PYTHONPATH="" .venv/bin/python3 scripts/portfolio.py close_position \
    --ticker HPG --sell-date 2026-08-15 --sell-price 26.5

# Check danh mục
PYTHONPATH="" .venv/bin/python3 scripts/portfolio.py status
```

---

## LONG-TERM EVALUATION

```bash
# Review sau 7/30/90 ngày
PYTHONPATH="" .venv/bin/python3 scripts/portfolio.py review --ticker HPG --days 30
```

---

## CÁCH DÙNG

→ Xem **🚦 ĐÁNH GIÁ CÂU HỎI & RẼ NHÁNH** ở đầu file. Agent tự đánh giá intent rồi rẽ nhánh.

### Industry Benchmarks (dùng trong Fundamental Analyst)

| Ngành | P/E hợp lý | P/B hợp lý | ROE tốt | Margin tốt | D/E an toàn |
|-------|-----------|-----------|---------|-----------|-------------|
| Ngân hàng | 8-12 | 1.0-2.0 | >15% | NIM >3% | N/A (đặc thù) |
| Công nghệ | 15-25 | 3-6 | >20% | GM >30% | <50% |
| Dệt may | 8-12 | 1-1.5 | >12% | GM >15% | <80% |
| BĐS | 10-18 | 1-2 | >10% | GM >30% | <100% |
| Thép | 6-12 | 0.8-1.5 | >10% | GM >12% | <60% |
| Bán lẻ | 12-18 | 2-5 | >15% | GM >20% | <80% |
| Điện/Nước | 12-18 | 1.5-3 | >10% | GM >25% | <100% |

## DAILY CRON JOB (Portfolio Check)

Chạy 15:30 mỗi ngày T2-T6: fetch giá đóng cửa → tính P&L → báo cáo từng vị thế.

---

## Pitfalls

- **Subagent không được ghi file**: Subagents (delegate_task) chạy với cwd = `~/` (home directory) — nếu chúng ghi file sẽ làm rác home. LUẬT: mọi subagent CHỈ trả JSON qua final summary, TUYỆT ĐỐI không ghi file ra đĩa. Việc lưu DB/journal do main agent đảm nhiệm sau Step 8.
- **data_lock.py**: Chạy TRƯỚC mọi thứ khác. Nếu `overall_data_quality = "none"` → DỪNG pipeline, báo user.
- **technical_compute.py**: Dùng `ta` library (130+ indicators, pure Python). LLM CHỈ diễn giải — CẤM tự tính. Cross-check: so sánh trend kỹ thuật với giá 5D thực tế, flag divergence.
- **fscore.py**: Piotroski F-Score (0-9) đo sức khỏe tài chính. NGÂN HÀNG được miễn (dùng P/B, ROE thay thế).
- **knowledge_query.py (TF-IDF RAG)**: Dùng sklearn TfidfVectorizer + cosine similarity. Cần chạy `knowledge_ingest.py` trước để build index. Nếu không có match → báo "Không có tài liệu tham khảo phù hợp". CẤM agent tự bịa kiến thức vĩ mô.
- **Anti-hallucination**: Mọi số trong Investment Thesis phải trace được về Data Lock hoặc Technical Compute. Hậu kiểm sau Step 8: số nào không khớp → gắn cảnh báo.
- **Rating constraints**: Nếu `fundamentals.data_status = "missing"` → rating tối đa HOLD. Nếu Fundamental tốt nhưng Technical xấu → tối đa HOLD.
- **Hard-cap position size**: Tối đa 20%/mã. Không agent nào được đề xuất vượt quá.
- **Confidence rubric**: Chỉ dùng 3 mức Thấp/Trung bình/Cao. Ghi rõ: "ước lượng định tính, không phải xác suất thống kê".
- **vnstock ad banner**: Script in ra quảng cáo vnstock insiders program ra stdout. Đây là output của vnstock library, không phải lỗi. Parser JSON cần bỏ qua dòng text trước dấu `{` đầu tiên.
- **vnstock free tier limits**: 20 req/phút, tối đa 4 kỳ báo cáo tài chính. Không thể xem data quá 4 quý gần nhất nếu dùng free. Nếu cần thêm → nâng cấp insiders program.
- **DNSE API signing**: Query string MUST be stripped from signing path. Use `path.split("?")[0]`.
- **DNSE foreignTrading**: Thường trả HTTP 400 "range exceeds maximum time range". Nếu rỗng → ghi chú "Không có dữ liệu NĐTNN".
- **News search bị CAPTCHA**: Google/Bing/DuckDuckGo qua browser đều bị chặn. Dùng Google News RSS (`news.google.com/rss/search`). Nếu vẫn không có kết quả → ghi "Không có sự kiện đáng kể trong 7 ngày".
- **max_concurrent_children=3**: Mỗi batch delegate tối đa 3 tasks. Phân bổ: Step 2 (2 agents), Step 3 (3 agents), Step 4 (2 agents), Step 6 (3 agents).
- **Banking stocks**: Báo cáo tài chính ngân hàng khác với doanh nghiệp thường. vnstock trả về ít metrics hơn (không có Revenue, Gross Margin). Fundamental analyst cần adapt — dùng P/B, ROE, NIM, CASA thay vì P/E, Margin.
- **Bỏ Round 2 Bull/Bear Debate (v2 có)**: Không cần thiết, tốn thêm 2-3 lần delegate, chất lượng không cải thiện đáng kể.

## Verification Checklist

- [x] `data_lock.py FPT` → overall_data_quality=full, lock file created
- [x] `technical_compute.py --ticker FPT` → RSI=39.4, MACD=-1.73, SMA20=67.6
- [x] `knowledge_ingest.py` → 2 files, 8 chunks, TF-IDF index built
- [x] `knowledge_query.py --ticker TCB` → banking.md (relevance=0.34)
- [x] `dnse_fetch.py FPT` → closePrice=67.1, 65 days OHLC
- [x] `fscore.py FPT` → 8/9, "CAO — doanh nghiệp chất lượng tốt"
- [x] `fscore.py TCB` → None (ngân hàng, miễn F-Score)
- [x] `technical_compute.py` → dùng `ta` library, cross-check divergence
- [x] `portfolio.py performance_report` → win rate by ticker/rating
- [x] `portfolio.py status` → hiển thị danh mục
- [x] `portfolio.py log_analysis` → lưu analysis_log + journal
- [ ] Pipeline đầy đủ 1 mã → Investment Thesis (cần test thực tế)
- [ ] Pipeline so sánh 2+ mã → bảng so sánh (cần test thực tế)
