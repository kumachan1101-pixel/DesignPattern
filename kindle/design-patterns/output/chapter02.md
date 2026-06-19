## 第2章 窓口を一本化する ―― Facade パターン

### この章の核心

**複雑な外部システムの仕様変更が、私たちのビジネスロジック全体に波及してしまう。それは、相手の「詳細な使い方」を私たちが直接知りすぎているからだ。**

---

### この章を読むと得られること

この章の痛みは「外部システムの詳細を、自社のコードが直接知りすぎている」問題です。

* **得られること1：** 「依存の広がり」という観点で、コードの波及範囲を識別できるようになる
* **得られること2：** 外部システムの詳細を知りすぎているクラスを見つけ、そこが変更に弱い接続点（変更の痛みの発生源）だと判断できるようになる
* **得られること3：** 複雑な呼び出し手順をカプセル化することで、クライアントコードをスッキリ保つ方法を説明できるようになる
* **得られること4：** 外部システムと自社システムの境界線（窓口）をどこに引くべきか判断できるようになる

---

## 🔵 フェーズ1：現状把握 ―― コードとクラス構成を読む

この問題を解くために7つのフェーズを使います。はじめに現状把握から開始し、仮説立案・問題特定・原因分析・課題定義・対策検討・対策実施という順で進みます。

変更要求が来る前のシステムの現状を事実として把握するところから始めます。はじめに仕様と動作例で「このシステムが何をするか」を確認し、それからコードを読みます。

### 2.1 システムの背景

このシステムは、ネット銀行の**振り込み処理を実行**します。

### 2.2 仕様表

このシステムは、ネット銀行の**振り込み処理を実行**します。

「振込先口座番号」「送金金額」を入力として受け取り、銀行のAPIを通じて以下の手順で振り込みを完了させます。

**振り込みの処理手順**

| 手順 | 処理内容 | 失敗した場合 |
|---|---|---|
| ① 口座確認 | 振込先口座が存在し有効であることを確認する | エラーで中止 |
| ② 残高確認 | 送金元の残高が十分あることを確認する | エラーで中止 |
| ③ OTP認証 | ワンタイムパスワードで本人確認を行う | エラーで中止 |
| ④ 送金実行 | 銀行APIへ送金指示を送信する | エラーで中止 |

この4つの手順は必ず順番通りに実行される必要があります。どこかで失敗すれば後続の手順は実行されません。

---

### 2.3 動作例テーブル

仕様を定義したところで、実際にどのような入力に対してどのような結果が返るかを確認します。このテーブルは「このシステムが正しく動いているとはどういう状態か」の基準になります。後で設計の改善（リファクタリング）を段階的に進めるときも、この表に立ち返ります。

| # | 振り込み先口座 | 送金金額 | 結果 | 適用ルール |
|---|---|---|---|---|
| 1 | 12345678（有効） | 5,000円（残高十分） | 振り込み完了 | 口座確認→残高確認→認証→送金 |
| 2 | 99999999（存在しない） | 5,000円 | エラー：口座なし | 口座確認で中止 |
| 3 | 12345678（有効） | 1,000,000円（残高不足） | エラー：残高不足 | 残高確認で中止 |
| 4 | 12345678（有効） | 5,000円（残高十分） | エラー：認証失敗 | 認証コード検証で中止 |
| 5 | 87654321（有効・バッチ） | 30,000円（残高十分） | 振り込み完了（OTP不要） | 口座確認→残高確認→送金（バッチ処理は事前に社内承認が完了しているため、OTPによる追加認証が不要） |

コードを読む前に、このシステムが「何をする必要があるか」をこの表で確認できました。次は「どのように実装されているか」を見ていきます。

---

### 2.4 実装コード（現状）

#### このシステムの登場クラス

| クラス名 | 役割 | 担当する仕様 |
|---|---|---|
| TransferProcessor | 振り込みフロー進行 | 仕様全体 |
| BankGateway | 銀行API通信 | 仕様①、②、④ |
| SecurityAuthenticator | 認証制御 | 仕様③ |

データの流れ：TransferProcessor → BankGateway / SecurityAuthenticator → 外部API
この章で注目するポイント：振り込み業務の流れと、銀行APIの呼び出し手順がどのように結びついているか


#### 銀行システムと通信するクラス群

はじめに、銀行APIとの通信を担うクラスと認証を担うクラスを見てみます。

```cpp
#include <iostream>
#include <string>

// 銀行との通信を担うクラス
class BankGateway {
public:
    void verifyAccount(const std::string& account) {
        std::cout << "口座確認: " << account << "\n";
    }
    void checkBalance(const std::string& account) {
        std::cout << "残高確認\n";
    }
    void executeTransfer(const std::string& account, int amount) {
        std::cout << "送金実行: " << amount << "円\n";
    }
};

// 認証を担うクラス
class SecurityAuthenticator {
public:
    void requestOTP() { std::cout << "認証コード発行\n"; }
    void verifyOTP(const std::string& token) {
        std::cout << "認証コード検証\n";
    }
};
```

`BankGateway` と `SecurityAuthenticator` は、それぞれ銀行APIとの通信・認証の詳細を担う専門クラスです。

#### 振り込み処理クラス

次に、振り込みの全体フローを管理するクラスを見ます。

```cpp
// 振り込み処理クラス
class TransferProcessor {
private:
    BankGateway gateway;
    SecurityAuthenticator auth;
public:
    void transfer(
        const std::string& toAccount, int amount,
        const std::string& otp) {
        // 銀行システムの複雑な手順を直接制御している
        gateway.verifyAccount(toAccount);
        gateway.checkBalance(toAccount);

        auth.requestOTP();
        auth.verifyOTP(otp);

        gateway.executeTransfer(toAccount, amount);
        std::cout << "振り込み完了\n";
    }
};
```

このクラスが今章の中心です。`transfer` メソッドの中に「振り込みという業務フローの制御」と「銀行APIの具体的な呼び出し手順」が一緒に書かれていることを確認しておいてください。

#### 呼び出し元と実行確認

```cpp
int main() {
    TransferProcessor processor;
    processor.transfer("12345678", 5000, "999999");
    return 0;
}
```

