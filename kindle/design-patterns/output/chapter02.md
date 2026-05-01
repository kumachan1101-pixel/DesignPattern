# 第2章　複雑な外部連携をどうシンプルにするか（Facade）
―― 思考の型：「各クラスの責任を把握し、責任外の関心を切り出す」

> **この章の核心**
> あるクラスが自分の責任ではない知識を持つと、
> その知識の持ち主が変わるたびに道連れになる。
> 責任を明確にし、変わる理由を1つに絞ることが、変更に強い設計への入り口だ。

---

## この章を読むと得られること

- 「使う側が知らなくていいこと」を知ってしまっているクラスを、コードの中から発見できるようになる
- 外部サービスの変更が内部実装に飛び火するパターンを、構造によって防ぐFacadeの設計を作れるようになる
- Facadeが過剰になる状況（外部依存が1つしかない場合、変更予定がない場合）を判断し、最小コストの代替案との使い分けができるようになる
- 変更要求が来たとき「どのクラスに知らせないか」を設計の出発点として考えられるようになる

## ステップ0：システムを把握し、仮説を立てる ―― クラス構成を見てから「変わりそうな場所」を予測する

> **入力：** システムのシナリオ説明 ＋ クラス構成の概要（仕様表・責任一覧）。実装コードはまだ読まない。
> **産物：** 変動と不変の「仮説テーブル」

**全パターンに共通する問い**

> 「このコードの中に、**『変わる理由』が異なる2つのものが、
> 同じ場所に混在していないか？」**

「変わる理由」とは **「誰の判断で変わるか」** のことです。
答えが2人以上になるなら、「変わる理由」が複数混在しています。

### 2.0 この章のシステム構成と仮説

**この章で扱うシステム：**
毎月末に全社員の給与処理を完了させる月次バッチシステムです。
`MonthlyBatch` クラスが起動し、3つの外部サービス（勤怠管理・給与計算・明細出力）を呼び出して処理を完了させます。

**仕様表（何ができるシステムか）**

| 機能 | 担当クラス | 入力 | 出力 |
|---|---|---|---|
| 勤怠取得 | LaborMgmtService | 社員ID・年・月 | 実働時間 |
| 給与計算 | PayrollService | 社員情報JSON・実働時間 | 給与額 |
| 明細生成 | PdfService | 社員ID・給与額 | PDFファイル名 |
| 処理統括 | MonthlyBatch | 年・月 | （記録・出力） |

**クラス構成の概要**

```mermaid
classDiagram
    class MonthlyBatch {
        -payroll_: PayrollService
        -labor_: LaborMgmtService
        -pdf_: PdfService
        +run(year, month)
    }
    class PayrollService {
        +calculateV1(json, hours) double
    }
    class LaborMgmtService {
        +getWorkHours(id, y, m) double
    }
    class PdfService {
        +generate(id, amount) string
    }

    MonthlyBatch --> PayrollService : 直接依存
    MonthlyBatch --> LaborMgmtService : 直接依存
    MonthlyBatch --> PdfService : 直接依存
```

*→ `MonthlyBatch` が3つの具体クラスを直接知っている。
この「直接依存」が、のちの変更飛び火の原因になる。*

**各クラスの責任一覧**

| クラス | 責任（1文） | 知るべきこと |
|---|---|---|
| `MonthlyBatch` | 月次給与処理のフローを完了させる | 年・月・処理の手順 |
| `PayrollService` | 給与額を計算する | 計算ルール・自分のAPI形式 |
| `LaborMgmtService` | 勤怠時間を集計する | 出退勤ログの集計方法 |
| `PdfService` | 給与明細を出力する | ファイル命名規則・出力形式 |

---

この構成を踏まえた上で、仮説を立てます。
`MonthlyBatch` が3つの外部サービスに直接依存していることが見えています。
どの部分が変わりやすく、どの部分は変わらないでしょうか。

**変動と不変の仮説（実装コードを読む前に立てる）**

| 分類 | 仮説 | 根拠（クラス構成から読み取れること） |
|---|---|---|
| 🔴 **変動する** | 各外部サービスのAPI仕様・引数形式 | 外部ベンダーの都合で変わる。3つの外部依存が直接見える |
| 🔴 **変動する** | 給与計算の詳細アルゴリズム | 労務規則の改定で変わる |
| 🟢 **不変** | 「月末に全社員の給与処理を完了する」業務フロー | 会社がある限り変わらない |
| 🟢 **不変** | 「処理できたか」という結果の形 | 経理上の必須要件 |

この仮説をステップ2（2.3）でヒアリング後に確定します。

---

## ステップ1：実装コードを読む ―― 責任チェックで問題の行を見つける

