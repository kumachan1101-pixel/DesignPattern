## 第1章 変わるものをカプセル化する ―― Strategy パターン

### この章の核心

**計算のルールが変わるたびに、それを呼び出す側のコードまで修正することになる。それは、「変わる理由（個別の割引ルール）」と「変わらない構造（処理の全体的な流れ）」が、同じ場所に混在しているからだ。**

---

### この章を読むと得られること

「割引ルールが増えるたびに、既存の計算ロジックに手を入れなければならない」——この痛みを経験したことがあるなら、この章はそのまま使える答えを持っています。

- **得られること1：** 「実行する振る舞い」という観点で、コードの変動箇所を識別できるようになる
- **得られること2：** 接続点（クラスとクラスのつなぎ目）が「具体×直接」になっているクラスを見て、「変わる理由が異なる知識が同じ場所に混在している」と現状の問題を認識できるようになる
- **得られること3：** 接続点の形を変えると変更がどのように局所化されるかを構造から説明でき、改善後にどんな効果が生まれるかを見通せるようになる
- **得られること4：** 増え続けるルールに対して、いつ・どのように構造を分けるべきかの判断ができるようになる

---

## 🔵 フェーズ1：現状把握 ―― コードとクラス構成を読む

この問題を解くために7つのフェーズを使います。はじめに現状把握から開始し、仮説立案・問題特定・原因分析・課題定義・対策検討・対策実施という順で進みます。

変更要求が来る前のシステムの現状を事実として把握するところから始めます。はじめに仕様と動作例で「このシステムが何をするか」を確認し、それからコードを読みます。
### 1-1：このシステムの仕様

このシステムは、ECサイトでお客様が商品を購入する際の**支払金額を計算**します。

入力として「商品リスト（各商品の名前と単価）」「会員種別（Premium / Regular）」「キャンペーン期間中フラグ（以後キャンペーンフラグ）」を受け取ります。システムは全商品の小計を算出し、以下の割引ルールを適用した最終的な支払金額を返します。
★ここで、これら割引がどのチームからの要求によるものなのかを記載してほしい。他の章も同様です。

**割引ルール一覧**

| ルール名     | 適用条件                        | 割引の内容    |
| -------- | --------------------------- | -------- |
| プレミアム割引  | 会員種別が "Premium"             | 20%引き    |
| キャンペーン割引 | 会員種別が "Regular" かつキャンペーン期間中 | 10%引き    |
| 割引なし     | 上記以外                        | 定価（割引なし） |

**優先・排他ルール**

| 条件 | 動作 |
|---|---|
| Premium かつ キャンペーン中 | Premium のみ適用（キャンペーン割引は無効） |

**この割引計算を使う場所**

| 使用場所 | 用途 |
|---|---|
| 決済計算モジュール | 注文確定時の支払金額の確定 |
| カートプレビュー機能 | カート画面の金額プレビュー表示 |

---

### 1-2：動作例テーブル

仕様を定義したところで、実際にどのような入力に対してどのような結果が返るかを確認します。このテーブルは「このシステムが正しく動いているとはどういう状態か」の基準になります。後で設計の改善（リファクタリング）を段階的に進めるときも、この表に立ち返ります。

| # | 会員種別 | キャンペーン | 小計 | 適用ルール | 支払金額 |
|---|---|---|---|---|---|
| 1 | Premium | ✗ | 10,000円 | プレミアム20%引き | 8,000円 |
| 2 | Premium | ✓ | 10,000円 | プレミアム優先（キャンペーン無効） | 8,000円 |
| 3 | Regular | ✓ | 10,000円 | キャンペーン10%引き | 9,000円 |
| 4 | Regular | ✗ | 10,000円 | 割引なし | 10,000円 |

コードを読む前に、このシステムが「何をする必要があるか」をこの表で確認できました。次は「どのように実装されているか」を見ていきます。
★全般的ですが、まずクラス構成を見て、仕様がどのクラスに紐づいて、どのような全体像になっているか説明した方が良いでしょうか。実際に現場では、設計書があるなら、全体構成やシステム構成を概要押さえてから、ポイント抑えてコードを見始めると思います。なぜなら、何のコードで何やっているか、いきなりコード見てもわからないですよね。ただ、条件として、全体システム構成と仕様の紐づけの説明は必要です。あとは、どんなデータの流れ、どんな責務でやっているか。これをまず説明するのが良いのでしょうか。

---

### 1-3：実装コード（現状）

#### データクラス

はじめに注文のデータを保持するクラス群から見てみます。

```cpp
// 商品クラス：商品名と単価を持つだけのシンプルなクラス
class Item {
public:
    std::string name;
    int price;
    Item(std::string n, int p) : name(n), price(p) {}
};

// 注文データクラス：カートの中身と顧客の属性を保持する
class Order {
public:
    std::vector<Item> items;
    std::string customerType;   // "Regular" または "Premium"
    bool isCampaignActive;      // キャンペーン期間中か
};
```

`Item` と `Order` は純粋なデータの入れ物です。計算のロジックは一切ありません。

#### 決済計算クラス

次に、割引を適用して最終的な支払金額を算出する計算クラスを見ます。

```cpp
class PaymentCalculator {
public:
    int calculate(const Order& order) {
        int total = 0;

        // 小計の計算：注文の全商品を足し合わせる
        for (const auto& item : order.items) {
            total += item.price;
        }

        // 割引ルール：条件ごとに if で分岐している
        if (order.customerType == "Premium") {
            total = static_cast<int>(total * 0.8);   // 20%引き
        } else if (order.customerType == "Regular"
                   && order.isCampaignActive) {
            total = static_cast<int>(total * 0.9);   // 10%引き
        }

        return total;
    }
};
```

このクラスが今章の中心です。`calculate` メソッドの中に「商品の価格を足し合わせる処理」と「割引ルールを判定する処理」が一緒に書かれていることを確認しておいてください。

#### 呼び出し元と実行確認

```cpp
class OrderProcessor {
private:
    PaymentCalculator calculator;
public:
    void process(const Order& order) {
        int finalPrice = calculator.calculate(order);
        std::cout << "支払金額は " << finalPrice << " 円です。\n";
    }
};

int main() {
    OrderProcessor processor;
    Order order;
    order.items.push_back(Item("ワイヤレスイヤホン", 10000));

    // 行1：Premium / キャンペーンなし → プレミアム20%引き
    order.customerType = "Premium";
    order.isCampaignActive = false;
    processor.process(order);

    // 行2：Premium / キャンペーンあり → Premium優先（キャンペーン無効）
    order.customerType = "Premium";
    order.isCampaignActive = true;
    processor.process(order);

    // 行3：Regular / キャンペーンあり → キャンペーン10%引き
    order.customerType = "Regular";
    order.isCampaignActive = true;
    processor.process(order);

    // 行4：Regular / キャンペーンなし → 割引なし
    order.customerType = "Regular";
    order.isCampaignActive = false;
    processor.process(order);

    return 0;
}
```