上記コードの実行結果：

```
口座確認: 12345678
残高確認
認証コード発行
認証コード検証
送金実行: 5000円
振り込み完了
```

動作例テーブルの行1（12345678 / 5,000円 → 振り込み完了）と一致しています。

行2〜4（口座なし・残高不足・認証失敗）については、現状コードの各メソッド（`verifyAccount`・`checkBalance`・`verifyOTP`）は `void` 型で処理を中止する仕組みを持っておらず、このコードでは表現していません。実際のシステムでは、これらのメソッドが例外またはエラーコードを返すことで後続処理を中止します。

行5（バッチ処理・OTP不要）は、現状コードの `transfer` メソッドが常に `auth.requestOTP()` と `auth.verifyOTP()` を呼び出す構造のため、OTPをスキップする仕組みが存在しません。この動作はフェーズ7の改善後コードで実現されます。

次のフェーズで変更が来たときに何が起きるかを確認します。

---

### 2.5 クラス構成図

コードを読んだところで、クラス間の関係を図で整理します。

```mermaid
classDiagram
    class TransferProcessor {
        -BankGateway gateway
        -SecurityAuthenticator auth
        +transfer(toAccount, amount, otp)
    }
    class BankGateway {
        +verifyAccount(account)
        +checkBalance(account)
        +executeTransfer(account, amount)
    }
    class SecurityAuthenticator {
        +requestOTP()
        +verifyOTP(token)
    }

    TransferProcessor --> BankGateway : 使う
    TransferProcessor --> SecurityAuthenticator : 使う
```

`TransferProcessor` が `BankGateway` と `SecurityAuthenticator` の両方を直接保持し、それぞれのメソッドを順番に呼び出してフローを制御しています。

---

### 2.6 届いた変更要求

ある月曜日の朝、銀行のシステム担当者から緊急の連絡が入りました。

「来月から、銀行のAPIの認証仕様が大幅に変更になります。これまでは単一のOTP（ワンタイムパスワード）認証だけで十分でしたが、今後は、はじめに『認証コードの発行』をリクエストし、その後、銀行から送られてくる『取引ID』とあわせて検証する必要があるのではないでしょうか。」

さらに、これに続いて「銀行側の送金APIのインターフェースもセキュリティ強化のため、送金時のパラメータに『トランザクションID』が必須になります」とのこと。

リリースは来月の頭。既存の `TransferProcessor` クラスの中身を書き換え、認証手順や送金手順を今のコードの `transfer` メソッドに直接追加しようとすれば、あっという間に複雑な複雑に絡み合った状態状態になってしまうのは目に見えています。

設計に絶対の正解はありません。だからこそ、この変更がどこまで広がるのか、慎重に見極める必要があります。


**仕様変更の内容**

変更要求を受けて、認証と送金の手順がどう変わるかを整理します。（これらの変更はすべて「銀行側のシステム担当者・セキュリティ担当者」の判断で発生した要求です）


| 手順 | 変更前 | 変更後 |
|---|---|---|
| ① 口座確認 | 変更なし | 変更なし |
| ② 残高確認 | 変更なし | 変更なし |
| **③ 認証** | OTP（ワンタイムパスワード）1ステップで完了 | **「認証コードの発行」→「取引IDと認証コードの照合」の2ステップに変更** |
| **④ 送金実行** | 振込先口座と金額だけを指定して送金 | **「トランザクションID」が必須パラメータとして追加** |

現行の単一OTP認証では `verifyOTP(code)` を1回呼ぶだけでよかったところ、新仕様では `requestAuthCode()` で認証コードを発行し、返ってきた取引IDと合わせて `verifyWithTransactionID(authCode, txId)` を呼ぶ流れに変わります。送金APIも `executeTransfer(account, amount, transactionId)` という形にパラメータが増えます。

フェーズ1でシステムの現状と変更要求が把握できました。次のフェーズ2では、「何が変わり、何が変わらないか」を整理します。

---

## 🟣 フェーズ2：仮説立案 ―― 何が変わるかを観察し、ヒアリングで裏付ける

### 2.7 責任テーブル

| **クラス名** | **責任（1文）** | **知るべきこと** |
|---|---|---|
| `TransferProcessor` | 振り込みの全体フローを進行する | 振り込みという業務フローの手順、誰に処理を依頼するか |
| `BankGateway` | 銀行APIを呼び出し、口座や送金を操作する | APIの仕様、通信のプロトコル、リクエストの組み立て方 |
| `SecurityAuthenticator` | 銀行システムの認証手順を制御する | 認証の手順、OTP（ワンタイムパスワード）の検証方法 |

### 2.8 責任チェック表

各クラスが「何を知るべきか」を整理します。

| **クラス名** | **責任（1文）** | **知るべきこと** |
|---|---|---|
| `TransferProcessor` | 振り込みの全体フローを進行する | 振り込みという業務フローの手順、誰に処理を依頼するか |
| `BankGateway` | 銀行APIを呼び出し、口座や送金を操作する | APIの仕様、通信のプロトコル、リクエストの組み立て方 |
| `SecurityAuthenticator` | 銀行システムの認証手順を制御する | 認証の手順、OTP（ワンタイムパスワード）の検証方法 |

### 2.9 仮説テーブル

| **分類** | **仮説** | **根拠（観察から読み取れること）** |
|---|---|---|
| 🔴 **変動しそう** | 銀行APIの呼び出し手順やパラメータ | メソッド内に外部システム詳細が直書きされているため |
| 🟢 **不変そう** | 振り込みフローの基本的な流れ | 業務の目的自体は変わらないため |

コードを読んだだけで断定するのは危険なため、関係者に直接確認します。

責任チェック表でクラスの責任が整理できました。次に、コードの各行が「誰の判断で変わる知識か」を確認することで、混在している責任をさらに細かく特定します。判断基準は、「このクラスの担当者（ここでは振り込みシステム開発チーム）とは別の人間が変更を決定するかどうか」です。別の人間が決定するなら、それは「責任外（❌）」と判断します。

`TransferProcessor.transfer()` の各行を見ると：

