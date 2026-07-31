---
name: dnse-stock-analysis
description: "Use when user asks to analyze/evaluate Vietnamese stocks. Fundamental-first 7-step pipeline: P/E, ROE, revenue → Investment Thesis. Portfolio tracking + journal."
version: 3.1.0
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

# DNSE Stock Analysis Pipeline v3.1 — Fund Manager Style

## 🚦 ĐÁNH GIÁ CÂU HỎI & RẼ NHÁNH (LÀM ĐẦU TIÊN)

Khi skill được load, **đánh giá intent của user trước**, sau đó rẽ nhánh:

```
User hỏi gì?
│
├── "phân tích FPT" / "đánh giá FPT" / "FPT có nên mua không"
│   └── Intent: PHÂN TÍCH 1 MÃ → Pipeline 7 bước (bên dưới)
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
│   ├── dnse_fetch.py          # Fetch OHLC, quotes, secDef, NĐTNN từ DNSE API
│   ├── fundamentals_fetch.py  # Fetch P/E, P/B, ROE, KQKD, company info từ vnstock
│   └── portfolio.py           # Quản lý SQLite portfolio + journal
├── references/
│   ├── dnse-api-auth.md
│   ├── dnse-auth-debug.md
│   ├── vnstock-v4-api.md
│   └── vnstock-v4-api-quickref.md
├── data/
│   ├── trading.db
│   └── symbols_by_industries.csv
├── journal/
│   └── YYYY-MM-DD_TICKER.md
└── .venv/                     # Python 3.14 + vnstock 4.0.5
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

## PIPELINE 7 BƯỚC

### Step 1: FETCH DATA (song song — 2 scripts)

```bash
# Script 1: Dữ liệu thị trường DNSE (OHLC, giá, bid/ask, NĐTNN, secDef)
PYTHONPATH="" .venv/bin/python3 scripts/dnse_fetch.py {TICKER}

# Script 2: Dữ liệu tài chính vnstock (P/E, P/B, ROE, ROA, KQKD, company info)
PYTHONPATH="" .venv/bin/python3 scripts/fundamentals_fetch.py {TICKER}
```

**Output từ `dnse_fetch.py`:** closePrice, ohlcHistory (65D), latestTrades, latestQuotes, foreignTrading, secDef, instruments.

**Output từ `fundamentals_fetch.py`:** company (tên, sàn, CEO, vốn điều lệ, business model), metrics (P/E, P/B, ROE, ROA, EPS, BVPS, Gross Margin, Net Margin, D/E, Interest Coverage, Dividend Yield...), income_yearly (Revenue, Net Profit 4 năm gần nhất), income_quarterly (QoQ growth).

> ⚠️ Nếu fundamentals_fetch.py lỗi → ghi chú "Không có dữ liệu tài chính (vnstock lỗi)", pipeline vẫn tiếp tục với dữ liệu DNSE.

### Step 2: NEWS + SENTIMENT (2 agents song song)

**News Agent** — "Chuyện gì vừa xảy ra với {TICKER}?"

Search Google News RSS: `news.google.com/rss/search?q={TICKER}+kết+quả+kinh+doanh+OR+cổ+tức+OR+hợp+đồng&hl=vi&gl=VN&ceid=VN:vi`

Output JSON:
```json
{
  "keyEvents": [{"event": "...", "date": "...", "impact": "+/-/neutral", "source": "..."}],
  "recentNews": [{"title": "...", "date": "...", "relevance": "high/medium/low"}],
  "pendingCatalysts": ["KQKD Q2", "ĐHCĐ", "chia cổ tức"...],
  "summary": "Tóm tắt 2-3 câu"
}
```

**Sentiment Agent** — "Mọi người nghĩ gì về {TICKER}?"

Dựa trên: News Agent output + price action + volume + kiến thức thị trường.

Output JSON:
```json
{
  "retailSentiment": {"score": -5 to 5, "label": "HOẢNG LOẠN / LẠC QUAN / TRUNG LẬP", "indicators": ["volume pattern", "price action"]},
  "institutionalSentiment": {"score": -5 to 5, "label": "MUA RÒNG / BÁN RÒNG / ĐỨNG NGOÀI", "indicators": ["NĐTNN", "ETF flow"]},
  "narrativeStrength": {"score": 1-10, "verdict": "MẠNH / SUY YẾU / BỊ THỬ THÁCH"},
  "divergenceFlag": {"present": true/false, "type": "bullish/bearish divergence", "note": "..."},
  "summary": "Tóm tắt 2-3 câu"
}
```

> ⚠️ News search thường bị chặn CAPTCHA. Dùng Google News RSS làm nguồn chính. Nếu không có kết quả → ghi "Không có sự kiện đáng kể trong 7 ngày" và suy luận sentiment từ price action + volume.

### Step 3: FUNDAMENTAL + MACRO + VN-SPECIFIC (3 agents song song)

Đây là BƯỚC QUAN TRỌNG NHẤT — quyết định CÓ MUA KHÔNG.

**3a. Fundamental Analyst (DOANH NGHIỆP CÓ TỐT KHÔNG?)**

```
Bạn là Fundamental Analyst. Phân tích {TICKER} dựa trên dữ liệu tài chính THỰC.

