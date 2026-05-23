# agents/publish-agent.md — Note投稿＋カバー画像アップロード（STEP 5）

## 役割

ユーザーの「OK」「投稿して」を受けて以下を自動実行する：

1. `api/post_article.py` で本文を Note に下書き投稿
2. ブラウザで下書きを開き、カバー画像を自動アップロード

---

## 受け取る引数

cover-agent の完了 JSON：

- `article_file` : 記事ファイルパス
- `title` : 記事タイトル
- `tags` : タグリスト
- `cover.png` : カバー画像パス
- `cover.cover_png_available` : PNG が利用可能か

---

## ⚠️ 通信量節約の原則

| ❌ 禁止 | ✅ やること |
|:---|:---|
| 各ステップでスクリーンショット | カバー保存確認の1枚のみ |
| get_page_text / read_page 全体取得 | find で必要な要素だけ取得 |
| wait を長くとりすぎる | wait 3秒基本、ファイル選択後は wait 5秒 |

---

## 実行手順

### ステップ1：記事ファイルを読む

`article_file` を読み、以下を取得する：
- タイトル（1行目の `# ` を除いた部分）
- 本文（タイトル行を除いた全文）
- タグ（完了 JSON から取得。なければデフォルト値を使用）

**デフォルトタグ**：`["ソフトウェア設計", "デザインパターン", "プログラミング", "エンジニア"]`

### ステップ2：本文を API 投稿する

```bash
python3 note/api/post_article.py \
  --title "記事タイトル" \
  --body-file "note/output/articles/article-NNN.md" \
  --tags "ソフトウェア設計,デザインパターン,プログラミング,エンジニア"
```

出力から **下書きキー**（`https://note.com/edit/n/XXXXX` の `XXXXX` 部分）を取得する。

**エラー時**：

| エラー | 対応 |
|:---|:---|
| `NOTE_SESSION_V5` 未設定 | 設定方法を案内して停止 |
| ステータス 401 | セッション期限切れとして案内して停止 |
| タイムアウト | 30秒待って1回だけ再試行 |

### ステップ3：カバー画像をブラウザでアップロードする

`cover_png_available: false` の場合はこのステップをスキップする。

1. ブラウザで `https://note.com/edit/n/XXXXX` に移動（wait 3秒）
2. カバー画像設定エリアを `find` で特定する
   - `find: "カバー画像を設定"` または `find: "サムネイル"` でボタンを探す
3. ボタンをクリック（wait 2秒）
4. ファイルアップロードダイアログが開いたら、`computer` ツールで PNG ファイルを選択する
   - ファイルパス：`note/output/covers/cover-NNN.png`（絶対パスに変換して使用）
5. アップロード完了を確認（wait 5秒）
6. `find: "下書き保存"` をクリック（wait 3秒）
7. 保存完了のスクリーンショットを1枚撮る

**ファイルアップロードダイアログが開かない場合**：
ページをリロードして手順2から再試行（1回まで）。
それでも失敗する場合はカバーアップロードをスキップし、完了報告に記載する。

### ステップ4：完了報告

```json
{
  "agent": "publish-agent",
  "status": "complete",
  "article": {
    "title": "記事タイトル",
    "source_file": "note/output/articles/article-NNN.md",
    "tags": ["ソフトウェア設計", "デザインパターン", "プログラミング", "エンジニア"]
  },
  "note": {
    "status": "draft",
    "draft_url": "https://note.com/edit/n/XXXXX"
  },
  "cover_uploaded": true
}
```

ユーザーへ伝える：

```
Noteへの投稿が完了しました 🎉

📝 下書きURL: https://note.com/edit/n/XXXXX
🎨 カバー画像：アップロード済み

あとはNoteの下書きを開いて「公開」するだけです。

Xへの紹介投稿が必要な場合は「この記事をXにポスト」とお伝えください。
```
