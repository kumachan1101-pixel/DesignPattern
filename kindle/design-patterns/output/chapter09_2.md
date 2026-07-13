## 第9章 変わるルールと状態の連鎖 ―― Strategy × State パターン

―― 思考の型：複雑なビジネスルールと状態遷移が絡み合う場所をどう解くか

### この章の核心

**チケットの優先度ルールと状態遷移が同じ管理処理に集まっていると、VIPルールの追加でも状態追加でも同じ場所全体を修正・確認する必要が生じる。こういう問題は、「判定ルール」と「状態ごとの振る舞い」という別々の変更理由が同じ場所に混在しているシステムで起きている。**

第9章からは本書の第二部です。第一部では、章ごとに主となる一つの変更課題へ焦点を当て、対応する構造を一つずつ学びました。第二部では、変更の決定者や頻度が異なる複数の課題が同じシステムに存在する場合を扱います。同じ7つのフェーズで問題を分析しますが、一つの構造だけでは変更影響を十分に分けられないとき、複数の構造を組み合わせます。「名前を先に置いて設計する」のではなく、「変更理由の種類を分析して必要な境界を選ぶ」という順序は変わりません。

### この章を読むと得られること

* **得られること1：** ビジネスルールの切り替えと状態ごとの振る舞いが混在している箇所を識別できるようになる

* **得られること2：** 接続点で状態遷移と優先度ルールの知識がどこへ漏れているかを調べ、変更の痛みが生まれる理由を判断できるようになる

* **得られること3：** 複合的な変化に対して、複数の解決手段を組み合わせてどのように局所化できるかを説明できるようになる

* **得られること4：** 現場の複雑な条件分岐を、if文の羅列からオブジェクトの構成へと変換する視点

## 🔵 フェーズ1：現状把握 ―― 仕様を整理し、システムと紐付ける

サポートチケット管理システムが何を入力として受け取り、どの処理で加工し、何を出力するのかを整理します。

### 1-1：このシステムの仕様

このシステムは、社内のITヘルプデスクで使われている「サポートチケット管理システム」です。社員から届くPCやネットワークのトラブル報告をチケットとして登録し、ヘルプデスク担当者がそれを解決するまでの過程を管理しています。

この章で扱う現状仕様は、次の範囲です。

| 仕様項目 | この章で扱う値 | 具体例 | 何に使うか |
|---|---|---|---|
| チケット | 問い合わせ内容と現在状態 | TCK001 が Open | 状態に応じて許可される操作を判定する |
| ユーザー種別 | standard / premium / enterprise | USR001 は enterprise | 優先度計算に使う |
| 操作 | 受付・対応開始・解決など | 担当者アサイン、解決 | 状態遷移と優先度更新のきっかけになる |
| 出力 | 更新後状態と優先度 | InProgress、高優先度 | 操作結果としてチケット状態を照合する |

ここで確認する対象は、どの入力で状態と優先度がどう変わるかです。

現在状態や優先度は、利用者が毎回入力する値ではありません。チケットIDから保存済みのチケットを取得し、その状態とユーザー種別を使って操作可否と優先度を決めます。

**仕様整理図：保存データとアクセス関係**

```mermaid
flowchart LR
    U["担当者<br>チケットIDと操作を指定"] --> S["TicketService<br>状態更新を進行"]
    S --> T["TicketRepository<br>現在状態・担当者・履歴"]
    S --> P["PriorityPolicy<br>ユーザー種別・SLA基準"]
    T --> S
    P --> S
    S --> R["実行結果<br>状態更新・優先度表示"]

    classDef actor fill:#f8fafc,stroke:#64748b,color:#111827;
    classDef data fill:#ecfeff,stroke:#0891b2,color:#111827;
    classDef process fill:#fff7ed,stroke:#ea580c,color:#111827;
    class U actor;
    class T,P data;
    class S,R process;
```

上の文章と表で仕様を一通り確認したので、まず正常にチケットを更新できる場合の入力・判定・加工・出力の流れとして整理します。

**仕様整理図：正常系の入力・判定・加工・出力**

```mermaid
flowchart LR
    A[/チケットID<br>TCK001/]:::input --> B{チケットは存在するか}:::decision
    C[(保存済みチケット<br>現在状態)]:::data --> D{操作は可能か}:::decision
    E[/ユーザー種別/]:::input --> F[優先度ルールを選ぶ]:::process
    G[/操作<br>担当者アサイン・解決など/]:::input --> D
    B -->|Yes| D
    D -->|Yes| H[状態ごとの処理を実行]:::process
    F --> I[優先度を計算]:::process
    H --> J([正常出力<br>状態更新・優先度表示]):::normal
    I --> J

    classDef data fill:#ecfeff,stroke:#0891b2,color:#111827;
    classDef input fill:#e7f0ff,stroke:#2563eb,color:#111827;
    classDef process fill:#fff7ed,stroke:#ea580c,color:#111827;
    classDef decision fill:#fef9c3,stroke:#ca8a04,color:#111827;
    classDef normal fill:#dcfce7,stroke:#16a34a,color:#111827;
```

この図から読み取ることは、次の3点です。

- チケット処理には、優先度を決める流れと状態を進める流れが同時に含まれる。
- 優先度判定条件は優先度に、状態操作はチケット状態に主に影響する。
- 正常系では、保存済みチケットの状態を更新し、ユーザー種別から計算した優先度を表示する。

**エラー条件**

正常系の状態更新へ進めない入力は、次のように分けて扱います。

| エラー条件 | どこで分かるか | 出力 | 保存・通知などの副作用 |
|---|---|---|---|
| チケットIDが存在しない | チケット取得時 | チケットIDエラー | 状態更新なし |
| 現在状態では操作できない | 状態と操作の組み合わせ確認時 | 操作不可エラー | 状態更新なし |

現状のシステムは、チケットの状態遷移と、ユーザー種別に応じた優先度設定という業務ルールを、一箇所にまとめて管理しています。

**チケットの状態と実行できる操作**

チケットに「状態」を持たせるのは、「今このチケットに対して何をしてよいか」を制御するためです。担当者が未アサインのチケットを勝手に解決済みにしてしまう、といったミスを防ぐために、この章のシステムでは状態ごとに許可される操作を絞っています。

| 状態 | 状態名（英語） | 実行できる操作 |
|---|---|---|
| 受付中 | Open | 担当者アサイン |
| 対応中 | In Progress | 解決・エスカレーション |
| 解決済み | Resolved | 再受付 |

基本の流れは「Open → InProgress → Resolved」の一方向です。解決済みチケットを再度受け付ける「Resolved → Open」という逆流もあります。「一度解決したのにまた同じ問題が起きた」というケースに対応するための遷移です。

**優先度ルール**

ユーザー種別によって優先度を変えるのは、対応時間の保証（SLA）に基づくものです。プレミアムユーザーには一次回答までの時間の約束があり、その約束を優先度へ反映します。エスカレーション時にも優先度を適用し、急ぎの対応が必要になった時点で担当者を動かせるようにします。

| ユーザー種別 | 設定される優先度 | 適用タイミング |
|---|---|---|
| 一般ユーザー | 標準（Normal） | チケット登録時・再受付時 |
| プレミアムユーザー | 高優先度（High） | チケット登録時・再受付時・エスカレーション時 |

このルールは現時点では2区分です。SLAの内容はビジネス上の契約によって変わるため、区分は今後増減する場合があります。

**このシステムの関係者**

どの知識がどの業務機能に属するかを把握しておくのは、設計判断において重要な手がかりになります。「どの業務機能に属するか」が違えば、それは別々に管理できるようにしておくべき知識かもしれないからです。

**この仕様を決める業務機能**
| 業務機能 | この章の仕様で決めていること |
|---|---|
| 運用・状態管理 | 状態の追加・変更・遷移条件 |
| 品質・評価管理 | ユーザー種別と優先度の基準 |

後のフェーズで変更要求を扱うとき、どの業務機能の知識なのかを確認するための名前として使います。

### 1-2：動作例テーブル

このシステムがどのように動くかを、代表的な操作例で示します。クラス図やコードを読む前に、「何をするシステムか」をここで確認してください。

| チケット種別 | 操作 | 優先度ルール | 状態遷移 |
| --- | --- | --- | --- |
| 新規チケット | 一般ユーザーが登録 | 標準優先度（Normal） | → 受付中（Open） |
| 新規チケット | プレミアムユーザーが登録 | 高優先度（High） | → 受付中（Open） |
| 受付中チケット | 担当者アサイン | ルール適用なし | → 対応中（InProgress）に遷移 |
| 対応中チケット | 担当者が解決 | ルール適用なし | → 解決済み（Resolved）に遷移 |
| 解決済みチケット | 一般ユーザーが再オープン | 標準優先度（Normal） | → 再受付中（Open）に遷移 |
| 対応中チケット | プレミアムユーザーがエスカレーション | 高優先度（High） | 緊急対応（担当者を招集） |

この6つの動作例が、このシステムが満たす必要がある動作の基準です。後でステップを比較するときも、「どのステップもこれと同じ動作を実現する」という前提で読んでください。


### 1-2b：状態遷移表

このシステムで管理する状態と、各状態から可能な遷移を整理します。これは、後のフェーズで状態ごとの振る舞いを確認するときの全体像です。

| 現在の状態 | アサイン | 解決 | 再受付 |
| --- | --- | --- | --- |
| Open（受付中） | → InProgress（対応中） | —— | —— |
| InProgress（対応中） | —— | → Resolved（解決済み） | —— |
| Resolved（解決済み） | —— | —— | → Open（再受付中） |

```mermaid
stateDiagram-v2
    [*] --> Open : 登録
    Open --> InProgress : アサイン
    InProgress --> Resolved : 解決
    Resolved --> Open : 再受付
```

「Open → InProgress → Resolved」という一方向の流れが基本ですが、「解決済み → 再受付」という逆流があります。状態が増えるほど、このマトリクスの「空欄（——）」の管理が複雑になります。

> **📌 変更要求をどこまで実装するか**
> 1-5節では「保留中」「ベンダー確認中」などの追加が予定されています。フェーズ3では、その代表として法人ユーザー向けSLAルールと `Pending`（保留中）を変更途中コードへ追加しました。フェーズ6の各案とフェーズ7の最終コードでも、この2要素を落とさず追います。`VendorWaiting`（ベンダー確認中）は、同じ `ITicketPhase` 契約へ追加する次の変更シナリオとして7-4で確認します。

次は、この仕様を担うクラスの顔ぶれと責任を確認します。

---

### 1-3：登場クラスとクラス構成図

フェーズ1の現状コード構造に登場するクラスを先に確認します。

| クラス名 | 役割 | 担当する仕様 |
|---|---|---|
| `TicketManager` | チケット状態の更新を進める | 状態管理、操作可否、優先度計算の呼び出し |
| `PriorityCalculator` | ユーザー種別から優先度を計算する | 優先度ルール |
| `UserDatabase` | ユーザー情報の管理 | ユーザーIDからユーザー名・ティアを検索する |

各クラスの責任を把握したところで、クラス間の関係を図で確認します。

```mermaid
classDiagram
    class TicketManager {
        -calc: PriorityCalculator
        -db: UserDatabase
        +updateStatus(userId, status)
    }
    class PriorityCalculator {
        +calculate(userType) string
    }
    class UserDatabase {
        +exists(id) bool
        +get(id) UserInfo
    }
    TicketManager *-- PriorityCalculator : 保持
    TicketManager *-- UserDatabase : 保持
```

**クラス図に出てくる主なメンバーと操作**

| クラス | メンバー・操作 | 何ができるか |
|---|---|---|
| `TicketManager` | `calc` / `db` | 優先度計算とユーザー検索を行うクラスを保持する |
| `TicketManager` | `updateStatus()` | ユーザーIDと状態を受け取り、状態更新と優先度計算を進める |
| `PriorityCalculator` | `calculate()` | ユーザー種別から優先度を返す |
| `UserDatabase` | `exists()` / `get()` | ユーザーIDの存在確認と、氏名・ティアの取得を行う |


`TicketManager` クラスが、チケットの状態管理と、その遷移に伴う優先度計算という異なる責務を抱えています。

---

### 1-4：実装コード（現状）

#### コードを読む前の責任・境界・C++記法

| 対象 | 呼び出しと内部処理 | 戻り値・副作用 | 掲載上の表現 |
|---|---|---|---|
| Ticket DB | チケットID・利用者IDで検索する | 現在状態・利用者属性 | `std::map`でDBを代替する |
| 優先度ルール | 属性・条件から優先度を計算する | 優先度値 | Strategyの戻り値として表す |
| 状態 | 操作を受け遷移可否を決める | 次状態・ログ | Stateオブジェクトへ委譲する |
| `vector` | イベントログを順番に保持する | 追記・一覧表示 | 永続監査ログのメモリ代替 |

実チケットDBと通知は省略しますが、誰がどの操作を行い、どの状態へ変わり、どの優先度になったかは値として残します。

システムの現状の実装を確認します。コードを役割ごとに分けて読んでいきます。

**UserInfo / UserDatabase / PriorityCalculator クラス**

