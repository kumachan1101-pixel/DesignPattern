# 🚀 実行タスク：記事003をNoteに投稿する

> このファイルをローカルのClaude Desktopで開いて「このタスクを実行して」と伝えてください。

---

## タスク概要

- **記事**：`note/output/articles/article-003.md`
- **タイトル**：【ソフトウェア設計】非同期処理を分離するというより、"責任"を分けたかった
- **タグ**：ソフトウェア設計 / 非同期処理 / プログラミング / エンジニア / クリーンアーキテクチャ
- **表紙画像**：ユーザーが用意済み（`note/output/covers/cover-003.png` として保存してください）

---

## 事前準備

### カバー画像の保存
添付の表紙画像（ソフトウェア設計の図解：非同期処理と責任分離のダイアグラム）を以下のパスに保存してください：

```
note/output/covers/cover-003.png
```

---

## 実行手順（Claude が自動で行う）

### STEP 1：NOTE_SESSION_V5 の確認

`note/api/post_article.py` の `NOTE_SESSION_V5` が有効であることを確認する。
期限切れの場合は、Noteにログイン → 開発者ツール → Cookie → `_note_session_v5` を取得して更新する。

### STEP 2：記事本文を Note に投稿する

```bash
python3 note/api/post_article.py \
  --title '【ソフトウェア設計】非同期処理を分離するというより、"責任"を分けたかった' \
  --body-file "note/output/articles/article-003.md" \
  --tags "ソフトウェア設計,非同期処理,プログラミング,エンジニア,クリーンアーキテクチャ"
```

出力から下書きURL（`https://note.com/edit/n/XXXXX`）を取得する。

### STEP 3：ブラウザでカバー画像をアップロードする

1. ブラウザで STEP 2 の下書き URL を開く（wait 3秒）
2. 「カバー画像を設定」ボタンを `find` でクリック
3. `note/output/covers/cover-003.png` をアップロード（wait 5秒）
4. 「下書き保存」をクリック（wait 3秒）
5. 完了のスクリーンショットを1枚撮る

### STEP 4：完了報告

```json
{
  "task": "publish-article-003",
  "status": "complete",
  "draft_url": "https://note.com/edit/n/XXXXX",
  "cover_uploaded": true,
  "cover_source": "user-provided"
}
```

完了後、このファイルの先頭行を `# [done] 🚀 実行タスク：記事003をNoteに投稿する` に変更して保存すること。

---

## 注意事項

- 投稿は必ず「下書き」状態で行う（「公開」はしない）
- `NOTE_SESSION_V5` が期限切れなら `note/api/post_article.py` を更新してから実行
