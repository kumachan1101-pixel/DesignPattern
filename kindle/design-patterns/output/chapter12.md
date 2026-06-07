## 第12章 承認ワークフローシステム ―― 状態変化・通知・判定ルールが絡む複合設計

―― 思考の型：複雑な承認プロセスと変化し続ける通知ルールをどう疎結合にするか

### この章の核心

**承認ワークフローのような「状態遷移」を伴う業務システムにおいて、各状態での挙動や通知ロジックを条件分岐で管理しようとすると、状態が増えるたびにコードの依存関係が爆発し、修正が極めて困難な「硬いシステム」になってしまう。**

### この章を読むと得られること

* **得られること1：** 承認状態の変化、関係者への通知、承認可否のルールという、それぞれ異なる「変わる理由」を識別できるようになる。


* **得られること2：** 状態遷移とアクションが「密結合」（複数の責務が一か所に混在し、一方を変えると他方まで影響を受ける状態）になっている接続点（クラスとクラスのつなぎ目）を特定し、問題の発生源を見極められるようになる。


* **得られること3：** 複数の構造を組み合わせることで、複雑なワークフローを疎結合（変更の影響が特定のクラスだけに閉じる状態）に保ちつつ、新しい承認フローにも対応できる設計手法を説明できるようになる。


* **得られること4：** 「状態管理」「通知」「判定ルール」が絡み合う現場で、変更影響を局所化する視点を養う。

---

## 🔵 フェーズ1：現状把握 ―― 変更が来る前にコードを把握する

### 1-1：システムの背景

このシステムは、企業内の稟議や経費精算を管理する「承認ワークフローシステム」です。 申請者が申請を作成し、上長や経理担当者が内容を確認・承認するプロセスをデジタル化し、効率的に管理することを目的としています。

リリース当初は「作成」「承認」「却下」という3つの状態のみを扱うシンプルなものでした。 しかし、組織の拡大に伴い「金額に応じた承認者の自動割り当て」「承認プロセス中の関係者への通知」「特定の部署のみ適用される特別な承認ルール」といった要件が次々と追加されています。

現場の担当者からは「承認ルールを一つ変えるだけで、ワークフロー全体のステータス管理を書き直さなければならない」という悲鳴が上がっています。 私自身、このコードを最初に開いたとき、状態遷移のロジック、通知先の一覧、そして判定ルールが巨大なクラスの中に複雑に絡み合っているのを見て、どこから手をつければいいのか言葉を失いました。 一見すると、承認という一連の業務フローは安定しているように見えますが、内側では小さな修正が全体に影響を与える「脆い構造」が構築されています。

### 1-2：仕様表


**承認ワークフロールール**

| ルール名 | 発動条件 | 結果 | 具体例 |
| --- | --- | --- | --- |
| 状態遷移 | 申請ステータスが変化する時（提出・承認・却下） | 次の状態へ移行し、対応する処理を実行 | ステータス="SUBMITTED" → 承認待ち状態へ移行 |
| 承認可否判定 | 承認者が操作した時（金額・役職に基づく） | 承認または却下の判定結果を返す | 金額 > 100,000円 → 役員承認が必要と判定 |
| 完了通知 | 各状態遷移が完了した時 | 登録済みの関係者全員へ承認状況を送信 | 承認完了 → 申請者・経理部門へ通知 |

**このルールを使う場所**

同じ承認処理を2か所で使います。この「2か所で使う」という仕様が、設計の違いを生む起点になります。

| 使用場所 | 用途 |
| --- | --- |
| `WorkflowManager` | ユーザーの申請・承認操作を処理する通常フロー |
| `EscalationEngine` | 期限超過申請を自動的にエスカレーションする自動フロー |

### 1-3：動作例テーブル

仕様表を読んだだけでは「実際にどう動くか」が見えにくいことがあります。コードを読む前に、代表的な入力パターンとその結果を確認しておきましょう。この表が、のちの設計選択の「共通のものさし」になります。

| 操作（入力） | 申請種別 | 結果の状態 | 通知先 |
| --- | --- | --- | --- |
| 申請書提出 | 通常申請 | 審査待ち状態へ移行 | 担当者に通知 |
| 申請書提出 | 緊急申請 | 優先審査待ちへ移行 | 管理者に通知 |
| 審査待ち + 承認操作 | — | 承認済み状態へ移行 | 申請者・次承認者に通知 |
| 審査待ち + 却下操作 | — | 却下状態へ移行 | 申請者に通知 |
| 承認済み + 最終承認操作 | — | 完了状態へ移行 | 全関係者に通知 |
| 却下状態 + 再申請操作 | — | 審査待ち状態に戻る | 担当者に通知 |

どの案を選んでも、この6行の動作を実現します。設計の違いは「変更が来たときにどこを触ることになるか」だけです。

### 1-4：クラス構成図

現状のクラス構成です。 ワークフローの制御主体である `WorkflowManager` にすべての責務が集中しています。

```mermaid
classDiagram
    class WorkflowManager {
        +process(request)
        +notifyStakeholders()
        +checkApprovalRule()
    }
    class Approver {
        +role
        +limit
    }
    WorkflowManager --> Approver : manages

```

`WorkflowManager` クラスが、ワークフローの「状態遷移」、各担当者への「通知」、「承認可否のルール判定」という3つの重い責務をすべて握りしめています。

### 1-5：責任配置テーブル

| **クラス名** | **責任（1文）** | **知るべきこと** |
| --- | --- | --- |
| `WorkflowManager` | 承認ワークフローの全体フローを統括する。 | 状態遷移ルール、通知先一覧、承認判定基準。 |
| `Approver` | 承認者個人の情報を管理する。 | 承認者の役職や承認上限額。 |

`WorkflowManager` は、ワークフローのフローそのものだけでなく、誰にどう通知するか、どう判定するかという個別の詳細までを知りすぎている状態です。

### 1-6：依存グラフ

```mermaid
graph TD
    WorkflowManager --> Approver

```

`WorkflowManager` に責務と依存が集中しており、このクラスを修正しないと何も変えられない「単一障害点」の構造になっています。

### 1-7：実装コード

現在の承認処理のコア部分です。

**Approver クラス**

```cpp
#include <iostream>
#include <string>

using namespace std;

// 承認者クラス
class Approver {
public:
    string role;
    double limit;
};

```

**WorkflowManager クラス（状態遷移・通知・ルール判定が混在）**

```cpp
// ワークフロー管理クラス（状態遷移、通知、ルール判定が混在）
class WorkflowManager {
public:
    void process(string status, double amount) {
        if (status == "SUBMITTED") {
            cout << "承認待ち状態へ移行。" << endl;
            notify("申請者に通知");
        } else if (status == "APPROVED") {
            cout << "承認完了状態へ移行。" << endl;
            notify("関係者に通知");
        }
        // 判定ルール（ハードコード）
        if (amount > 100000) cout << "役員承認が必要。" << endl;
    }
private:
    void notify(string msg) { cout << msg << endl; }
};

```

**main()**

```cpp
int main() {
    WorkflowManager wm;
    wm.process("SUBMITTED", 50000);
    return 0;
}

```

このコードを見ると、`WorkflowManager` が「状態の遷移処理」「通知の仕組み」「金額による判定ルール」のすべてを直接知っていることが分かります。

### 1-8：実行結果

上記コードの実行結果：
承認待ち状態へ移行。
申請者に通知

