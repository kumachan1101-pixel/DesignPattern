# 第2章　Facadeパターン：使う側に知らせない勇気
―― 思考の型：「各クラスの責任を把握し、責任外の関心を切り出す」

> **この章の核心**
> あるクラスが自分の責任ではない知識を持つと、
> その知識の持ち主が変わるたびに道連れになる。
> 責任を明確にし、変わる理由を1つに絞ることが、変更に強い設計への入り口だ。

---

## ステップ0：視点のチューニング ―― 「設計のレンズ」をセットする

コードを読む前に、この章で使う問いをセットアップします。

**【全パターン共通の問い】**

> 「このコードの中に、**『変わる理由』が異なる2つのものが、
> 同じ場所に混在していないか？」**

「変わる理由」とは **「誰の判断で変わるか」** のことです。
答えが2人以上になるなら、「変わる理由」が複数混在しています。

### 2.0 変動と不変の仮説（コードを読む前に立てる）

| 分類 | この章での仮説 | 根拠 |
|---|---|---|
| 🔴 **変動する** | 各外部サービスのAPI仕様・引数形式 | 外部ベンダーの都合で変わる |
| 🔴 **変動する** | 給与計算の詳細アルゴリズム | 労務規則の改定で変わる |
| 🟢 **不変** | 「月末に全社員の給与処理を完了する」業務フロー | 会社がある限り変わらない |
| 🟢 **不変** | 「処理できたか」という結果の形 | 経理上の必須要件 |

---

## ステップ1：現状把握 ―― 各クラスの責任を把握し、責任外の関心を探す

> **現状把握の本質**
> コードを読んで「動きを追う」だけでは不十分です。
> **「各クラスの責任は何か」を定義し、
> 「責任範囲外の知識を持っていないか」を確認する**のが、
> 設計上の現状把握です。

### 2.1 今のシステムの仕様とコードの構造

**要するに変わりやすい複数の外部サービスを隠して、窓口を一本化するパターン。**

月次給与バッチシステムです。`MonthlyBatch` が毎月末に起動し、
3つの外部サービスと連携して給与処理を完了させます。

| 機能 | 担当クラス | 入力 | 出力 |
|---|---|---|---|
| 勤怠取得 | LaborMgmtService | 社員ID・年・月 | 実働時間 |
| 給与計算 | PayrollService | 社員情報JSON・実働時間 | 給与額 |
| 明細生成 | PdfService | 社員ID・給与額 | PDFファイル名 |
| 処理統括 | MonthlyBatch | 年・月 | （記録・出力） |

---

**各クラスの責任と実装**

設計を読むときは、まず「このクラスの責任は何か」を確認します。
実装の中身を見ることで、責任の範囲が具体的に把握できます。

```cpp
// LaborMgmtService
// 責任：「勤怠時間を管理する」
class LaborMgmtService {
public:
    double getWorkHours(
        int employeeId, int year, int month
    );
};

double LaborMgmtService::getWorkHours(
    int employeeId, int year, int month
) {
    // 出退勤ログを集計して実働時間を返す
    // （ここでは固定値で代表）
    return 172.5; // 2024年12月の実働時間
}
```

LaborMgmtServiceが知っていること：社員IDと年月から実働時間を導く方法。
給与の計算ルールも、PDFの生成方法も、関知しません。

```cpp
// PayrollService
// 責任：「給与額を計算する」
// API仕様：社員情報はJSON形式で受け取る（例: {"base":300000}）
class PayrollService {
public:
    double calculateV1(
        const std::string& employeeJson,
        double workHours
    );
private:
    double parseBaseSalary(const std::string& json);
};

double PayrollService::calculateV1(
    const std::string& employeeJson,
    double workHours
) {
    double base = parseBaseSalary(employeeJson);
    // 160時間超は時給2500円で残業代を加算
    double overtime = (workHours > 160.0)
        ? (workHours - 160.0) * 2500.0
        : 0.0;
    return base + overtime;
}

double PayrollService::parseBaseSalary(
    const std::string& json
) {
    // {"base":300000} → 300000.0
    return 300000.0;
}
```

PayrollServiceが知っていること：給与の計算ルールと、自分のAPI形式（JSON形式）。
勤怠の集計方法も、PDF生成方法も、関知しません。

```cpp
// PdfService
// 責任：「給与明細PDFを生成する」
class PdfService {
public:
    std::string generate(int employeeId, double amount);
};

std::string PdfService::generate(
    int employeeId, double amount
) {
    // ファイル名規則: slip_{社員ID}_{給与額}.pdf
    return "slip_"
        + std::to_string(employeeId)
        + "_" + std::to_string((int)amount)
        + ".pdf";
}
```