| **コードの行** | **持っている知識** | **誰の判断で変わるか** | **責任内か** |
|---|---|---|---|
| `gateway.verifyAccount(toAccount);` | 銀行APIの口座確認手順 | 銀行側のシステム担当者 | ❌ 別担当者 |
| `gateway.checkBalance(toAccount);` | 銀行APIの残高確認手順 | 銀行側のシステム担当者 | ❌ 別担当者 |
| `auth.requestOTP();` | 認証のための手順（OTP発行） | 銀行側のセキュリティ担当者 | ❌ 別担当者 |
| `auth.verifyOTP(otp);` | 認証コードの検証方法 | 銀行側のセキュリティ担当者 | ❌ 別担当者 |
| `gateway.executeTransfer(toAccount, amount);` | 送金APIの呼び出し方法 | 銀行側のシステム担当者 | ❌ 別担当者 |

1つのメソッドの中に、ほぼすべての行が「外部の担当者の判断で変わる知識」で占められています。振り込みという業務フローを管理するはずのクラスが、銀行APIという外部システムの詳細を丸ごと抱え込んでいます。今すぐ問題とは言えませんが、これが後の痛みの予兆です。

### 2.10 ヒアリング

今回の変更要求から確定している変更は以下の2点です。
- 銀行APIの認証手順の変更：OTP1ステップから、認証コード発行＋取引IDとの照合という2ステップに変更
- 送金APIのパラメータ追加：送金時にトランザクションIDが必須になる

ただし「この変更が1回限りか、今後も続くか」によって、どこまで設計を変えるべきかが大きく変わります。関係者に確認します。

> **現実のヒアリングでは——** 本書のヒアリングシーンでは設計判断を明確にするため、意図的に「理想的な回答」が返ってくるように描いています。これはシミュレーションです。現実には、「変わるかどうか分からない」「たぶん変わらない」という曖昧な答えが返ることも多いです。そのときは `git log` や過去の障害記録を「ヒアリングの代わり」として使ってみてください。「過去に何度変わったか」が最も正直な証拠です。

今回、銀行のAPI担当者にヒアリングを行いました。

> **現実のヒアリングでは——** 本書のヒアリングシーンでは設計判断を明確にするため、意図的に「理想的な回答」が返ってくるように描いています。これはシミュレーションです。現実には、「変わるかどうか分からない」「たぶん変わらない」という曖昧な答えが返ることも多いです。そのときは `git log` や過去の障害記録を「ヒアリングの代わり」として使ってみてください。「過去に何度変わったか」が最も正直な証拠です。

今回の変更が一時的なものか、将来も続くリスクがあるのかを確認するため、銀行のAPI担当者にヒアリングを行いました。

- **開発者：** 「認証の仕様が変わるとのことですが、今回の変更は一時的なものでしょうか？今後、さらに認証方式が増える予定はありますか？」
- **銀行API担当者：** 「申し訳ありませんが、セキュリティ強化の波は止まりません。数ヶ月後には、生体認証を導入する予定もあります。今後も認証手順はさらに複雑になる可能性が高いです。」
- **開発者：** 「なるほど。送金APIについても、今後パラメータが増えたり、呼び出し順序が変わったりすることは考えられますか？」
- **銀行API担当者：** 「ええ、来年以降には、さらに上位のトランザクション管理システムと連携するため、送金時のリクエスト形式が現在のJSONからXMLへ移行する計画もあります。」
- **開発者：** 「分かりました。かなり頻繁に接続仕様が変わりそうですね。今回の認証フローの変更についても、将来的にさらに手順が増えるリスクはありますか？」
- **銀行API担当者：** 「おっしゃる通りです。現在は二段階認証ですが、将来的には三段階になるかもしれません。現時点での固定的な手順に縛られない設計にしておいた方が、お互いのためかもしれませんね。」

### 2.11 変動テーブル

ヒアリングの結果を受けて、変動の確定とリスクを一覧にまとめます。

ヒアリングで浮かび上がった「確定ではないが、近い将来起こりうる変化」を記録します。これは今回の設計判断の材料です。

| **将来リスク** | **時期の目安** | **根拠** |
|---|---|---|
| 認証フローの多段階化（二段階→三段階認証） | 銀行側のセキュリティ強化時 | 銀行API担当者との確認 |
| 送金リクエスト形式の変更（JSON→XML移行計画） | 来年以降の基幹システム連携時 | 銀行API担当者との確認 |
| 生体認証の導入 | 数ヶ月後の予定 | 銀行API担当者との確認 |

フェーズ2で「今変わること（確定）」と「将来変わるかもしれないこと（リスク）」を分けて整理できました。次のフェーズ3では、現在の構造で変更を試みたときに何が起きるかを確認します。

---

## 🟣 フェーズ3：問題特定 ―― 変更の痛みを発見する

### 2.12 変更シミュレーション

「銀行APIの認証フロー変更（発行と検証の2段階化）」と「送金時のトランザクションID付与」を、現在の `TransferProcessor` クラスの `transfer` メソッドに直接書き込む作業を試みてみましょう。変更前のコードはこうでした。

```cpp
gateway.verifyAccount(toAccount);
gateway.checkBalance(toAccount);

auth.requestOTP();
auth.verifyOTP(otp);

gateway.executeTransfer(toAccount, amount);
```

このコードに今回の変更を適用すると、以下のようになります。

```cpp
void transfer(
        const std::string& toAccount, int amount,
        const std::string& otp) {
    gateway.verifyAccount(toAccount);
    gateway.checkBalance(toAccount);

    // 【痛み：認証の手順が変わる】
    // 既存のコードを書き換える必要がある
    auth.requestOTP();
    // 銀行から発行された「取引ID」（認証フロー内の識別子）を保持しなければならない
    std::string transactionId = auth.getTransactionId();
    // 検証時に取引IDを渡す必要がある
    auth.verifyOTP(otp, transactionId);

    // 【痛み：送金APIの仕様が変わる】
    // 送金用の「トランザクションID」（認証の取引IDとは別の、送金単位の識別子）を生成して渡す
    std::string txId = generateTxId();
    gateway.executeTransfer(toAccount, amount, txId);

    std::cout << "振り込み完了\n";
}
```

