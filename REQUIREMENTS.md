# 🏦 VNStock AI Agent Suite — Requirements & Roadmap

> Bộ công cụ AI toàn diện cho phân tích & giao dịch chứng khoán Việt Nam.
> Từ phân tích cơ bản → screening → giao dịch tự động → học hỏi từ lịch sử.

---

## 🏗️ Tổng quan kiến trúc

```
┌──────────────────────────────────────────────────────────────────────┐
│                       VNStock AI Agent Suite                          │
├──────────┬──────────┬──────────┬──────────────┬───────────┬──────────┤
│ 🛡️       │ 🔭       │ 📊       │ 💾           │ 🔌        │ ⚡       │
│ Guardian │ Scout    │ Auditor  │ RAG Memory   │ Trading   │ Plugin   │
│ Cron     │ Cron     │ Cron     │ MCP Server   │ MCP       │ Hermes   │
├──────────┼──────────┼──────────┼──────────────┼───────────┼──────────┤
│ T2-T6    │ T2 08:00 │ T7 10:00 │ Search       │ Account   │ /stock   │
│ 15:30    │ Weekly   │ Weekend  │ Compare      │ Order     │ /screen  │
│ P&L      │ Top Pick │ Review   │ Context      │ OTP       │ /folio   │
└──────────┴──────────┴──────────┴──────────────┴───────────┴──────────┘
```

---

## 1. Skill: `dnse-stock-analysis`

### ✅ ĐÃ XONG

| Hạng mục | Mô tả |
|----------|-------|
| **Pipeline 7 bước** | Fundamental-First: BCTC → News/Sentiment → Analysts → Debate → Quyết định → Thesis |
| **Data Sources** | vnstock 4.0 (P/E, ROE, KQKD) + DNSE API (OHLC, quotes) |
| **Stock Screener** | Quét VN30, composite score, xếp hạng |
| **Investment Thesis** | Đầu ra có lý do, format chuẩn |
| **Portfolio Tracking** | SQLite: positions, analysis_log, outcome_review |
| **Scripts** | `fundamentals_fetch.py`, `dnse_fetch.py`, `screener.py`, `portfolio.py` |
| **README** | Hướng dẫn đầy đủ |
| **Cấu trúc** | Đạt chuẩn Hermes (Overview, When to Use, Pitfalls, Checklist) |

### Cần bổ sung

| Hạng mục | Mô tả |
|----------|-------|
| **Cross-ticker bảng so sánh** | Đã có logic, cần test thêm |
| **Support thêm ngành** | `screener.py` hỗ trợ `--industry Ngân hàng` |

---

## 2. Cron Agents (3 agents)

### 🛡️ Portfolio Guardian

| Field | Value |
|-------|-------|
| **Trigger** | 15:30 T2-T6 |
| **Skill** | `dnse-stock-analysis` |
| **Tools** | terminal, file |
| **Task** | Fetch giá đóng cửa → tính P&L → tìm tin → cảnh báo stop-loss/target |
| **Output** | Báo cáo P&L danh mục + alerts nếu có |

### 🔭 Market Scout

| Field | Value |
|-------|-------|
| **Trigger** | 08:00 sáng T2 |
| **Skill** | `dnse-stock-analysis` |
| **Tools** | terminal, file |
| **Task** | `screener.py VN30 --limit 10` → phân tích nhanh top 3 → top pick của tuần |
| **Output** | Bảng xếp hạng + Investment Thesis ngắn cho #1 |

### 📊 Performance Auditor

| Field | Value |
|-------|-------|
| **Trigger** | 10:00 sáng T7 |
| **Skill** | `dnse-stock-analysis` |
| **Tools** | terminal, file |
| **Task** | Query analysis_log >7 ngày → fetch giá hiện tại → so sánh dự đoán |
| **Output** | Accuracy report: đúng/sai/partial theo ticker, bài học rút ra |

---

## 3. RAG Memory MCP Server (`mcp-vnstock-rag`)

### Mục đích
Cho agent "trí nhớ dài hạn" — mọi phân tích cũ đều có thể tra cứu và đối chiếu.

### Data Source
- `data/trading.db` → bảng `analysis_log` + `outcome_review`
- `journal/*.md` → full markdown analyses

### MCP Tools

| Tool | Input | Output | Use Case |
|------|-------|--------|----------|
| `search_analyses` | ticker, limit=5 | List phân tích cũ (rating, target, date) | "Lần trước nói gì về FPT?" |
| `get_latest_analysis` | ticker | Phân tích gần nhất + so sánh giá hiện tại | Auto context injection |
| `search_similar` | query, limit=5 | Phân tích có nội dung tương tự | "Còn mã nào giống VIB không?" |
| `get_outcome_stats` | ticker | Accuracy: đúng/sai/partial count | "Tôi dự đoán FPT đúng bao nhiêu lần?" |
| `get_journal_content` | ticker, date | Full markdown của phân tích đó | Deep context |

### Tích hợp vào Pipeline

```
Step 0 (mới): RAG LOOKUP
├── search_analyses(ticker) → context từ phân tích cũ
├── get_outcome_stats(ticker) → accuracy history
└── Context được inject vào Step 3 analysts
    ↓
Step 1-7: Pipeline hiện tại (có thêm context lịch sử)
    ↓
Step 8 (mới): SAVE + INDEX
└── Lưu DB → RAG tự động có thể search được
```