> **入力：** ステップ0で把握したクラス責任 ＋ 実際の実装コード
> **産物：** 責任チェック表。「このクラスが持つべきでない知識」が混在している行の発見。

### 2.1 実装コードと責任チェック

ステップ0でクラスの責任は把握しました。
ここでは実際の実装コードを読み、「責任通りに書かれているか」を1行ずつ確認します。

**要するに複数のサービス呼び出しを1つの窓口に集め、呼び出し元の複雑な依存を隠すパターン。**

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

*→ PayrollServiceの都合がシステムのあちこちに侵食している。これが問題の全体像。*

```bash
$ grep -r "PayrollService\|calculateV1" .
MonthlyBatch.cpp:9      PayrollService payroll_;
MonthlyBatch.cpp:24     payroll_.calculateV1(json, hours);
PayslipExporter.cpp:7   PayrollService payroll_;
PayslipExporter.cpp:19  payroll_.calculateV1(json, hours);
OvertimeAlertJob.cpp:5  PayrollService payroll_;
OvertimeAlertJob.cpp:15 payroll_.calculateV1(json, hours);
# → 3ファイルにPayrollServiceの責任が染み出している
```

---

## ステップ2：仮説を確定する ―― 関係者ヒアリングで「変わる理由」に根拠をつける

> **入力：** ステップ0の仮説 × ステップ1の責任チェック結果。関係者（インフラ担当・業務担当など）に直接確認する。
> **産物：** 確定した変動/不変テーブル（「誰の判断で変わるか」明記）

### 2.3 仮説の検証と変動/不変の確定

ステップ0で「外部サービスのAPI仕様は変わりやすい」「業務フローは変わらない」という仮説を立てました。
コードを読んだ結果、この仮説はコード上でも確認できます。
しかし——**コードを読んだだけで「変わる」「変わらない」と断定するのは危険です。**

変わるかどうかを知っているのは、そのサービスのオーナーだけだからです。

---

**関係者ヒアリング**

変動/不変を確定する前に、各サービスのオーナーに確認しました。

> **開発者**：「PayrollServiceのAPIについて確認させてください。
> 今後バージョンアップの予定はありますか？」
>
> **インフラ担当**：「はい、次の四半期でv2への移行を予定しています。
> 今のJSON形式の引数はなくなり、`calcSalary(employeeId, hours)` のシンプルな形になります。」
>
> **開発者**：「LaborMgmtServiceの引数形式について確認させてください。
> 社員IDの型（int）は今後変更になる可能性はありますか？」
>
> **人事システム担当**：「現時点ではintのままですが、将来的に文字列IDに変わる
> 外部システムとの統合の可能性があります。まだ確定していませんが。」
>
> **開発者**：「給与明細の出力はPDFですが、将来フォーマットが変わる可能性はありますか？」
>
> **経理担当**：「来年度からExcel出力の要望が上がっています。
> 確定ではないですが、対応できれば嬉しいです。」

---

この「社員IDの型変更リスク」には、一つ注意が必要です。
社員IDは `ILaborMgmtService`・`IPayrollService`・`IPaySlipOutputService` の
3つのインターフェースに共通して使われています。
もし `int` から `string` に変わった場合、
**3つのインターフェース全てのシグネチャが変わります**。
「具体クラスの差し替え」を1箇所に局所化する構造を作っても、
「インターフェース自体のシグネチャが変わる」状況では、その保護の外側に出てしまいます。
こういう場合は、型をどう扱うかをチームで検討する必要があります。
型変更リスクへの対処の選択肢は、2.10（耐久テスト）で改めて示します。

チームで話し合う価値がある部分だと思います。
このヒアリングがあって初めて、変動/不変テーブルに根拠が生まれます。

| 分類 | 具体的な内容 | 変わるタイミング | 根拠 |
|---|---|---|---|
| 🔴 **変動する** | PayrollServiceのAPI仕様・バージョン | 次の四半期（確定） | インフラ担当への確認 |
| 🔴 **変動する** | LaborMgmtServiceの引数形式 | 海外拠点統合時（可能性） | 人事システム担当への確認 |
| 🔴 **変動する** | 給与明細の出力フォーマット | 来年度（可能性） | 経理担当への確認 |
| 🟢 **不変** | 「給与処理を完了する」業務フロー | 変わる日は来ない | ビジネスの根幹ルール |

> **設計の決断**：🟢 不変な業務フローを「契約（インターフェース）」として固定し、
> 🔴 変動する各サービスの詳細は、それぞれのインターフェースの裏側に押し込む。

**インターフェース命名の原則**：インターフェース名はビジネス上の責任で付ける。
実装手段（PDF・メール等）で付けない。
「給与明細を出力する」責任ならば `IPaySlipOutputService` ——
PDFかExcelかはインターフェースの名前には現れない。

