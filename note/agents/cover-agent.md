# agents/cover-agent.md — カバー画像生成（STEP 4・自動実行）

## 役割

draft-agent 完了後に自動実行される。
記事タイトル・テーマから SVG カバー画像を生成し output/covers/ に書き出す。

---

## 受け取る引数

draft-agent の完了 JSON：

- `title` : 記事タイトル
- `keywords` : キーワードリスト
- `file` : 記事ファイルパス（記事番号の取得に使う）

---

## 実行手順

### ステップ1：準備

以下を読む：

1. `skills/cover-design.md`（カラーパレット・レイアウトルール）
2. draft-agent の完了 JSON

### ステップ2：デザイン方針を決める

`cover-design.md` のテーマ別カラーパレットから背景色・アクセントカラーを選ぶ。
タイトルの文字数を確認して1行 or 2行（`<tspan>` 改行）を決める（目安：20文字/行）。

### ステップ3：SVG を生成して書き出す

`cover-design.md` の SVG 雛形をベースに、タイトル・サブテキストを埋め込んだ
SVG を生成し、`output/covers/cover-NNN.svg` に書き出す。
（NNN は記事番号に合わせる）

**仕様**：幅 1280px、高さ 670px（16:9）

### ステップ4：完了報告

完了後にユーザーへ以下を伝える：

```
記事ドラフトとカバー画像が完成しました。

📄 記事：output/articles/article-NNN.md
🎨 カバー：output/covers/cover-NNN.svg

内容をご確認いただき、問題なければ「OK」または「投稿して」とお伝えください。
Noteに下書きとして自動投稿します。

※ カバー画像はNote投稿後に手動でアップロードをお願いします
  （Note APIはカバー画像の自動アップロード非対応のため）
```

```json
{
  "agent": "cover-agent",
  "status": "complete",
  "cover": {
    "file": "output/covers/cover-NNN.svg",
    "width": 1280,
    "height": 670
  },
  "next": "publish-agent（ユーザーのOKを待つ）"
}
```
