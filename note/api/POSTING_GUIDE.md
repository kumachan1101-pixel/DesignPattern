# note.com 記事投稿手順（最新版）

最終更新: 2026-08-27

## 概要

ブラウザ直接操作（JavaScript実行 + スクリーンショット経由の画像アップロード）で投稿する。
Pythonスクリプト・file_uploadツール・外部APIは不要。
**全工程20〜40ターン想定（画像あり）。**

このガイドはAIエージェント非依存で書かれています。「何をするか」が主役で、Claude固有のツール名は補足扱いです。

---

## 前提条件

- `C:\Users\kumac\Downloads\cors_server.py` が存在する（後述）
- `C:\Users\kumac\Downloads\start_server.bat` が存在する（後述）
- 投稿したい画像が `C:\Users\kumac\Downloads\` に存在する
- ブラウザがnote.comにログイン済み

---

## 準備ファイル

### cors_server.py（Downloads/に設置済み）

```python
from http.server import HTTPServer, SimpleHTTPRequestHandler
import os

class CORSHandler(SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Private-Network', 'true')
        self.send_header('Access-Control-Allow-Methods', 'GET, OPTIONS')
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Private-Network', 'true')
        self.send_header('Access-Control-Allow-Methods', 'GET, OPTIONS')
        self.end_headers()

    def log_message(self, format, *args):
        pass  # suppress logs

os.chdir(r'C:\Users\kumac\Downloads')
HTTPServer(('', 8989), CORSHandler).serve_forever()
```

### start_server.bat（Downloads/に設置済み）

```batch
@echo off
cd /d "C:\Users\kumac\Downloads"
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8989 " ^| findstr LISTENING') do taskkill /PID %%a /F >nul 2>&1
timeout /t 1 /nobreak >nul
python cors_server.py
```

---

## 投稿フロー

### Step 0. 本文HTML準備

本文HTMLは **タスクプロンプトに直接含める**。
先頭に `<table-of-contents></table-of-contents>` を付けることで目次が自動挿入される。

```html
<table-of-contents></table-of-contents>
<h2>見出し1</h2>
<p>本文...</p>
```

- **AIによるHTML生成はNG**（convert.jsで生成したものをそのまま使うこと）
- 本文内の画像位置（どのh2の後か）を事前に決めておく

---

### Step 1. ローカルサーバー起動

**なぜ必要か**: note.comのHTTPSページからlocalhost画像を取得するにはCORS+PNAヘッダーが必要。
ただし、ブラウザがlocalhostに**ナビゲート**する分には制限なし。これを利用する。

1. File Explorer で `C:\Users\kumac\Downloads\start_server.bat` をダブルクリック実行
2. コマンドプロンプトウィンドウが起動したまま（閉じずに）残ればOK
3. ポート8989が既に使用中の場合、batが自動でkillしてから再起動する

---

### Step 2. 画像をブラウザ経由でキャプチャ（スクリーンショット方式）

**これが画像アップロードの核心。** file_uploadツールはnote.comでは動作しない（2026-08-27確認）。
代わりに、ブラウザをlocalhostに向けてスクリーンショットを撮り、そのIDで画像を挿入する。

1. ブラウザを `http://localhost:8989/カバー画像ファイル名` に移動
2. そのタブのスクリーンショットを撮る → スクリーンショットIDを記録（例: ss_1234）
3. ブラウザを `http://localhost:8989/本文画像ファイル名` に移動
4. スクリーンショット撮影 → IDを記録（例: ss_5678）

---

### Step 3. note.com新規作成

ブラウザを `https://note.com/notes/new` に移動。

---

### Step 4. タイトル入力

```javascript
const ta = document.querySelector('textarea[name="title"], textarea[placeholder*="タイトル"]');
const nativeSetter = Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype, 'value').set;
nativeSetter.call(ta, 'タイトル文字列');
ta.dispatchEvent(new Event('input', {bubbles: true}));
```

---

### Step 5. 本文ペースト（ClipboardEvent方式）

```javascript
const html = '<table-of-contents></table-of-contents><h2>見出し</h2><p>本文</p>';
const editor = document.querySelector('.ProseMirror');
editor.focus();
const dt = new DataTransfer();
dt.setData('text/html', html);
editor.dispatchEvent(new ClipboardEvent('paste', {clipboardData: dt, bubbles: true, cancelable: true}));
```

- HTMLの先頭に table-of-contents タグがあれば自動的に目次として認識される
- ペースト後確認: `document.querySelector('.ProseMirror').firstChild?.nodeName` → TABLE-OF-CONTENTS ならOK

---

### Step 6. カバー画像挿入

#### 6a. クリックを横取りしてメニューを開く

```javascript
HTMLInputElement.prototype.click = function() {};

function fireFullClick(el) {
  const rect = el.getBoundingClientRect();
  const x = rect.left + rect.width/2, y = rect.top + rect.height/2;
  const opts = {bubbles:true,cancelable:true,view:window,clientX:x,clientY:y};
  ['pointerdown','mousedown','pointerup','mouseup','click'].forEach(t =>
    el.dispatchEvent(t.startsWith('p') ? new PointerEvent(t,opts) : new MouseEvent(t,opts)));
}

const btn = document.querySelector('[class*="coverImage"] button, [class*="cover"] button');
if(btn) fireFullClick(btn);
```

#### 6b. メニューから「アップロード」を選ぶ

メニューが表示されたら「画像をアップロード」項目をクリック。file inputが現れる。

#### 6c. スクリーンショットIDで画像をアップロード

upload_imageツールで、Step 2で記録したカバー画像のスクリーンショットIDを指定する。

---

### Step 7. 本文内画像挿入

1. エディタ内で画像を挿入したい位置にカーソルを置く
2. 「+」ボタン → 「画像」を選択
3. Step 2で記録した本文画像のスクリーンショットIDで upload_image を実行

---

### Step 8. Kindleカード追加

エディタ末尾にAmazon URLを貼るだけでカード化される。ClipboardEventで追記するか視覚操作でペースト。

---

### Step 9. 公開ページへ遷移

```javascript
function fireFullClick(el) {
  const rect = el.getBoundingClientRect();
  const x = rect.left + rect.width/2, y = rect.top + rect.height/2;
  const opts = {bubbles:true,cancelable:true,view:window,clientX:x,clientY:y};
  ['pointerdown','mousedown','pointerup','mouseup','click'].forEach(t =>
    el.dispatchEvent(t.startsWith('p') ? new PointerEvent(t,opts) : new MouseEvent(t,opts)));
}
const btn = [...document.querySelectorAll('button')].find(b => b.textContent.includes('公開に進む'));
fireFullClick(btn);
```

URLが /publish/ に変わればOK。

---

### Step 10. タグ設定（/publish/ ページ）

```javascript
async function addTag(tagText) {
  const input = document.querySelector('input[placeholder*="タグ"], input[placeholder*="tag"]');
  if(!input) return "input not found";
  input.focus();
  const nativeSetter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
  nativeSetter.call(input, tagText);
  input.dispatchEvent(new Event('input', {bubbles: true}));
  await new Promise(r => setTimeout(r, 500));
  input.dispatchEvent(new KeyboardEvent('keydown', {key: 'Enter', keyCode: 13, bubbles: true}));
  input.dispatchEvent(new KeyboardEvent('keyup', {key: 'Enter', keyCode: 13, bubbles: true}));
  await new Promise(r => setTimeout(r, 500));
  return "added: " + tagText;
}
await addTag('AI');
await addTag('設計');
```

- form_inputは不要。このJS関数で確実に入力できる（2026-08-27確認済み）

---

### Step 11. 投稿

```javascript
const btn = [...document.querySelectorAll('button')].find(b => b.textContent.includes('投稿する'));
fireFullClick(btn);
```

---

## 再現性評価（2026-08-27）

| 手順 | 安定性 | 備考 |
|---|---|---|
| タイトル入力 | 安定 | nativeSetterで確実 |
| 本文ペースト | 安定 | ClipboardEvent方式 |
| TOC挿入 | 安定 | HTMLにtable-of-contentsタグを含めるだけ |
| カバー画像 | 安定 | localhost→スクリーンショット→upload_image |
| 本文画像 | 安定 | localhost→スクリーンショット→upload_image |
| Kindleカード | 安定 | Amazon URLペーストのみ |
| タグ設定 | 安定 | nativeSetter+KeyboardEventEnter |
| 投稿 | 安定 | fireFullClick |
| サーバー起動 | 条件付き | TextInputHostが前面に来ると妨害される場合あり |

**既知リスク**: Windows IMEパネル（TextInputHost）がstart_server.bat実行を妨害することがある。
その場合はタスクを停止して手動でbatを実行してから再試行。

---

## スクリーンショット方針

- **途中確認スクリーンショットは不要**（JS戻り値で判断）
- **最大2枚**: 画像キャプチャ用（localhost表示）、完了確認用
- 画像が複数ある場合はStep 2をその分繰り返す（各1枚）

---

## 旧手順との差異（2026-08-27更新）

| 項目 | 旧手順 | 新手順（確定） |
|---|---|---|
| 画像アップロード | file_upload（動作せず） | localhost→SS→upload_image |
| TOC挿入 | Ctrl+Home→+ボタン→目次 | HTML先頭にtable-of-contentsタグ |
| タグ入力 | form_input | nativeSetter+KeyboardEvent Enter |
| post_article.js | 使用 | 不要（全JS直接実行） |

---

## 注意事項

- **本文HTMLはタスクプロンプトに直接含めること**
- **複数タスク同時実行はブラウザ競合するため避ける**
- **一時保存（Ctrl+S）は公開に反映されない**。必ず「投稿する」まで完走すること
- **base64のチャンク化・分割は禁止**

---

## 投稿済み記事

- n68088c41faf0（ソフトウェア設計・まず動かす）
- n9edfbfc70ea3（非同期処理・責任分離）
- ne2a9b0b0b465（インターフェースの粒度）
- n7a602490a2a0（設計の見積もり）
- ne3788e81602b（設計資料の管理）
- na9eb9f7586ba（エラー設計・責任境界）
- n6a6545db6a2c（フォーマットと目的）
- naf1a3400718b（AIへの指示より検証できる出力をどう残すか）旧手順
- n2e4458e311c2（AIへの指示より、検証できる出力をどう残すか）2026-08-27 新手順で投稿確認済み

---

## テスト結果

- 2026-05-27: 旧手順テスト（file_upload方式）18ターン達成（タグなし）
- 2026-08-27: **新手順テスト（localhost→SS→upload_image方式）全要素込みで投稿成功**
  タイトル・本文・目次・カバー画像・本文画像・Kindleカード×2・タグ3個・公開まで完走。
  公開URL: https://note.com/rosy_flax9582/n/n2e4458e311c2