---

## 4. DNSE Trading MCP Server (`mcp-dnse-trading`)

### Mục đích
Cho phép agent tự động kiểm tra tài khoản & đặt lệnh thông qua DNSE API.

### Account Tools

| Tool | Mô tả | DNSE Endpoint |
|------|-------|---------------|
| `get_balance` | Số dư tiểu khoản (cơ sở + phái sinh) | Account info |
| `get_positions` | Danh sách vị thế đang nắm giữ | Positions |
| `get_orders_today` | Sổ lệnh trong ngày | Orders today |
| `get_order_detail` | Chi tiết 1 lệnh theo orderId | Order detail |
| `get_buying_power` | Sức mua/bán theo mã + gói vay | Buying power |
| `get_loan_packages` | Danh sách gói vay | Loan packages |
| `get_order_history` | Lịch sử lệnh (tối đa 1 năm) | Order history |
| `get_position_detail` | Chi tiết vị thế theo positionId | Position detail |
| `get_tp_sl_config` | Cấu hình chốt lời/cắt lỗ | TP/SL config |
| `get_rights_events` | Lịch sử sự kiện quyền | Rights events |

### Trading Tools

| Tool | Mô tả | DNSE Endpoint |
|------|-------|---------------|
| `send_otp` | Gửi OTP qua email → lấy trading token | Email OTP |
| `verify_otp` | Xác thực OTP → trading token (8h) | Verify OTP |
| `place_order` | Đặt lệnh (cơ sở/phái sinh) | Place order |
| `modify_order` | Sửa lệnh theo orderId | Modify order |
| `cancel_order` | Hủy lệnh theo orderId | Cancel order |
| `close_position` | Đóng vị thế phái sinh | Close position |
| `set_tp_sl` | Cài chốt lời/cắt lỗ cho vị thế | Set TP/SL |

### Flow giao dịch

```
Agent: "BUY TCB 1000 cp giá 29.0"
    ↓
① send_otp → User nhận OTP email
    ↓
② verify_otp → Trading token (8h)
    ↓
③ get_buying_power("TCB") → Đủ sức mua?
    ↓
④ place_order("TCB", "BUY", 1000, 29.0)
    ↓
⑤ get_orders_today → Xác nhận lệnh đã khớp
```

---

## 5. Hermes Plugin (`vnstock`)

### Mục đích
Slash commands để gọi nhanh từ chat.

### Commands

| Command | Hành động |
|---------|----------|
| `/stock FPT` | Phân tích 1 mã → Investment Thesis |
| `/stock FPT,TCB,VIB` | Phân tích nhiều mã → bảng so sánh |
| `/screen` | Screener VN30 → bảng xếp hạng |
| `/screen ngân-hàng` | Screener theo ngành |
| `/folio` | Check danh mục + P&L |
| `/folio buy FPT 1000 67.0` | Thêm vị thế |
| `/folio sell FPT` | Đóng vị thế |
| `/review FPT 30` | Review sau 30 ngày |

---

## 📋 Implementation Roadmap

| # | Phase | Hạng mục | Ước tính |
|---|-------|---------|----------|
| **1** | ✅ Done | Skill v3.1 + Screener + README | Đã xong |
| **2** | 🔜 Next | 3 Cron Agents (Guardian, Scout, Auditor) | 15 phút |
| **3** | 🔜 Next | RAG MCP Server (`mcp-vnstock-rag`) | 30 phút |
| **4** | ⏳ Sau | Tích hợp RAG vào Pipeline (Step 0 + Step 8) | 10 phút |
| **5** | ⏳ Sau | DNSE Trading MCP Server (`mcp-dnse-trading`) | 45 phút |
| **6** | ⏳ Sau | Tích hợp Trading → Auto order flow | 15 phút |
| **7** | ⏳ Sau | Hermes Plugin (`/stock`, `/screen`, `/folio`) | 20 phút |

---

## 📁 File Structure (khi hoàn thiện)

```
~/.hermes/skills/finance/dnse-stock-analysis/
├── SKILL.md                     # ✅ Logic + prompts
├── README.md                    # ✅ Documentation
├── scripts/
│   ├── dnse_fetch.py            # ✅ OHLC từ DNSE
│   ├── fundamentals_fetch.py    # ✅ BCTC từ vnstock
│   ├── screener.py              # ✅ Stock screening
│   ├── portfolio.py             # ✅ SQLite tracking
│   └── dnse_trading.py          # ⏳ Trading wrapper (Phase 5)
├── mcp/
│   ├── mcp-vnstock-rag/         # ⏳ RAG MCP (Phase 3)
│   │   ├── server.py
│   │   └── requirements.txt
│   └── mcp-dnse-trading/        # ⏳ Trading MCP (Phase 5)
│       ├── server.py
│       └── requirements.txt
├── plugin/
│   └── vnstock/                 # ⏳ Hermes Plugin (Phase 7)
│       └── plugin.py
├── references/
├── data/
├── journal/
└── .venv/
```