```

このコードは正しく動いています。これから検討するのは、同じ機能を保ちながら、変更に強い構造をどう作るかという点です。

### 1-9：責任チェック表

| **コードの行** | **持っている知識** | **管理者（観察）** |
| --- | --- | --- |
| `if (status == "SUBMITTED")` | 状態遷移のルール | フロー設計担当 |
| `notify("申請者に通知")` | 通知の仕組み | 通知サービス担当 |
| `if (amount > 100000)` | 承認の判定ルール | 経理ルール担当 |

> 複数の部門が関わる知識が同じ `WorkflowManager` 内に混在しており、状態遷移、通知、判定ルールという変化の理由が異なる要素が同じ場所に並んでいることが見えました。
> 
> 

フェーズ1で責任配置の観察が終わりました。 次のフェーズ2では、変更要求を受けて「何が変わり、何が変わらないか」の仮説を立てます。

---

## 🟣 フェーズ2：仮説立案 ―― 変更要求を受けて、変動と不変を整理する

### 2-1：届いた変更要求

ある金曜日の夕方、経理部のマネージャーがデスクにやってきました。

「お疲れ様。今度、承認ワークフローに『緊急申請ルート』を追加することになったんだ。 通常は平社員→課長→部長という承認順序なんだけど、緊急時は課長を飛ばして直接部長に通知が飛ぶようにしたい。 それと、部長が承認した直後に、自動的に『決済部門』へも通知が飛ぶようにしてほしいんだよね。 承認が却下された場合も、申請者に即座にアラートを出す仕組みは必須だよ。いつまでに対応できるかな？」

ふむ、なるほど。 承認ルートのスキップや、特定の状態での追加通知、そして却下時の通知強化と、ワークフローの柔軟性を高める要求ですね。 今の `WorkflowManager` にこれらを付け足すと、さらに条件分岐が複雑化し、修正が困難になる予感がします。

### 2-2：変動・不変の仮説テーブル

フェーズ1の観察（1-9の責任チェック表）を材料に、何が変動し、何が変わらないのかの仮説を立てます。

| **分類** | **仮説** | **根拠（フェーズ1の観察から）** |
| --- | --- | --- |
| 🔴 **変動しそう** | 承認ルートの遷移順序 | 1-9で状態遷移ルールがハードコードされていると観察したため。 |
| 🔴 **変動しそう** | 承認時の通知先リスト | 1-9で通知ロジックが固定されていると観察したため。 |
| 🔴 **変動しそう** | 金額に応じた判定ルール | 1-9で判定ロジックが混在していると観察したため。 |
| 🟢 **不変** | ワークフローシステム自体の存在意義 | 申請と承認という業務プロセス自体は不変のため。 |

コードを読んだだけで「変わる」「変わらない」と断定するのは危険です。 関係者に直接確認します。

### 2-3：関係者ヒアリング

仮説を持って、ワークフローの運用担当者と話し合いを持ちました。

* **開発者：** 「今回のような『緊急ルート』以外にも、今後別の承認ルートが追加される可能性はありますか？」


* **運用担当者：** 「ああ、あるね。 例えば、海外出張時だけの特殊ルートや、特定のプロジェクト限定の承認フローなども、今後は必要になるだろうな。」


* **開発者：** 「通知についても確認させてください。現状は『申請者』と『関係者』だけですが、承認プロセスに応じて通知先の役職が変わったりする要件はありますか？」


* **運用担当者：** 「それも重要だ。 部長が承認したら経理だけでなく、関連部署の担当者にもメールを飛ばしたいケースが多いね。」


* **開発者：** 「分かりました。状態遷移ルール、通知の送り先、判定ロジックを、すべて現在の `WorkflowManager` から切り離し、動的に組み合わせられる構造を目指すのが良さそうです。」

> **現実のヒアリングでは——** このシナリオでは相手がちょうど設計に役立つ情報を教えてくれています。現実には「変わるかどうか分からない」「たぶん変わらない」という答えが返ることも多いです。そのときは、コードの変更履歴（`git log`）や過去の障害記録を「ヒアリングの代わり」として使ってみてください。「過去に何度変わったか」が、「将来変わりやすいか」の最も正直な証拠です。

### 2-4：今回の確定変更テーブル

ヒアリングで「今回の変更要求として確実に変わること」が判明しました。これは今回のリファクタリングで必ず対応しなければならない内容です。

| **具体的な内容** | **変わるタイミング** | **根拠（誰との確認か）** |
| --- | --- | --- |
| 承認状態の遷移ルール（ルートスキップ等） | 承認フロー変更時 | 運用担当者との合意 |
| ステータス通知先リスト | 通知要件変更時 | 運用担当者との合意 |
| 金額等による判定ルール | 経理ルール変更時 | 運用担当者との合意 |

### 2-5：将来リスクテーブル

ヒアリングで「今回の変更ではないが、今後変わる可能性がある」として言及されたリスクです。確定変更と混在させずに別で管理することで、設計の根拠を明確に保てます。

| **変化リスク** | **言及内容** | **設計への影響** |
| --- | --- | --- |
| 承認ルートの多様化 | 海外出張時の特殊ルート、プロジェクト限定フローなどが今後必要になる可能性 | 状態遷移ロジックを外部から差し替えられる構造が望ましい |
| 通知先の拡張 | 部長承認後に経理以外の関連部署にも通知したいケースが増える可能性 | 通知先をリストとして管理し、追加が容易な構造が望ましい |

フェーズ2で「何が変わり、何が変わらないか」が確定しました。 次のフェーズ3では、この変更要求を実際に今のコードのままで試みて、どのような痛みが生じるかを確認します。

---

## 🟣 フェーズ3：問題特定 ―― 変更を試みて、痛みを発見する

### 3-1：変更シミュレーション

フェーズ2で確定した「緊急申請ルートの追加」と「承認直後の自動通知」という変更要求を、現在の `WorkflowManager` クラスに実装してみます。

まず、`process` メソッド内の状態遷移ロジックに「緊急フラグ」の判定を追加しました。 すると、本来であれば課長を経由すべきルートが複雑に分岐し始め、`if` 文がネストしてコードの可読性が急速に低下していきます。 次に、承認直後の通知処理を追加しようとして、また別の `if` 文を差し込みました。

すると、承認プロセスが「承認」なのか「却下」なのか、あるいは「緊急」なのかというフラグが大量に混在し、どのタイミングでどの通知が飛ぶのかを追うのが非常に困難になりました。 「あ、これ以上 `WorkflowManager` をいじると、既存の承認ルートまで壊れてしまいそうだ…」という不安が頭をよぎります。 実際に、緊急ルートを追加したことで、通常の承認ルートにおける通知が二重に送信されるバグが発生してしまいました。

### 3-2：変更影響グラフ

今の構造で変更を試みた際に、依存がどのように飛び火するかを図示します。

```mermaid
graph LR
    T1["変更要求：緊急ルート追加"] -->|"ロジック修正"| B["WorkflowManager.cpp"]
    T2["変更要求：承認後通知追加"] -->|"ロジック修正"| B
    B -->|"影響が飛び火"| C["承認判定ルール ✅"]
    B -->|"影響が飛び火"| D["状態遷移ロジック ✅"]

