# CLAUDE.md — Note記事作成プロジェクト（ソフトウェア設計）

## このプロジェクトが作るもの

ソフトウェア設計に関するNote記事。
読者は「設計を学び始めたエンジニア」または「設計に悩んでいるリーダー」。
著者の実体験と考え方を、同じ目線で届けることを最優先にする。

---

## 必ず最初に読むファイル

エージェントは作業開始前に以下を必ずこの順番で読むこと：

1. `../shared/skills/author-voice.md`  — 著者の人格（最重要）
2. このCLAUDE.md の残りのルール

---

## メインワークフロー：5ステップ記事作成

```
[STEP 1] idea-agent
  WebSearch で自動SEOリサーチ → 記事アイデア3〜5案を提案
  → ユーザーが「〇番を深掘りして」と選択

[STEP 2] structure-agent
  選ばれたアイデアをもとに記事構成を作成・提示
  → ユーザーが「構成OK」と承認

[STEP 3] draft-agent
  承認された構成から本文ドラフトを自動生成
  → output/articles/ に .md を書き出し

[STEP 4] cover-agent（STEP 3 完了後に自動実行）
  記事タイトル・テーマからカバー画像（SVG）を自動生成
  → output/covers/ に .svg を書き出し
  → 「確認してOKなら投稿してください」と伝える

[STEP 5] publish-agent
  ユーザーが「OK」または「投稿して」と言ったら
  api/post_article.py を自動実行 → Note に下書き投稿
```

### ユーザー承認フレーズ

| フレーズ例 | 動作 |
|:---|:---|
| 「〇番を深掘りして」「これで深掘りして」 | STEP 1 → STEP 2 |
| 「構成OK」「この構成で」 | STEP 2 → STEP 3（→ STEP 4 も自動） |
| 「OK」「投稿して」 | STEP 5 を自動実行 |

### ステップ間の引き継ぎ

- 各ステップ完了時にコンパクトな JSON を出力する
- 次のエージェントは前ステップの JSON を読んで続きを実行する
- ユーザーの承認なく次のステップに進まない（STEP 3→4 のみ自動）

---

## Note記事の構造ルール

### タイトルルール

**全記事のタイトル先頭に `【ソフトウェア設計】` を必ず付ける。**
例：`# 【ソフトウェア設計】「パターンを覚えたのに、コードに使えない」と感じていた頃のこと`

これはブログ全体で統一しているルールのため、例外なく適用する。

### 基本構造

```
# 【ソフトウェア設計】タイトル

## はじめに（3〜5文）

## 本題セクション①〜③（2〜5個）

## まとめ（3点以内）

## おわりに（温かみのある締め）
```

### Note固有の制限

- 文字数：1,500〜4,000文字
- コードブロック：3箇所以内
- Mermaid：使わない（表示されないため）
- 見出し：h2・h3 のみ（h4以下は使わない）
- 太字：1段落2箇所以内
- リスト：連続5項目以上は散文に変換

---

## 品質チェックリスト（生成後に必ず確認）

- [ ] 基本構造が揃っているか
- [ ] 1,500〜4,000文字の範囲か
- [ ] Mermaidを使っていないか / コードブロック3箇所以内か
- [ ] 「〜すべき」「〜べきです」がないか
- [ ] 著者の口癖が2〜3箇所散りばめられているか
- [ ] メモ書き・執筆指示コメントが残っていないか

---

## エージェント一覧

| エージェント | 役割 | 使用ツール |
|:---|:---|:---|
| **idea-agent** | SEOリサーチ＋アイデア提案 | WebSearch |
| **structure-agent** | 記事構成の作成 | Read/Write |
| **draft-agent** | 本文ドラフト生成 | Write |
| **cover-agent** | カバーSVG生成（自動） | Write |
| **publish-agent** | Note投稿 | Bash（Python実行） |
| review-agent | 品質レビュー | Read |
| gemini-to-note-agent | GeminiURL→Note投稿 | ブラウザ操作 |
| note-to-x-agent | Note記事→X紹介投稿 | WebFetch／ブラウザ |

---

## ファイル構成

```
note/
├── CLAUDE.md
├── agents/
│   ├── idea-agent.md          ← STEP 1
│   ├── structure-agent.md     ← STEP 2
│   ├── draft-agent.md         ← STEP 3
│   ├── cover-agent.md         ← STEP 4（自動）
│   ├── publish-agent.md       ← STEP 5
│   ├── review-agent.md
│   ├── gemini-to-note-agent.md
│   └── note-to-x-agent.md
├── skills/
│   ├── article-writer.md
│   ├── seo-research.md        ← NEW
│   └── cover-design.md        ← NEW
├── templates/
│   ├── article-template.md
│   ├── idea-proposal-template.md  ← NEW
│   └── structure-template.md      ← NEW
├── api/
│   ├── post_note_draft.py     ← 既存（参考）
│   └── post_article.py        ← NEW（引数対応版）
└── output/
    ├── ideas/        ← STEP 1 出力
    ├── structures/   ← STEP 2 出力
    ├── articles/     ← STEP 3 出力
    ├── covers/       ← STEP 4 出力
    └── images/
```
