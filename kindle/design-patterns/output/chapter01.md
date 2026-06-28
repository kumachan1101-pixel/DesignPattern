## 第1章 変わるものをカプセル化する ―― Strategy パターン

### この章の核心

**あるルールが変わるたびに、関係ないはずの場所まで修正が必要になる。こういう問題は、「変わる理由が違うもの」が同じ場所に混在しているシステムで起きている。**

---

### この章を読むと得られること

「割引ルールが増えるたびに、既存の計算ロジックに手を入れなければならない」——この痛みを経験したことがあるなら、この章はそのまま使える答えを持っています。

- **得られること1：** 「実行する振る舞い」という観点で、コードの変動箇所を識別できるようになる
- **得られること2：** 接続点で呼び出し元がどの知識を抱えているかを調べ、「変わる理由が異なる知識が同じ場所に混在している」と現状の問題を認識できるようになる
- **得られること3：** 接続点の形を変えると変更がどのように局所化されるかを構造から説明でき、改善後にどんな効果が生まれるかを見通せるようになる
- **得られること4：** 増え続けるルールに対して、いつ・どのように構造を分けるべきかの判断ができるようになる

---

## 🔵 フェーズ1：現状把握 ―― 仕様を整理し、システムと紐付ける
### 1-1：このシステムの仕様

このシステムは、ECサイトでお客様が商品を購入する際の**支払金額を計算**します。

入力として「商品リスト（各商品の名前と単価）」「会員種別（Premium / Regular）」「キャンペーン期間中フラグ（以後キャンペーンフラグ）」を受け取ります。システムは全商品の小計を算出し、以下の割引ルールを適用した最終的な支払金額を返します。

割引ルールは「誰に・いつ・どれだけ還元するか」というビジネス上の決定から生まれます。会員種別による優遇はリピーター獲得施策、キャンペーンは新規顧客向けの期間限定施策と、それぞれ担当チームが異なる目的で設計しています。

**割引ルール一覧**

| ルール名     | 適用条件                        | 割引の内容    | 業務機能                |
| -------- | --------------------------- | -------- | ------------------- |
| プレミアム割引  | 会員種別が "Premium"             | 20%引き    | 料金・プロモーション管理        |
| キャンペーン割引 | 会員種別が "Regular" かつキャンペーン期間中 | 10%引き    | マーケティング・通知管理        |
| 割引なし     | 上記以外                        | 定価（割引なし） | —（変更不要）              |

Premium会員にキャンペーン割引が重ならない理由は、業務上の判断からきています。Premium会員はすでに年会費や利用実績の対価として恒常的な20%引きを受けており、さらにキャンペーン割引を重ねると採算が合わなくなる可能性があるためです。「上位会員ほど割引が手厚いが、キャンペーンとは別枠」という設計は、ECサイトや航空会社のマイレージ会員制度でも広く見られます。

**優先・排他ルール**

| 条件 | 動作 |
|---|---|
| Premium かつ キャンペーン中 | Premium のみ適用（キャンペーン割引は無効） |

「クーポンと会員割引は併用不可」という注意書きをショッピングサイトで見かけたことはないでしょうか。このシステムの排他ルールは、その「併用不可」ルールと同じ発想です。どちらを優先するかは会社のポリシーによりますが、上位会員の特典を守ることを優先しています。

**この割引計算を使う場所**

| 使用場所 | 用途 |
|---|---|
| 決済計算処理 | 注文確定時の支払金額の確定 |
| カートプレビュー機能 | カート画面の金額プレビュー表示 |

**エラー条件**

| 条件 | 動作 |
|---|---|
| 顧客IDがCustomerDatabaseに存在しない | エラーメッセージを出力し、処理を中断する |
| 注文の商品リストが空の場合 | エラーメッセージを出力し、処理を中断する |

### 1-2：動作例テーブル

仕様を定義したところで、実際にどのような入力に対してどのような結果が返るかを確認します。このテーブルは「このシステムが正しく動いているとはどういう状態か」の基準になります。後で設計の改善（リファクタリング）を段階的に進めるときも、この表に立ち返ります。

| 会員種別 | キャンペーン | 適用ルール | 小計/支払金額 |
|---|---|---|---|
| Premium | ✗ | プレミアム20%引き | 10,000円 → 8,000円 |
| Premium | ✓ | プレミアム優先（キャンペーン無効） | 10,000円 → 8,000円 |
| Regular | ✓ | キャンペーン10%引き | 10,000円 → 9,000円 |
| Regular | ✗ | 割引なし | 10,000円 → 10,000円 |

コードを読む前に、このシステムが「何をする必要があるか」をこの表で確認できました。次は仕様とクラスを対応づけます。

**このシステムの登場クラス**

| クラス名 | 役割 | 担当する仕様 |
|---|---|---|
| Item | 商品データの保持 | 商品名・単価の元データ |
| Order | 注文データの保持 | 顧客IDとカート内商品リスト |
| CampaignContext | キャンペーン状態の保持 | キャンペーン有効フラグ |
| CustomerDatabase | 顧客情報の管理 | IDから会員種別・氏名を引く。エラー条件の一次判定 |
| PaymentCalculator | 支払金額の計算 | 合計金額の算出と割引ルールの適用 |
| CartPreviewService | カート画面のプレビュー表示 | 計算結果を使った金額プレビューの生成 |
| OrderProcessor | 注文処理の統合 | バリデーション・計算の一連の流れを担う |

---

### 1-3：クラス構成図

登場クラスの依存関係を図で整理します。`OrderProcessor` が中心となり、`CustomerDatabase`・`PaymentCalculator` の2つを使います。`PaymentCalculator` は `CartPreviewService` とも共有されています。

```mermaid
classDiagram
    class CustomerDatabase {
        -map~string,CustomerInfo~ records
        +exists(string) bool
        +get(string) CustomerInfo
    }
    class CustomerInfo {
        +string name
        +string memberType
    }
    class OrderProcessor {
        -CustomerDatabase& db
        -PaymentCalculator calculator
        +process(Order, CampaignContext)
    }
    class PaymentCalculator {
        +calculate(Order, string, CampaignContext) int
    }
    class CartPreviewService {
        -PaymentCalculator calculator
        +getEstimatedTotal(Order, string, CampaignContext) int
    }
    class Order {
        +string customerId
        +vector~Item~ items
    }
    class Item {
        +string name
        +int price
    }
    class CampaignContext {
        +bool isCampaignActive
    }

    OrderProcessor --> CustomerDatabase : 使う
    OrderProcessor --> PaymentCalculator : 使う
    CustomerDatabase --> CustomerInfo : 返す
    CartPreviewService --> PaymentCalculator : 使う
    PaymentCalculator ..> Order : 参照する
    PaymentCalculator ..> CampaignContext : 参照する
    Order o-- Item : 持つ
```