この変更を試みたとき、はじめに気づくのは `TransferProcessor` クラスが「銀行APIの細かな使い方」をあまりにも詳細に知りすぎているという点です。認証のステップが増えただけでメソッドのシグネチャを追いかける必要があり、ロジックの修正が連鎖的に発生してしまいます。

「振り込みを実行する」という業務上の命令を処理しているはずの `TransferProcessor` が、銀行システム側から送られてくる「取引IDを保持する」といった一時的な状態管理まで背負わされています。銀行側のAPI仕様が一つ変わるたびに、私たちの業務フローを制御するクラスのコードを書き換え、その結果、振り込み処理全体のテストをやり直さなければならないのです。

### 2.13 変更影響グラフ

```mermaid
graph LR
    T1["変更要求：API変更"] -->|"飛び火"| A["TransferProcessor"]
    A -->|"影響"| B["BankGateway"]
    A -->|"影響"| C["SecurityAuthenticator"]
```

このグラフを見ると、銀行APIの仕様という「外部システム都合の変更」が、私たちの業務フローの中枢である `TransferProcessor` を経由して、通信クラスや認証クラス全体に飛び火していることが分かります。

> **グラフの読み方：** この矢印は「フェーズ3で実際に変更したクラス」ではなく、「変更要求が来たときに影響が波及するリスクのある依存関係」を示しています。`TransferProcessor` が `BankGateway` と `SecurityAuthenticator` を直接知っているため、銀行APIの仕様が変わると `TransferProcessor` を経由して両クラスへの影響が及ぶ可能性があることを可視化しています。

### 2.14 痛みの言語化

**1つ目：仕様変更の波が業務ロジックに直撃する恐怖。** 今回の認証フローの変更は、本来であれば「振り込み」という業務プロセスには影響しないはずのものです。しかし、今の構造では、銀行APIという「外部システムの使い方」を `TransferProcessor` が直接知っているため、APIの引数が増えたり手順が変わったりするたびに、業務フローを記述している核心部分を書き換える羽目になります。

**2つ目：目的が見えなくなる複雑化。** コードを見れば、口座確認、残高確認、認証発行、検証、送金実行と、手続きが淡々と並んでいます。しかし、新しい仕様に対応するために一時的なIDを保持したり、条件分岐を足したりすることで、コードは「何のために振り込んでいるのか」という業務上の目的よりも、「銀行のAPIにどうやって命令を通すか」という技術的な手順の記述で埋め尽くされてしまいます。

---
> **📌 問題（確定）**
> 振り込み処理の認証手順や送金パラメータが変わるたびに、業務フローを管理する `TransferProcessor` のコードを直接書き換えなければならない。変わる理由が異なるコードが同じ場所に混在しているため、銀行API側の仕様変更が振り込み業務ロジック全体に波及し、影響範囲が読めない。
---

フェーズ3で「変更が辛い」ことが確認できました。次のフェーズ4では、なぜ辛いのかを構造的に言語化します。

---

## 🟠 フェーズ4：原因分析 ―― なぜ辛いのかを構造で言語化する

### 2.15 痛みの根源を探る（観察と原因）

フェーズ3で確認した「変更の辛さ」は、コードのどこから来ているのでしょうか。コードを注意深く観察すると、痛みを引き起こしている2つの事実が浮かび上がってきます。

第一に、新しい認証ステップが追加されたとき、なぜ毎回 `TransferProcessor` を開かなければならないのでしょうか？
それは、このクラス自身が「`auth.requestOTP()` を呼んで、取引IDを取得して、`auth.verifyOTP()` を呼ぶ」といった**銀行APIの具体的な呼び出し手順をすべて直接知ってしまっている（抱え込んでいる）**からです。

第二に、なぜ変更の影響範囲が読めず、振り込み全体のテストをやり直す恐怖を感じるのでしょうか？
それは、「振り込みという業務プロセスの進行」という責任と、「銀行APIという外部システムの技術的な利用手順」という責任が、**同じメソッドの中で物理的に混ざり合っている**からです。

この「症状（痛み）」と「根本原因」を整理すると、以下のようになります。

| **観察した症状（痛み）** | **構造的な原因（痛みの根源）** |
|---|---|
| 仕様変更の波が業務ロジックに直撃する | `TransferProcessor` が銀行APIの具体的な呼び出し手順を直接知っているから |
| 複雑化して目的が見えなくなる | 変わる理由が違う2つのもの（「振り込み業務のフロー」と「銀行APIの技術手順」）が同じメソッドの中に混在しているから |

### 2.16 変わるものと変わらないものの対比

> **「変わらないもの」と「変わってほしくないもの」は異なります。** 「変わらないもの」は経験的事実（今まで変わっていない）、「変わってほしくないもの」は設計意図（ここを安定させてほかを守りたい）です。ここで整理するのは後者です。

| **変わり続けるもの（外部システムの詳細）** | **変わってほしくないもの（業務フローの骨格）** |
|---|---|
| 銀行APIの認証手順（発行・検証のステップ） | 振り込みの全体フロー（口座確認→残高確認→送金） |
| 送金APIのパラメータ（IDの追加や型変更） | 振り込みという業務上の目的 |

**【変わる部分（外部システムの技術詳細）】**
```cpp
        // ← 銀行側の都合で変わり続ける部分
        auth.requestOTP();
        std::string transactionId = auth.getTransactionId();
        auth.verifyOTP(otp, transactionId);
        std::string txId = generateTxId();
        gateway.executeTransfer(toAccount, amount, txId);
```

**【変わらない部分（業務フローの不変の骨格）】**
```cpp
        // ← 振り込みという業務の意図は変わらない
        // （口座を確認する）
        // （認証する）
        // （送金を実行する）
        std::cout << "振り込み完了\n";
```

### 2.17 ケーブル比喩

現在、TransferProcessor と BankGateway などのクラスは、インターフェースを介さず、具体的なクラス名やメソッド名を直接知る形で直接依存しています。この状態を整理するために、接続形態という視点を使います。

現在の `TransferProcessor` は、銀行APIという「特定の機器」に対して、専用のケーブルを直に配線しているような状態です。