```

`WorkflowManager` が状態遷移、通知、判定ルールのすべてを抱え込んでいるため、一つの機能をいじると、本来無関係なはずの判定ロジックまで影響を受けてしまうことが分かります。

### 3-3：痛みの言語化

「承認ルートを変えたいだけなのに、なぜ他の状態遷移まで気にしなければならないのか…」

変更をシミュレーションする中で、明確な痛みが二つ浮き彫りになりました。

一つ目の痛みは、「状態管理とアクションの密結合」です。 承認状態が増えるたびに `WorkflowManager` 内の `if-else` 分岐が指数関数的に増え、状態遷移のルールを把握するのが極めて困難になっています。 「ある状態で何ができるか」というルールが、他の状態の知識と混在しているため、変更が怖くて手が付けられない状態です。

二つ目の痛みは、「通知と判定の責務過多」です。 承認時の通知や判定といったビジネスルールが、ワークフローの実行フローと同じ場所に記述されているため、これら一つを修正するたびに、本来のワークフロー実行フローを読み解き、壊さないように注意を払うという多大な認知的負荷が生じています。 このような構造では、承認プロセスの複雑化に伴って開発コストが膨れ上がるのは避けられません。

フェーズ3で「今の構造では変更が辛い」という事実が確認できました。 次のフェーズ4では、なぜこのように辛いのか、構造的な原因を深掘りします。

---

## 🟠 フェーズ4：原因分析 ―― なぜ辛いのかを構造的に言語化する

フェーズ3で確認したように、「状態遷移」「通知先」「判定ルール」が `WorkflowManager` クラス内で混在していることが、システムを不安定にし、変更を困難にする最大の要因です。 この状態のまま拡張を繰り返すことは、複雑性の増大という負のスパイラルを招きます。

### 4-1：観察→原因テーブル

フェーズ3で確認された「痛み」と、その根本にある構造的な原因を対応させます。

| **観察** | **原因の方向** |
| --- | --- |
| 承認ルートや通知先の変更時に、`WorkflowManager` を広範囲に修正する必要がある | 状態管理、通知、判定ルールという「変わる理由」の異なる責務が、一つのクラス内に混在しているから。 |
| 状態が増えるたびに `if-else` 分岐が爆発的に増殖する | 状態ごとの振る舞いが個別の条件判定として記述されており、状態遷移のルールをカプセル化できていないから。 |

コードを追うと、`WorkflowManager` がワークフローの「フロー（骨格）」だけでなく、「個別のビジネスルール（判定）」や「付随するアクション（通知）」までを一身に背負っていることが分かります。

### 4-2：変わるもの / 変わらないものテーブル

構造を整理するために、変化の軸を明確に分離します。

| **変わり続けるもの（🔴）** | **変わってほしくないもの（🟢）** |
| --- | --- |
| 承認状態遷移のルール（ルート制御） | 申請・承認という業務プロセスの基本骨格 |
| 各状態における通知先リスト | 承認フローの実行順序（入口から出口までの流れ） |
| 金額や役職による承認可否判定 | 申請データが通過する状態遷移の基盤 |

現状では、「承認フローを動かす」という一つの目的に向かって、これら全ての要素が同じレイヤーで記述されています。 変化する「承認ルール」や「通知要件」は、基本フローの骨格から切り離し、独立して差し替え可能な部品として定義する必要があります。

### 4-3：接続形態を診断する

現在の接続形態を2×2マトリクスで診断します。

今の承認システムは、USB-Cハブの中に専用の変換回路を無理やりはんだ付けし、直接ケーブルを直差ししているような状態（具体×直接）です。 状態遷移ルールを変えたり通知先を増やしたりするたびに、この複雑に絡み合った「基板」そのものを直接加工しなければならないため、少しの修正がシステム全体を揺るがすリスクを孕んでいます。

|  | 直接（直差し） | 間接（アダプター経由） |
|:---:|:---|:---|
| **具体**（専用規格） | **← 現在地**　iPhone → [Lightning] → Apple純正ドック（Lightning端子） | iPhone → [Lightning] → [変換] → USB-A充電器（汎用端子） |
| **抽象**（汎用規格） | MacBook → [USB-C] → USB-C対応モニター（汎用端子） | MacBook → [USB-C] → [ハブ] → HDMI・USB-A・LAN |

このコードで言うと：

| ケーブル比喩 | コードの対応箇所 |
|---|---|
| 「具体」＝専用規格ケーブル | `if (status == "SUBMITTED")` / `if (amount > 100000)` — 承認ステータス文字列と金額閾値を `process()` に直接ハードコードしている |
| 「直接」＝直差し | 状態遷移・`notify()` 呼び出し・判定ルール（`if (amount > 100000)`）を `process()` 内にすべて直接記述しており、責務を分離する中間層がない |

「状態遷移ルール」「通知要件」「判定ロジック」は、それぞれが独立して頻繁に変更される可能性を秘めています。 これらを一つのクラスで混在させて管理するのではなく、インターフェースを介した接続形態へ分離することが、システムの設計を健全化する鍵となります。

フェーズ4で根本原因が言語化できました。 次のフェーズ5では、この分析を元に解決すべき課題を具体的に定義していきます。

---

## 🟡 フェーズ5：課題定義 ―― 解くべき問題を具体的に定める

フェーズ4で、「承認状態の変化」「関係者への通知」「承認可否のルール判定」という異なる性質を持つ3つの責務が `WorkflowManager` クラスに混在していることが、システムを硬直化させている原因であると特定しました。 この状態を放置すると、承認プロセスが複雑になるたびに修正コストが指数関数的に増大し、システムの保守は不可能に近くなります。

対策案を検討する前に、今回のリファクタリングで解決すべき課題を4つの視点で整理し、確定させます。

### 5-1：接続点の特定

フェーズ4での分析に基づき、以下の3つの接続点（ジョイント）を特定しました。

* 接続点A：`WorkflowManager` ←→ 状態遷移ルールの境界
* 接続点B：`WorkflowManager` ←→ 通知処理の境界
* 接続点C：`WorkflowManager` ←→ 承認可否判定ロジックの境界

これらは現状、`WorkflowManager` 内で一つの巨大な処理塊として絡み合っています。 これらを独立した接続点として切り離し、外部から差し替え可能な構造にすることが今回の最大の課題です。

### 5-2：非機能制約の確認

接続形態の検討に必要な制約を整理します。

| **確認項目** | **内容** | **この章での判断** |
| --- | --- | --- |
| 変更頻度 | この接続点はどのくらいの頻度で変わるか | 高（承認ルールや組織変更により頻繁に変わる） |
| パフォーマンス | ホットパスか（高頻度で呼ばれるか） | 低（ワークフローの承認は非同期・低頻度） |
| メモリ | 間接層の追加でオーバーヘッドが問題になるか | いいえ（柔軟性を優先） |
| 同時承認 | 複数の承認者が同じ申請を同時に操作するか | 要注意（複数の上長が同一申請の承認・差し戻しを同時に操作する可能性がある。承認状態の競合を防ぐため、排他制御または楽観的ロックによる整合性保証が必要で、これはWorkflowOrchestratorの設計に影響する） |

変更頻度が極めて「高」であるため、修正のたびにメインロジックを書き換える構造は避ける必要があります。 パフォーマンスへの制約が低いことから、インターフェースを多用し、実行時に動的な結合ができる「間接層」を積極的に導入することが合理的です。 また、複数の承認者が同一申請を同時操作するケースでは、状態遷移の競合を防ぐ排他制御の仕組みを設計段階で検討する必要があります。

### 5-3：クライアントへの影響範囲

分離対象の各処理を呼び出している `WorkflowManager` クラスが最大のクライアントです。 このクラスが各ロジックの詳細をすべて直接呼び出しているために、少しの要件変更でクラス全体を書き直さざるを得ません。 各責務を分離することで、`WorkflowManager` はワークフローの「骨格（実行順序）」のみを管理し、実際の判定や通知は分離した部品に任せることができます。

### 5-4：課題まとめ表

分析結果をまとめます。

| **接続点** | **分けた理由** | **非機能制約** | **クライアント影響** |
| --- | --- | --- | --- |
| 接続点A | 状態遷移ロジックの複雑化回避 | 変更頻度：高・複数承認者による同時操作時の競合制御がWorkflowOrchestrator設計に影響 | `WorkflowManager` の状態管理部 |
| 接続点B | 通知ルールの多様化対応 | 変更頻度：高 | `WorkflowManager` のイベント処理 |
| 接続点C | 承認ルール変更への追随 | 変更頻度：高 | `WorkflowManager` の判定処理 |

この表が、フェーズ6の対策案検討における出発点となります。 「状態管理」「通知」「ルール判定」をどのようにこれら3つの接続点に割り当て、分離するかが、本章の設計の核心です。

フェーズ5で「何を解くか」が確定しました。 次のフェーズ6では、これらの課題に対して具体的にどのような構造を適用するか、コストの観点から案を検討します。

---

## 🔴 フェーズ6：対策案検討 ―― 解決策を並べ、コストで選ぶ

フェーズ5で整理した「状態遷移」「通知」「判定ルール」という3つの接続点に対し、柔軟で変更に強い設計を検討します。

### 6-1：接続の形 2×2マトリクス

現在の承認システムは、すべての責務が `WorkflowManager` に詰め込まれた「具体×直接」の状態です。 これらを分離し、抽象インターフェースと間接層を導入することで、責務を切り出します。

| 接続形態 | ケーブル例 | 特徴 |
|:---:|:---|:---|
| **具体×直接**（← 現在地） | iPhone → [Lightning] → Apple純正ドック（Lightning端子） | 専用端子のみ対応。差し替え不可 |
| **具体×間接** | iPhone → [Lightning] → [変換] → USB-A充電器（汎用端子） | 変換器を挟むが規格は専用のまま |
| **抽象×直接** | MacBook → [USB-C] → USB-C対応モニター（汎用端子） | どのメーカーでも同じ口で繋がる |
| **抽象×間接** | MacBook → [USB-C] → [ハブ] → HDMI・USB-A・LAN | ハブを介して多様な機器へ展開可能 |

---

どの案も、動作例テーブルで示した動作を実現します。違うのは「変更が来たときにどこを触ることになるか」です。

---

#### 案1：現状のまま ―― 構造を変えない

**この形の考え方：**
クラス分割や抽象化を行わず、`if-else` 文を増やして対応します。 承認ルートが今後一切増えず、変更要求もこれ以上発生しないと断言できる場合にのみ合理的な選択です。

**構造図：**

```mermaid
classDiagram
    class WorkflowManager {
        <<if分岐を直書き>>
        +process(status, amount)
    }
    class EscalationEngine {
        <<同じif分岐が重複>>
        +escalateOverdue()
    }
    class Approver {
        +role
        +limit
    }
    WorkflowManager --> Approver : 具体×直接
    EscalationEngine --> Approver : 具体×直接