Dữ liệu từ vnstock:
- P/E: {PE} | P/B: {PB} | ROE: {ROE}% | ROA: {ROA}%
- EPS: {EPS} | BVPS: {BVPS}
- Gross Margin: {GM}% | Net Margin: {NM}%
- D/E: {DE}% | Interest Coverage: {IC}
- Revenue 4 năm: {REVENUE_YEARLY}
- Net Profit 4 năm: {PROFIT_YEARLY}
- QoQ growth: Revenue {REV_QOQ}%, Profit {PROFIT_QOQ}%

Đánh giá 5 nhóm:
1. TĂNG TRƯỞNG: Revenue/Profit growth YoY, QoQ
2. CHẤT LƯỢNG: ROE, ROA, Gross Margin, Net Margin — so với ngành
3. ĐỊNH GIÁ: P/E, P/B — đắt/rẻ so với lịch sử và ngành?
4. NỢ & DÒNG TIỀN: D/E, Interest Coverage — an toàn không?
5. ĐIỂM YẾU: rủi ro gì từ báo cáo tài chính?

QUAN TRỌNG: So sánh với TRUNG BÌNH NGÀNH. Ví dụ:
- Ngân hàng: P/B 1.0-2.0 là bình thường, ROE 15%+ là tốt
- Công nghệ: P/E 15-25, ROE 20%+, D/E <50%
- Dệt may: P/E 8-12, biên LN thấp (5-10%)

Trả JSON: {growthAnalysis, qualityAnalysis, valuationAnalysis, debtAnalysis, redFlags[], overallScore (1-10), comparisonWithIndustry, summary}
```

**3b. Macro Analyst (VĨ MÔ ẢNH HƯỞNG THẾ NÀO?)**

```
Bạn là Macro Analyst. Đánh giá yếu tố vĩ mô ảnh hưởng đến {TICKER}.

CHỈ phân tích nếu LIÊN QUAN TRỰC TIẾP. Dựa trên ngành của ticker:
- Ngân hàng: lãi suất NHNN, tăng trưởng tín dụng, nợ xấu toàn ngành, chính sách tiền tệ
- BĐS: lãi suất, pháp lý dự án, đầu tư công, tín dụng BĐS
- Công nghệ: chi tiêu CNTT toàn cầu, tỷ giá USD/VND, xu hướng AI
- Dệt may: đơn hàng xuất khẩu, tỷ giá, cầu tiêu dùng toàn cầu
- Thép: giá thép thế giới, đầu tư công, BĐS

Trả JSON: {macroFactors[], interestRate, exchangeRate, industryTrend, relevantPolicies[], summary}
```

**3c. VN-Specific Analyst (YẾU TỐ ĐẶC THÙ VIỆT NAM)**

```
Bạn là VN-Specific Analyst. Đánh giá yếu tố đặc thù thị trường Việt Nam cho {TICKER}.

