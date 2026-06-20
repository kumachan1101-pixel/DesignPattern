## 第8章 変わる生成の種類 ―― Factory Method パターン

―― 思考の型：インスタンスを生成する責任を、どこに置くか

### この章の核心

**ある機能を利用しようとするとき、その機能を実現するための「オブジェクトの生成」まで呼び出し側が担ってしまうと、新しい実装が必要になった際に呼び出し側まで芋づる式に修正しなければならなくなる。**

---

### この章を読むと得られること

この章が問うのは「作る」ことの設計です——オブジェクトを生成している場所が、利用している場所と同居していると何が起きるか。「決済プロセッサーを切り替えたいだけなのに、なぜこんなにコードを変える必要が生じますのか」という問いが出てきたことがあるなら、この章に答えがあります。

* **得られること1：** 「オブジェクトを生成する」という観点で、コードの変動箇所を識別できるようになる
* **得られること2：** 利用処理が決済手段のクラス名と生成方法をどこまで知っているかを接続点から調べ、生成と利用の混在による痛みを説明できるようになる
* **得られること3：** 生成の責任を利用処理から分けることで、決済手段追加の変更をCreatorと組み立て箇所へ寄せられることを説明できるようになる
* **得られること4：** 利用側が具体的な生成ロジックを知らずに、必要な機能を持つオブジェクトを受け取れる視点

## 🔵 フェーズ1：現状把握 ―― コードとクラス構成を読む

この問題を解くために7つのフェーズを使います。はじめに現状把握から開始し、仮説立案・問題特定・原因分析・課題定義・対策検討・対策実施という順で進みます。

変更要求が来る前のシステムの現状を事実として把握するところから始めます。はじめに仕様と動作例で「このシステムが何をするか」を確認し、それからコードを読みます。

### 1-1：このシステムの仕様

このシステムは、ECサイトでお客様が選択した決済手段に応じて、**決済処理を実行**します。

「決済種別」と「金額」を入力として受け取り、対応する決済プロセッサーを呼び出して処理を行います。

**現在対応している決済手段**

| 決済種別 | 入力値 | 処理内容 |
|---|---|---|
| クレジットカード決済 | `"credit"` | クレジットカードの認証と決済を実行する |
| コンビニ決済 | `"cvs"` | コンビニ払いの支払い番号を発行する |

**決済の実行フロー**

1. 決済アプリケーションが決済種別を受け取る
2. 種別に応じた決済手段を選択する
3. 選択した決済手段で処理を実行する
4. 処理結果（成功／失敗）を返す

---

### 1-2：動作例テーブル

仕様を定義したところで、実際にどのような入力に対してどのような結果が返るかを確認します。このテーブルは「このシステムが正しく動いているとはどういう状態か」の基準になります。後で設計の改善（リファクタリング）を段階的に進めるときも、この表に立ち返ります。

| 決済種別 | 金額 | 状態 | 期待される結果 |
|---|---|---|---|
| クレジットカード | 1000円 | 正常 | 「クレジットで 1000 円決済しました。」を出力し完了を返す |
| コンビニ払い | 500円 | 正常 | 「コンビニで 500 円の支払い番号を発行しました。」を出力し完了を返す |
| ↓ 変更要求による追加分（PayPay・定期課金は1-5節で導入）↓ | | | |
| PayPay | 700円 | 正常 | 「PayPayで 700 円決済しました。」を出力し完了を返す |
| クレジットカード | 980円 | 定期課金 | 月額課金ログを出力した後、クレジット決済を実行し完了を返す |

このテーブルは最終実装（フェーズ7）が実現する動作の全シナリオを示しています。現状コード（1-3節）はクレジットカードとコンビニ払いの2種類のみ対応しており、PayPayと定期課金はフェーズ7で追加されます。「入力→出力」の期待される結果は段階が進んでも変わりません。この章で比べるのは「決済手段が増えたとき、どこを触れば済むか」という構造の違いです。

コードを読む前に、このシステムが「何をする必要があるか」をこの表で確認できました。次は「どのように実装されているか」を見ていきます。

---

### 1-2.5：クラス概要サマリー

#### このシステムの登場クラス

| クラス名 | 役割 | 担当する仕様 |
|---|---|---|
| PaymentApplication | 決済手段に応じた処理を呼び出す | 決済処理の分岐と実行 |
| CreditCardProcessor | クレジットカード決済の処理 | クレジットカード決済 |
| ConvenienceStoreProcessor | コンビニ決済の処理 | コンビニ決済 |

**データの流れ：** main() → PaymentApplication.processPayment() → 決済種別による分岐 → 各Processorの pay() 呼び出し

**注目ポイント：** 現在は PaymentApplication がすべての具体的な決済クラスを直接生成し、呼び出しています。フェーズ3以降で、この「具体的な決済手段を知りすぎていること」が問題として浮かび上がります。

---

### 1-3：実装コード（現状）（現状）

```cpp
#include <iostream>
#include <string>

using namespace std;

// 各決済手段の具体的な処理
class CreditCardProcessor {
public:
    void pay(int amount) {
        cout << "クレジットで "
             << amount << " 円決済しました。" << endl;
    }
};

class ConvenienceStoreProcessor {
public:
    void pay(int amount) {
        cout << "コンビニで " << amount
             << " 円の支払い番号を発行しました。" << endl;
    }
};

// 決済を統括するクラス
class PaymentApplication {
public:
    void processPayment(string type, int amount) {
        // ← 生成と利用が混在している箇所
        if (type == "credit") {
            CreditCardProcessor processor;
            processor.pay(amount);
        } else if (type == "cvs") {
            ConvenienceStoreProcessor processor;
            processor.pay(amount);
        }
    }
};

int main() {
    PaymentApplication app;
    app.processPayment("credit", 1000);
    app.processPayment("cvs", 500);
    return 0;
}
```

上記コードの実行結果：

```
クレジットで 1000 円決済しました。
コンビニで 500 円の支払い番号を発行しました。
```

このコードを見ると、`PaymentApplication` クラスが、どの決済手段のクラスを生成し、どう実行するかをすべて直接知っていることが分かります。次のフェーズで変更が来たときに何が起きるかを確認します。

---

### 1-4：クラス構成図

コードを読んだところで、クラス間の関係を図で整理します。