---

## ステップ3：課題分析 ―― 変更時の困難と痛み

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

*1つの変更が、MonthlyBatch・PayslipExporter・OvertimeAlertJobの3ファイルを道連れにする。これが設計の病巣。*

---

## ステップ4：原因分析 ―― 困難の根本にあるもの

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

## ステップ5：対策案の検討 ―― 方向性を決め、手段を順に試す

ステップ4の原因を確認します。

> **原因：MonthlyBatchが3つのサービスの内部仕様（具体クラス・API形式）を直接知っている。**

### 2.5.1 方向性の特定

原因が「呼び出し元が実装詳細を知りすぎている」なら、解消する方向性は自然に出てきます。

**→ 「依存を一つの窓口に統合する」方向。**

「統合する」という方向性が決まりました。では「どこまで統合するか」について考えます。統合の仕方には複数の手段があります。順番に試してみましょう。

---

### 2.5.2 手段①：窓口クラスでまとめる（窓口集約のみ）

最初に人が思いつく案は、「3サービスへの呼び出しを専用クラスに集める」ことです。

第0章の手札選択表を引くと：「外部依存のAPI・呼び出し構造が変わる」→ **窓口集約**（第0章 手札）。この原因に直接対応します。

```cpp
// 手段①：集約クラス PayrollCoordinator の導入
// MonthlyBatch はこれ1つだけを知ればよい状態にする
```

**残る課題：**

窓口（PayrollCoordinator）が各サービスの具体クラスを直接持っています。
PayrollServiceの内部実装が変わると、PayrollCoordinatorも変わります。
「依存の場所を集めた」だけで、「具体クラスへの依存」は残ったままです。

---

### 2.5.3 手段②：インターフェース層を加える（発想の転換）

手段①の課題（具体クラスへの依存が残る）を受けて、発想を転換します。

**「窓口と各サービスの間にインターフェース（契約）を導入する。」**

窓口（PayrollCoordinator）が具体クラスではなくインターフェースだけを知る構造にすれば、具体クラスの実装が変わっても窓口は変わりません。

このように、複雑なサブシステムへの窓口を1つにまとめ、背後を隠蔽する構造を **Facade（ファサード）パターン** と呼びます。

今回はこの問題に「層」があるため、以下の段階で適用します。

| 段階 | 使う手札 | 解決する層 |
|---|---|---|
| 第1段階 | 窓口集約 | MonthlyBatchの直接依存を集約クラスへ移す |
| 第2段階 | インターフェース抽出 | MonthlyBatchと窓口の間に契約を置く |
| 第3段階 | インターフェース抽出 | 窓口と各サービスの間も契約化する |
| 第4段階 | Composition Root | 組み立ての責任を1箇所に集める |

---

### 第1段階：集約クラスの導入（窓口集約）

**3サービスの呼び出しを専用クラスに移す**

MonthlyBatchからPayrollServiceの知識を追い出すために、
3サービスへの呼び出しを `PayrollCoordinator` クラスに集めます。

```cpp
class PayrollCoordinator {
public:
    void process(int year, int month);
private:
    PayrollService   payroll_; // ← 具体クラスを直接持っている
    LaborMgmtService labor_;
    PdfService       pdf_;
};

void PayrollCoordinator::process(int year, int month) {
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
    PayrollCoordinator coordinator_; // ← 3サービスの代わりに1つ
};

void MonthlyBatch::run(int year, int month) {
    coordinator_.process(year, month);
}
```

**責任チェック（MonthlyBatch）**

| コードの行 | 持っている知識 | MonthlyBatchの責任か |
|---|---|---|
| `coordinator_.process(year, month)` | 給与処理を依頼する | ○ |

MonthlyBatchの責任チェックは通過しました。

**しかし新たな問題が見えてきます。**

PayrollCoordinatorの責任チェックを確認します。

| PayrollCoordinatorが持っている知識 | 誰の責任か |
|---|---|
| `PayrollService` の具体クラス | PayrollServiceの実装 |
| `LaborMgmtService` の具体クラス | LaborMgmtServiceの実装 |
| `PdfService` の具体クラス | PdfServiceの実装 |
| `"{\"base\":300000}"` のJSON形式 | PayrollServiceのAPI仕様 |

PayrollCoordinatorは3つのサービスの具体クラスを直接持っています。
変わる理由が3つある状態です。
また、PayrollServiceが変わればPayrollCoordinatorも変わります。
**「MonthlyBatchからPayrollCoordinatorへ」問題が移動しただけです。**

私自身、ここで何度も迷いました。「クラスを1つ作れば解決」という思いに走りがちですが、
責任チェックなしに次へ進んでしまうと、また同じ問題を作り直すことになります。