**【具体×直接のコード】**
```cpp
class TransferProcessor {
private:
    BankGateway gateway;         // ← 具体：型名を直接宣言
    SecurityAuthenticator auth;  // ← 具体：型名を直接宣言
public:
    void transfer(...) {
        // ← 直接：各APIメソッドを窓口なしに直接順に呼び出す
        gateway.verifyAccount(toAccount);
        auth.requestOTP();
        // gateway.executeTransfer(fromAccount, toAccount, amount);
        // gateway.confirmTransaction(); など送金実行処理が直接続く
    }
};
```

この状態は **「具体×直接」の接続形態** です。iPhoneに専用のLightningケーブルを直差ししている状態と同じで、銀行側の認証方式が変わり送金時のパラメータが増えるたびに、私たちはその専用端子に合わせてコードという名の「配線」を直接付け替えなければなりません。

「振り込み業務」と「銀行APIの仕様」は、変わる理由が全く異なります。これらが同じ場所に混在していることが、根本原因として確認できました。

私たちは今、最も密結合で変更に弱い「具体×直接」の地点にいます。

---
> **📌 原因（確定）**
> 具体×直接の接続形態は、銀行APIが変わらない状況であれば問題にならない。問題になるのは、ヒアリングで確認された「認証フローの多段階化」「送金パラメータの変更」という変化を、`TransferProcessor` が銀行APIの呼び出し手順として直接抱え込んでいるからだ。外部システムの都合で変わる知識と、振り込み業務のフローという変わってほしくない知識が、同じクラスの中に物理的に混在している。
---

フェーズ4で根本原因が言語化できました。「どこを分けるか」は明確です。次のフェーズ5では、その境界で実際に何が流れているかを値・型のレベルで具体化し、「何が変わり、何が変わらないか」を明確にします。

---

## 🟡 フェーズ5：課題定義 ―― 接続点で何が流れているかを見る

フェーズ4は「なぜ辛いか」を答えました。フェーズ5が問うのは「分けるべき境界で、実際に何が流れているか」です。クラスの参照関係ではなく、**値・型のレベル**に降りていきます。

フェーズ4の分析により、問題は「振り込み業務のフロー」と「銀行APIの技術的な呼び出し手順」が混在していることだと分かりました。その境界で何がやり取りされているかを具体化します。

### 2.18 接続点の特定

`transfer()` の中で分けるべき境界は1か所。「銀行APIを呼び出す生産者」が業務フローに渡しているデータを見ます。

```cpp
void transfer(
        const std::string& toAccount, int amount,
        const std::string& otp) {

    // ↓ 銀行API呼び出しの生産者（変わり続ける）
    gateway.verifyAccount(toAccount);
    gateway.checkBalance(toAccount);
    auth.requestOTP();
    std::string transactionId = auth.getTransactionId();
    auth.verifyOTP(otp, transactionId);
    std::string txId = generateTxId();
    gateway.executeTransfer(toAccount, amount, txId);
    // ↑ ここまでが分離するターゲット

    std::cout << "振り込み完了\n"; // ← 変わらない骨格
}
```

「銀行API呼び出し群」が受け取るのは振り込み先・金額・OTPです。完了は副作用（void）で表現されます。

| 接続点 | 接続するデータ | 変わるもの |
|---|---|---|
| 銀行API群 → `transfer()` の骨格 | toAccount（string）・amount（int）・otp（string）→ 完了（void） | APIの呼び出し手順・実装詳細 |

### 2.19 非機能制約の確認

| **確認項目** | **内容** | **この章での判断** |
|---|---|---|
| 変更頻度 | この接続点はどのくらいの頻度で変わるか | 高 |
| パフォーマンス | ホットパスか（高頻度で呼ばれるか） | いいえ |
| メモリ | 間接層の追加でオーバーヘッドが問題になるか | いいえ |

### 2.20 課題まとめ表

| **接続点** | **分けた理由** | **非機能制約** | **クライアント影響** |
|---|---|---|---|
| 銀行API群 → `transfer()` の骨格 | 変わる理由が異なる | ホットパスではない | `TransferProcessor` 全体に影響 |



- **変わるもの**：銀行APIの呼び出し手順（gateway/auth のメソッド群・順序・パラメータ）。外部システムの仕様変更のたびに内部が変わる。
- **変わらないもの**：受け取る引数の型（toAccount:string・amount:int・otp:string）。業務フローが求める「振り込みを完了する」という意図。

呼び出し元（`BatchTransferService` 等）は「口座・金額・OTPを渡せれば十分」なので安定しています。問題は「どのAPIをどの順番でどう呼ぶか」という**生産者の側**が外部仕様変更のたびに揺れること。

**具体×直接のままでよい場面**：銀行APIが今後変わらない確証があれば、現状のまま（具体×直接）で十分です。接続形態の選択は「**生産者が変わるかどうか**」で決まります。今回はAPIの変更リスクがヒアリングで確認済みなので、次のフェーズで生産者を差し替えられる設計を検討します。

---
> **📌 課題（確定）**
> 認証フローや送金仕様が変わるたびに増え続けることが確定している以上、`TransferProcessor` がその全種類の呼び出し手順を直接知り続けるのはコストが合わない。銀行APIの「具体的な呼び出し手順（生産者）」を外から差し替えられるようにし、`TransferProcessor` からは安定したインターフェース越しに処理を委譲できる構造に変える必要がある。
---

## 🔴 フェーズ6：対策検討 ―― 段階的な改善と決断

フェーズ5で「変わるのは銀行APIの呼び出し手順（生産者）であり、業務フローが受け取る引数の型は安定している」ことが分かりました。ここでは、その生産者をどのように差し替え可能にするかを段階的に検討します。いきなり正解へ飛ぶのではなく、各ステップで「どこまで痛みが解消されるか」を確認しながら、今回の要件において「どのステップで止めるべきか」を決断します。

### 2.21 接続の形：2×2マトリクス

どの案もフェーズ1の動作例テーブルで示した動作を実現します。違うのは「変更が来たときにどこを触ることになるか」だけです。

| **なぜ分けたか** | **接続の形** |
|---|---|
| 責任を整理したい | 具体×直接 |
| 実装を差し替えたい | 抽象×直接 |
| 複雑さを隠したい | 具体×間接 |
| 差し替えたい かつ 知らせたくない | 抽象×間接 |