```mermaid
classDiagram
    class PaymentApplication {
        +processPayment(type, amount)
    }
    class CreditCardProcessor {
        +pay(amount)
    }
    class ConvenienceStoreProcessor {
        +pay(amount)
    }
    PaymentApplication ..> CreditCardProcessor : uses
    PaymentApplication ..> ConvenienceStoreProcessor : uses
```

この図が示す通り、`PaymentApplication` というクラスが、クレジットカードやコンビニ決済といった個別の決済プロセッサーを直接利用（依存）している構成になっています。

---

### 1-5：変更要求

**変更要求の発生チーム：** 今回の変更要求は決済プラットフォームチームから届いています。新しい決済手段の導入を推進するチームです。この点をフェーズ2の「誰の判断で変わるか」への伏線として覚えておきます。


ある週の火曜日、決済プラットフォームチームのリーダーからチャットで連絡が入りました。

「急ぎの相談なんだけど、来月から導入する新しい決済手段として『PayPay』に対応してほしいんだ。今のシステムでそのまま行けるか確認して、もし難しそうなら方針を教えてもらえるかな？ 決済手段が増えるのはビジネス上不可欠だから、なんとか対応したいんだ。」

なるほど、PayPayの対応ですね。コード上の PaymentApplication クラスを見ると、現状では CreditCardProcessor や ConvenienceStoreProcessor を直接 new して使っています。このままでは新しい決済手段が増えるたびに、PaymentApplication に新しい分岐を書き足し、クラスを直接生成するコードが増殖し続けることになります。このままの構造で対応してしまって本当に良いのか、少し立ち止まって考えてみたいと思います。

**仕様変更の内容**

変更要求を受けて、対応する決済手段がどう変わるかを整理します。

| 決済手段 | 変更前 | 変更後 |
|---|---|---|
| クレジットカード（`"credit"`） | 対応済み | 変更なし |
| コンビニ払い（`"cvs"`） | 対応済み | 変更なし |
| **PayPay（`"paypay"`）** | 未対応 | **新規追加** |

PayPay決済が追加されても、決済の実行フロー（「種別を受け取り→プロセッサーを選択→処理を実行→結果を返す」）は変わりません。変わるのは「対応できる種別が1つ増える」という点だけです。

PayPay決済の動作：`"paypay"` を受け取ると、PayPay用のプロセッサーが呼び出され「PayPayで〇〇円決済しました」という結果を返します。

フェーズ1でシステムの現状と変更要求が把握できました。次のフェーズ2では、「何が変わり、何が変わらないか」を整理します。

## 🟣 フェーズ2：仮説立案 ―― 何が変わるかを観察し、ヒアリングで裏付ける

### 2-1：責任チェック表

各クラスが「何を知るべきか」を整理します。

| **クラス名** | **責任（1文）** | **知るべきこと** |
|---|---|---|
| `PaymentApplication` | 決済手段の種類に応じて適切な決済処理をキックする | 利用可能な全決済プロセッサの具体名と、その生成方法 |
| `CreditCardProcessor` | クレジットカード決済を実行する | クレジットカード特有のAPIやパラメータ |
| `ConvenienceStoreProcessor` | コンビニ決済を実行する | コンビニ特有のAPIやパラメータ |

この表から、`PaymentApplication` が本来の責務である「決済処理の振り分け」だけでなく、すべての決済手段の「具体名」や「生成方法」までを知っている状態が見て取れます。

### 2-2：変わる理由の分析

責任チェック表でクラスの責任が整理できました。次に、コードの各行が「誰の判断で変わる知識か」を確認することで、混在している責任をさらに細かく特定します。判断基準は、「このクラスの担当者（ここでは決済基盤開発チーム）とは別の人間が変更を決定するかどうか」です。別の人間が決定するなら、それは「責任外（❌）」と判断します。

`PaymentApplication.processPayment()` の各行を見ると：

| **コードの行** | **持っている知識** | **誰の判断で変わるか** | **責任内か** |
|---|---|---|---|
| `if (type == "credit") { ... }` | クレジットカード決済クラスの生成条件と具体型名 | 決済手段を追加する事業側の判断 | ❌ 別担当者 |
| `CreditCardProcessor processor;` | 生成するクラスの具体名 | 決済手段を実装する開発チーム | ❌ 別担当者 |
| `processor.pay(amount);` | 決済処理の呼び出し方（インターフェース） | 決済基盤開発チーム | ✅ |

1つのメソッドの中に、変える理由が異なる複数の知識が混在しています。今すぐ問題とは言えませんが、これが後の痛みの予兆です。

### 2-3：今回の変更で確実に変わること

今回の変更要求から確定している変更は2点です。

- **`PayPayProcessor` という新しい具体クラスの追加**：PayPay決済の実装クラスを新規作成する
- **`PaymentApplication` 内の分岐条件への `"paypay"` 追記**：現状のコード構造上、型名と分岐が直結しているため

ただし「この変更が1回限りか、今後も続くか」によって、どこまで設計を変えるべきかが大きく変わります。関係者に確認します。

### ヒアリングに向けた背景確認

このシステムは、ある決済サービス事業者の「決済プロセッサー」を管理する基盤です。お客様がECサイトで買い物をするとき、クレジットカード決済やコンビニ決済など、さまざまな決済手段を選択しますが、このシステムは裏側でその手段ごとの処理を振り分ける役割を担っています。

当初、このサービスはクレジットカード決済だけをサポートしていました。しかし、ユーザーの利便性を高めるために、後からコンビニ決済、さらにPayPayなどのQRコード決済と、次々に新しい決済手段が追加されてきました。

コードを眺めてみると、`PaymentApplication` クラスという決済処理を統括するクラスの中で、`CreditCardProcessor` や `ConvenienceStoreProcessor` といった各決済手段の具体クラスを直接 `new` して利用する構成になっています。新しい決済手段が増えるたびに、この `PaymentApplication` クラスに新しい `else if` 文が追加され、利用するクラスが増え続けてきました。

### 2-4：関係者ヒアリング

> **現実のヒアリングでは——** 本書のヒアリングシーンでは設計判断を明確にするため、意図的に「理想的な回答」が返ってくるように描いています。これはシミュレーションです。現実には、「変わるかどうか分からない」「たぶん変わらない」という曖昧な答えが返ることも多いです。そのときは `git log` や過去の障害記録を「ヒアリングの代わり」として使ってみてください。「過去に何度変わったか」が最も正直な証拠です。

