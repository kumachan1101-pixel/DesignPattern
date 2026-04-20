#!/bin/bash
# .claude/hooks/post-chapter.sh
# 章の生成後に実行される品質チェックスクリプト

CHAPTER_FILE=$1
CHAPTER_NUM=$(echo "$CHAPTER_FILE" | grep -o '[0-9]\+' | head -1)
ISSUES=0

echo "========================================"
echo "章生成後チェック：$CHAPTER_FILE"
echo "========================================"

# 1. ファイル存在確認
if [ ! -f "$CHAPTER_FILE" ]; then
  echo "ERROR: $CHAPTER_FILE が存在しません"
  exit 1
fi

# 2. 仕様の3層チェック
if ! grep -q "このシステムが何をするか" "$CHAPTER_FILE"; then
  echo "WARN: 仕様の第1層（システム概要）が見つかりません"
  ISSUES=$((ISSUES+1))
fi
if ! grep -q "現在の仕様" "$CHAPTER_FILE"; then
  echo "WARN: 仕様の第2層（現在の仕様）が見つかりません"
  ISSUES=$((ISSUES+1))
fi
if ! grep -q "いま立っている状況" "$CHAPTER_FILE"; then
  echo "WARN: 仕様の第3層（状況）が見つかりません"
  ISSUES=$((ISSUES+1))
fi

# 3. コードラベルチェック
for label in "起点コード" "試行コード" "解決コード" "深化コード" "過剰コード"; do
  if ! grep -q "$label" "$CHAPTER_FILE"; then
    echo "WARN: 【${label}】が見つかりません"
    ISSUES=$((ISSUES+1))
  fi
done

# 4. ステップラベルチェック
for step in "ステップ1" "ステップ2" "ステップ3" "ステップ4" "ステップ5"; do
  if ! grep -q "$step" "$CHAPTER_FILE"; then
    echo "WARN: $step のラベルが見つかりません"
    ISSUES=$((ISSUES+1))
  fi
done

# 5. 著者の禁止表現チェック
forbidden_words="スパゲッティ 地獄 最悪 ダメなコード すべきです べきです"
for word in $forbidden_words; do
  if grep -q "$word" "$CHAPTER_FILE"; then
    echo "ERROR: 著者の禁止表現「$word」が検出されました"
    ISSUES=$((ISSUES+1))
  fi
done

# 6. 執筆指示コメントの残留チェック
if grep -q "執筆指示\|ここに〜\|後で確認\|TODO\|FIXME" "$CHAPTER_FILE"; then
  echo "WARN: 執筆指示またはメモが残っている可能性があります"
  ISSUES=$((ISSUES+1))
fi

# 7. コードブロックの対応確認（簡易）
OPEN=$(grep -c '^\`\`\`' "$CHAPTER_FILE")
if [ $((OPEN % 2)) -ne 0 ]; then
  echo "WARN: コードブロックの開閉が一致しない可能性があります（合計${OPEN}個）"
  ISSUES=$((ISSUES+1))
fi

# 8. テスト存在チェック
TEST_COUNT=$(grep -c "TEST(" "$CHAPTER_FILE" 2>/dev/null || echo 0)
if [ "$TEST_COUNT" -lt 4 ]; then
  echo "WARN: テストが${TEST_COUNT}個しかありません（最低4個：試行×1、解決×2、深化×1）"
  ISSUES=$((ISSUES+1))
fi

# 9. 他章への言及チェック
if grep -qE "前章で|第[0-9]+章と同様|すでに学んだ" "$CHAPTER_FILE"; then
  echo "ERROR: 他章への言及が検出されました（章の独立性違反）"
  ISSUES=$((ISSUES+1))
fi

# 結果レポート
echo "========================================"
if [ "$ISSUES" -eq 0 ]; then
  echo "✅ 後チェック完了：問題なし"
else
  echo "⚠️  後チェック完了：${ISSUES}件の問題が検出されました"
fi
echo "========================================"

# レビュー記録を作成
mkdir -p review
cat > "review/chapter${CHAPTER_NUM}-auto-review.md" << EOF
# 第${CHAPTER_NUM}章 自動レビュー結果

- 生成日時：$(date)
- 対象ファイル：$CHAPTER_FILE
- 検出された問題：${ISSUES}件

チェック項目は post-chapter.sh を参照してください。
EOF

exit 0
