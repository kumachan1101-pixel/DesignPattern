# 目次：設計思考を鍛える本（デザインパターンはおまけ）

「名前を覚える」のではなく、「考え方を身につける」ことを目的とした技術書。
1章1パターン。よく使うパターンに絞った構成。

---

## 全体構成

### はじめに・第一部

| 役割 | 内容 | ファイル | 進捗 |
|:---|:---|:---|:---|
| **はじめに** | なぜパターンを覚えても使えないのか・3つの原則 | chapter00_1.md | ✅ 完成 |
| **第一部の説明** | 7フェーズの思考プロセス・ケーブル比喩・案0〜案4 | chapter00_2.md | ✅ 完成 |
| **第1章** Strategy | 増え続ける割引ルールをどう整理するか | chapter01.md | ✅ 完成 |
| **第2章** Facade | 振り込み処理の裏側を、呼び出す側に見せない | chapter02.md | ✅ 完成 |
| **第3章** State | 状態によって変わる振る舞いをどう整理するか | chapter03.md | ✅ 完成 |
| **第4章** Template Method | 手順は同じなのに3つのクラスに書き直していないか | chapter04.md | ✅ 完成 |
| **第5章** Command | 操作を取り消せるようにするにはどうするか | chapter05.md | ✅ 完成 |
| **第6章** Decorator | 組み合わせが増えるたびにクラスを作っていないか | chapter06.md | ✅ 完成 |
| **第7章** Observer | 在庫が変わったとき、複数のシステムをどう連動させるか | chapter07.md | ✅ 完成 |
| **第8章** Factory Method | 決済手段が増えるたびに利用側も変わっていないか | chapter08.md | ✅ 完成 |

### 第二部

| 役割 | 内容 | ファイル | 進捗 |
|:---|:---|:---|:---|
| **第二部の説明** | 第一部との違い・複合問題の読み方 | chapter09_1.md | ✅ 完成 |
| **第9章** | 増え続けるルールと変わり続ける状態をどう整理するか | chapter09_2.md | ✅ 完成 |
| **第10章** | 外部連携・通知・生成が絡む複合設計 | chapter10.md | ✅ 完成 |
| **第11章** | 骨格・組み合わせ・操作履歴が絡む複合設計 | chapter11.md | ✅ 完成 |
| **第12章** | 状態変化・通知・判定ルールが絡む複合設計 | chapter12.md | ✅ 完成 |

---

## 各章の詳細（第一部）

| 章 | パターン | 変化の種類 | ドメイン | 切り口 |
|:---|:---|:---|:---|:---|
| 第1章 | Strategy | 「実行する振る舞い」が変わる | ECサイト決済計算 | A：変化の混在 |
| 第2章 | Facade | 「複雑な依存関係」を隠したい | ネット銀行の振り込み処理 | B：依存の過多 |
| 第3章 | State | 「状態」によって振る舞いが変わる | チケット予約管理 | C：状態と振る舞いの混在 |
| 第4章 | Template Method | 「処理の一部のステップ」が変わる | CSVインポート処理 | A：変化の混在 |
| 第5章 | Command | 「実行する操作」が変わる | 家計簿アプリの操作履歴 | A：変化の混在 |
| 第6章 | Decorator | 「機能の組み合わせ」が変わる | カスタマイズ注文システム | A：変化の混在 |
| 第7章 | Observer | 「変化に反応する相手」が変わる | 在庫管理システム | A：変化の混在 |
| 第8章 | Factory Method | 「作るオブジェクト」が変わる | 決済プロセッサーの切り替え | D：生成と利用の混在 |

---

## 原因特定の切り口（4種類）

| 切り口 | 一言で | 使うパターン |
|:---|:---|:---|
| A：変化の混在 | 変わるものと変わらないものが同じ場所にいる | Strategy / Template Method / Command / Decorator / Observer |
| B：依存の過多 | 使う側が知らなくていいことまで知っている | Facade |
| C：状態と振る舞いの混在 | 状態が増えるたびに振る舞いの記述も増殖する | State |
| D：生成と利用の混在 | 何を作るかの判断と、どう使うかが同じ場所にある | Factory Method |

---

## ファイル対応表

| 役割 | 定義ファイル | 出力ファイル |
|:---|:---|:---|
| はじめに | ― | output/chapter00_1.md |
| 第一部の説明 | ― | output/chapter00_2.md |
| 第1章 | patterns/strategy.yaml | output/chapter01.md |
| 第2章 | patterns/facade.yaml | output/chapter02.md |
| 第3章 | patterns/state.yaml | output/chapter03.md |
| 第4章 | patterns/template-method.yaml | output/chapter04.md |
| 第5章 | patterns/command.yaml | output/chapter05.md |
| 第6章 | patterns/decorator.yaml | output/chapter06.md |
| 第7章 | patterns/observer.yaml | output/chapter07.md |
| 第8章 | patterns/factory-method.yaml | output/chapter08.md |
| 第二部の説明 | ― | output/chapter09_1.md |
| 第9章 | ― | output/chapter09_2.md |
| 第10章 | ― | output/chapter10.md |
| 第11章 | ― | output/chapter11.md |
| 第12章 | ― | output/chapter12.md |