仮説を持って、決済プラットフォームチームの担当者と話し合いを持ちました。

- **開発者：** 「PayPay対応の件ですが、今の構造だと決済手段が増えるたびに PaymentApplication クラスを修正する必要があります。今後も新しい決済手段は追加される予定でしょうか？」
- **決済担当者：** 「ああ、かなりハイペースで追加していく予定だよ。次は銀行系の決済も入るし、後払いサービスも検討している。だから、決済手段が増えるたびに基幹部分のコードを書き換えるようなことはなるべく避けてほしいんだ。」
- **開発者：** 「なるほど。では、決済処理を実行する時のインターフェース（金額を渡して実行する点）は今後も変わらないでしょうか？」
- **決済担当者：** 「そこは固定だよ。どの手段でも『金額を受け取って決済する』という手続き自体は同じだからね。」
- **開発者：** 「分かりました。決済の実行ルールは固定だけれど、生成する対象（プロセッサーの種類）はどんどん増えていくということですね。」

### 2-5：ヒアリングで判明した将来リスク

ヒアリングで浮かび上がった「確定ではないが、近い将来起こりうる変化」を記録します。これは今回の設計判断の材料です。

| **将来リスク** | **時期の目安** | **根拠** |
|---|---|---|
| 決済手段の種類がさらに増加する（銀行系・後払いなど） | 新しい決済手段の追加ごと | 「かなりハイペースで追加していく予定」との合意 |
| 決済手段を特定するための識別子と具体クラスの紐付け | 新しい決済手段の追加ごと | 識別子と生成が現在直結しており、追加のたびに修正が必要 |

フェーズ2で「今変わること（確定）」と「将来変わるかもしれないこと（リスク）」を分けて整理できました。次のフェーズ3では、現在の構造で変更を試みたときに何が起きるかを確認します。

---

## 🟣 フェーズ3：問題特定 ―― 変更の痛みを発見する

### 3-1：変更を試みる

「PayPay対応」の要求を、今のコードで実装しようと試みます。変更前のコードはこうでした。

```cpp
void processPayment(string type, int amount) {
    if (type == "credit") {
        CreditCardProcessor processor;
        processor.pay(amount);
    } else if (type == "cvs") {
        ConvenienceStoreProcessor processor;
        processor.pay(amount);
    }
}
```

このコードにPayPay対応を追加すると、以下のようになります。

```cpp
void processPayment(string type, int amount) {
    if (type == "credit") {
        CreditCardProcessor processor;
        processor.pay(amount);
    } else if (type == "cvs") {
        ConvenienceStoreProcessor processor;
        processor.pay(amount);
    } else if (type == "paypay") {  // ← 追加
        PayPayProcessor processor;   // ← 追加
        processor.pay(amount);       // ← 追加
    }
}
```

一見シンプルな追加ですが、問題が浮かび上がります。決済手段が増えるたびにこの `PaymentApplication` クラスがどんどん長くなり、修正のたびにクラス内の既存ロジックを触らなければならないという事実です。もし決済手段が10個、20個と増えたら、このクラスは管理不能なほど巨大な「神クラス」になってしまうでしょう。

さらに、将来追加が想定される `SubscriptionService`（定期課金サービス）のような別の呼び出し元も同じ分岐ロジックを複製することになった場合、そちらも同様に修正必要があります。

### 3-2：変更影響グラフ

```mermaid
graph LR
    T1["変更要求：PayPay対応"] -->|"追記"| A["PaymentApplication<br>（既存の条件分岐全体）"]
    A -->|"新規クラス作成"| B["PayPayProcessor"]
```

新しい決済手段という「ビジネス上の変化」を実装するたびに、本来は決済手段の振り分けだけを担うべき `PaymentApplication` クラスが必ず修正対象として矢印を向けられていることが分かります。

### 3-3：痛みの言語化

**1つ目：修正のたびに「決済の統括者」が汚染される辛さ。** このクラスは本来、どの決済手段を使うかを判断するだけで良いはずなのに、個別のプロセッサーの生成方法や詳細な使い方までを直接握りしめています。決済手段が増えるたびにこのクラスを書き直す必要があるため、変更のたびにバグを混入させるリスクが付きまといます。

**2つ目：決済手段という「変わるもの」と、決済の振り分けという「変わらない構造」が同じ場所に混在している辛さ。** 決済プロセッサーが増えるたびに `if-else` のジャングルが深まり、コードの見通しが悪くなります。新しい決済手段を一つ足すだけで、既存の無関係な決済手段のコードまで巻き込んでテストをやり直す必要に迫られます状況は、開発のスピードを著しく低下させる要因になっています。

フェーズ3で「変更のたびに決済統括クラスが書き換わる」という痛みが確認できました。次のフェーズ4では、利用処理と生成処理の接続点に漏れている知識を確認します。

---
> **📌 問題（確定）**
> 決済手段が変わるたびに、利用側の `PaymentApplication` クラスの分岐条件・生成コードが連動して変わる。決済手段という「管理者が異なる知識」が、決済の振り分けフローと同じクラスに混在しているため、決済手段の追加・変更が統括クラスへの修正を引き起こし続ける。
---

ここまでで「何が痛いか」が事実として確認できました。次のフェーズ4では、その痛みが「なぜ起きているか」を構造の言葉で言語化します。

---

## 🟠 フェーズ4：原因分析 ―― なぜ辛いのかを構造で言語化する

### 4-1：痛みの根源を探る（観察と原因）

フェーズ3で確認した「変更の辛さ」は、コードのどこから来ているのでしょうか。コードを注意深く観察すると、痛みを引き起こしている2つの事実が浮かび上がってきます。

第一に、新しい決済手段を追加するとき、なぜ毎回 `PaymentApplication` を開かなければならないのでしょうか？
それは、このクラス自身が「クレジットカードなら `CreditCardProcessor` を生成する」「PayPayなら `PayPayProcessor` を生成する」といった**具体的なクラス名と生成方法をすべて直接知ってしまっている（抱え込んでいる）**からです。

第二に、なぜ変更の影響範囲が読めず、全テストをやり直す恐怖を感じるのでしょうか？
それは、「決済の振り分けフロー（変わらない骨格）」と「どの具体クラスを生成するか（変わる生成ロジック）」が、**同じメソッドの中で物理的に混ざり合っている**からです。

