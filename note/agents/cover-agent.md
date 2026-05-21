# agents/cover-agent.md — カバー画像生成（STEP 4・自動実行）

## 役割

Gemini にカバー画像を生成させ、ユーザーが確認後に画像を保存する。
ダウンロードと Note へのアップロードは Claude が自動で行う。

> ⚠️ ブラウザ操作を使用するため、ローカルの Claude Desktop で実行すること。

---

## ⚠️ 通信量節約の原則

| ❌ 禁止 | ✅ やること |
|:---|:---|
| 各ステップでスクリーンショット | 生成確認の1枚のみ |
| get_page_text 全体取得 | find で必要な要素だけ取得 |
| wait を長くとりすぎる | 生成中は wait 20秒、それ以外は wait 3秒 |

---

## 実行手順

### ステップ1：画像生成プロンプトを作る

記事タイトル・テーマから以下の形式でプロンプトを生成する：

```
Note記事のカバー画像を作成してください。

【条件】
- サイズ：横長（16:9）
- テーマ：{記事のテーマ}
- スタイル：ダークトーン（ネイビー・ブルー系）、プロフェッショナル、テクノロジー感のある図解イラスト
- 画像内にテキストやラベルを入れる（日本語で）
- 左右の対比構造（問題 vs 解決）または中央に象徴的なビジュアルを配置
- コード・クラス図・ノード・接続線などソフトウェア設計を連想させる要素を含む
- アクセントカラー：{テーマに合わせてオレンジ/赤/グリーンから選ぶ}
```

### ステップ2：Gemini を開いてプロンプトを送信する

1. `tabs_create_mcp` で新しいタブを作成する
2. `https://gemini.google.com` に移動する（wait 3秒）
3. ログイン済みであることを確認する（未ログインならユーザーに通知して停止）
4. テキスト入力欄にプロンプトをペーストして送信する
5. 画像生成が完了するまで待つ（wait 20秒）

### ステップ3：生成画像をユーザーに確認してもらう

スクリーンショットを1枚撮り、以下をユーザーに伝える：

```
カバー画像が生成されました。スクリーンショットをご確認ください。
問題なければ「OK」と、修正が必要であれば内容をお伝えください。
```

- **「OK」** → ステップ4へ進む
- **修正依頼** → Gemini にフォローアップを送信して再生成（wait 20秒）→ 再度確認

### ステップ4：画像をダウンロードして保存する

以下の順で試みる。成功したらステップ5へ。

#### 方法A：JavaScript で base64 変換して保存

```javascript
// 生成された画像要素を取得
const img = Array.from(document.querySelectorAll('img')).find(
  i => i.naturalWidth > 400 && i.src.length > 50
);
if (!img) { 'not found'; }
else {
  const canvas = document.createElement('canvas');
  canvas.width = img.naturalWidth;
  canvas.height = img.naturalHeight;
  canvas.getContext('2d').drawImage(img, 0, 0);
  canvas.toDataURL('image/png');
}
```

取得した base64 文字列を Python で保存する：

```bash
python3 -c "
import base64, sys
data = sys.stdin.read().split(',')[1]
with open('note/output/covers/cover-NNN.png', 'wb') as f:
    f.write(base64.b64decode(data))
print('保存完了')
"
```

#### 方法B：Gemini のダウンロードボタンを使う

```
find: "ダウンロード" または find: "Download" ボタンをクリック
→ ブラウザのダウンロードフォルダに保存される
→ computer ツールで note/output/covers/cover-NNN.png に移動する
```

#### 方法C：画像 URL を取得して Python でダウンロード

```javascript
const img = Array.from(document.querySelectorAll('img')).find(
  i => i.naturalWidth > 400
);
img ? img.src : 'not found';
```

```bash
python3 -c "
import urllib.request
urllib.request.urlretrieve('IMAGE_URL', 'note/output/covers/cover-NNN.png')
print('保存完了')
"
```

いずれの方法も失敗した場合は、ユーザーに手動保存を依頼し、
保存パスだけ確認してステップ5へ進む。

### ステップ5：完了報告

```json
{
  "agent": "cover-agent",
  "status": "complete",
  "cover": {
    "file": "note/output/covers/cover-NNN.png",
    "source": "gemini",
    "user_approved": true,
    "cover_png_available": true
  },
  "next": "publish-agent"
}
```
