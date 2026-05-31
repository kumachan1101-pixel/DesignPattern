# note.com 記事投稿手順（最新版）

最終更新: 2026-05-31

## 概要
ブラウザ直接操作（Claude in Chrome）で投稿する。Pythonスクリプト不要。

## 投稿フロー

### 1. 新規ノート作成
`https://note.com/notes/new` にnavigate

### 2. タイトル入力
```javascript
const input = document.querySelector('input[placeholder*="タイトル"]');
Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value')
  .set.call(input, 'タイトル文字列');
input.dispatchEvent(new Event('input', {bubbles: true}));
```
- セレクタが合わない場合：`find` でタイトル要素を特定してから同様のJSを実行（フォールバック）

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
```javascript
// file inputクリックをインターセプト
const orig = HTMLInputElement.prototype.click;
HTMLInputElement.prototype.click = function() {
  if (this.type === 'file') { window._capturedInput = this; return; }
  return orig.call(this);
};
```
- `find` でカバー画像ボタンを取得 → JS `element.click()` で開く → find で `window._capturedInput` のrefを取得
- `file_upload` ツールで画像をセット → 「保存」クリック
- ※ file_upload は start_task の `attachments` パラメータで画像を渡した子タスクでのみ有効
- **注意①**: インターセプター設定後は必ずJS `!!window._capturedInput` で値がセットされているか確認してから `file_upload` を実行すること
- **注意②**: ページ遷移やReactの再レンダリングでインターセプターがリセットされる場合がある。カバー画像エリアをクリックした直後に `!!window._capturedInput` をチェックし、`false` なら再度インターセプターを設定してからクリックし直すこと

### 6. タグ設定
- 「公開に進む」は `find` で要素を取得してJSクリック（`element.click()`）で遷移
  ```javascript
  // findで取得した要素をJSでクリック（computerツールの視覚クリック不要）
  // find結果のelementに対して: element.click()
  ```
- タグ入力は `find` でタグ入力フィールドを取得 → `form_input` で入力（シャープ記号なし）
  - **効果**: computerツールでのクリック+タイプ方式（4タグで10ターン）から1〜2ターンに削減
- ※ `#C#` などシャープ含むタグはnote側の制限で入力不可
- 「キャンセル」でエディタに戻る

### 7. 公開
- 「公開する」ボタンは `find` で要素を取得してJSクリック（`element.click()`）で実行
  - computerツールでの視覚クリック不要
  - 下書き保存ではなく即時公開されることを確認

## スクリーンショット方針
- 途中の確認スクリーンショットは **不要**
- 操作の成否はJSの戻り値・findの結果で判断
- **最後の1枚のみ** 撮影して完了確認

## 予約投稿について
- **noteプレミアム会員限定機能**
- 非プレミアム会員は下書き保存のみ対応

## 注意事項
- **1タスクで全工程完結。目安20〜30ターン**（タグなし実績18ターン）
- 複数タスク同時実行はブラウザ競合するため避ける
- **本文HTMLはタスクプロンプトに直接含めること**（既存記事からの取得は30+ターン無駄になるためNG）
- **ペースト前に本文エリアをクリックしてフォーカスを確認すること**（タイトルフィールドにフォーカスが残っていると本文がタイトル欄に入る）

## テスト結果
- 2026-05-27 手順テスト実施：本文プロンプト直接渡し方式で18ターン達成（タグなし）、公開フロー込みで20〜30ターン見込み

## 投稿済み記事
- n68088c41faf0（ソフトウェア設計・まず動かす）
- n9edfbfc70ea3（非同期処理・責任分離）
- ne2a9b0b0b465（インターフェースの粒度）
- n7a602490a2a0（設計の見積もり）
- ne3788e81602b（設計資料の管理）
- na9eb9f7586ba（エラー設計・責任境界）
- n6a6545db6a2c（フォーマットと目的）
