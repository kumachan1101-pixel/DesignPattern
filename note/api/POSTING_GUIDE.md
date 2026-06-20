# note.com 記事投稿手順（最新版）

最終更新: 2026-06-20

## 概要
ブラウザ直接操作（Claude in Chrome）で投稿する。Pythonスクリプト不要。

## 投稿フロー

### 1. 新規ノート作成
`https://note.com/notes/new` にnavigate

### 2. タイトル入力
```javascript
const titleEl = document.querySelector('textarea[placeholder="記事タイトル"]');
const titleSetter = Object.getOwnPropertyDescriptor(window.HTMLTextAreaElement.prototype, 'value').set;
titleSetter.call(titleEl, 'タイトル文字列');
titleEl.dispatchEvent(new Event('input', { bubbles: true }));
```
- セレクタはDOM調査で確認済みの安定セレクタ（`find` フォールバックは要素が本当に見つからない場合のみ）

### 3. 本文ペースト（javascript_tool 1回）
```javascript
const html = `<h2>見出し</h2><p>本文</p>`;
const editor = document.querySelector('.ProseMirror');
editor.focus();
document.execCommand('selectAll');
const dt = new DataTransfer();
dt.setData('text/html', html);
dt.setData('text/plain', editor.textContent);
editor.dispatchEvent(new ClipboardEvent('paste', {clipboardData: dt, bubbles: true, cancelable: true}));
```
- markdownの `##` → `<h2>` タグに変換してからペースト
- コードブロック → `<pre><code class="language-X">` に変換
- **`<table>` タグ禁止**（article-013で発見）: `<table><tr><td>` を含むHTMLをClipboardEventでペーストすると、ProseMirrorエディタがテーブルとして解釈せず、セル内容がすべて1つの段落に連結されてしまう（例：「コメントの内容補おうとしているもの　この処理は〇〇をしている処理の意図…」のように繋がる）。比較表・対応表は以下の形式で代替すること：
  ```html
  <p><strong>ラベル1</strong> → 値1</p>
  <p><strong>ラベル2</strong> → 値2</p>
  ```

### 4. TOC挿入（安定版：Ctrl+Shift+Down方式）
※ ProseMirror JS直接操作は不可（pmView取得できず）
※ 旧手順（カーソル位置依存）は廃止。以下の手順を使うこと。

1. 本文ペースト後、**Ctrl+Home** でエディタ先頭へ移動
2. 「**+**」ブロックボタンをクリック → 「**目次**」を選択
   - まず `find` で「+」ボタン要素を取得し JS で `element.click()`
   - `find` で見つからない場合は `computer` ツールで視覚的にクリック（フォールバック）
   - この時点でTOCがh2の直前か直後に挿入される
3. TOCがh2の**後ろ**に入った場合：h2ブロックにカーソルを置き `Ctrl+Shift+Down` でh2を下へ移動
4. JS確認：
   ```javascript
   document.querySelector('.ProseMirror').firstChild?.nodeName
   // → 'TABLE-OF-CONTENTS' になればOK
   ```

### 5. カバー画像アップロード
- **前提**: `#note-editor-eyecatch-input` はクリック前はDOMに存在しない。「画像をアップロード」クリック後に動的生成される（article-011で確認）

**確定手順（DOM調査済み）:**
1. `button[aria-label="画像を追加"]` をJS `click()`
2. 300ms 待機
3. テキスト一致で「画像をアップロード」ボタンをJS `click()` → `#note-editor-eyecatch-input` が動的生成される
4. `find({cssSelector:'#note-editor-eyecatch-input'})` → `file_upload` で画像をセット
5. computerでスクリーンショット1回 → トリムダイアログの「保存」をクリック

```javascript
document.querySelector('button[aria-label="画像を追加"]').click();
await new Promise(r => setTimeout(r, 300));
[...document.querySelectorAll('button')].find(b => b.textContent.trim().startsWith('画像をアップロード')).click();
// → find({cssSelector:'#note-editor-eyecatch-input'}) → file_upload → computerでスクリーンショット1回 → 「保存」クリック
```
- ※ `file_upload` は start_task の `attachments` パラメータで画像を渡した子タスクでのみ有効

### 6. タグ設定
- 「公開に進む」ボタン: テキスト一致で取得してJSクリック（タイトル・本文が空だとエラーモーダルが出るので先に入力すること）
  ```javascript
  [...document.querySelectorAll('button')].find(b => b.textContent.trim() === '公開に進む').click();
  ```
