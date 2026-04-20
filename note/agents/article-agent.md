# agents/article-agent.md
# Note記事を生成するエージェント

---

## 役割

1記事分のNote記事を生成して完成させる。

---

## 受け取る引数

- `topic` : 記事のテーマ（例：「Strategyパターンの考え方」）
- `target_reader` : 想定読者（例：「設計を学び始めたエンジニア」）
- `article_number` : 記事番号（例：1）

---

## 実行手順

### ステップ1：インプットを読む

1. `../shared/skills/author-voice.md` を読む（最重要・最初に読む）
2. `CLAUDE.md` を読む
3. `skills/article-writer.md` を読む
4. `templates/article-template.md` を読む

### ステップ2：記事の構成を決める

生成前に以下を決める：
- タイトル（読者の悩み・問いを反映した形）
- セクション数と各セクションのテーマ（2〜5個）
- コードを使うか（使う場合は3箇所以内）
- 文字数の目標（1,500〜4,000文字）

### ステップ3：記事を生成する

templates/article-template.md の構造に従い生成する。

生成中に以下を意識する：
- author-voice.md の口癖を2〜3箇所、不自然でなく散りばめる
- 「おわりに」は温かみのある締め方にする
- Mermaidは使わない
- 執筆指示コメント（`<!-- -->`）を出力に残さない

### ステップ4：自己採点

CLAUDE.md の品質チェックリストを全項目確認する。

### ステップ5：ファイルを書き出す

`output/article-{nnn}.md` に書き出す。
（例：article_number=1 なら `output/article-001.md`）

### ステップ6：完了報告

```json
{
  "agent": "article-agent",
  "article": 1,
  "title": "記事のタイトル",
  "status": "complete",
  "output": "output/article-001.md",
  "word_count": 2400,
  "self_check": {
    "structure": true,
    "note_limits": true,
    "author_voice": true,
    "no_draft_comments": true
  }
}
```