上記コードの実行結果（動作例テーブルの全4行と一致）：

```
支払金額は 8000 円です。   // 行1：Premium 20%引き
支払金額は 8000 円です。   // 行2：Premium優先（キャンペーン無効）
支払金額は 9000 円です。   // 行3：Regular 10%引き
支払金額は 10000 円です。  // 行4：割引なし
```

動作例テーブルの全4パターンをコードが正しく処理していることを確認できました。次のフェーズで変更が来たときに何が起きるかを確認します。

---

### 1-4：クラス構成図

コードを読んだところで、クラス間の関係を図で整理します。

```mermaid
classDiagram
    class OrderProcessor {
        -PaymentCalculator calculator
        +process(Order)
    }
    class PaymentCalculator {
        +calculate(Order) int
    }
    class Order {
        +vector~Item~ items
        +String customerType
        +bool isCampaignActive
    }
    class Item {
        +String name
        +int price
    }

    OrderProcessor --> PaymentCalculator : 使う
    PaymentCalculator --> Order : 参照する
    Order o-- Item : 持つ
```

`OrderProcessor` が `PaymentCalculator` を使い、`PaymentCalculator` が `Order` の属性を直接参照しています。

---

### 1-5：変更要求

マーケティング部から以下の変更要求が来ました。

「来週から『サマーセール』を開始します。期間中はRegular会員を対象に5%オフを追加してください。プレミアム会員はすでに20%引きが適用されているため、今回のセールは対象外です。」

リリースは来週末。既存の `if` 文の隙間に `else if` を追加すれば間に合うかもしれません。しかし少し立ち止まって、「これは1回限りの変更なのか、今後も続くのか」を確認しましょう。


**仕様変更の内容**

変更要求を受けて、現在の割引ルールがどう変わるかを整理します。

| ルール名 | 変更前 | 変更後 |
|---|---|---|
| プレミアム割引 | Premium会員に20%引き | 変更なし |
| キャンペーン割引 | Regular会員にキャンペーン10%引き | 変更なし |
| **サマーセール割引（新規）** | —（なし） | **Regular会員に5%引きを追加** |

★以下の表の一番下の行は何を意味するのか
★あと、重ねかけってどういう意味か。15％引きになるってことでしょうか。そうであれば、８５００円になるのでは。


**変更後の動作例**

| 会員種別 | キャンペーン | サマーセール | 変更前の支払金額（1万円の場合） | 変更後の支払金額 |
|---|---|---|---|---|
| Premium | ✓ | ✓ | 8,000円（20%引き） | 8,000円（変更なし） |
| Regular | ✓ | ✓ | 9,000円（10%引き） | **8,550円（重ね掛け：5%引き×10%引き）** |
| Regular | ✗ | ✓ | 10,000円（割引なし） | **9,500円（5%引き）** |
| Regular | ✓/✗（どちらでも） | ✗ | 変更なし | 変更なし |

Regular会員はサマーセール中に5%引きが新たに加わります。プレミアム会員はすでに20%引きが適用されているため、今回のサマーセールの対象外となります。

フェーズ1でシステムの現状と変更要求が把握できました。次のフェーズ2では、「何が変わり、何が変わらないか」を整理します。

## 🟣 フェーズ2：仮説立案 ―― 何が変わるかを観察し、ヒアリングで裏付ける

### 2-1：責任チェック表

各クラスが「何を知るべきか」を整理します。
★１文って、いらないよね。何のために入れているのか。責任チェック表は、クラス図の説明のところで持ってきた方が良いのでしょうか

| **クラス名**            | **責任（1文）**            | **知るべきこと**               |
| ------------------- | --------------------- | ------------------------ |
| `OrderProcessor`    | 注文処理の全体フローを進行する       | 計算を誰に依頼するか、結果をどう出力するか    |
| `PaymentCalculator` | 注文内容をもとに最終的な支払金額を計算する | 商品の小計の出し方、適用する必要がある割引ルール |
| `Order`             | 注文された内容と顧客の属性を保持する    | 注文商品のリスト、顧客の種別、キャンペーン状態  |
| `Item`              | 商品一つの情報を保持する          | 商品名、単価                   |

### 2-2：変わる理由の分析

責任チェック表でクラスの責任が整理できました。次に、コードの各行が「誰の判断で変わる知識か」を確認することで、混在している責任をさらに細かく特定します。判断基準は、「このクラスの担当者（ここでは決済システム開発チーム）とは別の人間が変更を決定するかどうか」です。別の人間が決定するなら、それは「責任外（❌）」と判断します。

★責任内かどうかの以下表について、上の責任チェック表を見ると、全て責任範囲内ではないですか。つまり、今の責任は微妙だけど、全て責任内という事になりませんか。ここで言いたいのは、責任の話ではなく、誰の判断で変わるのかが複数のチームの判断で混ざっている事ではないのでしょうか

`PaymentCalculator.calculate()` の各行を見ると：

| **コードの行** | **持っている知識** | **誰の判断で変わるか** | **責任内か** |
|---|---|---|---|
| `total += item.price` | 商品単価を合算するロジック | 決済システム開発チーム | ✅ |
| `if (customerType == "Premium")` | プレミアム会員の条件と割引率 | 会員サービス企画チーム | ❌ 別担当者 |
| `else if (...isCampaignActive)` | キャンペーンの条件と割引率 | マーケティングチーム | ❌ 別担当者 |

1つのメソッドの中に、変える理由が異なる3つの知識が混在しています。今すぐ問題とは言えませんが、これが後の痛みの予兆です。

### 2-3：今回の変更で確実に変わること

今回の変更要求から確定している変更は1点です。

- **サマーセール割引の追加**：Regular会員を対象に5%オフを追加する

ただし「この変更が1回限りか、今後も続くか」によって、どこまで設計を変えるべきかが大きく変わります。関係者に確認します。

### ヒアリングに向けた背景確認

このシステムは、私たちが運用している中堅ECサイトの決済計算を担っています。数年前にサービスが立ち上がった当初は、お客様が商品を選んでカートに入れ、そのままの合計金額で決済するシンプルな流れでした。

しかし、サービスが成長し競合他社との競争が激しくなるにつれて、様々な施策が打たれるようになりました。新規顧客向けの期間限定キャンペーンや、リピーター向けのプレミアム会員制度など、ビジネス上の要求は日々増えています。