このシステムには以下の3件のユーザーデータがあらかじめ登録されています。

| ユーザーID | 氏名 | サポートティア |
|---|---|---|
| USR001 | 田中 一郎 | enterprise（最優先） |
| USR002 | 佐藤 花子 | premium（優先） |
| USR003 | 鈴木 次郎 | standard（通常） |

ティアによって対応優先度と状態遷移の振る舞いが変わります。コードを読む前にこの対応を把握しておくと、動作結果が追いやすくなります。

この章では、画面表示・実際の通知送信・時計の実測を省略し、状態更新と優先度の計算結果を中心に確認します。実システムなら通知や時刻取得は境界へ渡しますが、本章の論点は「状態遷移とルール判定という2つの変化軸を分ける構造」です。SLAの残り時間の判定は `SlaTimer`、担当者割当の発火は `AssignmentEvent` にあたる境界の向こう側として扱い、掲載コードでは優先度ルールの結果と状態遷移の呼び出しだけを追います。`print` はこれら境界の先に閉じ、SLA期限そのものの時刻計算や通知配信の中身は扱いません。

```cpp
#include <iostream>
#include <string>
#include <map>

using namespace std;

// ユーザー情報
struct UserInfo {
    string name; // 氏名
    string tier; // "standard", "premium", "enterprise"
};

// ユーザーデータベース
class UserDatabase {
    map<string, UserInfo> records;
public:
    UserDatabase() {
        records["USR001"] = {"田中 一郎", "enterprise"};
        records["USR002"] = {"佐藤 花子", "premium"};
        records["USR003"] = {"鈴木 次郎", "standard"};
    }
    bool exists(const string& id) const {
        return records.count(id) > 0;
    }
    UserInfo get(const string& id) const {
        return records.at(id);
    }
    void save(const string& id, const UserInfo& info) {
        records[id] = info;           // 実行中のユーザー表へ追加
    }
};

// 優先度ルール（変わる可能性がある）
class PriorityCalculator {
public:
    string calculate(string userType) {
        if (userType == "premium") return "High"; // ← ルール判定を直書き
        if (userType == "enterprise") return "High";
        return "Normal";
    }
};
```

**TicketManager クラス**

```cpp
// チケット管理（優先度計算と状態更新を行う）
class TicketManager {
    PriorityCalculator calc;
    UserDatabase db;
public:
    void updateStatus(string userId, string status) {
        if (!db.exists(userId)) {             // ← DBにないIDはエラー
            cout << "エラー: ユーザーID "
                 << userId << " は存在しません。" << endl;
            return;
        }
        UserInfo user = db.get(userId);
        string priority = calc.calculate(user.tier);
        if (status == "Open") {
            cout << "チケット受付中。優先度: " << priority << endl;
        } else if (status == "InProgress" && priority == "High") {
            cout << "緊急対応中。担当者を招集します。" << endl;
        }
    }
};
```

**main 関数**

```cpp
int main() {
    TicketManager manager;

    // 行1: 鈴木（standard）が新規チケットを登録（標準優先度 → 受付中）
    manager.updateStatus("USR003", "Open");

    // 行2: 佐藤（premium）が新規チケットを登録（高優先度 → 受付中）
    manager.updateStatus("USR002", "Open");

    // 行6: 佐藤（premium）がエスカレーション（高優先度 → 緊急対応）
    manager.updateStatus("USR002", "InProgress");

    // 存在しないユーザーIDを渡した場合
    manager.updateStatus("USR999", "Open");

    return 0;
}
```

実行対象コード：1-4の現状コード
対応する動作例：1-2の動作例テーブル
確認したいこと：入力、加工、出力が仕様どおりに対応していること

実行結果：

```
チケット受付中。優先度: Normal
チケット受付中。優先度: High
緊急対応中。担当者を招集します。
エラー: ユーザーID USR999 は存在しません。
```

> [!NOTE]
> 上記はフェーズ1の現状コードで確認できる代表的な3ケースです（行1・行2・行6）。行3（アサイン）・行4（解決）・行5（再受付）の状態遷移は、フェーズ1の現状コードでは `updateStatus()` に遷移のロジックが含まれておらず、出力が生じません。行6（エスカレーション）はフェーズ1の現状コードで出力されますが、フェーズ7では行1〜5の基本フローが実装されます。

このコードを見ると、`TicketManager` が優先度の計算ルール（`PriorityCalculator`）と、状態に応じたアクション（if-else）の両方を直接知っていることが分かります。

---

> **手元で動かすには**
> このコードは1つの `.cpp` に貼り付けて、そのままコンパイル・実行できます（例：`g++ chapter09.cpp -o app && ./app`）。`main()` は自由に組み替えて構いません。`manager.updateStatus("USR002", "Open");` の呼び出しを増減させれば、ユーザー種別（standard/premium/enterprise）ごとの優先度判定と状態遷移がその場の実行結果に表れます。新しいユーザーを試すときは `UserDatabase` の登録へ `records["USR010"] = {"高橋 三郎", "enterprise"};` を足す（または `save()` を呼ぶ）と、そのユーザーでも同じ処理を実行できます。データはプロセス実行中だけ有効で、終了すると消えます。

### 1-5：変更要求

【運用チームと品質管理チームからの要求】
ある月曜日の朝、ヘルプデスクのマネージャーからチャットが届きました。

「お疲れ様。現在対応しているチケットシステムなんだけど、今度から『SLA（サービスレベル合意）』を厳格に運用することになったんだ。特に、重要度が高いチケットが『Open』状態のまま長時間放置されるのは何としても避けたい。それと同時に、これまではチケットのステータスが3種類しかなかったけれど、今後は『保留中』や『ベンダー確認中』といった状態も増える予定だ。この新しいルールと状態遷移の複雑さに、今のシステムで対応できるかな？」

今回の変更要求は「重要度に応じた優先度判断ルールの追加」と「状態遷移の増加」という、二つの大きな柱があるようです。

**仕様変更の内容**

変更要求を受けて、現在の仕様がどう変わるかを整理します。

| 項目 | 変更前 | 変更後 |
|---|---|---|
| チケット状態の種類 | 3種類（Open / InProgress / Resolved） | 保留中・ベンダー確認中など新状態を追加予定 |
| 優先度ルール | 一般→Normal、プレミアム→High の固定判定 | SLA基準に基づく判定ルール（四半期ごとに改定） |
| SLA期限 | 未対応 | 受付から一定時間で期限超過を判定し優先度へ反映 |
| 担当者割当 | 未対応 | アサイン操作を割当イベントとして扱い状態を進める |
| 再オープン | Resolved→Open のみ | 再オープン時も優先度ルールを再適用して評価する |

「状態が増える」変更と「優先度ルールが変わる」変更は、今後も別のタイミングで届く可能性があります。この2つは独立した軸として扱う必要があります。

**複雑度ストレス条件**

今回の要求には、状態とルールが同じきっかけで同時に動く場面が混ざっています。2軸以上の変化が重なっても、軸を分ければ扱えるかをこの章で確認します。

| 追加する複雑さ | 具体例 | この章で見ること |
|---|---|---|
| SLAタイマー | Open のまま期限超過で優先度をHighへ引き上げる | 期限判定を優先度ルール側へ寄せられるか |
| 担当者割当イベント | アサイン操作でOpen→InProgressへ進める | 割当という契機と状態遷移を分けて扱えるか |
| 再オープン | Resolved→Open で再度ルール評価する | 逆流時も状態軸とルール軸が独立に動くか |
| 状態とルールの同時変化 | エスカレーションで状態進行と優先度上げが同時 | 同時に動いても2軸へ分けて追えるか |

**変更前後の入力・判定・加工・出力差分**

1-1の現状仕様を退避し、変更要求を当てた後の仕様と同じ粒度で並べます。以降の分析では、この差分を追います。

| 要素 | 変更前（1-1の現状仕様） | 変更後（今回の要求） | 差分として追うもの |
|---|---|---|---|
| 入力 | チケットID、ユーザー種別、操作、保存済みの現在状態 | チケットID、ユーザー種別、操作、保存済みの現在状態、SLA基準、新状態、割当・再オープン契機 | 優先度ルールと状態種類、契機が増える |
| 判定 | 状態ごとの操作可否、固定優先度判定 | 新状態を含む操作可否、SLA期限とSLA基準の優先度判定 | 状態判定と優先度判定が別々に変わる |
| 加工 | 状態更新と優先度計算 | 割当・再オープンによる新状態への遷移とSLA優先度計算 | 二つの加工軸を分けて追う |
| 出力 | 更新後状態と優先度 | 新状態を含む更新後状態とSLA優先度 | 出力状態と優先度が増える |

**変更後の入力・加工・出力**

変更後の仕様を、1-1と同じ粒度で、正常系の入力・判定・加工・出力として確認します。1-1の図との差分は、保存済みの現在状態に保留中・ベンダー確認中などが加わること、「優先度ルールを選ぶ」の選択肢が固定の2区分からSLA基準の判定ルールに変わること、そして割当・再オープンといった契機とSLA期限の確認が入ることです。流れの形そのものは変わりません。

```mermaid
flowchart LR
    A[/チケットID<br>TCK001/]:::input --> B{チケットは存在するか}:::decision
    C[(保存済みチケット<br>Open・InProgress・Resolved<br>＋保留中・ベンダー確認中など)]:::data --> D{操作は可能か}:::decision
    E[/ユーザー種別/]:::input --> F[優先度ルールを選ぶ<br>SLA期限・基準を反映]:::process
    G[/操作・契機<br>割当・解決・再オープン/]:::input --> D
    B -->|Yes| D
    D -->|Yes| H[状態ごとの処理を実行]:::process
    F --> I[優先度を計算]:::process
    H --> J([正常出力<br>状態更新・優先度表示]):::normal
    I --> J

    classDef data fill:#ecfeff,stroke:#0891b2,color:#111827;
    classDef input fill:#e7f0ff,stroke:#2563eb,color:#111827;
    classDef process fill:#fff7ed,stroke:#ea580c,color:#111827;
    classDef decision fill:#fef9c3,stroke:#ca8a04,color:#111827;
    classDef normal fill:#dcfce7,stroke:#16a34a,color:#111827;
```

この図から読み取ることは、次の3点です。

- 変更の1つ目の柱（状態の増加・割当・再オープン）は入力の「操作・契機」と「操作は可能か」「状態ごとの処理を実行」に、2つ目の柱（優先度ルールとSLA期限の改定）は「優先度ルールを選ぶ」「優先度を計算」に、それぞれ別の箱に現れる。
- エスカレーションのように状態進行と優先度上げが同時に起きても、図の上では別々の箱を通る別の流れであり、独立した軸として扱う根拠になる。
- 出力とエラーの形は変わらない。

変更後も、失敗条件は正常系図へ混ぜずに別で確認します。

| エラー条件 | どこで分かるか | 出力 | 保存・通知などの副作用 |
|---|---|---|---|
| チケットIDが存在しない | チケット取得時 | チケットIDエラー | 状態更新なし |
| 現在状態では操作できない | 状態と操作の組み合わせ確認時 | 操作不可エラー | 状態更新なし |
| SLA期限を超過している | 割当・再オープン時のSLA確認時 | 期限超過を優先度へ反映 | 状態更新は継続、優先度がHighへ |

2つの柱が実際のコードでどこに現れるかは、フェーズ3で変更を試すコードと、フェーズ7の最終コード・実行結果で追います。

---

## 🟣 フェーズ2：仮説立案 ―― 何が変わるかを観察し、ヒアリングで裏付ける
フェーズ1で、`TicketManager` がチケットの状態遷移と優先度計算ロジックを直接保持している現状を把握しました。届いた変更要求を踏まえ、この設計における変わる見込みと当面安定の前提を整理します。

### 2-1：変わりそうな仕様の見当をつける

ここで作る一覧は、思いつきで「変わりそう」と感じたものを並べる表ではありません。フェーズ1で確認した仕様・動作例・クラス図を材料に、次の順で候補を絞ります。

1. 仕様図と動作例から、入力・判定・加工・出力のうち条件や値が変わりそうな箇所を拾う。
2. その箇所が、1-3のどのクラス・メソッドに書かれているかを対応づける。
3. その仕様が、どんな理由で、何をきっかけに、どのくらいの頻度で変わりそうかを仮説として書く。
4. 逆に、当面変えない前提にできる処理の骨格も分けておく。

この手順で見ると、「チケットを更新する」という大きな処理全体ではなく、その中のどの優先度ルール・状態遷移・操作条件が変更候補なのかを読者自身で追えるようになります。

フェーズ2では、フェーズ1で見た仕様のうち、どの状態遷移・優先度ルール・操作条件が変わりそうかを見当づけます。責務の配置は、変更要求を当てた後の痛みと合わせて確認します。

