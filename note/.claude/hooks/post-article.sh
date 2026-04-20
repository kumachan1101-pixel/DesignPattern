#!/bin/bash
# .claude/hooks/post-article.sh
# Note記事の生成後に実行される品質チェックスクリプト

ARTICLE_FILE=$1
ARTICLE_NUM=$(echo "$ARTICLE_FILE" | grep -o '[0-9]\+' | head -1)
ISSUES=0

echo "========================================"
echo "記事生成後チェック：$ARTICLE_FILE"
echo "========================================"

# 1. ファイル存在確認
if [ ! -f "$ARTICLE_FILE" ]; then
  echo "ERROR: $ARTICLE_FILE が存在しません"
  exit 1
fi

# 2. 基本構造チェック
for section in "はじめに" "まとめ" "おわりに"; do
  if ! grep -q "$section" "$ARTICLE_FILE"; then
    echo "ERROR: 「$section」セクションが見つかりません"
    ISSUES=$((ISSUES+1))
  fi
done
echo "✅ 基本構造チェック完了"

# 3. h4以下の見出しチェック
if grep -qE "^####" "$ARTICLE_FILE"; then
  echo "WARN: h4以下の見出しが使われています（Noteでは読みにくい）"
  ISSUES=$((ISSUES+1))
fi

# 4. Mermaidチェック
if grep -q '```mermaid' "$ARTICLE_FILE"; then
  echo "ERROR: Mermaidが使われています（Noteでは表示されません）"
  ISSUES=$((ISSUES+1))
fi

# 5. コードブロック数チェック
CODE_BLOCKS=$(grep -c '^\`\`\`' "$ARTICLE_FILE")
CODE_COUNT=$((CODE_BLOCKS / 2))
if [ "$CODE_COUNT" -gt 3 ]; then
  echo "WARN: コードブロックが${CODE_COUNT}箇所あります（3箇所以内を推奨）"
  ISSUES=$((ISSUES+1))
fi

# 6. 著者の禁止表現チェック
for word in "スパゲッティ" "地獄" "最悪" "ダメなコード" "すべきです" "べきです"; do
  if grep -q "$word" "$ARTICLE_FILE"; then
    echo "ERROR: 著者の禁止表現「$word」が検出されました"
    ISSUES=$((ISSUES+1))
  fi
done

# 7. 他記事への依存チェック
if grep -qE "前回の記事|次回の記事" "$ARTICLE_FILE"; then
  echo "WARN: 他記事への依存表現が検出されました（各記事は単独で完結させる）"
  ISSUES=$((ISSUES+1))
fi

# 8. 執筆指示コメントの残留チェック
if grep -q "<!-- " "$ARTICLE_FILE"; then
  echo "WARN: HTMLコメント（執筆指示）が残っている可能性があります"
  ISSUES=$((ISSUES+1))
fi

# 9. TODO残留チェック
if grep -qE "TODO|FIXME|後で確認|未記入" "$ARTICLE_FILE"; then
  echo "WARN: メモ書きが残っています"
  ISSUES=$((ISSUES+1))
fi

# 文字数カウント（目安）
CHAR_COUNT=$(wc -m < "$ARTICLE_FILE")
echo "📝 文字数（概算）：${CHAR_COUNT}文字"
if [ "$CHAR_COUNT" -lt 1500 ]; then
  echo "WARN: 文字数が少ない可能性があります（1,500文字以上を推奨）"
fi
if [ "$CHAR_COUNT" -gt 8000 ]; then
  echo "WARN: 文字数が多い可能性があります（4,000文字以内を推奨）"
fi

# 結果レポート
echo "========================================"
if [ "$ISSUES" -eq 0 ]; then
  echo "✅ 後チェック完了：問題なし"
else
  echo "⚠️  後チェック完了：${ISSUES}件の問題が検出されました"
fi
echo "========================================"

# レビュー記録
mkdir -p review
cat > "review/article-${ARTICLE_NUM}-auto-review.md" << EOF
# 記事${ARTICLE_NUM} 自動レビュー結果

- 生成日時：$(date)
- 対象ファイル：$ARTICLE_FILE
- 文字数概算：${CHAR_COUNT}文字
- 検出された問題：${ISSUES}件
EOF

exit 0