さらに、テストの問題も残ります。

```cpp
TEST(MonthlyBatchTest, RunsPayrollProcess) {
    MonthlyBatch batch;
    // PayrollCoordinatorが具象クラスなので差し替えられない
    // テスト中に本物の3サービスが全て動く
    batch.run(2024, 12);
}
```

第1段階ではMonthlyBatchの問題は解決しましたが、PayrollCoordinatorが各サービスの具体クラスを直接持っています。次の層へ進みます。

---

### 第2段階：MonthlyBatchの独立（インターフェース抽出）

**MonthlyBatchとPayrollCoordinatorの間に契約を置く**

MonthlyBatchが「具体的なPayrollCoordinator」を知っているのが問題です。
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

> **スタブとは：** テスト専用の「偽の実装」です。本物のサービス（PayrollServiceなど）の代わりに差し込み、「呼ばれたかどうか」だけを記録します。テスト中にネットワークやDBが動かなくて済むのはこのためです。

```cpp
class StubPayrollFacade : public IPayrollFacade {
public:
    bool called = false;
    void process(int year, int month) override {
        called = true; // 呼ばれたことだけ記録
    }
};

TEST(MonthlyBatchTest, CallsFacade) {
    StubPayrollFacade stub;
    MonthlyBatch batch(&stub);
    batch.run(2024, 12);
    // EXPECT_TRUE(条件)：条件が真ならテスト通過という検証
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

第2段階でMonthlyBatchは解決しました。しかしPayrollFacadeが各サービスの具体クラスを直接持っています。次の層へ進みます。

---

### 第3段階：サービス層の独立（インターフェース抽出＋値オブジェクト化）

**各サービスにも契約を定義する**

各サービスに対しても、同じ考え方を適用します。
「具体的なPayrollService」ではなく「給与を計算してくれる何か」という契約を定義します。

インターフェース名は「ビジネス上の責任」で付けます。
「明細を出力する責任」ならば `IPaySlipOutputService`——
PDFかExcelかは名前に現れません。

**ここで一度立ち止まります。**

2.3のヒアリングで「社員IDが将来的にstring型に変わる可能性がある」という情報が出ました。
インターフェースを定義する**このタイミング**が、その知識を設計に活かす唯一の機会です。

インターフェースのシグネチャを `int employeeId` のまま定義すると、型が変わったとき3つのインターフェース全てを修正する必要があります。
第0章の「型の安定性」で示した通り、値オブジェクトでくるむと型変更をその1箇所に閉じ込められます。

> **設計の決断：`EmployeeId` 値オブジェクトを定義し、3つのインターフェースに使う**
>
> 今のコストは小さい（構造体1つの追加）。
> 将来の保護は大きい（型が変わっても `EmployeeId::value` の型だけを直せばよい）。

```cpp
// EmployeeId：社員IDの型を値オブジェクトとして定義する
// 将来 int → string になっても、このクラスの中だけを変えれば
// 3つのインターフェースのシグネチャは変わらない
struct EmployeeId {
    int value;
    explicit EmployeeId(int v) : value(v) {}
};
```

```cpp
// 各サービスの契約（インターフェース）
// 引数に EmployeeId を使うことで、型変更リスクを1箇所に封じ込める
class IPayrollService {
public:
    virtual ~IPayrollService() {}
    virtual double calcSalary(
        EmployeeId employeeId, double workHours) = 0;
};

class ILaborMgmtService {
public:
    virtual ~ILaborMgmtService() {}
    virtual double getWorkHours(
        EmployeeId employeeId, int year, int month) = 0;
};

// ビジネス責任で命名：「給与明細を出力する」責任
// PDF か Excel かは名前に現れない
class IPaySlipOutputService {
public:
    virtual ~IPaySlipOutputService() {}
    virtual std::string output(
        EmployeeId employeeId, double amount) = 0;
};
```

```cpp
// PayrollFacadeは契約だけを知る
class PayrollFacade : public IPayrollFacade {
public:
    PayrollFacade(
        IPayrollService*      payroll,
        ILaborMgmtService*    labor,
        IPaySlipOutputService* pdf
    );
    void process(int year, int month) override;
private:
    IPayrollService*      payroll_; // ← 契約だけを知る
    ILaborMgmtService*    labor_;
    IPaySlipOutputService* pdf_;
};

PayrollFacade::PayrollFacade(
    IPayrollService*      payroll,
    ILaborMgmtService*    labor,
    IPaySlipOutputService* pdf
) : payroll_(payroll), labor_(labor), pdf_(pdf) {}