| 仕様候補 | 仕様上の場所 | フェーズ1の現状コードでの場所 | 見立て |
|---|---|---|---|
| 優先度計算ルール | 判定、状態更新前の評価 | `TicketManager.updateStatus()` | 四半期ごとに評価基準が変わる可能性があるため、今回見る |
| SLA期限による優先度引き上げ | 判定、優先度評価 | `TicketManager.updateStatus()` | 期限超過の扱いが契約で変わるため、優先度軸として今回見る |
| Open状態の振る舞い・割当契機 | 状態遷移、操作条件 | `TicketManager.updateStatus()` | 新しい状態や割当・再オープンの契機が増えるため、今回見る |
| 対応中かつ高優先度の処理 | 状態遷移、優先度判定 | `TicketManager.updateStatus()` | 状態と優先度の両方に依存する条件が変わる可能性があるため、今回見る |

この表から、今回の検討対象は「優先度ルール」と「状態ごとの振る舞い」に絞れます。2つの変化候補が同じ条件に重なると困るかどうかは、フェーズ3で変更を入れてから確認します。

### 2-2：今回の変更で確実に変わること

変更要求として明示的に届いた内容と、現状把握から見えている直近の変化を整理します。今回の変更は2つの独立した軸で同時に起きています。

| **分類** | **具体的な内容** | **変わる軸** |
| --- | --- | --- |
| 🔴 **変動する** | ステータスごとの振る舞い（遷移先・アクション・割当・再オープン） | 状態遷移の軸 |
| 🔴 **変動する** | 優先度判定ルール（SLA基準・SLA期限超過等） | 優先度ルールの軸 |
| 🟢 **当面安定** | チケットの基本属性データ | 今回の変更要求では見直し対象にしない |

コードを読んだだけで「このルールと状態管理は分離できる」と断定するのは危険です。実際に運用を担うヘルプデスクの担当者に、この先の見通しを直接確認します。

### ヒアリングに向けた背景確認

このシステムは、社内のITヘルプデスク部門が運用するサポートチケット管理を担っています。サービスが拡大するにつれて、対応フローの複雑さが増し、特に重要顧客向けのSLA（サービスレベル合意）の厳格化が求められるようになっています。変更の主な関係者は、ビジネスルールを管理するSLA管理チームと、業務プロセスを設計する運用プロセスチームの2者です。この2者が独立して変更を決定している点が、この章の設計判断の核心になります。

### 2-3：関係者ヒアリング

仮説を持って、ヘルプデスクの運用担当者と話し合いを持ちました。

* **開発者：** 「今後『保留中』や『ベンダー確認中』といったステータスが増えるとのことですが、状態によって『できること（遷移先）』や『通知の有無』は変わりますか？」
* **運用担当者：** 「そうなんだ。例えば『ベンダー確認中』の時は、こちらから担当者への割り当ては行わず、自動通知を止める必要がある。逆に『保留中』の時は…」
* **開発者：** 「なるほど。では、重要度に応じた『優先度判定ルール』は、今後も頻繁に調整されますか？」
* **運用担当者：** 「その通り。SLAの基準は四半期ごとに見直す予定だし、顧客との契約内容によってもルールが変わる可能性があるんだよ。プレミアムユーザー向けに今後さらに細かい区分ができるかもしれない。」
* **開発者：** 「確認させてください。状態の種類が増えたとき、SLAのルールも同時に変わりますか？それとも別々に変わりますか？」
* **運用担当者：** 「決める場が別だね。SLAは四半期ごとに契約で見直すもの。状態の追加は業務プロセスの話で、半年単位でシステム側と相談して決める。ただし、エスカレーションのように両方を使う機能では接続の確認が必要だよ。」
* **開発者：** 「分かりました。状態ごとの振る舞いと、優先度の計算ルールは、それぞれ独立して頻繁に変更されるということですね。」

ヒアリングの結果、「チケットの状態ごとの振る舞い」と「優先度判定ルール」は、変更のタイミングと決定者が異なることが分かりました。SLAは四半期ごと、状態の種類追加は半年単位です。実装上は組み合わせて使う場面がありますが、変更理由は分けて扱う価値がある二つの軸です。

### 2-4：ヒアリングで判明した将来リスク

ヒアリングで「今すぐではないが将来起こりうる」と判明したリスクを確定変更とは分けて記録します。

| **リスク** | **ヒアリングでの発言** | **発生確率** |
| --- | --- | --- |
| プレミアムユーザーの区分細分化 | 「今後さらに細かい区分ができるかもしれない」 | 中（次の契約改定時） |
| 複数担当者による同時操作 | 「複数のヘルプデスク担当者が同じチケットを同時に見ることがある」 | 高（日常的に発生） |
| 新状態の追加（保留中・ベンダー確認中） | 「今後はこうした状態も増える予定」 | 確定（半期以内） |

「状態遷移」という変更軸と「優先度ルール」という変更軸を、今の混沌とした `TicketManager` から切り離す必要がありそうです。フェーズ2で「何を変え、何を守るか」が確定しました。次のフェーズ3では、この変更要求を実際に今のコードで試みて、具体的にどのような問題が起きるかを明らかにします。

### 2-5：変わる見込みと当面安定の前提を確定する

2-4のヒアリング結果をもとに、将来起こりうる変更を現在の状態と対比して整理します。

| 変更内容 | 現在 | 将来（時期の目安） |
| --- | --- | --- |
| ユーザー区分と優先度の対応 | 一般→Normal、プレミアム→High の2区分 | プレミアム内にさらに細かい区分が加わる（次の契約改定時） |
| SLA期限による優先度引き上げ | 期限の概念を持たない | 受付から一定時間の超過でHighへ引き上げる基準が入る（四半期改定に連動） |
| 同一チケットへの同時アクセス | 担当者は1人を前提とした設計 | 複数担当者が同じチケットを同時に操作するケースが発生（日常的） |
| チケット状態の種類・割当契機 | Open / InProgress / Resolved の3種類、割当は手動 | 保留中・ベンダー確認中などの状態と割当・再オープンの契機が追加される（半期以内、確定） |

この変化が来たとき、状態の追加と優先度ルールの変更が別々のタイミングで到着することは確認済みです。次のフェーズ3では、フェーズ1の現状コードにこれらの変化を当ててみて、どこが痛みになるかを確認します。

---

## 🟣 フェーズ3：問題特定 ―― 変更の痛みを発見する
### 3-1：変更を試みる

フェーズ2で確定した「状態遷移の増加」と「優先度判定ルールの変更」を、今のコードにそのまま実装してみることにしました。

はじめに、新しいステータス「保留中」に対応するために、`TicketManager` の `updateStatus` メソッド内にある条件分岐に新しい状態の処理を書き足します。続いて、SLAルールの変更に対応するため、`PriorityCalculator` の `calculate` メソッドも修正します。

作業を進める中で、すぐに気づきました。「状態ごとのアクションとルールの条件分岐が混在していて、どちらが変わったときにどこを直せばいいか分からない」という感覚です。ステータスが一つ増えるだけで、「遷移の可否」「担当者への通知」「優先度計算」という、それぞれ変更理由の異なるロジックを一つの大きなメソッドの中で同時に考慮する必要があります。「状態を足したのにSLAのロジックも壊れたかもしれない」という不安が、常について回ります。

実際に変更を加えたコードを見てみましょう。なお、ユーザーIDからティアを引く `UserDatabase` は今回の変更で変わらないため、この変更試行コードでは省略し、ティア（ユーザー種別）を直接渡しています。

```cpp
// 優先度ルール（SLA改定を反映）
class PriorityCalculator {
public:
    std::string calculate(std::string userType) {
        if (userType == "premium")   return "High";
        if (userType == "corporate") return "High"; // ← 追加
        return "Normal";
    }
};

// チケット管理（「保留中」状態を追加）
class TicketManager {
    PriorityCalculator calc;
public:
    void updateStatus(std::string userType,
                      std::string status) {
        std::string priority = calc.calculate(userType);
        if (status == "Open") {
            std::cout << "チケット受付中。優先度: "
                      << priority << std::endl;
        } else if (status == "InProgress"
                   && priority == "High") {
            std::cout << "緊急対応中。担当者を招集します。"
                      << std::endl;
        } else if (status == "Pending") { // ← 新規追加
            std::cout << "保留中。理由を記録します。"
                      << std::endl;
        }
    }
};

int main() {
    TicketManager mgr;
    mgr.updateStatus("premium",   "Open");
    mgr.updateStatus("premium",   "InProgress");
    mgr.updateStatus("corporate", "Open");    // SLA変更で High
    mgr.updateStatus("general",   "Pending"); // 新規状態
    return 0;
}
```

実行対象コード：3-1の変更試行コード
対応する動作例：変更要求後の代表ケース
確認したいこと：変更要求を現状構造へ当てはめたとき、修正箇所と痛みがどこに出るか

実行結果：

```
チケット受付中。優先度: High
緊急対応中。担当者を招集します。
チケット受付中。優先度: High
保留中。理由を記録します。
```

動作は正しくなっています。しかし `PriorityCalculator` と `TicketManager` の両方を修正しており、「状態追加」と「SLAルール変更」という2つの異なる変化が同じ `updateStatus` メソッド内に絡み合っています。

### 3-2：変更影響グラフ

今のコードのまま変更を試みた際の影響範囲を可視化します。

```mermaid
graph LR
    T1["変更要求：SLAルール変更"] -->|"ロジック修正"| A["PriorityCalculator"]
    T1 -->|"複雑な分岐の修正"| B["TicketManager"]
    T2["変更要求：新規状態の追加"] -->|"分岐条件の追加"| B
    B -->|"影響が飛び火"| C["既存の状態遷移ロジック ✅"]
```

グラフが示す通り、ルール変更であれ状態追加であれ、結局は `TicketManager` という唯一の「状態管理の中心となるクラス」が修正のたびに常に触られることになります。

### 3-3：痛みの言語化

「またこの巨大な `if-else` を編集するのか…」というのが、この作業を始めた瞬間の率直な感覚です。

1つ目の痛みは、このクラスが「何でも屋」になりすぎていることです。状態遷移という「振る舞い」と、優先度計算という「ビジネスルール」が密接に絡み合っているため、片方をいじると、もう片方のロジックを無意識に壊してしまう恐怖が常にあります。

2つ目の痛みは、変更の局所化ができていないことです。新しい状態を追加するたびに、本来なら関係のないはずの優先度計算ロジックや、既存の遷移処理まで全てテストし直さなければなりません。この「どこまで影響が出るか分からない」という不安が、開発者の手を鈍らせ、システムをより硬直的なものにしています。

3つ目の痛みは、状態遷移とルール判定が同じきっかけで同時に動く場面で顕在化します。エスカレーションでは「状態を進める」と「SLA期限を見て優先度を上げる」が一度に走り、割当イベントや再オープンでも状態の遷移とその時点の優先度再評価が絡みます。同時に動くこと自体は要求どおりですが、それが同じ `updateStatus` の一続きの `if` に押し込まれているため、状態側の分岐を直したつもりが期限判定の順序を崩す、といった取り違えが起きやすくなっています。

---
> **📌 問題（確定）**
> チケット管理システムでは、「優先度ルールの変更」と「状態遷移の追加」という2つの変化が、それぞれ異なる担当者の判断で独立して発生する。どちらの変化が来ても `TicketManager` を開かなければならず、無関係なロジックまで再テストを強いられる。
---

フェーズ3で「変更が辛い」という事実が確認できました。次のフェーズ4では、なぜ辛いのかを構造的に言語化します。

---

## 🟠 フェーズ4：原因分析 ―― なぜ辛いのかを構造で言語化する
フェーズ3で確認したように、チケットの「状態」が増えるたびに、チケット管理クラスのコードが肥大化し、修正のたびに予期せぬ副作用への恐怖を感じる状態にあります。ここでは、この問題の原因を構造的な観点から紐解いていきます。

### 4-1：痛みの根源を探る（観察と原因）

フェーズ3でのシミュレーションから見えてきた観察事実と、その根本にある構造的な原因を対応させます。「根本原因（構造で言語化）」の列には、「なぜ変更が辛いのか」をコードの構造として表現した原因を記載します。観察事実から「症状」ではなく「構造上の欠陥」を言語化することが、このステップの目的です。

| **根本原因（構造で言語化）** | **観察** | **変わる理由** | **分離の方向性** |
| --- | --- | --- | --- |
| **根本原因A：優先度ルールの混在** | 優先度計算ルールが変わると、チケットの状態遷移ロジックまで再テストが必要になる | ビジネスルールの変更（SLA改定・顧客区分の細分化） | ルールを差し替え可能にする分離 |
| **根本原因B：状態遷移ロジックの混在** | 新しいチケット状態を追加するたびに、管理クラスが修正される | 状態の種類の追加（保留中・ベンダー確認中など） | 状態ごとの振る舞いをオブジェクト化する分離 |

これら2つの根本原因は**互いに独立した変化軸**です。優先度ルールが変わっても状態遷移は変わりません。状態の種類が増えても優先度ルールは変わりません。独立しているからこそ、1つの構造だけでは解決しきれません。

ここで注意したいのは、エスカレーション・割当イベント・SLA期限超過・再オープンのように、状態遷移とルール判定が同じ操作で**同時に動く**場面があることです。同時に動くからといって、変わる理由まで一つとは限りません。状態の追加を決めるのは運用プロセスチーム、SLA期限や優先度基準を決めるのはSLA管理チームで、決定者と改定タイミングは別のままです。「同じきっかけで一緒に動く」ことと「同じ理由で変わる」ことを混同すると、2軸を1つの構造へ無理に押し込む判断につながります。

