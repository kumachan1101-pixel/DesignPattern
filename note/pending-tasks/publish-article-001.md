# 🚀 実行タスク：記事001をNoteに投稿する

> このファイルをローカルのClaude Desktopで開いて「このタスクを実行して」と伝えてください。

---

## タスク概要

- **記事**：`note/output/articles/article-001.md`
- **カバー画像**：`note/output/covers/cover-001.png`
- **タイトル**：【ソフトウェア設計】「パターンを覚えたのに、コードに使えない」と感じていた頃のこと
- **タグ**：ソフトウェア設計 / デザインパターン / プログラミング / エンジニア

---

## 実行手順（Claude が自動で行う）

### STEP 1：記事本文を Note に投稿する

`note/output/articles/article-001.md` を読み、以下を実行する：

```bash
python3 note/api/post_article.py \
  --title "【ソフトウェア設計】「パターンを覚えたのに、コードに使えない」と感じていた頃のこと" \
  --body-file "note/output/articles/article-001.md" \
  --tags "ソフトウェア設計,デザインパターン,プログラミング,エンジニア"
```

出力から下書きURL（`https://note.com/edit/n/XXXXX`）を取得する。

### STEP 2：下書きをブラウザで開いてカバー画像をアップロードする

`agents/gemini-to-note-agent.md` のブラウザ操作方式に従い：

1. ブラウザで STEP 1 で取得した下書き URL を開く（wait 3秒）
2. カバー画像エリア（「カバー画像を設定」ボタン）を `find` で特定してクリック
3. `note/output/covers/cover-001.png` をアップロード（wait 5秒）
4. 「下書き保存」をクリック（wait 3秒）
5. 完了のスクリーンショットを1枚撮る

### STEP 3：完了報告

```json
{
  "task": "publish-article-001",
  "status": "complete",
  "draft_url": "https://note.com/edit/n/XXXXX",
  "cover_uploaded": true
}
```

タスク完了後、このファイルの先頭に `[done]` を付けて保存すること。

---

## 注意事項

- 投稿は必ず「下書き」状態で行う（「公開」はしない）
- `NOTE_SESSION_V5` が期限切れの場合は `note/api/post_article.py` を更新してから実行
- カバー画像アップロード後に「公開」するかどうかはユーザーが決める
