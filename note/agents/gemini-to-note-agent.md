# agents/gemini-to-note-agent.md
# GeminiのURLからNote記事を下書き保存するエージェント

---

## 役割

指定されたGeminiのURLにある記事コンテンツをコピーし、
Noteに下書き状態で投稿する。

---

## 受け取る引数

- `gemini_url` : GeminiのURL（以下2種類に対応）
  - Gem URL：`https://gemini.google.com/gem/ab22a645b92d/64716de513a74bbc`
  - Share URL：`https://g.co/gemini/share/xxxxxxx` または `https://gemini.google.com/share/xxxxxxx`

---

## 固定設定値

| 設定項目 | 値 |
|:---|:---|
| Note投稿URL | https://note.com/notes/new |

---

## ⚠️ 通信量節約の原則

| ❌ 禁止 | ✅ やること |
|:---|:---|
| 各ステップでスクリーンショット | 保存後の1枚のみ |
| get_page_text / read_page | find で目的の要素だけ取得 |
| ペースト後のDOM直接書き換え | ペースト前にクリップボードをクリーニング |
| wait を長くとりすぎる | wait 3秒を基本、ペーストのみ wait 8秒 |

---

## 実行手順

### ステップ1：記事コンテンツをコピーする

1. ブラウザで `gemini_url` に移動する（wait 3秒）
2. URLが `gemini.google.com/share/` または `g.co/gemini/share/` の場合 → **Share URLフロー**へ
   URLが `gemini.google.com/gem/` の場合 → **Gem URLフロー**へ

#### Gem URLフロー
1. ページを最下部までスクロールして応答末尾を表示する
2. 応答ブロック下部の **📋アイコン（コピーボタン）** を `find` で取得してクリック
   - ✅ `find: "コピーボタン 応答をコピー"` → クリック
   - ❌ 「コピー」ボタン（ページ上部）はURL/タイトルをコピーするため使わない
3. ページ上部のタイトルテキストを `find` で取得して記録する
4. → **ステップ2**へ（通常通り）

#### Share URLフロー
1. `javascript_tool` でコンテンツを抽出してtextareaにセットする：

```javascript
const msgEl = document.querySelector('message-content');
const text = msgEl ? msgEl.innerText : '';
const lines = text.split('\n');

// タイトル行（先頭）を記録してから削除
const titleLine = lines[0];
const withoutTitle = lines.slice(1);

// コードブロックラベル行を削除
const labels = new Set([
  'plaintext', 'javascript', 'typescript', 'python', 'bash', 'shell',
  'json', 'xml', 'css', 'html', 'sql', 'cpp', 'c++', 'java', 'go',
  'ruby', 'c#', 'php', 'kotlin', 'swift', 'rust', 'scala', 'yaml',
  'markdown', 'diff', 'text', 'txt'
]);
const cleaned = withoutTitle.filter(line => !labels.has(line.trim().toLowerCase()));

// 一時textareaを作成して選択状態にする
const ta = document.createElement('textarea');
ta.id = '__copy_area';
ta.value = cleaned.join('\n');
ta.style.cssText = 'position:fixed;top:10px;left:10px;width:400px;height:200px;z-index:99999;';
document.body.appendChild(ta);
ta.select();
`title: ${titleLine} | lines: ${lines.length}→${cleaned.length}`;
```

2. タイトル（`titleLine`の値）を記録する
3. `computer` ツールでtextareaをクリック → `Ctrl+A` → `Ctrl+C`
4. textareaを削除する：

```javascript
document.getElementById('__copy_area')?.remove(); 'removed';
```

5. → **ステップ2をスキップ**してステップ3へ（クリーニング済みのため）

---

### ステップ2：クリップボードを事前クリーニングする

コピー直後（Geminiページ上で）クリップボードをクリーニングする。
**Gem URLフローのみ実行。Share URLフローはステップ1で完了済みのためスキップ。**