コードを追うと、単に状態が増えるだけでなく、その状態によって「何をする必要があるか（通知するのか、誰に割り当てるのか）」という判定ロジックが、優先度の計算ルールと複雑に絡み合っていることが分かります。これにより、コードを変更する際に「どこからどこまでが影響範囲なのか」を直感的に捉えることが難しくなっています。

### 4-2：変わるもの/変わってほしくないもの

> **「変わらないもの」と「変わってほしくないもの」は異なります。** 「変わらないもの」は経験的事実（今まで変わっていない）、「変わってほしくないもの」は設計意図（ここを安定させてほかを守りたい）です。ここで整理するのは後者です。

構造を整理するために、変更理由の種類を分けてみます。

| **変わり続けるもの（🔴）** | **変わってほしくないもの（🟢）** |
| --- | --- |
| チケットの「状態ごとの振る舞い」（遷移先、アクション） | チケットの「現在の状態」を保持する基盤データ |
| 優先度判定の「ビジネスルール」（SLA基準、顧客要件） | 「状態遷移を開始する」という汎用的なインターフェース |

これまで私たちは、「チケット」という一つのオブジェクトの中に、ライフサイクルの管理（状態）と、そこから派生するビジネス上の判断（ルール）をまとめて扱っていました。状態が変わるたびにルールが動くのではなく、それぞれが別の軸として進化できるように整理する必要があります。

### 4-3：2つの接続点に漏れている知識を確認する

ここでの「確認すること」は、前節までに見つけた原因から抽出します。まず、原因文から「守りたい骨格」と「変わる差分」を分けます。次に、その差分を動かすために骨格側が知ってしまっている名前・条件・順序・型を拾います。最後に、接続点に残す最小の約束を、値・型・操作・イベントとして書きます。

原因によって、接続点で見る抽象観点は変わります。条件分岐が原因なら条件・定数・選択基準を見ます。処理手順が原因なら呼び出し順・前後条件・失敗時分岐を見ます。生成判断が原因なら具体クラス名・生成条件・登録場所を見ます。通知や外部連携が原因なら通知先・タイミング・成否の扱いを見ます。データや状態が原因なら、境界を流れる値・型・状態を見ます。

現在の`TicketManager`が、状態遷移と優先度判定について何を知っているかを確認します。

今の`TicketManager`には、状態名・遷移条件・優先度計算の条件が集まっています。状態担当とSLA担当の知識が一つのクラスへ埋め込まれています。

現在は、状態遷移・優先度計算・エスカレーション判定・SLA期限判定・割当契機の扱いが `TicketManager` の条件分岐へ集まっています。そのため、優先度ルールだけを変える要求でも、状態遷移を含むクラス全体を確認しなければなりません。割当や再オープンで状態とルールが同時に動く行では、どちらの軸の分岐なのかが読み手に見分けづらくなっています。

---
> **📌 原因（確定）**
> 以下の2つの独立した根本原因が重なっている：
> 1. **優先度ルールの混在**：ビジネスルールの変更による優先度計算の変化が管理クラスに波及する。
> 2. **状態遷移ロジックの混在**：状態の種類が増えるたびに、管理クラスの条件分岐が直接修正される。
>
> これらの変更理由（ルール改定と状態追加）はそれぞれ異なる頻度で発生するため、1つのクラスに混在していることで影響確認コストが発生し続ける。
---

フェーズ4で根本原因が言語化できました。次のフェーズ5では、この整理を元に、解決する課題を具体的に定義していきます。

---

## 🟡 フェーズ5：課題定義 ―― 解くべき接続点を定める
フェーズ4は「なぜ辛いか」を答えました。フェーズ5が問うのは「その境界でどんなデータが流れているか」です。型・値のレベルに降りていきます。

フェーズ4で、「チケットの状態ごとの振る舞い」と「優先度判定ルール」が `TicketManager` クラス内で密結合に混在していることが、変更のたびにコードを汚染させる原因だと特定しました。今のままでは、状態遷移のロジックに手を入れるたびに、無関係な優先度計算のコードまで確認対象に入りやすく、効率が悪くなっています。

### 接続点を特定する

接続点は、クラス図の線やインターフェース名から探すのではなく、変更要求を当てて特定します。まず、その要求で変えたい側と変えたくない側を分けます。次に、両者がどのメソッド呼び出し・引数・戻り値・生成・イベントでつながっているかを見ます。そのつながりのうち、変更要求のたびに知識が漏れて修正が波及する場所が、ここで解くべき接続点です。

今回の分析により、`TicketManager` クラス内に以下の2つの接続点（ジョイント）が存在することが明確になりました。接続点A は状態遷移ロジックの境界、接続点B は優先度判定ロジックの境界です。

以上の分析を、フェーズ6の対策検討に向けたまとめ表として整理します。

| **接続点** | **接続するデータ（型・値）** |
| --- | --- |
| 接続点A | `updateStatus()` 内の `if (status == "Open")` / `"InProgress"` / `"Resolved"` 等の文字列定数 ― 状態名・遷移条件・割当や再オープンの契機が `TicketManager` の条件分岐に直接埋め込まれている |
| 接続点B | `calculatePriority()` 内の `calc.calculate(userType: string)` の引数・戻り値（`"High"` / `"Normal"` 等の文字列）― SLA基準・SLA期限超過・顧客区分の判定値が直接ハードコードされている |

この表が埋まったことで、私たちが解くべき課題は「状態ごとの振る舞いをオブジェクトへ抽出すること」と「優先度判定ルールを独立したアルゴリズムとして分離すること」の2点に絞り込まれました。

---
> **📌 課題（確定）**
> 解くべき課題は2つある。接続点Aでは、状態遷移の条件分岐（`if (status == "Open")` 等）を `TicketManager` から切り離し、状態ごとの振る舞いを独立したオブジェクトとして管理できるようにすること。接続点Bでは、SLA基準や顧客区分の判定ロジック（`calc.calculate(userType)` 等）を `TicketManager` の外に出し、優先度ルールを単独で差し替えられるようにすること。
---

フェーズ5で「何を解くか」が確定しました。次のフェーズ6では、この2つの課題に対し、案を比べ、採用する形を決めます。

---

## 🔴 フェーズ6：対策検討 ―― 案を比べ、採用する形を決める

フェーズ6の出発点は、フェーズ3で変更要求（優先度ルールと状態の追加）を当てて痛んだ「変更途中コード」です。変更要求を容れる前の現状コードには戻しません。状態判定と優先度判定が同じ分岐に同居して増えたコードから、同じ形で扱える共通点（状態ごとの振る舞いと、優先度判定という2つの契約）を抜き出し、変わる差分を接続点の外へ出す形へ整理していきます。読者が「痛み → 共通点の発見 → 抽象化」の順で追えるよう、最初の小さな案も、この変更途中コードを整理する形から始めます。

フェーズ6では、第0章の段階的進化アプローチを標準フローとして使います。ただし、ここでのステップは一本道の作業手順ではなく、対策案を比較するための候補です。まず小さな整理で何が見えるかを確認し、次に責任の移動、契約、窓口、組み合わせ、生成責任の移動のうち、この章の課題に必要な案だけを比べます。章の題材に合わない案を省略したり、順序を入れ替えたり、接続点ごとに分岐させたりする場合は、論点外・効果不足・導入コスト過多・接続点が別であるなどの理由を本文中で説明します。
フェーズ5で整理した「状態ごとの振る舞い」と「優先度判定ルール」という二つの課題に対し、どのように構造を分離するかを検討します。どちらの課題も「変わりやすさ」が特徴であるため、それぞれの接続点から不要な知識を移す必要があります。

フェーズ5の課題から、対策候補は次のように出します。

| フェーズ4で見えた原因 | フェーズ5で定めた課題 | だからフェーズ6で見る候補 |
|---|---|---|
| チケット状態ごとの操作可否と遷移条件が `TicketManager` に集まっている | 状態ごとの振る舞いを、チケット操作の公開形を変えずに切り離す | 状態処理を関数化した後、状態ごとの部品へ移す案を見る |
| 優先度判定の条件がSLA基準・SLA期限に応じて変わる | 優先度計算ルールを状態遷移とは別に差し替えられるようにする | 優先度計算を独立したアルゴリズムとして扱う案を見る |
| 割当・再オープンで状態遷移と優先度再評価が同時に動く | 同時に動く軸を、状態側とルール側の別々の構造へ分けて解く | 状態側と優先度側で別々の候補案を比較し、組み合わせるか判断する |

どのステップも、動作例テーブルで示した基本的な動作（行1〜3）を実現します。行4・5（Resolved遷移・再オープン）はフェーズ7の最終実装で初めて全カバーされます。違うのは「変更が来たときにどこを触ることになるか」です。

---

#### ステップ1の比較元：仕様変更後の痛みコードをおさらいする

比較元は、法人ユーザーの優先度変更と `Pending` 状態を同時に追加したフェーズ3の変更途中コードです。2つの変更要求を残したまま、状態処理と優先度判定を分けます。

```cpp
// フェーズ3の変更途中コード（対策前）の要点
string PriorityCalculator::calculate(string userType) {
    if (userType == "premium")   return "High";
    if (userType == "corporate") return "High";
    return "Normal";
}

void TicketManager::updateStatus(string userType, string status) {
    string priority = calc.calculate(userType);
    if (status == "Open") {
        cout << "チケット受付中。優先度: " << priority << endl;
    } else if (status == "InProgress" && priority == "High") {
        cout << "緊急対応中。担当者を招集します。" << endl;
    } else if (status == "Pending") {
        cout << "保留中。理由を記録します。" << endl;
    }
}
```

ステップ1は法人ルールと `Pending` を維持してメソッドへ分けます。ステップ2以降は、直前ステップから状態分岐と優先度ルールの知識がどこへ移ったかを比べます。

### ステップ1：各処理を独立した関数として切り出す（共通構造を発見する）

**この形の考え方：**
フェーズ3で示したコードを、接続点の設計は変えずに各処理を独立したプライベートメソッドとして切り出した形です。`Open` 状態の処理と `InProgress` 状態の処理を、それぞれ独立したメソッドに分割します。`PriorityCalculator` を直接メンバに持ち、`if-else` 分岐もそのままですが、各分岐をプライベートメソッドに抽出して責任を整理します。

**構造図：**

```mermaid
classDiagram
    class TicketManager {
        <<プライベートメソッドで整理>>
        +updateStatus(userType, status)
        -handleOpen(priority)
        -handleInProgress(priority)
        -handlePending()
    }
    class PriorityCalculator {
        +calculate(userType) string
    }
    TicketManager --> PriorityCalculator : クラス名と条件を呼び出し元が知る
```

`TicketManager`が`PriorityCalculator`というクラス名を知っており、ルール変更のたびにコードを修正する必要がある点はフェーズ3と同じです。プライベートメソッドで読みやすくなりましたが、知識の置き場所は変わっていません。


**PriorityCalculator クラス（ステップ1）：**

```cpp
// ステップ1：優先度ルールをそのまま維持（クラス名と条件を呼び出し元が知る）
class PriorityCalculator {
public:
    string calculate(string userType) {
        if (userType == "premium")   return "High"; // ← 具体：文字列を直書き
        if (userType == "corporate") return "High"; // SLA変更を維持
        return "Normal";
    }
};
```

**TicketManager クラス（ステップ1）：**

```cpp
// ステップ1：各処理を独立したプライベートメソッドに切り出す
class TicketManager {
    PriorityCalculator calc; // ← 具体：PriorityCalculatorを直接保持
public:
    void updateStatus(string userType, string status) {
        string priority = calc.calculate(userType);
        if (status == "Open") {
            handleOpen(priority); // ← Open状態の処理を独立したメソッドへ
            return;
        }
        if (status == "InProgress") {
            handleInProgress(priority); // ← InProgress状態の処理を独立したメソッドへ
            return;
        }
        if (status == "Pending") {
            handlePending(); // ← 追加済み状態も独立したメソッドへ
        }
    }
private:
    void handleOpen(string priority) {
        cout << "チケット受付中。優先度: " << priority << endl;
    }
    void handleInProgress(string priority) {
        if (priority == "High") {
            cout << "緊急対応中。担当者を招集します。" << endl;
        }
    }
    void handlePending() {
        cout << "保留中。理由を記録します。" << endl;
    }
};
```

**main 関数（ステップ1）：**

```cpp
int main() {
    TicketManager manager;

    // 行1: 一般ユーザーが新規登録（Normal優先度でOpen）
    manager.updateStatus("normal", "Open");

    // 行2: プレミアムユーザーが新規登録（High優先度でOpen）
    manager.updateStatus("premium", "Open");

    // 行3: 担当者アサイン（InProgressへ遷移）
    manager.updateStatus("normal", "InProgress");

    // フェーズ3で追加した2要件も維持
    manager.updateStatus("corporate", "Open");
    manager.updateStatus("normal", "Pending");

    // 行4・行5（Resolved／再オープン）はこのステップでは未実装
    return 0;
}
```