```

両クラスが状態チェックと通知ロジックを内部に直書きしており、承認ルールが変わると2か所を同時に修正しなければならない。

**手段比較：**

| 手段 | アプローチ | 採用するか |
| --- | --- | --- |
| 手段A：if-else を増やす | 既存の `process()` 内にフラグと分岐を追加 | 採用（最小コスト） |
| 手段B：メソッド抽出のみ | `notifyStakeholders()` などの private メソッドに切り出す | 不採用（呼び出し元の修正が依然必要） |

手段Aが最小コストですが、ルール変更のたびに `WorkflowManager` を直接修正しなければならない構造は変わりません。

【コード例】

```cpp
if (isEmergency) {
    status = "EMERGENCY";                  // ← 具体："EMERGENCY"という具体的な状態名を直接書いている
    notify("部長へ直接通知");               // ← 具体：通知先を具体的な文字列で直接書いている
}

```

**呼び出し側から見た違い（main() 例）：**

**EscalationEngine クラス（同じロジックが重複）**

```cpp
// 案1（現状のまま）の呼び出し側
// 両クラスが同じ承認状態チェック/ルールチェックのロジックを重複して持つ
class EscalationEngine {
public:
    void escalateOverdue() {
        // ← 具体：WorkflowManagerと同じif-else分岐をそのまま複製している
        if (amount > 100000) {
            cout << "役員承認が必要。エスカレーション実行。" << endl;
            notify("役員へ直接通知");
        }
    }
private:
    double amount = 150000;
    void notify(string msg) { cout << msg << endl; }
};

```

**main()**

```cpp
int main() {
    WorkflowManager wf;               // ← 直接：WorkflowManagerを直接生成して使う
    wf.process("SUBMITTED", 50000);   // ← 具体：内部にif-else分岐が直書きされている

    EscalationEngine engine;          // ← 直接：EscalationEngineも直接生成
    engine.escalateOverdue();
    // ← 具体：内部にWorkflowManagerと同じif-else分岐が重複している
    return 0;
}
```

両クラスが同じロジックを重複して持つため、ルールが変わると2か所を修正しなければならない。

一文要約：状態遷移・通知・判定ロジックが各クラスの内部に直書きされているため外部への呼び出しが発生せず、同じ条件分岐が2か所で並行して走る。

**この形のトレードオフ：**

* 変更容易性：低（変更のたびにメインロジックの修正が不可避）


* テスト容易性：低（状態と条件が密結合のため、特定経路のテストが困難）


* 実装コスト：低（今のコードに追記するだけ）



---

#### 案2：具体×直接 ―― クラスを分けるが参照は具体型のまま

**この形の考え方：**
状態遷移、通知、ルール判定を独立した責務としてクラス化し、`WorkflowManager` から切り出します。 ただし、`WorkflowManager` がそれらの具体クラスを直接保持・生成するため、疎結合化には至りません。

**構造図：**

```mermaid
classDiagram
    class WorkflowManager {
        +process(request)
    }
    class EscalationEngine {
        +escalateOverdue()
    }
    class RuleChecker {
        +isApproved(amount)
        +isOverdue()
    }
    class PendingPhase {
        +enter()
    }
    WorkflowManager --> RuleChecker : 具体×直接
    WorkflowManager --> PendingPhase : 具体×直接
    EscalationEngine --> RuleChecker : 具体×直接
    EscalationEngine --> PendingPhase : 具体×直接
```

クラスは分離されたが、`WorkflowManager` と `EscalationEngine` の両方が同じ具体クラスを直接参照しており、ルール変更時に両方の修正が必要になる。

**手段比較：**

| 手段 | アプローチ | 採用するか |
| --- | --- | --- |
| 手段A：クラス抽出のみ | ロジックを別クラスに切り出し、直接インスタンス化 | 採用（案1より責務が分かれる） |
| 手段B：静的メソッド化 | `RuleChecker::check(amount)` のように静的関数として定義 | 不採用（テスト時にスタブ化できない） |

手段Aを採用しますが、具体クラスを直接 `new` しているため、クラスを差し替えるには呼び出し元の修正が必要です。

【コード例】

**RuleChecker クラス・PendingPhase クラス**

```cpp
class RuleChecker {
public:
    bool isApproved(double amount) {
        return amount <= 100000; // ← 具体：判定ルールが直接書かれている
    }
    bool isOverdue() { return true; }
};

class PendingPhase {
public:
    void enter() {
        cout << "審査待ち状態へ移行。" << endl;
    }
};

```

**WorkflowManager クラス（具体型を直接使用）**

```cpp
void process(double amount) {
    RuleChecker checker; // ← 具体：RuleCheckerという型名を直接書いている
    if (checker.isApproved(amount)) {
        // ← 直接：呼び出し側がこのクラスを直接インスタンス化している
        cout << "承認完了。" << endl;
    }
}

```

**呼び出し側から見た違い（main() 例）：**

**EscalationEngine クラス（同じ選択ロジックが重複）**

```cpp
// 案2（具体×直接）の呼び出し側
// 選択ロジックが両クラスに重複している
class EscalationEngine {
public:
    void escalateOverdue() {
        RuleChecker checker; // ← 具体：RuleCheckerという型名を直接書いている
        PendingPhase pending; // ← 具体：PendingPhaseという型名を直接書いている
        if (checker.isOverdue()) {
            pending.enter();
            cout << "[EscalationEngine] 期限超過申請をエスカレーション。"
                 << endl;
        }
    }
};