PdfServiceが知っていること：ファイル命名規則とPDFのレイアウト。
給与の計算方法も、勤怠の集計方法も、関知しません。

---

これで3つのサービスの責任と実装が見えました。
次に、これらを呼び出す `MonthlyBatch` を見ます。

```cpp
// MonthlyBatch（今の設計）
// 責任のはず：「月次給与処理を完了させる」
class MonthlyBatch {
public:
    void run(int year, int month);
private:
    PayrollService   payroll_;
    LaborMgmtService labor_;
    PdfService       pdf_;
};

void MonthlyBatch::run(int year, int month) {
    int employeeId = 1001;

    double hours = labor_.getWorkHours(
        employeeId, year, month
    );

    // PayrollServiceのAPI仕様に従ってJSONを組み立てる
    std::string json = "{\"base\":300000}";
    double amount = payroll_.calculateV1(json, hours);

    std::string slipFile = pdf_.generate(employeeId, amount);

    saveResult(year, month, amount, slipFile);
}

int main() {
    MonthlyBatch batch;
    batch.run(2024, 12);
    return 0;
}
```

**実行結果：**
```
[LaborMgmt]    社員1001: 実働 172.5時間
[Payroll]      基本給 300000円 + 残業 31250円 = 331250円
[Pdf]          slip_1001_331250.pdf を生成
[MonthlyBatch] 2024年12月 処理完了
```

動いています。では、**責任チェック**に入ります。

---

**責任チェック：MonthlyBatchは自分の責任だけを持っているか**

MonthlyBatchの責任は「月次給与処理を完了させること」です。
その責任を果たすために、MonthlyBatchが「知るべきこと」は何でしょうか。

> 対象の年・月。処理の流れ（勤怠取得→計算→明細生成→保存）。

今のコードで `MonthlyBatch::run()` が「知っていること」を1行ずつ確認します。

| コードの行 | 持っている知識 | MonthlyBatchの責任か |
|---|---|---|
| `labor_.getWorkHours(id, year, month)` | 勤怠取得の流れ | ○ 処理の流れとして自然 |
| `"{\"base\":300000}"` のJSON組み立て | PayrollServiceのAPI形式 | **✗ PayrollServiceの責任** |
| `payroll_.calculateV1(json, hours)` | APIメソッド名・バージョン | **✗ PayrollServiceの内部事情** |
| `pdf_.generate(employeeId, amount)` | 引数の意味（id・amount） | △ 呼び出し自体は自然 |

MonthlyBatchは `"{\"base\":300000}"` というJSON文字列を自分で組み立てています。
このJSON形式を決めているのはPayrollServiceです。
**PayrollServiceの責任（API仕様の定義）が、MonthlyBatchのコードの中に染み出しています。**

これが「責任範囲外の関心が混在している」状態です。

---

### 2.2 届いた変更要求

以上の責任チェックを踏まえた上で、変更要求を受け取ります。

---

**インフラ担当**：「PayrollServiceがv2になります。
引数の形式が変わり、`calcSalary(employeeId, hours)` になります。
JSONは不要です。」

**開発者**：「PayrollServiceが変わっただけなのに、
　　　　　　なぜMonthlyBatchを開いているのだろう…」

---

責任チェックで確認した通り、PayrollServiceのAPI形式という
「PayrollServiceの責任」がMonthlyBatchの中に染み出していたため、
その持ち主（PayrollService）が変わればMonthlyBatchも変わります。

**依存の広がり**

```mermaid
graph TD
    A[MonthlyBatch.cpp<br/>月次バッチ処理]
    B[PayslipExporter.cpp<br/>明細出力処理]
    C[OvertimeAlertJob.cpp<br/>残業アラートJob]
    X[PayrollService<br/>給与計算サービス]

    A -->|直接依存| X
    B -->|直接依存| X
    C -->|直接依存| X

    style X fill:#ffcccc,stroke:#cc0000
    style A fill:#ffe8cc,stroke:#cc7700
    style B fill:#ffe8cc,stroke:#cc7700
    style C fill:#ffe8cc,stroke:#cc7700
```

```bash
$ grep -r "PayrollService\|calculateV1" .
MonthlyBatch.cpp:9     PayrollService payroll_;
MonthlyBatch.cpp:24    payroll_.calculateV1(json, hours);
PayslipExporter.cpp:7  PayrollService payroll_;
PayslipExporter.cpp:19 payroll_.calculateV1(json, hours);
OvertimeAlertJob.cpp:5 PayrollService payroll_;
OvertimeAlertJob.cpp:15 payroll_.calculateV1(json, hours);
# → 3ファイルにPayrollServiceの責任が染み出している
```