void PayrollFacade::process(int year, int month) {
    EmployeeId employeeId(1001); // 値オブジェクトとして扱う
    double hours = labor_->getWorkHours(
        employeeId, year, month
    );
    double amount = payroll_->calcSalary(
        employeeId, hours
    );
    std::string slip = pdf_->output(employeeId, amount);
    saveResult(year, month, amount, slip);
}
```

**責任チェック（PayrollFacade）**

| PayrollFacadeが持っている知識 | 誰の責任か |
|---|---|
| IPayrollService（契約） | 給与計算の「できること」の定義 |
| ILaborMgmtService（契約） | 勤怠取得の「できること」の定義 |
| IPaySlipOutputService（契約） | 明細出力の「できること」の定義 |
| 3サービスを協調させる手順 | ○ PayrollFacadeの責任 |

PayrollFacadeは各サービスの「契約」だけを知っています。
具体クラスは見えていません。責任チェック：通過。

**もう1つ問題が残っています。**
「誰が具体クラスを生成し、注入するか」です。

現在の `main()` を見てみます：

```cpp
// ← main()がここで全ての具体クラスを知っている
int main() {
    PayrollServiceImpl    payroll;
    LaborMgmtServiceImpl  labor;
    PdfServiceImpl        pdf;
    PayrollFacade facade(&payroll, &labor, &pdf);
    MonthlyBatch  batch(&facade);
    batch.run(2024, 12);
}
```

`main()` はプログラムの入り口です。機能をキックする責任を持ちます。
「どのクラスをどう組み立てるか」は `main()` の責任ではありません。
この組み立ての責任は、専用のクラスが持つべきです。

---

### 第4段階：Composition Root（組み立ての責任を1箇所に集める）

**BatchApplicationが組み立てを担う**

組み立ての責任を `BatchApplication` クラスに与えます。
具体クラスを知っているのは `BatchApplication` だけです。
これを「Composition Root（コンポジションルート）」と呼びます。
「どの具体クラスを使うか」を決める権限と知識を1箇所に集め、他のクラスはインターフェースだけを知る構造を作ります。

```cpp
// BatchApplication（Composition Root）
// 責任：「依存を組み立て、バッチを起動する」
class BatchApplication {
public:
    void run(int year, int month);
};