Phân tích 5 yếu tố:
1. NĐTNN: Dữ liệu foreignTrading từ DNSE. Mua/bán ròng? Room ngoại còn bao nhiêu?
2. CỔ TỨC & CORPORATE ACTIONS: Dividend yield? Lịch sử chia cổ tức? ESOP? Phát hành thêm?
3. SECTOR ROTATION: Ngành này đang ở đâu trong chu kỳ? Dòng tiền đang vào hay ra?
4. KHỐI TỰ DOANH: Các CTCK đang mua hay bán? (suy luận từ volume pattern nếu không có data)
5. THANH KHOẢN: Volume TB, giá trị giao dịch, spread bid/ask

Trả JSON: {foreignFlow, corporateActions, sectorRotation, liquidityAnalysis, summary}
```

### Step 4: BULL / BEAR DEBATE (2 agents song song)

**Bull Researcher:** Tìm mọi lý do nên MUA, dùng evidence từ Step 3.
**Bear Researcher:** Tìm mọi lý do KHÔNG nên mua, dùng evidence từ Step 3.

Mỗi agent trả JSON: `{argument, evidence[], confidence, summary}`

> Bỏ Round 2 phản biện (v2 có) — không cần thiết, tốn thời gian, không cải thiện chất lượng.

### Step 5: RESEARCH MANAGER (trọng tài)

```
Bạn là Research Manager. Dựa trên toàn bộ phân tích (Fundamental + Macro + VN-Specific + Bull/Bear Debate), đưa RATING:

- BUY: doanh nghiệp TỐT + định giá HẤP DẪN + sentiment TÍCH CỰC
- OVERWEIGHT: doanh nghiệp tốt + định giá hợp lý + tăng tỷ trọng nếu đang nắm giữ
- HOLD: doanh nghiệp tốt nhưng định giá chưa đủ hấp dẫn HOẶC kỹ thuật xấu
- UNDERWEIGHT: doanh nghiệp khá nhưng rủi ro ngắn hạn cao → giảm tỷ trọng
- SELL: doanh nghiệp XẤU hoặc định giá QUÁ ĐẮT hoặc rủi ro QUÁ CAO

Trả JSON: {decision, rating, confidence (0-1), reasoning, bullSummary, bearSummary, keyFactors[{factor, assessment, detail}]}
```

### Step 6: TECHNICAL + RISK + TRADER (3 agents song song)

**Technical Analyst — CHỈ ĐỂ TIMING. KHÔNG QUYẾT ĐỊNH MUA/BÁN.**

```
Bạn là Technical Analyst. Phân tích kỹ thuật {TICKER} để tìm ĐIỂM VÀO TỐI ƯU.

LƯU Ý: Bạn KHÔNG quyết định mua hay bán. Fundamental đã quyết định điều đó.
Bạn chỉ tìm timing: khi nào vào? giá nào?

Phân tích: trend, SMA(20,50), RSI, MACD, volume, hỗ trợ/kháng cự, Bollinger Bands.

Trả JSON: {trend, supportLevels[], resistanceLevels[], indicators{rsi, macd, volume}, optimalEntry{zones[], confirmationSignals[]}, stopLossLevel, summary}
```

**Risk Analyst — Đánh giá MẤT GÌ NẾU SAI?**

```
Bạn là Risk Analyst. Đánh giá toàn diện rủi ro cho {TICKER}.

1. Market Risk: mất support → rủi ro giảm bao nhiêu %?
2. Technical Risk: volume, divergence, fake breakout?
3. Fundamental Risk: định giá có bị nén không? KQKD có rủi ro miss?
4. Macro Risk: tỷ giá, lãi suất, chính sách
5. Liquidity Risk: có thoát được hàng không?
6. Sentiment Risk: panic selling, narrative shift

Mỗi loại: severity (CAO/TRUNG BÌNH/THẤP), probability (%), impact (%), mitigation.
+ Position sizing: nên phân bổ bao nhiêu % danh mục?
+ Max drawdown dự kiến?

Trả JSON: {risks[{type, severity, probability, impact, mitigation}], overallRiskScore (1-10), suggestedPositionSize, maxDrawdownEstimate, summary}
```

**Trader — Kế hoạch giao dịch cụ thể**

```
Bạn là Trader. Dựa trên rating từ Research Manager + timing từ Technical + risk từ Risk Analyst.