---

## ステップ2：変動と不変の峻別 ―― 仮説をコードで検証する

### 2.3 仮説の検証と変動/不変の確定

| 分類 | 具体的な内容 | 変わるタイミング | 設計への影響 |
|---|---|---|---|
| 🔴 変動 | PayrollServiceのAPI仕様・バージョン | ベンダーのリリース | 呼び出し元に置いてはいけない |
| 🔴 変動 | LaborMgmtServiceの引数形式 | 人事システム改修 | 呼び出し元に置いてはいけない |
| 🔴 変動 | PDFファイル命名規則 | PdfService仕様変更 | 呼び出し元に置いてはいけない |
| 🟢 不変 | 「給与処理を完了する」業務フロー | 変わる日は来ない | ここを契約として固定する |

> **設計の決断**：🟢 不変な業務フローを「契約（インターフェース）」として固定し、
> 🔴 変動する各サービスの詳細は、それぞれのインターフェースの裏側に押し込む。

---

## ステップ3：課題分析 ―― 変更しようとしたときの困難と痛み

### 2.4 変更しようとしたときの困難

PayrollService が v2 になる場合の修正：

```cpp
// 変更前：MonthlyBatchがPayrollServiceのJSON形式を知っていた
std::string json = "{\"base\":300000}";
double amount = payroll_.calculateV1(json, hours);

// 変更後：API形式が変わったのでMonthlyBatchも変更
double amount = payroll_.calcSalary(employeeId, hours);
```

**「PayrollServiceの責任範囲が変わっただけ」で、
MonthlyBatch（月次処理の本体）のコードを開いて変更しています。**

MonthlyBatchの責任（月次処理の完了）は何も変わっていないのに。

**変更影響グラフ（改善前）**

```mermaid
graph LR
    subgraph 変更のトリガー
        T[PayrollService v1 → v2]
    end
    subgraph 変更が必要なファイル
        A[MonthlyBatch.cpp]
        B[PayslipExporter.cpp]
        C[OvertimeAlertJob.cpp]
    end
    T -->|影響が飛び火| A
    T -->|影響が飛び火| B
    T -->|影響が飛び火| C

    style T fill:#ffcccc,stroke:#cc0000
    style A fill:#ffe8cc,stroke:#cc7700
    style B fill:#ffe8cc,stroke:#cc7700
    style C fill:#ffe8cc,stroke:#cc7700
```

---

## ステップ4：原因分析 ―― 困難の根本にあるもの

### 2.5 困難の根本にあるもの

| 問い | 答え |
|---|---|
| なぜMonthlyBatchを変更しなければならないか？ | PayrollServiceのAPI知識がMonthlyBatchの中にあるから |
| なぜMonthlyBatchにその知識があるか？ | 「処理の流れ（What）」と「各サービスの呼び方（How）」を同じクラスに書いたから |
| 根本原因は？ | **各クラスの責任が混在している。MonthlyBatchがPayrollServiceの責任を代わりに持っている** |

**構造的原因の言語化：**

> 「知りすぎているクラスは、知っている相手の変更に道連れになる。」
>
> 知識の持ち主（PayrollService）が変われば、
> その知識を借りているクラス（MonthlyBatch）も変わらざるを得ない。
> 解決策は「各クラスが自分の責任の知識だけを持つ」構造を作ることだ。

---

## ステップ5：対策案の検討 ―― 責任の境界線を引く

> **この章の思考の進め方**
> 1つの解決案を作るたびに「責任チェック」を行います。
> チェックをパスしない限り、次の改善へ進みます。
> この繰り返しが、最終設計へ至る思考の道筋です。

### 2.6 最初の試み：【試行コード】

**試み①：3サービスの呼び出しを専用クラスに移す**

MonthlyBatchからPayrollServiceの知識を追い出すために、
3サービスへの呼び出しを `PayrollFacade` クラスに集めます。

```cpp
class PayrollFacade {
public:
    void process(int year, int month);
private:
    PayrollService   payroll_; // ← 具体クラスを直接持っている
    LaborMgmtService labor_;
    PdfService       pdf_;
};

void PayrollFacade::process(int year, int month) {
    int employeeId = 1001;
    double hours = labor_.getWorkHours(
        employeeId, year, month
    );
    std::string json = "{\"base\":300000}";
    double amount = payroll_.calculateV1(json, hours);
    std::string slip = pdf_.generate(employeeId, amount);
    saveResult(year, month, amount, slip);
}

class MonthlyBatch {
public:
    void run(int year, int month);
private:
    PayrollFacade facade_; // ← 3サービスの代わりに1つ
};

void MonthlyBatch::run(int year, int month) {
    facade_.process(year, month);
}
```