この「症状（痛み）」と「根本原因」を整理すると、以下のようになります。

| **観察した症状（痛み）** | **構造的な原因（痛みの根源）** |
|---|---|
| 決済手段を追加するたびに統括クラスが修正対象になる | `PaymentApplication` が各決済手段の具体的なクラス名と生成方法を直接知っているから |
| 影響範囲が読めず、全テストをやり直す恐怖 | 「決済の振り分けフロー」と「具体クラスの生成ロジック」という変わる理由が異なる2つのものが同じメソッドの中に混在しているから |

### 4-2：変わるもの/変わってほしくないもの

> **「変わらないもの」と「変わってほしくないもの」は異なります。** 「変わらないもの」は経験的事実（今まで変わっていない）、「変わってほしくないもの」は設計意図（ここを安定させてほかを守りたい）です。ここで整理するのは後者です。

| **変わるもの（生成ロジック）** | **変わってほしくないもの（振り分けの骨格）** |
|---|---|
| 決済プロセッサーの具体的なクラス（クレジット、コンビニ、PayPay等） | 「金額を受け取って決済を実行する」というAPIの定義（インターフェース） |
| 各決済手段の生成方法・コンストラクタ引数 | 決済の振り分けフロー全体 |

**【変わる部分（変わり続ける生成コード）】**
```cpp
        if (type == "credit") {
            CreditCardProcessor processor;
            processor.pay(amount);
        } else if (type == "paypay") {
            PayPayProcessor processor;
            processor.pay(amount);
        }
        // 銀行振込・Apple Pay など、決済手段を追加するたびに else if がここに増える
```

**【変わらない部分（不変の骨格）】**
```cpp
        // どの決済手段であっても「種別を受け取り→実行する」という流れは変わらない
        // (ここに変わる部分の生成ロジックが入っている状態)
```

### 4-3：接続点に漏れている生成の知識を確認する

現在の `PaymentApplication` は、すべての決済プロセッサーを自分自身の中で直接生成しています。

**【生成方法が利用処理へ漏れているコード】**
```cpp
class PaymentApplication {
public:
    void processPayment(string type, int amount) {
        // 具体クラスを直接知り、直接生成して呼び出している
        if (type == "credit") {
            CreditCardProcessor processor;  // ← 利用処理が生成するクラス名を知っている
            processor.pay(amount);
        }
        // PayPay・銀行振込など、決済手段を追加するたびに else if がここに増える
    }
};
```

新しい決済手段が増えるたびに、決済フローを持つ`PaymentApplication`を開き、生成分岐を追加する必要があります。利用処理が生成するクラス名を知っているためです。

決済の振り分けフローと個別の生成ロジックは、変わる理由が全く異なります。これらが同じ場所に混在していることが、根本原因として確認できました。

今回見直す接続点は、「決済手段を生成して利用処理へ渡す境界」です。利用側は`pay()`できることだけを知れば十分です。

フェーズ4で根本原因が言語化できました。「どこを分けるか」は明確です。次のフェーズ5では、その境界で実際に何が流れているかを値・型のレベルで具体化し、「何が変わり、何が変わらないか」を明確にします。

---
> **📌 原因（確定）**
> `PaymentApplication`が決済手段のクラス名と生成方法を知っている。決済手段の追加が、変えたくない決済フローの修正へ直結している。
---

「何が痛いか（問題）」と「なぜ痛いか（原因）」が揃いました。次のフェーズ5では、「何を切り離す必要があるか（課題）」を、接続点で流れるデータのレベルで言語化します。

---

## 🟡 フェーズ5：課題定義 ―― 接続点で何が流れているかを見る

フェーズ4は「なぜ辛いか」を答えました。フェーズ5が問うのは「分けるべき境界で、実際に何が流れているか」です。クラスの参照関係ではなく、**値・型のレベル**に降りていきます。

フェーズ4の分析により、問題は「決済の振り分けフロー」と「具体クラスの生成ロジック」が混在していることだと分かりました。その境界で何がやり取りされているかを具体化します。

### 接続点を特定する

`processPayment()` の中で分けるべき境界は1か所です。決済処理を利用する流れと、具体的な処理クラスを生成する判断との境界を見ます。

```cpp
void processPayment(string type, int amount) {
    // ↓ 具体クラスを選んで生成する判断（変わり続ける）
    if (type == "credit") {
        CreditCardProcessor processor;
        processor.pay(amount);
    } else if (type == "cvs") {
        ConvenienceStoreProcessor processor;
        processor.pay(amount);
    } else if (type == "paypay") {
        PayPayProcessor processor;
        processor.pay(amount);
    }
    // ↑ ここまでが分離するターゲット
}
```

生成処理が振り分けフローに提供しているのは「`pay(amount)` を実行できるオブジェクト」です。

| 接続点 | 接続するデータ | 変わるもの |
|---|---|---|
| 具体クラス生成 → `processPayment()` の骨格 | `pay(int)` を持つオブジェクト（将来はIPaymentProcessor*） | 生成する具体クラスの種類 |

### 何が変わり、何が変わらないか

- **変わるもの**：生成する具体クラス（CreditCardProcessor / ConvenienceStoreProcessor / PayPayProcessor …）。新しい決済手段が追加されるたびに生成判断が増える。
- **変わらないもの**：振り分けフローが呼ぶ操作（`pay(amount)`）。振り分けロジックが期待するインターフェース形は変わらない。

呼び出し元（`PaymentApplication`）が必要とするのは「`pay(amount)` を呼べること」です。問題は「どのクラスを生成するか」という**生成判断**まで同じクラスへ積み重なっていることです。

**現状のままでよい場面**：決済手段が1種類で固定されるなら、利用処理で生成する単純さを保つ判断もあります。今回は決済手段が増えるため、利用フローから生成判断を分ける設計を検討します。

---
> **📌 課題（確定）**
> 「決済の振り分けフロー（`processPayment`）」と「決済プロセッサーの生成ロジック（具体クラスの選択と`new`）」を切り離す必要がある。渡すデータ（`pay(amount)` を呼べるオブジェクト）の形は安定しているため、「何を呼ぶか」ではなく「どのクラスを生成するか」という生成の知識を `PaymentApplication` から取り除くことが課題である。
---