Đưa kế hoạch giao dịch CỤ THỂ:
- action: buy/sell/hold/accumulate
- entryPoint: giá vào (hoặc vùng vào)
- entryStrategy: lump sum hay DCA? mấy lần?
- targetPrice: giá mục tiêu (1-3 mức)
- stopLoss: cắt lỗ cứng
- positionSize: % danh mục
- timeframe: ngắn hạn (<1 tháng) / trung hạn (1-6 tháng) / dài hạn (>6 tháng)
- exitStrategy: trailing stop? chốt từng phần?
- riskRewardRatio

Trả JSON: {action, ticker, entryPoint, entryStrategy, targetPrice[], stopLoss, positionSize, timeframe, exitStrategy, riskRewardRatio, confidence, reasoning}
```

### Step 7: PORTFOLIO MANAGER — Investment Thesis + LƯU KẾT LUẬN

Main agent tự tổng hợp TOÀN BỘ pipeline thành Investment Thesis. Format bắt buộc:

```
📊 **LUẬN ĐIỂM ĐẦU TƯ — {TICKER} | {DATE}**

🏢 **DOANH NGHIỆP**
- Tên: {NAME} | Sàn: {EXCHANGE} | Ngành: {INDUSTRY}
- Vốn hóa: ~{MARKET_CAP} tỷ | CEO: {CEO}

💰 **SỨC KHỎE TÀI CHÍNH**
- P/E: {PE} (ngành: {INDUSTRY_PE}) | P/B: {PB} (ngành: {INDUSTRY_PB})
- ROE: {ROE}% | ROA: {ROA}% | EPS: {EPS}
- Gross Margin: {GM}% | Net Margin: {NM}%
- D/E: {DE}% | Interest Coverage: {IC}x
- Revenue {LATEST_YEAR}: {REVENUE} tỷ | Net Profit: {PROFIT} tỷ
- Tăng trưởng lợi nhuận YoY: {PROFIT_GROWTH}% | QoQ: {PROFIT_QOQ}%

📰 **SỰ KIỆN & TÂM LÝ**
- Sự kiện: [tóm tắt từ News Agent]
- Sentiment: {SENTIMENT_LABEL} ({SENTIMENT_SCORE}/10)

⚖️ **LUẬN ĐIỂM**
- ✅ BULL: [2-3 ý chính từ Bull Researcher]
- ❌ BEAR: [2-3 ý chính từ Bear Researcher]

📈 **KỸ THUẬT** (timing)
- Giá: {CLOSE_PRICE} | Trend: {TREND}
- Hỗ trợ: {SUPPORTS} | Kháng cự: {RESISTANCES}
- Volume: {VOLUME_ANALYSIS}

🛡️ **RỦI RO**
- Overall Risk: {RISK_SCORE}/10
- Rủi ro lớn nhất: {TOP_RISKS}
- Max Drawdown dự kiến: {MAX_DD}%

🎯 **KHUYẾN NGHỊ**
- Rating: {RATING} | Confidence: {CONFIDENCE}%
- Hành động: {ACTION}
- Vào: {ENTRY} | Mục tiêu: {TARGET} | Cắt lỗ: {STOP_LOSS}
- Tỷ trọng: {POSITION_SIZE}% danh mục
- Timeframe: {TIMEFRAME}
- Risk/Reward: {R_R}

📝 **LUẬN ĐIỂM ĐẦU TƯ**
[3-4 câu — tại sao nên/không nên đầu tư vào {TICKER} ở mức giá này?]

⚠️ **LƯU Ý**
- Đây là phân tích tham khảo, KHÔNG phải lời khuyên tài chính
- Luôn có kế hoạch cắt lỗ. Không dùng đòn bẩy nếu chưa có kinh nghiệm.
```

**SAU KHI hiển thị, LƯU NGAY vào database:**

```bash
PYTHONPATH="" .venv/bin/python3 scripts/portfolio.py log_analysis \
    --ticker {TICKER} --date {DATE} --close-price {CLOSE_PRICE} \
    --rating "{RATING}" --action {ACTION} --target-price {TARGET} \
    --stop-loss {STOP_LOSS} --confidence {CONFIDENCE} \
    --bull-case "{BULL_SUMMARY}" --bear-case "{BEAR_SUMMARY}" \
    --key-news '{KEY_NEWS_JSON}' --recommendation "{THESIS_SHORT}"