**責任チェック（MonthlyBatch）**

| コードの行 | 持っている知識 | MonthlyBatchの責任か |
|---|---|---|
| `facade_.process(year, month)` | 給与処理を依頼する | ○ |

MonthlyBatchの責任チェックは通過しました。

**しかし新たな問題が見えてきます。**

PayrollFacadeの責任チェックを確認します。

| PayrollFacadeが持っている知識 | 誰の責任か |
|---|---|
| `PayrollService` の具体クラス | PayrollServiceの実装 |
| `LaborMgmtService` の具体クラス | LaborMgmtServiceの実装 |
| `PdfService` の具体クラス | PdfServiceの実装 |
| `"{\"base\":300000}"` のJSON形式 | PayrollServiceのAPI仕様 |

PayrollFacadeは3つのサービスの具体クラスを直接持っています。
変わる理由が3つある状態です。
また、PayrollServiceが変わればPayrollFacadeも変わります。
**「MonthlyBatchからPayrollFacadeへ」問題が移動しただけです。**

さらに、テストの問題も残ります。

```cpp
TEST(MonthlyBatchTest, RunsPayrollProcess) {
    MonthlyBatch batch;
    // PayrollFacadeが具象クラスなので差し替えられない
    // テスト中に本物の3サービスが全て動く
    batch.run(2024, 12);
}
```

試み①では不十分です。次の改善へ進みます。

---

**試み②：MonthlyBatchとPayrollFacadeの間に契約を置く**

MonthlyBatchが「具体的なPayrollFacade」を知っているのが問題です。
「給与処理を完了してくれる何か」という契約（インターフェース）を定義します。

```cpp
// MonthlyBatchが知るべき「契約」だけを定義する
class IPayrollFacade {
public:
    virtual ~IPayrollFacade() {}
    virtual void process(int year, int month) = 0;
};

// MonthlyBatchは契約だけを知る
class MonthlyBatch {
public:
    explicit MonthlyBatch(IPayrollFacade* facade);
    void run(int year, int month);
private:
    IPayrollFacade* facade_; // ← 契約だけを知る
};

MonthlyBatch::MonthlyBatch(IPayrollFacade* facade)
    : facade_(facade) {}

void MonthlyBatch::run(int year, int month) {
    facade_->process(year, month);
}
```

**責任チェック（MonthlyBatch）**

MonthlyBatchは `IPayrollFacade` という契約だけを知っています。
PayrollService・LaborMgmtService・PdfServiceの名前は一切見えません。
責任チェック：通過。

テストも可能になりました。

```cpp
class StubPayrollFacade : public IPayrollFacade {
public:
    bool called = false;
    void process(int year, int month) override {
        called = true;
    }
};

TEST(MonthlyBatchTest, CallsFacade) {
    StubPayrollFacade stub;
    MonthlyBatch batch(&stub);
    batch.run(2024, 12);
    EXPECT_TRUE(stub.called);
}
```

MonthlyBatchの問題は解決しました。

**しかし、PayrollFacadeはまだ改善できます。**

```cpp
// 現状のPayrollFacade：3つの具体クラスを直接持っている
class PayrollFacade : public IPayrollFacade {
private:
    PayrollService   payroll_; // ← 具体クラス
    LaborMgmtService labor_;   // ← 具体クラス
    PdfService       pdf_;     // ← 具体クラス
};
```

PayrollFacadeが具体クラスを直接持っているため、
PayrollServiceが変わればPayrollFacadeが変わります。
PayrollFacadeが各サービスの実装詳細（具体クラス）に依存したままです。

試み②はMonthlyBatchを救いましたが、PayrollFacadeはまだ改善できます。

---

**試み③：各サービスにも契約を定義する**

各サービスに対しても、同じ考え方を適用します。
「具体的なPayrollService」ではなく「給与を計算してくれる何か」という契約を定義します。

```cpp
// 各サービスの契約（インターフェース）
class IPayrollService {
public:
    virtual ~IPayrollService() {}
    virtual double calcSalary(
        int employeeId, double workHours) = 0;
};

class ILaborMgmtService {
public:
    virtual ~ILaborMgmtService() {}
    virtual double getWorkHours(
        int employeeId, int year, int month) = 0;
};

class IPdfService {
public:
    virtual ~IPdfService() {}
    virtual std::string generate(
        int employeeId, double amount) = 0;
};
```