各処理を独立したプライベートメソッドへ切り出したことで、状態ごとの振る舞いがメソッド単位で分離されました。

**この段階の評価：**

`handleOpen(string priority)` と `handleInProgress(string priority)` を並べて見ると、どちらも「`priority` を引数に受け取り、何も返さない」という同じシグネチャを持っています。さらに `calc.calculate(userType)` と `handleXxx(priority)` という2つの処理のかたまりを観察すると、「優先度の計算」と「状態ごとのアクション実行」が `updateStatus()` の中で混在していることが見えてきます。「処理の実行（`handleXxx`）」と「どの処理を選ぶか（`if` の制御）」が同じメソッドにあるという構造の分離の必要性が浮かび上がります。

この「複数のメソッドが同じシグネチャを持つ」という気づきは、次のステップでインターフェースへ抽象化するための足がかりになります。

**このステップのトレードオフ：**

* 変更容易性：低（ルール変更のたびに具体型を知る `TicketManager` を修正する必要がある）
* テスト容易性：低（具体クラスへの依存が残り、切り離せない）
* 実装コスト：低（プライベートメソッドへの抽出のみ）


---

### ステップ2：処理を別クラスに切り出す

**ステップ1との差：** プライベートメソッドとして整理した状態処理を独立クラスへ移します。法人優先度と `Pending` 状態はそのまま保持します。

**この形の考え方：**
優先度計算や状態処理を別クラスへ切り出し、呼び出し元がそれらへ処理を委ねる形です。処理の置き場所は分かれますが、呼び出し元は `PriorityCalculator` や各Phaseのクラス名と生成方法を知っています。実装を差し替える要求では、呼び出し元も修正します。

**構造図：**

```mermaid
classDiagram
    class TicketManager {
        +updateStatus(userType, status)
    }
    class PriorityCalculator {
        +calculate(userType) string
    }
    class OpenPhase {
        +activate()
    }
    class InProgressPhase {
        +activate()
    }
    class PendingPhase {
        +activate()
    }
    TicketManager --> PriorityCalculator : 別クラスへ委譲するがクラス名を知る
    TicketManager --> OpenPhase : 別クラスへ委譲するがクラス名を知る
    TicketManager --> PendingPhase : 追加済み状態も具体名を知る
```

クラスは分離されて処理を委ねるようになりましたが、呼び出し元が各実装のクラス名と生成方法を知っています。状態やルールを差し替えるときは、処理クラスだけでなく呼び出し元も修正する構造です。

**PriorityCalculator クラスと状態クラス（ステップ2）：**

```cpp
// ステップ2：処理を別クラスに切り出した（別クラスへ委譲するがクラス名を知る）
class PriorityCalculator {
public:
    string calculate(string userType) {
        if (userType == "premium")   return "High";
        if (userType == "corporate") return "High";
        return "Normal";
    }
};

class OpenPhase {
public:
    // 呼び出し元はここに処理を委ねる（間接）
    void activate() { cout << "チケットをオープン状態に設定。" << endl; }
};

class InProgressPhase {
public:
    void activate() { cout << "チケットを対応中状態に設定。" << endl; }
};

class PendingPhase {
public:
    void activate() { cout << "保留中。理由を記録します。" << endl; }
};
```

**TicketManager クラス（ステップ2）：**

```cpp
// ステップ2：TicketManagerが具体クラスを知り、処理をそのクラスに委ねる
class TicketManager {
public:
    void updateStatus(string userType, string status) {
        PriorityCalculator calc; // ← 具体：型名を直接書いている
        string priority = calc.calculate(userType);
        // ← 間接：計算はcalcに委ねて自分ではやらない
        if (status == "Open") {
            OpenPhase s; // ← 具体：OpenPhaseという型名を直接書いている
            s.activate(); // ← 間接：Open状態の処理をsに委ねる
            cout << "優先度: " << priority << endl;
            return;
        }
        if (status == "InProgress" && priority == "High") {
            InProgressPhase s; // ← 具体：InProgressPhaseを直接生成
            s.activate(); // ← 間接：対応中状態の処理をsに委ねる
            cout << "緊急対応中。担当者を招集します。" << endl;
            return;
        }
        if (status == "Pending") {
            PendingPhase s;
            s.activate();
        }
    }
};
```

**main 関数（ステップ2）：**

```cpp
int main() {
    TicketManager manager;
    manager.updateStatus("premium", "InProgress");
    manager.updateStatus("corporate", "Open");
    manager.updateStatus("normal", "Pending");
    return 0;
}
```

処理を別クラスに委ねる形（間接）になりましたが、具体クラス名の知識が `TicketManager` に残っており、クラスを差し替えるには呼び出し元を修正する必要があるでしょう。

**このステップのトレードオフ：**

* 変更容易性：低〜中（クラスは分かれたが、具体クラス名の依存は残る）
* テスト容易性：低（依然として具体クラスを直接生成する必要がある）
* 実装コスト：低（リファクタリングの範囲が限定的）


---

### ステップ3：関数アプローチの限界を確認する

**ステップ2との差：** 別クラス化しても具体クラス名の依存が残ったため、同じ形の関数へ整理した場合と比較し、契約へ抽象化すべき共通点を確認します。

ステップ1・2の構造では呼び出し元がルールの種類と状態名を知る問題が残りました。ここで少し立ち止まって、処理を関数（プライベートメソッド）として整理し直した場合に何が見えてくるかを確認します。

```cpp
// ステップ3：条件・処理を関数に切り出した場合の整理限界
class TicketManager {
    // 処理を個別メソッドに切り出す
    string calcPremiumPriority() { return "High"; }
    string calcNormalPriority() { return "Normal"; }
    void handleOpen(string priority) {
        cout << "チケット受付中。優先度: " << priority << endl;
    }
    void handleInProgress(string priority) {
        if (priority == "High") {
            cout << "緊急対応中。担当者を招集します。" << endl;
        }
    }
    void handlePending() {
        cout << "保留中。理由を記録します。" << endl;
    }
    string routePriority(string userType) {
        if (userType == "premium") return calcPremiumPriority();
        if (userType == "corporate") return calcPremiumPriority();
        return calcNormalPriority();
    }
    void routeStatus(string status, string priority) {
        if (status == "Open") handleOpen(priority);
        else if (status == "InProgress") handleInProgress(priority);
        else if (status == "Pending") handlePending();
    }
public:
    void updateStatus(string userType, string status) {
        string priority = routePriority(userType);
        routeStatus(status, priority);
    }
};
```


関数化により各処理の意図は読みやすくなりました。しかしここで立ち止まって、抽出した関数群を観察してください。`calcPremiumPriority()` と `calcNormalPriority()` はどちらも「同じ引数を受け取り同じ型を返す」一貫した構造を持っています。`handleOpen()` と `handleInProgress()` も同様です。「一貫した構造（同じ形）を持つ関数が並んでいる」ことは「共通インターフェースとして抽象化できる」証拠です。

しかし関数化のままでは2つの軸で同じ限界に直面します。**優先度ルールの軸：**「VIP優先度」が増えるたびに `TicketManager` を開いて新しい関数を追加し、`routePriority` の `if` 文に書き足す必要があります。**状態遷移の軸：**「保留中」状態が追加されるたびに `TicketManager` を開いて `handleHold()` 関数を追加し、`routeStatus` の `if` 文に書き足す必要があります。2つの軸それぞれで「クラスが永遠に変わり続ける」という根本問題は解決していません。

この限界が、次のステップ4でルール差し替え構造を導入する動機になります。

---

### ステップ4：ルール差し替え構造で優先度ルールを分離する

ステップ3で「関数化の限界」が見えました。各関数が「同じ形（インターフェース）を持つ」なら、それを共通インターフェースとして抽象化できます。はじめに優先度ルールの変化軸から解決します。

**構造図：**

```mermaid
classDiagram
    class IPriorityRule {
        <<interface>>
        +getPriority(userType) string
    }
    class TicketManager {
        -strategy IPriorityRule
        +update()
    }
    class PremiumPriority {
        +getPriority(userType) string
    }
    class NormalPriority {
        +getPriority(userType) string
    }
    PremiumPriority ..|> IPriorityRule : 実装
    NormalPriority ..|> IPriorityRule : 実装
    TicketManager --> IPriorityRule : 共通の契約だけを知る
```

**インターフェースと優先度戦略クラス（ステップ4）：**

```cpp
#include <iostream>
#include <string>
using namespace std;

// 優先度判定のインターフェース（ルール差し替え構造の骨格）
class IPriorityRule {
public:
    virtual ~IPriorityRule() = default;
    virtual string getPriority(string userType) = 0;
};

// プレミアムユーザー向け優先度ルール
class PremiumPriority : public IPriorityRule {
public:
    string getPriority(string userType) override {
        return "High"; // ← プレミアムユーザーは常にHighとする
    }
};

// 一般ユーザー向け優先度ルール
class NormalPriority : public IPriorityRule {
public:
    string getPriority(string userType) override {
        return "Normal";
    }
};

// SLA変更で追加した法人ユーザー向け優先度ルール
class CorporatePriority : public IPriorityRule {
public:
    string getPriority(string userType) override {
        return "High";
    }
};
```

**TicketManager クラス（ステップ4）：**

```cpp
// ステップ4：TicketManagerはIPriorityRule*のみを知る（優先度ルールの軸が解決）
class TicketManager {
    // ← 抽象：外部から注入されたインターフェースのみ知っている
    IPriorityRule* strategy;
public:
    TicketManager(IPriorityRule* s) : strategy(s) {}
    void updateStatus(string userType, string status) {
        string priority = strategy->getPriority(userType); // ← 抽象経由で呼ぶ
        // 状態遷移のif-elseはまだTicketManager内に残っている
        if (status == "Open") {
            cout << "チケット受付中。優先度: " << priority << endl;
        } else if (status == "InProgress" && priority == "High") {
            cout << "緊急対応中。担当者を招集します。" << endl;
        } else if (status == "Pending") {
            cout << "保留中。理由を記録します。" << endl;
        }
    }
};
```

> [!INFO] 生ポインタの使用について
> このサンプルでは依存性の注入を示すため、生ポインタ（`IPriorityRule* strategy`）を使用しています。本書では全章を通じて生ポインタを使い、所有権の議論よりも構造の変化に集中します。

**main 関数（ステップ4）：**

```cpp
int main() {
    // ← 具体：呼び出し側だけが具体クラスを生成
    PremiumPriority strategy;
    TicketManager manager(&strategy);
    manager.updateStatus("premium", "InProgress");
    CorporatePriority corporateRule;
    TicketManager corporateManager(&corporateRule);
    corporateManager.updateStatus("corporate", "Open");
    corporateManager.updateStatus("corporate", "Pending");
    return 0;
}
```

ステップ4でルール差し替え構造を導入したことで、優先度ルールは新しいルールクラスと選択・注入箇所へ分けられました。`TicketManager` の判定ロジックへルール種別の条件分岐を増やさずに済みます。しかし状態遷移の変化軸はまだ残っています。新しい状態「保留中」が追加されるたびに、`TicketManager` の状態判定の `if` 文を開かなければなりません。この残課題を解決するのがステップ5です。

---

### ステップ5：状態分離構造で状態ごとの振る舞いを分離する

ステップ4で残った「状態による変化」を解決するために、状態ごとの振る舞いをオブジェクトとして分離する設計を導入します。なお、この実装例では状態遷移の管理責任は呼び出し側（Context）に残し、「状態ごとの表示やアクション」の分離に焦点を当てています。

なお、このステップから `TicketManager` を **`TicketContext`** に改名します。状態分離構造の導入によりこのクラスはもはや「状態を管理する」責務を持たず、現在の状態オブジェクトを保持して委譲するだけの「コンテキスト」に変わるためです。GoFの状態分離構造では、状態オブジェクトを保持するクラスを慣習的に Context と呼びます。

**構造図：**

```mermaid
classDiagram
    class IPriorityRule {
        <<interface>>
        +getPriority(userType) string
    }
    class ITicketPhase {
        <<interface>>
        +handle(context)
        +display()
    }
    class TicketContext {
        -strategy IPriorityRule
        -state ITicketPhase
        +execute()
    }
    class PremiumPriority {
        +getPriority(userType) string
    }
    class NormalPriority {
        +getPriority(userType) string
    }
    class CorporatePriority {
        +getPriority(userType) string
    }
    class OpenPhase {
        +handle(context)
        +display()
    }
    class InProgressPhase {
        +handle(context)
        +display()
    }
    class PendingPhase {
        +handle(context)
        +display()
    }
    PremiumPriority ..|> IPriorityRule : 実装
    NormalPriority ..|> IPriorityRule : 実装
    CorporatePriority ..|> IPriorityRule : 実装
    OpenPhase ..|> ITicketPhase : 実装
    InProgressPhase ..|> ITicketPhase : 実装
    PendingPhase ..|> ITicketPhase : 実装
    TicketContext --> IPriorityRule : 共通の契約だけを知る
    TicketContext --> ITicketPhase : 共通の契約だけを知る
```