### 2-4：関係者ヒアリング

> **現実のヒアリングでは——** 本書のヒアリングシーンでは設計判断を明確にするため、意図的に「理想的な回答」が返ってくるように描いています。これはシミュレーションです。現実には、「変わるかどうか分からない」「たぶん変わらない」という曖昧な答えが返ることも多いです。そのときは `git log` や過去の障害記録を「ヒアリングの代わり」として使ってみてください。「過去に何度変わったか」が最も正直な証拠です。

- **開発者：** 「サマーセールの件、承知しました。今後もこのような新しい割引ルールは追加される予定はありますか？」
- **マーケティング部リーダー：** 「はい、もちろんです。秋にはハロウィンキャンペーン、冬には年末大感謝祭など、毎月のように新しい企画を予定しています。」
- **開発者：** 「ちなみに、割引の計算方法自体が変わることはありますか？今はパーセント引きですが、定額割引などです。」
- **マーケティング部リーダー：** 「実は秋のキャンペーンでは、一律1000円引きクーポンの配布を検討しています。これも対応できますか？」

### 2-5：ヒアリングで判明した将来リスク

ヒアリングで浮かび上がった「確定ではないが、近い将来起こりうる変化」を記録します。これは今回の設計判断の材料です。

| **将来リスク** | **時期の目安** | **根拠** |
|---|---|---|
| 新しい割引ルールの追加が毎月続く | 継続的に | マーケティング責任者から直接確認 |
| 計算方法が「パーセント引き」から「定額引き」に変わる | 数ヶ月後 | 秋のクーポン企画として言及 |

フェーズ2で「今変わること（確定）」と「将来変わるかもしれないこと（リスク）」を分けて整理できました。次のフェーズ3では、現在の構造で変更を試みたときに何が起きるかを確認します。

---

## 🟣 フェーズ3：問題特定 ―― 変更の痛みを発見する

### 3-1：変更を試みる

「サマーセール：Regular会員に5%オフを追加」を現在の `PaymentCalculator` に追加してみます。変更前のコードはこうでした。

```cpp
if (order.customerType == "Premium") {
    total = static_cast<int>(total * 0.8);   // 20%引き
} else if (order.customerType == "Regular"
           && order.isCampaignActive) {
    total = static_cast<int>(total * 0.9);   // 10%引き
}
```

このコードにサマーセールの条件を追加すると、以下のようになります。

```cpp
// サマーセール対応：Regular会員向けに条件を追加
if (order.customerType == "Premium") {
    total = static_cast<int>(total * 0.80);  // 20%引き（サマーセール対象外）
} else if (order.isSummerSale && order.isCampaignActive) {
    total = static_cast<int>(total * 0.95 * 0.90); // 重ね掛け（Regular会員）
} else if (order.isSummerSale) {
    total = static_cast<int>(total * 0.95);  // 5%引き（Regular会員）
} else if (order.isCampaignActive) {
    total = static_cast<int>(total * 0.90);  // 10%引き
}
```

この変更後コードを見ると、問題が浮かび上がります。

一見シンプルな追加に見えますが、サマーセールは「Regular会員のみ」「キャンペーンと重複した場合は重ね掛け」という複合条件を持っています。単純に `else if` を1行追加するだけでは済まず、`isSummerSale && isCampaignActive` の組み合わせを考慮した分岐も追加する必要があります。さらに、`Order` クラスに `isSummerSale` フラグを追加しなければなりません。

```cpp
// Order クラスへの変更（サマーセールフラグの追加が必要）
class Order {
public:
    std::vector<Item> items;
    std::string customerType;
    bool isCampaignActive;
    bool isSummerSale;   // ← 追加。データクラスにまでフラグが増え続ける
};
```

ヒアリングで予告された「1000円引きクーポン」が来た場合はどうでしょうか。パーセント計算とは異なる「引き算」のロジックが混入し、全ての `if` ブロックの計算順序を見直す必要が出てきます。

### 3-2：変更影響グラフ

```mermaid
graph LR
    T1["変更要求：サマーセール追加"] -->|影響| A["PaymentCalculator<br>（既存の条件分岐全体）"]
    A -->|さらに影響| B["Order<br>（新しいフラグの追加）"]
    A -->|さらに影響| C["CartPreviewService<br>（同じif文の重複）"]
```

新しいルールを1つ追加するだけで、既存の計算ロジック全体・データクラス・カートプレビューにまで影響が波及しています。

### 3-3：痛みの言語化

**1つ目：影響範囲が読めない恐怖。** 新しい割引を追加するには、複雑化しつつある `if-else` の隙間にコードを差し込む必要があります。変更のたびに、無関係なはずの過去のルールも含めて全テストケースを見直す必要があります。

**2つ目：grep地獄。** キャンペーンのたびに条件分岐が追加されていくと、半年後には `PaymentCalculator` が数百行の複雑な分岐の塊になります。「どの条件が今のキャンペーンのものか」を理解するために、コードの隅々まで解読しなければなりません。2種類の電圧が1本のケーブルに混在しているような状態。触れると回路全体に影響が走る。★ケーブルの例え話よくわからないのでやめて。本当にgrep時刻になるのでしょうか。クラスとしては責任としては全うしているように見えます。しかも、タイミング依存で変動するようなものでもありません。つまり、どこで使っていようが関係ないと思います。フェーズ４の原因の表にも紐づく話です。

---
> **📌 問題（確定）**
> 割引という「実行する振る舞い」が変わるたびに、`PaymentCalculator`・`Order`・`CartPreviewService` の3か所が連動して変わる。変わる理由が異なるコードが同じ場所に混在しているため、1か所の修正が他への影響確認を強いる。
---

フェーズ3で「変更が辛い」ことが確認できました。次のフェーズ4では、なぜ辛いのかを構造的に言語化します。

---

## 🟠 フェーズ4：原因分析 ―― なぜ辛いのかを構造で言語化する

### 4-1：痛みの根源を探る（観察と原因）

フェーズ3で確認した「変更の辛さ」は、コードのどこから来ているのでしょうか。コードを注意深く観察すると、痛みを引き起こしている2つの事実が浮かび上がってきます。

第一に、新しい割引を追加するとき、なぜ毎回 `PaymentCalculator` を開かなければならないのでしょうか？
★責任チェック表から、現状はそういう責任なんだからしょうがないよね。責任が見直す必要があるという話にもっていった方が良いのでは。複数のチームからの変更要求を１つのクラスでになっている事が、この問題構造を引き起こしている原因ではないのでしょうか。だから、仕様変更が１つのクラスに密集してしまう。