```cpp
// PayrollFacadeは契約だけを知る
class PayrollFacade : public IPayrollFacade {
public:
    PayrollFacade(
        IPayrollService*   payroll,
        ILaborMgmtService* labor,
        IPdfService*       pdf
    );
    void process(int year, int month) override;
private:
    IPayrollService*   payroll_; // ← 契約だけを知る
    ILaborMgmtService* labor_;
    IPdfService*       pdf_;
};

PayrollFacade::PayrollFacade(
    IPayrollService*   payroll,
    ILaborMgmtService* labor,
    IPdfService*       pdf
) : payroll_(payroll), labor_(labor), pdf_(pdf) {}

void PayrollFacade::process(int year, int month) {
    int employeeId = 1001;
    double hours = labor_->getWorkHours(
        employeeId, year, month
    );
    double amount = payroll_->calcSalary(
        employeeId, hours
    );
    std::string slip = pdf_->generate(employeeId, amount);
    saveResult(year, month, amount, slip);
}
```

**責任チェック（PayrollFacade）**

| PayrollFacadeが持っている知識 | 誰の責任か |
|---|---|
| IPayrollService（契約） | 給与計算の「できること」の定義 |
| ILaborMgmtService（契約） | 勤怠取得の「できること」の定義 |
| IPdfService（契約） | 明細生成の「できること」の定義 |
| 3サービスを協調させる手順 | ○ PayrollFacadeの責任 |

PayrollFacadeは各サービスの「契約」だけを知っています。
具体クラスは見えていません。責任チェック：通過。

**もう1つ問題が残っています。**
「誰が具体クラスを生成し、注入するか」です。

現在の `main()` を見てみます：

```cpp
// ← main()がここで全ての具体クラスを知っている
int main() {
    PayrollServiceImpl   payroll;
    LaborMgmtServiceImpl labor;
    PdfServiceImpl       pdf;
    PayrollFacade facade(&payroll, &labor, &pdf);
    MonthlyBatch  batch(&facade);
    batch.run(2024, 12);
}
```

`main()` はプログラムの入り口です。機能をキックする責任を持ちます。
「どのクラスをどう組み立てるか」は `main()` の責任ではありません。
この組み立ての責任は、専用のクラスが持つべきです。

---

### 2.7 発想の転換：【解決コード】

**試み④：BatchApplicationが組み立てを担う**

組み立ての責任を `BatchApplication` クラスに与えます。
具体クラスを知っているのは `BatchApplication` だけです。

```cpp
// BatchApplication
// 責任：「依存を組み立て、バッチを起動する」
class BatchApplication {
public:
    void run(int year, int month);
};

void BatchApplication::run(int year, int month) {
    // 具体クラスを知っているのはここだけ
    PayrollServiceImpl   payroll;
    LaborMgmtServiceImpl labor;
    PdfServiceImpl       pdf;

    PayrollFacade facade(&payroll, &labor, &pdf);
    MonthlyBatch  batch(&facade);

    batch.run(year, month);
}

// main()は入り口としてキックするだけ
int main() {
    BatchApplication app;
    app.run(2024, 12);
    return 0;
}
```

**最終的な責任チェック（全クラス）**

| クラス | 責任（1文） | 知っていること |
|---|---|---|
| `main()` | プログラムを起動する | `BatchApplication` の存在のみ |
| `BatchApplication` | 依存を組み立て、バッチを起動する | 全具体クラス（ここだけ） |
| `MonthlyBatch` | 月次給与処理のフローを完了させる | `IPayrollFacade`（契約） |
| `PayrollFacade` | 3サービスを協調させて給与処理を完了する | 3つのインターフェース（契約） |
| `PayrollServiceImpl` | 給与額を計算する | 計算ルール・自分の実装 |
| `LaborMgmtServiceImpl` | 勤怠時間を管理する | 勤怠ログ・自分の実装 |
| `PdfServiceImpl` | 給与明細PDFを生成する | ファイル命名規則・自分の実装 |

各クラスの「知っていること」に、他のクラスの責任範囲が混入していません。
これが目指した状態です。

**変更後のクラス図**

