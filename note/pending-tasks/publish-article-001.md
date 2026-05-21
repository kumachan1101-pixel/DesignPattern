# 🚀 実行タスク：記事001をNoteに投稿する

> このファイルをローカルのClaude Desktopで開いて「このタスクを実行して」と伝えてください。

---

## タスク概要

- **記事**：`note/output/articles/article-001.md`
- **タイトル**：【ソフトウェア設計】「パターンを覚えたのに、コードに使えない」と感じていた頃のこと
- **タグ**：ソフトウェア設計 / デザインパターン / プログラミング / エンジニア

---

## 実行手順（Claude が自動で行う）

### STEP 1：Gemini でカバー画像を生成する

`agents/cover-agent.md` の手順に従い実行する：

1. `https://gemini.google.com` を開く（wait 3秒）
2. 以下のプロンプトを送信する（wait 15秒）：

```
Note記事のカバー画像を作成してください。

【条件】
- サイズ：横長（16:9）
- テーマ：ソフトウェア設計・デザインパターン
- 記事タイトル：「パターンを覚えたのに、コードに使えない」と感じていた頃のこと
- スタイル：ダークトーン、プロフェッショナル、テクノロジー感のある抽象的なデザイン
- テキストは入れない（タイトル文字は不要）
- クラス図・ノード・接続線などソフトウェア設計を連想させる抽象的なビジュアル
- 色調：ネイビー・ブルー系をベースに赤のアクセント
```

3. 生成された画像のURLを取得してダウンロードする
4. `note/output/covers/cover-001.png` として保存する

### STEP 2：記事本文を Note に投稿する

```bash
python3 note/api/post_article.py \
  --title "【ソフトウェア設計】「パターンを覚えたのに、コードに使えない」と感じていた頃のこと" \
  --body-file "note/output/articles/article-001.md" \
  --tags "ソフトウェア設計,デザインパターン,プログラミング,エンジニア"
```

出力から下書きURL（`https://note.com/edit/n/XXXXX`）を取得する。

### STEP 3：ブラウザでカバー画像をアップロードする

1. ブラウザで STEP 2 の下書き URL を開く（wait 3秒）
2. 「カバー画像を設定」ボタンを `find` でクリック
3. `note/output/covers/cover-001.png` をアップロード（wait 5秒）
4. 「下書き保存」をクリック（wait 3秒）
5. 完了のスクリーンショットを1枚撮る

### STEP 4：完了報告

```json
{
  "task": "publish-article-001",
  "status": "complete",
  "draft_url": "https://note.com/edit/n/XXXXX",
  "cover_uploaded": true,
  "cover_source": "gemini"
}
```

完了後、このファイルの先頭行を `# [done] 🚀 実行タスク：記事001をNoteに投稿する` に変更して保存すること。

---

## 注意事項

- 投稿は必ず「下書き」状態で行う（「公開」はしない）
- `NOTE_SESSION_V5` が期限切れなら `note/api/post_article.py` を更新してから実行
- Gemini 未ログインの場合はログインしてから再実行