`OrderProcessor` が `CustomerDatabase` で顧客情報を取得し、`PaymentCalculator` で支払金額を計算します。`CartPreviewService` は同じ `PaymentCalculator` を利用します。

---

### 1-4：実装コード（現状）

#### データクラスとインフラ

このシステムには以下の3件の顧客データがあらかじめ登録されています。

| 顧客ID | 氏名 | 会員種別 |
|---|---|---|
| C001 | 田中 一郎 | Premium |
| C002 | 佐藤 花子 | Regular |
| C003 | 鈴木 次郎 | Regular |

コードを読む前に、どのIDが「Premium」でどのIDが「Regular」かを把握しておくと、動作結果と仕様の対応が追いやすくなります。

はじめに、注文データ・顧客情報の役割を担うクラス群を見ます。

```cpp
#include <iostream>
#include <string>
#include <vector>
#include <map>

class Item {
public:
    std::string name;
    int price;
    Item(std::string n, int p) : name(n), price(p) {}
};

class CampaignContext {
public:
    bool isCampaignActive = false;
};

class Order {
public:
    std::string customerId;
    std::vector<Item> items;
};

struct CustomerInfo {
    std::string name;
    std::string memberType;  // "Premium" または "Regular"
};

class CustomerDatabase {
private:
    std::map<std::string, CustomerInfo> records;
public:
    CustomerDatabase() {
        records["C001"] = {"田中 一郎", "Premium"};
        records["C002"] = {"佐藤 花子", "Regular"};
        records["C003"] = {"鈴木 次郎", "Regular"};
    }

    bool exists(const std::string& id) const {
        return records.count(id) > 0;
    }

    CustomerInfo get(const std::string& id) const {
        return records.at(id);
    }
};
```

`CustomerDatabase` は `std::map` でIDと顧客情報を対応づけています。

#### 決済計算クラス

次に、割引を適用して最終的な支払金額を算出する計算クラスを見ます。

```cpp
class PaymentCalculator {
public:
    int calculate(const Order& order,
                  const std::string& memberType,
                  const CampaignContext& context) {
        int total = 0;
        for (const auto& item : order.items) {
            total += item.price;
        }

        // 割引ルール：条件ごとに if で分岐している
        if (memberType == "Premium") {
            total = total * 80 / 100;
        } else if (memberType == "Regular" && context.isCampaignActive) {
            total = total * 90 / 100;
        }

        return total;
    }
};
```

このクラスが今章の中心です。`calculate` メソッドの中に「商品の価格を足し合わせる処理」と「割引ルールを判定する処理」が一緒に書かれていることを確認しておいてください。

カートプレビューは割引条件を重複実装せず、同じ計算クラスを利用しています。

```cpp
class CartPreviewService {
private:
    PaymentCalculator calculator;
public:
    int getEstimatedTotal(const Order& order,
                          const std::string& memberType,
                          const CampaignContext& context) {
        return calculator.calculate(order, memberType, context);
    }
};
```

#### 呼び出し元と実行確認

`OrderProcessor` は顧客IDのバリデーション・割引計算をまとめて担います。

```cpp
class OrderProcessor {
private:
    CustomerDatabase& db;
    PaymentCalculator calculator;
public:
    OrderProcessor(CustomerDatabase& db) : db(db) {}

    void process(const Order& order, const CampaignContext& context) {
        if (!db.exists(order.customerId)) {
            std::cerr << "エラー: 顧客ID " << order.customerId
                      << " は登録されていません\n";
            return;
        }
        if (order.items.empty()) {
            std::cerr << "エラー: 注文が空です\n";
            return;
        }

        CustomerInfo customer = db.get(order.customerId);
        int finalPrice = calculator.calculate(order, customer.memberType, context);
        std::cout << customer.name << " の支払金額は "
                  << finalPrice << " 円です。\n";
    }
};

int main() {
    CustomerDatabase db;
    OrderProcessor processor(db);
    CampaignContext context;

    // 行1：C001（Premium）/ キャンペーンなし → 20%引き
    Order order1;
    order1.customerId = "C001";
    order1.items.push_back(Item("ワイヤレスイヤホン", 10000));
    context.isCampaignActive = false;
    processor.process(order1, context);

    // 行2：C002（Regular）/ キャンペーンあり → 10%引き
    Order order2;
    order2.customerId = "C002";
    order2.items.push_back(Item("ワイヤレスイヤホン", 10000));
    context.isCampaignActive = true;
    processor.process(order2, context);

    // 行3：C003（Regular）/ キャンペーンなし → 割引なし
    Order order3;
    order3.customerId = "C003";
    order3.items.push_back(Item("スマホケース", 3000));
    context.isCampaignActive = false;
    processor.process(order3, context);

    // エラーケース：存在しない顧客ID
    Order order4;
    order4.customerId = "UNKNOWN";
    order4.items.push_back(Item("ケーブル", 1000));
    processor.process(order4, context);

    return 0;
}
```

上記コードの実行結果：

```
田中 一郎 の支払金額は 8000 円です。
佐藤 花子 の支払金額は 9000 円です。
鈴木 次郎 の支払金額は 3000 円です。
エラー: 顧客ID UNKNOWN は登録されていません
```

> [!NOTE]
> 上記は代表的な実行ケースを示したものです。全ケースの検証は別途テストで行ってください。

`CustomerDatabase` からの情報を使ってバリデーションと計算を行います。次のフェーズで変更が来たときに何が起きるかを確認します。

---

### 1-5：変更要求

マーケティング部から以下の変更要求が来ました。

「来週から『サマーセール』を開始します。期間中はRegular会員を対象に5%オフを追加してください。プレミアム会員はすでに20%引きが適用されているため、今回のセールは対象外です。」

リリースは来週末。既存の `if` 文の隙間に `else if` を追加すれば間に合うかもしれません。


**仕様変更の内容**

変更要求を受けて、現在の割引ルールがどう変わるかを整理します。

| ルール名 | 変更前 | 変更後 |
|---|---|---|
| プレミアム割引 | Premium会員に20%引き | 変更なし |
| キャンペーン割引 | Regular会員にキャンペーン10%引き | 変更なし |
| **サマーセール割引（新規）** | —（なし） | **Regular会員に5%引きを追加** |

※表の一番下の行（Premium・キャンペーン・サマーセールがすべて重なった場合）は、「プレミアム割引（20%引き）」が最優先され、他のキャンペーンやサマーセールは無効になるという仕様を表しています。そのため、変更後も8,000円のままとなります。


**変更後の動作例**