それは、このクラス自身が「プレミアム会員なら20%引き」「サマーセールなら5%引き」といった**具体的な割引の条件をすべて直接知ってしまっている（抱え込んでいる）**からです。

第二に、なぜ変更の影響範囲が読めず、全テストをやり直す恐怖を感じるのでしょうか？
それは、「商品をループで回して金額を足し合わせる」という土台となる骨格ロジックと、「特定のキャンペーンを判定して割引する」というビジネスロジックが、**同じメソッドの中で物理的に混ざり合っている**からです。

この「症状（痛み）」と「根本原因」を整理すると、以下のようになります。

| **観察した症状（痛み）** | **構造的な原因（痛みの根源）**                                                                                                                    |
| -------------- | ------------------------------------------------------------------------------------------------------------------------------------ |
| 影響範囲が読めない恐怖    | `PaymentCalculator` が各割引の具体的な条件を直接知っているから                                                                                            |
| grep地獄・複雑化     | 変わる理由が違う2つのもの（「合算ロジック」と「割引条件」）が同じメソッドの中に混在しているから。USBのように端子を分けておらず、基板に直差ししている状態と同じで、端子の形が変わるたびに本体側の配線を開け直す必要がある★ここの説明が意味が分かりませんので修正して |

### 4-2：変わるもの/変わってほしくないもの

> **「変わらないもの」と「変わってほしくないもの」は異なります。** 「変わらないもの」は経験的事実（今まで変わっていない）、「変わってほしくないもの」は設計意図（ここを安定させてほかを守りたい）です。ここで整理するのは後者です。

| **変わるもの（割引ルール）** | **変わってほしくないもの（計算骨格）** |
|---|---|
| 各キャンペーンの適用条件（サマーセール、ハロウィン等） | 商品単価を順番に足す合算ロジック |
| 割引額の計算方法（パーセント引き・定額引きなど） | 計算を依頼して最終金額を受け取る呼び出し側のフロー |

**【変わる部分（変わり続けるif文と計算）】**

1-3で示した `calculate` メソッドの割引判定ブロックが、キャンペーンのたびに変わる箇所です。

```cpp
        if (order.customerType == "Premium") {
            total = static_cast<int>(total * 0.8);   // 20%引き
        } else if (order.isSummerSale && order.isCampaignActive) {
            total = static_cast<int>(total * 0.95 * 0.90); // 複合割引
        // ← 新しいキャンペーンが来るたびに、ここにelse ifが追加される
```

**【変わってほしくない部分（守りたい骨格）】**

1-3の `calculate` メソッドのうち、「商品を順に足して合計を出し、最終金額を返す」という骨格部分は変えたくありません。

```cpp
        int total = 0;
        for (const auto& item : order.items) {
            total += item.price;             // 小計計算（変えたくない）
        }
        // ← ここに「変わる部分」（割引判定）が割り込んでいる
        return total;                        // 結果を返す（変えたくない）
```

### 4-3：接続形態の診断

現在の `PaymentCalculator` は、すべての割引ルールを自分自身の中に直接抱え込んでいます。
★急に具体直接と記載されてもなんのはないかわかりません。もっと前置きの説明があるのでは？このクラスとこのクラスはこういうデータを直接、複数結び付けている。密結合になっている。また抽象クラスではなく、具体クラスで複数の同じデータで処理を分岐させている構造は、見直した方が良いという課題があるという事ですよね。何かしら説明を入れてくれないと、具体直接形態って何ってなるし。他の章も見直して

**【具体×直接のコード】**
```cpp
class PaymentCalculator {
public:
    int calculate(const Order& order) {
        // ← 1-3で示した合算ループ（for + total += item.price）がここに入る
        // 割引ルール（具体）を、自分自身で直接判断して処理している
        if (order.customerType == "Premium") {
            total = static_cast<int>(total * 0.8);
        }
        // ← 1-3で示した他のelse ifブロックがここに続く
    }
};
```

この状態は **「具体×直接」の接続形態** です。iPhoneに専用のLightningケーブルを直差ししている状態と同じで、新しいキャンペーンが増えるたびに本体側を開いて専用の配線（`else if` 文）を直接追加しなければなりません。

決済の合算ロジックと個別の割引ルールは、変わる理由が全く異なります。これらが同じ場所に混在していることが、根本原因として確認できました。

私たちは今、最も密結合で変更に弱い「具体×直接」の地点にいます。

---
> **📌 原因（確定）**
> 「具体×直接」はルールが変わらないなら問題にならない。問題になるのは、割引ルールが「毎月追加される」とヒアリングで確定しているのに、その全種類を `PaymentCalculator` が直接抱え込んでいる場合だ。追加のたびに `PaymentCalculator` を開かなければならない。
---

フェーズ4で根本原因が言語化できました。「どこを分けるか」は明確です。次のフェーズ5では、その境界で実際に何が流れているかを値・型のレベルで具体化し、「何が変わり、何が変わらないか」を明確にします。

---

## 🟡 フェーズ5：課題定義 ―― 接続点で何が流れているかを見る

フェーズ4は「なぜ辛いか」を答えました。フェーズ5が問うのは「分けるべき境界で、実際に何が流れているか」です。クラスの参照関係ではなく、**値・型のレベル**に降りていきます。

フェーズ4の分析により、問題は「計算の骨格」と「割引の条件分岐」が混在していることだと分かりました。その境界で何がやり取りされているかを具体化します。

### 接続点を特定する

`calculate()` の中で分けるべき境界は1か所。「割引を計算する側」が骨格に渡しているデータを見ます。

```cpp
        // 骨格（変わらない）
        for (const auto& item : order.items) {
            total += item.price;
        }

        // ↓ 割引の生産者（変わり続ける）
        if (order.customerType == "Premium") {
            total = static_cast<int>(total * 0.8);
        } else if (order.isSummerSale && order.isCampaignActive) {
            total = static_cast<int>(total * 0.95 * 0.90);
        } else if (order.isSummerSale) {
            total = static_cast<int>(total * 0.95);
        } else if (order.isCampaignActive) {
            total = static_cast<int>(total * 0.90);
        }
        // ↑ ここまでが分離するターゲット

        return total;
```

割引の生産者が骨格に渡しているのは「割引適用後の合計金額（`int`）」です。

| 接続点 | 接続するデータ | 変わるもの |
|---|---|---|
| 割引ロジック → `calculate()` の骨格 | `int` 型の割引適用後の合計金額 | 計算ロジック（誰がどう割引するか） |

### 何が変わり、何が変わらないか

- **変わるもの**：割引の計算ロジック（生産者）。新しいキャンペーンや顧客種別のたびに増える。
- **変わらないもの**：流れるデータの型（`int` 型の金額）。`CartPreviewService` が受け取る値の形は変わらない。

