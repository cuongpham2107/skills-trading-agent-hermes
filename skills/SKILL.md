---
name: dnse-stock-analysis
description: "Use when phân tích/đánh giá/screening cổ phiếu Việt Nam. Fundamental-first multi-agent pipeline mô phỏng quỹ đầu tư: báo cáo tài chính → news/sentiment → technical (timing) → risk → investment thesis + portfolio tracking."
version: 3.1.0
author: Hermes + Cuong
platforms: [macos, linux]
metadata:
  hermes:
    triggers:
      - "phân tích mã {ticker}"
      - "phân tích cổ phiếu {ticker}"
      - "đánh giá {ticker}"
      - "nên mua {ticker} không"
      - "phân tích kỹ thuật {ticker}"
      - "nên đầu tư mã nào"
      - "top pick"
      - "cổ phiếu nào đáng mua"
      - "screening"
    tags: [finance, stock, vietnam, fundamental, multi-agent, portfolio, journal, screener]
---

# VNStock AI Analyst

## Overview

Multi-agent AI pipeline phân tích cổ phiếu Việt Nam, mô phỏng quy trình của một quỹ đầu tư chuyên nghiệp. Dùng vnstock 4.0 cho dữ liệu cơ bản (P/E, P/B, ROE, KQKD) và DNSE API cho dữ liệu thị trường (OHLC, quotes, NĐTNN).

Triết lý: **Fundamental quyết định CÓ MUA KHÔNG. Technical chỉ quyết định MUA LÚC NÀO.** Đầu ra là investment thesis có lý do, không phải tín hiệu Buy/Sell.

## When to Use

**Phân tích mã cụ thể:**
- `phân tích FPT` / `đánh giá VIB` → Pipeline 7 bước → Investment Thesis
- `phân tích FPT, TCB, VIB` → Song song pipeline + bảng so sánh

**Tìm kiếm cơ hội (không chỉ định mã):**
- `nên đầu tư mã nào` / `top pick hiện tại` → Screener VN30 → Xếp hạng → User chọn → Deep dive
- `mã nào tốt nhất ngành ngân hàng` → Screener theo ngành

**Quản lý danh mục:**
- `check danh mục` → P&L từng vị thế
- `đã mua 1000 HPG giá 24.8` → Lưu vị thế
- `đánh giá lại HPG sau 30 ngày` → So sánh dự đoán vs thực tế

**Không dùng cho:** phân tích coin/crypto, chứng khoán quốc tế, forex.

## Data Sources

| Source | Dữ liệu | Script/Tool |
|--------|---------|------------|
| **vnstock 4.0** | Fundamental (P/E, P/B, ROE, EPS, KQKD...), Macro (VN-Index, tỷ giá), Sector | `scripts/fundamentals_fetch.py` |
| **DNSE API** | OHLC, quotes, bid/ask, NĐTNN real-time | `scripts/dnse_fetch.py` |
| **Google News RSS** | News (sự kiện) | web_search / curl |
| **SQLite** | Portfolio, analysis log, outcome review | `scripts/portfolio.py` |

## Directory Structure

```
~/.hermes/skills/finance/dnse-stock-analysis/
├── SKILL.md
├── README.md
├── scripts/
│   ├── dnse_fetch.py            # OHLC/quotes/foreign via DNSE API
│   ├── fundamentals_fetch.py    # Financial data via vnstock 4.0
│   ├── screener.py              # Stock screening & ranking
│   └── portfolio.py             # SQLite: positions, analysis_log, outcome_review
├── references/
│   ├── dnse-api-auth.md
│   └── vnstock-v4-api.md
├── data/
│   ├── trading.db
│   └── symbols_by_industries.csv
├── journal/
│   └── YYYY-MM-DD_TICKER.md
└── .venv/                       # Brew Python 3.14 + vnstock 4.0.5
```

---

## Pipeline: Phân Tích 1 Mã (7 bước)

### Step 1: FETCH ALL DATA (song song)

```bash
# 1a. Fundamental data từ vnstock 4.0
PYTHONPATH="" .venv/bin/python3 scripts/fundamentals_fetch.py {TICKER}

# 1b. Market data từ DNSE
python3 scripts/dnse_fetch.py {TICKER}
```

