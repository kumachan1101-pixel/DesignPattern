# agents/cover-agent.md — カバー画像生成（STEP 4・自動実行）

## 役割

draft-agent 完了後に自動実行される。
Gemini に画像生成を依頼し、生成された画像を取得して
`output/covers/cover-NNN.png` に保存する。

> ⚠️ このエージェントはブラウザ操作を使用するため、ローカルの Claude Desktop で実行すること。

---

## 受け取る引数

draft-agent の完了 JSON：

- `title` : 記事タイトル
- `keywords` : キーワードリスト
- `file` : 記事ファイルパス（記事番号の取得に使う）

---

## ⚠️ 通信量節約の原則

| ❌ 禁止 | ✅ やること |
|:---|:---|
| 各ステップでスクリーンショット | 画像保存確認の1枚のみ |
| get_page_text 全体取得 | find で必要な要素だけ取得 |
| wait を長くとりすぎる | 画像生成中は wait 15秒、それ以外は wait 3秒 |

---

## 実行手順

### ステップ1：画像生成プロンプトを作る

記事タイトルとキーワードから以下の形式でプロンプトを生成する：

```
Note記事のカバー画像を作成してください。

【条件】
- サイズ：横長（16:9）
- テーマ：ソフトウェア設計・デザインパターン
- 記事タイトル：{title}
- キーワード：{keywords}
- スタイル：ダークトーン、プロフェッショナル、テクノロジー感のある抽象的なデザイン
- テキストは入れない（タイトル文字は不要）
- クラス図・ノード・接続線などソフトウェア設計を連想させる抽象的なビジュアル
- 色調：ネイビー・ブルー系をベースに赤やオレンジのアクセント
```

### ステップ2：Gemini を開いてプロンプトを送る

1. `tabs_create_mcp` で新しいタブを作成する
2. `https://gemini.google.com` に移動する（wait 3秒）
3. ログイン済みであることを確認する
   - 未ログインの場合はユーザーに通知して停止する
4. テキスト入力欄にステップ1で作成したプロンプトをペーストして送信する（wait 15秒）
   - Gemini の画像生成が完了するまで待つ

### ステップ3：生成された画像をダウンロードする

1. 生成された画像を `find` で特定する
2. 画像を右クリック → 「名前を付けて画像を保存」 または
   `javascript_tool` で画像の src URL を取得してダウンロードする：

```javascript
// 生成画像のURLを取得
const img = document.querySelector('img[src*="lh3.googleusercontent"]')
  || document.querySelector('.generative-image img')
  || document.querySelector('[data-image-src]');
img ? img.src : 'not found';
```

3. 取得した URL から画像をダウンロードして `output/covers/cover-NNN.png` に保存する

### ステップ4：SVG は生成しない

Gemini 生成画像を PNG としてそのまま使用する。SVG は不要。

### ステップ5：完了報告

```json
{
  "agent": "cover-agent",
  "status": "complete",
  "cover": {
    "file": "output/covers/cover-NNN.png",
    "source": "gemini",
    "cover_png_available": true
  },
  "next": "publish-agent（ユーザーのOKを待つ）"
}
```

完了後にユーザーへ以下を伝える：

```
記事ドラフトとカバー画像（Gemini生成）が完成しました。

📄 記事：note/output/articles/article-NNN.md
🎨 カバー：note/output/covers/cover-NNN.png

内容をご確認いただき、問題なければ「OK」または「投稿して」とお伝えください。
Note に記事を投稿し、カバー画像も自動でアップロードします。
```

---

## エラー時の対応

| エラー | 対応 |
|:---|:---|
| Gemini 未ログイン | ログインを促してから再実行する |
| 画像生成に失敗（エラーメッセージ表示） | プロンプトを短くして再試行（1回まで） |
| 画像 URL が取得できない | スクリーンショットを撮ってユーザーに確認を求める |
| 画像の縦横比が合わない | Gemini 再生成を依頼し「横長16:9」を強調する |