```

**main()**

```cpp
int main() {
    WorkflowManager wf; // ← 直接：WorkflowManagerを直接生成して使う
    wf.process(50000); // ← 具体：内部でRuleCheckerが直接生成される

    EscalationEngine engine; // ← 直接：EscalationEngineも直接生成して使う
    engine.escalateOverdue();
    // ← 具体：内部で状態/ルールの具体クラスが直接生成される
    return 0;
}
```

選択ロジックが両クラスに重複しており、具体クラスへの依存が両方に残る。

一文要約：クラスは分かれたが「どのクラスを呼ぶか」という判断を両方の呼び出し元がそれぞれ行っており、判定クラスや状態クラスへの呼び出し経路が2本並んで重複している。

**この形のトレードオフ：**

* 変更容易性：低〜中（責務は分かれたが、利用側の修正は必要）


* テスト容易性：低（具体クラスへの強い依存が残る）


* 実装コスト：低（クラスの抽出のみ）



---

#### 案3：抽象×直接 ―― インターフェースを挟み、型だけで接続する

**この形の考え方：**
判定ルール、状態遷移の各責務にインターフェースを導入します。 インターフェースを介すことで、クラス間の依存を具体型から抽象型へ切り替え、差し替え可能にします。

**構造図：**

```mermaid
classDiagram
    class IApprovalRule {
        <<interface>>
        +canApprove(amount)
    }
    class IWorkflowPhase {
        <<interface>>
        +handle(wm)
    }
    class WorkflowManager {
        -rule IApprovalRule
        +process(amount)
    }
    class EscalationEngine {
        -rule IApprovalRule
        -state IWorkflowPhase
        +escalateOverdue()
    }
    class ManagerApprovalRule {
        +canApprove(amount)
    }
    class DirectorApprovalRule {
        +canApprove(amount)
    }
    class PendingPhase {
        +handle(wm)
    }
    ManagerApprovalRule ..|> IApprovalRule : 実装
    DirectorApprovalRule ..|> IApprovalRule : 実装
    PendingPhase ..|> IWorkflowPhase : 実装
    WorkflowManager --> IApprovalRule : 抽象×直接
    EscalationEngine --> IApprovalRule : 抽象×直接
    EscalationEngine --> IWorkflowPhase : 抽象×直接
```

`main()` が具体クラスを生成してインターフェース経由で注入するため、両クラスとも具体的な判定クラスや状態クラスを知らずに済み、選択ロジックの重複が解消される。

**手段比較：**

| 手段 | アプローチ | 採用するか |
| --- | --- | --- |
| 手段A：コンストラクタ注入 | 依存をコンストラクタ引数として受け取る | 採用（最も単純で明示的） |
| 手段B：セッター注入 | `setRule(IApprovalRule*)` のように後から差し込む | 不採用（初期化順序の管理が複雑になる） |
| 手段C：サービスロケーター | グローバルなレジストリから取得 | 不採用（依存が暗黙になりテストが困難） |

手段Aのコンストラクタ注入を採用します。依存が明示的になり、テスト時にスタブを渡しやすくなります。

【コード例】

**インターフェース定義**

```cpp
// 承認可否の判定ルール（インターフェース）
class IApprovalRule {
public:
    virtual bool canApprove(double amount) = 0;
};

// 状態遷移の抽象（インターフェース）
class IWorkflowPhase {
public:
    virtual void handle(class WorkflowManager* wm) = 0;
};

```

**判定ルールの実装クラス群**

```cpp
class ManagerApprovalRule : public IApprovalRule {
public:
    bool canApprove(double amount) override {
        return amount <= 500000; // ← 課長の承認上限
    }
};

class DirectorApprovalRule : public IApprovalRule {
public:
    bool canApprove(double amount) override {
        return amount <= 5000000; // ← 部長の承認上限
    }
};

```

**状態クラスの実装**

```cpp
class PendingPhase : public IWorkflowPhase {
public:
    void handle(WorkflowManager* wm) override {
        cout << "審査待ち状態で処理中。" << endl;
    }
};

```

**WorkflowManager クラス（抽象型で受け取る）**

```cpp
class WorkflowManager {
    IApprovalRule* rule; // ← 抽象：IApprovalRule*型で受け取り、具体クラスを知らない
public:
    WorkflowManager(IApprovalRule* r) : rule(r) {}
    void process(double amount) {
        if (rule->canApprove(amount)) {
            // ← 直接：中間クラスを挟まずに直接呼び出す
            cout << "承認完了。" << endl;
        } else {
            cout << "上位承認者へ転送。" << endl;
        }
    }
};

```

**呼び出し側から見た違い（main() 例）：**

**EscalationEngine クラス（インターフェース経由で注入）**

```cpp
// 案3（抽象×直接）の呼び出し側
// 注入アプローチにより、両クラスで選択ロジックの重複がなくなる
class EscalationEngine {
    IApprovalRule* rule;
    // ← 抽象：外部から注入されたインターフェースのみ知っている
    IWorkflowPhase* state;
    // ← 抽象：外部から注入されたインターフェースのみ知っている
public:
    EscalationEngine(IApprovalRule* r, IWorkflowPhase* st)
        : rule(r), state(st) {}
    void escalateOverdue() {
        cout << "[EscalationEngine] 期限超過申請を処理中。" << endl;
        state->handle(nullptr);
        // ← 直接：インターフェース経由で直接呼び出す
    }
};

```

**main()**

```cpp
int main() {
    ManagerApprovalRule rule;              // ← 具体：呼び出し側だけが具体クラスを生成
    WorkflowManager wf(&rule);            // ← 直接：インターフェース経由で直接注入
    wf.process(50000);

    DirectorApprovalRule esc_rule;
    PendingPhase esc_state;
    EscalationEngine engine(&esc_rule, &esc_state);
    // ← 直接：同様に注入
    engine.escalateOverdue();
    return 0;
}
```

注入アプローチにより、両クラスとも具体クラスを知らずに済み、選択ロジックの重複が解消される。

一文要約：`main()` が具体型を組み立て、両方の呼び出し元は `IApprovalRule*`・`IWorkflowPhase*` という型だけを介して呼ぶため、具体クラスが変わっても呼び出し経路は変わらない。

**この形のトレードオフ：**

* 変更容易性：中〜高（ルール差し替えがインターフェース経由で完結する）


* テスト容易性：高（判定ルールをスタブに差し替えてテスト可能）


* 実装コスト：中（インターフェースと複数の実装クラスが必要）

> **【案3の限界：通知の問題が残る】**
> 案3では「承認ルールの判定」と「状態遷移」を分離できますが、**承認結果を誰にどう通知するかという責務が `WorkflowManager` に残り続けます**。
>
> 「Slackにも通知してほしい」「却下時はメールも送ってほしい」という要求が来るたびに、`WorkflowManager` の通知ロジックを直接修正しなければなりません。通知先が増えるほどクラスが肥大化し、案3だけでは「判定ルールの変更」と「通知先の変更」を独立して扱えない構造が残ります。
>
> この「通知の変化軸」を分離するために、案4でさらに通知リスナーの仕組みが加わります。

---

#### 案4：抽象×間接 ―― インターフェース＋仲介役を両立する

**この形の考え方：**
状態遷移、ルール判定、通知を、それぞれインターフェース経由で仲介クラスに結合させます。 完全に疎結合となり、将来のあらゆる変更要求に対して、メインロジックを一切触らずに対応可能です。

**構造図：**

```mermaid
classDiagram
    class IPhaseFactory {
        <<interface>>
        +create(status) IState
    }
    class IWorkflowPhase {
        <<interface>>
        +handle(wm)
    }
    class IApprovalRule {
        <<interface>>
        +canApprove(amount)
    }
    class INotificationListener {
        <<interface>>
        +onStatusChanged(msg)
    }
    class WorkflowManager {
        -stateFactory IPhaseFactory
        -listeners INotificationListener[]
        +process(status)
    }
    class EscalationEngine {
        -stateFactory IPhaseFactory
        +escalateOverdue()
    }
    class ConcretePhaseFactory {
        +create(status) IState
    }
    ConcretePhaseFactory ..|> IPhaseFactory : 実装
    WorkflowManager --> IPhaseFactory : 抽象×間接
    WorkflowManager --> INotificationListener : 抽象×直接
    EscalationEngine --> IPhaseFactory : 抽象×間接
    ConcretePhaseFactory --> IWorkflowPhase : 抽象×直接
    IWorkflowPhase --> IApprovalRule : 抽象×直接