- タグ入力はネイティブセッター方式（`form_input` より高速。シャープ記号なし）
  ```javascript
  const tagEl = document.querySelector('input[placeholder="ハッシュタグを追加する"]');
  const tagSetter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
  tagSetter.call(tagEl, 'タグ名');
  tagEl.dispatchEvent(new Event('input', { bubbles: true }));
  ```
  - ※ タグ入力後にEnterキーでのチップ確定が**必須**（article-016で確認）: ネイティブセッター方式だけではタグがチップ化されない。computerツールでtagElにフォーカスした状態でEnterキーを送ること
  - ※ `#C#` などシャープ含むタグはnote側の制限で入力不可
- 「キャンセル」でエディタに戻る

### 7. 公開
- 「**投稿する**」ボタン: テキスト一致で取得してJSクリック（DOM調査で確認済み。「公開する」というボタンは存在しない）
  ```javascript
  [...document.querySelectorAll('button')].find(b => b.textContent.trim() === '投稿する').click();
  ```
  - computerツールでの視覚クリック不要
  - 下書き保存ではなく即時公開されることを確認

## スクリーンショット方針
- 途中の確認スクリーンショットは **不要**
- 操作の成否はJSの戻り値・findの結果で判断
- **最後の1枚のみ** 撮影して完了確認

### ペースト後の確認（ターン数節約の最重要ポイント）
- ペースト直後の反映確認は **JSで `editor.textContent.length` などを取得し、元の本文の大まかな文字数と一致するかを確認する程度**に留める
  ```javascript
  document.querySelector('.ProseMirror').textContent.length
  // → 元の本文の文字数と大まかに一致していればOK
  ```
- スクリーンショットでの目視確認をする場合も **最大1回まで**
- スクロールしながら複数回スクリーンショットを撮って細部まで確認する行為はターン数を大きく消費するため **絶対に避ける**（article-014では本文やり直しが発生しなかったにもかかわらず、確認作業だけで数十回分のツール呼び出しを消費し合計約90ターンになった）

## 予約投稿について
- **noteプレミアム会員限定機能**
- 非プレミアム会員は下書き保存のみ対応

## 注意事項
- **1タスクで全工程完結。目安20〜30ターン**（タグなし実績18ターン）
- 複数タスク同時実行はブラウザ競合するため避ける
- **本文HTMLはタスクプロンプトに直接含めること**（既存記事からの取得は30+ターン無駄になるためNG）
- **ペースト前に本文エリアをクリックしてフォーカスを確認すること**（タイトルフィールドにフォーカスが残っていると本文がタイトル欄に入る）
- 同一操作を2回失敗した場合は、リトライを続けず一度状況を報告すること（無駄なトークン消費を避ける）
- **本文HTMLに `<table>` タグを使わない**（article-013、約8ターン浪費）: note.comのProseMirrorエディタはClipboardEvent経由の `<table>` をテーブルとして解釈しないため、公開直前に発覚すると本文の削除・再ペーストという手戻りが発生する。本文HTML作成段階から `<table>` は一切使わず、比較表・対応表は `<p><strong>ラベル</strong> → 値</p>` 形式で書くこと
- **ペースト確認はJSで文字数チェックのみ、スクリーンショット最大1回**（article-014、約90ターン消費）: `<table>` タグ問題も本文やり直しも発生しなかったにもかかわらず、ペースト後の目視確認のためにスクロールしながら複数回スクリーンショットを撮り続けた結果、確認作業だけで数十回分のツール呼び出しを消費した。ペースト直後は `editor.textContent.length` をJSで取得して文字数を確認するだけにとどめ、スクリーンショットは撮らないか撮っても1回限りとすること

## 別タスク・別セッションへの引き渡し

投稿作業を別タスク・別セッションに依頼する場合、手順の要約やこのファイルへの参照だけでは元の手順を再現できない。article-011では90ターン程度の試行錯誤が発生した実例がある。

本文HTML・タイトル入力・画像アップロードの具体的な操作手順は省略せず、**確定手順を全文プロンプトに埋め込むこと**。

## 確定セレクタ一覧（DOM調査済み）

note.com は styled-components 製でCSSクラス名がビルドごとに変わり、React useId 由来の id（`:r9:` 等）も非安定なため、これらは使わない。以下の安定セレクタを使うこと。

| 要素 | セレクタ |
|:---|:---|
| タイトル | `textarea[placeholder="記事タイトル"]` |
| 本文エディタ | `.ProseMirror` |
| カバー画像「+」ボタン | `button[aria-label="画像を追加"]` |
| 「画像をアップロード」項目 | `[...document.querySelectorAll('button')].find(b => b.textContent.trim().startsWith('画像をアップロード'))` |
| カバー画像 file input | `#note-editor-eyecatch-input`（「画像をアップロード」クリック後に動的生成。クリック前はDOMに存在しない） |
| 「公開に進む」ボタン | `[...document.querySelectorAll('button')].find(b => b.textContent.trim() === '公開に進む')` |
| タグ入力欄 | `input[placeholder="ハッシュタグを追加する"]` |
| 最終公開ボタン | `[...document.querySelectorAll('button')].find(b => b.textContent.trim() === '投稿する')` |

