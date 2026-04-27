# agents/gemini-to-note-agent.md
# GeminiのURLからNote記事を下書き保存するエージェント

---

## 役割

指定されたGeminiのURLにある記事コンテンツをコピーし、
Gemini GEMに画像生成を依頼して、Noteに下書き状態で投稿する。

---

## 受け取る引数

- `gemini_url` : GeminiのGemコンテンツURL
  （例：https://gemini.google.com/gem/ab22a645b92d/64716de513a74bbc）

---

## 固定設定値

| 設定項目 | 値 |
|:---|:---|
| 画像生成GEM URL | https://gemini.google.com/gem/a11de770c380 |
| Note投稿URL | https://note.com/notes/new |

---

## ⚠️ 通信量節約の原則

| ❌ 禁止 | ✅ やること |
|:---|:---|
| 各ステップでスクリーンショット | 保存後の1枚のみ（画像生成は不要） |
| get_page_text / read_page | find で目的の要素だけ取得 |
| ペースト後のDOM直接書き換え | ペースト前にクリップボードをクリーニング |
| wait を長くとりすぎる | wait 3秒を基本、画像生成のみ wait 12秒 |

---

## 実行手順

### ステップ1：記事コンテンツをコピーする

1. ブラウザで `gemini_url` に移動する（wait 3秒）
2. ページを最下部までスクロールして応答末尾を表示する
3. 応答ブロック下部の **📋アイコン（コピーボタン）** を `find` で取得してクリック
   - ✅ `find: "コピーボタン 応答をコピー"` → クリック
   - ❌ 「コピー」ボタン（ページ上部）はURL/タイトルをコピーするため使わない
4. ページ上部のタイトルテキストを確認して記録する（タイトル入力・タグ決定に使う）

---

### ステップ2：クリップボードを事前クリーニングする

コピー直後（Geminiページ上で）`javascript_tool` を実行してクリップボードを整形する。
これにより、Noteへのペースト後にタイトルとコードラベルが残る問題を防ぐ。

```javascript
(async () => {
  const text = await navigator.clipboard.readText();
  const lines = text.split('\n');

  // 先頭行（タイトル）を削除
  const withoutTitle = lines.slice(1);

  // コードブロックラベル行を削除
  const labels = new Set([
    'plaintext', 'javascript', 'typescript', 'python', 'bash', 'shell',
    'json', 'xml', 'css', 'html', 'sql', 'cpp', 'c++', 'java', 'go',
    'ruby', 'c#', 'php', 'kotlin', 'swift', 'rust', 'scala', 'yaml',
    'markdown', 'diff', 'text', 'txt'
  ]);
  const cleaned = withoutTitle.filter(line => !labels.has(line.trim().toLowerCase()));

  await navigator.clipboard.writeText(cleaned.join('\n'));
  return `cleaned: ${lines.length} → ${cleaned.length} lines`;
})();
```

> **もし clipboard API が権限エラーになった場合：**
> このステップをスキップして次へ進む。ペースト後にステップ7-Bのフォールバックで対処する。

---

### ステップ3：画像生成を依頼する

1. `tabs_create_mcp` で新しいタブを作成する
2. `https://gemini.google.com/gem/a11de770c380` に移動（wait 3秒）
3. 入力欄にステップ1で記録した **記事タイトルをそのままペーストしてEnter**
4. wait 12秒（画像生成完了を待つ）
5. ユーザーに保存を依頼する：
   > 「画像が生成されました。`note\output\images\` に名前をつけて保存してください。保存できたら教えてください。」
6. ユーザーの返答を待つ（保存完了 or スキップの確認）

---

### ステップ4：Note新規記事を開く

1. `tabs_create_mcp` で新しいタブを作成する
2. `https://note.com/notes/new` に移動（wait 3秒）

---

### ステップ5：タイトルを入力する

```
find: タイトル入力欄（プレースホルダー「記事タイトル」）
form_input: ステップ1で記録したタイトルを入力
```

---

### ステップ6：目次を挿入する

1. 本文エリア（タイトル下）をクリックしてカーソルを置く（wait 1秒）
2. `/` のみ入力して wait 1秒
3. パレットから「目次」を `find` でクリック
   - パレットが出ない場合：本文エリアをクリックし直して再試行

---

### ステップ7-A：本文をペーストする（クリーニング済みの場合）

1. 目次コンポーネントの下の行をクリック
2. `Ctrl+V` でペーストする（wait 8秒）

ステップ2が成功していれば、タイトル行・コードラベルはすでに除去されている。
スクリーンショットは不要。そのまま次のステップへ進む。

---

### ステップ7-B：フォールバック（クリーニングがスキップされた場合のみ）

ステップ2をスキップした場合のみ実行する。

#### 先頭タイトル行の削除

```
Ctrl+Home でドキュメント先頭へ移動
Shift+End で先頭行を選択
Delete で削除
空行が残った場合はさらに Backspace
```

#### コードラベル行の削除

```javascript
const labels = new Set([
  'plaintext', 'javascript', 'typescript', 'python', 'bash', 'shell',
  'json', 'xml', 'css', 'html', 'sql', 'cpp', 'c++', 'java', 'go',
  'ruby', 'c#', 'php', 'kotlin', 'swift', 'rust', 'scala', 'yaml',
  'markdown', 'diff', 'text', 'txt'
]);
document.querySelectorAll('.ProseMirror p').forEach(p => {
  if (labels.has(p.textContent.trim().toLowerCase())) p.remove();
});
```

実行後、`Ctrl+S` で下書き保存してProseMirrorに変更を反映させる。

---

### ステップ8：タグを入力する

```
「公開に進む」ボタンをクリック
→ タグ入力欄に1タグ入力 → Enter（3〜5タグ分繰り返す）
→ 「キャンセル」で編集画面に戻る
```

タグ候補：`ソフトウェア設計 / デザインパターン / プログラミング / エンジニア / AI`

---

### ステップ9：カバー画像をアップロードする（任意）

ステップ3でユーザーが画像を保存済みの場合のみ実行。

```
find: サムネイル設定エリア（カメラアイコン、タイトル上部）
left_click: カメラアイコン → 「画像をアップロード」
find: file input要素
file_upload: C:\Users\kumac\OneDrive\デスクトップ\Claude\files\note\output\images\{ファイル名}
```

---

### ステップ10：下書き保存して完了報告する

```
「下書き保存」ボタンをクリック
screenshot 1枚で「下書きを保存しました」を確認
```

完了報告（JSON）：

```json
{
  "agent": "gemini-to-note-agent",
  "source_url": "<使用したGemini URL>",
  "title": "<記事タイトル>",
  "tags": ["タグ1", "タグ2", "タグ3"],
  "note_status": "draft",
  "clipboard_cleaned": true,
  "status": "complete"
}
```

---

## よくあるエラーと対処

| エラー | 対処 |
|:---|:---|
| clipboard API が権限エラー | ステップ2をスキップしてステップ7-Bを実行 |
| 「コピー」ボタンでURLがペーストされた | 応答ブロック下部の📋アイコンを使う |
| NoteタブからGeminiに戻れない（Leave site?ダイアログ） | `tabs_create_mcp` で新規タブを開く |
| 目次がプレーンテキストになった | `/` のみ入力してパレット表示を確認してから「目次」を選択 |
| ペースト後にブラウザが固まる | wait 10秒待ってから操作再開 |
| コードラベル削除後に本文が壊れた | Ctrl+Z でアンドゥして手動削除する |