問題・原因・課題の3点が揃いました。次のフェーズ6では、この課題を解消するための具体的な設計案を段階的に検討します。

---

## 🔴 フェーズ6：対策検討 ―― 段階的な改善と決断

フェーズ5で「変わるのは生成する具体クラスと選択条件であり、振り分けフローが使う操作インターフェースは安定している」ことが分かりました。ここでは、生成判断をどこへ移すと変更を局所化できるかを、段階を追って試します。それぞれの段階で「まだ何が残っているか」を確認し、その積み重ねの先で「どこまで進むべきか」を決断します。

### ステップ1：生成ロジックをプライベートメソッドに切り出す

`processPayment` の中を見ると、「どの種別か判断する if-else」と「具体クラスを生成して pay() を呼ぶ」が一体になっています。「とりあえず読みやすくしよう」と思ったとき、最初に思いつくのは「生成の部分だけをメソッドに切り出す」ことではないでしょうか。クラスは分けず、`PaymentApplication` の中に `createProcessor` というプライベートメソッドを作ります。なお、コード中の `IPaymentProcessor*` は、ステップ3で正式に定義するインターフェースです。ここでは「どのクラスを返すかを一か所にまとめる」という構造の変化に注目してください。

```cpp
class PaymentApplication {
private:
    // 生成処理を切り出す（PaymentApplicationの中にとどまっている）
    IPaymentProcessor* createProcessor(string type) {
        if (type == "credit") return new CreditCardProcessor();
        if (type == "paypay") return new PayPayProcessor();
        if (type == "cvs")    return new ConvenienceStoreProcessor();
        return nullptr;
    }

public:
    void processPayment(string type, int amount) {
        IPaymentProcessor* processor = createProcessor(type);
        if (processor) {
            processor->pay(amount);
            delete processor;
        }
    }
};
```

`processPayment` が「生成→実行」という流れだけを担い、`createProcessor` が「どのクラスを生成するか」の判断を一手に引き受けた形になっています。

**この段階の評価：**
`processPayment` の見通しが良くなり、生成処理がひとまとまりになりました。これは確かな一歩前進です。しかし `createProcessor` は `PaymentApplication` の中にあるため、新しい決済手段が増えるたびに `PaymentApplication` を開いて `if` を追加する必要があります。生成処理がまとまったことは良いのですが、`PaymentApplication` がすべての具体クラス（`CreditCardProcessor`・`PayPayProcessor`・`ConvenienceStoreProcessor`）を直接知っているという根本は変わっていません。

「生成の知識を `PaymentApplication` の外に出せないか」という問いが自然に湧いてきます。

### ステップ2：生成ロジックを専用の PaymentFactory クラスに分離する

ステップ1で気になったのは「生成の知識が `PaymentApplication` に留まっている」という点でした。「では、生成の担当クラスを別に作ろう」という次の一手を試してみます。`createProcessor` の中身をそのまま `PaymentFactory` という独立したクラスに移します。

```cpp
// 生成の責任を専用クラスに分離する
class PaymentFactory {
public:
    IPaymentProcessor* create(string type) {
        if (type == "credit") return new CreditCardProcessor();
        if (type == "paypay") return new PayPayProcessor();
        if (type == "cvs")    return new ConvenienceStoreProcessor();
        return nullptr;
    }
};

class PaymentApplication {
private:
    PaymentFactory factory;  // ← 生成の担当を外部クラスに委ねる

public:
    void processPayment(string type, int amount) {
        IPaymentProcessor* processor = factory.create(type);
        if (processor) {
            processor->pay(amount);
            delete processor;
        }
    }
};
```

`PaymentApplication` は `PaymentFactory` に生成を依頼するだけになり、具体クラスの名前（`CreditCardProcessor` など）を直接知らなくなっています。

**この段階の評価：**
生成の責任を `PaymentApplication` から切り出せました。`PaymentApplication` は決済の振り分けフローに集中できるようになっています。しかし今度は `PaymentFactory` がすべての具体クラスを知っており、新しい決済手段を追加するたびに `PaymentFactory` を修正必要があります。「修正が必要なクラスが `PaymentApplication` から `PaymentFactory` に移っただけ」という見方もできます。

もう少し深く考えると、`PaymentFactory` は固定された1つのクラスです。「テスト環境ではモック用のプロセッサーを使いたい」「本番とステージングで生成ロジックを変えたい」といった要求が来たとき、`PaymentFactory` ごと差し替える仕組みがありません。Factory クラスを分離したのに、その Factory 自体が固定されてしまっているのです。

「Factory の生成ロジック自体を差し替え可能にできないか」という問いが見えてきます。

### ステップ3：生成メソッドを抽象化し、具体クラスに委ねる（Factory Method）

ステップ2の `PaymentFactory` は、「どの具体クラスを生成するか」という知識を一手に持つ固定されたクラスでした。この発想を逆転させてみます。`PaymentApplication` 自体に `createProcessor` という抽象メソッドを宣言し、「生成の仕方は自分では決めない、サブクラスに任せる」という構造にします。

はじめに、すべての決済プロセッサーが従う共通のインターフェースを定義します。

```cpp
// 決済プロセッサーの共通インターフェース（契約）
class IPaymentProcessor {
public:
    virtual ~IPaymentProcessor() {}
    virtual void pay(int amount) = 0;
};
```

`IPaymentProcessor` は「金額を受け取って決済を実行する」という約束だけを定義します。

次に、各決済手段の具体クラスがこのインターフェースを実装します。

```cpp
class CreditCardProcessor : public IPaymentProcessor {
public:
    void pay(int amount) override {
        cout << "クレジットで " << amount << " 円決済しました。" << endl;
    }
};

class PayPayProcessor : public IPaymentProcessor {
public:
    void pay(int amount) override {
        cout << "PayPayで " << amount << " 円決済しました。" << endl;
    }
};

class ConvenienceStoreProcessor : public IPaymentProcessor {
public:
    void pay(int amount) override {
        cout << "コンビニで " << amount << " 円の支払い番号を発行しました。" << endl;
    }
};
```

どのクラスも `IPaymentProcessor` を実装しており、呼び出し側は `pay(amount)` という一つの窓口だけを使えます。

そして核心の構造です。`PaymentApplication` は `createProcessor` を純粋仮想メソッドとして宣言し、具体的な生成はサブクラスに委ねます。

