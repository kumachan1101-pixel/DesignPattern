#!/bin/bash
# .claude/hooks/pre-chapter.sh
# 章の生成を始める前に実行される検証スクリプト

CHAPTER_NUM=$1
PATTERN_NAME=$2
PATTERN_FILE="patterns/${PATTERN_NAME}.yaml"

echo "========================================"
echo "章生成前チェック：第${CHAPTER_NUM}章（${PATTERN_NAME}）"
echo "========================================"

# 1. パターン定義ファイルの存在確認
if [ ! -f "$PATTERN_FILE" ]; then
  echo "ERROR: $PATTERN_FILE が見つかりません"
  exit 1
fi
echo "✅ パターン定義ファイル確認済み"

# 2. 必須フィールドの確認
required_fields="change_type scenario: observations trial_approach advanced_scenario next_chapter"
for field in $required_fields; do
  if ! grep -q "$field" "$PATTERN_FILE"; then
    echo "ERROR: $PATTERN_FILE に '$field' が定義されていません"
    exit 1
  fi
done
echo "✅ 必須フィールド確認済み"

# 3. 共通スキルファイルの存在確認
if [ ! -f "../../shared/skills/author-voice.md" ]; then
  echo "ERROR: shared/skills/author-voice.md が見つかりません"
  exit 1
fi
if [ ! -f "../../shared/skills/markdown-checker.md" ]; then
  echo "ERROR: shared/skills/markdown-checker.md が見つかりません"
  exit 1
fi
echo "✅ 共通スキルファイル確認済み"

# 4. テンプレートファイルの確認
if [ ! -f "templates/chapter-template.md" ]; then
  echo "ERROR: templates/chapter-template.md が見つかりません"
  exit 1
fi
echo "✅ テンプレートファイル確認済み"

# 5. output ディレクトリの存在確認
if [ ! -d "output" ]; then
  mkdir -p "output"
fi
echo "✅ outputディレクトリ確認済み"

echo "========================================"
echo "前チェック完了。章の生成を開始します。"
echo "========================================"
exit 0