| 会員種別    | キャンペーン     | サマーセール | 変更前/後の支払金額（1万円の場合）                                        |
| ------- | ---------- | ------ | --------------------------------------------------------- |
| Premium | ✓          | ✓      | 8,000円（20%引き）→ 8,000円（変更なし）                               |
| Regular | ✓          | ✓      | 9,000円（10%引き）→ **8,550円（9,000円にサマーセール5%引きを追加）** |
| Regular | ✗          | ✓      | 10,000円（割引なし）→ **9,500円（5%引き）**                           |
| Regular | ✓/✗（どちらでも） | ✗      | 変更なし                                                      |

Regular会員はサマーセール中に5%引きが新たに加わります。プレミアム会員はすでに20%引きが適用されているため、今回のサマーセールの対象外となります。

フェーズ1でシステムの現状と変更要求が把握できました。次のフェーズ2では、「何が変わり、何が変わらないか」を整理します。

## 🟣 フェーズ2：仮説立案 ―― 何が変わるかを観察し、ヒアリングで裏付ける
### 2-1：変わりそうな仕様の見当をつける

`PaymentCalculator.calculate()` が現在抱えている知識と、それぞれがどの業務機能に属するかを確認します。ここでは断定ではなく、変わりそうな箇所を予測し、後続のヒアリングで裏付けるための仮説として整理します。

| 知識（コードが直接持っているもの） | 業務機能 | 適切か |
|---|---|---|
| 商品単価の合算ロジック | インフラ・システム管理 | ✅ |
| プレミアム割引の条件・割引率 | 料金・プロモーション管理 | ❌ 混在 |
| キャンペーン割引の条件・割引率 | マーケティング・通知管理 | ❌ 混在 |

❌が2つある。この1つのメソッドを、複数の業務機能が異なる時期に変更することになります。これが後の変更の痛みの予兆です。

### 2-2：今回の変更で確実に変わること

今回の変更要求から確定している変更は1点です。

- **サマーセール割引の追加**：Regular会員を対象に5%オフを追加する

ただし「この変更が1回限りか、今後も続くか」によって、どこまで設計を変えるべきかが大きく変わります。関係者に確認します。

### ヒアリングに向けた背景確認

このシステムは、ある中堅ECサイトの決済計算を担っています。数年前にサービスが立ち上がった当初は、お客様が商品を選んでカートに入れ、そのままの合計金額で決済するシンプルな流れでした。

しかし、サービスが成長し競合他社との競争が激しくなるにつれて、様々な施策が打たれるようになりました。新規顧客向けの期間限定キャンペーンや、リピーター向けのプレミアム会員制度など、ビジネス上の要求は日々増えています。

### 2-3：関係者ヒアリング


- **開発者：** 「サマーセールの件、承知しました。今後もこのような新しい割引ルールは追加される予定はありますか？」
- **マーケティング部リーダー：** 「はい、もちろんです。秋にはハロウィンキャンペーン、冬には年末大感謝祭など、毎月のように新しい企画を予定しています。」
- **開発者：** 「ちなみに、割引の計算方法自体が変わることはありますか？今はパーセント引きですが、定額割引などです。」
- **マーケティング部リーダー：** 「実は秋のキャンペーンでは、一律1000円引きクーポンの配布を検討しています。これも対応できますか？」

### 2-4：ヒアリングで判明した将来リスク

ヒアリングで浮かび上がった「確定ではないが、近い将来起こりうる変化」を記録します。これは今回の設計判断の材料です。

| **将来リスク** | **時期の目安** | **根拠** |
|---|---|---|
| 新しい割引ルールの追加が毎月続く | 継続的に | マーケティング責任者から直接確認 |
| 計算方法が「パーセント引き」から「定額引き」に変わる | 数ヶ月後 | 秋のクーポン企画として言及 |

フェーズ2で「今変わること（確定）」と「将来変わるかもしれないこと（リスク）」を分けて整理できました。次はリスクをもう少し具体的な「仕様の変化」として整理します。

### 2-5：将来の変更仕様の見通し

2-4のリスクを「現在の仕様」と「将来起こりうる仕様変化」に並べて整理します。

| 変更内容 | 現在 | 将来（時期の目安） |
|---|---|---|
| 割引ルールの種類 | プレミアム割引・キャンペーン割引の2種類 | 毎月新しいルールが追加され続ける（継続的） |
| 割引の計算方法 | パーセント引き（小計 × 割引率） | 定額引き（小計 − 固定額）が混入する（数ヶ月後） |

この変化が来たとき、現在の構造がどれだけの修正コストを要求するかを、次のフェーズ3で実際に確かめます。

---

## 🟣 フェーズ3：問題特定 ―― 変更の痛みを発見する
### 3-1：変更を試みる

「サマーセール：Regular会員に5%オフを追加」を現在の `PaymentCalculator` に追加してみます。変更前のコードはこうでした。

```cpp
if (order.customerType == "Premium") {
    total = total * 80 / 100;   // 20%引き
} else if (order.customerType == "Regular"
           && context.isCampaignActive) {
    total = total * 90 / 100;   // 10%引き
}
```

このコードにサマーセールの条件を追加すると、以下のようになります。

```cpp
// サマーセール対応：Regular会員向けに条件を追加
if (order.customerType == "Premium") {
    total = total * 80 / 100;  // 20%引き（サマーセール対象外）
} else if (context.isSummerSale && context.isCampaignActive) {
    total = (total * 95 / 100) * 90 / 100; // 重ね掛け（Regular会員）
} else if (context.isSummerSale) {
    total = total * 95 / 100;  // 5%引き（Regular会員）
} else if (context.isCampaignActive) {
    total = total * 90 / 100;  // 10%引き
}
```

変更後のコードを実行すると、次のような結果になります（1万円の注文で4ケースを確認）。

```cpp
// 変更後のクラスを使った動作確認
int main() {
    CustomerDatabase db;
    OrderProcessor processor(db);
    CampaignContext context;
    Order order;
    order.items.push_back(Item("ワイヤレスイヤホン", 10000));

    // C001（Premium）/ キャンペーンあり / サマーセール中
    // → Premium優先（キャンペーン・サマーセール無効）
    order.customerId = "C001";
    context.isSummerSale     = true;
    context.isCampaignActive = true;
    processor.process(order, context);

    // C002（Regular）/ キャンペーンあり / サマーセール中
    // → 重ね掛け（10%引き ＋ 5%引き）
    order.customerId = "C002";
    context.isSummerSale     = true;
    context.isCampaignActive = true;
    processor.process(order, context);

    // C002（Regular）/ キャンペーンなし / サマーセール中 → 5%引き
    order.customerId = "C002";
    context.isSummerSale     = true;
    context.isCampaignActive = false;
    processor.process(order, context);

    // C002（Regular）/ キャンペーンなし / サマーセールなし → 割引なし
    order.customerId = "C002";
    context.isSummerSale     = false;
    context.isCampaignActive = false;
    processor.process(order, context);

    return 0;
}
```

