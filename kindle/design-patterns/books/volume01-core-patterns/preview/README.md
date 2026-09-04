# PDFプレビュー

## 現在の公開PDF

`volume01-preview.pdf` は、現在の分冊原稿から組版した最新版です（546ページ）。
コード290ブロックを333枚、Mermaid 56図を画像として掲載しています。

PDFと原稿の一致は `volume01-preview.manifest.json` に記録しています。原稿、表紙、
`book.json`、または組版コードを変更したのにPDFを更新し忘れると、出版ゲートが
失敗します。

## 再生成して公開PDFへ反映する

プロジェクトルート `kindle/design-patterns` で次を実行します。

```powershell
python script/build_epub.py --config books/volume01-core-patterns/publishing/book.json all --clean
python script/release_artifact.py sync --config books/volume01-core-patterns/publishing/book.json
python script/run_completion_gate.py --release --package
```

`publishing/dist/` に次が出力されます（dist はGit管理対象外）。

| ファイル | サイズ | 内容 |
|---|---|---|
| `book.epub` | 約57MB | KDPへの入稿候補 |
| `book.mobi` | 約44MB | 旧端末での確認用 |
| `book.pdf` | 約52MB / 546ページ | A5サイズの組版確認用 |
| `book.html` | 約667KB | 結合後の本文 |

Windows環境で `wkhtmltoimage` と `ebook-convert` が未導入の場合は、
先に `python script/build_epub.py doctor` で確認してください。
