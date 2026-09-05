# 次AIへの引き継ぎ ―― 現在地と残件

最終更新：2026-09-05

## AIへ渡す指示文（そのまま貼る）

```
kumachan1101-pixel/DesignPattern のリポジトリで作業してほしい。

まず kindle/design-patterns/NEXT_AI_HANDOFF.md を全文読む。現在地と残タスクは
そこが正。次に kindle/design-patterns/CLAUDE.md を読む。執筆規約はここが最新で、
templates/ と rules/ は追随しきれていない。

守ること。
- 触ってよいのは kindle/design-patterns/ 配下だけ
- 第1冊の正本は books/volume01-core-patterns/output/ の7ファイル。
  output/ の同名章は古い供給元なので触らない
- 直したら必ず次を通し、結果をそのまま報告する。落ちたら直してから次へ進む
    python3 script/check_volume.py --config books/volume01-core-patterns/publishing/book.json
    python3 script/run_completion_gate.py
- 既存ファイルの構造を変える書き換え、ファイルの削除、新しいフォルダの作成は、
  実行前に私へ確認する
- コミットメッセージ・PR・コード内コメントに、使っているAIのモデル名を書かない

今回やってほしいのは NEXT_AI_HANDOFF.md の A節「AIがそのまま進められるもの」の
<A1などの番号>。着手前に、何をどう変えるつもりか3行で説明してほしい。
```

レビューを回させるときは、上の最後の段落を次に差し替える。

```
今回は通しレビューを1レンズ分やってほしい。
kindle/design-patterns/agents/volume-review-runbook.md を先に読むこと。
章で割らずレンズで割る、1体ずつ順に走らせる、といった前提がそこにある。

担当レンズ：<言葉／ノイズ／表と図／初読>
対象：books/volume01-core-patterns/output/ の7ファイル全部（1ファイルではない）

原稿は編集しない。reviews/agent-<レンズ名>.md にレポートだけ書く。
1件につき「原文の逐語引用／検算した結果／読者がどう困るか／直し方」の4つを書く。
検算していない指摘は書かない。判断が付かないものは保留へ回す。
見つけたそばからレポートへ書き足す（最後にまとめて書かない）。
```

## 現在地

**第1冊『分離と再結合で学ぶ C++ソフトウェア設計』の正本は
`books/volume01-core-patterns/output/` の7ファイルである。**
はじめに・第0章・第1章（Strategy）・第2章（State）・第3章（Observer）・
おわりに・奥付。`output/` の同名章は供給元として残っているが**内容は古い**ので、
第1冊を直すときにそちらを触らない（詳細は `CLAUDE.md` の「冊の構成と正本の所在」）。

- 本文ゲート（`python3 script/run_completion_gate.py`）は **PASS**
- `check_volume.py` は32観点すべて通過。クラス図の線66本もコードと一致
- 第二部（旧第9〜12章）は出版対象外。旧第2・4・5・6・8章は第2冊以降の素材

### 直近の作業（2026-09-04〜05）

**レンズ別サブエージェントによる通しレビュー**を始めた。回し方は
`agents/volume-review-runbook.md` にある。**この手順書を先に読むこと。**
章で割らずレンズで割る、1体ずつ順に走らせる、といった前提がここにある。

| レンズ | 状態 | レポート |
|---|---|---|
| 言葉（一語ずつの正確さ） | **第1章のみ完了**（23件、全件対応済み） | `reviews/agent-ch01-words.md` |
| 論理と数 | 全7ファイル完了（16件＋保留5件、全件対応済み） | `reviews/agent-logic.md` |
| ノイズ | 未着手 | ― |
| 表と図 | 未着手 | ― |
| 初読 | 未着手 | ― |

**言葉レンズは7ファイル中1ファイルしか見ていない。** 残る6ファイルへ当てるのが
最短の次の一手である。

## 残タスク

### A. AIがそのまま進められるもの

| # | 内容 | 手掛かり |
|---|---|---|
| A1 | 言葉レンズを残り6ファイルへ当てる | `agents/volume-review-runbook.md`、`agents/clarity-agent.md` |
| A2 | ノイズレンズを全7ファイルへ当てる | 同上、`CLAUDE.md`「当たり前のことを弁明しない」「編集の舞台裏を本文へ書かない」 |
| A3 | 表と図レンズを全7ファイルへ当てる | 同上、`CLAUDE.md`「図は『新しく作る』と『開いて直す』を塗り分ける」「2列の表は…」 |
| A4 | 初読レンズを全7ファイルへ当てる | 同上、`agents/readability-agent.md` |
| A5 | 概要スライドが第1冊で0枚（PUB-005） | `publishing/book.json` の `slidePageOrder`、`build_epub.py slides --pdf` |
| A6 | 矛盾検出の機械化の残り（CONTRA-009） | 検査29〜32は追加済み。`script/check_volume.py` の末尾を見て続きを足す |
| A7 | 正本3ファイルの規定欠落（CONTRA-005） | `templates/chapter-template.md` と `rules/checklist.md` に、`CLAUDE.md` へ後から入れた規約が反映されていない |
| A8 | 読みやすさ13件（READ-003〜015） | `review-tasks.md` 内。圧縮工程としてまとめて実行する計画になっている |