```mermaid
classDiagram
    class BatchApplication {
        +run(year, month)
    }
    class MonthlyBatch {
        -facade_: IPayrollFacade*
        +MonthlyBatch(facade)
        +run(year, month)
    }
    class IPayrollFacade {
        <<interface>>
        +process(year, month)
    }
    class PayrollFacade {
        -payroll_: IPayrollService*
        -labor_: ILaborMgmtService*
        -pdf_: IPdfService*
        +process(year, month)
    }
    class IPayrollService {
        <<interface>>
        +calcSalary(id, hours) double
    }
    class ILaborMgmtService {
        <<interface>>
        +getWorkHours(id, y, m) double
    }
    class IPdfService {
        <<interface>>
        +generate(id, amount) string
    }
    class PayrollServiceImpl { +calcSalary(id, hours) }
    class LaborMgmtServiceImpl { +getWorkHours(id, y, m) }
    class PdfServiceImpl { +generate(id, amount) }

    BatchApplication  --> MonthlyBatch      : 組み立て・起動
    BatchApplication  --> PayrollFacade     : 組み立て
    MonthlyBatch      --> IPayrollFacade    : 契約だけを知る
    IPayrollFacade    <|.. PayrollFacade    : 実装
    PayrollFacade     --> IPayrollService   : 契約だけを知る
    PayrollFacade     --> ILaborMgmtService : 契約だけを知る
    PayrollFacade     --> IPdfService       : 契約だけを知る
    IPayrollService   <|.. PayrollServiceImpl
    ILaborMgmtService <|.. LaborMgmtServiceImpl
    IPdfService       <|.. PdfServiceImpl
```

---

## ステップ6：天秤にかける ―― 柔軟性とシンプルさのバランスを評価する

### 2.8 比較の基準を先に宣言する

1. **変更の局所性** ―― サービス仕様変更の影響が1箇所に収まるか
2. **テストの独立性** ―― 各クラスを他クラスなしで単独テストできるか
3. **責任の明確さ** ―― 各クラスが自分の責任だけを持っているか
4. **実装コスト** ―― 今すぐ払う手間はどれくらいか

### 2.9 比較と判断

| 評価軸 | ❌ 改善前 | ✅ 解決後 |
|---|---|---|
| 変更の局所性 | PayrollService変更 → 3ファイル変更 | PayrollServiceImpl のみ変更 |
| テストの独立性 | 本番サービスなしでテスト不可 | 各クラスをスタブで単独テスト可 |
| 責任の明確さ | MonthlyBatchに3サービスの責任が混在 | 各クラスが自分の責任のみを持つ |
| 実装コスト | 少ない | 多い（インターフェース・クラス数が増える） |

設計に絶対の正解はありません。
ただ「責任が明確な設計」では、変更の影響が予測できます。
「このクラスを変えれば、影響するのはここだけ」と言える状態です。

**適用判断のフローチャート**

```mermaid
flowchart TD
    A[外部サービスの仕様変更は繰り返し発生するか？]
    A -->|Yes| B[そのサービスを呼ぶ場所が複数あるか？]
    A -->|No| G[シンプルな直接依存のままでよい]
    B -->|Yes| C[Facadeパターンを適用する]
    B -->|No| D[1箇所だけなら様子見でもよい]

    style C fill:#ccffcc,stroke:#00aa00
    style G fill:#ffe8cc,stroke:#cc7700
    style D fill:#ffe8cc,stroke:#cc7700
```

一つの参考として受け取っていただければと思います。

### 2.10 より難しい変化への耐久テスト

「PayrollServiceとLaborMgmtServiceが同時に変わった」とします。

**【深化コード】**

```cpp
// PayrollService v2: 新しいインターフェースを実装
class PayrollServiceV2Impl : public IPayrollService {
public:
    double calcSalary(
        int employeeId, double workHours) override {
        // v2の計算ルールで実装
        double base = fetchBaseSalary(employeeId);
        double rate = (workHours > 160.0) ? 3000.0 : 0.0;
        double overtime = (workHours - 160.0) * rate;
        return base + overtime;
    }
private:
    double fetchBaseSalary(int employeeId) {
        return 320000.0; // v2では社員ごとの基本給を参照
    }
};

// BatchApplicationで新しい実装に差し替えるだけ
void BatchApplication::run(int year, int month) {
    PayrollServiceV2Impl payroll; // ← ここだけ変わる
    LaborMgmtServiceImpl labor;
    PdfServiceImpl       pdf;
    PayrollFacade facade(&payroll, &labor, &pdf);
    MonthlyBatch  batch(&facade);
    batch.run(year, month);
}

// MonthlyBatch・PayrollFacade・各インターフェースは
// 一行も変わらない
```

変更は `PayrollServiceV2Impl` の追加と
`BatchApplication` の1行差し替えだけです。
「責任が明確な設計」だから変更が局所化されています。

### 2.11 使う場面・使わない場面

