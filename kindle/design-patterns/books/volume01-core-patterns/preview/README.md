# PDFプレビュー

## 注意：ここにあるPDFは、最新の原稿ではありません

`volume01-preview.pdf` は、**初版の矛盾修正より前**に組版したものです（554ページ）。
リモート環境から Git LFS の保存先へ接続できず（`lfs.github.com` が拒否される）、
差し替えられていません。

最新の原稿から生成したPDFは **543ページ** で、次の内容を含みます。

- 章タイトルを `#` へ上げ、EPUBの目次が7項目から68項目になった状態
- 奥付（免責・商標・著作権）
- 第1章・第2章・第3章・第0章の矛盾修正10件

## 手元で生成する

プロジェクトルート `kindle/design-patterns` で次を実行します。

```
python script/build_epub.py --config books/volume01-core-patterns/publishing/book.json all --clean
```

`publishing/dist/` に次が出力されます（dist はGit管理対象外）。

| ファイル | サイズ | 内容 |
|---|---|---|
| `book.epub` | 74MB | KDPへの入稿候補 |
| `book.mobi` | 40MB | 旧端末での確認用 |
| `book.pdf` | 77MB / 543ページ | A5サイズの組版確認用 |
| `book.html` | 712KB | 結合後の本文 |

コード298ブロックを327枚、Mermaid 49図を画像として掲載します。

Windows環境で `wkhtmltoimage` と `ebook-convert` が未導入の場合は、
先に `python script/build_epub.py doctor` で確認してください。