呼び出し元は「金額を渡してもらえれば十分」なので安定しています。問題は「どのように計算するか」という**生産者の側**が膨れ続けていること。

**具体×直接のままでよい場面**：割引ルールが今後増えない確証があれば、`if-else` のまま（具体×直接）で十分です。接続形態の選択は「**生産者が変わるかどうか**」で決まります。今回は増え続けることがヒアリングで確認済みなので、次のフェーズで生産者を差し替えられる設計を検討します。

---
> **📌 課題（確定）**
> 割引ルールが増え続けると確定している以上、`PaymentCalculator` がその全種類を直接知り続ける設計はコストが合わない。割引ロジックを外から差し替えられるようにし、`PaymentCalculator` は受け取るだけにする。
---

## 🔴 フェーズ6：対策検討 ―― 段階的な改善と決断

フェーズ5で「変わるのは生産者（計算ロジック）であり、流れるデータの型は安定している」ことが分かりました。ここでは、その生産者をどのように差し替え可能にするかを段階的に検討します。いきなり正解へ飛ぶのではなく、各ステップで「どこまで痛みが解消されるか」を確認しながら、今回の要件において「どのステップで止めるべきか」を決断します。

### ステップ1：プライベートメソッドに切り出す（同じクラスの中で整理する）

「if-else が乱立しているなら、まずそれをメソッドに切り出して整理しよう」というのが自然な最初の発想です。クラスを新しく作るのはコストがかかる。同じクラスの中で、割引の塊をプライベートメソッドとして分離してみます。

```cpp
class PaymentCalculator {
    // 割引の条件と計算をプライベートメソッドに切り出す
    int applyDiscount(int total, const Order& order) {
        if (order.customerType == "Premium")
            return static_cast<int>(total * 0.80);
        if (order.isSummerSale && order.isCampaignActive)
            return static_cast<int>(total * 0.95 * 0.90);
        if (order.isSummerSale)
            return static_cast<int>(total * 0.95);
        if (order.isCampaignActive)
            return static_cast<int>(total * 0.90);
        return total;
    }
public:
    int calculate(const Order& order) {
        int total = 0;
        for (const auto& item : order.items) total += item.price;
        return applyDiscount(total, order); // 骨格が読みやすくなった
    }
};
```

`calculate()` の骨格は一目で読めるようになり、割引の詳細は `applyDiscount()` の中に隠れた。

**この段階の評価：** `calculate()` は確かにスッキリしました。しかし整理できたのは「見た目」だけです。新しい割引が来るたびに `applyDiscount()` を開いて `else if` を書き足す、という根本は何も変わっていません。整理できたが、新しい割引が来るたびに同じクラスを修正する根本は変わっていない。「クラスを分ける」方向を試してみましょう。

---

### ステップ2：各割引を別のクラスに切り出す（具体×直接）

★私なら、クラスをいきなり分けず、判定分を関数に別途分けてみようとしますが、どうですか。そこで、１つのクラスが膨大になっている事に気づき、クラスを分けようという思考になります。

「割引ロジックが増えてきたなら、それぞれを別のクラスにしよう」という発想は自然です。ステップ1では1つのメソッドに詰め込んでいましたが、今度は割引の種類ごとにクラスを作ってみます。

```cpp
// 割引ごとに別のクラスに分けた（インターフェースはまだない）
class PremiumDiscount {
public:
    int apply(int total) { return static_cast<int>(total * 0.80); }
};

class SummerSaleDiscount {
public:
    int apply(int total) { return static_cast<int>(total * 0.95); }
};

class CampaignDiscount {
public:
    int apply(int total) { return static_cast<int>(total * 0.90); }
};

class PaymentCalculator {
public:
    int calculate(const Order& order) {
        int total = 0;
        for (const auto& item : order.items) total += item.price;

        // ← if文はここに残ったまま。しかも全具体クラスを知らなければならない
        if (order.customerType == "Premium") {
            PremiumDiscount rule;
            return rule.apply(total);
        } else if (order.isSummerSale && order.isCampaignActive) {
            SummerSaleDiscount s;
            CampaignDiscount c;
            return c.apply(s.apply(total));
        } else if (order.isSummerSale) {
            SummerSaleDiscount rule;
            return rule.apply(total);
        } else if (order.isCampaignActive) {
            CampaignDiscount rule;
            return rule.apply(total);
        }
        return total;
    }
};
```

各割引の計算ロジックが別クラスに分かれ、それぞれのクラスは小さくなった。

**この段階の評価：** 割引の計算が別ファイルに分かれたのは良い変化です。しかし `PaymentCalculator` は `PremiumDiscount`・`SummerSaleDiscount`・`CampaignDiscount` の全クラス名を直接知っており、if文も本体に残ったままです。新しい割引が来るたびに新しいクラスを作るのと同時に `PaymentCalculator` の中の if 文も書き足さなければなりません。クラスに分けられたが、`PaymentCalculator` が全クラスを直接知っている問題は残っています。「直接知る」という部分を何とかできないか、考えてみましょう。

---

### ステップ3：インターフェースを導入するが、生成は自分で行う（抽象×直接）

「全クラスを直接知っているのが問題なら、共通のインターフェースを作ってそれだけを知ればいい」という発想です。`IDiscountRule` インターフェースを導入し、`PaymentCalculator` はそれだけを知るようにします。ただし、どの具体クラスを生成するかはまだ `PaymentCalculator` 自身が if 文で判断します。

```cpp
// 共通のインターフェース（契約）を導入する
class IDiscountRule {
public:
    virtual int apply(int total) = 0;
    virtual ~IDiscountRule() = default;
};

class PremiumDiscount : public IDiscountRule {
public:
    int apply(int total) override { return static_cast<int>(total * 0.80); }
};

class SummerSaleDiscount : public IDiscountRule {
public:
    int apply(int total) override { return static_cast<int>(total * 0.95); }
};

class CampaignDiscount : public IDiscountRule {
public:
    int apply(int total) override { return static_cast<int>(total * 0.90); }
};

class PaymentCalculator {
public:
    int calculate(const Order& order) {
        int total = 0;
        for (const auto& item : order.items) total += item.price;

        // ← 型は抽象（IDiscountRule*）になったが、
        //   どれを生成するかの判断はまだif文に残っている
        IDiscountRule* rule = nullptr;
        PremiumDiscount premium;
        SummerSaleDiscount summer;
        CampaignDiscount campaign;

        if (order.customerType == "Premium") {
            rule = &premium;
        } else if (order.isSummerSale) {
            rule = &summer;
        } else if (order.isCampaignActive) {
            rule = &campaign;
        }

        return rule ? rule->apply(total) : total;
    }
};
```

