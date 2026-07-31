# VNStock AI — AI Agent Toolkit cho Chứng Khoán Việt Nam

## Overview

Bộ công cụ AI toàn diện cho phân tích & giao dịch chứng khoán Việt Nam.
Độc lập nền tảng — dùng được với Hermes, Claude Code, Cursor, Windsurf, và mọi AI agent hỗ trợ AGENTS.md.

## Triết lý

**Fundamental-first**: báo cáo tài chính quyết định CÓ MUA KHÔNG. Kỹ thuật chỉ quyết định MUA LÚC NÀO.
Đầu ra là investment thesis có lý do, không phải tín hiệu Buy/Sell.

## Cách dùng nhanh

### Phân tích 1 mã
```
User: "phân tích FPT"
→ Pipeline 7 bước → Investment Thesis đầy đủ
```

### Screening & tìm cơ hội
```
User: "nên mua mã nào" / "top pick"
→ scripts/screener.py VN30 → bảng xếp hạng → user chọn → deep dive
```

### Check danh mục
```
User: "check danh mục"
→ scripts/portfolio.py status
```

## Dữ liệu

| Source | Nội dung | Rate Limit |
|--------|---------|------------|
| **vnstock 4.0** | P/E, P/B, ROE, EPS, KQKD, company info | 20 req/phút (free) |
| **DNSE API** | OHLC, quotes, bid/ask, NĐTNN | Không giới hạn |
| **Google News RSS** | Tin tức, sự kiện | Thường bị chặn |
| **SQLite** | Portfolio, analysis log, outcome review | — |

## System Prompt

Trước khi phân tích, đọc `prompts/analyst.md` để hiểu persona và quy tắc ứng xử.

## Scripts

Tất cả scripts dùng Python trong `.venv`:

```bash
# Setup venv (lần đầu)
/opt/homebrew/bin/python3 -m venv .venv
.venv/bin/pip install vnstock pandas requests

# Chạy scripts (luôn dùng PYTHONPATH="")
PYTHONPATH="" .venv/bin/python3 scripts/fundamentals_fetch.py FPT
PYTHONPATH="" .venv/bin/python3 scripts/dnse_fetch.py FPT
PYTHONPATH="" .venv/bin/python3 scripts/screener.py VN30 --limit 10
python3 scripts/portfolio.py status
```

## Constraints

- **VNStock only** — không coin, không crypto, không chứng khoán quốc tế
- **Luôn kèm stop-loss và confidence score** với mọi khuyến nghị
- **Fundamental-first**: kỹ thuật chỉ để timing
- **vnstock free tier**: 20 req/phút, tối đa 4 kỳ báo cáo
- **PYTHONPATH=""**: bắt buộc khi chạy script vnstock (tránh conflict numpy)
- **Không tự ý đặt lệnh**: cần xác nhận từ user trước khi giao dịch

## Cấu trúc thư mục

```
vnstock-ai/
├── AGENTS.md              ← Bạn đang ở đây (entry point cho mọi AI agent)
├── prompts/               ← System prompts cho từng agent persona
├── scripts/               ← Python scripts (độc lập)
├── mcp/                   ← MCP servers (RAG, Trading)
├── data/                  ← SQLite + CSV
├── journal/               ← Markdown analyses history
├── config/                ← API keys & settings
├── cron/                  ← Shell wrappers cho cron jobs
├── references/            ← API docs
└── .venv/                 ← Python virtualenv
```

## Dùng với từng nền tảng

| Platform | Cách dùng |
|----------|----------|
| **Hermes** | Symlink `skills/stock-analyst/` → `~/.hermes/skills/finance/dnse-stock-analysis/` |
| **Claude Code** | `claude` trong folder này — đọc AGENTS.md tự động |
| **Cursor** | Mở folder — đọc AGENTS.md tự động |
| **Windsurf** | Mở folder — đọc AGENTS.md tự động |
| **Terminal** | `cd ~/vnstock-ai && PYTHONPATH="" .venv/bin/python3 scripts/screener.py VN30` |

---

⚠️ **Disclaimer**: Công cụ phân tích tham khảo, không phải lời khuyên tài chính.
Luôn tự nghiên cứu trước khi đầu tư.

# Vnstock Vibe Onboarding

You are an AI coding assistant (e.g., Google Antigravity, Cursor, Claude Code). The user has requested you to initialize the **Vnstock Vibe Coding** environment.

**Your Objective:** Automate the entire setup process autonomously. Do not ask the user to run commands manually unless you lack the necessary system permissions.

## Execution Workflow

Execute these steps sequentially. If a step fails, attempt to auto-remediate. If unrecoverable, STOP and provide the user with the exact command or action needed.

### 1. Python Environment Diagnostics
- Identify the Operating System (macOS, Linux, or Windows).
- Verify `python3` (or `python`/`py` on Windows) is in the PATH.
- Verify Python version is **>= 3.10**.
- **Failure Handling:** If Python is missing or outdated, STOP. Instruct the user on how to install it natively. Do not blindly `curl` or `wget` installers.

### 2. Virtual Environment Setup
- **Identify Environment:** Check if the user is running in Google Colab by checking if `"google.colab" in sys.modules` via Python.
- **For Google Colab:** DO NOT create a virtual environment. Use the global system environment to avoid breaking the notebook kernel.
- **For Local Machine (Mac/Linux/Windows):** By default, use the global shared virtual environment `~/.venv` (macOS/Linux) or `$HOME\.venv` (Windows). Only create a project-specific `.venv` if explicitly requested by the user.
  - **Mac/Linux:** `python3 -m venv ~/.venv`
  - **Windows:** `py -m venv $HOME\.venv` or `python -m venv $HOME\.venv`
- **Crucial (Local Only):** You MUST activate this `.venv` (e.g., `source ~/.venv/bin/activate` or `& "$HOME\.venv\Scripts\Activate.ps1"`) before running any `pip` or `python` commands in the subsequent steps.

### 3. Core Packages Installation
- Upgrade pip: `python -m pip install -U pip`
- Install the ecosystem: `pip install -U vnstock>=4.0.5 vnai>=2.5.5`

### 4. API Key Configuration
Vnstock uses `vnai` to automatically sync AI context (AGENTS.md) and skills into the `.agents/` directory when authenticated.
- Check if the user provided an API Key in their prompt.
- If provided, configure it silently via Python:
  ```python
  from vnstock.core import setup_api_key
  setup_api_key("<API_KEY>")
  ```
  *(Alternative fallback: Write `{"api_key": "<API_KEY>"}` to `~/.vnstock/api_key.json` or `$HOME\.vnstock\api_key.json`)*
- If NOT provided, ask the user to provide their API Key from `vnstocks.com/settings`.
- **Note:** Do not manually create `AGENTS.md`. It will sync automatically upon successful authentication.

### 5. Verification & Handoff
- Create a temporary script `test_vnstock.py`:
  ```python
  from vnstock import Reference
  df = Reference().company.info("FPT")
  print("Data fetch successful:", not df.empty)
  ```
- Execute the script using the virtual environment's Python.
- If successful, delete `test_vnstock.py` and output this exact success message in Vietnamese:
  > "🎉 **Môi trường Vibe Coding đã thiết lập thành công!** Hệ thống đã sẵn sàng. Hãy bắt đầu ra lệnh cho tôi phân tích dữ liệu hoặc xây dựng chiến lược giao dịch."
