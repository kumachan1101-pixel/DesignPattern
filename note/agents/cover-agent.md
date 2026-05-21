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

### ステップ4：Pillow で PNG を直接生成する（自動実行）

SVG 経由ではなく Pillow で直接 PNG を生成する。
（cairosvg は日本語フォントを正しく描画できないため使用しない）

日本語フォント：`/usr/share/fonts/opentype/ipafont-gothic/ipag.ttf`

```bash
pip install Pillow -q && python3 << 'PYEOF'
from PIL import Image, ImageDraw, ImageFont

# cover-design.md のテーマ別カラーから選んだ値を使う
W, H   = 1280, 670
BG     = (26, 26, 46)     # テーマに合わせて変更
ACCENT = (74, 158, 255)   # テーマに合わせて変更
WHITE  = (255, 255, 255)
SUBCLR = (176, 184, 200)
CREDIT = (108, 122, 141)

img  = Image.new("RGB", (W, H), BG)
draw = ImageDraw.Draw(img)

font_path = "/usr/share/fonts/opentype/ipafont-gothic/ipag.ttf"
f_title  = ImageFont.truetype(font_path, 58)
f_sub    = ImageFont.truetype(font_path, 32)
f_credit = ImageFont.truetype(font_path, 24)

# 装飾円（半透明は Pillow では RGBA レイヤーで対応）
overlay = Image.new("RGBA", (W, H), (0,0,0,0))
od = ImageDraw.Draw(overlay)
od.ellipse([(-120,-120),(300,300)], fill=(*ACCENT, 20))
od.ellipse([(1050,450),(1380,780)], fill=(*ACCENT, 15))
img.paste(Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB"))

draw = ImageDraw.Draw(img)
draw.line([(100, H//2),(W-100, H//2)], fill=(*ACCENT, 80), width=1)

# タイトル行（最大4行、1行20文字目安で分割）
lines = [
    "【ソフトウェア設計】",   # 1行目はアクセントカラー
    "（タイトル1行目）",
    "（タイトル2行目）",
]
line_h = 72
start_y = (H - line_h * len(lines)) // 2 - 30
for i, line in enumerate(lines):
    bbox = draw.textbbox((0,0), line, font=f_title)
    x = (W - (bbox[2]-bbox[0])) // 2
    color = tuple(ACCENT) if i == 0 else WHITE
    draw.text((x, start_y + i * line_h), line, font=f_title, fill=color)

# サブテキスト
sub = "デザインパターン ／ ソフトウェア設計"
bbox = draw.textbbox((0,0), sub, font=f_sub)
draw.text(((W-(bbox[2]-bbox[0]))//2, start_y + line_h*len(lines)+24), sub, font=f_sub, fill=SUBCLR)

# 著者クレジット
draw.text((60, H-48), "note.com/kumachan1101", font=f_credit, fill=CREDIT)

img.save("note/output/covers/cover-NNN.png")
print("PNG生成完了")
PYEOF
```

失敗した場合は `cover_png_available: false` を JSON に含め、
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
