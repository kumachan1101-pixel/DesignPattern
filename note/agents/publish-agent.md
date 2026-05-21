# agents/publish-agent.md — Note投稿（STEP 5）

## 役割

ユーザーの「OK」「投稿して」を受けて、`api/post_article.py` を自動実行し
記事を Note.com に下書き投稿する。

---

## 受け取る引数

cover-agent の完了 JSON、または直接指定：

- `article_file` : output/articles/ 内の記事ファイルパス

---

## 実行手順

### ステップ1：記事ファイルを読む

`article_file` を読み、以下を取得する：
- タイトル（1行目の `# ` を除いた部分）
- 本文（タイトル行を除いた全文）
- タグ（draft-agent の完了 JSON から取得。なければデフォルト値を使用）

**デフォルトタグ**：`["ソフトウェア設計", "デザインパターン", "プログラミング", "エンジニア"]`

### ステップ2：api/post_article.py を実行

```bash
python3 note/api/post_article.py \
  --title "記事タイトル" \
  --body-file "output/articles/article-NNN.md" \
  --tags "ソフトウェア設計,デザインパターン,プログラミング,エンジニア"
```

スクリプトが `NOTE_SESSION_V5` 未設定エラーを返した場合：
```
Note.comのセッションクッキーが未設定です。
api/post_article.py の NOTE_SESSION_V5 を更新してください。
取得方法：Noteにログイン → ブラウザの開発者ツール → Cookie → _note_session_v5 の値
```
と伝えて停止する。

### ステップ3：結果を確認

スクリプト出力を確認：
- `✅ 成功！下書きURL: https://note.com/edit/n/XXXXX` → 完了報告へ
- `❌ エラー: ステータス 401` → セッション期限切れとして案内
- タイムアウトエラー → 30秒待って1回だけ再試行

### ステップ4：完了報告

```json
{
  "agent": "publish-agent",
  "status": "complete",
  "article": {
    "title": "記事タイトル",
    "source_file": "output/articles/article-NNN.md",
    "tags": ["ソフトウェア設計", "デザインパターン", "プログラミング", "エンジニア"]
  },
  "note": {
    "status": "draft",
    "draft_url": "https://note.com/edit/n/XXXXX"
  }
}
```

完了後にユーザーへ伝える：
```
Noteに下書き投稿しました。
📝 下書きURL: https://note.com/edit/n/XXXXX

次のステップ：
1. 上記URLでNote記事を開いてカバー画像をアップロード
   （カバーSVG: output/covers/cover-NNN.svg）
2. 内容を最終確認して「公開」

Xへの紹介投稿が必要な場合は「この記事をXにポスト」とお伝えください。
```