```cpp
// 生成の仕方を「サブクラスに任せる」抽象クラス
class PaymentApplication {
protected:
    //  Factory Method：「何を作るか」はサブクラスが決める
    virtual IPaymentProcessor* createProcessor(string type) = 0;

public:
    void processPayment(string type, int amount) {
        // ← 生成結果の型は IPaymentProcessor* だけを知る
        IPaymentProcessor* processor = createProcessor(type);
        if (processor) {
            processor->pay(amount);
            delete processor;
        }
    }
};

// 実際の生成ロジックはここだけに閉じる
class DefaultPaymentApplication : public PaymentApplication {
protected:
    IPaymentProcessor* createProcessor(string type) override {
        if (type == "credit") return new CreditCardProcessor();
        if (type == "paypay") return new PayPayProcessor();
        if (type == "cvs")    return new ConvenienceStoreProcessor();
        return nullptr;
    }
};
```

`PaymentApplication` の `processPayment` は `IPaymentProcessor*` を受け取って `pay` を呼びます。「どのクラスを生成するか」という判断は `DefaultPaymentApplication` へ移りました。新しい決済手段を追加するときは、具体Processorと生成判断を変更しますが、決済を実行する共通フローへ分岐を増やさずに済みます。

**この段階の評価：**
`PaymentApplication`（振り分けフローの骨格）から、`DefaultPaymentApplication`へ生成判断を移しました。新しい決済手段を追加するときはCreatorの生成処理と、必要に応じて種別の入力・組み立て設定を変更します。`processPayment`の処理手順は変更せずに済みます。「テスト用にモックプロセッサーを使いたい」という要求では、別のCreatorを用意できます。

---

### どこまで設計を進めるのが良いか（採用ステップの決断）

3つのステップにはそれぞれトレードオフがあります。ステップ3の抽象化は強力ですが、クラスの数が増えるという「初期投資コスト」もかかります。どこで止めるかは、**「今後の変更頻度（ビジネス要求）」**で決断します。

*   **ステップ1（プライベートメソッド化）で止めるケース：** 決済手段が2〜3種類で今後増える予定が全くない場合。生成処理がひとまとまりになるだけで、読みやすさは十分改善されます。
*   **ステップ2（具体ファクトリへの分離）で止めるケース：** 生成ロジックを `PaymentApplication` から切り出したいが、抽象化とサブクラスを増やすコストをまだかけたくない場合の「中間策」です。変更の主体が `PaymentFactory` に移るため、`PaymentApplication` への修正は不要になります。
*   **ステップ3（Factory Method）まで進むケース：** 「今後も新しい決済手段が追加される」と確定しており、かつ「生成の仕方そのものを差し替えたい（テスト・環境別設定など）」という要求が見込まれる場合。今すぐ初期投資コストを払ってでも、将来の変更コストを最小化するのが適切です。

**今回の決断：**
フェーズ2のヒアリングで、決済担当者から「かなりハイペースで追加していく予定」と明言されています。したがって、今回は**ステップ3（Factory Method）まで進化させる**決断を下します。

生成するオブジェクトの種類（決済手段）を、利用側から隠蔽するメソッドに集約し、利用側がインターフェースを通じてインスタンスを得る構造——これが **Factory Method（ファクトリーメソッド）パターン** と呼ばれています。

フェーズ6で採用ステップが決まりました。次のフェーズ7では、この決断を最終的なコードに落とし込みます。

## 🟢 フェーズ7：対策実施 ―― 変化に強いコードを完成させる

### 7-1：解決後のコード（全体）

ステップ3で決断した構造を、実行可能な完全なコードとして組み上げます。各役割ごとにコードを分けて見ていきましょう。

**1. インターフェース（契約）の定義**
すべての決済プロセッサーが守るべき共通のインターフェースを定義します。

```cpp
#include <iostream>
#include <string>

using namespace std;

// インターフェース：ビジネス責任で命名
class IPaymentProcessor {
public:
    virtual ~IPaymentProcessor() {}
    virtual void pay(int amount) = 0;
};
```

`IPaymentProcessor` は「決済を実行するために持つべきメソッドと戻り値の約束」を定義します。具体クラスが何であれ、このインターフェースさえ実装していれば、利用側はそのまま使えます。

**2. 個別の決済プロセッサーの実装（具体）**
インターフェースを満たす具体的な決済クラスを作成します。本体コードに触れることなく、このクラス群だけを自由に追加・変更できます。

```cpp
class CreditCardProcessor : public IPaymentProcessor {
public:
    void pay(int amount) override {
        cout << "クレジットで " << amount
             << " 円決済しました。" << endl;
    }
};

class ConvenienceStoreProcessor : public IPaymentProcessor {
public:
    void pay(int amount) override {
        cout << "コンビニで " << amount
             << " 円の支払い番号を発行しました。" << endl;
    }
};

// ← 新手段はここに追加するだけ（ここだけ変わる）
class PayPayProcessor : public IPaymentProcessor {
public:
    void pay(int amount) override {
        cout << "PayPayで " << amount << " 円決済しました。" << endl;
    }
};
```

**3. 本体クラス（Factory Methodを持つCreator）**
決済を行う本体クラスです。`PaymentApplication` が「振り分けフローの骨格」を担い、`DefaultPaymentApplication` が「どのクラスを生成するか」という判断を一手に引き受けます。利用側である `processPayment` はインターフェースを通じて結果を受け取るだけになります。

```cpp
// 振り分けフローの骨格（生成は知らない）
class PaymentApplication {
protected:
    // Factory Method：生成はサブクラスに委ねる
    virtual IPaymentProcessor* createProcessor(string type) = 0;

public:
    void processPayment(string type, int amount) {
        // ← 生成結果の型は気にしなくていい（IPaymentProcessor*として受け取るだけ）
        IPaymentProcessor* processor = createProcessor(type);
        if (processor) {
            processor->pay(amount); // ← 実装詳細を直接触らない
            delete processor;
        }
    }
};

// 生成ロジックはここだけに閉じる（← ここだけ変わる）
class DefaultPaymentApplication : public PaymentApplication {
protected:
    IPaymentProcessor* createProcessor(string type) override {
        if (type == "credit") return new CreditCardProcessor();
        if (type == "cvs")    return new ConvenienceStoreProcessor();
        if (type == "paypay") return new PayPayProcessor();
        return nullptr;
    }
};
```