### 2.22 ステップ1：丸ごと関数に切り出す（とりあえず分ける）

API呼び出しが複雑に絡み合っているなら、まずは一塊として関数に切り出してみよう、というのが自然な最初の発想です。クラスを新しく作るのはコストがかかります。

```cpp
class TransferProcessor {
    BankGateway gateway;
    SecurityAuthenticator auth;

    // 銀行とのやり取りを丸ごと一つのメソッドに押し込む
    void executeBankOperations(const std::string& account, int amount, const std::string& otp) {
        gateway.verifyAccount(account);
        gateway.checkBalance(account);
        if (!otp.empty()) {
            auth.requestOTP();
            auth.verifyOTP(otp, "TXN12345"); // ダミー値
        }
        gateway.executeTransfer(account, amount, "TXN12345");
    }

public:
    void transfer(const std::string& toAccount, int amount, const std::string& otp) {
        executeBankOperations(toAccount, amount, otp);
        std::cout << "振り込み完了\n";
    }
};
```

**この段階の評価：**
`transfer()` 自身はスッキリしましたが、`executeBankOperations()` の中身は相変わらずAPIの手順がベタ書きされたスパゲティ状態のままです。

### 2.23 ステップ2：処理を個別の関数に分ける

次に、丸ごとまとめた処理を意味のある単位（口座確認・認証・送金）に分割してみます。

```cpp
class TransferProcessor {
    BankGateway gateway;
    SecurityAuthenticator auth;

    void checkAccount(const std::string& account) {
        gateway.verifyAccount(account);
        gateway.checkBalance(account);
    }

    void authenticate(const std::string& otp) {
        auth.requestOTP();
        auth.verifyOTP(otp, "TXN12345");
    }

    void sendMoney(const std::string& account, int amount) {
        gateway.executeTransfer(account, amount, "TXN12345");
    }

public:
    void transfer(const std::string& toAccount, int amount, const std::string& otp) {
        checkAccount(toAccount);
        if (!otp.empty()) {
            authenticate(otp);
        }
        sendMoney(toAccount, amount);
        std::cout << "振り込み完了\n";
    }
};
```

**この段階の評価：**
各処理の意図は明確になりました。しかし、条件判定（`if (!otp.empty())`）が `transfer()` の中に露出してしまいました。

### 2.24 ステップ3：条件も個別の関数に分ける

露出したif文も関数の中に隠蔽し、呼び出し元をさらに単純化します。

```cpp
class TransferProcessor {
    BankGateway gateway;
    SecurityAuthenticator auth;
    // ... (checkAccount, sendMoney は同じ)

    void authenticateIfNeeded(const std::string& otp) {
        if (!otp.empty()) {
            auth.requestOTP();
            auth.verifyOTP(otp, "TXN12345");
        }
    }

public:
    void transfer(const std::string& toAccount, int amount, const std::string& otp) {
        checkAccount(toAccount);
        authenticateIfNeeded(otp);
        sendMoney(toAccount, amount);
        std::cout << "振り込み完了\n";
    }
};
```

**この段階の評価：**
最高に読みやすくなりました。しかし、結局 `checkAccount()` などはすべて `TransferProcessor` クラスの内部にあります。銀行APIの仕様が変わるたびに、`TransferProcessor` を開いて書き直す必要があるという根本的な痛みが残っています。

### 2.25 ステップ4：別のクラスに切り出してみる（具体×間接）

「銀行APIとのやり取りをすべて別のクラスに任せてしまえば、`TransferProcessor` は呼ぶだけでよくなる」という発想です。手順全体を担当するクラスを新しく作ります。

```cpp
// 銀行APIの手順を隠蔽する専用クラス（インターフェースなし）
class BankTransferHelper {
    BankGateway gateway;
    SecurityAuthenticator auth;
public:
    void execute(const std::string& account, int amount, const std::string& otp) {
        gateway.verifyAccount(account);
        gateway.checkBalance(account);
        if (!otp.empty()) {
            auth.requestOTP();
            auth.verifyOTP(otp, "TXN12345");
        }
        gateway.executeTransfer(account, amount, "TXN12345");
    }
};

class TransferProcessor {
    BankTransferHelper* helper; // 具体クラスへの依存
public:
    TransferProcessor(BankTransferHelper* h) : helper(h) {}
    void transfer(const std::string& toAccount, int amount, const std::string& otp) {
        helper->execute(toAccount, amount, otp);
        std::cout << "振り込み完了\n";
    }
};
```

**この段階の評価：**
ファイルを分けたことで業務フローは守られましたが、`TransferProcessor` は依然として `BankTransferHelper` という具体クラスを直接知っています。

### 2.26 ステップ5：インターフェース化して呼び出し手順ごと追い出す（抽象×間接）

具体クラスへの依存を断ち切るために、インターフェースを導入して呼び出し側（`main` 等）に組み立ての責任を移動させます。

```cpp
// 窓口のインターフェース
class IBankTransferService {
public:
    virtual void performTransfer(const std::string& account, int amount, const std::string& otp) = 0;
    virtual ~IBankTransferService() = default;
};

// 実装クラス（内部でAPIを呼び出す）
class BankTransferService : public IBankTransferService {
    BankGateway gateway;
    SecurityAuthenticator auth;
public:
    void performTransfer(const std::string& account, int amount, const std::string& otp) override {
        gateway.verifyAccount(account);
        gateway.checkBalance(account);
        if (!otp.empty()) {
            auth.requestOTP();
            auth.verifyOTP(otp, "TXN12345");
        }
        gateway.executeTransfer(account, amount, "TXN12345");
    }
};

class TransferProcessor {
    IBankTransferService* service; // 抽象にのみ依存
public:
    TransferProcessor(IBankTransferService* s) : service(s) {}
    void transfer(const std::string& toAccount, int amount, const std::string& otp) {
        service->performTransfer(toAccount, amount, otp);
        std::cout << "振り込み完了\n";
    }
};
```

**この段階の評価：**
ついに外部システムの具体的な手順が `TransferProcessor` から消え去り、インターフェース越しに操作する形になりました。しかも、実行結果は最初と1ミリも変わりません。