実行結果：

```
田中 一郎 の支払金額は 8000 円です。   // Premium優先
佐藤 花子 の支払金額は 8550 円です。   // 9000円に5%引きを追加
佐藤 花子 の支払金額は 9500 円です。   // サマーセール5%引き
佐藤 花子 の支払金額は 10000 円です。  // 割引なし
```

1-5の変更後の動作例と対応する出力が得られています。

> [!NOTE]
> 上記は代表的な実行ケースを示したものです。この章では、掲載した動作例と出力が対応していることを確認しながら読み進めます。

この変更後コードを見ると、問題が浮かび上がります。

一見シンプルな追加に見えますが、サマーセールは「Regular会員のみ」「キャンペーンと重複した場合は重ね掛け」という複合条件を持っています。単純に `else if` を1行追加するだけでは済まず、`context.isSummerSale && context.isCampaignActive` の組み合わせを考慮した分岐も追加する必要があります。さらに、`CampaignContext` クラスに `isSummerSale` フラグを追加する作業が発生します。

```cpp
// CampaignContext クラスへの変更（サマーセールフラグの追加が必要）
class CampaignContext {
public:
    bool isCampaignActive = false;
    bool isSummerSale = false;   // ← 追加。データクラスにまでフラグが増え続ける
};
```

ヒアリングで予告された「1000円引きクーポン」が来た場合はどうでしょうか。パーセント計算とは異なる「引き算」のロジックが混入し、全ての `if` ブロックの計算順序を見直す必要が出てきます。

### 3-2：変更影響グラフ

```mermaid
graph LR
    T1["変更要求：サマーセール追加"]
        -->|影響| A["PaymentCalculator<br>（既存の条件分岐全体）"]
    A -->|さらに影響| B["CampaignContext<br>（新しいフラグの追加）"]
    A -.->|表示結果の回帰確認| C["CartPreviewService<br>（利用側）"]
```

新しいルールを1つ追加するだけで、既存の計算ロジック全体とデータクラスを修正し、同じ計算結果を表示するカートプレビューも回帰確認する必要があります。ここでは、**ソースを修正する場所**と**動作を再確認する場所**を区別します。

### 3-3：痛みの言語化

**1つ目：影響範囲が読めない恐怖。** 新しい割引を追加するには、複雑化しつつある `if-else` の隙間にコードを差し込む必要があります。変更のたびに、無関係なはずの過去のルールも含めて全テストケースを見直す必要があります。

**2つ目：検索・解読コストの増大。** キャンペーンのたびに条件分岐が追加されていくと、PaymentCalculator が数百行の複雑な分岐を抱える可能性があります。「どの条件が今のキャンペーンのものか」「過去のセール条件とどう違うのか」を理解するために、コードの広い範囲を確認する作業が発生します。機能として動いていても、変更箇所を特定する負担が徐々に大きくなります。

---
> **📌 問題（確定）**
> 割引という「実行する振る舞い」が変わるたびに、`PaymentCalculator` と `CampaignContext` を修正し、その計算を使う `CartPreviewService` まで回帰確認する必要がある。変わる理由が異なる知識が計算本体に混在しているため、1つの施策変更が広い影響確認を強いる。
---

フェーズ3で「変更が辛い」ことが確認できました。次のフェーズ4では、なぜ辛いのかを構造的に言語化します。

---

## 🟠 フェーズ4：原因分析 ―― なぜ辛いのかを構造で言語化する
### 4-1：痛みの根源を探る（観察と原因）

フェーズ3で確認した「変更の辛さ」は、コードのどこから来ているのでしょうか。コードを注意深く観察すると、痛みを引き起こしている2つの事実が浮かび上がってきます。

第一に、新しい割引を追加するとき、なぜ毎回 `PaymentCalculator` を開かなければならないのでしょうか？
フェーズ2の責任チェック表から見えたように、現状の PaymentCalculator はこれらすべての割引ルールを責任として持っています。問題は、その責任を**複数の業務機能からの変更要求によって変えなければならない点**です。複数の業務機能の変化が1つのクラスに集中してしまっているため、仕様変更の影響がここに密集してしまうのです。

それは、このクラス自身が「プレミアム会員なら20%引き」「サマーセールなら5%引き」といった**具体的な割引の条件をすべて直接知ってしまっている（抱え込んでいる）**からです。

第二に、なぜ変更の影響範囲が読めず、全テストをやり直す恐怖を感じるのでしょうか？
それは、「商品をループで回して金額を足し合わせる」という土台となる骨格ロジックと、「特定のキャンペーンを判定して割引する」というビジネスロジックが、**同じメソッドの中で物理的に混ざり合っている**からです。

この「症状（痛み）」と「根本原因」を整理すると、以下のようになります。