`TicketContext` は2つのインターフェースのみを知り、具体クラスはmain()側だけが生成して注入する。


**インターフェース定義（ステップ5）：**

```cpp
#include <iostream>
#include <string>
using namespace std;

// ルール差し替え構造: 優先度判定のインターフェース
class IPriorityRule {
public:
    virtual ~IPriorityRule() = default;
    virtual string getPriority(string userType) = 0;
};

// 状態分離構造: 状態別振る舞いのインターフェース
class ITicketPhase {
public:
    virtual ~ITicketPhase() = default;
    virtual void handle(class TicketContext* context) = 0;
    virtual void display() = 0;
};
```

**優先度戦略クラス（ステップ5）：**

```cpp
// プレミアムユーザー向け優先度ルール
class PremiumPriority : public IPriorityRule {
public:
    string getPriority(string userType) override {
        return "High"; // ← プレミアムユーザーは常にHighとする
    }
};

// 一般ユーザー向け優先度ルール
class NormalPriority : public IPriorityRule {
public:
    string getPriority(string userType) override {
        return "Normal";
    }
};

class CorporatePriority : public IPriorityRule {
public:
    string getPriority(string userType) override {
        return "High";
    }
};
```

**状態クラス（ステップ5）：**

```cpp
// Open状態の振る舞い
class OpenPhase : public ITicketPhase {
public:
    void handle(TicketContext* context) override { display(); }
    void display() override {
        cout << "チケット受付中。" << endl;
    }
};

// 対応中状態の振る舞い
class InProgressPhase : public ITicketPhase {
public:
    void handle(TicketContext* context) override { display(); }
    void display() override {
        cout << "チケット対応中。担当者に割り当て。" << endl;
    }
};

class PendingPhase : public ITicketPhase {
public:
    void handle(TicketContext* context) override { display(); }
    void display() override {
        cout << "保留中。理由を記録します。" << endl;
    }
};
```

**TicketContext クラス（ステップ5）：**

```cpp
// コンテキスト：インターフェース型のみを知る
class TicketContext {
    ITicketPhase* state;
    IPriorityRule* strategy;
public:
    TicketContext(ITicketPhase* st, IPriorityRule* s)
        : state(st), strategy(s) {}
    void setState(ITicketPhase* s) { state = s; }
    void setStrategy(IPriorityRule* s) { strategy = s; }
    void execute(string userType) {
        string priority = strategy->getPriority(userType); // ← 抽象経由
        cout << "優先度: " << priority << " — ";
        state->handle(this); // ← 直接呼び出し
    }
    string calculatePriority(string userType) {
        return strategy->getPriority(userType);
    }
};
```

**main 関数（ステップ5）：**

```cpp
int main() {
    // ← 具体：呼び出し側だけが具体クラスを生成
    PremiumPriority strategy;
    // ← 具体：呼び出し側だけが具体クラスを生成
    InProgressPhase state;
    TicketContext ctx(&state, &strategy);
    ctx.execute("premium");
    CorporatePriority corporateRule;
    PendingPhase pending;
    TicketContext corporatePending(&pending, &corporateRule);
    corporatePending.execute("corporate");
    return 0;
}
```

ここまでの短いコードは、2つの変化軸を別のインターフェースへ分ける骨格を示したものです。`handle()` は表示だけに省略しています。フェーズ7の完成版では、各状態クラスが次の状態を保持し、`TicketContext::setState()` を呼んで実際に遷移させます。

**このステップのトレードオフ：**

* 変更容易性：高（主な変更は対応する独立クラス内に限定できる）
* テスト容易性：高（インターフェースに対しスタブを差し込んで個別にテストできる）
* 実装コスト：中（インターフェースと複数の実装クラスを定義する必要がある）

---

### 採用する形を決める

それぞれのステップには一長一短があります。ステップ5の「共通の契約だけを知る（インターフェースの導入）」は強力ですが、クラス数が増加する「初期投資コスト」もかかります。どこで止めるかは、**「今後の変更頻度（ビジネス要求）」**で決断します。

今回の課題は、優先度ルールと状態ごとの振る舞いという2つの変化軸を、同じ条件分岐の中で扱っていることです。どちらか一方だけを分ければ足りるのか、両方を分ける必要があるのかを比べます。

| 案 | 解けること | 残ること | 今回の判断 |
|---|---|---|---|
| 何もしない | 追加コストはない | ルール変更と状態追加のたびに同じ分岐を修正する | 2軸の変更頻度と合わない |
| 関数化 | 優先度計算や状態処理に名前が付く | どの関数を使うかの判断は本体に残る | 最初の整理として有効 |
| 優先度ルールだけ分ける | SLA期限や顧客区分の変更を局所化できる | 状態追加や割当契機の分岐は残る | 状態が固定なら有効 |
| 状態だけ分ける | 状態ごとの振る舞いを局所化できる | 優先度ルールの差し替えは残る | ルールが固定なら有効 |
| ルールと状態を別々に分ける | 2つの変化軸を独立して扱える | クラス数と組み立てが増える | 両方が増えるため採用する |

エスカレーションや割当のように状態とルールが同時に動く行があっても、採用する形は変わりません。同時に動く1回の操作を、状態軸は状態オブジェクトへ、ルール軸（SLA期限を含む優先度判定）は優先度ルールへと、別々の構造へ振り分けます。同時に呼ぶこと自体は組み立て側の役目に残し、それぞれの軸が独立して差し替えられる状態を保ちます。

* **ステップ1（プライベートメソッドで整理）で止めるケース：** 優先度ルールが「通常」と「緊急」の2つだけで、当面増える見込みが低い場合。
* **ステップ2（処理を別クラスに切り出す）で止めるケース：** クラスごとに分けたいが、動的なルールの切り替えは発生しない場合。
* **ステップ3（関数アプローチの限界確認）で止めるケース：** チームに関数化アプローチの限界を共有したが、まだ変更頻度が低くインターフェース導入のコストが高い場合の様子見判断。
* **ステップ4（ルール差し替え構造）で止めるケース：** 優先度ルールは複数存在し今後も増えるが、状態遷移はまだシンプルで増える見込みがない場合。
* **ステップ5（ルール差し替え構造 × 状態分離構造）まで進むケース：** 優先度ルールと状態遷移の両方が、独立した担当者によって頻繁に変更されることが確定している場合。

**今回の決断：**
フェーズ2のヒアリングで「SLA基準の四半期ごとの見直し」や「プレミアムユーザー区分の細分化」など、優先度ルールの頻繁な変更が確定しています。さらに「保留中」「ベンダー確認中」といった状態自体の追加も確定しています。2つの変化軸（状態の増減、優先度ルールの変更）をそれぞれ独立して安全に変更できるようにするため、**ステップ5（ルール差し替え構造 × 状態分離構造）まで進む**決断を下します。

> 実はこのステップ5の構造には名前があります。「優先度ルールの差し替え可能な分離」は **ルール差し替え構造**、「状態ごとの振る舞いをオブジェクトとして表現する」は **状態分離構造** と呼ばれています。この構造は、第1章で学んだ**ルール差し替え構造**と、第3章で学んだ**状態分離構造**を組み合わせた複合設計です。

フェーズ6で採用する形が決まりました。次のフェーズ7では、この決断を最終的なコードに落とし込みます。

---

## 🟢 フェーズ7：対策実施 ―― 変化に強いコードを完成させる
採用した ルール差し替え構造（優先度ルールの分離）および 状態分離構造（状態ごとの振る舞いの分離）を実装し、ビジネスルールと状態固有の処理をそれぞれ独立したクラスへカプセル化します。

### 7-1：解決後のコード（全体）

優先度判定を `IPriorityRule`、状態管理を `ITicketPhase` へとそれぞれ分離しました。

**UserInfo / UserDatabase / IPriorityRule インターフェースと実装クラス**

```cpp
#include <iostream>
#include <string>
#include <vector>
#include <map>

using namespace std;

// ユーザー情報
struct UserInfo {
    string name; // 氏名
    string tier; // "standard", "premium", "corporate"
};

// ユーザーデータベース
class UserDatabase {
    map<string, UserInfo> records;
public:
    UserDatabase() {
        records["USR001"] = {"田中 一郎", "corporate"};
        records["USR002"] = {"佐藤 花子", "premium"};
        records["USR003"] = {"鈴木 次郎", "standard"};
    }
    bool exists(const string& id) const {
        return records.count(id) > 0;
    }
    UserInfo get(const string& id) const {
        return records.at(id);
    }
    void save(const string& id, const UserInfo& info) {
        records[id] = info;           // 実行中のユーザー表へ追加
    }
};

// ルール差し替え構造: 優先度計算のインターフェース
class IPriorityRule {
public:
    virtual ~IPriorityRule() = default;
    virtual string getPriority(string userTier) = 0;
};
```

チケットイベントログ（`TicketEventLog`）はシステム起動時は空で、チケットの作成・アサイン・解決・再オープンのたびに1件追記されます。ファイルへの保存は行わず、実行中のメモリ上にのみ保持します。

```cpp
struct TicketEvent {
    std::string userId;
    std::string userName;
    std::string eventType;   // "チケット作成", "アサイン", "解決", "再オープン"
    std::string priority;    // "Normal", "High"
};

// チケットイベントログを管理するクラス
class TicketEventLog {
    std::vector<TicketEvent> records;
public:
    void add(const std::string& userId, const std::string& userName,
             const std::string& eventType, const std::string& priority) {
        records.push_back({userId, userName, eventType, priority});
    }
    void printAll() const {
        for (const auto& r : records) {
            std::cout << "[" << r.userId << "] " << r.userName
                      << " " << r.eventType
                      << " (" << r.priority << ")" << std::endl;
        }
    }
    int size() const { return (int)records.size(); }
};
```

**CorporatePriority、PremiumPriority、NormalPriority クラス**

```cpp
// 法人ユーザー向けSLA優先度ルール（フェーズ3の変更を維持）
class CorporatePriority : public IPriorityRule {
public:
    string getPriority(string userTier) override { return "High"; }
};

// プレミアム向け優先度ルール
class PremiumPriority : public IPriorityRule {
public:
    string getPriority(string userTier) override { return "High"; }
};

// 一般（standard）ユーザー向け優先度ルール
class NormalPriority : public IPriorityRule {
public:
    string getPriority(string userTier) override { return "Normal"; }
};
```

**ITicketPhase インターフェース**

```cpp
// 状態分離構造: 状態別振る舞いのインターフェース
class ITicketPhase {
public:
    virtual ~ITicketPhase() = default;
    virtual void handle(class TicketContext* context) = 0;
    virtual void display() = 0;
};
```

**OpenPhase / InProgressPhase / ResolvedPhase / PendingPhase クラス**

```cpp
// Open状態の振る舞い
class OpenPhase : public ITicketPhase {
    ITicketPhase* next = nullptr;
public:
    void setNext(ITicketPhase* phase) { next = phase; }
    void handle(TicketContext* context) override;
    void display() override;
};

// InProgress状態の振る舞い
class InProgressPhase : public ITicketPhase {
    ITicketPhase* next = nullptr;
public:
    void setNext(ITicketPhase* phase) { next = phase; }
    void handle(TicketContext* context) override;
    void display() override;
};

// Resolved状態の振る舞い
class ResolvedPhase : public ITicketPhase {
    ITicketPhase* next = nullptr;
public:
    void setNext(ITicketPhase* phase) { next = phase; }
    void handle(TicketContext* context) override;
    void display() override;
};

// 変更要求で追加した保留中状態
class PendingPhase : public ITicketPhase {
    ITicketPhase* next = nullptr;
public:
    void setNext(ITicketPhase* phase) { next = phase; }
    void handle(TicketContext* context) override;
    void display() override;
};
```

**TicketContext クラス（コンテキスト）**

```cpp
// コンテキスト：インターフェース型のみを保持する
class TicketContext {
    ITicketPhase* state;
    IPriorityRule* strategy;
public:
    TicketContext(ITicketPhase* st, IPriorityRule* s)
        : state(st), strategy(s) {}
    void setState(ITicketPhase* s) { state = s; }
    void setStrategy(IPriorityRule* s) { strategy = s; }
    void execute(string userTier) {
        string priority = strategy->getPriority(userTier); // ← 抽象経由
        cout << "優先度: " << priority << " — ";
        state->display();
    }
    void transition(string userTier) {
        string priority = strategy->getPriority(userTier);
        cout << "優先度: " << priority << " — ";
        state->handle(this); // 現在の状態が次の状態を決める
    }
    string calculatePriority(string userTier) {
        return strategy->getPriority(userTier);
    }
};
```

**状態クラスの handle 実装**

