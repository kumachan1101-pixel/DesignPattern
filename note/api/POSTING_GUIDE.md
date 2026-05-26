# note.com 記事投稿手順（最新版）

最終更新: 2026-05-27

## 概要
ブラウザ直接操作（Claude in Chrome）で投稿する。Pythonスクリプト不要。

## 投稿フロー

### 1. 新規ノート作成
`https://note.com/notes/new` にnavigate

### 2. タイトル入力
- `find` でタイトルフィールド取得 → `form_input` でテキスト入力
- `computer` toolでタイプ入力も可（React管理フィールドなので `.value=` 代入NG）

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

### 4. TOC挿入（UIクリック、スクリーンショット不要）
※ ProseMirror JS直接操作は不可（pmView取得できず）
- browser_batch でまとめて実行：Ctrl+Home → Enter → ArrowUp → 「+」ボタンfindクリック → 「目次」findクリック
- TOCは必ず **h2より前・本文最上部** に挿入

### 5. カバー画像アップロード
```javascript
// file inputクリックをインターセプト
const orig = HTMLInputElement.prototype.click;
HTMLInputElement.prototype.click = function() {
  if (this.type === 'file') { window._capturedInput = this; return; }
  return orig.call(this);
};
```
- カバー画像エリアをfindでクリック → find で `window._capturedInput` のrefを取得
- `file_upload` ツールで画像をセット → 「保存」クリック
- ※ file_upload は start_task の `attachments` パラメータで画像を渡した子タスクでのみ有効

### 6. タグ設定
- 「公開に進む」をクリック
- タグ入力は `browser_batch` で一括処理（シャープ記号なしで入力 → Enter）
- ※ `#C#` などシャープ含むタグはnote側の制限で入力不可
- 「キャンセル」でエディタに戻る

### 7. 公開
- 「公開に進む」画面でタグ設定後、**「公開する」をクリック**（下書き保存ではなく即時公開）

## スクリーンショット方針
- 途中の確認スクリーンショットは **不要**
- 操作の成否はJSの戻り値・findの結果で判断
- **最後の1枚のみ** 撮影して完了確認

## 予約投稿について
- **noteプレミアム会員限定機能**
- 非プレミアム会員は下書き保存のみ対応

## 注意事項
- セッションのターン制限対策：工程を分ける場合
  - タスク1：本文ペースト＋タイトル＋TOC
  - タスク2：カバー画像（attachments経由で別タスク起動）
  - タスク3：タグ設定＋下書き保存
- 複数タスク同時実行はブラウザ競合するため避ける

## 投稿済み記事
- n68088c41faf0（ソフトウェア設計・まず動かす）
- n9edfbfc70ea3（非同期処理・責任分離）
- ne2a9b0b0b465（インターフェースの粒度）
- n7a602490a2a0（設計の見積もり）
- ne3788e81602b（設計資料の管理）
- na9eb9f7586ba（エラー設計・責任境界）
- n6a6545db6a2c（フォーマットと目的）
