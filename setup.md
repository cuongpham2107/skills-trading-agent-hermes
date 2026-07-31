# VNStock AI — Setup Guide cho máy mới

Đưa file này cho Hermes (hoặc bất kỳ AI agent nào) trên máy mới và nói: **"Làm theo setup.md"**

---

## Step 1: Clone repo

```bash
git clone https://github.com/cuongpham2107/skills-trading-agent-hermes.git ~/vnstock-ai
cd ~/vnstock-ai
```

## Step 2: Tạo Python venv + cài vnstock

```bash
# Tạo venv (dùng brew Python nếu có, không thì system Python ≥3.10)
/opt/homebrew/bin/python3 -m venv .venv 2>/dev/null || python3 -m venv .venv
PYTHONPATH="" .venv/bin/pip install -U pip vnstock pandas requests pytz python-dateutil

# Test
PYTHONPATH="" .venv/bin/python3 -c "from vnstock import Fundamental; print('✅ vnstock OK')"
```

## Step 3: Cấu hình DNSE API keys

```bash
cp config/config.example.yaml config/config.yaml
```

Sau đó EDIT `config/config.yaml` — điền API key thật của DNSE:
```yaml
dnse:
  api_key: "YOUR_REAL_DNSE_API_KEY"
  api_secret: "YOUR_REAL_DNSE_API_SECRET"
```

## Step 4: Cài đặt vào Hermes (symlink skill)

```bash
SKILL_DIR=~/.hermes/skills/finance/dnse-stock-analysis
mkdir -p "$SKILL_DIR"

# Copy SKILL.md
cp ~/vnstock-ai/skills/SKILL.md "$SKILL_DIR/SKILL.md"

# Symlink các thư mục dùng chung
for dir in scripts data journal references prompts; do
  [ -L "$SKILL_DIR/$dir" ] || [ ! -e "$SKILL_DIR/$dir" ] && ln -sf ~/vnstock-ai/"$dir" "$SKILL_DIR/$dir"
done
ln -sf ~/vnstock-ai/AGENTS.md "$SKILL_DIR/AGENTS.md"
```

## Step 5: Cấu hình Telegram (nhận thông báo)

### 5a. Tạo Telegram Bot
1. Chat với [@BotFather](https://t.me/BotFather) trên Telegram
2. Gửi `/newbot` → đặt tên `VNStock AI` → username `vnstock_ai_bot`
3. Copy token (dạng `123456:ABC...`)

### 5b. Lấy Chat ID
1. Chat với bot vừa tạo (gửi `/start`)
2. Truy cập: `https://api.telegram.org/bot<TOKEN>/getUpdates`
3. Tìm `"chat":{"id": XXXXXXXX}` — đó là chat ID

### 5c. Config Hermes
```bash
hermes config set platforms.telegram.bot_token "BOT_TOKEN"
```

## Step 6: Tạo cron jobs (3 agents tự động)

### 🛡️ Portfolio Guardian — 15:30 T2-T6

```
Tạo cron job trong Hermes:

Tên: 🛡️ Portfolio Guardian
Skill: dnse-stock-analysis
Lịch: 0 15 * * 1-5 (15:30 mỗi T2-T6)
Workdir: /Users/USER/vnstock-ai
Tools: terminal, file
Deliver: telegram (với chat ID từ bước 5b)

Prompt:
Bạn là Portfolio Guardian. Mỗi ngày kiểm tra danh mục:
1. Chạy `python3 scripts/portfolio.py status` lấy danh sách vị thế
2. Với mỗi mã, chạy `python3 scripts/dnse_fetch.py {TICKER}` lấy giá đóng cửa
3. Tính P&L từng vị thế
4. Tìm tin mới nhất qua Google News RSS
5. Format output:

📊 DANH MỤC {DATE}
| Mã | Mua | Giá | P&L | % | Stop | Target | Trạng thái |

🚨 CẢNH BÁO (nếu giá gần stop-loss hoặc đạt target)

Nếu không có vị thế: "📭 Không có vị thế nào đang mở."
```

### 🔭 Market Scout — 08:00 sáng T2

```
Tên: 🔭 Market Scout
Skill: dnse-stock-analysis
Lịch: 0 8 * * 1 (08:00 mỗi thứ 2)
Workdir: /Users/USER/vnstock-ai
Tools: terminal, file
Deliver: telegram

Prompt:
Bạn là Market Scout. Mỗi sáng thứ 2:
1. Chạy `PYTHONPATH="" .venv/bin/python3 scripts/screener.py VN30 --limit 10`
2. Chọn TOP PICK của tuần
3. Format output:

🔭 MARKET SCOUT — TUẦN {DATE}
🏆 TOP PICK: {TICKER} — {lý do}
📊 TOP 5 XẾP HẠNG
| # | Mã | P/E | ROE | Score | Ngành |

⚠️ Screening nhanh, cần phân tích sâu trước khi đầu tư.
```

### 📊 Performance Auditor — 10:00 sáng T7

```
Tên: 📊 Performance Auditor
Skill: dnse-stock-analysis
Lịch: 0 10 * * 6 (10:00 mỗi thứ 7)
Workdir: /Users/USER/vnstock-ai
Tools: terminal, file
Deliver: telegram

Prompt:
Bạn là Performance Auditor. Mỗi thứ 7:
1. Đọc analysis_log trong data/trading.db, lấy phân tích >7 ngày
2. Fetch giá hiện tại cho từng mã
3. So sánh dự đoán vs thực tế
4. Format:

📊 PERFORMANCE REVIEW — {DATE}
📈 Đúng hướng: {X}% | Sai: {Y}% | Đạt target: {Z}%
📋 CHI TIẾT | Mã | Rating | Target | Giá HT | KQ
💡 BÀI HỌC: [pattern đúng/sai]
```

## Step 7: Test

```bash
# Test phân tích 1 mã
PYTHONPATH="" .venv/bin/python3 scripts/fundamentals_fetch.py FPT

# Test screener
PYTHONPATH="" .venv/bin/python3 scripts/screener.py LIST "TCB,VIB"

# Test portfolio
python3 scripts/portfolio.py status
```

---

## Sau khi setup xong

- **Guardian** sẽ tự động báo P&L mỗi 15:30 T2-T6 qua Telegram
- **Scout** sẽ gợi ý top pick mỗi sáng thứ 2
- **Auditor** sẽ review accuracy mỗi sáng thứ 7
- Trên Hermes: gõ `phân tích FPT` để chạy pipeline đầy đủ
- Trên Hermes: gõ `nên mua mã nào` để chạy screener

---

⚠️ **Lưu ý cho AI agent trên máy mới:**
- Luôn dùng `PYTHONPATH=""` trước mọi lệnh gọi vnstock
- vnstock free tier: 20 req/phút, delay 3.5s giữa các request
- DNSE foreignTrading thường lỗi HTTP 400 → bỏ qua
- News search có thể bị chặn CAPTCHA → fallback ghi chú
