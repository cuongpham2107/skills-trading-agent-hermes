# 🏦 VNStock AI Agent Suite — Requirements & Roadmap

> Bộ công cụ AI toàn diện cho phân tích & giao dịch chứng khoán Việt Nam.

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

### ✅ ĐÃ XONG (v3.2)

| Hạng mục | Mô tả |
|----------|-------|
| **Pipeline 8 bước** | Data Lock → Technical Compute → News/Sentiment → Analysts → Judge → Risk → Reflection → Thesis |
| **Anti-hallucination** | Data Lock khóa dữ liệu, Technical Compute tính chỉ báo, hậu kiểm số liệu |
| **TF-IDF RAG** | `knowledge_ingest.py` + `knowledge_query.py` — semantic search vĩ mô/ngành |
| **Judge Agent** | Tách khỏi Research Manager — phân xử Bull/Bear dựa trên bằng chứng |
| **Reflection** | Học từ lịch sử phân tích trước khi ra kết luận |
| **Data Sources** | vnstock 4.0 (BCTC) + DNSE API (OHLC) + Knowledge base (vĩ mô) |
| **Stock Screener** | `screener.py` — quét VN30, composite score, xếp hạng |
| **Investment Thesis** | Đầu ra có lý do, post-validation, format chuẩn |
| **Portfolio Tracking** | SQLite: positions, analysis_log, outcome_review |
| **Rating constraints** | Thiếu BCTC → max HOLD. Fundamental tốt + TA xấu → max HOLD |
| **Hard-cap position** | Tối đa 20%/mã |
| **Confidence rubric** | 3 mức (Thấp/Trung bình/Cao) — định tính, không phải xác suất |
| **Cross-ticker so sánh** | Bảng so sánh khi hỏi nhiều mã |
| **Scripts (8)** | `data_lock.py`, `dnse_fetch.py`, `fundamentals_fetch.py`, `technical_compute.py`, `knowledge_ingest.py`, `knowledge_query.py`, `screener.py`, `portfolio.py` |
| **Documentation** | README.md + SETUP.md + SKILL.md + prompts/ |

### Cần bổ sung

| Hạng mục | Mô tả |
|----------|-------|
| **Knowledge nội dung** | Thêm file macro + sector-frameworks + historical-cases (framework đã có, cần điền nội dung) |
| **screener --industry** | Lọc theo ngành từ `symbols_by_industries.csv` |
| **portfolio.py performance_report** | B.9 — thống kê win rate toàn bộ lịch sử |
| **portfolio.py review_all** | Auditor dùng để review hàng loạt |

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
| **Prompt** | `prompts/guardian.md` |

### 🔭 Market Scout

| Field | Value |
|-------|-------|
| **Trigger** | 08:00 sáng T2 |
| **Skill** | `dnse-stock-analysis` |
| **Tools** | terminal, file |
| **Task** | `screener.py VN30 --limit 10` → phân tích nhanh top 3 → top pick của tuần |
| **Output** | Bảng xếp hạng + Investment Thesis ngắn cho #1 |
| **Prompt** | `prompts/scout.md` |

### 📊 Performance Auditor

| Field | Value |
|-------|-------|
| **Trigger** | 10:00 sáng T7 |
| **Skill** | `dnse-stock-analysis` |
| **Tools** | terminal, file |
| **Task** | Query analysis_log >7 ngày → fetch giá hiện tại → so sánh dự đoán |
| **Output** | Accuracy report: đúng/sai/partial theo ticker, bài học rút ra |
| **Prompt** | `prompts/auditor.md` |

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

---

## 4. DNSE Trading MCP Server (`mcp-dnse-trading`)

### Account Tools

| Tool | Mô tả |
|------|-------|
| `get_balance` | Số dư tiểu khoản |
| `get_positions` | Danh sách vị thế |
| `get_orders_today` | Sổ lệnh trong ngày |
| `get_buying_power` | Sức mua theo mã + gói vay |
| `get_loan_packages` | Danh sách gói vay |

### Trading Tools

| Tool | Mô tả |
|------|-------|
| `send_otp` | Gửi OTP → lấy trading token |
| `verify_otp` | Xác thực OTP → token (8h) |
| `place_order` | Đặt lệnh |
| `modify_order` | Sửa lệnh |
| `cancel_order` | Hủy lệnh |
| `set_tp_sl` | Cài chốt lời/cắt lỗ |

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

## 📋 Implementation Roadmap

| # | Phase | Hạng mục | Status |
|---|-------|---------|--------|
| **1** | ✅ | Skill v3.2 (Data Lock + Technical Compute + TF-IDF RAG + Judge + Reflection) | Done |
| **2** | ✅ | Cron Agents (Guardian, Scout, Auditor prompts) | Done |
| **3** | 🔜 | Điền nội dung knowledge base (macro files, sector frameworks, historical cases) | Next |
| **4** | 🔜 | `portfolio.py performance_report` + `review_all` | Next |
| **5** | ⏳ | RAG Memory MCP Server | Sau |
| **6** | ⏳ | DNSE Trading MCP Server | Sau |
| **7** | ⏳ | Hermes Plugin (`/stock`, `/screen`, `/folio`) | Sau |

---

## 📁 File Structure

```
vnstock-ai/
├── README.md, SKILL.md, AGENTS.md, SETUP.md, REQUIREMENTS.md
├── scripts/
│   ├── data_lock.py              ✅
│   ├── dnse_fetch.py             ✅
│   ├── fundamentals_fetch.py     ✅
│   ├── technical_compute.py      ✅
│   ├── knowledge_ingest.py       ✅
│   ├── knowledge_query.py        ✅
│   ├── screener.py               ✅
│   ├── portfolio.py              ✅
│   └── dnse_trading.py           ⏳ Phase 6
├── knowledge/
│   ├── _index.md                 ✅
│   ├── macro/                    ⚠️ Cần điền nội dung
│   ├── sector-frameworks/        ⚠️ Mới có banking + technology
│   ├── historical-cases/         ⚠️ Chưa có file
│   └── .index/                   ✅ TF-IDF (auto-generated)
├── prompts/
│   ├── analyst.md                ✅
│   ├── guardian.md               ✅
│   ├── scout.md                  ✅
│   └── auditor.md                ✅
├── mcp/
│   ├── mcp-vnstock-rag/          ⏳ Phase 5
│   └── mcp-dnse-trading/         ⏳ Phase 6
├── references/, data/, journal/, config/, .venv/
```