`fundamentals_fetch.py` trả về JSON với: metrics (EPS, P/E, P/B, ROE...), income (KQKD 2 quý), company info, events.

### Step 2: NEWS & SENTIMENT (2 agent song song)

**News Agent** — "Chuyện gì vừa xảy ra?": Google News RSS → lọc sự kiện (KQKD, cổ tức, M&A, nhân sự...)
**Sentiment Agent** — "Mọi người nghĩ gì?": CTCK khuyến nghị, retail vs institutional, narrative strength.

**FALLBACK:** News search thường bị chặn CAPTCHA. Nếu không có kết quả → ghi chú và tiếp tục pipeline với dữ liệu fundamental + kỹ thuật.

### Step 3: 3 ANALYSTS (1 batch song song qua delegate_task)

| Analyst | Nhiệm vụ | Output |
|---------|---------|--------|
| **Fundamental** | Doanh nghiệp tốt? Giá hợp lý? | Score 1-10, P/E analysis, ROE, risks |
| **Macro & VN-Specific** | Vĩ mô, ngành, NĐTNN, cổ tức | Macro score, industry outlook, foreign flow |
| **Technical** | TÌM ĐIỂM VÀO (timing only) | Trend, support/resistance, ideal entry, RSI |

### Step 4: BULL/BEAR DEBATE (2 agent song song)

Bull Researcher vs Bear Researcher — mỗi bên đưa luận điểm mạnh nhất dựa trên 3 analyst reports. Bỏ Round 2 phản biện.

### Step 5: RESEARCH MANAGER + TRADER + RISK (1 batch gộp)

- **Research Manager**: Trọng tài → RATING (Buy/Overweight/Hold/Underweight/Sell)
- **Trader**: Kế hoạch giao dịch cụ thể (entry, stop, targets, position size)
- **Risk Analyst**: 6 loại rủi ro (market, fundamental, technical, macro, liquidity, sentiment)

### Step 6: INVESTMENT THESIS (main agent)

Tổng hợp toàn bộ pipeline → Investment Thesis format:

```
📊 LUẬN ĐIỂM ĐẦU TƯ — {TICKER} | {DATE} | Giá: {PRICE}
🏢 DOANH NGHIỆP | 📈 SỨC KHỎE TÀI CHÍNH | 📰 SỰ KIỆN | 😐 SENTIMENT
📉 KỸ THUẬT | ⚖️ LUẬN ĐIỂM (BULL vs BEAR) | 🛡️ RỦI RO
🎯 KHUYẾN NGHỊ | 📝 LUẬN ĐIỂM ĐẦU TƯ
```

### Step 7: LƯU DATABASE + JOURNAL

```bash
python3 scripts/portfolio.py log_analysis \
  --ticker {TICKER} --date {DATE} --close-price {PRICE} \
  --rating {RATING} --action {ACTION} \
  --target-price {TARGET} --stop-loss {STOP_LOSS} \
  --confidence {CONFIDENCE} \
  --bull-case "..." --bear-case "..." --recommendation "..."
```

---

## Stock Screener: "Nên đầu tư mã nào?"

Khi user hỏi không chỉ định ticker cụ thể:

### Flow

```
① Clarify universe (nếu chưa rõ)
   → VN30 (mặc định) | Ngành X | VN100 | Custom list

② SCREENING NHANH (~105s cho 30 mã)
   PYTHONPATH="" .venv/bin/python3 scripts/screener.py VN30 --limit 10
   Delay 3.5s/request → tôn trọng rate limit 20 req/phút (vnstock free tier)

③ HIỂN THỊ BẢNG XẾP HẠNG
   | # | Mã | Giá | P/E | ROE | EPS | Score | Ngành |

④ User chọn mã → Chạy pipeline 7 bước
```

### Composite Score Formula

```
pe_score   = (1 - pe/max_pe) * 35     # P/E thấp = tốt
roe_score  = (roe/max_roe) * 30       # ROE cao = tốt
quality    = (net_margin/30)*10 + (roa/15)*10
pb_score   = (1 - pb/max_pb) * 15     # P/B thấp = tốt
TOTAL      = pe_score + roe_score + quality + pb_score  (max ~100)
```