void BatchApplication::run(int year, int month) {
    // 具体クラスを知っているのはここだけ
    PayrollServiceImpl    payroll;
    LaborMgmtServiceImpl  labor;
    PdfServiceImpl        pdf;

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
| `PdfServiceImpl` | 給与明細を出力する | ファイル命名規則・自分の実装 |

各クラスの「知っていること」に、他のクラスの責任範囲が混入していません。
これが目指した状態です。

---

## ステップ6：天秤にかける ―― 手段①と手段②を評価軸で比べる

解決策（手段②：Facade + インターフェース層）を導き出しましたが、ここで一度立ち止まります。手段①（単純な窓口集約）の方が実装がシンプルで済むからです。本当に今回の状況で、層を厚くするコストを払う価値があるかを天秤にかけます。

### 2.6.1 評価軸の宣言

比較を始める前に、今回の状況で重視する基準を明示します。

| 評価軸 | なぜこの状況で重要か |
|---|---|
| 変更の局所性 | 四半期ごとのAPI変更が確定的であり、修正範囲を最小化したい |
| テストの独立性 | 外部サービスの実機がない環境でも、ロジックを検証可能にしたい |
| 実装のシンプルさ | コードの理解しやすさと、今すぐリリースできるスピード |

### 2.6.2 手段①vs手段②の比較

宣言した評価軸で両方を測ります。

**比較のまとめ**

| 評価軸 | 手段①（窓口集約のみ） | 手段②（Facade + インターフェース） |
|---|---|---|
| 変更の局所性 | 窓口クラスの修正が必要 | 実装クラスの追加/修正のみで完了 |
| テストの独立性 | 依然として外部依存が残り、テストしづらい | 完全にスタブ化でき、単独テストが可能 |
| 実装のシンプルさ | ✅ 非常にシンプル。クラス数も少ない | ❌ クラス数・インターフェースが増える |

今回の状況では、将来のAPI変更が確実であること、および開発環境で実機テストが困難であることを考慮し、**手段②（Facadeパターンによる層化）を採用します。**

---

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

### より難しい変化への耐久テスト

「PayrollServiceとLaborMgmtServiceが同時に変わった」とします。

**実装例：2サービスが同時に変わった場合**

```cpp
// PayrollService v2: 新しいインターフェースを実装
class PayrollServiceV2Impl : public IPayrollService {
public:
    double calcSalary(
        EmployeeId employeeId, double workHours) override {
        // v2の計算ルールで実装
        double base = fetchBaseSalary(employeeId);
        double rate = (workHours > 160.0) ? 3000.0 : 0.0;
        double overtime = (workHours - 160.0) * rate;
        return base + overtime;
    }
private:
    double fetchBaseSalary(EmployeeId employeeId) {
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
「責任が明確な設計」だから変更が局所化されています——
この感覚、うまく伝わっているでしょうか。

---

**次の変化：明細をExcelファイルでGitHubに登録する要求**

2.3のヒアリングで「来年度からExcel出力の要望が上がっています」という言葉がありました。
その変化が実際に来たとします。

> 「給与明細をPDFではなく、Excelファイルとして社内GitHubリポジトリに登録してほしい。」

この要求に応えるには、`ExcelGitHubServiceImpl` という新しい実装クラスを追加します。

```cpp
// ExcelGitHubServiceImpl
// 責任：給与明細をExcelファイルとしてGitHubに登録する
class ExcelGitHubServiceImpl : public IPaySlipOutputService {
public:
    std::string output(
        EmployeeId employeeId, double amount) override {
        // Excelファイルを生成し、GitHubリポジトリに登録する
        std::string fileName = "slip_"
            + std::to_string(employeeId.value)
            + "_" + std::to_string((int)amount)
            + ".xlsx";
        // pushToGitHub(fileName); // GitHubへの登録処理
        return fileName;
    }
};
```

BatchApplicationでの差し替えは、たった1行だけです。

```cpp
void BatchApplication::run(int year, int month) {
    PayrollServiceImpl     payroll;
    LaborMgmtServiceImpl   labor;
    ExcelGitHubServiceImpl pdf;   // ← ここだけ変わる
    PayrollFacade facade(&payroll, &labor, &pdf);
    MonthlyBatch  batch(&facade);
    batch.run(year, month);
}
```

インターフェース名 `IPaySlipOutputService` は変わりません。
「給与明細を出力する」という責任の名前は、PDFでもExcelでもGitHubでも同じです。
2.3で決めた「ビジネス責任で命名する」原則が、ここで実証されました。

---

**型変更リスクへの耐久テスト：社員IDがstring型に変わった場合**

2.3のヒアリングで「社員IDが将来的にstring型に変わる可能性がある」ことが判明していました。
第3段階のインターフェース定義時点で `EmployeeId` を導入していたため、
**この変化が来ても修正は1箇所だけ**です。

```cpp
// EmployeeId の value フィールドの型を int → string に変えるだけ
struct EmployeeId {
    std::string value;  // ← ここだけを変える
    explicit EmployeeId(const std::string& v) : value(v) {}
};
```

3つのインターフェースのシグネチャを確認します。

```cpp
// インターフェースのシグネチャは変わらない
class IPayrollService {
    virtual double calcSalary(
        EmployeeId employeeId, double workHours) = 0;
    //  ↑ EmployeeId のまま。変更不要。
};
class ILaborMgmtService {
    virtual double getWorkHours(
        EmployeeId employeeId, int year, int month) = 0;
    //  ↑ EmployeeId のまま。変更不要。
};
class IPaySlipOutputService {
    virtual std::string output(
        EmployeeId employeeId, double amount) = 0;
    //  ↑ EmployeeId のまま。変更不要。
};
```

| 変更のシナリオ | 変わる場所 | 変わらない場所 |
|---|---|---|
| 社員IDの型が `int` → `string` | `EmployeeId::value` の型のみ | 3つのインターフェース・全クラスのシグネチャ |

2.3のヒアリングで判明したリスクを「インターフェース定義のタイミング」に活かした結果、
型変更の影響が `EmployeeId` の中だけに封じ込められています。

> **ヒアリングで得た知識は、設計の決断に変換して初めて価値を持ちます。**
> ステップ2で「変わりうる」と判明した情報を、ステップ5の設計に閉じたループで返す——
> この往復がなければ、ヒアリングは単なる記録で終わります。

### 使う場面・使わない場面

**使いすぎた例**

```cpp
// ❌ やりすぎの例
// 変わらない1行の計算にFacadeとインターフェースを作る
class ITaxCalcService {
public:
    virtual ~ITaxCalcService() {}
    virtual double calculate(double amount) = 0;
};
class TaxCalcServiceImpl : public ITaxCalcService {
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

### 解決後のコード（全体）

**変更に強い設計の完成形**

```cpp
// ── 値オブジェクト ──────────────────────────────────

// EmployeeId：社員IDの型を封じ込める値オブジェクト
// int → string に変わっても、この1箇所だけを変えればよい
struct EmployeeId {
    int value;
    explicit EmployeeId(int v) : value(v) {}
};

// ── インターフェース定義 ─────────────────────────

class IPayrollService {
public:
    virtual ~IPayrollService() {}
    virtual double calcSalary(
        EmployeeId employeeId, double workHours) = 0;
};

class ILaborMgmtService {
public:
    virtual ~ILaborMgmtService() {}
    virtual double getWorkHours(
        EmployeeId employeeId, int year, int month) = 0;
};

// ビジネス責任で命名：「給与明細を出力する」責任
// PDF か Excel かは名前に現れない
class IPaySlipOutputService {
public:
    virtual ~IPaySlipOutputService() {}
    virtual std::string output(
        EmployeeId employeeId, double amount) = 0;
};

class IPayrollFacade {
public:
    virtual ~IPayrollFacade() {}
    virtual void process(int year, int month) = 0;
};

// ── 実装クラス ─────────────────────────────────────

class PayrollServiceImpl : public IPayrollService {
public:
    double calcSalary(
        EmployeeId employeeId, double workHours) override {
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
        EmployeeId employeeId, int year, int month) override {
        return 172.5;
    }
};

class PdfServiceImpl : public IPaySlipOutputService {
public:
    std::string output(
        EmployeeId employeeId, double amount) override {
        return "slip_"
            + std::to_string(employeeId.value)
            + "_" + std::to_string((int)amount)
            + ".pdf";
    }
};

// ── Facade ─────────────────────────────────────────

class PayrollFacade : public IPayrollFacade {
public:
    PayrollFacade(
        IPayrollService*      payroll,
        ILaborMgmtService*    labor,
        IPaySlipOutputService* pdf
    ) : payroll_(payroll), labor_(labor), pdf_(pdf) {}

    void process(int year, int month) override {
        EmployeeId employeeId(1001);
        double hours = labor_->getWorkHours(
            employeeId, year, month
        );
        double amount = payroll_->calcSalary(
            employeeId, hours
        );
        std::string slip = pdf_->output(
            employeeId, amount
        );
        saveResult(year, month, amount, slip);
    }
private:
    IPayrollService*      payroll_;
    ILaborMgmtService*    labor_;
    IPaySlipOutputService* pdf_;
};

// ── MonthlyBatch ───────────────────────────────────

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

// ── 組み立てと起動 ─────────────────────────────────

class BatchApplication {
public:
    void run(int year, int month) {
        PayrollServiceImpl    payroll;
        LaborMgmtServiceImpl  labor;
        PdfServiceImpl        pdf;
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

    EXPECT_TRUE(stub.called);
    // EXPECT_EQ(期待値, 実際の値)：等しければテスト通過という検証
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
| 明細をExcel出力に切り替える | `ExcelServiceImpl` を追加し `BatchApplication` で差し替え | 他の全クラス |
| 月次処理の業務フローが変わる | `MonthlyBatch` | 各サービス実装 |
| 社員IDの型が `int` → `string` に変わる | `EmployeeId::value` の型のみ | 3インターフェース・全クラスのシグネチャ変わらない |

「変わる理由が異なるクラス」が「別の場所にいる」。
これが変更に強い設計の正体です。

間違えても大丈夫です。設計は一度決めたら終わりではなく、
状況が変わればまた考え直せばいい、という軽さで向き合ってほしいと思います。

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

ステップ1で感じた「なぜ給与処理の本体が、PayrollServiceのAPI形式まで知っているんだ？」
という違和感は完全に消えました。
新しい通知手段やサービスのバージョンが変わっても、変更は1クラスに収まります。

---

## 整理

### 8ステップとこの章でやったこと

| ステップ | この章でやったこと |
|---|---|
| ステップ0 | システムの構成と現状のコードを共有し、設計のレンズ（問い）をセットアップした |
| ステップ1 | 各クラスの責任を定義し、責任チェックでMonthlyBatchに責任外の知識が混在していることを確認した |
| ステップ2 | 関係者ヒアリングで変動/不変の根拠を固め、表で確定させた |
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
| `PdfServiceImpl` | 給与明細を出力する | 出力仕様が変わるとき |

「変わる理由が1つ」のクラスだけで構成されている。
このプロセスを回した結果にたどり着いた構造こそが **Facadeパターン** です。

設計に絶対の正解はありません。ただ「各クラスの責任は何か」「変わる理由は1つか」を問い続けることが、変更に強いコードへの入り口になります。

---

## 振り返り：第0章の3つの哲学はどう適用されたか

改めて、ここまで導き出してきた「最終的な設計」を、第0章でお話しした「3つの哲学」と照らし合わせてみましょう。

### 哲学1「変わるものをカプセル化せよ」の現れ

**具体化された場所：** `MonthlyBatch` から追い出された「各APIの仕様や呼び方」の知識

外部サービスの都合で変わりやすい「APIのバージョンや引数の形式」を、`PayrollFacade` と各インターフェースの裏側に分離（カプセル化）しました。「外部サービスの都合が変わっただけで、システムの中核が道連れになる」という負の連鎖を断ち切った部分です。

### 哲学2「実装ではなくインターフェースに対してプログラムせよ」の現れ

**具体化された場所：** `MonthlyBatch` が `IPayrollFacade` のみを知り、`PayrollFacade` が各インターフェースのみを知っている依存関係

`MonthlyBatch` は具体クラスではなく契約（`IPayrollFacade`）にのみ依存します。相手のAPI仕様がどれほど変わろうとも、影響はインターフェースの裏側に封じ込められます。矢印の数の変化（3本→1本）が責任の整理の成果を物語っています。

### 哲学3「継承よりコンポジションを優先せよ」の現れ

**具体化された場所：** `PayrollFacade` が3つのサービスインターフェースを「部品として持つ（`payroll_`・`labor_`・`pdf_`）」構造

もし `PayrollFacade` が各サービスを継承して実装していたら、サービスの変更が `PayrollFacade` に直接波及します。「部品として持つ」ことで、差し替えは外からの注入だけで済み、`PayrollFacade` 自身には一切触れません。

---


---

## パターン解説：Facadeパターン

### パターンの骨格

Facadeパターンは、複数のサブシステムへの入り口を1つに集約します。

```mermaid
classDiagram
    class Client {
        +operation()
    }
    class Facade {
        +unifiedOperation()
    }
    class SubsystemA {
        +doA()
    }
    class SubsystemB {
        +doB()
    }
    class SubsystemC {
        +doC()
    }
    Client --> Facade : 1つの窓口のみ呼ぶ
    Facade --> SubsystemA
    Facade --> SubsystemB
    Facade --> SubsystemC
    note for Client "SubsystemA/B/Cの存在を知らない"
    note for Facade "呼び出し順序・依存関係をここに封じる"
```

**Facade** は複数のSubsystemを束ね、1つの窓口を提供します。呼び出し順序・エラーハンドリング・依存関係をここに封じます。**Client** はFacadeの1メソッドだけを呼びます。Subsystemの数・種類・順序を知りません。**Subsystem** はそれぞれ独立した責任を持ちます。FacadeやClientの存在を知りません。

### この章の実装との対応

```mermaid
classDiagram
    class MonthlyBatch {
        +run()
    }
    class PayrollFacade {
        -attendance : IAttendanceService
        -tax : ITaxService
        -insurance : IInsuranceService
        -payment : IPaymentService
        +processPayroll(employeeId int)
    }
    class IAttendanceService {
        <<interface>>
        +calculate(id int) AttendanceResult
    }
    class ITaxService {
        <<interface>>
        +calculate(salary int) TaxResult
    }
    class IInsuranceService {
        <<interface>>
        +calculate(salary int) InsuranceResult
    }
    class IPaymentService {
        <<interface>>
        +transfer(id int, amount int)
    }
    MonthlyBatch --> PayrollFacade : processPayroll()を呼ぶだけ
    PayrollFacade --> IAttendanceService
    PayrollFacade --> ITaxService
    PayrollFacade --> IInsuranceService
    PayrollFacade --> IPaymentService
    note for MonthlyBatch "4サービスの存在を知らない"
```

`MonthlyBatch` は `processPayroll()` を呼ぶだけです。勤怠・税務・保険・振込みの4サービスをどの順序でどう組み合わせるかは `PayrollFacade` の内部知識であり外に漏れません。サービスが追加・変更されても `MonthlyBatch` は一切変わりません。

### どんな構造問題を解くか

「複数のサービスを決まった手順で使う知識」が、使う側に漏れ出している状態がFacadeパターンの出番です。

この章では、勤怠・税務・保険・振込みという4サービスを正しい順序で呼び出す知識が `MonthlyBatch` に直接埋まっていました。「どのサービスを使うか」「どの順番か」「どの結果を次に渡すか」——これらはすべて `MonthlyBatch` が知る必要のない知識です。

FacadeパターンはそれらをFacadeに集め、Clientを「呼び出し元」だけに専念させます。Subsystemの構成が変わっても、ClientはFacadeの窓口が変わらない限り影響を受けません。

### 使いどころと限界

**使いどころ：**「複数の依存先を決まった手順で組み合わせる処理」をひとまとめにしたい場合です。呼び出し元が「複数の具体的なサービスの存在」を知っていること自体が問題の兆候です。

**限界：** Facadeは「窓口」であり「制御の主体」ではありません。処理の途中結果を使って呼び出し元が判断を変える必要がある場合、Facadeに全部隠すと呼び出し元が制御を失います。依存しているサービスが1つだけの場合はFacadeを挟む意味がありません。