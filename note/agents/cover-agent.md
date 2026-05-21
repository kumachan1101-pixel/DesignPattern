# agents/cover-agent.md — カバー画像生成（STEP 4・自動実行）

## 役割

draft-agent 完了後に自動実行される。
記事タイトル・テーマから SVG を生成し、Python で PNG に変換して
`output/covers/cover-NNN.png` に保存する。

---

## 受け取る引数

draft-agent の完了 JSON：

- `title` : 記事タイトル
- `keywords` : キーワードリスト
- `file` : 記事ファイルパス（記事番号の取得に使う）

---

## 実行手順

### ステップ1：準備

以下を読む：

1. `skills/cover-design.md`（カラーパレット・レイアウトルール）
2. draft-agent の完了 JSON

### ステップ2：デザイン方針を決める

`cover-design.md` のテーマ別カラーパレットから背景色・アクセントカラーを選ぶ。
タイトルの文字数を確認して1行 or 2行（`<tspan>` 改行）を決める（目安：20文字/行）。

### ステップ3：SVG を生成して書き出す

`cover-design.md` の SVG 雛形をベースに、タイトル・サブテキストを埋め込んだ
SVG を生成し、`output/covers/cover-NNN.svg` に書き出す。
（NNN は記事番号に合わせる）

仕様：幅 1280px、高さ 670px（16:9）

### ステップ4：SVG を PNG に変換する（自動実行）

以下の Bash コマンドを実行する：

```bash
pip install cairosvg -q && \
python3 -c "
import cairosvg
cairosvg.svg2png(
    url='note/output/covers/cover-NNN.svg',
    write_to='note/output/covers/cover-NNN.png',
    output_width=1280,
    output_height=670
)
print('PNG変換完了: note/output/covers/cover-NNN.png')
"
```

**cairosvg インストール失敗またはエラーの場合**：
Pillow で日本語フォント指定なしの代替 PNG を生成する：

```bash
pip install Pillow -q && \
python3 -c "
from PIL import Image, ImageDraw
import json

# カラーはcover-design.mdで決めた値を使う
bg_color = (26, 26, 46)       # #1a1a2e
accent   = (74, 158, 255)     # #4a9eff
img = Image.new('RGB', (1280, 670), bg_color)
draw = ImageDraw.Draw(img)
img.save('note/output/covers/cover-NNN.png')
print('PNG生成完了（簡易版）: note/output/covers/cover-NNN.png')
"
```

どちらも失敗した場合は `cover_png_available: false` を JSON に含め、
publish-agent へ「カバーのブラウザアップロードをスキップ」と伝える。

### ステップ5：完了報告

```json
{
  "agent": "cover-agent",
  "status": "complete",
  "cover": {
    "svg": "note/output/covers/cover-NNN.svg",
    "png": "note/output/covers/cover-NNN.png",
    "cover_png_available": true,
    "width": 1280,
    "height": 670
  },
  "next": "publish-agent（ユーザーのOKを待つ）"
}
```

完了後にユーザーへ以下を伝える：

```
記事ドラフトとカバー画像が完成しました。

📄 記事：note/output/articles/article-NNN.md
🎨 カバー：note/output/covers/cover-NNN.png

内容をご確認いただき、問題なければ「OK」または「投稿して」とお伝えください。
Note に記事を投稿し、カバー画像も自動でアップロードします。
```