### 2.27 どこまで設計を進めるべきか（採用案の決断）

それぞれのステップには一長一短があります。どこで止めるかは、「今後の変更頻度（ビジネス要求）」で決断します。

*   **Step 1・2・3（関数化）で止めるケース：** 「銀行APIの仕様変更が過去5年で一度も起きていない」場合。現在のコードを整理するだけで十分です。
*   **Step 4（単純なクラス化）で止めるケース：** 将来APIの変更があるかもしれないが、複数の呼び出し元がまだ1つしかない場合。
*   **Step 5（抽象化）まで進むケース：** 認証手順や通信仕様が今後頻繁に変わると確定している場合。

**今回の決断：**
フェーズ2のヒアリングで、銀行API担当者から今後も頻繁に仕様変更が発生することが明言されています。したがって、今回は迷わず**ステップ5（抽象化）まで進化させる**決断を下します。

フェーズ6で採用ステップが決まりました。次のフェーズ7では、この決断を最終的なコードに落とし込みます。

## 🟢 フェーズ7：対策実施 ―― 変化に強いコードを完成させる

---

### 2.28 最終コード（全体）

ステップ5で決断した構造を、実行可能な完全なコードとして組み上げます。なお、フェーズ6の検討では `TransferProcessor` などの名前を使っていましたが、最終実装では各役割ごとにコードを分けて見ていきましょう。

```cpp
#include <iostream>
#include <string>
#include <vector>

// 1. サブシステム群（銀行APIと認証）
// 銀行との通信を担うクラス
class BankGateway {
public:
    void verifyAccount(const std::string& account) {
        std::cout << "口座確認: " << account << "\n";
    }
    void checkBalance(const std::string& account) {
        std::cout << "残高確認\n";
    }
    void executeTransfer(const std::string& account, int amount, const std::string& txId) {
        std::cout << "送金実行: " << amount << "円\n";
    }
};

// 認証を担うクラス
class SecurityAuthenticator {
public:
    void requestOTP() { std::cout << "認証コード発行\n"; }
    void verifyOTP(const std::string& token, const std::string& txId) {
        std::cout << "認証コード検証\n";
    }
};

// 2. 窓口となるインターフェースと実装
// 業務フロー側に見せる窓口（インターフェース）
class IBankTransferService {
public:
    virtual void performTransfer(const std::string& account, int amount, const std::string& otp) = 0;
    virtual ~IBankTransferService() = default;
};

// 銀行との複雑なやり取りをすべて隠蔽する窓口クラス
class BankTransferService : public IBankTransferService {
private:
    BankGateway gateway;
    SecurityAuthenticator auth;
public:
    void performTransfer(const std::string& account, int amount, const std::string& otp) override {
        gateway.verifyAccount(account);
        gateway.checkBalance(account);
        // バッチ処理（otp=""）は社内承認済みのためOTPをスキップ
        if (!otp.empty()) {
            auth.requestOTP();
            auth.verifyOTP(otp, "TXN12345"); // 内部的に取引IDを扱う
        }
        gateway.executeTransfer(account, amount, "TXN12345");
    }
};

// 3. 本体クラス（コンテキスト）
// 振り込み処理クラス：銀行の仕様を一切知らなくてよい
class TransferProcessor {
private:
    IBankTransferService* facade;
public:
    TransferProcessor(IBankTransferService* f) : facade(f) {}
    void transfer(const std::string& toAccount, int amount, const std::string& otp) {
        facade->performTransfer(toAccount, amount, otp);
        std::cout << "振り込み完了\n";
    }
};

// 給与振り込みなどの一括処理バッチ
class BatchTransferService {
private:
    IBankTransferService* facade;
public:
    BatchTransferService(IBankTransferService* f) : facade(f) {}
    void processPayroll(const std::vector<std::pair<std::string, int>>& transfers) {
        for (int i = 0; i < (int)transfers.size(); i++) {
            const std::string& account = transfers[i].first;
            int amount = transfers[i].second;
            facade->performTransfer(account, amount, "");
        }
    }
};

// 4. 組み立てと実行（メイン関数）
class BatchApplication {
public:
    void run() {
        BankTransferService facade;
        TransferProcessor processor(&facade);
        BatchTransferService batch(&facade);

        processor.transfer("12345678", 5000, "999999");

        std::vector<std::pair<std::string, int>> payroll;
        payroll.push_back(std::make_pair("87654321", 30000));
        payroll.push_back(std::make_pair("11112222", 25000));
        batch.processPayroll(payroll);
    }
};

int main() {
    BatchApplication app;
    app.run();
    return 0;
}
```

---

### 2.29 変更シナリオ表

| **シナリオ** | **変わるクラス** | **変わらないクラス** |
|---|---|---|
| 認証フローの変更（2段階→3段階） | `BankTransferService`（内部手順のみ） | `TransferProcessor`, `BatchTransferService` |
| 送金APIのパラメータ追加 | `BankTransferService`（内部手順のみ） | `TransferProcessor`, `BatchTransferService` |

---

### 2.30 この構造には名前がある

フェーズ6で選び、今コードとして完成させた構造には、実は名前がある。

> **Facade パターン** ――「複雑なサブシステムの手順を、一つのシンプルな窓口で覆い隠す」

GoFが1994年に整理したこの構造は、まさに今この章で辿った思考プロセスを結晶化したものだ。

---

### 2.31 耐久テスト

フェーズ2のヒアリングで挙がった「将来のリスク」が実際に発生したときに、触る場所が最小限で済むかを確認する。

| **変更シナリオ** | **触る場所** | **コスト評価** |
|---|---|---|
| 生体認証の導入 | `BankTransferService` | 低（業務ロジックは無傷） |
| 送金リクエスト形式のJSON→XML移行 | `BankTransferService` | 低（変換を内部で完結できる） |

---

### 整理

#### この章でやったこと

