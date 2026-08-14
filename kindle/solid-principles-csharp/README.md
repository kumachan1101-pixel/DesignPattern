# C#言語版 SOLID原則 — 最新スナップショット

`C:\Users\kumac\OneDrive\デスクトップ\hiroaki\kindle\SOLID原則`から、最終更新されたC#版だけを選別した保存先です。旧版の`整形*`、`old`、テスト用`bin/obj`、中間HTMLは含めていません。

## 登録内容

すべて `latest/` にまとめています。Pandocコマンドをそのまま実行できるよう、参照ファイルを同じ階層に置いています。

| ファイル | 用途 | 元ファイルの更新日時 |
|---|---|---|
| `latest/solid.md` | 最終Markdown原稿 | 2026-03-29 10:03:33 |
| `latest/book.epub` | 最新EPUB | 2026-03-29 10:03:40 |
| `latest/epub.css` | EPUB用CSS | 2025-08-09 13:26:52 |
| `latest/pandoc_cmd.txt` | EPUB／HTML生成コマンド | 2025-07-27 15:08:07 |
| `latest/cover.jpg` | `solid.md`が参照する画像 | 2026-03-08 10:21:09 |

## EPUB再生成

Pandocを導入し、このフォルダで実行します。`pandoc_cmd.txt`に残るEPUBコマンドのうち、後に記載された目次深度3のコマンドを最新として使用します。

```powershell
cd kindle/solid-principles-csharp/latest
pandoc -o book.epub --toc --toc-depth=3 -f markdown -t epub --css=epub.css --wrap=preserve solid.md
```

HTMLを確認する場合は次を実行します。生成される`solid.html`は中間確認物のためGit管理しません。

```powershell
pandoc -s solid.md -o solid.html
```

## 同一性確認

- `solid.md` SHA-256: `7DB54096BA8A508D042BBF9893E57DA8CDB20FC62CA3F5D829356872A3A0C569`
- `book.epub` SHA-256: `98E3549C9513BC27F7D5BA69131370DB058DE0E36E82D909E0307B7F78EC203E`
- EPUB ZIP検査: 破損なし、`mimetype=application/epub+zip`