**【過剰コード】**

```cpp
// ❌ やりすぎの例
// 変わらない1行の計算にFacadeとインターフェースを作る
class ITaxFacade {
public:
    virtual ~ITaxFacade() {}
    virtual double calculate(double amount) = 0;
};
class TaxFacadeImpl : public ITaxFacade {
public:
    double calculate(double amount) override {
        return amount * 0.1; // 消費税10%。変わらない。
    }
};
// 責任の混在が起きていない場所に
// Facadeを入れる必要はない。
```

| 使う場面 | 使わない場面 |
|---|---|
| 複数サービスの責任が呼び出し元に混在している | 責任の混在が起きていない |
| 外部サービスの仕様変更が繰り返し発生する | 一度作ったら変わらない処理 |
| 各クラスを単独でテストしたい | 結合テストで十分な場面 |

---

## ステップ7：決断と、手に入れた未来

### 2.12 解決後のコード（全体）

**変更に強い設計の完成形**

```cpp
// ── インターフェース定義 ──────────────────────

class IPayrollService {
public:
    virtual ~IPayrollService() {}
    virtual double calcSalary(
        int employeeId, double workHours) = 0;
};

class ILaborMgmtService {
public:
    virtual ~ILaborMgmtService() {}
    virtual double getWorkHours(
        int employeeId, int year, int month) = 0;
};

class IPdfService {
public:
    virtual ~IPdfService() {}
    virtual std::string generate(
        int employeeId, double amount) = 0;
};

class IPayrollFacade {
public:
    virtual ~IPayrollFacade() {}
    virtual void process(int year, int month) = 0;
};

// ── 実装クラス ────────────────────────────────

class PayrollServiceImpl : public IPayrollService {
public:
    double calcSalary(
        int employeeId, double workHours) override {
        double base = 300000.0;
        double overtime = (workHours > 160.0)
            ? (workHours - 160.0) * 2500.0
            : 0.0;
        return base + overtime;
    }
};

class LaborMgmtServiceImpl : public ILaborMgmtService {
public:
    double getWorkHours(
        int employeeId, int year, int month) override {
        return 172.5;
    }
};

class PdfServiceImpl : public IPdfService {
public:
    std::string generate(
        int employeeId, double amount) override {
        return "slip_"
            + std::to_string(employeeId)
            + "_" + std::to_string((int)amount)
            + ".pdf";
    }
};

// ── Facade ────────────────────────────────────

class PayrollFacade : public IPayrollFacade {
public:
    PayrollFacade(
        IPayrollService*   payroll,
        ILaborMgmtService* labor,
        IPdfService*       pdf
    ) : payroll_(payroll), labor_(labor), pdf_(pdf) {}

    void process(int year, int month) override {
        int employeeId = 1001;
        double hours = labor_->getWorkHours(
            employeeId, year, month
        );
        double amount = payroll_->calcSalary(
            employeeId, hours
        );
        std::string slip = pdf_->generate(
            employeeId, amount
        );
        saveResult(year, month, amount, slip);
    }
private:
    IPayrollService*   payroll_;
    ILaborMgmtService* labor_;
    IPdfService*       pdf_;
};

// ── MonthlyBatch ──────────────────────────────

class MonthlyBatch {
public:
    explicit MonthlyBatch(IPayrollFacade* facade)
        : facade_(facade) {}

    void run(int year, int month) {
        facade_->process(year, month);
    }
private:
    IPayrollFacade* facade_;
};

// ── 組み立てと起動 ────────────────────────────

class BatchApplication {
public:
    void run(int year, int month) {
        PayrollServiceImpl   payroll;
        LaborMgmtServiceImpl labor;
        PdfServiceImpl       pdf;
        PayrollFacade facade(&payroll, &labor, &pdf);
        MonthlyBatch  batch(&facade);
        batch.run(year, month);
    }
};

int main() {
    BatchApplication app;
    app.run(2024, 12);
    return 0;
}
```

**実行結果：**
```
[LaborMgmt]    社員1001: 実働 172.5時間
[Payroll]      基本給 300000円 + 残業 31250円 = 331250円
[Pdf]          slip_1001_331250.pdf を生成
[MonthlyBatch] 2024年12月 処理完了
```

---

**テストで動作を保証する**

インターフェースがあるため、各クラスを独立してテストできます。

