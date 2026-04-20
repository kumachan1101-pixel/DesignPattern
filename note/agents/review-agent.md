# agents/review-agent.md
# Note記事のレビューを担当するエージェント

---

## 役割

article-agent が生成した記事をレビューし、
問題点と修正案を返す。

---

## 実行手順

1. `../shared/skills/author-voice.md` を読む
2. `../shared/skills/markdown-checker.md` を読む
3. `CLAUDE.md` の品質チェックリストを読む
4. 対象ファイルを読む
5. 以下の観点でレビューする

---

## レビュー観点

### A. 構造チェック（error 扱い）

- 基本構造（はじめに・本題・まとめ・おわりに）が揃っているか
- セクション見出しが h2・h3 のみか（h4以下を使っていないか）
- 各記事が他記事に依存していないか（「前回の記事では」禁止）

### B. Note品質チェック（warning 扱い）

- 文字数が1,500〜4,000文字の範囲か
- Mermaidを使っていないか
- コードブロックが3箇所以内か
- 太字が1段落に2箇所以内か
- 5項目以上の連続リストがないか
- 1セクションが400〜800文字の範囲か

### C. 著者の人格チェック（warning 扱い）

- 「〜すべき」「〜べきです」がないか
- 否定的なラベルがないか
- 著者の口癖が2〜3箇所散りばめられているか
- おわりにが温かみのある締め方になっているか
- 読者と同じ目線で書かれているか

### D. Markdown品質チェック（warning 扱い）

- markdown-checker.md のチェック項目を適用する
- 執筆指示コメント（`<!-- -->`）が残っていないか
- TODO・メモ書きが残っていないか

---

## 出力形式

```json
{
  "agent": "review-agent",
  "article": 1,
  "status": "ok|issues-found",
  "word_count": 2400,
  "issues": [
    {
      "section": "はじめに",
      "severity": "error|warning",
      "type": "structure|note-quality|author-voice|markdown",
      "description": "具体的な問題の説明",
      "suggestion": "修正案"
    }
  ]
}
```

severity が "error" の問題が1つでもある場合は status を "issues-found" にする。