```

`WorkflowManager` は抽象ファクトリーのみを知り、状態クラスの具体型は `ConcretePhaseFactory` の内部に完全に隠蔽されるため、新しい状態を追加してもワークフロー本体への変更は不要となる。

**手段比較：**

| 手段 | アプローチ | 採用するか |
| --- | --- | --- |
| 手段A：ファクトリー＋リスナーリスト | 状態生成をファクトリーに委譲し、通知はリスナーリストで管理 | 採用（3つの変化軸すべてを独立して差し替え可能） |
| 手段B：ファクトリーのみ | 状態生成だけファクトリーに委譲し、通知は直書き | 不採用（通知の変化軸が残る） |
| 手段C：DIコンテナ | フレームワークに依存解決を委ねる | 不採用（本章のスコープ外。フレームワーク依存を避ける） |

手段Aを採用します。状態生成・判定ルール・通知の3つをすべて独立して差し替えられる唯一の構造です。

【コード例】

**インターフェース定義**

```cpp
// 状態遷移の抽象（インターフェース）
class IWorkflowPhase {
public:
    virtual void handle(class WorkflowManager* wm) = 0;
};

// 承認可否の判定ルール（インターフェース）
class IApprovalRule {
public:
    virtual bool canApprove(double amount) = 0;
};

// 通知リスナー（インターフェース）
class INotificationListener {
public:
    virtual void onStatusChanged(string msg) = 0;
};

// 状態生成ファクトリー（インターフェース）
class IPhaseFactory {
public:
    virtual IWorkflowPhase* create(string status) = 0;
};

```

**具体的な状態クラス群**

```cpp
class PendingPhase : public IWorkflowPhase {
public:
    void handle(WorkflowManager* wm) override {
        cout << "審査待ち状態で処理中。" << endl;
        // 判定ルールへの委譲はWorkflowManagerが保持するルールを使う
    }
};

class ApprovedState : public IWorkflowPhase {
public:
    void handle(WorkflowManager* wm) override {
        cout << "承認済み状態へ移行。" << endl;
    }
};

class RejectedState : public IWorkflowPhase {
public:
    void handle(WorkflowManager* wm) override {
        cout << "却下状態へ移行。" << endl;
    }
};

```

**ファクトリークラス（具体型の知識をここに封じ込める）**

```cpp
class ConcretePhaseFactory : public IPhaseFactory {
public:
    IWorkflowPhase* create(string status) override {
        if (status == "PENDING")   return new PendingPhase();
        if (status == "APPROVED")  return new ApprovedState();
        if (status == "REJECTED")  return new RejectedState();
        return nullptr;
    }
};

```

**WorkflowManager クラス（抽象ファクトリーとリスナーリストのみ知る）**

```cpp
#include <vector>
using namespace std;

class WorkflowManager {
    IPhaseFactory* stateFactory; // ← 抽象：IPhaseFactory*型で受け取り、具体実装を知らない
    vector<INotificationListener*> listeners;
public:
    WorkflowManager(IPhaseFactory* f) : stateFactory(f) {}

    void addListener(INotificationListener* listener) {
        listeners.push_back(listener);
    }

    void process(string status) {
        IWorkflowPhase* state = stateFactory->create(status);
        // ← 間接：Factory経由で呼ぶため具体クラスが見えない
        state->handle(this);
        notifyAll("状態変化: " + status);
    }

private:
    void notifyAll(string msg) {
        for (auto listener : listeners) {
            listener->onStatusChanged(msg);
        }
    }
};

```

**呼び出し側から見た違い（main() 例）：**

**通知リスナーの実装クラス**

```cpp
class EmailNotificationListener : public INotificationListener {
public:
    void onStatusChanged(string msg) override {
        cout << "[Email通知] " << msg << endl;
    }
};

class SlackNotificationListener : public INotificationListener {
public:
    void onStatusChanged(string msg) override {
        cout << "[Slack通知] " << msg << endl;
    }
};

```

**main()**

```cpp
// 案4（抽象×間接）の呼び出し側
int main() {
    ConcretePhaseFactory factory;         // ← 具体：組み立て側だけが具体型を知る
    WorkflowManager wf(&factory);         // ← 間接：抽象Factoryのみ見えて具体実装は隠れる

    EmailNotificationListener emailListener;
    SlackNotificationListener slackListener;
    wf.addListener(&emailListener);
    wf.addListener(&slackListener);

    wf.process("PENDING");
    return 0;
}
```

**動作図：**

```mermaid
sequenceDiagram
    participant main
    participant CSF as ConcretePhaseFactory
    participant WM as WorkflowManager
    participant EE as EscalationEngine
    participant PS as PendingPhase
    Note over main: 具体型を組み立てる唯一の場所
    main->>CSF: new ConcretePhaseFactory
    main->>WM: new（factory: IPhaseFactory*）
    main->>EE: new（factory: IPhaseFactory*）
    main->>WM: process("PENDING")
    WM->>CSF: stateFactory->create("PENDING")
    Note right of WM: IPhaseFactory* 経由
    CSF->>PS: new PendingPhase
    PS-->>CSF: 状態オブジェクト
    CSF-->>WM: IState*
    WM->>PS: state->handle(this)
    Note right of WM: IState* 経由
    PS-->>WM: 完了
    WM-->>main: 完了
    main->>EE: escalateOverdue()
    EE->>CSF: stateFactory->create("PENDING")
    Note right of EE: IPhaseFactory* 経由
    CSF-->>EE: IState*
    EE-->>main: 完了