| **フェーズ** | **この章でやったこと** |
|---|---|
| 🔵 フェーズ1：現状把握 | 仕様と動作例テーブルを確認した後、コードをクラス単位で読んだ。クラス構成図と変更要求を把握した |
| 🟣 フェーズ2：仮説立案 | 責任テーブルと変わる理由の分析で、`TransferProcessor` が外部システムの詳細を全て抱え込んでいることを確認し、確定変更と将来リスクを分けて整理した |
| 🟣 フェーズ3：問題特定 | API変更の適用を試み、影響が `TransferProcessor` を経由して全体に飛び火することを確認した |
| 🟠 フェーズ4：原因分析 | 振り込み業務のフローと銀行APIの技術詳細が同じ場所にいることが痛みの根本と特定した |
| 🟡 フェーズ5：課題定義 | 接続点で流れるのは toAccount/amount/otp（安定）、変わるのはAPIの呼び出し手順（生産者）であることを特定した |
| 🔴 フェーズ6：対策検討 | 5ステップの段階的進化で限界を確認し、ステップ5（抽象化・インターフェース化）まで進化させる決断を下した |
| 🟢 フェーズ7：対策実施 | 最終コードを実装し、変更シナリオ表と耐久テストで変更の局所化を確認した |

#### 最終責任テーブル

| **クラス名** | **責任（1文）** | **変わる理由** |
|---|---|---|
| `TransferProcessor` | 振り込み業務フローの進行 | 業務ルールの変更 |
| `BankTransferService` | 銀行APIの呼び出し手順の管理 | 銀行システムの仕様変更 |
| `IBankTransferService` | 銀行API窓口の契約定義 | 業務が必要とする操作の変更 |

---

### 振り返り

#### 「この章を読むと得られること」は手に入ったか

| **得られること** | **この章のどこで示したか** |
|---|---|
| 得られること1：変動箇所を識別できる | フェーズ2の変わる理由の分析 |
| 得られること2：接続点の形を読み取れる | フェーズ4のケーブル比喩と具体×直接の診断 |
| 得られること3：変更の局所化を構造で説明できる | フェーズ7の変更シナリオ表・耐久テスト |
| 得られること4：境界線の引き方 | フェーズ5の課題定義とフェーズ2のヒアリング |

#### 第0章の3つの設計原則はどう適用されたか

- **原則1「変わるものをカプセル化せよ」の現れ**
  - **具体化された場所：** `BankTransferService` クラス
  - **解説：** 銀行APIの複雑な手順という「頻繁に変わる詳細」を、`BankTransferService` の中に閉じ込めた。これにより、業務クラスは銀行APIの詳細を知る必要がなくなった。

- **原則2「実装ではなくインターフェースに対してプログラムせよ」の現れ**
  - **具体化された場所：** `TransferProcessor` のメンバ変数 `IBankTransferService* facade`
  - **解説：** 業務クラスは「どのようなAPIか」ではなく、「振り込みを実行する（`performTransfer`）」という窓口のインターフェースに対して命令を送るようになった。

- **原則3「継承よりコンポジションを優先せよ」の現れ**
  - **具体化された場所：** `TransferProcessor` と `BatchTransferService` に `IBankTransferService` を持たせる構造
  - **解説：** 継承を使うと銀行APIの変更のたびにクラス階層が深くなる。コンストラクタインジェクションによるコンポジションは、実装クラスを切り替えたり将来的な窓口の増設にも容易に対応できる。

---

### あなたのコードで考えてみてください

この章で辿った思考プロセスを、あなた自身のコードに当てはめてみましょう。

1. **変動の兆候を探す：** あなたのコードに「外部APIやライブラリの呼び出し手順（認証→接続→送信→確認など）を、ビジネスロジックと同じ場所に書いている」箇所がありますか？
2. **変える理由を問う：** そのコードの各行は、誰の判断で変わりますか？同じチームで完結していますか、それとも外部の担当者が絡んでいますか？
3. **結合の強さを測る：** ビジネスロジックのコードが、外部システムの「エラーコードの体系」や「接続パラメータの名前」を直接知っていますか？
4. **分けた後を想像する：** もし「外部システムとのやりとりをすべて担う窓口クラス」を1つ置いたとすると、外部仕様が変わったときの修正はどこだけで完結するようになりますか？

---

### パターン解説：Facade パターン

#### パターンの骨格

Facadeパターンは、複雑なサブシステム（銀行APIなど）の一連のインターフェースに対する統合された窓口を提供し、サブシステムを使いやすくするパターンです。

```mermaid
classDiagram
    class Client {
        +doWork()
    }
    class Facade {
        +operation()
    }
    class SubsystemA {
        +doWork()
    }
    class SubsystemB {
        +doSomething()
    }
    Client --> Facade
    Facade --> SubsystemA
    Facade --> SubsystemB
```

#### この章のコードとの対応

| **GoFの役割** | **この章のクラス** | **担っている責任** |
|---|---|---|
| Client | `TransferProcessor` / `BatchTransferService` | サブシステムを使って業務を遂行する |
| Facade | `IBankTransferService` / `BankTransferService` | クライアントからの要求を適切なサブシステムに委譲する |
| Subsystem | `BankGateway` / `SecurityAuthenticator` | 実際の処理を行う |

#### 使いどころと限界

- サブシステムが複雑で、クライアントが直接扱うには手順が多すぎる場合
- サブシステムとクライアントの依存関係を減らしたい場合

**使わない方がよい状況（過剰コード）：**

```cpp
// Facadeを導入しても元のメソッドをそのまま呼ぶだけで隠蔽の効果がない場合
class SimpleFacade {
    OriginalClass sub;
public:
    void doIt() { sub.doIt(); } // Facadeの意味が薄い
};
```

サブシステムが十分に単純であり、Facadeを介すことでかえってファイル数とクラス数が増えるコストが見合わない場合。

| **状況** | **適切な選択** | **理由** |
|---|---|---|
| 手順が複雑で頻繁に変わる | Facadeを導入する | 呼び出し元を変更から保護するため |
| 単純な委譲のみ | 案1（現状のまま）で十分 | クラスが増えるだけの過剰設計になるため |

#### この章のまとめ

「複雑な手順の呼び出しを隠蔽する」という Facade パターンの導入により、外部システムの手順が変わっても業務ロジックが無傷で済むようになりました。接続点の形が「具体×直接」から「抽象×間接」へと変化し、確実な防波堤が築かれたことを実感できたはずです。
