# Kindle × Note 執筆プロジェクト

ソフトウェア設計に関するKindle本とNote記事を
Claude Codeで自律的に生成するための環境です。

---

## フォルダ構成

```
files/
├── README.md                          ← このファイル
├── shared/
│   └── skills/
│       ├── author-voice.md            ← 著者の人格（全プロジェクト共通）
│       └── markdown-checker.md        ← Markdown品質チェック（全プロジェクト共通）
│
├── kindle/
│   ├── design-patterns/               ← デザインパターンの考え方を学ぶ本（作成中）
│   │   ├── CLAUDE.md
│   │   ├── .claude/hooks/
│   │   ├── agents/
│   │   ├── skills/
│   │   ├── templates/
│   │   ├── patterns/                  ← 各パターンの定義YAML
│   │   └── output/                    ← 生成された章
│   │
│   └── book-template/                 ← 新しいKindle本を作る時のひな型
│       ├── CLAUDE.md
│       ├── agents/
│       ├── skills/
│       ├── templates/
│       └── output/
│
└── note/                              ← Note記事プロジェクト
    ├── CLAUDE.md
    ├── ideas.txt                      ← 記事ネタ（1行1ネタ）← ここに書くだけで自動生成
    ├── .claude/hooks/
    ├── agents/
    ├── skills/
    ├── templates/
    └── output/                        ← 生成された記事
```

---

## 全プロジェクト共通のルール

### 著者について

`shared/skills/author-voice.md` に著者の人格が定義されています。
**すべてのエージェントは作業開始前にこのファイルを必ず読みます。**

著者の核心：
> 「ポンコツだった自分が設計の楽しさに気づいた。
>  同じように悩んでいる人に、一つの参考として届けたい。」

### 語り口の三原則

1. **読者と同じ目線**：「答えを知っている人」ではなく「同じ道を先に歩んだ人」として書く
2. **正解を押しつけない**：「〜すべき」は使わない。「一つの参考として」のスタンスを貫く
3. **既存コードへのリスペクト**：「スパゲッティ」「地獄」などの否定的なラベルは使わない

---

## Kindle本の作り方

### 既存プロジェクト（design-patterns）を動かす

```bash
cd kindle/design-patterns

# 全章を生成する（orchestratorに任せる）
claude "agents/orchestrator.md の手順に従って本を生成してください"

# 特定の章だけ生成する
claude "agents/chapter-agent.md の手順に従って、
patterns/strategy.yaml を使って第1章を生成してください"
```

### 新しいKindle本を作る

1. `kindle/book-template/` をコピーして新しいフォルダを作る（例：`kindle/my-new-book/`）
2. CLAUDE.md の「このプロジェクトが作るもの」を書き換える
3. `templates/chapter-template.md` を本の構造に合わせて書き換える
4. `agents/chapter-agent.md` を調整する

---

## Note記事の作り方

### 自動生成（推奨）

`note/ideas.txt` に記事ネタを1行1ネタで書くだけで、
スケジュールエージェントが定期的に読んで記事を自動生成します。

```
# ideas.txt の書き方例
Strategyパターンで「変わるもの」を分離する考え方
設計を学び始めたとき最初につまずいた3つのこと
チームで設計を議論するときに意識していること
```

処理済みのネタには自動で `[done]` が付きます。

### 手動生成

```bash
cd note

# 記事を1本生成する
claude "agents/article-agent.md の手順に従って、
テーマ『Strategyパターンの考え方』の記事を生成してください"
```

---

## 新しいパターンを追加する（design-patterns）

1. `kindle/design-patterns/patterns/` に新しい YAML ファイルを作る
2. `patterns/strategy.yaml` を参考に必須フィールドを埋める
3. orchestrator に「新しいパターンの章を生成してください」と依頼する

### YAMLの必須フィールド

```yaml
pattern:
  name:         # パターン名
  chapter:      # 章番号
  change_type:  # 今回の変化の種類（一言で）

scenario:
  domain:           # システムのドメイン
  system_overview:  # システムの概要
  current_spec:     # 現在の仕様（リスト）
  situation:        # いま立っている状況（who/what/deadline）

observations:       # 観察のリスト（3〜5個）
trial_approach:     # 試行案の方針
trial_limits:       # 試行案の限界（リスト）

advanced_scenario:  # より難しい変化（深化コード用）
  what:
  extension:

threshold:
  use_when:   # 使う状況（リスト）
  skip_when:  # 使わない状況（リスト）

next_chapter:
  preview:    # 次章の予告（一文）
```

---

## よくある質問

**Q. どの章から読んでも大丈夫？**
A. はい。第1章以降は完全に独立しています。第0章を読んでいれば、どの章からでも始められます。

**Q. 著者の人格を変えたい**
A. `shared/skills/author-voice.md` を編集してください。全プロジェクトに反映されます。

**Q. 生成が途中で止まったら**
A. `review/` フォルダのレビュー結果を確認して、問題の章を再生成してください。