| **観察した症状（痛み）** | **構造的な原因（痛みの根源）**                                                                                                                    |
| -------------- | ------------------------------------------------------------------------------------------------------------------------------------ |
| 影響範囲が読めない恐怖    | `PaymentCalculator` が各割引の具体的な条件を直接知っているから                                                                                            |
| 検索・解読コストの増大 | 変わる理由が違う2つのもの（「合算ロジック」と「割引条件」）が同じメソッドの中に混在しているから。異なる理由で変わるロジックが分離されず、同じメソッド内に直接書かれているため、割引条件が変わるたびに合算ロジックも含めたメソッド全体を確認する作業が発生する。 |

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
            total = total * 80 / 100;   // 20%引き
        } else if (context.isSummerSale && context.isCampaignActive) {
            total = (total * 95 / 100) * 90 / 100; // 複合割引
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

### 4-3：接続点に漏れている知識を確認する

今、`PaymentCalculator`は割引ルールの条件（`isPremium`や`isSummerSale`等）を自分の中に抱えています。接続点で見ると、計算の骨格が必要としているのは「合計金額を渡し、割引後の金額を受け取ること」だけです。それにもかかわらず、骨格側が個々の適用条件と割引率まで知っています。

現在の `PaymentCalculator` は、すべての割引ルールを自分自身の中に直接抱え込んでいます。

**【接続点へ割引条件が漏れているコード】**
```cpp
class PaymentCalculator {
public:
    int calculate(const Order& order) {
        // ← 1-3で示した合算ループ（for + total += item.price）がここに入る
        // 割引ルール（具体）を、自分自身で直接判断して処理している
        if (order.customerType == "Premium") {
            total = total * 80 / 100;
        }
        // ← 1-3で示した他のelse ifブロックがここに続く
    }
};
```

新しいキャンペーンが増えるたびに、計算の骨格を持つクラスを開き、`else if`を追加する作業が発生します。割引ルールの知識が接続点を越えて骨格側へ漏れているためです。

決済の合算ロジックと個別の割引ルールは、変わる理由が全く異なります。これらが同じ場所に混在していることが、根本原因として確認できました。

今回着目する接続点は、「合計金額」と「割引後の金額」を受け渡す境界です。個々のキャンペーン条件は、この境界の外へ移せます。

---
> **📌 原因（確定）**
> 割引ルールが「毎月追加される」と確認できているのに、その全種類を`PaymentCalculator`が抱え込んでいる。追加のたびに計算の骨格を開く必要があり、割引担当の変更が注文計算の再テストへ波及する。
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

        // ↓ 割引ルール（変わり続ける）
        if (order.customerType == "Premium") {
            total = total * 80 / 100;
        } else if (context.isSummerSale && context.isCampaignActive) {
            total = (total * 95 / 100) * 90 / 100;
        } else if (context.isSummerSale) {
            total = total * 95 / 100;
        } else if (context.isCampaignActive) {
            total = total * 90 / 100;
        }
        // ↑ ここまでが分離するターゲット

        return total;
```

割引ルールが計算の骨格に返しているのは「割引適用後の合計金額（`int`）」です。

| 接続点 | 接続するデータ | 変わるもの |
|---|---|---|
| 割引ロジック → `calculate()` の骨格 | `int` 型の割引適用後の合計金額 | 計算ロジック（誰がどう割引するか） |

### 何が変わり、何が変わらないか

- **変わるもの**：割引の計算ロジック。新しいキャンペーンや顧客種別のたびに増える。
- **変わらないもの**：流れるデータの型（`int` 型の金額）。`CartPreviewService` が受け取る値の形は変わらない。

呼び出し元は「割引後の金額を受け取れれば十分」なので、必要とする結果の型は安定しています。問題は「どのように計算するか」という**割引ルールの知識**が本体に膨れ続けていることです。

**現状のままでよい場面**：割引ルールが少数で、当面追加されないとチームで確認できるなら、`if-else`のまま保つ判断もあります。今回はルールが毎月増えるため、計算の骨格から割引判断を切り離し、同じ受け渡し方で交換できる設計を検討します。

---
> **📌 課題（確定）**
> 割引ルールが増え続けると確定している以上、`PaymentCalculator` がその全種類を直接知り続ける設計はコストが合わない。割引ロジックを外から差し替えられるようにし、`PaymentCalculator` は受け取るだけにする。
---

## 🔴 フェーズ6：対策検討 ―― 段階的な改善と決断
フェーズ5で「変わるのは割引の計算ロジックであり、割引後の金額という結果の型は安定している」ことが分かりました。ここでは、その割引ルールをどのように差し替え可能にするかを段階的に検討します。いきなり正解へ飛ぶのではなく、各ステップで「どこまで痛みが解消されるか」を確認しながら、今回の要件において「どのステップで止めるのが良いか」を決断します。

### ステップ1：各処理を独立した関数として切り出す（共通構造を発見する）

「if-else が乱立しているなら、まずそれをメソッドに切り出して整理しよう」というのが自然な最初の発想です。クラスを新しく作るのはコストがかかる。同じクラスの中で、割引の計算を種類ごとに独立したプライベートメソッドとして分離してみます。

```cpp
class PaymentCalculator {
    // 各割引を独立した関数として切り出す（判定なし、計算だけ）
    int applyPremiumRule(int total) {
        return total * 80 / 100;
    }
    int applySummerRule(int total) {
        return total * 95 / 100;
    }
    int applyCampaignRule(int total) {
        return total * 90 / 100;
    }

    // 判定（どのルールを選ぶか）も独立した関数として切り出す
    int selectAndApply(int total, const Order& order,
                       const CampaignContext& ctx) {
        if (order.customerType == "Premium")
            return applyPremiumRule(total);
        if (ctx.isSummerSale && ctx.isCampaignActive)
            return applyCampaignRule(applySummerRule(total));
        if (ctx.isSummerSale)
            return applySummerRule(total);
        if (ctx.isCampaignActive)
            return applyCampaignRule(total);
        return total;
    }
public:
    int calculate(const Order& order,
                  const CampaignContext& ctx) {
        int total = 0;
        for (const auto& item : order.items)
            total += item.price;
        return selectAndApply(total, order, ctx);
    }
};
```

`calculate()` の骨格は一目で読めるようになり、「どれを選ぶか」の判定は `selectAndApply()` に、「実際の計算」は各 `applyXxx()` に分かれた。

**この段階の評価：** ここで気づくことがあります。`applyPremiumRule`・`applySummerRule`・`applyCampaignRule` の3つは、引数も戻り値の型も同じです。同じシグネチャ（`int (int)`）を持つ関数が並んでいる——これが「共通の構造」の初めての兆候です。また、`selectAndApply()` を独立させたことで、「計算の処理」と「どれを選ぶかの判定」が別の関心事だということも見えてきました。`calculate()` は確かにスッキリしましたが、新しい割引が来るたびに `applyXxx()` の追加と `selectAndApply()` の書き足しが必要です。整理と共通構造の発見はできたが、同じクラスを修正する根本は変わっていない。次のステップでは、この共通構造を持つ関数たちをクラスに昇格させてみます。

---

### ステップ2：各割引を別のクラスに切り出す

ステップ1では関数を種類ごとに独立させ、「共通のシグネチャを持つ関数が並んでいる」という構造が見えてきました。しかし、関数が増えるにつれて1つのクラスの中に処理がどんどん積み重なっていきます。そこで「それぞれを別のクラスにしよう」という発想が生まれます。

「割引ロジックが増えてきたなら、それぞれを別のクラスにしよう」という発想は自然です。今度は割引の種類ごとにクラスを作ってみます。

```cpp
// 割引ごとに別のクラスに分けた（インターフェースはまだない）
class PremiumDiscount {
public:
    int apply(int total) { return total * 80 / 100; }
};

class SummerSaleDiscount {
public:
    int apply(int total) { return total * 95 / 100; }
};

class CampaignDiscount {
public:
    int apply(int total) { return total * 90 / 100; }
};

class PaymentCalculator {
public:
    int calculate(const Order& order, const CampaignContext& context) {
        int total = 0;
        for (const auto& item : order.items) total += item.price;

        // ← if文はここに残ったまま。しかも全具体クラスを知らなければならない
        if (order.customerType == "Premium") {
            PremiumDiscount rule;
            return rule.apply(total);
        } else if (context.isSummerSale && context.isCampaignActive) {
            SummerSaleDiscount s;
            CampaignDiscount c;
            return c.apply(s.apply(total));
        } else if (context.isSummerSale) {
            SummerSaleDiscount rule;
            return rule.apply(total);
        } else if (context.isCampaignActive) {
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

### ステップ3：共通の契約を導入するが、生成は自分で行う

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
    int apply(int total) override { return total * 80 / 100; }
};

class SummerSaleDiscount : public IDiscountRule {
public:
    int apply(int total) override { return total * 95 / 100; }
};

class CampaignDiscount : public IDiscountRule {
public:
    int apply(int total) override { return total * 90 / 100; }
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
        } else if (context.isSummerSale) {
            rule = &summer;
        } else if (context.isCampaignActive) {
            rule = &campaign;
        }

        return rule ? rule->apply(total) : total;
    }
};
```

> [!INFO] 生ポインタの使用について
> このサンプルでは段階的な設計の変化を示すため、生ポインタ（`IDiscountRule* rule`）を使用しています。本書では全章を通じて生ポインタを使い、所有権の議論よりも構造の変化に集中します。

`PaymentCalculator` が持つ型は `IDiscountRule*` という抽象型になり、具体クラスのメソッドを直接呼ぶ行は消えた。

**この段階の評価：** 型を抽象化できたのは前進です。しかし `PaymentCalculator` はまだ `PremiumDiscount` や `SummerSaleDiscount` という具体クラス名を知っており、if 文で生成を選んでいます。新しい割引クラスを追加するとき、`PaymentCalculator` の中の if 文も書き足さなければなりません。加えて、この `else if` の連鎖は、「Regular会員でSummerSale中かつキャンペーン中（重ね掛け：8,550円）」のケースを正しく表現できません。`isSummerSale` が真であれば `CampaignDiscount` は無視されるためです。この問題は、割引ルールの適用条件や優先順位を外側でどのように制御するかによって解決を図ります。型は抽象化できたが、どれを生成するかの判断はまだ if 文に残っている。「生成の選択」そのものを外に出せれば、`PaymentCalculator` から if 文が消えるはずです。

---

### ステップ4：ルールを外から受け取る（依存性の注入）

「`PaymentCalculator` が自分でルールを生成するから if 文が必要になる。なら、外からルールを渡してもらえばいい」という発想です。どのルールを使うかを決める責任を呼び出し側に移し、`PaymentCalculator` はただ受け取って使うだけにします。

```cpp
class IDiscountRule {
public:
    virtual int apply(int total) = 0;
    virtual ~IDiscountRule() = default;
};

class PremiumDiscount : public IDiscountRule {
public:
    int apply(int total) override { return total * 80 / 100; }
};

class SummerSaleDiscount : public IDiscountRule {
public:
    int apply(int total) override { return total * 95 / 100; }
};

class SummerSaleAndCampaignDiscount : public IDiscountRule {
public:
    int apply(int total) override {
        return (total * 95 / 100) * 90 / 100;
    }
};

class CampaignDiscount : public IDiscountRule {
public:
    int apply(int total) override { return total * 90 / 100; }
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
        return rule->apply(total); // 割引種別を選ぶif文が計算フローから外れた
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
    } else if (context.isSummerSale && context.isCampaignActive) {
        rule = &both;
    } else if (context.isSummerSale) {
        rule = &summer;
    } else if (context.isCampaignActive) {
        rule = &campaign;
    }

    PaymentCalculator calculator(rule);
    int finalPrice = calculator.calculate(order);
}
```

`PaymentCalculator` の中から割引種別を選ぶ `if` 文が消え、`IDiscountRule* rule` を受け取って計算を委譲する骨格になりました。

**この段階の評価：** `PaymentCalculator` から割引種別の選択判断が消えました。新しい割引を追加するときは、ルールクラスと選択を担う組み立て箇所を変更します。`IDiscountRule` の契約が安定している限り、`PaymentCalculator` の計算フローへ条件分岐を追加せずに済みます。これが今回目指した「変わる理由の分離」の到達点です。

ただし、この設計は「実行するアルゴリズムの差し替え」を解決するもので、複数の割引を自由に重ねる問題まで自動的に解決するわけではありません。この例では重ね掛けを1つのルールとして表す `SummerSaleAndCampaignDiscount` を用意しています。独立した割引が増え、組み合わせごとのクラスが増え始めたら、割引のリストを順番に適用する仕組みや、ルールを入れ子にして重ねる構造を別途検討します。

---

### どこまで設計を進めるのが良いか（採用ステップの決断）

それぞれのステップには一長一短があります。ステップ4のインターフェース化は強力ですが、ファイル数や型が増えるという「初期投資コスト」もかかります。どこで止めるかは、**「今後の変更頻度（ビジネス要求）」**で決断します。

*   **ステップ1（プライベートメソッド化）で止めるケース：** 「今回限りの特例」の場合。見た目を整理するだけで十分です。
*   **ステップ2（具体クラスへの分離）で止めるケース：** ファイルを分けて整理したいが、インターフェース導入のコストをまだかけたくない場合の「中間策」です。
*   **ステップ3（インターフェース化・生成は自分）で止めるケース：** 型を統一したいが、呼び出し側にルール選択の責任を渡す準備がまだできていない場合。
*   **ステップ4（依存性の注入）まで進むケース：** 「毎月新しい割引が追加される」と確定している場合。今すぐ初期投資コストを払ってでも、将来の変更箇所を限定するのが適切です。

**今回の決断：**
フェーズ2のヒアリングで、マーケティング責任者から「今後も毎月ルールが追加される」と明言されています。この変更頻度を重視し、今回は**ステップ4（インターフェース化・依存性の注入）まで進化させる**案を採用します。

フェーズ6で採用ステップが決まりました。次のフェーズ7では、この決断を最終的なコードに落とし込みます。

## 🟢 フェーズ7：対策実施 ―― 変化に強いコードを完成させる
### 7-1：解決後のコード（全体）

ステップ4で決断した構造を、実行可能な完全なコードとして組み上げます。各役割ごとにコードを分けて見ていきましょう。

**1. データの定義とインフラ（CustomerDatabase）**
注文データ・顧客情報クラスはリファクタリング前後で変わりません。割引ロジックの分離が、これらのクラスに影響しないことを確認してください。

```cpp
#include <iostream>
#include <string>
#include <vector>
#include <map>