**注意**: 「公開に進む」ボタンはタイトル・本文が空の状態でクリックするとエラーモーダルが出て遷移しない。先に両方入力してから押すこと。

## ネイティブセッター方式

タイトル・タグの入力には、`computer` ツールでのタイピングシミュレーションより高速な以下の方式が使える：

```javascript
// タイトル（textarea）
const titleSetter = Object.getOwnPropertyDescriptor(window.HTMLTextAreaElement.prototype, 'value').set;
titleSetter.call(titleEl, 'テキスト');
titleEl.dispatchEvent(new Event('input', { bubbles: true }));

// タグ（input）
const tagSetter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
tagSetter.call(tagEl, 'テキスト');
tagEl.dispatchEvent(new Event('input', { bubbles: true }));
```

本文（`.ProseMirror`、contenteditable）にはこの方式は使えない。本文は既存のClipboardEventペースト方式（ステップ3）を継続すること。

## 確定スクリプト（実行そのまま使う）

**方針**: 次回からはこのスクリプトをそのまま実行し、AIが毎回手順を考え直さない。`TITLE_TEXT`・`BODY_HTML`・`TAG_TEXT` を差し替えるだけでよい。`find` + `computer` へのフォールバックは要素が本当に見つからない場合のみに限定する。

```javascript
// ステップA: タイトル設定
const titleEl = document.querySelector('textarea[placeholder="記事タイトル"]');
const titleSetter = Object.getOwnPropertyDescriptor(window.HTMLTextAreaElement.prototype, 'value').set;
titleSetter.call(titleEl, TITLE_TEXT);
titleEl.dispatchEvent(new Event('input', { bubbles: true }));

// ステップB: 本文ペースト
const editor = document.querySelector('.ProseMirror');
editor.focus();
document.execCommand('selectAll');
const dt = new DataTransfer();
dt.setData('text/html', BODY_HTML);
dt.setData('text/plain', editor.textContent);
editor.dispatchEvent(new ClipboardEvent('paste', {clipboardData: dt, bubbles: true, cancelable: true}));

// ステップC: カバー画像アップロードのトリガー
document.querySelector('button[aria-label="画像を追加"]').click();
await new Promise(r => setTimeout(r, 300));
[...document.querySelectorAll('button')].find(b => b.textContent.trim().startsWith('画像をアップロード')).click();
// → find({cssSelector:'#note-editor-eyecatch-input'}) → file_upload → computerでスクリーンショット1回 → トリムダイアログの「保存」をクリック

// ステップD: 公開フロー
[...document.querySelectorAll('button')].find(b => b.textContent.trim() === '公開に進む').click();
await new Promise(r => setTimeout(r, 500));
const tagEl = document.querySelector('input[placeholder="ハッシュタグを追加する"]');
const tagSetter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
tagSetter.call(tagEl, TAG_TEXT);
tagEl.dispatchEvent(new Event('input', { bubbles: true }));
await new Promise(r => setTimeout(r, 300));
// ⚠️ ネイティブセッター方式だけではタグがチップ化されない（article-016で確認）。
// 必ずEnterキー送信が必要（computerツールでtagElにフォーカスした状態でEnterキーを送る）
// 最終公開（コメントアウトを解除して実行）:
// [...document.querySelectorAll('button')].find(b => b.textContent.trim() === '投稿する').click();
```

**確定事項（article-016）**: タグ入力後のEnterキーによるチップ確定は必須。ネイティブセッター + `input` イベントだけではタグがチップ化されない。computerツールでtagElにフォーカスした状態でEnterキーを送ること（`KeyboardEvent('keydown', { key: 'Enter' })` のJS dispatch では不十分な可能性があるため、computerツールのEnterキー操作を優先すること）。

## テスト結果
- 2026-05-27 手順テスト実施：本文プロンプト直接渡し方式で18ターン達成（タグなし）、公開フロー込みで20〜30ターン見込み
- 2026-06-20 article-016：確定スクリプト方式で約20ターンで完了（前回article-014の約90ターンから大幅短縮）。タイトル設定・本文ペーストを1回のJS実行にまとめる方式が完全に機能。唯一フォールバックが必要だったのはタグ入力のEnterキー確定のみ。

## 投稿済み記事
- n68088c41faf0（ソフトウェア設計・まず動かす）
- n9edfbfc70ea3（非同期処理・責任分離）
- ne2a9b0b0b465（インターフェースの粒度）
- n7a602490a2a0（設計の見積もり）
- ne3788e81602b（設計資料の管理）
- na9eb9f7586ba（エラー設計・責任境界）
- n6a6545db6a2c（フォーマットと目的）