**Lưu ý:** Ngân hàng không có gross_margin, net_margin → quality score thấp hơn (đặc thù ngành). Nên so sánh trong cùng ngành.

### Rate Limiting

vnstock free tier: **20 req/phút**. Screener tự delay 3.5s/request.
- VN30 (30 mã) → ~105s | Top 10 VN30 → ~35s | VN100 → ~6 phút (không khuyến nghị)

---

## Cross-Ticker Analysis

Khi user hỏi ≥2 mã cùng lúc: chạy pipeline song song + thêm bảng so sánh:

```
📊 SO SÁNH NHANH
| Mã | Giá | P/E | P/B | ROE | LN Q2 | Trend | Rating | Target |
🏆 TOP PICK: {BEST_TICKER} — {REASON}
```

---

## Portfolio Tracking

```bash
# Thêm vị thế
python3 scripts/portfolio.py add_position --ticker HPG --buy-date 2026-07-30 --buy-price 24.8 --quantity 1000

# Đóng vị thế
python3 scripts/portfolio.py close_position --ticker HPG --sell-date 2026-08-15 --sell-price 26.5

# Check danh mục
python3 scripts/portfolio.py status

# Review sau N ngày
python3 scripts/portfolio.py review --ticker HPG --days 30
```

---

## Common Pitfalls

- **PYTHONPATH conflict**: Hermes set PYTHONPATH vào Python 3.11 của nó → gây conflict numpy với venv Python 3.14. Luôn dùng `PYTHONPATH=""` khi chạy script vnstock. Script `fundamentals_fetch.py` và `screener.py` đã tự xóa PYTHONPATH, nhưng khi gọi trực tiếp từ terminal() vẫn nên unset.
- **vnstock ratio() item_ids**: `trailing_eps`, `book_value_per_share_bvps`, `pe_ratio` (không phải `price_to_earnings_ratio`), `roe_trailling`, `roa_trailling`.
- **vnstock free tier**: Tối đa 4 kỳ báo cáo, 20 req/phút. Rate limit exceeded → script tự delay.
- **DNSE foreignTrading**: Thường HTTP 400 — không phải lỗi script. Ghi chú "Không có dữ liệu NĐTNN".
- **News search bị CAPTCHA**: Google/Bing/DuckDuckGo browser đều bị chặn. Fallback: Google News RSS, nhưng thường trả về ticker LIÊN QUAN (FPT → FRT). Luôn kiểm tra ticker trong title.
- **max_concurrent_children=3**: Tối đa 3 subagents song song. Step 3 (3 analysts) vừa đủ. Step 5 gộp 3 agent vào 1 batch → tiết kiệm 2 lần delegate.
- **fundamentals_fetch.py**: PHẢI dùng `.venv/bin/python3` (brew Python 3.14 + vnstock 4.0.5). Không dùng system Python (3.9 không cài được vnstock ≥4.0).

---

## Verification Checklist

- [ ] Step 1: Cả 2 scripts (`fundamentals_fetch.py` + `dnse_fetch.py`) chạy thành công, có JSON output
- [ ] Step 2: News Agent có kết quả HOẶC ghi chú fallback rõ ràng
- [ ] Step 3: 3 analyst reports đầy đủ (Fundamental score, Macro score, Technical entry)
- [ ] Step 4: Bull & Bear cases có evidence cụ thể, không chung chung
- [ ] Step 5: Rating có confidence score, Trader có entry/stop/target cụ thể, Risk có overall score
- [ ] Step 6: Investment Thesis đầy đủ các section (Doanh nghiệp → Tài chính → Sự kiện → Sentiment → Kỹ thuật → Luận điểm → Rủi ro → Khuyến nghị → Luận điểm đầu tư)
- [ ] Step 7: `portfolio.py log_analysis` chạy thành công, journal file được tạo
- [ ] Cross-ticker: Bảng so sánh có đầy đủ các cột, TOP PICK được chỉ định rõ
- [ ] Screener: `screener.py` chạy không lỗi rate limit, bảng xếp hạng hiển thị đúng
- [ ] Tất cả lệnh `terminal()` gọi script vnstock đều có `PYTHONPATH=""` prefix