**A1〜A4は1体ずつ順に。並列で起動すると回数制限に当たって全体が止まる。**

### B. 著者判断が要る（AIだけでは決められない）

| # | 内容 |
|---|---|
| B1 | **刊行計画（PLAN-001）。** 第2冊以降の冊構成と収録章。ここが決まらないと B2・B4 も決まらない |
| B2 | 第2冊以降の第0章の扱い（SHRINK-011）。毎冊置くのか、共通の巻頭章にするのか |
| B3 | 分量判断（PUB-002／SHRINK-012・013）。第1冊に絞ってなお読み切れる厚さか |
| B4 | 各冊巻頭の「この本を読むための言語」10〜15頁を作るか（PLAN-002） |
| B5 | KDP出稿フォームの項目確定（PUB-007）。書名・サブタイトル・紹介文・カテゴリ・価格 |
| B6 | 第二部（旧9〜12章）のリリース単位（PLAN-003） |

### C. 著者本人でないとできない最終確認

| # | 内容 |
|---|---|
| C1 | **Kindle Previewer での端末別表示確認（PUB-009）。** 出版前の最終関門。この環境にPreviewerは無い |
| C2 | 初見読者としての通読（PUB-010） |

### D. この環境の制約

- **Git LFS が使えない。** `lfs.github.com:443` への CONNECT が 403 で弾かれる。
  LFS 追跡下のファイル（`preview/volume01-preview.pdf` など）は**このセッションから
  push できない**。PDFを更新したら、著者の手元で push する必要がある
- Kindle Previewer は無い（C1）
- `publishing/dist/` は Git 管理対象外。生成物はコミットしない

### E. 第1冊の対象外（第2冊以降で扱う）

台帳に残っているが、**第1冊の7ファイルには影響しない**もの。旧章番号なので
混乱しやすい。第1冊は旧 chapter01／chapter03／chapter07 の3章だけである。

| ID | 対象 |
|---|---|
| CONTRA-004 | 旧第6章・第9章の実行結果ラベル |
| CONTRA-006 | 旧第4章の「利用開始」 |
| CONTRA-010 | 旧第10章の `BatchExecutor` |
| CONTRA-011 | 旧第9章の `TicketStatus` |
| CONTRA-107 | 旧第5章・第2章の7-3と3-2のずれ |
| CONTRA-112 | 旧第4章の完成後クラス図 |
| PUB-004 | 実在サービス名の商標表記（第1冊は該当0件） |

## 作業の進め方

1. `agents/volume-review-runbook.md` を読む（レビューを回すなら必須）
2. `CLAUDE.md` を読む。**規約はここが最新で、`templates/` と `rules/` は
   追随しきれていない**（A7）
3. `review-tasks.md` の冒頭で、直近の著者指摘とその対応を確認する
4. 直したら必ず次を通す

```
python3 script/check_volume.py --config books/volume01-core-patterns/publishing/book.json
python3 script/run_completion_gate.py
```

本文が PASS でも、KDP入稿用成果物が完成したことは意味しない。
出版パッケージの判定は `--package` を付ける。

## 引き継ぐ側が間違えやすい点

- **第1冊を `output/` 側で直さない。** 正本は `books/volume01-core-patterns/output/`
- **エージェントの指摘をそのまま適用しない。** 全件を自分で実物に当てる。
  当たっている指摘でも原因の見立てが違うことがある（実例は runbook にある）
- **数の主張は数え直す。** 直近のレビューで見つかった16件のうち4件が
  「本文の数と、直後の表・図・コードの数が違う」だった
- **`check_volume.py` は表のセル幅も見る。** 指摘を反映して表を長くすると落ちる。
  落ちたセルは名前を外すか、内容を表の外の一文へ出す
- **`FAIL: Mermaid rendering` はタイムアウトのことがある。**
  `script/check_mermaid.py` を単体で通して全図が描けるなら原稿側の問題ではない