```cpp
// OpenPhase の実装（TicketContextが定義された後）
void OpenPhase::handle(TicketContext* context) {
    if (next == nullptr) { display(); return; }
    context->setState(next);
    next->display();
}
void OpenPhase::display() {
    cout << "チケット受付中。" << endl;
}

// InProgressPhase の実装
void InProgressPhase::handle(TicketContext* context) {
    if (next == nullptr) { display(); return; }
    context->setState(next);
    next->display();
}
void InProgressPhase::display() {
    cout << "チケット対応中。担当者に割り当て。" << endl;
}

// ResolvedPhase の実装
void ResolvedPhase::handle(TicketContext* context) {
    if (next == nullptr) { display(); return; }
    context->setState(next);
    next->display();
}
void ResolvedPhase::display() {
    cout << "チケット解決済み。クローズしました。" << endl;
}

// PendingPhase の実装（フェーズ3の保留中状態を維持）
void PendingPhase::handle(TicketContext* context) {
    if (next == nullptr) { display(); return; }
    context->setState(next);
    next->display();
}
void PendingPhase::display() {
    cout << "保留中。理由を記録します。" << endl;
}
```

`handle(context)` は各状態が次の状態を選び、`TicketContext` を更新する通常処理で使います。`display()` は状態を変えずに現在の振る舞いだけを実行するときに使います。遷移先は組み立て時に `setNext()` で注入するため、`TicketContext` に状態名の条件分岐は戻りません。将来の状態クラスが `context` を参照する実装へ変わっても安全です。


**TicketApplication クラス（組み立て担当）**

具体クラスを知っているのはこの1クラスだけです。`main()` は組み立てを知りません。

```cpp
// TicketApplication：具体クラスの組み立てと実行を担当する
class TicketApplication {
    UserDatabase db;

    // ユーザーIDからルール差し替え構造を選択する補助メソッド
    IPriorityRule* selectStrategy(
            const string& userId,
            NormalPriority& normal,
            PremiumPriority& premium,
            CorporatePriority& corporate) {
        if (!db.exists(userId)) {
            cout << "エラー: ユーザーID "
                 << userId << " は存在しません。" << endl;
            return nullptr;
        }
        string tier = db.get(userId).tier;
        if (tier == "corporate") {
            return &corporate;
        }
        if (tier == "premium") {
            return &premium;
        }
        return &normal;
    }

public:
    void run() {
        NormalPriority normalStrategy;
        PremiumPriority premiumStrategy;
        CorporatePriority corporateStrategy;
        OpenPhase openPhase;
        InProgressPhase inProgressPhase;
        ResolvedPhase resolvedPhase;
        PendingPhase pendingPhase;
        openPhase.setNext(&inProgressPhase);
        inProgressPhase.setNext(&resolvedPhase);
        resolvedPhase.setNext(&openPhase);
        pendingPhase.setNext(&openPhase);
        TicketEventLog ticketLog;

        // 行1: 鈴木（standard）が新規登録
        cout << "--- 行1: 鈴木（standard）が新規登録 ---" << endl;
        IPriorityRule* s1 =
            selectStrategy("USR003", normalStrategy, premiumStrategy,
                           corporateStrategy);
        if (!s1) return;
        TicketContext ctx1(&openPhase, s1);
        ctx1.execute(db.get("USR003").tier);
        ticketLog.add("USR003", db.get("USR003").name,
                      "チケット作成", "Normal");

        // 行2: 佐藤（premium）が新規登録
        cout << "--- 行2: 佐藤（premium）が新規登録 ---" << endl;
        IPriorityRule* s2 =
            selectStrategy("USR002", normalStrategy, premiumStrategy,
                           corporateStrategy);
        if (!s2) return;
        TicketContext ctx2(&openPhase, s2);
        ctx2.execute(db.get("USR002").tier);
        ticketLog.add("USR002", db.get("USR002").name,
                      "チケット作成", "High");

        // 行3: 受付中チケットに担当者をアサイン（Open→InProgress）
        cout << "--- 行3: 担当者アサイン ---" << endl;
        ctx1.transition(db.get("USR003").tier);
        ticketLog.add("USR003", db.get("USR003").name,
                      "アサイン", "Normal");

        // 行4: 担当者が解決（InProgress→Resolved）
        cout << "--- 行4: 担当者が解決 ---" << endl;
        ctx1.transition(db.get("USR003").tier);
        ticketLog.add("USR003", db.get("USR003").name,
                      "解決", "Normal");

        // 行5: 解決済みを鈴木が再オープン（Resolved→Open）
        cout << "--- 行5: 鈴木が再オープン ---" << endl;
        ctx1.transition(db.get("USR003").tier);
        ticketLog.add("USR003", db.get("USR003").name,
                      "再オープン", "Normal");

        // 変更要求: 法人ユーザーのSLAルールと保留中状態
        cout << "--- 変更要求: 田中（corporate）を保留中で受付 ---"
             << endl;
        IPriorityRule* s3 =
            selectStrategy("USR001", normalStrategy, premiumStrategy,
                           corporateStrategy);
        if (!s3) return;
        TicketContext ctx3(&pendingPhase, s3);
        ctx3.execute(db.get("USR001").tier);
        ticketLog.add("USR001", db.get("USR001").name,
                      "保留", "High");

        cout << "\n--- チケットイベントログ ---\n";
        ticketLog.printAll();
    }
};
```

**main 関数**

```cpp
int main() {
    TicketApplication app;
    app.run();
    return 0;
}
```

実行対象コード：7-1の解決後コード
対応する動作例：1-2の動作例テーブル、および変更要求後の代表ケース
確認したいこと：外部から見える結果を保ちながら、変更理由ごとの責任が分離されていること

**実行結果：**

```
--- 行1: 鈴木（standard）が新規登録 ---
優先度: Normal — チケット受付中。
--- 行2: 佐藤（premium）が新規登録 ---
優先度: High — チケット受付中。
--- 行3: 担当者アサイン ---
優先度: Normal — チケット対応中。担当者に割り当て。
--- 行4: 担当者が解決 ---
優先度: Normal — チケット解決済み。クローズしました。
--- 行5: 鈴木が再オープン ---
優先度: Normal — チケット受付中。
--- 変更要求: 田中（corporate）を保留中で受付 ---
優先度: High — 保留中。理由を記録します。

--- チケットイベントログ ---
[USR003] 鈴木 次郎 チケット作成 (Normal)
[USR002] 佐藤 花子 チケット作成 (High)
[USR003] 鈴木 次郎 アサイン (Normal)
[USR003] 鈴木 次郎 解決 (Normal)
[USR003] 鈴木 次郎 再オープン (Normal)
[USR001] 田中 一郎 保留 (High)
```

動作テーブルの行1〜5（状態遷移の基本フロー）に加え、フェーズ3の変更途中コードと同じ「法人ユーザーはHigh」「保留中は理由を記録する」を確認できます。行6（エスカレーション）はフェーズ1の現状コードで示した動作であり、フェーズ7のルール差し替え構造 × 状態分離構造では各Phaseの `display()` を拡張することで対応できます。

`TicketApplication` は初期状態と優先度ルールの組み立てを担当し、`main()` は起動だけを担います。ただし、具体状態への遷移先は各Phaseクラスにも記述されています。初期状態や注入するルール差し替え構造を替える変更は `TicketApplication`、状態遷移ルールを替える変更は関係するPhase、共通契約を替える変更は利用側も含めて修正します。

---

#### 解決後のクラス構成

```mermaid
classDiagram
    class TicketContext
    class ITicketPhase { <<interface>> }
    class OpenPhase
    class InProgressPhase
    class ResolvedPhase
    class PendingPhase
    class IPriorityRule { <<interface>> }
    class PremiumPriority
    class NormalPriority
    class CorporatePriority
    TicketContext o--> ITicketPhase
    ITicketPhase <|.. OpenPhase
    ITicketPhase <|.. InProgressPhase
    ITicketPhase <|.. ResolvedPhase
    ITicketPhase <|.. PendingPhase
    TicketContext --> IPriorityRule
    IPriorityRule <|.. PremiumPriority
    IPriorityRule <|.. NormalPriority
    IPriorityRule <|.. CorporatePriority
```

完成後はStateで進行状態を、Strategyで優先度判定を分離します。章末の抽象図と比べると、`TicketContext` が両構造のContextを担うことが分かります。

### 7-2：動作シーケンス図

ステップ5で到達したルール差し替え構造 × 状態分離構造の実行時のオブジェクト間のやり取りを可視化します。`TicketApplication` が依存関係を注入し、`TicketContext` が具象クラスを知らずに抽象インターフェース経由で処理を委譲する流れが確認できます。

```mermaid
sequenceDiagram
    participant App as TicketApplication
    participant TM as TicketContext
    participant PS as PendingPhase
    participant CP as CorporatePriority
    Note over App: 組み立てと実行
    App->>PS: new PendingPhase()
    App->>CP: new CorporatePriority()
    App->>TM: new TicketContext(&state, &strategy)
    App->>TM: execute(...)
    TM->>CP: strategy->getPriority("corporate")
    Note right of TM: IPriorityRule* 経由
    CP-->>TM: "High"
    TM->>PS: state->display()
    Note right of TM: ITicketPhase* 経由
    PS-->>TM: "保留中。理由を記録します。"
    TM-->>App: 完了
```

---

### 7-3：変更影響グラフ（改善後）

フェーズ3と同じ「SLAルール変更」や「状態追加」を試みます。

```mermaid
graph LR
    T1["変更要求：法人向けSLAルール"] --> F1["CorporatePriorityクラス ✅"]
    T1 -. "影響なし" .-> A["TicketContext ✅"]
    T2["変更要求：保留中状態追加"] --> F2["PendingPhaseクラス ✅"]
    T2 -. "影響なし" .-> A
```

フェーズ3のグラフと比較して、変更要求がそれぞれ独立したクラスに閉じるようになり、`TicketContext` への飛び火がなくなりました。

### 7-4：変更シナリオ表

フェーズ1の現状コードと改善後で、変更の影響がどう変わるかを対比します。

| **シナリオ** | **フェーズ1の現状コードでの影響** | **この設計での影響** |
| --- | --- | --- |
| 新しい状態（保留中）を追加 | `TicketManager` の条件分岐に新状態の処理を追加 | `PendingPhase` クラスを新規作成し、遷移ルールを設定する |
| 法人向けSLA優先度ルールを追加 | `TicketManager` の if-else ロジックを修正 | `CorporatePriority` クラスと組み立てを追加。状態クラスは保つ |
| ベンダー確認中状態を追加 | `TicketManager` の条件分岐と既存状態を確認 | `VendorWaitingPhase` クラスと遷移の組み立てを追加。優先度ルールは保つ |
| 状態遷移のルールを変更 | `TicketManager` の遷移条件を修正 | 対象の Phase クラスのみ修正 |

フェーズ1の現状コードでは状態の追加や優先度ルールの変更のたびに `TicketManager` 本体を直接修正する必要がありました。改善後は `TicketContext` に触れず、対象の Phase クラスまたは ルール差し替え構造（優先度ルール）クラスだけを変えれば済みます——それがこの設計で手に入れたものです。諦めたものは、インターフェースやクラスの増加というわずかな設計コストです。


---

## 整理

### 問題・原因・課題・解決策

| | 内容 |
|---|---|
| **問題** | チケット管理で「優先度ルールの変更」と「状態遷移の追加」という変わる理由が異なる2つの変化が、同じ `TicketManager` に混在している |
| **原因** | `TicketManager` が `PriorityCalculator` と状態遷移ロジックを「クラス名と条件を呼び出し元が知る」で保持しているため、どちらの変化が来ても両方への影響確認が必要になる |
| **課題** | 状態ごとの振る舞い（接続点A）と優先度判定ロジック（接続点B）を、それぞれ独立して差し替えられる構造に切り離すこと |
| **解決策** | ルール差し替え構造 × 状態分離構造：`IPriorityRule`（優先度ルールの軸）と `ITicketPhase`（状態遷移の軸）の2つのインターフェースで変化軸を分離し、`TicketContext` はどちらの具体クラスも知らない設計にする |

### フェーズとこの章でやったこと

| **フェーズ** | **この章でやったこと** |
| --- | --- |
| 🔵 フェーズ1：現状把握 | チケット管理システムにおける状態遷移とルール判定の混在を観察した。仕様・動作例・コード・クラス構成図・変更要求を把握した |
| 🟣 フェーズ2：仮説立案 | 業務機能の所在表・変わる理由の分析で2つの変化軸を特定した。運用担当者へのヒアリングで、二つの軸（ルールと状態）が独立して変動することを確認した |
| 🟣 フェーズ3：問題特定 | `if-else` 分岐の肥大化による修正の連鎖という痛みを確認した |
| 🟠 フェーズ4：原因分析 | 振る舞いとルールの密結合を「直差し」状態として診断した |
| 🟡 フェーズ5：課題定義 | 状態とルールの二つの接続点を特定し、疎結合化を課題とした |
| 🔴 フェーズ6：対策検討 | 5ステップを比較し、ルール差し替え構造 × 状態分離構造（共通の契約だけを知る）を採用した |
| 🟢 フェーズ7：対策実施 | インターフェースを導入し、責務をクラスに分離した。シーケンス図・変更影響グラフ・変更シナリオ表で局所化を確認した |

### 責任の移動