**4. 組み立てと実行（メイン関数）**

```cpp
// 定期課金サービス：Factory Method経由でクレジット決済を行う
class SubscriptionService {
private:
    PaymentApplication* app;
public:
    SubscriptionService(PaymentApplication* a) : app(a) {}
    void chargeMonthly(int amount) {
        cout << "[定期課金] 月額 " << amount
             << " 円 課金ログを記録しました。" << endl;
        // Factory Method経由で決済を実行（SubscriptionServiceはcreditしか使わない）
        app->processPayment("credit", amount);
    }
};

int main() {
    DefaultPaymentApplication app;  // ← 具体的な生成担当を選ぶのはここだけ

    // 行1：credit / 1000円
    app.processPayment("credit", 1000);
    // 行2：paypay / 700円
    app.processPayment("paypay", 700);   // ← 新しい決済手段も呼び出せる
    // 行3：cvs / 500円
    app.processPayment("cvs", 500);
    // 行4：定期課金（SubscriptionService経由でcredit/980円）
    SubscriptionService sub(&app);
    sub.chargeMonthly(980);
    return 0;
}
```

上記コードの実行結果：

```
クレジットで 1000 円決済しました。
PayPayで 700 円決済しました。
コンビニで 500 円の支払い番号を発行しました。
[定期課金] 月額 980 円 課金ログを記録しました。
クレジットで 980 円決済しました。
```

掲載した実行結果は動作例テーブルの4行に対応しています。`SubscriptionService`は`PaymentApplication`を利用するため、今回の決済手段追加ではその処理を変更していません。`processPayment`の中から決済手段のクラス名がなくなりました。

### 7-2：動作シーケンス図

ステップ3で到達したFactory Methodパターンの実行時のオブジェクト間のやり取りを可視化します。`PaymentApplication` が `createProcessor` を通じて生成の判断を委譲し、利用側は `IPaymentProcessor*` というインターフェース経由で処理を実行する流れが確認できます。

> **図の読み方：** `createProcessor` はシーケンス図では独立した参加者として描かれていますが、実際には `PaymentApplication`（またはそのサブクラス）のメソッドです。処理の委譲関係を明確に可視化するために図上で分離して表現しています。

```mermaid
sequenceDiagram
    participant main
    participant PA as PaymentApplication
    participant CP as createProcessor
    participant CC as CreditCardProcessor

    main->>PA: processPayment("credit", 1000)
    PA->>CP: createProcessor("credit")
    Note right of PA: 生成をメソッドに委譲
    CP->>CC: new CreditCardProcessor()
    CC-->>CP: インスタンス
    CP-->>PA: IPaymentProcessor*
    PA->>CC: processor->pay(1000)
    Note right of PA: インターフェース経由（具体型を知らない）
    CC-->>PA: 完了
    PA-->>main: 完了
```

### 7-3：変更影響グラフ（改善後）

```mermaid
graph LR
    T1["変更要求：PayPay対応"] --> F1["createProcessor ✅"]
    T1 -. "影響なし" .-> A["processPayment ✅"]
    T1 -. "影響なし" .-> B["CreditCardProcessor ✅"]
```

フェーズ3の変更影響グラフと比べると、変更要求が `createProcessor` の修正だけに閉じるようになりました。

### 7-4：変更シナリオ表

| **シナリオ** | **変わるクラス** | **変わらないクラス** |
|---|---|---|
| 銀行系決済を追加する | `createProcessor`（1行追加）、新クラスの作成 | `PaymentApplication`（利用ロジック）、他の決済クラス |
| コンビニ決済の実装を変更する | `ConvenienceStoreProcessor`（1箇所修正） | `PaymentApplication`、他の決済クラス |
| クレジット決済を廃止する | `createProcessor`（1行削除） | `PaymentApplication`（利用ロジック）、他の決済クラス |

---

## 整理

### この章で定義したこと

| | 内容 |
|---|---|
| **問題** | 決済手段が変わるたびに `PaymentApplication` の分岐条件・生成コードが連動して変わる |
| **原因** | `PaymentApplication` が具体的な決済プロセッサーのクラス名と生成方法を直接知っており、決済手段の追加コストが統括クラスの修正回数に直結している |
| **課題** | 振り分けフローと生成ロジックを切り離し、`PaymentApplication` が具体クラスを知らずに決済を実行できる構造にする |
| **解決策** | Factory Method パターン：`createProcessor` という抽象メソッドに生成の判断を委ね、`processPayment` は `IPaymentProcessor*` インターフェース経由だけで結果を受け取る |

### フェーズとこの章でやったこと

| **フェーズ** | **この章でやったこと** |
|---|---|
| 🔵 フェーズ1：現状把握 | 仕様と動作例テーブルを確認した後、コードをクラス単位で読んだ。クラス構成図と変更要求を把握した |
| 🟣 フェーズ2：仮説立案 | 責任チェック表でクラスごとの変わる理由を確認した。今回の確定変更とヒアリングで判明した将来リスクを分けて整理した |
| 🟣 フェーズ3：問題特定 | PayPay追加を試み、決済手段が増えるたびに統括クラスが修正対象になることを確認した |
| 🟠 フェーズ4：原因分析 | 変わる理由が異なる2つのもの（振り分けフローと生成ロジック）が同じ場所にいることが痛みの根本と特定した |
| 🟡 フェーズ5：課題定義 | IPaymentProcessor* を共通の接続点とし、具体クラスの生成判断を利用側から分ける課題を定めた |
| 🔴 フェーズ6：対策検討 | 3ステップの段階的進化でそれぞれの限界を確認し、ステップ3（Factory Method・抽象化）まで進化させる決断を下した |
| 🟢 フェーズ7：対策実施 | 最終コードを実装し、変更影響グラフで変更の局所化を確認した |

### 責任の移動

| **責任** | **変更前** | **変更後** |
|---|---|---|
| 決済の振り分けフローの進行 | `PaymentApplication` | `PaymentApplication`（変わらず） |
| 決済種別に応じたプロセッサーの生成 | `PaymentApplication`（if-else + new 直書き） | `PaymentApplication.createProcessor()`（Factory Methodとして分離） |
| 各決済の具体的な処理 | `CreditCardProcessor` 等（変わらず） | `CreditCardProcessor` 等（`IPaymentProcessor`経由に） |
| 決済処理の契約定義 | —（なし） | `IPaymentProcessor` |