`PaymentCalculator` が持つ型は `IDiscountRule*` という抽象型になり、具体クラスのメソッドを直接呼ぶ行は消えた。

**この段階の評価：** 型を抽象化できたのは前進です。しかし `PaymentCalculator` はまだ `PremiumDiscount` や `SummerSaleDiscount` という具体クラス名を知っており、if 文で生成を選んでいます。新しい割引クラスを追加するとき、`PaymentCalculator` の中の if 文も書き足さなければなりません。加えて、この `else if` の連鎖は、「Regular会員でSummerSale中かつキャンペーン中（重ね掛け：8,550円）」のケースを正しく表現できません。`isSummerSale` が真であれば `CampaignDiscount` は無視されるためです。この問題はステップ4で `SummerSaleAndCampaignDiscount` を追加することで解決します。型は抽象化できたが、どれを生成するかの判断はまだ if 文に残っている。「生成の選択」そのものを外に出せれば、`PaymentCalculator` から if 文が消えるはずです。

---

### ステップ4：ルールを外から受け取る（依存性の注入・Strategy）

「`PaymentCalculator` が自分でルールを生成するから if 文が必要になる。なら、外からルールを渡してもらえばいい」という発想です。どのルールを使うかを決める責任を呼び出し側に移し、`PaymentCalculator` はただ受け取って使うだけにします。

```cpp
class IDiscountRule {
public:
    virtual int apply(int total) = 0;
    virtual ~IDiscountRule() = default;
};

class PremiumDiscount : public IDiscountRule {
public:
    int apply(int total) override { return static_cast<int>(total * 0.80); }
};

class SummerSaleDiscount : public IDiscountRule {
public:
    int apply(int total) override { return static_cast<int>(total * 0.95); }
};

class SummerSaleAndCampaignDiscount : public IDiscountRule {
public:
    int apply(int total) override {
        return static_cast<int>(total * 0.95 * 0.90);
    }
};

class CampaignDiscount : public IDiscountRule {
public:
    int apply(int total) override { return static_cast<int>(total * 0.90); }
};

class NoDiscount : public IDiscountRule {
public:
    int apply(int total) override { return total; }
};

// ← コンストラクタでルールを受け取る。自分では生成しない
class PaymentCalculator {
private:
    IDiscountRule* rule;
public:
    PaymentCalculator(IDiscountRule* r) : rule(r) {}

    int calculate(const Order& order) {
        int total = 0;
        for (const auto& item : order.items) total += item.price;
        return rule->apply(total); // if文がなくなり、無傷の骨格になった
    }
};

// ─── 呼び出し側：どのルールを使うかはここで決める ───
void processOrder(const Order& order) {
    PremiumDiscount premium;
    SummerSaleAndCampaignDiscount both;
    SummerSaleDiscount summer;
    CampaignDiscount campaign;
    NoDiscount none;

    // かつてPaymentCalculatorの中にあったif文がここに移動した
    // 実行結果は一切変わらず、判断の責任だけが外側に押し出された
    IDiscountRule* rule = &none;
    if (order.customerType == "Premium") {
        rule = &premium;
    } else if (order.isSummerSale && order.isCampaignActive) {
        rule = &both;
    } else if (order.isSummerSale) {
        rule = &summer;
    } else if (order.isCampaignActive) {
        rule = &campaign;
    }

    PaymentCalculator calculator(rule);
    int finalPrice = calculator.calculate(order);
}
```

`PaymentCalculator` の中から `if` 文が完全に消え、`IDiscountRule* rule` を受け取って使うだけの無傷の骨格になった。

**この段階の評価：** `PaymentCalculator` からすべての割引判断が消えました。新しい割引が来たとき、触るのは新しいクラスを1つ追加することと、呼び出し側の if 文だけです。`PaymentCalculator` 本体には一切手を入れなくて済みます。これが今回目指した「変わる理由の分離」の到達点です。

---

### どこまで設計を進めるべきか（採用ステップの決断）

それぞれのステップには一長一短があります。ステップ4のインターフェース化は強力ですが、ファイル数や型が増えるという「初期投資コスト」もかかります。どこで止めるかは、**「今後の変更頻度（ビジネス要求）」**で決断します。

*   **ステップ1（プライベートメソッド化）で止めるケース：** 「今回限りの特例」の場合。見た目を整理するだけで十分です。
*   **ステップ2（具体クラスへの分離）で止めるケース：** ファイルを分けて整理したいが、インターフェース導入のコストをまだかけたくない場合の「中間策」です。
*   **ステップ3（インターフェース化・生成は自分）で止めるケース：** 型を統一したいが、呼び出し側にルール選択の責任を渡す準備がまだできていない場合。
*   **ステップ4（依存性の注入）まで進むケース：** 「毎月新しい割引が追加される」と確定している場合。今すぐ初期投資コストを払ってでも、将来の変更コストをゼロにするのが適切です。

**今回の決断：**
フェーズ2のヒアリングで、マーケティング責任者から「今後も毎月ルールが追加される」と明言されています。したがって、今回は迷わず**ステップ4（インターフェース化・依存性の注入）まで進化させる**決断を下します。

このように、変わるロジック（割引ルール）をインターフェースで分離し、呼び出し側から自由に差し替え可能にするこの設計構造を **Strategy（ストラテジー）パターン** と呼びます。

フェーズ6で採用ステップが決まりました。次のフェーズ7では、この決断を最終的なコードに落とし込みます。

## 🟢 フェーズ7：対策実施 ―― 変化に強いコードを完成させる

### 7-1：解決後のコード（全体）

ステップ4で決断した構造を、実行可能な完全なコードとして組み上げます。各役割ごとにコードを分けて見ていきましょう。

**1. データの定義とインターフェース（契約）**
計算に必要なデータクラスと、すべての割引ルールが守るべき共通のインターフェースを定義します。

```cpp
#include <iostream>
#include <string>
#include <vector>

class Item {
public:
    std::string name;
    int price;
    Item(std::string n, int p) : name(n), price(p) {}
};

class Order {
public:
    std::vector<Item> items;
    std::string customerType;
    bool isCampaignActive;
    bool isSummerSale;   // サマーセール期間中か
};

// 割引ルールの共通インターフェース（Strategy）
class IDiscountRule {
public:
    virtual int apply(int total) = 0;
    virtual ~IDiscountRule() = default;
};
```

**2. 個別の割引ルールの実装（具体）**
インターフェースを満たす具体的な割引クラスを作成します。本体コードに触れることなく、このクラス群だけを自由に追加・変更できます。