```

一文要約：呼び出し元→`IPhaseFactory*`→`IState*` という2段階の抽象型を経由するため、どの具体クラスが動くかは `main()` の組み立て部分だけが知っている。

**この形のトレードオフ：**

* 変更容易性：高（どのパーツが変わっても全体は無影響）


* テスト容易性：高（すべての部品が独立してスタブ化可能）


* 実装コスト：高（インターフェース、ファクトリ、多数のクラスが必要）

---

### 6-2：評価軸

対策案を比較するための評価軸を宣言します。 承認フローの複雑化に対応しつつ、将来のルール変更に耐えうる設計を目指すための基準です。

| **評価軸** | **意味** | **ウェイト** |
| --- | --- | --- |
| 変更容易性 | 承認ルールや通知要件の変更に対し、触る場所が最小で済むか | ×3 |
| テスト容易性 | 判定ロジックや状態遷移を独立してテストできるか | ×2 |
| 可読性 | 複数の構造導入による理解コスト | ×1 |

> **注：** このウェイト（変更容易性×3など）は本書の例です。チームの変更頻度・テスト文化に合わせて、比較を始める前にチームで合意してください。スコアは「答えを決める計算式」ではなく、「チームの議論を整理する道具」です。

**採点基準：**

* **3点**：1クラスの修正で完結。スタブで完全に切り離し可能。クラス増なし。
* **2点**：2〜3クラスの修正。一部スタブが必要。標準的な構造。
* **1点**：4クラス以上の波及。テスト困難。中間層が多く理解コスト高。

パフォーマンスはバッチ処理のため VETO（足切り）は発動しません。

---

### 6-3：コスト天秤

案1〜案4を定量比較します。

| **案** | **現在の対応コスト** | **未来の対応コスト** |
| --- | --- | --- |
| 案1：現状のまま | 低 | 高 |
| 案2：具体×直接 | 低〜中 | 高 |
| 案3：抽象×直接 | 中 | 低〜中 |
| 案4：抽象×間接 | 高 | 低 |

**ステップ1：採点表**

| 案 | 変更容易性（×3） | テスト容易性（×2） | 可読性（×1） |
| --- | --- | --- | --- |
| 案1 | 1 | 1 | 3 |
| 案2 | 1 | 1 | 2 |
| 案3 | 2 | 2 | 2 |
| 案4 | 3 | 3 | 1 |

**ステップ2：加重合計表**

| 案 | 加重スコア | 判定 |
| --- | --- | --- |
| 案1 | 8 |  |
| 案2 | 7 |  |
| 案3 | 12 |  |
| 案4 | 16 | ← 採用候補 |

### 6-4：採用案の決定

**採用する案：** 案4（抽象×間接）

**理由：**
承認フローの「状態」「通知」「判定ルール」という3つの変動軸をすべて独立したインターフェースとして切り出すことで、将来的に組織変更やルール追加が発生しても、メインロジックを一切修正せずに拡張可能となるため、長期的な運用コストを最小化できると判断しました。

---

### 6-5：耐久テスト

フェーズ2で予告された変更要求に対する、採用案（案4）の耐性をテストします。

| **変更シナリオ** | **触る場所** | **コスト評価** |
| --- | --- | --- |
| 承認順序を役職ベースから金額ベースへ変更する | 新規判定ルールクラスの実装 | 低 |
| 承認却下時にSlackだけでなくメール通知を追加する | 新規リスナークラスの実装 | 低 |

採用した複合設計では、ルール判定も通知もインターフェース越しに結合されているため、新しい要件は新規クラスを追加するだけで対応でき、既存のワークフロー本体を触る必要がありません。

---

## 🟢 フェーズ7：対策実施 ―― 決断し、変化に強い設計を手に入れる

採用した案4を実装し、承認ワークフローの「状態」「判定」「通知」という3つの責務を疎結合に分離します。

フェーズ6で案4として選んだ構造は、「状態ごとの振る舞いをオブジェクトとして切り出す」手法、「判定ルールを外部から差し替え可能にする」手法、「状態変化を登録されたリスナーへ伝搬させる」手法の3つの仕組みを組み合わせた複合設計です。

### 7-1：解決後のコード（全体）

判定ルールを `IApprovalRule` として、状態遷移を `IWorkflowPhase` として、通知を `INotificationListener` として定義しました。 これらを `WorkflowManager` が保持・管理することで、複雑なワークフローを整理します。

**インターフェース定義（3つの変化軸）**

```cpp
#include <iostream>
#include <vector>

using namespace std;

// 判定ルールの契約（変わる理由：経理ルール変更）
class IApprovalRule {
public:
    virtual bool canApprove(double amount) = 0;
};

// 通知リスナーの契約（変わる理由：通知先変更）
class INotificationListener {
public:
    virtual void onStatusChanged(string msg) = 0;
};

// 状態遷移の契約（変わる理由：承認フロー変更）
class IWorkflowPhase {
public:
    virtual void handle(class WorkflowManager* wm) = 0;
};

```

**WorkflowManager クラス（骨格のみを担当）**

```cpp
// 最終的なワークフロー管理
class WorkflowManager {
    IWorkflowPhase* state; // ← ここだけ変わる
    vector<INotificationListener*> listeners;
public:
    void setState(IWorkflowPhase* s) { state = s; }

    void addListener(INotificationListener* listener) {
        listeners.push_back(listener);
    }

    void process() {
        state->handle(this); // ← 知らなくていい（状態遷移の詳細はStateが管理）
    }

    void notifyAll(string msg) {
        for (auto listener : listeners) {
            listener->onStatusChanged(msg);
        }
    }
};

```

各責務をインターフェース経由で独立させることで、個別の修正がワークフロー全体の動作を壊すリスクを排除しました。

### 7-2：変更影響グラフ（改善後）

フェーズ3で行った「緊急ルート追加」の変更要求を再度試みます。

```mermaid
graph LR
    %% 変更が特定のクラス（判定ルールや状態の実装）に局所化されている
    T1["変更要求：緊急ルート追加"] --> F1["EmergencyPhase ✅"]
    T1 -. "影響なし" .-> A["WorkflowManager本体 ✅"]
    T2["変更要求：新通知先追加"] --> F2["NewNotificationListener ✅"]
    T2 -. "影響なし" .-> A

