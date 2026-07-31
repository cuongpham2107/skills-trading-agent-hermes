#!/bin/bash
# VNStock AI — Setup script cho máy mới
# Usage: bash setup.sh [github_url]

set -e

PROJECT_DIR="$HOME/vnstock-ai"
HERMES_SKILL_DIR="$HOME/.hermes/skills/finance/dnse-stock-analysis"

echo "🚀 VNStock AI Setup"
echo "===================="

# 1. Clone repo (skip if already in project dir)
if [ ! -d "$PROJECT_DIR/.git" ]; then
    REPO_URL="${1:-https://github.com/YOUR_USER/vnstock-ai.git}"
    echo ""
    echo "📦 Cloning $REPO_URL ..."
    git clone "$REPO_URL" "$PROJECT_DIR"
else
    echo "✅ Project already exists at $PROJECT_DIR"
fi

cd "$PROJECT_DIR"

# 2. Create Python venv
if [ ! -d ".venv" ]; then
    echo ""
    echo "🐍 Creating Python venv..."
    /opt/homebrew/bin/python3 -m venv .venv || python3 -m venv .venv
    .venv/bin/pip install -U pip vnstock pandas requests pytz python-dateutil
    echo "✅ venv created"
else
    echo "✅ venv exists"
fi

# 3. Test vnstock
echo ""
echo "🧪 Testing vnstock..."
PYTHONPATH="" .venv/bin/python3 -c "from vnstock import Fundamental; print('✅ vnstock OK')" || echo "⚠️ vnstock test failed — check Python version (need >=3.10)"

# 4. Create Hermes skill symlinks
echo ""
echo "🔗 Setting up Hermes skill symlinks..."
mkdir -p "$HERMES_SKILL_DIR"

# Copy SKILL.md
cp "$PROJECT_DIR/skills/SKILL.md" "$HERMES_SKILL_DIR/SKILL.md"

# Symlink directories
for dir in scripts data journal references prompts; do
    [ -L "$HERMES_SKILL_DIR/$dir" ] && rm "$HERMES_SKILL_DIR/$dir"
    [ -d "$HERMES_SKILL_DIR/$dir" ] && mv "$HERMES_SKILL_DIR/$dir" "$HERMES_SKILL_DIR/${dir}.old"
    ln -sf "$PROJECT_DIR/$dir" "$HERMES_SKILL_DIR/$dir"
done
ln -sf "$PROJECT_DIR/AGENTS.md" "$HERMES_SKILL_DIR/AGENTS.md"

echo "✅ Symlinks created"

# 5. Copy config template if not exists
if [ ! -f "config/config.yaml" ]; then
    cp config/config.example.yaml config/config.yaml
    echo ""
    echo "⚠️  Edit config/config.yaml with your DNSE API keys!"
fi

echo ""
echo "✅ Setup complete!"
echo ""
echo "📋 Next steps:"
echo "  1. Edit config/config.yaml with your DNSE API keys"
echo "  2. Configure Telegram: hermes config set platforms.telegram.bot_token \"YOUR_TOKEN\""
echo "  3. Create cron jobs (see README.md)"
echo "  4. Test: PYTHONPATH=\"\" .venv/bin/python3 scripts/fundamentals_fetch.py FPT"
