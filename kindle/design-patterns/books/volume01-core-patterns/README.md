# 第1冊：分離と再結合の基本構造

既存原稿を変更せず、出版対象だけを分離した第1冊の作業フォルダです。

## 収録順と章番号

ファイル名の先頭の番号が、そのまま本へ結合する順です。

| 掲載順 | このフォルダのファイル | コピー元（旧一枚本） |
|---|---|---|
| はじめに | `output/01-preface.md` | `../../output/chapter00_1.md` |
| 第0章 | `output/02-chapter00.md` | `../../output/chapter00_2.md` |
| 第1章 Strategy | `output/03-chapter01.md` | `../../output/chapter01.md` |
| 第2章 State | `output/04-chapter02.md` | `../../output/chapter03.md` |
| 第3章 Observer | `output/05-chapter03.md` | `../../output/chapter07.md` |
| おわりに | `output/06-epilogue.md` | `../../output/epilogue.md` |
| 奥付 | `output/07-colophon.md` | 分冊で新規作成 |

**コピー元はすでに古い。** 初版に向けた修正はすべてこのフォルダ側へ入れてある。

## この3章を選ぶ理由

三つとも、契約を境界に具体を分離して再結合します。ただし、再結合後の動きが異なります。

- Strategyは、利用時に選んだルールへ処理を委譲します。
- Stateは、現在状態の変化に伴って委譲先が切り替わります。
- Observerは、一つの変化を登録済みの複数の相手へ伝えます。

この違いにより、読者は「インターフェースを作る」という手段ではなく、何が変わり、誰が選び、いつ切り替わり、何件へ伝えるかという目的から構造を選べます。

## 編集方針

- コピー元の原稿は変更しません。
- このフォルダ内の原稿だけで章番号、章間参照、目次、章数を整合させます。
- 内容を修正する場合も、このフォルダを第1冊の正本として進めます。
- 元の第2・4〜6・8〜12章は、将来の別冊候補として元の場所に保持します。

## 出版設定

プロジェクトルート `kindle/design-patterns` で次を実行します。

```powershell
python script/build_epub.py --config books/volume01-core-patterns/publishing/book.json inventory
```