```

Đồng thời lưu markdown vào `journal/{DATE}_{TICKER}.md`.

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

## PORTFOLIO TRACKING

```bash
PYTHONPATH="" .venv/bin/python3 scripts/portfolio.py add_position --ticker HPG --buy-date 2026-07-30 --buy-price 24.8 --quantity 1000
PYTHONPATH="" .venv/bin/python3 scripts/portfolio.py close_position --ticker HPG --sell-date 2026-08-15 --sell-price 26.5
PYTHONPATH="" .venv/bin/python3 scripts/portfolio.py status
```

## LONG-TERM EVALUATION

```bash
PYTHONPATH="" .venv/bin/python3 scripts/portfolio.py review --ticker HPG --days 30
```

## DAILY CRON JOB (Portfolio Check)

Chạy 15:30 mỗi ngày T2-T6: fetch giá đóng cửa → tính P&L → báo cáo từng vị thế.

---

## Pitfalls

- **fundamentals_fetch.py**: PHẢI chạy với `PYTHONPATH=""` và skill's `.venv/bin/python3`. Không dùng system Python (thiếu vnstock) hoặc vnstock-ai/.venv (sai path check). Script đã clear PYTHONPATH tự động từ bên trong.
- **vnstock ad banner**: Script in ra quảng cáo vnstock insiders program ra stdout. Đây là output của vnstock library, không phải lỗi. Parser JSON cần bỏ qua dòng text trước dấu `{` đầu tiên.
- **vnstock free tier limits**: 20 req/phút, tối đa 4 kỳ báo cáo tài chính. Không thể xem data quá 4 quý gần nhất nếu dùng free. Nếu cần thêm → nâng cấp insiders program.
- **DNSE API signing**: Query string MUST be stripped from signing path. Use `path.split("?")[0]`.
- **DNSE foreignTrading**: Thường trả HTTP 400 "range exceeds maximum time range". Nếu rỗng → ghi chú "Không có dữ liệu NĐTNN".
- **News search bị CAPTCHA**: Google/Bing/DuckDuckGo qua browser đều bị chặn. Dùng Google News RSS (`news.google.com/rss/search`). Nếu vẫn không có kết quả → ghi "Không có sự kiện đáng kể trong 7 ngày".
- **max_concurrent_children=3**: Mỗi batch delegate tối đa 3 tasks. Phân bổ: Step 2 (2 agents), Step 3 (3 agents), Step 4 (2 agents), Step 6 (3 agents).
- **Banking stocks**: Báo cáo tài chính ngân hàng khác với doanh nghiệp thường. vnstock trả về ít metrics hơn (không có Revenue, Gross Margin). Fundamental analyst cần adapt — dùng P/B, ROE, NIM, CASA thay vì P/E, Margin.
- **Bỏ Round 2 Bull/Bear Debate (v2 có)**: Không cần thiết, tốn thêm 2-3 lần delegate, chất lượng không cải thiện đáng kể.

## Verification Checklist

- [x] `fundamentals_fetch.py FPT` → P/E=15.53, ROE=27.33%, Revenue=70,113 tỷ
- [x] `fundamentals_fetch.py TCB` → P/E=12.16, ROE=14.22%, Profit=25,954 tỷ
- [x] `fundamentals_fetch.py VIB` → P/E=7.97, ROE=17.34%, Profit=7,285 tỷ
- [x] `dnse_fetch.py FPT` → closePrice=67.1, 65 days OHLC
- [x] `portfolio.py status` → hiển thị danh mục
- [x] `portfolio.py log_analysis` → lưu analysis_log + journal
- [ ] Pipeline đầy đủ cho 1 mã → Investment Thesis format mới (cần test thực tế)
- [ ] Pipeline so sánh 2+ mã → bảng so sánh (cần test thực tế)