```

→ フェーズ3のグラフと比較して、承認ルートの変更は「状態クラスの追加」、通知の変更は「リスナークラスの追加」のみで完結し、ワークフロー本体のロジックには一切影響を与えなくなりました。

### 7-3：変更シナリオ表

本設計により、承認業務における頻繁なルール変更に柔軟に対応できるようになりました。

| **シナリオ** | **変わるクラス（触る場所）** | **変わらないクラス** |
| --- | --- | --- |
| 緊急ルートを追加する | 新規状態クラスの実装 | `WorkflowManager`, 既存の状態クラス |
| 新しい承認ルールを追加する | 新規判定ルールクラスの実装 | `WorkflowManager`, リスナークラス |
| 却下時の通知先を増やす | 新規リスナークラスの実装 | `WorkflowManager`, 判定ルールクラス |

「変更が来ても、関連する独立したクラスを一つ作るだけ——それがこの設計で手に入れたものだ。 諦めたものは、クラス数が増えるというわずかな複雑さだ。」

---

### 7-4：接続形態の確認 ── この設計はどの接続か

フェーズ4-3で診断した通り、変更前のコードは **具体×直接** の状態でした。
採用した設計では、接続形態が **抽象×間接（USB-Cハブ経由）** へと変化しています。

**「抽象×間接」の証拠となるコード：**

```cpp
class WorkflowManager {
    IWorkflowPhase* state;                    // ← インターフェース型 = 「抽象」の証拠
    vector<INotificationListener*> listeners; // ← インターフェース型 = 「抽象」の証拠
public:
    void process() {
        state->handle(this);  // ← State が IApprovalRule に判定を委譲 = 「間接」の証拠
    }
};
// WorkflowManager → IWorkflowPhase → IApprovalRule という委譲チェーン
```

- `IWorkflowPhase*` と `vector<INotificationListener*>` はインターフェース型 → **「抽象」** の証拠
- `state->handle(this)` では状態クラスが内部で判定ルールに判定を委譲し、`WorkflowManager` は承認ロジックを直接知らない → **「間接」** の証拠

「状態遷移・通知・判定ルールをすべて独立して差し替えたい」という動機から、**抽象×間接** が選ばれました。


---

### 整理：7フェーズとこの章でやったこと

| **フェーズ** | **この章でやったこと** |
| --- | --- |
| 🔵 フェーズ1：現状把握 | `WorkflowManager` に状態遷移、通知、判定ルールが混在している現状を観察した。 |
| 🟣 フェーズ2：仮説立案 | 「状態遷移」「判定」「通知」の3つの軸に分離する仮説を立てた。 |
| 🟣 フェーズ3：問題特定 | 承認状態が増えるたびに `if-else` 分岐が爆発する「痛み」をシミュレーションした。 |
| 🟠 フェーズ4：原因分析 | ワークフローのフロー（骨格）と、個別のビジネスルールが混在している構造的問題を特定した。 |
| 🟡 フェーズ5：課題定義 | 状態遷移・通知・ルール判定という3つの接続点を課題として定義した。 |
| 🔴 フェーズ6：対策案検討 | 3つの変化軸を独立したインターフェースで切り出す案4を採用した。 |
| 🟢 フェーズ7：対策実施 | 責務をインターフェースで疎結合化し、変更影響をクラス単位に局所化した。 |

### 各クラスの最終的な責任

| **クラス名** | **責任（1文）** | **変わる理由** |
| --- | --- | --- |
| `WorkflowManager` | 承認ワークフローの実行フローを統括する。 | 承認プロセスの基本骨格が変わる場合 |
| `IWorkflowPhase` | 現在の承認状態に応じた振る舞いを管理する。 | 承認の状態遷移ルールが変わる場合 |
| `IApprovalRule` | 承認の可否判定ロジックを管理する。 | 金額や役職による判定ルールが変わる場合 |
| `INotificationListener` | 承認結果に基づいた通知を実行する。 | 通知先や通知要件が変わる場合 |

> **このプロセスを回した結果にたどり着いた構造こそが State × Observer × Strategy の複合パターン です。**
> 

### 振り返り：「この章を読むと得られること」は手に入ったか

| **得られること** | **この章のどこで示したか** |
| --- | --- |
| 得られること1 | フェーズ2の確定テーブルで、変化の軸（状態・通知・判定）を識別した。 |
| 得られること2 | フェーズ5で、ワークフロー本体から切り離すべき3つの接続点を特定した。 |
| 得られること3 | フェーズ7の変更シナリオ表で、責務分離による局所化を実証した。 |

### 振り返り：3つの設計原則はどう適用されたか

* **原則1「変わるものをカプセル化せよ」の現れ**
* **具体化された場所：** 各状態実装クラス、判定ルール実装クラス、通知リスナー実装クラス
* **解説：** 変化の理由が異なる「状態遷移」「判定ルール」「通知」を個別のクラスにカプセル化しました。




* **原則2「実装ではなくインターフェースに対してプログラムせよ」の現れ**
* **具体化された場所：** `IWorkflowPhase`, `IApprovalRule`, `INotificationListener`
* **解説：** `WorkflowManager` は具体的なルールや遷移先を知らず、インターフェース経由で処理を委譲するようにしました。




* **原則3「継承よりコンポジションを優先せよ」の現れ**
* **具体化された場所：** `WorkflowManager` が各インターフェースを保持する構成
* **解説：** 承認ルールを継承による拡張ではなく、コンポジションによる差し替え可能な構成にしました。




---

### あなたのコードで考えてみてください

この章で辿った思考プロセスを、あなた自身のコードに当てはめてみましょう。

1. **複雑さの核心を探す：** あなたのコードに「現在の状態によって処理が変わり、かつ状態が変わったときに他のクラスへの通知が必要で、さらにどの処理をするかのルールも変わる」箇所がありますか？
2. **肥大化のサインを確認する：** その処理をすべて一か所にまとめているクラスがあるとしたら、そのクラスのコード行数と `if` ブロックの数はどのくらいですか？
3. **変更の交差点を測る：** 「新しい状態の追加」「新しい通知先の追加」「新しいビジネスルールの追加」という3種類の変更は、今の構造では同じファイルを変更しますか？それとも別々のファイルで済みますか？
4. **分けた後のシンプルさを想像する：** 3つの責任（状態遷移・通知・ルール判定）を別々のクラスに切り出したとき、それぞれを独立してテストできるようになりますか？

---

### パターン解説：複合適用

今回は単一の構造ではなく、3つのパターンを組み合わせて解決しました。

#### 仕組みの骨格

```mermaid
classDiagram
    class Phase { <<状態管理>> }
    class Listener { <<通知>> }
    class Rule { <<判定ルール>> }

```

状態管理の仕組みが「今の状態での振る舞い」を整理し、判定ルールの仕組みが「承認の可否」を判定し、通知の仕組みが「変更の伝搬」を担うことで、複雑なワークフローを整理しています。

#### この章の実装との対応

```mermaid
classDiagram
    class WorkflowManager {
        -IWorkflowState* state
        -INotificationListener[] listeners
        +process()
    }
    class IWorkflowPhase {
        <<Phase>>
        +handle(WorkflowManager*)*
    }
    class IApprovalRule {
        <<Rule>>
        +canApprove(double)*
    }
    class INotificationListener {
        <<Listener>>
        +onStatusChanged(string)*
    }
    WorkflowManager --> IWorkflowPhase : phase
    WorkflowManager --> INotificationListener : listeners
    IWorkflowPhase ..> IApprovalRule : 判定委譲

```

#### 使いどころと限界

* **使いどころ**：状態遷移が複雑で、さらに通知先や判定ロジックが頻繁に変わるような大規模な業務ワークフロー。


* **限界**：3つのパターンを組み合わせるため、単純なフローであれば過剰設計となります。



【過剰コード：単純なフローへの適用例】

「申請中 → 承認済み」の2状態しかなく、判定ルールも「上長が承認ボタンを押したら確定」だけのシンプルなフローに、State・Observer・Strategyをすべて適用しようとした例です。

```cpp
// ❌ 2状態・固定ルール・通知先1件のフローに
//    3つの仕組みを持ち込んだ過剰設計
class IWorkflowPhase { /* ... */ };
class IApprovalRule { /* ... */ };
class INotificationListener { /* ... */ };

// ↑ インターフェースが3枚、実装クラスが6枚——
//   変わらないルールのために構造だけが膨れ上がる

// ✅ このケースは if 文で十分
class SimpleApproval {
public:
    void approve() {
        if (status == "PENDING") {
            status = "APPROVED";
            sendMail(); // 通知先は固定で1件だけ
        }
    }
private:
    std::string status = "PENDING";
    void sendMail() { /* メール送信 */ }
};
```

これらの仕組みが威力を発揮するのは、「状態の数が増える」「通知先が変わる」「判定ルールが差し替わる」という変化軸が**実際に複数存在するとき**です。その変化軸が見えないうちはシンプルな実装を選んでください。



---

## おわりに

ここまで読んでいただき、ありがとうございます。

あるとき気づいたのです。**名前を知っているだけでは、設計の問題は解けない**、と。

問題を解くために必要なのは、「このコードの中に、変わる理由が異なるものが同じ場所にいないか？」という問いを立てる力でした。その問いを9つのステップで繰り返し体験することで、目の前のコードがどう見えるかが、少しずつ変わってきました。パターンの名前は、その後に「ああ、これが世間でいう設計パターンか」とついてくるものだった。

この本が届けたかったのは、その順序です。

第1章から第12章まで、題材は銀行振り込みだったり、カスタムドリンクだったり、承認ワークフローだったりと変わり続けましたが、思考の型はずっと同じでした。「何が変わるか」「なぜ変わるか」「誰のために分けるか」——この3つの問いを自分の頭で回せるようになったとき、デザインパターンはもう「暗記するもの」ではなく、「現れるもの」に変わります。

この本で紹介した9ステップは、あくまで一つの参考です。現場によって、チームによって、コードの文脈によって、最適な解は変わります。「正しい設計」を覚えるのではなく、「自分で考えるプロセス」を手に入れてほしい——それが、この本を書いた唯一の動機です。

あなたの現場で、ぜひ一度、このプロセスを回してみてください。

「変わる理由」が見えた瞬間、コードの読み方が変わります。

---

この本を最後まで読んだあなたは、すでに変わっています。「どのパターンを使うか」ではなく、「何が変わるか、なぜ変わるか、誰のために分けるか」を問える目を持っています。その目は、この本を閉じた後も、現場のコードのそばにあり続けます。

もし「このコードを見せたい人がいる」と思ったなら、ぜひ。設計の議論が、職場の言語になっていく——それが、この本の最終的なゴールです。
