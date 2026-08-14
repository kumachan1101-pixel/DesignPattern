# Kindle出版パイプライン

過去のC言語SOLID本で使用した出版処理を、現在のC++原稿向けに移植したものです。
原稿のMarkdownは変更せず、出版時だけ次の順に処理します。

1. 各章の概要スライドをPNGとして用意する
2. MermaidブロックをPNGへ変換する
3. C++を含むコード／実行結果ブロックを、構文強調したPNGへ変換する
4. 長いコード画像をKindleで読める高さへ分割する
5. スライド、Mermaid、コード画像を本文へ差し戻して全章を結合する
6. HTMLからEPUB、MOBI、PDFを生成する

## 概要スライドの境界

スクリプトがスライドの文章や図を自動設計するわけではありません。NotebookLM、PowerPoint、Canvaなどで「1ページ＝1章」の概要スライドを作り、PDFへ書き出します。そのPDFを次のコマンドで章別PNGへ分割します。

```powershell
cd kindle/design-patterns
python script/build_epub.py slides --pdf "C:\path\to\chapter-overviews.pdf"
```

PDFページと章の対応順は [book.json](book.json) の `slidePageOrder` です。生成後は `publishing/slides/` のPNGを目視確認してください。PNGを直接作成する場合も、`chapter01.png`のように同じ名前で配置すれば利用できます。ここに置いた元画像はGitで管理し、`publishing/dist/`の生成物は管理しません。

## セットアップ

Python依存関係を導入します。

```powershell
python -m pip install -r publishing/requirements.txt
```

別途、次のコマンドが必要です。

- `wkhtmltoimage`：コードHTMLのPNG化（wkhtmltopdfに同梱）
- `mmdc`：Mermaid CLI。既存の `script/setup_mermaid.sh` でも導入可能
- `ebook-convert`：Calibreに同梱。EPUB/MOBI/PDFの生成に使用

環境を変更する前に、検出結果だけ確認できます。

```powershell
python script/build_epub.py doctor
```

## 実行方法

原稿、コードブロック数、Mermaid数、未配置スライドを確認します。

```powershell
python script/build_epub.py inventory
```

HTMLまで生成します。

```powershell
python script/build_epub.py html --clean
```

EPUB、MOBI、PDFまで生成します。

```powershell
python script/build_epub.py all --clean
```

特定章の画像だけを作り直す場合は、既存キャッシュを残したまま対象を指定します。全章HTMLは常に再結合されます。

```powershell
python script/build_epub.py html --target chapter05 --force
```

`--clean`は`publishing/dist/`だけを削除します。`publishing/slides/`の元画像や`output/`の原稿は削除しません。`--clean`と`--target`を同時に指定した場合、キャッシュが無いため不足画像は全章分生成されます。

## コード画像の仕様

- Pygmentsで言語を自動選択し、`cpp`はC++、`c`はCとして構文強調する
- 背景、コメント、型、キーワード、文字列、数値、関数名の配色はSOLID本の採用色を継承する
- 最初の画像はタイトル込み19行、続きは22行を基準に分割する
- 末尾4行以下だけが孤立する場合は直前画像へ含める
- コード直前にある見出しまたは太字行を画像タイトルとして使う
- `mermaid`以外のフェンス（`cpp`、`text`、`csv`など）は、表示崩れを避けるため画像化する

設定値、章順、PDFページ対応、表紙、出力形式は [book.json](book.json) で変更できます。