class Item {
public:
    std::string name;
    int price;
    Item(std::string n, int p) : name(n), price(p) {}
};

class CampaignContext {
public:
    bool isCampaignActive = false;
    bool isSummerSale = false;
};

class Order {
public:
    std::string customerId;
    std::vector<Item> items;
};

struct CustomerInfo {
    std::string name;
    std::string memberType;
};

class CustomerDatabase {
private:
    std::map<std::string, CustomerInfo> records;
public:
    CustomerDatabase() {
        records["C001"] = {"田中 一郎", "Premium"};
        records["C002"] = {"佐藤 花子", "Regular"};
        records["C003"] = {"鈴木 次郎", "Regular"};
    }

    bool exists(const std::string& id) const { return records.count(id) > 0; }
    CustomerInfo get(const std::string& id) const { return records.at(id); }
};

// 割引ルールの共通インターフェース（Strategy）
class IDiscountRule {
public:
    virtual int apply(int total) = 0;
    virtual ~IDiscountRule() = default;
};
```

**2. 個別の割引ルールの実装（具体）**
インターフェースを満たす具体的な割引クラスを作成します。割引計算の追加・変更は主にこのクラス群へ閉じ、利用するルールの選択は組み立て箇所で行います。

```cpp
class NoDiscount : public IDiscountRule {
public:
    int apply(int total) override { return total; }
};