```cpp
class NoDiscount : public IDiscountRule {
public:
    int apply(int total) override { return total; }
};

class PremiumDiscount : public IDiscountRule {
public:
    int apply(int total) override {
        return static_cast<int>(total * 0.80);
    }
};

class SummerSaleAndCampaignDiscount : public IDiscountRule {
public:
    int apply(int total) override {
        return static_cast<int>(total * 0.95 * 0.90);
    }
};

class SummerSaleDiscount : public IDiscountRule {
public:
    int apply(int total) override {
        return static_cast<int>(total * 0.95);
    }
};

class CampaignDiscount : public IDiscountRule {
public:
    int apply(int total) override {
        return static_cast<int>(total * 0.90);
    }
};
```

**3. 本体クラス（コンテキスト）**
計算を行う本体クラスです。具体的な割引ルールを知らず、インターフェースだけを通じて計算を委譲します。これにより、if文が存在しない無傷の骨格が完成します。

```cpp
class PaymentCalculator {
private:
    IDiscountRule* rule;
public:
    PaymentCalculator(IDiscountRule* r) : rule(r) {}

    int calculate(const Order& order) {
        int total = 0;
        for (const auto& item : order.items) total += item.price;
        return rule->apply(total);
    }
};

// カートプレビュー機能も同じインターフェースを使い回せる
// フェーズ3で発見した「同じif文の重複」問題は、このインターフェース共有によって自動的に解消される
class CartPreviewService {
private:
    IDiscountRule* rule;
public:
    CartPreviewService(IDiscountRule* r) : rule(r) {}

    int getEstimatedTotal(const Order& order) {
        int total = 0;
        for (const auto& item : order.items) total += item.price;
        return rule->apply(total);
    }
};
```

**4. 組み立てと実行（メイン関数）**
最後に、必要な部品を組み立てて実行します。具体的なクラス名（`PremiumDiscount`等）を知っているのは、この組み立てを行う箇所だけです。

```cpp
// ルールを選択するファクトリ（かつて本体にあったif文を隔離する場所）
class RuleFactory {
public:
    // メモリ管理を簡略化するため、今回は静的なインスタンスのポインタを返します
    static IDiscountRule* create(const Order& order) {
        static PremiumDiscount premium;
        static SummerSaleAndCampaignDiscount both;
        static SummerSaleDiscount summer;
        static CampaignDiscount campaign;
        static NoDiscount none;

        // 実行結果を変えないため、元のコードと全く同じif文が存在する
        if (order.customerType == "Premium") return &premium;
        if (order.isSummerSale && order.isCampaignActive) return &both;
        if (order.isSummerSale) return &summer;
        if (order.isCampaignActive) return &campaign;
        return &none;
    }
};

class BatchApplication {
public:
    void run() {
        Order order;
        order.items.push_back(Item("ワイヤレスイヤホン", 10000));
        order.customerType = "Premium";
        order.isCampaignActive = false;

        // 組み立て役がif文でルールを選び、本体に注入する（DI）
        IDiscountRule* rule = RuleFactory::create(order);
        
        PaymentCalculator calculator(rule);
        CartPreviewService preview(rule);

        int finalPrice = calculator.calculate(order);
        int previewPrice = preview.getEstimatedTotal(order);

        std::cout << "支払金額: " << finalPrice << " 円\n";
        std::cout << "プレビュー: " << previewPrice << " 円\n";
    }
};

int main() {
    BatchApplication app;
    app.run();
    return 0;
}
```

★現状把握の実装コードに対して仕様変更を加えた実行結果にしてくれませんか。
★実行結果が同じだが、システム構成は大きく違う点を示したい。他の章も同様です。

上記コードの実行結果：

```
支払金額: 8000 円
プレビュー: 8000 円
```

動作例テーブルの行1（Premium / キャンペーンなし / 10,000円 → 8,000円）と一致しています。`PaymentCalculator` の中から `if` 文が完全に消えました。

### 7-2：動作シーケンス図

ステップ4で到達したStrategyパターンの実行時のオブジェクト間のやり取りを可視化します。`main()` が依存関係を注入し、`PaymentCalculator` が具象クラスを知らずに抽象インターフェース経由で処理を委譲する流れが確認できます。

```mermaid
sequenceDiagram
    participant B as BatchApplication
    participant P as PaymentCalculator
    participant I as IDiscountRule<br/>(PremiumDiscount)

    B->>B: 注文データ作成
    B->>I: 生成 (RuleFactory::create)
    B->>P: 生成 (rule を注入)
    B->>P: calculate(order)
    activate P
    P->>I: apply(total)
    activate I
    I-->>P: 計算結果を返す
    deactivate I
    P-->>B: finalPrice を返す
    deactivate P
```

### 7-3：変更影響グラフ（改善後）

```mermaid
graph LR
    T1["変更要求：新しい割引ルールの追加"] --> F1["新しい割引クラス（新規作成）"]
    T1 -. "影響なし" .-> A["PaymentCalculator ✅"]
    T1 -. "影響なし" .-> B["CartPreviewService ✅"]
```

フェーズ3の変更影響グラフと比べると、変更要求が新規クラスの作成だけに閉じるようになりました。

### 7-4：変更シナリオ表

| **シナリオ** | **変わるクラス** | **変わらないクラス** |
|---|---|---|
| サマーセール追加 | `SummerSaleDiscount`（新規作成） | `PaymentCalculator`, `CartPreviewService` |
| クーポン割引（定額）導入 | `CouponDiscount`（新規作成） | `PaymentCalculator`, `CartPreviewService` |
| プレミアム割引率の変更 | `PremiumDiscount`（1行修正） | `PaymentCalculator`, `CartPreviewService` |

---

## 整理

★今までの指摘を踏まえると、以下の大きく見直しが必要ですので、見直してください。
### この章で定義したこと

| | 内容 |
|---|---|
| **問題** | 割引の「実行する振る舞い」が変わるたびに3か所が連動して変わる。変わる理由が異なるコードが同じ場所に混在しているため |
| **原因** | 割引ルールが「毎月追加される」と確定しているのに、`PaymentCalculator` が全種類を直接抱え込んでいる（この変化の頻度では「具体×直接」のコストが合わない） |
| **課題** | 割引ロジックを外から差し替えられるようにし、`PaymentCalculator` は受け取るだけにする |
| **解決策** | Strategy パターン：`IDiscountRule` を接続点として、外からルールを注入する |

### フェーズとこの章でやったこと