---

## 振り返り

### 「この章を読むと得られること」は手に入ったか

| **得られること** | **この章のどこで示したか** |
|---|---|
| 1. 変動箇所の識別 | フェーズ2の責任チェック表と変わる理由の分析で、生成ロジックを変動要因として特定した |
| 2. 接続点の診断 | フェーズ4で、決済手段のクラス名と生成方法が利用処理へ漏れている状態を確認した |
| 3. 変更局所化の説明 | フェーズ7の変更シナリオ表で、変更が `createProcessor` に閉じる構造を示した |
| 4. 利用側が生成知識から解放される視点 | フェーズ6のステップ3で、`processPayment` からif文が消える様子を示した |

### 3つの設計原則はどう適用されたか

**原則1「変わるものをカプセル化せよ」の現れ**

- 具体化された場所：`createProcessor` メソッド（Factory Method）
- 解説：具体クラスの生成という「変わる理由」を、メソッド内にカプセル化した。新しい決済手段が追加されても `processPayment` は無影響。

**原則2「実装ではなくインターフェースに対してプログラムせよ」の現れ**

- 具体化された場所：`PaymentApplication` の `processPayment` メソッド内の `IPaymentProcessor* processor`
- 解説：具体的な決済クラスではなく `IPaymentProcessor` インターフェースだけを知ることで、実行時にどの決済手段が呼び出されるかを気にせず処理フローを進められる。

**原則3「継承よりコンポジションを優先せよ」の現れ**

- 具体化された場所：`PaymentApplication` と決済プロセッサーの接続
- 解説：生成したプロセッサーインスタンスを「利用する（コンポジション）」という関係を保ちつつ、生成の手順だけをメソッドに分離した。継承で新しい手段を追加しようとすると階層が深くなるが、コンポジション＋インターフェースは追加コストを最小化する。

---

## あなたのコードで考えてみてください

1. **変動の兆候を探す：** あなたのコードに「使う具体クラスが条件によって変わる」`if-else` や `switch` があり、新しい種類が増えるたびにそこを書き換えている箇所がありますか？
2. **変える理由を問う：** 「どのクラスを生成するか」という判断は、誰の決定で変わりますか？それは業務ルールの変化ですか、それとも技術的な都合ですか？
3. **結合の強さを測る：** 利用側が具体クラスの名前を直接知っていると、「別の実装に切り替える」ときに利用側も変更する必要がありますか？その変更はどのくらい広がりますか？
4. **分けた後を想像する：** もし「生成の知識」を1か所に集めると、新しい実装を追加するとき変わるファイルはどこだけになりますか？利用側は本当に何も変えなくて済みますか？

---

## パターン解説：Factory Method パターン

### パターンの骨格

Factory Method パターンは、インスタンスの生成をメソッド（またはサブクラス）に委譲することで、具体クラスへの依存を断ち切り、利用側をインスタンス生成の知識から解放するパターンです。

```mermaid
classDiagram
    class Creator {
        <<abstract>>
        +factoryMethod()* Product
        +anOperation()
    }
    class ConcreteCreator {
        +factoryMethod() Product
    }
    class Product {
        <<interface>>
    }
    class ConcreteProduct {
    }
    Creator --> Product
    ConcreteCreator --|> Creator
    ConcreteProduct ..|> Product
```

### この章の実装との対応

GoF（Gang of Four）とは、1994年に出版された書籍『Design Patterns』の4人の著者の総称です。彼らが整理した23のパターンは、現在も設計の共通言語として広く使われています。

| GoFの名前 | この章での対応 |
|---|---|
| Creator | `PaymentApplication`（`createProcessor` を持つ） |
| factoryMethod | `createProcessor(string type)` |
| Product | `IPaymentProcessor` |
| ConcreteProduct | `CreditCardProcessor` / `PayPayProcessor` / `ConvenienceStoreProcessor` |

### 使いどころと限界

- **使うと良い：** クラスが生成するオブジェクトの具体クラスを特定できない場合、または将来的に新しいサブクラスを柔軟に追加したい場合。今後もオブジェクトの種類が増え続けると確定しているとき。
- **使わない方が良い：** 生成するクラスが常に1種類で固定されていて、今後増える見込みがない場合。ファイル数とクラス数が増えるコストが見合わない。

```cpp
// 決済手段が1種類しかなく、今後も増える予定がない場合
// Factory Methodを導入すると、かえって複雑になります。

// ❌ 過剰なFactory（固定クラスをnewするだけなら不要）
class PaymentApplication {
    IPaymentProcessor* createProcessor() {
        return new CreditCardProcessor(); // ← 常にこれだけ
    }
public:
    void processPayment(int amount) {
        IPaymentProcessor* p = createProcessor();
        p->pay(amount);
        delete p;
    }
};

// ✅ この場合はシンプルに直接生成すれば十分
class PaymentApplication {
public:
    void processPayment(int amount) {
        CreditCardProcessor processor;
        processor.pay(amount);
    }
};
```

生成するクラスが常に1種類で固定されているなら、Factoryを介する必要はありません。「今後も変わらない」という確信があるときは、シンプルな直接生成の方が読みやすいコードになります。

### この章のまとめ

この章の冒頭で示した「得られること」4点を、あらためて確認します。

**得られること1**（変動箇所の識別）：フェーズ1とフェーズ2を通じて、「決済プロセッサーの生成ロジック」そのものが変化し続けるものであることを確認しました。実行するクラスの種類が変動箇所になるという視点が得られたはずです。

**得られること2**（変更の痛みの発生源の判断）：フェーズ4で、利用処理が決済手段のクラス名と生成方法を知っていることを確認しました。これが決済手段追加のたびに既存フローを修正する理由です。

**得られること3**（生成責任を分ける効果）：フェーズ6と7で、`createProcessor`へ生成判断を移し、利用側は`IPaymentProcessor`の操作だけを知る構造を学びました。

**得られること4**（利用側が生成知識から解放される視点）：フェーズ6のステップ3で見たように、`processPayment` の中からif文が消え、「どの具体クラスが動くか」を知らずに処理を委譲できるようになった状態がFactory Methodパターンの到達点です。