class PremiumDiscount : public IDiscountRule {
public:
    int apply(int total) override {
        return total * 80 / 100;
    }
};

class SummerSaleAndCampaignDiscount : public IDiscountRule {
public:
    int apply(int total) override {
        return (total * 95 / 100) * 90 / 100;
    }
};

class SummerSaleDiscount : public IDiscountRule {
public:
    int apply(int total) override {
        return total * 95 / 100;
    }
};

class CampaignDiscount : public IDiscountRule {
public:
    int apply(int total) override {
        return total * 90 / 100;
    }
};
```

**3. 本体クラス（コンテキスト）**
計算を行う本体クラスです。具体的な割引ルールを知らず、インターフェースを通じて計算を委譲します。これにより、割引種別を選ぶ条件分岐を計算フローから外せます。

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

class CartPreviewService {
private:
    PaymentCalculator calculator;
public:
    CartPreviewService(IDiscountRule* r) : calculator(r) {}

    int getEstimatedTotal(const Order& order) {
        return calculator.calculate(order);
    }
};
```

**4. ルール選択と組み立て（RuleFactory・OrderProcessor）**
具体的なクラス名（`PremiumDiscount`等）を知っているのは `RuleFactory` だけです。`OrderProcessor` は CustomerDatabase・RuleFactory・PaymentCalculator を組み合わせて注文処理全体を担います。

```cpp
class RuleFactory {
public:
    static IDiscountRule* create(const std::string& memberType,
                                 const CampaignContext& context) {
        if (memberType == "Premium") return new PremiumDiscount();
        if (context.isSummerSale && context.isCampaignActive)
            return new SummerSaleAndCampaignDiscount();
        if (context.isSummerSale)  return new SummerSaleDiscount();
        if (context.isCampaignActive) return new CampaignDiscount();
        return new NoDiscount();
    }
};

class OrderProcessor {
private:
    CustomerDatabase& db;
public:
    OrderProcessor(CustomerDatabase& db) : db(db) {}

    void process(const Order& order, const CampaignContext& context) {
        if (!db.exists(order.customerId)) {
            std::cerr << "エラー: 顧客ID " << order.customerId
                      << " は登録されていません\n";
            return;
        }
        if (order.items.empty()) {
            std::cerr << "エラー: 注文が空です\n";
            return;
        }

        CustomerInfo customer = db.get(order.customerId);
        IDiscountRule* rule = RuleFactory::create(customer.memberType, context);
        PaymentCalculator calculator(rule);
        CartPreviewService preview(rule);

        int finalPrice = calculator.calculate(order);
        std::cout << customer.name << " の支払金額は " << finalPrice << " 円\n";
        std::cout << "  プレビュー: " << preview.getEstimatedTotal(order) << " 円\n";

        delete rule;
    }
};

int main() {
    CustomerDatabase db;
    OrderProcessor processor(db);
    CampaignContext context;

    // C001（Premium）/ キャンペーンなし / サマーセールなし → 20%引き
    Order order1;
    order1.customerId = "C001";
    order1.items.push_back(Item("ワイヤレスイヤホン", 10000));
    context.isCampaignActive = false;
    context.isSummerSale = false;
    processor.process(order1, context);

    // C001（Premium）/ キャンペーンあり / サマーセール中 → Premium優先
    Order order2;
    order2.customerId = "C001";
    order2.items.push_back(Item("ワイヤレスイヤホン", 10000));
    context.isCampaignActive = true;
    context.isSummerSale = true;
    processor.process(order2, context);

    // C002（Regular）/ キャンペーンあり / サマーセール中 → 重ね掛け
    Order order3;
    order3.customerId = "C002";
    order3.items.push_back(Item("ワイヤレスイヤホン", 10000));
    context.isCampaignActive = true;
    context.isSummerSale = true;
    processor.process(order3, context);

    // C002（Regular）/ サマーセールのみ → 5%引き
    Order order4;
    order4.customerId = "C002";
    order4.items.push_back(Item("ワイヤレスイヤホン", 10000));
    context.isCampaignActive = false;
    context.isSummerSale = true;
    processor.process(order4, context);

    // C003（Regular）/ 割引なし
    Order order5;
    order5.customerId = "C003";
    order5.items.push_back(Item("スマホケース", 3000));
    context.isCampaignActive = false;
    context.isSummerSale = false;
    processor.process(order5, context);

    return 0;
}
```

仕様変更後の主要ケースを実行し、既存の割引を保ちながら、サマーセール単独とキャンペーンとの重ね掛けが仕様どおりになることを確認します。今回のルール追加では、`PaymentCalculator` の計算フローを変更せず、ルール実装・選択箇所・入力モデルの変更で対応した点に注目してください。

上記コードの実行結果：

```
田中 一郎 の支払金額は 8000 円
  プレビュー: 8000 円
田中 一郎 の支払金額は 8000 円
  プレビュー: 8000 円
佐藤 花子 の支払金額は 8550 円
  プレビュー: 8550 円
佐藤 花子 の支払金額は 9500 円
  プレビュー: 9500 円
鈴木 次郎 の支払金額は 3000 円
  プレビュー: 3000 円
```

> [!NOTE]
> 上記は代表的な実行ケースを示したものです。全ケースの検証は別途テストで行ってください。

### 7-2：動作シーケンス図

ステップ4で到達したStrategyパターンの実行時のオブジェクト間のやり取りを可視化します。`main()` が依存関係を注入し、`PaymentCalculator` が具象クラスを知らずに抽象インターフェース経由で処理を委譲する流れが確認できます。

```mermaid
sequenceDiagram
    participant M as main / OrderProcessor
    participant DB as CustomerDatabase
    participant F as RuleFactory
    participant P as PaymentCalculator
    participant I as IDiscountRule<br/>(PremiumDiscount)

    M->>DB: exists(customerId)
    DB-->>M: true
    M->>DB: get(customerId)
    DB-->>M: CustomerInfo
    M->>F: create(memberType, context)
    F-->>M: rule
    M->>P: 生成 (rule を注入)
    M->>P: calculate(order)
    activate P
    P->>I: apply(total)
    activate I
    I-->>P: 割引後金額
    deactivate I
    P-->>M: finalPrice
    deactivate P
```