⚠️ `navigator.clipboard.writeText()` はユーザー操作なしではタイムアウトする。必ず以下の textarea方式を使うこと。

```javascript
// 1. クリップボードから取得（readTextは権限エラーになることがある）
//    → エラーなら後述のフォールバックへ
const text = await navigator.clipboard.readText();
const lines = text.split('\n');
const withoutTitle = lines.slice(1);
const labels = new Set([
  'plaintext', 'javascript', 'typescript', 'python', 'bash', 'shell',
  'json', 'xml', 'css', 'html', 'sql', 'cpp', 'c++', 'java', 'go',
  'ruby', 'c#', 'php', 'kotlin', 'swift', 'rust', 'scala', 'yaml',
  'markdown', 'diff', 'text', 'txt'
]);
const cleaned = withoutTitle.filter(line => !labels.has(line.trim().toLowerCase()));

// 2. textarea方式で書き込み（clipboard.writeText は使わない）
const ta = document.createElement('textarea');
ta.id = '__copy_area2';
ta.value = cleaned.join('\n');
ta.style.cssText = 'position:fixed;top:10px;left:10px;width:400px;height:200px;z-index:99999;';
document.body.appendChild(ta);
ta.select();
`ready: ${cleaned.length} lines`;
```

その後、`computer` ツールでtextareaをクリック → `Ctrl+A` → `Ctrl+C` → textareaを削除：

```javascript
document.getElementById('__copy_area2')?.remove(); 'removed';
```

> **もし clipboard.readText() が権限エラーになった場合：**
> このステップをスキップして次へ進む。ペースト後にステップ6-Bのフォールバックで対処する。

---

### ステップ3：Note新規記事を開く

1. `tabs_create_mcp` で新しいタブを作成する
2. `https://note.com/notes/new` に移動（wait 3秒）

---

### ステップ4：タイトルを入力する

```
find: タイトル入力欄（プレースホルダー「記事タイトル」）
form_input: ステップ1で記録したタイトルを入力
```

---

### ステップ5：目次を挿入する

1. 本文エリア（タイトル下）をクリックしてカーソルを置く（wait 1秒）
2. `/` のみ入力して wait 1秒
3. パレットから「目次」を `find` でクリック
   - パレットが出ない場合：本文エリアをクリックし直して再試行

---

### ステップ6-A：本文をペーストする（クリーニング済みの場合）

1. 目次コンポーネントの下の行をクリック
2. `Ctrl+V` でペーストする（wait 8秒）

ステップ2が成功していれば、タイトル行・コードラベルはすでに除去されている。
スクリーンショットは不要。そのまま次のステップへ進む。

---

### ステップ6-B：フォールバック（クリーニングがスキップされた場合のみ）

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

### ステップ7：タグを入力する

```
「公開に進む」ボタンをクリック
→ タグ入力欄に1タグ入力 → Enter（3〜5タグ分繰り返す）
→ 「キャンセル」で編集画面に戻る
```

タグ候補：`ソフトウェア設計 / デザインパターン / プログラミング / エンジニア / AI`

---

### ステップ8：下書き保存して完了報告する

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
| Share URLで📋コピーボタンが見つからない | Share URLフロー（ステップ1のJS抽出）を使う |
| clipboard API が権限エラー | ステップ2をスキップしてステップ6-Bを実行 |
| clipboard.writeText() がタイムアウト | textarea方式（作成→クリック→Ctrl+C）を使う |
| 「コピー」ボタンでURLがペーストされた | 応答ブロック下部の📋アイコンを使う |
| NoteタブからGeminiに戻れない（Leave site?ダイアログ） | `tabs_create_mcp` で新規タブを開く |
| 目次がプレーンテキストになった | `/` のみ入力してパレット表示を確認してから「目次」を選択 |
| ペースト後にブラウザが固まる | wait 10秒待ってから操作再開 |
| コードラベル削除後に本文が壊れた | Ctrl+Z でアンドゥして手動削除する |
