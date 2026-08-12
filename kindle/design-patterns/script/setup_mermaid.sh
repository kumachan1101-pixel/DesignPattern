#!/bin/sh
# Mermaid CLI（mmdc）を script/.mermaid-tools/ へ入れる。
#
# check_mermaid.py は PATH の mmdc が無ければここを見る。Chromium は
# 環境にあるもの（Playwright 同梱・apt の chromium・CI の google-chrome）を
# check_mermaid.py 側が探して使うため、ここでは落とさない。
#
#   bash kindle/design-patterns/script/setup_mermaid.sh
#
# 削除して入れ直すときは script/.mermaid-tools/ ごと消してよい（gitignore 済み）。
set -eu

SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)
TOOLS_DIR="$SCRIPT_DIR/.mermaid-tools"

mkdir -p "$TOOLS_DIR"
cd "$TOOLS_DIR"

if [ ! -f package.json ]; then
    printf '{ "private": true, "description": "check_mermaid.py 用のローカル依存" }\n' \
        > package.json
fi

# Puppeteer に Chrome を落とさせない。既存の Chromium を check_mermaid.py が使う。
PUPPETEER_SKIP_DOWNLOAD=1 npm install --no-audit --no-fund @mermaid-js/mermaid-cli

echo
echo "導入先: $TOOLS_DIR/node_modules/.bin/mmdc"
echo "確認  : python3 $SCRIPT_DIR/check_mermaid.py"
