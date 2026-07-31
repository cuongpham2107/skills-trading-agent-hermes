# 🏦 VNStock AI Analyst

> Multi-agent AI pipeline phân tích cổ phiếu Việt Nam — mô phỏng quy trình của một quỹ đầu tư chuyên nghiệp.

## Triết lý

```
Không hỏi: "MACD cắt lên chưa?"
    Mà hỏi: "Đây có phải doanh nghiệp tốt ở mức giá hiện tại không?"
```

**Fundamental-first.** Technical chỉ để timing, không phải để quyết định.

## Tính năng

| Chế độ | Trigger | Kết quả |
|--------|---------|---------|
| **Phân tích 1 mã** | `phân tích FPT` | Investment Thesis đầy đủ 7 bước |
| **So sánh nhiều mã** | `đánh giá FPT, TCB, VIB` | Pipeline song song + bảng so sánh |
| **Stock Screener** 🆕 | `nên đầu tư mã nào` | Quét VN30 → xếp hạng → user chọn → deep dive |
| **Check danh mục** | `check danh mục` | P&L từng vị thế |
| **Review dài hạn** | `đánh giá lại FPT sau 30 ngày` | So sánh dự đoán vs thực tế |

## Pipeline 7 bước

```
Step 1: FETCH DATA (song song)
├── vnstock 4.0 → Fundamental (P/E, P/B, ROE, KQKD...)
└── DNSE API → OHLC, quotes, bid/ask

Step 2: NEWS & SENTIMENT (song song)
├── News Agent: "Chuyện gì vừa xảy ra?"
└── Sentiment Agent: "Mọi người nghĩ gì?"

Step 3: 3 ANALYSTS (song song)
├── Fundamental Analyst: Doanh nghiệp tốt? Giá hợp lý?
├── Macro & VN-Specific: Vĩ mô, ngành, dòng tiền ngoại
└── Technical Analyst: TÌM ĐIỂM VÀO (timing only)

Step 4: BULL vs BEAR DEBATE (song song)
├── Bull Researcher: Luận điểm MUA
└── Bear Researcher: Luận điểm BÁN

Step 5: QUYẾT ĐỊNH (song song)
├── Research Manager: RATING
├── Trader: Kế hoạch giao dịch
└── Risk Analyst: 6 loại rủi ro

Step 6: INVESTMENT THESIS
└── Tổng hợp → Luận điểm đầu tư có lý do

Step 7: LƯU DB & JOURNAL
└── SQLite + Markdown
```

## Đầu ra mẫu

```
📊 LUẬN ĐIỂM ĐẦU TƯ — VIB | 31/07/2026 | Giá: 14.75

🏢 DOANH NGHIỆP
VIB — Ngân hàng TMCP Quốc tế Việt Nam | HOSE | VN30, VN100

📈 SỨC KHỎE TÀI CHÍNH
P/E: 5.9x (vs ngành 9-10x 🔥) | P/B: 1.11x | ROE: 17.34%
EPS: 2,496 | LNST Q2: 1,625 tỷ | H1/2026 PAT: 4,147 tỷ

⚖️ LUẬN ĐIỂM
🐂 BULL: Deep value, insider mua 4.5M cp, ROE top-quartile
🐻 BEAR: Auditor=None CRITICAL, phân phối đỉnh, room ngoại cạn

🎯 KHUYẾN NGHỊ
Rating: HOLD (nghiêng UNDERWEIGHT) | Confidence: 50%
Entry: 14.10-14.30 | Target: 15.75 | Stop: 13.85
```

## Stock Screener 🆕

```
User: "nên đầu tư mã nào bây giờ?"

→ Chọn universe (VN30 mặc định)
→ Quét ~30 mã, tính composite score
→ Hiển thị bảng xếp hạng:

| # | Mã  | P/E  | ROE   | Score |
|---|-----|------|-------|-------|
| 1 | VIB | 5.9x | 17.3% | 46.0  |
| 2 | FPT | 11.2x| 27.3% | 43.3  |
| 3 | TCB | 9.4x | 14.2% | 42.1  |

→ User chọn mã → Pipeline 7 bước deep dive
```

## Data Sources

| Source | Dữ liệu | Rate Limit |
|--------|---------|------------|
| **vnstock 4.0** | P/E, P/B, ROE, KQKD, company info, ngành | 20 req/phút (free) |
| **DNSE API** | OHLC, quotes, bid/ask, NĐTNN | Không giới hạn |
| **Google News RSS** | Tin tức, sự kiện | Thường bị chặn |

## Cài đặt

```bash
# 1. Python 3.10+ (đã có brew Python 3.14)
brew install python@3.14

# 2. Tạo venv + cài vnstock
/opt/homebrew/bin/python3 -m venv .venv
.venv/bin/pip install vnstock pandas requests

# 3. Cấu hình DNSE API key
# Xem references/dnse-api-auth.md
```

## Cấu trúc thư mục

```
skills/finance/dnse-stock-analysis/
├── README.md                     ← Bạn đang ở đây
├── SKILL.md                      ← Logic + prompt cho AI agent
├── scripts/
│   ├── dnse_fetch.py             # OHLC, quotes từ DNSE
│   ├── fundamentals_fetch.py     # P/E, P/B, ROE từ vnstock
│   ├── screener.py               # Quét & xếp hạng cổ phiếu 🆕
│   └── portfolio.py              # SQLite positions + journal
├── references/
│   ├── dnse-api-auth.md
│   └── vnstock-v4-api.md
├── data/
│   ├── trading.db                # SQLite database
│   └── symbols_by_industries.csv
├── journal/                      # Markdown kết luận hàng ngày
└── .venv/                        # Python 3.14 + vnstock 4.0.5
```

## Ví dụ nhanh

```bash
# Fetch fundamental data
PYTHONPATH="" .venv/bin/python3 scripts/fundamentals_fetch.py FPT

# Screener VN30
PYTHONPATH="" .venv/bin/python3 scripts/screener.py VN30 --limit 10

# Check portfolio
python3 scripts/portfolio.py status

# Review sau 30 ngày
python3 scripts/portfolio.py review --ticker FPT --days 30
```

## ⚠️ Lưu ý

- **PYTHONPATH**: Hermes set PYTHONPATH vào Python 3.11 của nó → gây conflict numpy. Luôn dùng `PYTHONPATH=""` khi chạy script.
- **vnstock rate limit**: 20 req/phút cho free tier. Screener tự delay 3.5s/request.
- **DNSE foreignTrading**: Thường lỗi HTTP 400 — không phải lỗi script.
- **News search**: Google/Bing browser bị chặn CAPTCHA. Fallback: Google News RSS.
- Phân tích chỉ mang tính tham khảo, không phải lời khuyên tài chính.

## License

MIT — tự do sử dụng, phân phối, chỉnh sửa.