| **責任** | **変更前** | **変更後** |
| --- | --- | --- |
| チケットの全体フロー管理 | `TicketManager` | `TicketContext`（変わらず） |
| 状態ごとの振る舞いの実装 | `TicketManager`（if-else直書き） | `OpenPhase` / `InProgressPhase` 等の各フェーズクラス |
| 優先度判定ルールの実装 | `TicketManager`（直書き） | `PremiumPriority` / `NormalPriority` 等の各ルールクラス |
| 状態遷移の契約定義 | —（なし） | `ITicketPhase` |
| 優先度判定の契約定義 | —（なし） | `IPriorityRule` |

### 使った構造 × 解消した根本原因

| **使った構造** | **解消した根本原因** |
| --- | --- |
| ルール差し替え構造（`IPriorityRule`） | 根本原因A：優先度ルールが `TicketManager` 内に混在し、SLA改定のたびに状態遷移ロジックまで再テストが必要だった |
| 状態分離構造（`ITicketPhase`） | 根本原因B：状態遷移ロジックが `TicketManager` 内に混在し、新状態を追加するたびに管理クラスへの修正が必要だった |

2つの構造はそれぞれ独立した根本原因を解消しています。どちらか一方だけでは、残った根本原因が将来の変更で痛みを生み続けます。

### 複雑度ストレス検証

今回足した複雑さが、どの原因に効き、どの課題を生み、最終的にどちらの軸の構造へ収まったかを対応させます。2軸以上の変化が重なっても、軸を分ければ複数構造へ自然に進められることの確認です。

| 追加した複雑さ | 見えた原因 | 定めた課題 | 採用した扱い（2軸分離） |
|---|---|---|---|
| SLAタイマー | 期限超過の判定が優先度と一緒に本体へ入る | 期限を優先度ルール側へ寄せる | ルール軸（`IPriorityRule`）で判定する |
| 担当者割当イベント | 割当契機が状態遷移の分岐へ埋もれる | 契機と状態遷移を分けて扱う | 状態軸（`ITicketPhase`）の遷移で扱う |
| 再オープン | 逆流時に状態とルールが同じ行で動く | 逆流時も両軸を独立に動かす | 状態軸で遷移し、ルール軸で再評価する |
| 状態とルールの同時変化 | 同時に動くため1軸へまとめたくなる | 同時でも軸ごとに振り分ける | 組み立て側が両軸を順に呼び分ける |

---

## 振り返り

### 「この章を読むと得られること」は手に入ったか

| **得られること** | **この章のどこで示したか** |
| --- | --- |
| 1. 変動箇所の識別力 | フェーズ2の業務機能の所在表・変わる理由の分析でルールと状態を変動要因として特定した |
| 2. 接続点の診断力 | フェーズ4の原因分析で、状態遷移と優先度判定の知識が `TicketManager` に集まっている状態を診断した |
| 3. 構造改善の説明力 | フェーズ7の変更シナリオ表で、変更が独立クラスに閉じる構造を示した |
| 4. if文からオブジェクトへの変換視点 | フェーズ6の5ステップで、関数化の限界からインターフェース化への変換プロセスを示した |

### 3つの設計原則はどう適用されたか

**原則1「変わるものをカプセル化せよ」の現れ**

- 具体化された場所：各 `IPriorityRule` および `ITicketPhase` の実装クラス
- 解説：変化するロジックを個別のクラスへ追い出し、`TicketContext` から切り離しました。新しいルールや状態が追加されても `TicketContext` は無影響です。

**原則2「実装ではなくインターフェースに対してプログラムせよ」の現れ**

- 具体化された場所：`IPriorityRule`, `ITicketPhase`
- 解説：統括クラスは具体的なアルゴリズムや状態を知らず、インターフェース経由で呼び出します。既存の契約に収まる優先度ルールや状態を差し替える場合、`TicketContext` の委譲ロジックは保てます。新しい操作や遷移用の契約が必要になれば、インターフェースとContextも見直します。

**原則3「継承よりコンポジションを優先せよ」の現れ**

- 具体化された場所：`TicketContext` が ルール差し替え構造 と 状態分離構造 を保持する構成
- 解説：ロジックの振る舞いを継承ではなく、保持するオブジェクトの差し替えによって実現しました。継承だけで「状態×優先度ルール」の全組み合わせを表すと、状態3種類×優先度ルール3種類で9クラスになります。状態やルールが増えるたびに組み合わせクラスも増える、二次元的な膨張が起きます。コンポジションなら、状態クラスまたはルールクラスと、それらを結び付ける組み立て箇所を変更できます。

---

## あなたのコードで考えてみてください

この章で辿った思考プロセスを、あなた自身のコードに当てはめてみましょう。

1. **複数の変動軸を探す：** あなたのコードに「振る舞いが変わる理由が2つ以上、同じクラスに混在している」箇所がありますか？「状態によって処理が変わる」と「ビジネスルールによって処理が変わる」が同居していませんか？**判断基準：** そのクラスの変更理由を1文で書こうとして「AまたはBが変わったとき」という形になるなら、変動軸が混在しています。
2. **変わる理由を分ける：** そのクラスの変更要求が来たとき、担当者は何人いますか？異なる担当者の判断が1か所に混在しているなら、分けるサインです。**判断基準：** git blameで「このメソッドは営業が要求した変更で前回修正、前々回はシステムチームの要件で修正」となっていれば、2つの責任が混在しています。
3. **爆発を想像する：** 状態の種類が3つ→5つ、ルールの種類が2つ→4つになったとき、今の構造ではメソッド数はどのくらい増えますか？それは管理できる範囲ですか？**判断基準：** 「状態×ルール数」のかけ算でメソッドや分岐が増えるなら爆発します。足し算で済むなら許容範囲です。
4. **分けた後を想像する：** 「状態の遷移ロジック」と「ビジネスルール」をそれぞれ別クラスに切り出したとき、新しい状態を追加するとき触るファイルはどこだけになりますか？**判断基準：** 「1ファイルだけ」が答えなら設計が機能しています。「複数ファイル」が答えなら、まだ依存が残っています。

---

**題材を置き換えるときの共通手順**

この章の題材名を、自分の現場のシステム名に置き換えて考えます。

1. そのシステムは、誰が何を達成するために使うものか。
2. 入力、加工、出力は何か。
3. 最近入った変更要求、または次に来そうな変更要求は何か。
4. その変更で、触りたくない場所まで修正や再テストが広がるか。
5. 変えたいものと守りたいものを分けると、接続点には何を残すべきか。
6. 何もしない、関数化、クラス分離、契約導入、登録/組み立て移動のうち、どこまで進めるのが今回の文脈に合うか。

## パターン解説：Strategy × State

この複合パターンは、ビジネス上の「アルゴリズム（戦略）」と「状態（状態遷移）」が独立して変化する際、それぞれをパターンの対象とすることで、爆発的な分岐を整理する強力なアプローチです。

> [!INFO] コラム: StrategyとState、似ているけれど何が違う？
> どちらのパターンも「インターフェースを使って具体的な振る舞いを切り替える」という構造は同じです。しかし、目的（意図）が異なります。Strategyは「優先度計算」のような特定のアルゴリズムを差し替えるためのものですが、Stateは「受付中」「対応中」といったオブジェクトのライフサイクル（状態）を表現するためのものです。構造が同じでも、変更理由の種類が違うため別々に扱う必要があります。

### 抽象骨格の実行シーケンス

```mermaid
sequenceDiagram
    participant C as Client
    participant X as Context
    participant S as State
    participant R as Strategy
    C->>X: event(input)
    X->>S: handle(Context, input)
    S->>R: evaluate(input)
    R-->>S: 判定結果
    S->>X: setState(next)
    X-->>C: 状態・優先度
```

Stateが状態固有の処理を選び、その中の独立して変わる判定をStrategyへ委譲します。

### この章の実装との対応

GoF（Gang of Four）とは、1994年に出版された書籍『Design Patterns』の4人の著者の総称です。彼らが整理した23のパターンは、現在も設計の共通言語として広く使われています。

**Strategyパターン（GoF標準）：**

```mermaid
classDiagram
    class Context {
        -strategy: IStrategy
        +setStrategy(s: IStrategy)
        +doWork()
    }
    class IStrategy {
        <<interface>>
        +execute()
    }
    class ConcreteStrategyA {
        +execute()
    }
    class ConcreteStrategyB {
        +execute()
    }
    Context --> IStrategy
    IStrategy <|.. ConcreteStrategyA
    IStrategy <|.. ConcreteStrategyB
```

| GoFの名前 | この章での対応 |
| --- | --- |
| Context | `TicketContext` |
| Strategy | `IPriorityRule` |
| ConcreteStrategyA | `PremiumPriority` |
| ConcreteStrategyB | `NormalPriority` |

**Stateパターン（GoF標準）：**

```mermaid
classDiagram
    class Context {
        -state: IState
        +setState(s: IState)
        +request()
    }
    class IState {
        <<interface>>
        +handle(context: Context)
    }
    class ConcreteStateA {
        +handle(context: Context)
    }
    class ConcreteStateB {
        +handle(context: Context)
    }
    Context --> IState
    IState <|.. ConcreteStateA
    IState <|.. ConcreteStateB
```

| GoFの名前 | この章での対応 |
| --- | --- |
| Context | `TicketContext` |
| IState | `ITicketPhase` |
| ConcreteStateA | `OpenPhase` |
| ConcreteStateB | `InProgressPhase` |

### 使いどころと限界

- **使うと良い：** 状態遷移が複雑で、さらにその状態ごとのルールが頻繁に変わるような大規模なワークフロー管理。または「変わる理由が2種類あり、それぞれ異なる担当者が変更を決定する」ことがヒアリングで確認された場合。
- **使わない方が良い：** シンプルな遷移であれば `if-else` の方が可読性が高いこともあります。判断基準として以下を確認してください。① 状態が2種類以下かつ今後増える予定がない、② ビジネスルールが1種類だけで四半期改定などの変更予定がない、③ 担当者が1人（変更の判断者が1人）——この3条件をすべて満たすなら、パターン適用はやりすぎです。1つでも満たさない場合は、将来のクラス爆発を避けるためにパターン適用を検討してください。

【過剰コード：シンプルなものまで無理に分離した例】

状態が「Open」「Closed」の2つだけで、ルールも「ハイか否か」1種類だけのシンプルなシステムにStrategy × Stateを適用すると、クラス爆発が起きます。

```cpp
// 【過剰コード】状態2種類・ルール1種類のみのシンプルなシステムに
// Strategy × State を適用した場合の例

// ── Strategy側（ルール1種類だけなのにインターフェースを定義）
class IPriorityRule {
public:
    virtual ~IPriorityRule() = default;
    virtual string getPriority() = 0;
};
class SinglePriority : public IPriorityRule { // ← 実装クラスが1つだけ
public:
    string getPriority() override { return "Normal"; }
};

// ── State側（状態2種類のみなのにインターフェースを定義）
class ISimpleState {
public:
    virtual ~ISimpleState() = default;
    virtual void handle() = 0;
};
class OpenState : public ISimpleState {  // ← 状態クラスが2つだけ
public:
    void handle() override { cout << "Open" << endl; }
};
class ClosedState : public ISimpleState {
public:
    void handle() override { cout << "Closed" << endl; }
};

// ── 合計5クラス + 2インターフェース。if-else 2行で書けた処理が
//    7つのクラスに分散し、次に触る人は全クラスを読まないと
//    「何をしているか」を理解できなくなる。
```

これを素直に書くと次のように2行で済みます。

```cpp
// シンプルな if-else の方が読みやすい場合
void updateStatus(string status) {
    if (status == "Open") cout << "Open" << endl;
    else cout << "Closed" << endl;
}
```

「状態が2つ以下・ルールが1種類」という条件では、パターン適用はクラス数を増やすだけで変更耐性の恩恵がありません。変化の見込みがないなら、シンプルな実装が一つの考え方です。

### この章のまとめ

チケット管理というドメインと Strategy × State の組み合わせの関係を一言で言うなら、「優先度ルール」と「状態遷移」は変わる速度も担当者も違う2つの変化軸であり、それぞれに別の境界を設けることで変更影響を分けやすくなる、ということです。先にパターン名を選ぶのではなく、問題を分析した結果がStrategyとStateの役割に対応した——この順序が、第二部を通じて最も伝えたいことです。

7つのフェーズを通じて、読者は1つのクラスに混在する2つの変化軸という観察から始まり、「変わる速度と担当者が違うならば分けるべき」という分析を経て、軸ごとに異なるパターンを当てるという判断へと進みました。フェーズ4で「優先度ルール」と「状態遷移」が独立した接続点を持つことが確認された時点で、1つのパターンでは解決しきれないことが見えました。その「解決しきれない」という気づきこそが、2つ目のパターンへ進む根拠になります。フェーズ6の5ステップで段階的に進化させた思考の流れは、複合問題に直面したときの手順として、このまま現場で使えると思っています。

あなたのコードの中にも、「どの業務機能に属するか」が異なる2つのロジックが同じクラスに同居している箇所があるはずです。それぞれの変化軸を問うことが、どのパターンをどこに当てるかを見つける入口になります。