| **フェーズ** | **この章でやったこと** |
|---|---|
| 🔵 フェーズ1：現状把握 | 仕様と動作例テーブルを確認した後、コードをクラス単位で読んだ。クラス構成図と変更要求を把握した |
| 🟣 フェーズ2：仮説立案 | 責任チェック表でクラスごとの変わる理由を確認した。今回の確定変更とヒアリングで判明した将来リスクを分けて整理した |
| 🟣 フェーズ3：問題特定 | サマーセールの追加を試み、影響が `Order` と `CartPreviewService` にまで波及することを確認した |
| 🟠 フェーズ4：原因分析 | 変わる理由が異なる2つのものが同じ場所にいることが痛みの根本と特定した |
| 🟡 フェーズ5：課題定義 | 接続点で流れるのは `int` 型の金額（安定）、変わるのは計算ロジック（生産者）であることを特定した |
| 🔴 フェーズ6：対策検討 | 4ステップの段階的進化でそれぞれの痛みの限界を確認し、ステップ4（インターフェース化・依存性の注入）まで進化させる決断を下した |
| 🟢 フェーズ7：対策実施 | 最終コードを実装し、変更影響グラフで変更の局所化を確認した |

### 責任の移動

| **責任** | **変更前** | **変更後** |
|---|---|---|
| 決済の計算フローの進行 | `PaymentCalculator` | `PaymentCalculator`（変わらず） |
| 個別の割引計算の実行 | `PaymentCalculator`（if-else直書き） | `PremiumDiscount` 等の各実装クラス |
| 割引ルールの契約定義 | —（なし） | `IDiscountRule` |

---

## 振り返り

### 「この章を読むと得られること」は手に入ったか

| **得られること** | **この章のどこで示したか** |
|---|---|
| 1. 変動箇所の識別 | フェーズ2の責任チェック表で、変わる理由の異なる知識の混在を発見した |
| 2. 接続形態の診断 | フェーズ4で「具体×直接」の状態を診断した |
| 3. 変更局所化の説明 | フェーズ7の変更シナリオ表で、変更が新規クラスに閉じる構造を示した |
| 4. いつ構造を分けるか | フェーズ6の「どこまで設計を進めるべきか」で判断基準を示した |

★もし０章の３つ原則を修正した場合、以下も見直して
### 3つの設計原則はどう適用されたか

**原則1「変わるものをカプセル化せよ」の現れ**

- 具体化された場所：`PremiumDiscount` / `SummerSaleDiscount` 等の実装クラス
- 解説：頻繁に変わる「割引の計算詳細」を個別クラスに閉じ込めた。新しいルールが追加されても `PaymentCalculator` は無影響。

**原則2「実装ではなくインターフェースに対してプログラムせよ」の現れ**

- 具体化された場所：`PaymentCalculator` のメンバ変数 `IDiscountRule* rule`
- 解説：具体的な割引クラスではなく `IDiscountRule` インターフェースだけを知ることで、実行時にどの割引が適用されるかを気にせず計算フローを進められる。

**原則3「継承よりコンポジションを優先せよ」の現れ**

- 具体化された場所：`PaymentCalculator` と割引ルールの接続
- 解説：（もし継承を使って新しいルールを追加しようとすると）継承を使うとルールごとにクラス階層が深くなる。コンストラクタインジェクションによるコンポジション（オブジェクトを内部に保持して機能を借りる仕組み）は、複数ルールの組み合わせも将来的に可能にする。

---

## あなたのコードで考えてみてください

1. **変動の兆候を探す：** あなたのコードに「条件が1つ増えるたびに、既存の `if-else` チェーンを開いて書き足している」メソッドがありますか？
2. **変える理由を問う：** そのメソッド内の各条件は、誰の判断で変わりますか？同じチームで完結していますか、それとも複数の部門が絡んでいますか？
3. **テストの範囲を測る：** 新しい条件を1つ追加したとき、再確認が必要だったテストは何件でしたか？
4. **分けた後を想像する：** 「変わる計算ロジック」を別クラスに切り出したとすると、次の変更要求が来たとき、触らなくて済むファイルはどこですか？

---

## パターン解説：Strategy パターン

### パターンの骨格

Strategy パターンは、アルゴリズムのファミリーを定義し、それぞれをカプセル化して、呼び出し側から自由に差し替えられるようにするパターンです。

```mermaid
classDiagram
    class Context {
        -Strategy* strategy
        +execute()
    }
    class Strategy {
        <<interface>>
        +algorithm()
    }
    class ConcreteStrategyA {
        +algorithm()
    }
    class ConcreteStrategyB {
        +algorithm()
    }
    Context o--> Strategy
    ConcreteStrategyA ..|> Strategy
    ConcreteStrategyB ..|> Strategy
```

### この章の実装との対応

GoF（Gang of Four）とは、1994年に出版された書籍『Design Patterns』の4人の著者の総称です。彼らが整理した23のパターンは、現在も設計の共通言語として広く使われています。

| GoFの名前 | この章での対応 |
|---|---|
| Context | `PaymentCalculator` / `CartPreviewService` |
| Strategy | `IDiscountRule` |
| ConcreteStrategy | `PremiumDiscount` / `SummerSaleDiscount` / `CampaignDiscount` 等 |

### 使いどころと限界

- **使うと良い：** 似たような振る舞いが複数あり、状況に応じて切り替えたい場合。または今後も新しいアルゴリズムが追加される可能性が高い場合。
- **使わない方が良い：** ルールが1種類しかなく、今後増える見込みがない場合。ファイル数とクラス数が増えるコストが見合わない。

### この章のまとめ

この章の冒頭で示した「得られること」4点を、あらためて確認します。

**得られること1**（変動箇所の識別）：フェーズ1とフェーズ2を通じて、「割引ルール」というアルゴリズム自体が変化し続けるものであることを確認しました。実行する振る舞いそのものが変動箇所になるという視点が得られたはずです。

**得られること2**（変更の痛みの発生源の判断）：フェーズ3〜4で、条件分岐を使って各種計算ロジックを直書きしている状態を「具体×直接」の接続と診断しました。この接続形態は「変わる理由が異なる知識が同じ場所に混在している」状態であり、仕様変更のたびに既存コードを壊すリスク（痛みの発生源）になっていると判断できるようになります。

**得られること3**（接続の形の効果を説明する）：フェーズ6と7で、「抽象×間接」へと接続の形を変えることで、既存の計算フローには一切触れずに新しい割引ルールを追加できるようになること（変更の局所化）を学びました。

**得られること4**（構造を分ける判断）：フェーズ6の「どこまで設計を進めるべきか」で見たように、ルールが一つしかない状態から、今後も増え続けると予想される状態へと変化したタイミングこそが、Strategyパターンへの移行を決断する時です。