### 7-3：変更影響グラフ（改善後）

```mermaid
graph LR
    T1["変更要求：新しい割引ルールの追加"] --> F1["新しい割引クラス"]
    T1 --> F2["RuleFactory<br>選択条件の追加"]
    T1 -. "入力項目が増える場合" .-> F3["Order<br>データ項目の追加"]
    T1 -. "影響なし" .-> A["PaymentCalculator ✅"]
    T1 -. "影響なし" .-> B["CartPreviewService ✅"]
```

フェーズ3の変更影響グラフと比べると、割引の計算詳細は新しいルールクラスへ移り、計算本体の条件分岐は変更せずに済みます。一方、**どのルールを選ぶか**という条件は `RuleFactory` に残り、施策を表す入力項目が増えるなら `Order` も変わります。Strategyが分離するのは計算アルゴリズムであり、選択条件や入力モデルまで自動的に不変にするわけではありません。

### 7-4：変更シナリオ表

| **シナリオ** | **現状コードでの影響** | **この設計での影響** |
|---|---|---|
| サマーセール割引を追加 | `PaymentCalculator` の if 文を修正 | `SummerSaleDiscount` を新規作成、`RuleFactory` に1行追加 |
| クーポン割引（定額）を追加 | `PaymentCalculator` の if 文を修正 | `CouponDiscount` を新規作成、`RuleFactory` に1行追加 |
| プレミアム割引率を変更 | `PaymentCalculator` の計算式を直接修正 | `PremiumDiscount` の計算式のみ修正 |

---

## 整理

### 問題・原因・課題・解決策

| | 内容 |
|---|---|
| **問題** | 割引の「実行する振る舞い」が変わるたびに計算本体と入力モデルを修正し、利用側まで広く回帰確認する。変わる理由が異なる知識が同じ場所に混在しているため |
| **原因** | 割引ルールが「毎月追加される」と確認できているのに、`PaymentCalculator`が全種類の条件と計算方法を抱え込んでいる |
| **課題** | 割引ロジックを外から差し替えられるようにし、`PaymentCalculator` は受け取るだけにする |
| **解決策** | Strategy パターン：`IDiscountRule` を接続点として、外からルールを注入する |

### フェーズとこの章でやったこと

| **フェーズ** | **この章でやったこと** |
|---|---|
| 🔵 フェーズ1：現状把握 | 仕様と動作例テーブルを確認した後、コードをクラス単位で読んだ。クラス構成図と変更要求を把握した |
| 🟣 フェーズ2：仮説立案 | 責任チェック表でクラスごとの変わる理由を確認した。今回の確定変更とヒアリングで判明した将来リスクを分けて整理した |
| 🟣 フェーズ3：問題特定 | サマーセールの追加を試み、`Order` の修正と `CartPreviewService` の回帰確認まで必要になることを確認した |
| 🟠 フェーズ4：原因分析 | 変わる理由が異なる2つのものが同じ場所にいることが痛みの根本と特定した |
| 🟡 フェーズ5：課題定義 | 接続点では `int` 型の割引後金額を受け渡し、変わる割引ルールを本体から分ける課題を定めた |
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
| 2. 接続点の診断 | フェーズ4で、割引条件の知識が計算の骨格へ漏れている状態を確認した |
| 3. 変更局所化の説明 | フェーズ7の変更シナリオ表で、変更の中心が新しい実装クラスへ移る構造を示した |
| 4. いつ構造を分けるか | フェーズ6の「どこまで設計を進めるのが良いか」で判断基準を示した |

### 3つの設計原則はどう適用されたか

**原則1「変わるものをカプセル化せよ」の現れ**

- 具体化された場所：`PremiumDiscount` / `SummerSaleDiscount` 等の実装クラス
- 解説：頻繁に変わる「割引の計算詳細」を個別クラスに閉じ込めた。新しいルールでは選択箇所や入力モデルが変わる場合もあるが、`PaymentCalculator` の計算フローは保てる。

**原則2「実装ではなくインターフェースに対してプログラムせよ」の現れ**

- 具体化された場所：`PaymentCalculator` のメンバ変数 `IDiscountRule* rule`
- 解説：具体的な割引クラスではなく `IDiscountRule` インターフェースだけを知ることで、実行時にどの割引が適用されるかを気にせず計算フローを進められる。

**原則3「継承よりコンポジションを優先せよ」の現れ**

- 具体化された場所：`PaymentCalculator` と割引ルールの接続
- 解説：コンストラクタインジェクションによるコンポジションで、計算本体と選択したルールを実行時に組み合わせる。複数の割引を重ねるには、組み合わせ用Strategy、ルールの列、Decoratorなど、別の構成方法が必要になる。

---

## あなたのコードで考えてみてください

1. **変動の兆候を探す：** あなたのコードに「条件が1つ増えるたびに、既存の `if-else` チェーンを開いて書き足している」メソッドがありますか？
2. **変える理由を問う：** そのメソッド内の各条件は、どの業務機能に属しますか？同じ業務機能で完結していますか、それとも複数の業務機能が絡んでいますか？
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
- **別の構造も検討する：** 独立したルールを同時に複数適用し、組み合わせが増え続ける場合。Strategyを組み合わせ用クラスだけで表すとクラス数が増えるため、適用順序を持つルール列やDecoratorなどと比較する。

### この章のまとめ

割引計算というドメインと Strategyパターンの関係を一言で言うなら、「どの業務機能に属する知識か」を問うと、条件分岐の中に隠れていた変化軸が浮かび上がる、ということだと思います。料金・プロモーション管理とマーケティング・通知管理という2つの業務機能が、同じ `if-else` の中に混在していた——その事実に気づいた瞬間、計算の骨格と割引ルールを分けなければならない理由が、設計論としてではなく、現場のコストとして腹に落ちたのではないでしょうか。

7つのフェーズを通じて、読者は「動くコード」の観察から「変わる理由の発見」へ、そして「接続点を金額の授受だけに絞る」という判断へと、一歩ずつ進みました。フェーズ2のヒアリングで「ルールは今後も増える」と分かった時点で問題の輪郭が見え、フェーズ4で接続点の分析をした時点で解決の方向が決まる——その気づきの順序こそが、パターン名を先に覚えることでは得られない体験です。

あなたのコードの中にも、同じ条件分岐がいくつかのルールを束ねている箇所がきっとあるはずです。それぞれのケースが「どの業務機能に属する知識か」を問うことが、次の変化に備えた構造を見つける入口になります。
