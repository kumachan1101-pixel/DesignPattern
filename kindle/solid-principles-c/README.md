# C言語版 SOLID原則 — 最新スナップショット

先に特定した`C:\Users\kumac\OneDrive\デスクトップ\antigravity\BookProject`から、2026-03-29に最新EPUBを生成した原稿・入力画像・生成機構・EPUBだけを選別した保存先です。

バックアップ、旧ビルド、校正用スクリプト、MOBI/PDF、生成済みコード画像・Mermaid画像は含めていません。コード画像とMermaid画像はビルド時に再生成されます。

## 登録内容

| パス | 内容 |
|---|---|
| `02_章別/*.md` | ビルドが読む最終章別Markdown 33ファイル |
| `02_章別/solid_design.jpg` | あとがきのMarkdownが参照する画像 |
| `03_資料/png/chapter_01.png`〜`chapter_20.png` | 各章先頭の概要スライド20枚 |
| `04_work/build_epub.py` | 最新EPUB生成本体 |
| `04_work/convert_to_standalone.py` | 結合HTMLの単体化処理 |
| `05_生成/cover.jpg` | EPUB表紙 |
| `release/book.epub` | 2026-03-29 11:56:10生成の最新EPUB |

`BookProject`側では、9個の章Markdown、`build_epub.py`、`solid_design.jpg`がGit未確定の状態でした。しかし、いずれも最新EPUBより前に更新されており、ディスク上の最新ビルド入力として使われているため、このスナップショットでは最新版として採用しています。

## EPUB再生成

### 必要なもの

- Python 3
- `Pygments`、`imgkit`、`Pillow`
- wkhtmltopdf付属の`wkhtmltoimage`
- Mermaid CLIの`mmdc`
- Calibre付属の`ebook-convert`

Python依存関係は次で導入できます。

```powershell
python -m pip install -r requirements.txt
```

### 実行

相対パスと補助スクリプトの探索を維持するため、必ず`04_work`から実行します。

```powershell
cd kindle/solid-principles-c/04_work
python build_epub.py
```

生成先は`05_生成/dist/`です。スクリプトは起動時にこの`dist`を削除して作り直しますが、`02_章別`、`03_資料/png`、`release/book.epub`は変更しません。

`build_epub.py`の`MMDC`は元環境の絶対パスを保持しています。別環境で動かす場合は、`mmdc`の場所に合わせて変更してください。

## 同一性確認

- `04_work/build_epub.py` SHA-256: `CAA854AE2571C5B4B05449B6C5B4DC1EB4DA7359D64980CEB62F830E60DA9423`
- `release/book.epub` SHA-256: `23A2A0C955EA1C87FBA6D04C569580C2EC71BE492E153831410836F83ED73BC3`
- EPUB ZIP検査: 破損なし、`mimetype=application/epub+zip`、画像727点
- `release/book.epub`は約176MBのためGit LFSで管理します。
