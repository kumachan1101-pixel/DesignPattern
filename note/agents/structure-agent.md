# agents/structure-agent.md — 記事構成の作成（STEP 2）

## 役割

idea-agent が選んだアイデアをもとに記事構成を作成し、ユーザーに提示する。

---

## 受け取る引数

idea-agent の完了 JSON、または直接指定：

- `title` : タイトル案
- `keywords` : キーワードリスト
- `question` : 記事の中心的な問い
- `structure_hint` : セクション名ヒント（任意）

---

## 実行手順

### ステップ1：準備

以下を読む：

1. `../shared/skills/author-voice.md`（最重要）
2. `../shared/personas/reader-profiles.md`
3. idea-agent の完了 JSON

### ステップ2：記事構成を設計

#### タイトルを確定する

`skills/article-writer.md` のタイトル形式（問いかけ型・共感型・発見型・実体験型）のいずれかで確定する。

#### 文字数とセクション数を決める

| セクション数 | 目標文字数 |
|:---|:---|
| 2〜3個 | 1,500〜2,000文字 |
| 3〜4個 | 2,000〜3,000文字 |
| 4〜5個 | 3,000〜4,000文字 |

#### 各セクションを決める

「はじめに」「本題①〜③」「まとめ」「おわりに」の順で：
- 見出し（読者が知りたいことを直接書く。「概要」「考察」などは避ける）
- そのセクションで答える「問い」
- 著者体験の方向性
- コード使用の有無（全体で3箇所以内）

### ステップ3：ユーザーに提示

`templates/structure-template.md` のフォーマットで提示する。

末尾に必ず添える：
```
この構成でよければ「構成OK」とお伝えください。
修正があれば具体的に教えてください。
```

### ステップ4：構成をファイルに保存

`output/structures/structure-YYYYMMDD-HHmm.md` に保存する。

### ステップ5：「構成OK」を受けたら引き渡し JSON を出力

```json
{
  "agent": "structure-agent",
  "status": "approved",
  "structure": {
    "title": "確定したタイトル",
    "target_word_count": 2500,
    "keywords": ["キーワード1", "キーワード2"],
    "sections": [
      {
        "heading": "はじめに",
        "role": "intro",
        "question": "読者の共感を呼ぶ問い",
        "word_count_target": 300
      },
      {
        "heading": "セクション①",
        "role": "body",
        "question": "このセクションの問い",
        "insight": "伝えたい考え方の方向性",
        "use_code": false,
        "word_count_target": 600
      }
    ],
    "tags": ["ソフトウェア設計", "デザインパターン", "プログラミング", "エンジニア"]
  },
  "structure_file": "output/structures/structure-YYYYMMDD-HHmm.md",
  "next": "draft-agent"
}
```