```cpp
// スタブ：本物のサービスを呼ばずに動く差し替えクラス。
// IPayrollFacadeを継承することで
// 本番のPayrollFacadeとそのまま入れ替えられる。
class StubPayrollFacade : public IPayrollFacade {
public:
    bool called      = false;
    int  calledYear  = 0;
    int  calledMonth = 0;

    void process(int year, int month) override {
        called      = true;
        calledYear  = year;
        calledMonth = month;
    }
};

TEST(MonthlyBatchTest, CallsFacadeWithCorrectYearMonth) {
    StubPayrollFacade stub;
    MonthlyBatch batch(&stub);

    batch.run(2024, 12);

    // EXPECT_TRUE(条件)：条件が真ならテスト通過。Google Testのマクロ。
    EXPECT_TRUE(stub.called);
    // EXPECT_EQ(期待値, 実際の値)：等しければテスト通過。
    EXPECT_EQ(2024, stub.calledYear);
    EXPECT_EQ(12,   stub.calledMonth);
}
```

```
[  PASSED  ] MonthlyBatchTest.CallsFacadeWithCorrectYearMonth
```

---

**変更に強いことを確認する**

| 変更のシナリオ | 変わるクラス | 変わらないクラス |
|---|---|---|
| PayrollService APIが変わる | `PayrollServiceImpl` のみ | 他の全クラス |
| 別の給与計算エンジンに切り替える | `BatchApplication`（差し替え先を指定） | 他の全クラス |
| LaborMgmtService APIが変わる | `LaborMgmtServiceImpl` のみ | 他の全クラス |
| PDF命名規則が変わる | `PdfServiceImpl` のみ | 他の全クラス |
| 月次処理の業務フローが変わる | `MonthlyBatch` | 各サービス実装 |

「変わる理由が異なるクラス」が「別の場所にいる」。
これが変更に強い設計の正体です。

**変更影響グラフ（改善後）**

```mermaid
graph LR
    subgraph 変更のトリガー
        T[PayrollService v1 → v2]
    end
    subgraph 変更が必要なファイル
        F[PayrollServiceImpl.cpp のみ]
    end
    subgraph 変更不要なファイル
        A[MonthlyBatch.cpp ✅]
        B[PayrollFacade.cpp ✅]
        C[BatchApplication.cpp ✅]
        D[PayslipExporter.cpp ✅]
        E[OvertimeAlertJob.cpp ✅]
    end
    T --> F
    T -. 影響なし .-> A
    T -. 影響なし .-> B
    T -. 影響なし .-> C
    T -. 影響なし .-> D
    T -. 影響なし .-> E

    style T fill:#ffcccc,stroke:#cc0000
    style F fill:#ccffcc,stroke:#00aa00
```

---

## 整理

### 2.13 8ステップとこの章でやったこと

| ステップ | この章でやったこと |
|---|---|
| ステップ0 | 「API仕様は変動、業務フローは不変」という仮説を立てた |
| ステップ1 | 各クラスの責任を定義し、責任チェックでMonthlyBatchに責任外の知識が混在していることを確認した |
| ステップ2 | 変更要求を受け取り、責任の混在が変更の飛び火を生む構造を確認した |
| ステップ3 | PayrollService変更が3ファイルに飛び火する痛みを確認した |
| ステップ4 | 「知りすぎているクラスは道連れになる」という根本原因を言語化した |
| ステップ5 | 試行①→②→③→④と段階的に責任を整理し、最終設計に至った |
| ステップ6 | 変更の局所性・責任の明確さを評価軸にして適用を判断した |
| ステップ7 | 全コードを示し、変更シナリオ別に「変わるクラス・変わらないクラス」で効果を確認した |

**各クラスの最終的な責任**

| クラス | 責任 | 変わる理由 |
|---|---|---|
| `main()` | プログラムを起動する | 起動方法が変わるとき |
| `BatchApplication` | 依存を組み立て、バッチを起動する | 使うクラスの組み合わせが変わるとき |
| `MonthlyBatch` | 月次給与処理のフローを完了させる | 業務フローが変わるとき |
| `PayrollFacade` | 3サービスを協調させて給与処理を完了する | 協調の手順が変わるとき |
| `PayrollServiceImpl` | 給与額を計算する | 計算ルールやAPIが変わるとき |
| `LaborMgmtServiceImpl` | 勤怠時間を管理する | 勤怠APIが変わるとき |
| `PdfServiceImpl` | 給与明細PDFを生成する | PDF仕様が変わるとき |

「変わる理由が1つ」のクラスだけで構成されている。
このプロセスを回した結果にたどり着いた構造こそが **Facadeパターン** です。

設計に絶対の正解はありません。ただ「各クラスの責任は何か」「変わる理由は1つか」を
問い続けることが、変更に強いコードへの入り口になると私は感じています。
