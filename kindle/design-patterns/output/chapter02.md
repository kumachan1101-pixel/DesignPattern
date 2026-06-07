## 第2章 窓口を一本化する ―― Facade パターン

### この章の核心

**複雑な外部システムの仕様変更が、私たちのビジネスロジック全体に波及してしまう。それは、相手の「詳細な使い方」を私たちが直接知りすぎているからだ。**

### この章を読むと得られること

この章の痛みは「外部システムの詳細を、自社のコードが直接知りすぎている」問題です。

* **得られること1：** 「依存の広がり」という観点で、コードの波及範囲を識別できるようになる
* **得られること2：** 接続点（クラスとクラスのつなぎ目）が「具体×間接」（仲介クラスを経由しているが具体型を直接知っている状態）になっていないクラスを見て、そこが変更の痛みの発生源だと判断できるようになる
* **得られること3：** 複雑な呼び出し手順をカプセル化することで、クライアントコードをスッキリ保つ方法を説明できるようになる
* **得られること4：** 外部システムと自社システムの境界線（窓口）をどこに引くべきか判断できるようになる

## 🔵 フェーズ1：現状把握 ―― 変更が来る前にコードを把握する

システム全体がどのような仕様で動き、どう実装されているのかをフラットな視点で確認していきましょう。まずはこのシステムの背景から見ていきます。

### 1-1：システムの背景

このシステムは、あるネット銀行の振り込み処理を自動化するためのものです。銀行のシステムは非常に堅牢で、安全に送金を行うために、口座情報の確認、残高チェック、手数料の計算、そして実際の送金指示という、いくつもの手順を正しい順番で実行する必要があります。

開発チームは、この銀行のAPIを直接叩いて振り込みを行うプログラムをメンテナンスしています。当初は単純な送金機能だけでしたが、最近では、振り込み先に応じた送金限度額の確認や、二要素認証の呼び出しなど、銀行側から求められるセキュリティ要件が年々厳しくなってきました。



一見すると、このプログラムは一つのクラスの中に必要な手順がすべて網羅されており、手続き通りに順番を追えば良いため、うまく整理されているように見えます。必要な手続きはすべて揃っており、コードを上から下に読めば何が起きているか理解できるため、当初はこれで十分だったのかもしれません。

### 1-2：仕様表


**振り込み処理ルール**

| ルール名 | 発動条件 | 結果 | 具体例 |
| --- | --- | --- | --- |
| 口座確認 | 振り込み先を指定したとき | 口座の存在を確認してから次の処理へ進む | 存在しない口座への送金をブロックする |
| 残高確認 | 口座確認が完了したとき | 送金可能な残高があるかを確認する | 残高不足の場合は送金を中止する |
| 認証コード発行 | 送金実行前の認証ステップ | 銀行からワンタイムパスワードが発行される | 二要素認証の第一段階 |
| 認証コード検証 | 認証コードを受け取ったとき | 発行された認証コードが一致するか検証する | 不一致の場合は送金を中止する |
| 送金実行 | 全確認・認証が完了したとき | 指定した金額を送金先口座に送る | 5,000円を口座12345678へ送金 |

**このルールを使う場所**

同じ振り込み処理を2か所で使います。この「2か所で使う」という仕様が、設計の違いを生む起点になります。

| 使用場所 | 用途 |
| --- | --- |
| `TransferProcessor` | ユーザーが行う通常の振り込み処理 |
| `BatchTransferService` | 給与振り込みなどの一括処理バッチ |

### 1-X：動作例テーブル ―― 仕様を「動かした結果」で確認する

コードを読む前に、このシステムがどんな入力に対してどんな出力を返すかを確認します。この章のどの案も、以下の動作を実現します。

| # | 振り込み先口座 | 送金金額 | 結果 | 適用ルール |
|---|---|---|---|---|
| 1 | 12345678（有効） | 5,000円（残高十分） | 振り込み完了 | 口座確認→残高確認→認証→送金 |
| 2 | 99999999（存在しない） | 5,000円 | エラー：口座なし | 口座確認で中止 |
| 3 | 12345678（有効） | 1,000,000円（残高不足） | エラー：残高不足 | 残高確認で中止 |
| 4 | 12345678（有効） | 5,000円（残高十分） | エラー：認証失敗 | 認証コード検証で中止 |
| 5 | 87654321（有効・バッチ） | 30,000円（残高十分） | 振り込み完了（OTP不要） | 口座確認→残高確認→送金（バッチは社内承認済み） |

これが「このシステムが実現すべき動作」の全体像です。構造をどう変えても、この入出力パターンは変わりません。

### 1-3：クラス構成図

現状のコードがどのような構成になっているかを見てみましょう。`TransferProcessor` が銀行システムの機能に深く依存している様子が見て取れます。

```mermaid
classDiagram
    class TransferProcessor {
        -BankGateway gateway
        -SecurityAuthenticator auth
        +transfer(toAccount, amount)
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

このクラス図から、`TransferProcessor` クラスが `BankGateway` や `SecurityAuthenticator` といった、外部システムと通信するクラスを直接保持し、その複雑な手順を制御しているという事実が見えます。

### 1-4：責任配置テーブル

各クラスが「何を知るべきか」を定義します。

| **クラス名** | **責任（1文）** | **知るべきこと** |
| --- | --- | --- |
| `TransferProcessor` | 振り込みの全体フローを進行する | 銀行との通信手順、認証手順の正しい呼び出し順 |
| `BankGateway` | 銀行APIを呼び出し、口座や送金を操作する | APIの仕様、通信のプロトコル、リクエストの組み立て方 |
| `SecurityAuthenticator` | 銀行システムの認証手順を制御する | 認証の手順、OTP（ワンタイムパスワード）の検証方法 |

各クラスの責任と知識の定義が確認できました。この時点では、`TransferProcessor` が「銀行システムの使い方」をすべて知っているのは、送金という複雑な処理を完了させるために必要なことのように見えます。

### 1-5：依存グラフ

次に、クラス間の「依存の方向」を確認します。

```mermaid
graph TD
    TP["TransferProcessor.cpp"] --> BG["BankGateway.cpp"]
    TP --> SA["SecurityAuthenticator.cpp"]

```

このグラフを見ると、`TransferProcessor` に銀行システムとの通信を担う `BankGateway` と、認証を担う `SecurityAuthenticator` の両方への依存が集中していることが分かります。

### 1-6：実装コード

このシステムは具体的にどのようなコードで動いているのでしょうか。振り込みを実行する起点となるコードを確認します。

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

int main() {
    TransferProcessor processor;
    processor.transfer("12345678", 5000, "999999");
    return 0;
}

```

このコードを見ると、`TransferProcessor` の `transfer` メソッドの中に、銀行APIの手順や認証のフローがそのまま書き込まれていることが分かります。

### 1-7：実行結果

上記コードの実行結果：

```text
口座確認: 12345678
残高確認
認証コード発行
認証コード検証
送金実行: 5000円
振り込み完了
```

このコードは正しく動いています。これから検討するのは、同じ機能を保ちながら、変更に強い構造をどう作るかという点です。

### 1-8：責任チェック表

コードの各行が「誰の判断で変わる知識か」を観察してみましょう。

| **コードの行** | **持っている知識** | **管理者（観察）** |
| --- | --- | --- |
| `gateway.verifyAccount(toAccount);` | 銀行APIの口座確認手順 | 銀行側のシステム仕様変更で変わる |
| `auth.requestOTP();` | 認証のための手順 | 銀行側のセキュリティポリシーで変わる |
| `gateway.executeTransfer(toAccount, amount);` | 送金実行のAPI呼び出し方法 | 銀行側の送金仕様変更で変わる |

`TransferProcessor` クラスの中に、銀行側のAPI仕様や認証手順という、外部システム由来の知識が色濃く混在している様子が見えてきます。

要するに、銀行のAPI呼び出し手順や認証フローが `TransferProcessor` に埋め込まれているという観察から、「業務の流れ（振り込み）」と「外部システムの使い方（API通信や認証手順）」が同じ場所に混在しているという構造の問題が見えてくる。

フェーズ1で責任配置の観察が終わりました。次のフェーズ2では、変更要求を受けて「何が変わり、何が変わらないか」の仮説を立てます。


---

## 🟣 フェーズ2：仮説立案 ―― 変更要求を受けて、変動と不変を整理する

フェーズ1で、銀行システムとの連携処理が `TransferProcessor` クラスに集中している現状を把握しました。このフェーズでは、実際に届いた変更要求を起点にして、「コードのどこが変わり、どこが変わらないか」を整理し、関係者とヒアリングを行いながら設計の方向性を定めます。

### 2-1：届いた変更要求

ある月曜日の朝、銀行のシステム担当者から緊急の連絡が入りました。

「来月から、銀行のAPIの認証仕様が大幅に変更になります。これまでは単一のOTP（ワンタイムパスワード）認証だけで十分でしたが、今後は、まず『認証コードの発行』をリクエストし、その後、銀行から送られてくる『取引ID』とあわせて検証しなければなりません。」

さらに、これに続いて「銀行側の送金APIのインターフェースもセキュリティ強化のため、送金時のパラメータに『トランザクションID』が必須になります」とのこと。

リリースは来月の頭。既存の `TransferProcessor` クラスの中身を書き換え、認証手順や送金手順を今のコードの `transfer` メソッドに直接追加しようとすれば、あっという間に複雑なスパゲッティ状態になってしまうのは目に見えています。

設計に絶対の正解はありません。だからこそ、この変更がどこまで広がるのか、慎重に見極める必要があります。

### 2-2：今回の確定変更テーブル

フェーズ1の観察（責任チェック表）を材料に、今回の変更要求で「確実に変わること」を整理します。これは将来の話ではなく、来月のリリースで必ず発生する変更です。

| **分類** | **確定変更の内容** | **根拠（変更要求から）** |
| --- | --- | --- |
| 🔴 **変動する** | 銀行APIの認証手順（OTP発行＋取引IDとのペア検証） | 認証仕様の変更に伴い、`SecurityAuthenticator` の使い方が根本から変わるため |
| 🔴 **変動する** | 送金APIのパラメータ（トランザクションIDが必須になる） | 送金APIに必須パラメータが増えたため、`BankGateway` の呼び出しコードの修正が必要になるため |
| 🟢 **不変** | 振り込みの全体フロー（口座確認→残高確認→送金） | 銀行APIの仕様が変わっても、私たちの業務としての「振り込み」という流れ自体は変わらないため |

今回の変更は、銀行側の「詳細な使い方（APIの仕様）」に起因するものです。私たちが持っている「振り込み」という業務プロセス自体には、何の影響もありません。

### 2-3：関係者ヒアリング

今回の変更が一時的なものか、将来も続くリスクがあるのかを確認するため、銀行のAPI担当者にヒアリングを行いました。

* **開発者：** 「認証の仕様が変わるとのことですが、今回の変更は一時的なものでしょうか？今後、さらに認証方式が増える予定はありますか？」
* **銀行API担当者：** 「申し訳ありませんが、セキュリティ強化の波は止まりません。数ヶ月後には、生体認証を導入する予定もあります。今後も認証手順はさらに複雑になる可能性が高いです。」
* **開発者：** 「なるほど。送金APIについても、今後パラメータが増えたり、呼び出し順序が変わったりすることは考えられますか？」
* **銀行API担当者：** 「ええ、来年以降には、さらに上位のトランザクション管理システムと連携するため、送金時のリクエスト形式が現在のJSONからXMLへ移行する計画もあります。」
* **開発者：** 「分かりました。かなり頻繁に接続仕様が変わりそうですね。今回の認証フローの変更についても、将来的にさらに手順が増えるリスクはありますか？」
* **銀行API担当者：** 「おっしゃる通りです。現在は二段階認証ですが、将来的には三段階になるかもしれません。現時点での固定的な手順に縛られない設計にしておいた方が、お互いのためかもしれませんね。」

> **現実のヒアリングでは——** このシナリオでは相手がちょうど設計に役立つ情報を教えてくれています。現実には「変わるかどうか分からない」「たぶん変わらない」という答えが返ることも多いです。そのときは、コードの変更履歴（`git log`）や過去の障害記録を「ヒアリングの代わり」として使ってみてください。「過去に何度変わったか」が、「将来変わりやすいか」の最も正直な証拠です。

### 2-4：将来リスクテーブル

ヒアリングの結果、今回の確定変更に加えて、将来発生する可能性がある変化も明らかになりました。これらは確定ではありませんが、設計の方向性を決める上で無視できないリスクです。

| **分類** | **将来リスクの内容** | **変わるタイミング** | **根拠（誰との確認か）** |
| --- | --- | --- | --- |
| 🟡 **将来リスク** | 認証フローの多段階化（二段階→三段階認証） | 銀行側のセキュリティ強化時 | 銀行API担当者との確認 |
| 🟡 **将来リスク** | 送金リクエスト形式の変更（JSON→XML移行計画） | 来年以降の基幹システム連携時 | 銀行API担当者との確認 |
| 🟡 **将来リスク** | 生体認証の導入 | 数ヶ月後の予定 | 銀行API担当者との確認 |
| 🟢 **不変** | 振り込みという業務プロセス | 変わらない | チーム内での合意 |

テーブルを見ると、私たちが今解決すべき課題が浮かび上がってきました。
それは、銀行システムという「変動する詳細な使い方」を、私たちの「振り込み」という業務プロセスからどうやって切り離すか、という問題です。

フェーズ2で「今回確実に変わること」と「将来変わりうるリスク」が整理できました。次のフェーズ3では、今のコードでこの変更を試みたときに何が起きるかを確認します。

## 🟣 フェーズ3：問題特定 ―― 変更を試みて、痛みを発見する

フェーズ2で、銀行APIの認証仕様変更という「将来的に繰り返されるであろう変更要求」が確定しました。このフェーズでは、その変更要求を今のコードのまま適用しようとしたとき、システムにどのような「痛み」が生じるのかを観察していきます。

### 3-1：変更シミュレーション

さっそく、銀行から要求された「認証フローの変更（発行と検証の2段階化）」と「送金時のトランザクションID付与」を、現在の `TransferProcessor` クラスの `transfer` メソッドに直接書き込む作業を試みてみましょう。

```cpp
void transfer(
        const std::string& toAccount, int amount,
        const std::string& otp) {
    gateway.verifyAccount(toAccount);
    gateway.checkBalance(toAccount);
    
    // 【痛み：認証の手順が変わる】
    // 既存のコードを書き換える必要がある
    auth.requestOTP(); 
    // 銀行から発行された取引IDを保持しなければならない
    std::string transactionId = auth.getTransactionId(); 
    // 検証時に取引IDを渡す必要がある
    auth.verifyOTP(otp, transactionId); 
    
    // 【痛み：送金APIの仕様が変わる】
    // TxIDを生成し、送金時に渡さなければならない
    std::string txId = generateTxId();
    gateway.executeTransfer(toAccount, amount, txId);
    
    std::cout << "振り込み完了\n";
}

```

この変更を試みたとき、まず気づくのは `TransferProcessor` クラスが、「銀行APIの細かな使い方」をあまりにも詳細に知りすぎているという点です。認証のステップが増えただけでメソッドのシグネチャ（引数や戻り値）を追いかける必要があり、ロジックの修正が連鎖的に発生してしまいます。

「振り込みを実行する」という業務上の命令を処理しているはずの `TransferProcessor` が、銀行システム側から送られてくる「取引IDを保持する」といった一時的な状態管理まで背負わされています。銀行側のAPI仕様が一つ変わるたびに、私たちの業務フローを制御するクラスのコードを書き換え、その結果、振り込み処理全体のテストをやり直さなければならないのです。

### 3-2：変更影響グラフ

変更を試みようとしたときに頭の中で起きた「影響の広がり」を図にしてみます。

```mermaid
graph LR
    T1["変更要求：API変更"] -->|"飛び火"| A["TransferProcessor.cpp"]
    A -->|"影響"| B["BankGateway.cpp"]
    A -->|"影響"| C["SecurityAuthenticator.cpp"]

```

このグラフを見ると、銀行APIの仕様という「外部システム都合の変更」が、私たちの業務フローの中枢である `TransferProcessor` を経由して、通信クラスや認証クラス全体に飛び火していることが分かります。

### 3-3：痛みの言語化

変更を試みてみた結果、私たちが現場でよく直面する2つの辛い状況がより鮮明になりました。

1つ目は、銀行側の都合による「仕様変更の波」に、私たちの業務ロジックが直接さらされてしまうことです。
今回の認証フローの変更は、本来であれば「振り込み」という業務プロセスには影響しないはずのものです。しかし、今の構造では、銀行APIという「外部システムの使い方」を `TransferProcessor` が直接知っているため、APIの引数が増えたり手順が変わったりするたびに、業務フローを記述している核心部分を書き換える羽目になります。まるで、銀行側の仕様変更という嵐の中に、私たちの心臓部が直接さらされているようなものです。

2つ目は、複雑な手続きの連鎖が「振り込み」の目的を見えにくくしていることです。
コードを見れば、口座確認、残高確認、認証発行、検証、送金実行と、手続きが淡々と並んでいます。しかし、新しい仕様に対応するために一時的なIDを保持したり、条件分岐を足したりすることで、コードは「何のために振り込んでいるのか」という業務上の目的よりも、「銀行のAPIにどうやって命令を通すか」という、技術的な手順の記述で埋め尽くされてしまいました。

「今のままだと、銀行側のAPIが新しくなるたびに、私たちは振り込みの処理フローを壊すリスクを背負い続けることになる」という感覚が伝わっているでしょうか。まずは現状の辛さを言語化することが、良い設計への第一歩になります。

フェーズ3で「変更が辛い」という事実が確認できました。次のフェーズ4では、なぜ辛いのかを構造的に言語化します。

## 🟠 フェーズ4：原因分析 ―― 「なぜ辛いのか」を構造的に言語化する

フェーズ3で、銀行APIの仕様変更が私たちの業務コードに直接飛び火し、変更のたびにコードの核心部分を書き換えなければならないという痛みが確認できました。このフェーズでは、なぜそのような痛みが生まれるのかを、コードの構造（接続形態）の観点から言語化していきます。

### 4-1：観察→原因テーブル

フェーズ3で観察した「痛み」と、その裏にある構造的な原因を紐解いてみましょう。

| **観察** | **原因の方向** |
| --- | --- |
| 認証フローやAPI仕様が変わるたびに、業務フローを記述している `TransferProcessor` が修正を強いられる | `TransferProcessor` クラスが、銀行システムの「詳細な使い方（APIの認証手順やパラメータ）」を直接知っているから |
| 複雑な手順が並び、本来の「振り込み」という目的が見えにくくなっている | 「振り込みという業務プロセス」と「銀行APIの技術的な利用手順」が、同じメソッドの中に混在しているから |

### 4-2：変わるもの / 変わらないものテーブル

原因がはっきりしてくると、どこに境界線を引くべきかが見えてきます。「変わる側」をカプセル化（呼び出し元が知らなくていい詳細を隠すこと）できれば、「変わらない側」である業務ロジックは安定します。

| **変わり続けるもの（🔴）** | **変わってほしくないもの（🟢）** |
| --- | --- |
| 銀行APIの認証手順（発行・検証のステップ） | 振り込みの全体フロー（口座確認→残高確認→送金） |
| 送金APIのパラメータ（IDの追加や型変更） | 振り込みという業務上の目的 |

### 4-3：接続形態を診断する

現在の `TransferProcessor` は、銀行のAPIという「特定の機器」に対して、専用のケーブルを直に配線しているような状態です。

この接続形態は、iPhoneに専用のLightningケーブルを直差ししている状態（具体×直接）だと診断できます。認証方式が変わり、送金時のパラメータが増えるたびに、私たちはその専用端子に合わせてコードという名の「配線」を直接付け替えなければなりません。これでは、銀行側の仕様変更が起こるたびに、私たちの業務フローを制御するクラスの心臓部を切り刻むことになってしまいます。

本来であれば、業務ロジック側は「振り込みたい」という命令を送るだけでよく、具体的な接続手順は窓口の向こう側に隠すべきです。

|  | 直接（直差し） | 間接（アダプター経由） |
|:---:|:---|:---|
| **具体**（専用規格） | **← 現在地**　iPhone → [Lightning] → Apple純正ドック（Lightning端子） | iPhone → [Lightning] → [変換] → USB-A充電器（汎用端子） |
| **抽象**（汎用規格） | MacBook → [USB-C] → USB-C対応モニター（汎用端子） | MacBook → [USB-C] → [ハブ] → HDMI・USB-A・LAN |

このコードで言うと：

| ケーブル比喩 | コードの対応箇所 |
|---|---|
| 「具体」＝専用規格ケーブル | `BankGateway gateway;` / `SecurityAuthenticator auth;` — 銀行APIの具体クラス名を `TransferProcessor` がメンバとして直接宣言している |
| 「直接」＝直差し | `gateway.verifyAccount(toAccount); auth.requestOTP();` など — 窓口なしに各APIメソッドを `transfer()` 内で直接順に呼び出している |

銀行の認証フローや送金APIの使い方は、私たちの業務フローとは「変わる理由」が異なるため、業務フローから切り離すべき存在です。

フェーズ4で根本原因が言語化できました。次のフェーズ5では、解決すべき問題を具体的に定めます。

## 🟡 フェーズ5：課題定義 ―― 解くべき問題を具体的に定める

フェーズ4で「銀行APIの接続手順」と「振り込みという業務プロセス」が密接に絡み合い、互いの変更理由を引きずり合っているという構造的問題が明らかになりました。対策案（フェーズ6）に進む前に、ここで「何を解くべき課題とするか」を具体的に確定させます。

### 5-1：接続点の特定

今回のリファクタリングにおいて、もっとも深刻な影響が出ている場所、つまり、解決すべき「接続点（ジョイント）」は以下の1箇所です。

* **接続点A：** `TransferProcessor`（業務フロー管理クラス） ←→ `BankGateway` ＋ `SecurityAuthenticator`（外部システム利用クラス）の境界

この接続点は、「振り込み」という業務上の命令と、「銀行APIを叩く」という技術的な手順が直接つながっている場所です。ここを切り離すことで、銀行側の仕様変更が業務フローを破壊する波及を止めることが課題となります。

### 5-2：非機能制約の確認

このシステムの規模では、クラス分割によるパフォーマンスオーバーヘッドや仮想関数のコストは設計判断を絞り込む制約になりません。唯一注意すべき点は、銀行APIがネットワーク障害で失敗したときの再試行と**二重送金防止（べき等性の保証）**です。外部API呼び出しの集約先がどのクラスになるかという構造の選択が、この実装しやすさに直接影響します。この点は案4の選定に影響するため、案4のトレードオフで触れます。

### 5-3：クライアントへの影響範囲

「接続点A」を変えることで、どのクラスに修正が及ぶかを確認します。

現在の `TransferProcessor` クラスがこの接続点のクライアントです。`TransferProcessor` は銀行の具体的なゲートウェイや認証のクラスを直接持っているため、この境界を抽象化して切り離す設計変更を行うと、`TransferProcessor` クラス自身のコンストラクタやメンバ変数の定義を変更する必要があります。

しかし、一度切り離してしまえば、以降の銀行側の変更時には `TransferProcessor` に一切手を触れることなく、裏側の接続用クラスを差し替えるだけで済むようになります。

### 5-4：課題まとめ表

以上の情報をまとめ、フェーズ6での対策案検討の基盤となる課題定義を確定させます。

| **接続点** | **分けた理由** | **非機能制約** | **クライアント影響** |
| --- | --- | --- | --- |
| 接続点A | 外部システムという「変わる理由」を業務フローから隔離するため | 障害時のリトライと二重送金防止のべき等性設計が必要 | `TransferProcessor` の内部実装に影響あり |

フェーズ5で「何を解くか」が具体化されました。次のフェーズ6では、この課題に対してどのような「接続の形」を採用すべきか、案1〜案4を並べてコスト比較を行います。

## 🔴 フェーズ6：対策案検討 ―― 解決策を並べ、コストで選ぶ

フェーズ5の課題定義で、業務フロー（`TransferProcessor`）と外部システム（銀行API群）の間の接続点を切り離すべきだと確認しました。このステップで最も重要なことは、「最初からどうコードを書くか」を決めないことです。課題の形が決まれば、そこをつなぐ「接続の形」の選択肢は自然と導き出されます。

どの案も、動作例テーブルで示した動作を実現します。違うのは「変更が来たときにどこを触ることになるか」です。

---

### 6-1：接続の形 2×2マトリクス

現在の `TransferProcessor` と外部システム群との接続は、銀行のAPIという「特定の仕様」に対して、コードという配線を直にハンダ付けしている状態（具体×直接）です。ここから、今後予想される「認証手順の複雑化」や「APIの仕様変更」に耐えうる柔軟な接続形態へ移行するため、以下の4つの案を検討します。

| 接続形態 | ケーブル例 | 特徴 |
|:---:|:---|:---|
| **具体×直接**（← 現在地） | iPhone → [Lightning] → Apple純正ドック（Lightning端子） | 専用端子のみ対応。差し替え不可 |
| **具体×間接** | iPhone → [Lightning] → [変換] → USB-A充電器（汎用端子） | 変換器を挟むが規格は専用のまま |
| **抽象×直接** | MacBook → [USB-C] → USB-C対応モニター（汎用端子） | どのメーカーでも同じ口で繋がる |
| **抽象×間接** | MacBook → [USB-C] → [ハブ] → HDMI・USB-A・LAN | ハブを介して多様な機器へ展開可能 |

---

#### 案1：現状のまま ―― 構造を変えない

**この形の考え方：**
クラスの分割やインターフェースの導入を行わず、既存の `transfer` メソッドの中に、銀行APIの新しい仕様を `if` 文で追加します。銀行側の接続仕様が極めて安定しており、今後数年は変更が来ないような場合にのみ、実装コストを最小化するための選択肢となります。

**手段の比較：**

| 手段 | 方法 | 特徴 |
|---|---|---|
| 手段A：条件分岐の直書き | `if` 文で新旧仕様を `transfer()` 内に並べる | コード量は最少だが、条件が増えるたびにメソッドが肥大化する |
| 手段B：メソッド分割 | 認証手順を別メソッドに切り出し、`transfer()` から呼ぶ | 少しだけ読みやすくなるが、クラス内の依存は変わらない |

→ **採用：手段A**（構造を変えないという方針に忠実なため。手段Bも構造的には同じ問題を抱える）

**構造図：**

```mermaid
classDiagram
    class TransferProcessor {
        <<if分岐を直書き>>
        +transfer(toAccount, amount, otp)
    }
    class BatchTransferService {
        <<同じif分岐が重複>>
        +processPayroll(transfers)
    }
    class BankGateway {
        +verifyAccount(account)
        +checkBalance(account)
        +executeTransfer(account, amount, txId)
    }
    class SecurityAuthenticator {
        +requestOTP()
        +verifyOTP(token)
    }
    TransferProcessor ..> BankGateway : 具体×直接
    TransferProcessor ..> SecurityAuthenticator : 具体×直接（重複）
    BatchTransferService ..> BankGateway : 具体×直接（重複）
```

両クラスが銀行APIの呼び出し手順を内部に直書きしており、外部への依存矢印ではなく内部の重複ロジックが問題の核心です。

**実装コード：**

まず、銀行APIと認証を担う既存クラスを確認します。

```cpp
// 銀行との通信を担うクラス（変更なし）
class BankGateway {
public:
    void verifyAccount(const std::string& account) {
        std::cout << "口座確認: " << account << "\n";
    }
    void checkBalance(const std::string& account) {
        std::cout << "残高確認\n";
    }
    void executeTransfer(const std::string& account, int amount,
                         const std::string& txId) {
        std::cout << "送金実行: " << amount << "円\n";
    }
};

// 認証を担うクラス（変更なし）
class SecurityAuthenticator {
public:
    void requestOTP() { std::cout << "認証コード発行\n"; }
    void verifyOTP(const std::string& token, const std::string& txId) {
        std::cout << "認証コード検証\n";
    }
};
```

このコードで分かること：`BankGateway` と `SecurityAuthenticator` は変更されていないが、呼び出し側で仕様の変化を全部吸収しなければならない。

次に、呼び出し元の `TransferProcessor` と `BatchTransferService` を見ます。

```cpp
// 振り込み処理クラス（呼び出し元1）
class TransferProcessor {
    BankGateway gateway;
    SecurityAuthenticator auth;
public:
    void transfer(
            const std::string& toAccount, int amount,
            const std::string& otp) {
        gateway.verifyAccount(toAccount);
        gateway.checkBalance(toAccount);
        // 新しい認証手順をif文でねじ込む
        // ← 具体：条件を呼び出し側が直接書いている
        if (/* 新仕様 */) {
            auth.requestOTP();
            std::string txId = auth.getTransactionId();
            auth.verifyOTP(otp, txId);
        } else {
            auth.requestOTP();
            auth.verifyOTP(otp, "");
        }
        gateway.executeTransfer(toAccount, amount, generateTxId());
        std::cout << "振り込み完了\n";
    }
};

// 給与振り込みなどの一括処理バッチ（呼び出し元2）
// ← 案1の問題：同じ銀行API手順を重複して持つことになる
class BatchTransferService {
    BankGateway gateway;         // ← 同じ具体クラスを再度保持
    SecurityAuthenticator auth;  // ← 同じ具体クラスを再度保持
public:
    void processPayroll(
            const std::vector<std::pair<std::string, int>>& transfers) {
        for (const auto& [account, amount] : transfers) {
            // ← TransferProcessorと全く同じ手順が重複している
            gateway.verifyAccount(account);
            gateway.checkBalance(account);
            gateway.executeTransfer(account, amount, generateTxId());
        }
    }
};
```

このコードで分かること：銀行APIの呼び出し手順が `TransferProcessor` と `BatchTransferService` の両方に重複して書かれており、銀行APIの仕様が変わるたびに2箇所を同時に修正しなければなりません。

**呼び出し側から見た違い（main() 例）：**

```cpp
// 案1（現状のまま）の呼び出し側
int main() {
    TransferProcessor processor;
    processor.transfer("12345678", 5000, "999999");

    BatchTransferService batch;
    batch.processPayroll({{"87654321", 30000}, {"11112222", 25000}});
    return 0;
}
```

銀行APIの呼び出し手順が各クラスの内部に直書きされているため、同じ手順が2か所で並行して走ります。

**この形のトレードオフ：**

* 変更容易性：低（銀行APIが変わるたびに業務フローであるメソッドが破壊される）
* テスト容易性：低（銀行APIと業務フローが分離されておらずテスト困難）
* 実装コスト：低（今のコードに数行足すだけ）

---

#### 案2：具体×直接 ―― クラスを分けるが参照は具体型のまま

**この形の考え方：**
銀行通信用のクラスを切り出して責任を分担させますが、呼び出し側の `TransferProcessor` は、相変わらず銀行専用クラス（`BankGateway` 等）の具体型を直接知っている状態です。「責任の分担」という第一段階の整理だけを行いたい場合に合う形です。

**手段の比較：**

| 手段 | 方法 | 特徴 |
|---|---|---|
| 手段A：コンストラクタ注入 | `TransferProcessor(BankTransferService* s)` でポインタを受け取る | 呼び出し元が生成して注入するため、生成と使用が分離される |
| 手段B：メンバ変数で直接生成 | `BankTransferService service;` をメンバとして内部で生成する | シンプルだが、外部から差し替えが一切できない |

→ **採用：手段A**（注入方式にすることで、将来的なテスト時に差し替えの余地が生まれるため）

**構造図：**

```mermaid
classDiagram
    class TransferProcessor {
        -BankTransferService service
        +transfer(toAccount, amount, otp)
    }
    class BatchTransferService {
        -BankTransferService service
        +processPayroll(transfers)
    }
    class BankTransferService {
        +execute(account, amount, otp)
    }
    TransferProcessor --> BankTransferService : 具体×直接
    BatchTransferService --> BankTransferService : 具体×直接（重複）
```

2つの呼び出し元がどちらも `BankTransferService` という同じ具体クラスを直接参照しており、依存の重複が構造として見えます。

**実装コード：**

通信ロジックを切り出した `BankTransferService` クラスです。

```cpp
// 通信ロジックを切り出したクラス
// ← 具体：BankTransferServiceという型名を直接書いている
class BankTransferService {
public:
    void execute(const std::string& account, int amount,
                 const std::string& otp) {
        std::cout << "口座確認: " << account << "\n";
        std::cout << "残高確認\n";
        std::cout << "認証コード発行\n";
        std::cout << "認証コード検証\n";
        std::cout << "送金実行: " << amount << "円\n";
    }
};
```

このコードで分かること：銀行APIの呼び出し手順が `BankTransferService` に集約されたが、呼び出し元はこの具体クラスを名指しで知らなければならない。

次に、呼び出し元の2クラスです。

```cpp
// TransferProcessorは具体型を直接知っている
class TransferProcessor {
    BankTransferService* service;  // ← 直接：具体型を直接保持
public:
    TransferProcessor(BankTransferService* s) : service(s) {}
    void transfer(const std::string& toAccount, int amount,
                  const std::string& otp) {
        service->execute(toAccount, amount, otp);
        std::cout << "振り込み完了\n";
    }
};

// 給与振り込みなどの一括処理バッチ（呼び出し元2）
class BatchTransferService {
    // ← 直接：同じ具体クラスをここでも直接保持
    BankTransferService* service;
public:
    BatchTransferService(BankTransferService* s) : service(s) {}
    void processPayroll(
            const std::vector<std::pair<std::string, int>>& transfers) {
        // ← 選択ロジックがここにも重複している
        for (const auto& [account, amount] : transfers) {
            service->execute(account, amount, "");  // バッチはOTP不要
        }
    }
};
```

このコードで分かること：通信ロジックは別クラスに切り出せましたが、`TransferProcessor` も `BatchTransferService` も `BankTransferService` という具体クラスを直接知っており、その依存関係が両方に重複しています。

**呼び出し側から見た違い（main() 例）：**

```cpp
// 案2（具体×直接）の呼び出し側
int main() {
    // ← 直接：呼び出し側が具体クラスを直接生成
    BankTransferService service;
    TransferProcessor processor(&service);
    processor.transfer("12345678", 5000, "999999");

    // ← 直接：同じ具体クラスをここでも直接生成
    BatchTransferService batch(&service);
    batch.processPayroll({{"87654321", 30000}, {"11112222", 25000}});
    return 0;
}
```

クラスは分かれたが「どのクラスを呼ぶか」という判断を両方の呼び出し元がそれぞれ行っており、呼び出し経路が2本並んで重複しています。

**この形のトレードオフ：**

* 変更容易性：低〜中（APIクラスのインターフェースが変わると、Processor側も修正が必要）
* テスト容易性：低（具体クラスを生成しているため、切り離しができない）
* 実装コスト：低（既存コードを別のクラスにコピー＆ペーストする程度）

---

#### 案3：抽象×直接 ―― インターフェースを挟み、型だけで接続する

**この形の考え方：**
銀行APIの具体的な実装を隠すためにインターフェースを導入し、業務クラスはインターフェース型に対してプログラムします。これにより、APIの実装が銀行Aから銀行Bへ変わろうと、私たちの業務クラスは影響を受けません。

**手段の比較：**

| 手段 | 方法 | 特徴 |
|---|---|---|
| 手段A：コンストラクタインジェクション | `TransferProcessor(IBankService* s)` でインターフェース型を受け取る | テスト時にスタブ（本物のAPIの代わりに動く模擬実装）を差し込みやすい。最も一般的 |
| 手段B：セッターインジェクション | `setService(IBankService* s)` で後から注入する | 生成後に差し替えできるが、未設定状態が生まれやすい |
| 手段C：継承 | `TransferProcessor` が `IBankService` を継承する | インターフェースと呼び出し元が同一クラスになり責任が混在する |

→ **採用：手段A**（コンストラクタ注入は「生成時に依存が確定する」ため未設定状態が生まれず、最もシンプルで安全なため）

※スタブ：テストを実施するときに、本物のクラスの代わりに用意する「偽物の部品」のこと。本物の銀行APIを呼ばずにテストするために必要になります。

**構造図：**

```mermaid
classDiagram
    class IBankService {
        <<interface>>
        +send(acc, amt)
    }
    class BankTransferService {
        +send(acc, amt)
    }
    class TransferProcessor {
        -IBankService service
        +transfer(toAccount, amount, otp)
    }
    class BatchTransferService {
        -IBankService service
        +processPayroll(transfers)
    }
    BankTransferService ..|> IBankService : 実装
    TransferProcessor --> IBankService : 抽象×直接
    BatchTransferService --> IBankService : 抽象×直接
```

両クラスが `IBankService` インターフェースだけを知り、`main()` だけが具体クラスを生成・注入する構造です。

**実装コード：**

まず、業務上の窓口となるインターフェースと、その実装クラスを確認します。

```cpp
// 共通の窓口（インターフェース）
class IBankService {
public:
    virtual void send(const std::string& acc, int amt) = 0;
};

// 銀行APIの具体的な実装
class BankTransferService : public IBankService {
public:
    void send(const std::string& acc, int amt) override {
        std::cout << "口座確認: " << acc << "\n";
        std::cout << "残高確認\n";
        std::cout << "認証コード発行\n";
        std::cout << "認証コード検証\n";
        std::cout << "送金実行: " << amt << "円\n";
    }
};
```

このコードで分かること：`BankTransferService` が `IBankService` を実装しており、呼び出し元はこの具体クラスを知らなくてよくなる。

次に、インターフェース型だけを知る2つの呼び出し元クラスです。

```cpp
// 振り込み処理クラス（呼び出し元1）
class TransferProcessor {
private:
    // ← 抽象：IBankService*型で受け取る
    IBankService* service;
public:
    TransferProcessor(IBankService* s) : service(s) {}
    void transfer(const std::string& toAccount, int amount,
                  const std::string& otp) {
        service->send(toAccount, amount);
        std::cout << "振り込み完了\n";
    }
};

// 給与振り込みなどの一括処理バッチ（呼び出し元2）
class BatchTransferService {
private:
    // ← 抽象：同じIBankService*型で受け取る
    IBankService* service;
public:
    BatchTransferService(IBankService* s) : service(s) {}
    void processPayroll(
            const std::vector<std::pair<std::string, int>>& transfers) {
        // ← 抽象：IBankService経由で送金
        for (const auto& [account, amount] : transfers) {
            service->send(account, amount);
        }
    }
};
```

このコードで分かること：`TransferProcessor` も `BatchTransferService` も `IBankService` というインターフェースだけを知っており、銀行APIの具体的な実装に一切依存していません。

**呼び出し側から見た違い（main() 例）：**

```cpp
// 案3（抽象×直接）の呼び出し側
int main() {
    // ← 具体：呼び出し側だけが具体クラスを生成
    BankTransferService bankService;
    TransferProcessor processor(&bankService);  // ← 直接：注入
    BatchTransferService batch(&bankService);   // ← 直接：使い回せる
    processor.transfer("12345678", 5000, "999999");
    batch.processPayroll({{"87654321", 30000}, {"11112222", 25000}});
    return 0;
}
```

`main()` が具体型を組み立て、両方の呼び出し元は `IBankService*` という型だけを介して同じオブジェクトを呼ぶため、具体クラスが変わっても呼び出し経路は変わりません。

**この形のトレードオフ：**

* 変更容易性：中〜高（実装が変わっても、業務フロー側は影響を受けない）
* テスト容易性：高（I/Fにスタブを差し込んでテストできる）
* 実装コスト：中（インターフェースの設計が必要）

---

#### 案4：抽象×間接 ―― インターフェース＋仲介役を両立する

**この形の考え方：**
`TransferProcessor` に対しては抽象的な窓口を提供し、かつその窓口の中で具体的なAPIの複雑な手順を隠蔽します。最も柔軟ですが、全層にインターフェースと仲介クラスを導入するため、実装コストは最大になります。

**手段の比較：**

| 手段 | 方法 | 特徴 |
|---|---|---|
| 手段A：インターフェース＋仲介クラス | `IBankServiceWindow` インターフェースと `BankServiceWindow` 実装クラスの2層構成 | 最も変更に強い。呼び出し元は型すら変わらない |
| 手段B：抽象基底クラス＋仲介クラス | 純粋仮想クラスではなく継承可能な基底クラスを使う | 部分的な実装を基底クラスに置けるが、継承の硬直性がある |

→ **採用：手段A**（純粋なインターフェースにすることで、将来スタブやモック（スタブに加えて呼び出し記録の検証もできる模擬実装）差し替えが最もシンプルになるため）

**構造図：**

```mermaid
classDiagram
    class IBankServiceWindow {
        <<interface>>
        +transfer(acc, amt)
    }
    class BankServiceWindow {
        -BankGateway gateway
        -SecurityAuthenticator auth
        +transfer(acc, amt)
    }
    class TransferProcessor {
        -IBankServiceWindow facade
        +transfer(toAccount, amount, otp)
    }
    class BatchTransferService {
        -IBankServiceWindow facade
        +processPayroll(transfers)
    }
    class BankGateway {
        +verifyAccount(account)
        +executeTransfer(account, amount, txId)
    }
    class SecurityAuthenticator {
        +requestOTP()
        +verifyOTP(token)
    }
    BankServiceWindow ..|> IBankServiceWindow : 実装
    TransferProcessor --> IBankServiceWindow : 抽象×間接
    BatchTransferService --> IBankServiceWindow : 抽象×間接
    BankServiceWindow --> BankGateway : 具体×直接
    BankServiceWindow --> SecurityAuthenticator : 具体×直接
```

インターフェース層（`IBankServiceWindow`）と仲介層（`BankServiceWindow`）の2層を挟むことで、両クラスは具体実装を一切知らない。変更影響が最も局所化された構造です。

**実装コード：**

まず、インターフェースの宣言です。

```cpp
// 抽象的な窓口（インターフェース）
class IBankServiceWindow {
public:
    virtual void transfer(const std::string& acc, int amt) = 0;
};
```

このコードで分かること：呼び出し元が知るのはこの1行だけ。銀行APIの内部構造は完全に見えない。

次に、複雑な手順を内部に隠す仲介クラスです。

```cpp
// 銀行APIとの複雑なやり取りをすべて隠蔽する仲介クラス
class BankServiceWindow : public IBankServiceWindow {
    BankGateway gateway;
    SecurityAuthenticator auth;
public:
    void transfer(const std::string& acc, int amt) override {
        gateway.verifyAccount(acc);
        gateway.checkBalance(acc);
        auth.requestOTP();
        auth.verifyOTP("TXN12345", "token");
        gateway.executeTransfer(acc, amt, "TXN12345");
        std::cout << "送金実行完了\n";
    }
};
```

このコードで分かること：`BankGateway` と `SecurityAuthenticator` という具体クラスを `BankServiceWindow` だけが知っており、呼び出し元には一切見えない。

最後に、インターフェース型だけを知る2つの呼び出し元クラスです。

```cpp
// 振り込み処理クラス（呼び出し元1）
class TransferProcessor {
private:
    // ← 抽象：IBankServiceWindow*型で受け取り、具体実装を知らない
    // ← 間接：Facadeを経由するため内部クラス群が見えない
    IBankServiceWindow* facade;
public:
    TransferProcessor(IBankServiceWindow* f) : facade(f) {}
    void transfer(const std::string& toAccount, int amount,
                  const std::string& otp) {
        facade->transfer(toAccount, amount);
        std::cout << "振り込み完了\n";
    }
};

// 給与振り込みなどの一括処理バッチ（呼び出し元2）
class BatchTransferService {
private:
    IBankServiceWindow* facade;  // ← 抽象：IBankServiceWindow*型
public:
    BatchTransferService(IBankServiceWindow* f) : facade(f) {}
    void processPayroll(
            const std::vector<std::pair<std::string, int>>& transfers) {
        for (const auto& [account, amount] : transfers) {
            facade->transfer(account, amount);
        }
    }
};
```

このコードで分かること：変更の影響は最も小さく抑えられますが、ファイル数が一気に増え、システム全体の繋がりを追うのが非常に難しくなっています。

**呼び出し側から見た違い（main() 例）：**

```cpp
// 案4（抽象×間接）の呼び出し側
int main() {
    BankServiceWindow facade;                         // ← 具体：組み立て側だけが具体型を知る
    TransferProcessor processor(&facade);      // ← 間接：抽象Facadeのみ見えて具体実装は隠れる
    BatchTransferService batch(&facade);       // ← 間接：同じFacadeを共有
    processor.transfer("12345678", 5000, "999999");
    batch.processPayroll({{"87654321", 30000}, {"11112222", 25000}});
    return 0;
}
```

**動作図：**

```mermaid
sequenceDiagram
    participant main
    participant BF as BankServiceWindow
    participant TP as TransferProcessor
    participant BTS as BatchTransferService
    participant BG as BankGateway
    Note over main: 具体型を組み立てる唯一の場所
    main->>BF: new BankServiceWindow
    main->>TP: new（facade: IBankServiceWindow*）
    main->>BTS: new（facade: IBankServiceWindow*）
    main->>TP: transfer(account, amount, otp)
    TP->>BF: facade->transfer(account, amount)
    Note right of TP: IBankServiceWindow* 経由
    BF->>BG: 内部で複雑な手順を実行
    Note right of BF: IBankServiceWindow* 経由
    BG-->>BF: 完了
    BF-->>TP: 処理完了
    TP-->>main: 振り込み完了
    main->>BTS: processPayroll(transfers)
    BTS->>BF: facade->transfer(account, amount)
    BF->>BG: 内部で複雑な手順を実行
    BG-->>BF: 完了
    BF-->>BTS: 処理完了
    BTS-->>main: 処理完了
```

呼び出し元→`IBankServiceWindow*`→内部の具体実装という2段階の経由により、どの具体クラスが動くかは `main()` の組み立て部分だけが知っています。

**この形のトレードオフ：**

* 変更容易性：高（どの層の変更も他層に影響しない）
* テスト容易性：高（Facade をスタブに差し替え可能）
* 実装コスト：高（インターフェースと仲介クラスが必須となる）
* ※ 障害時のリトライと二重送金防止：`BankServiceWindow` が銀行API呼び出しを一箇所に集約しているため、再試行ロジックとべき等性の保証（同一振り込みが二重実行されない仕組み）をここに実装できる。`TransferProcessor` はこれを一切意識する必要がない。

### 6-7：評価軸

対策案が揃ったところで、どの案を採用すべきかを決めるための「ものさし」を宣言します。後から基準を持ち出すと議論が混迷しやすいため、比較表を提示する前に、チーム内で評価軸とその重要度を合意しておくことが大切です。

今回の銀行システム連携では、以下の3軸で評価を行います。

| **評価軸** | **意味** | **ウェイト** |
| --- | --- | --- |
| 変更容易性 | 変更要求が来たとき、触る場所が最小で済むか | ×3 |
| テスト容易性 | 依存をスタブ/モックに差し替えてテストを書けるか | ×2 |
| 可読性 | コードの読みやすさ・構造を理解する工数 | ×1 |

> **注：** このウェイト（変更容易性×3など）は本書の例です。チームの変更頻度・テスト文化に合わせて、比較を始める前にチームで合意してください。スコアは「答えを決める計算式」ではなく、「チームの議論を整理する道具」です。

採点基準は、全章共通で以下の通りとします。

| 点数 | 変更容易性 | テスト容易性 | 可読性 |
| --- | --- | --- | --- |
| 3 | 変更が1クラスのみで完結する | スタブ1つで完全に切り離せる | クラス数が増えない・既存構造と同じ読み方で理解できる |
| 2 | 変更が2〜3クラスに及ぶ | 一部スタブが必要だが差し替え可能 | クラスが1〜2増える |
| 1 | 変更が4クラス以上に波及する | 実装に依存しテストが困難 | 中間層・インターフェースが複数増え理解コストが高い |

パフォーマンスのVETO（拒否権）については、フェーズ5で「ホットパスではない」と判断したため、今回はスコアリングを優先して検討します。

---

### 6-8：コスト天秤

案1〜案4を定量的に比較します。

| **案** | **現在の対応コスト** | **未来の対応コスト** |
| --- | --- | --- |
| 案1：現状のまま | 低 | 高 |
| 案2：具体×直接 | 低〜中 | 高 |
| 案3：抽象×直接 | 中 | 低〜中 |
| 案4：抽象×間接 | 高 | 低 |

**ステップ1：採点表**

| 案 | 変更容易性（×3） | テスト容易性（×2） | 可読性（×1） |
| --- | --- | --- | --- |
| 案1：現状のまま | 1 | 1 | 3 |
| 案2：具体×直接 | 1 | 2 | 3 |
| 案3：抽象×直接 | 2 | 3 | 2 |
| 案4：抽象×間接 | 3 | 3 | 1 |

**ステップ2：加重合計表**

| 案 | 加重スコア | 判定 |
| --- | --- | --- |
| 案1 | 8 |  |
| 案2 | 10 |  |
| 案3 | 14 | 次点 |
| 案4 | 16 | ← 最終採用 |

**案3 vs 案4 の最終判断：** スコア上は案4（16点）が案3（14点）を上回ります。ただし、スコアはトレードオフの見える化であり「最高点＝採用」ではありません。ここでは次の問いに答えて判断します——「フェーズ2で予告されたリスクが来たとき、どちらの案が変更を1クラスに閉じられるか？」。案3では、認証フロー変更や JSON→XML 移行のたびに `IBankService` を実装する具体クラスを修正し、さらに呼び出し元（`TransferProcessor`）への影響確認も必要です。案4は仲介クラスが銀行APIの複雑さを完全に隠蔽するため、将来の変更を「窓口クラス1つの修正」に閉じ込められます。この将来コストの差が、可読性スコアの差を上回ると判断し、案4を採用します。

---

### 6-9：採用案の決定

**採用する案：** 案4

ここで一度立ち止まります。採点表では案3（抽象×直接）が14点、案4（抽象×間接）が16点でした。フェーズ2のヒアリングで確認した将来リスクを振り返ると、「認証フローの三段階化」「JSON→XML移行」という変化が予告されています。これらが来るたびに `BankTransferService` の内部を書き換え、かつインターフェース `IBankService` を通じて呼び出し元に影響が及ぶリスクを考えると、案4の「仲介クラスが複雑な手順を完全に隠蔽する」構造が長期的には最もコスト効率が良いと判断します。

**採用する理由：** 銀行APIの複雑な手順を `BankServiceWindow` クラスという一つの窓口に閉じ込めることで、業務フロー側をシンプルに保ちつつ、将来的なAPIの仕様変更が業務ロジック全体に波及するリスクを最小化できるため、案4を採用します。

「銀行APIとのやり取りを一つの窓口クラス（`BankServiceWindow`）に集約する」この構造は、Facade（ファサード）パターンと呼ばれています。パターン名に倣い、以降ではこの窓口クラスを `BankFacade` と表記します。

仲介クラス（`BankTransferService`）がサブシステム群（`BankGateway`・`SecurityAuthenticator`）の複雑さを隠蔽し、呼び出し元にはシンプルな窓口だけを見せるこの構造が、Facadeパターンの本質です。「Facade（建物の正面）」という名前の通り、裏側にある複雑な配管や配線を見せず、綺麗な受付窓口だけを提供する役割を果たします。

---

### 6-10：耐久テスト

フェーズ2で挙がっていた「将来のリスク」をシミュレートします。

| **変更シナリオ** | **触る場所** | **コスト評価** |
| --- | --- | --- |
| 銀行側APIのJSON→XML移行計画が発生 | `BankTransferService` (内部の変換処理のみ) | 低 |
| 三段階認証へのフロー変更が発生 | `BankTransferService` (内部の手順のみ) | 低 |

今回の設計変更により、たとえ銀行側の認証やAPI形式がどれだけ複雑になろうとも、私たちの業務フロー側のクラス（`TransferProcessor`）を書き換える必要はなくなりました。「あのとき言っていた変化」が来たとしても、私たちはただ `BankTransferService` クラスだけを修正すればよいのです。

## 🟢 フェーズ7：対策実施 ―― 決断し、変化に強い設計を手に入れる

フェーズ6で採用した「窓口クラスの導入」を、実際のコードに実装します。これにより、銀行システムの詳細な通信手順を `BankTransferService` クラスという一つの窓口に閉じ込め、業務フローを記述する `TransferProcessor` から「銀行APIの具体的な使い方」という知識を追い出します。

この設計変更の最大の価値は、今後銀行側のAPI仕様がどれほど複雑になっても、業務フロー全体には一切影響を与えないという安定性を手に入れたことです。

### 7-1：解決後のコード（全体）

新しい設計では、銀行システムとのやり取りをすべて隠蔽する `BankTransferService` クラスを作成します。まずはサブシステム群（銀行APIと認証）から確認します。

```cpp
#include <iostream>
#include <string>
#include <vector>

// 銀行との通信を担うクラス（サブシステム1）
class BankGateway {
public:
    void verifyAccount(const std::string& account) {
        std::cout << "口座確認: " << account << "\n";
    }
    void checkBalance(const std::string& account) {
        std::cout << "残高確認\n";
    }
    void executeTransfer(const std::string& account, int amount,
                         const std::string& txId) {
        std::cout << "送金実行: " << amount << "円\n";
    }
};

// 認証を担うクラス（サブシステム2）
class SecurityAuthenticator {
public:
    void requestOTP() { std::cout << "認証コード発行\n"; }
    void verifyOTP(const std::string& token, const std::string& txId) {
        std::cout << "認証コード検証\n";
    }
};
```

このコードで分かること：`BankGateway` と `SecurityAuthenticator` はサブシステムとして独立しており、今後も銀行側の仕様変更に応じて変わり続けるクラスです。

次に、これらのサブシステムをすべて隠蔽するインターフェースと窓口クラスです。

```cpp
// 業務フロー側に見せる窓口（インターフェース）
class IBankTransferService {
public:
    virtual void performTransfer(
        const std::string& account, int amount,
        const std::string& otp) = 0;
};

// 銀行との複雑なやり取りを隠蔽する窓口（Facade実装）
class BankTransferService : public IBankTransferService {
private:
    BankGateway gateway;
    SecurityAuthenticator auth;
public:
    void performTransfer(
            const std::string& account, int amount,
            const std::string& otp) override {
        // 複雑な手順はすべてこの窓口の中に閉じる
        gateway.verifyAccount(account);
        gateway.checkBalance(account);
        auth.requestOTP();
        auth.verifyOTP(otp, "TXN12345"); // 内部的に取引IDを扱う
        gateway.executeTransfer(account, amount, "TXN12345");
    }
};
```

このコードで分かること：`BankTransferService` が `BankGateway` と `SecurityAuthenticator` の両方を内部に持ち、銀行APIとのやり取りを一手に引き受けています。呼び出し元はこの内部構造を知る必要がありません。

最後に、窓口だけを知る業務クラスと、組み立てを担う `BatchApplication` です。

```cpp
// 振り込み処理クラス：銀行の仕様を一切知らなくてよい
class TransferProcessor {
private:
    IBankTransferService* facade;
public:
    TransferProcessor(IBankTransferService* f) : facade(f) {}
    void transfer(
        const std::string& toAccount, int amount,
        const std::string& otp) {
        // 振り込みという業務プロセスに集中できる
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
    void processPayroll(
            const std::vector<std::pair<std::string, int>>& transfers) {
        for (const auto& [account, amount] : transfers) {
            facade->performTransfer(account, amount, "");
        }
    }
};

// 依存の組み立てを担うクラス（Composition Root）
class BatchApplication {
public:
    void run() {
        BankTransferService facade;
        TransferProcessor processor(&facade);
        processor.transfer("12345678", 5000, "999999");
    }
};

int main() {
    BatchApplication app;
    app.run();
    return 0;
}
```

このコードで分かること：`TransferProcessor` クラスの中から銀行特有の複雑な認証フローやAPI呼び出しの記述が消えました。このクラスは「窓口（`BankTransferService`）を使って送金を実行する」という業務上の責務に専念できるようになりました。

### 7-2：変更影響グラフ（改善後）

フェーズ3で確認したシナリオを再び当てはめてみます。

```mermaid
graph LR
    T1["認証フロー変更"] --> F1["BankTransferService.cpp<br>（窓口のみ）"]
    T1 -. "影響なし" .-> A["TransferProcessor.cpp ✅"]

```

→ **フェーズ3の変更影響グラフと比較して、銀行側の認証フロー変更という要求が、窓口クラスである `BankTransferService` クラスだけに閉じた設計になりました。**

### 7-3：変更シナリオ表

この設計で何を手に入れたかを確認します。

| **シナリオ** | **変わるクラス（触る場所）** | **変わらないクラス** |
| --- | --- | --- |
| 認証フローの変更 | `BankTransferService` | `TransferProcessor`, `BatchTransferService` |
| 送金APIのパラメータ追加 | `BankTransferService` | `TransferProcessor`, `BatchTransferService` |

変更が来ても、触るのは1クラスだけ——それがこの設計で手に入れたものです。諦めたものは、窓口となるクラスを1つ増やすという、わずかな実装の複雑さです。

---

### 7-4：接続形態の確認 ── この設計はどの接続か

フェーズ4-3で診断した通り、変更前のコードは **具体×直接** の状態でした。
採用した設計では、接続形態が **抽象×間接** へと変化しています。

**「抽象×間接」の証拠となるコード：**

```cpp
class TransferProcessor {
    // ← インターフェース型 = 「抽象」の証拠
    IBankTransferService* facade;
public:
    void transfer(const std::string& toAccount, int amount,
                  const std::string& otp) {
        // ← Facade経由 = 「間接」の証拠
        facade->performTransfer(toAccount, amount, otp);
    }
};
```

- メンバ変数 `facade` の型が `IBankTransferService*`（インターフェース）→ **「抽象」** の証拠
- `TransferProcessor` は `BankGateway` や `SecurityAuthenticator` を直接知らず、`BankTransferService` を経由して間接的に操作する → **「間接」** の証拠

「銀行APIの複雑さを知らせたくない・隠したい」という動機から、**抽象×間接** が選ばれました。

銀行システムという外部環境の変化に対して、私たちの業務ロジックを守り抜く。これこそが窓口クラスによるカプセル化の真骨頂です。


---

### 整理：7フェーズとこの章でやったこと

この章では、外部システム（銀行API）との複雑な連携が、私たちの業務ロジックをどれほど困難にしているかを学びました。7フェーズの思考プロセスを適用して、その構造的課題をどう解決したのかを振り返ります。

| **フェーズ** | **この章でやったこと** |
| --- | --- |
| 🔵 フェーズ1：現状把握 | 銀行APIの認証・送金手順が `TransferProcessor` クラスに直接記述されている現状を可視化しました。 |
| 🟣 フェーズ2：仮説立案 | ヒアリングを通じ、銀行側のAPI仕様が今後も繰り返し変わるリスクを特定しました。 |
| 🟣 フェーズ3：問題特定 | API仕様変更をシミュレーションし、業務フロー全体が破壊される「飛び火」という痛みを確認しました。 |
| 🟠 フェーズ4：原因分析 | 業務ロジックと外部システムの詳細な利用手順が密結合していることが原因だと言語化しました。 |
| 🟡 フェーズ5：課題定義 | 「接続点A」を外部システムとの窓口として定義し、業務フローから詳細を切り離す課題を設定しました。 |
| 🔴 フェーズ6：対策案検討 | 案1〜案4を比較し、複雑さを隠蔽する「窓口（Facade）」を採用しました。 |
| 🟢 フェーズ7：対策実施 | `BankFacade` クラスを導入し、`TransferProcessor` から直接的な依存を取り除きました。 |

### 各クラスの最終的な責任

今回の設計変更により、各クラスの責任は以下のように整理されました。

| **クラス名** | **責任（1文）** | **変わる理由** |
| --- | --- | --- |
| `TransferProcessor` | 振り込みという業務フローを進行する | 銀行との送金ルール（業務）が変わるとき |
| `BankTransferService` | 銀行APIの複雑な手順を窓口として隠蔽する | 銀行側のAPI仕様（通信手順やパラメータ）が変わるとき |
| `BankGateway` 他 | 外部システムと通信する詳細を担う | 通信プロトコルや認証方式が変わるとき |

> **このプロセスを回した結果にたどり着いた構造こそが Facade パターンです。**

---

### 振り返り：「この章を読むと得られること」は手に入ったか

| **得られること** | **この章のどこで示したか** |
| --- | --- |
| 1. 依存の広がりを識別 | フェーズ3の「変更影響グラフ」で、変更が全体に波及する様子を可視化したこと。 |
| 2. 接続形態の診断 | フェーズ4で、現在の密結合を「Lightning直差し」という比喩で診断したこと。 |
| 3. 構造改善の説明 | フェーズ7の「変更シナリオ表」で、Facadeの導入により影響が局所化されたこと。 |

---

### 振り返り：3つの設計原則はどう適用されたか

* **原則1「変わるものをカプセル化せよ」の現れ**
* **具体化された場所：** `BankTransferService` クラス
* **解説：** 銀行APIの複雑な手順という「頻繁に変わる詳細」を、`BankTransferService` の中に閉じ込めました。これにより、業務クラスは銀行APIの詳細を知る必要がなくなりました。


* **原則2「実装ではなくインターフェースに対してプログラムせよ」の現れ**
* **具体化された場所：** `TransferProcessor` が `IBankTransferService` を通して処理を依頼する構造
* **解説：** 業務クラスは「どのようなAPIか」ではなく、「振り込みを実行する（`performTransfer`）」という窓口のインターフェースに対して命令を送るようになりました。


* **原則3「継承よりコンポジションを優先せよ」の現れ**
* **具体化された場所：** `TransferProcessor` に `IBankTransferService` を持たせる構造
* **解説：** 継承を使って銀行機能を拡張するのではなく、コンポジションを用いることで、Facadeを切り替えたり、あるいは将来的なFacadeの増設にも容易に対応できるようになりました。



---

---

### あなたのコードで考えてみてください

この章で辿った思考プロセスを、あなた自身のコードに当てはめてみましょう。

1. **変動の兆候を探す：** あなたのコードに「外部APIやライブラリの呼び出し手順（認証→接続→送信→確認など）を、ビジネスロジックと同じ場所に書いている」箇所がありますか？
2. **変える理由を問う：** その外部APIのバージョンが変わったとき、修正が必要なファイルは何個ありましたか？理想的には1ファイルで済むはずです。
3. **知りすぎを測る：** ビジネスロジックのコードが、外部システムの「エラーコードの体系」や「接続パラメータの名前」を直接知っていますか？
4. **窓口を想像する：** もし「外部システムとのやりとりをすべて担う窓口クラス」を1つ置いたとすると、外部仕様が変わったときの修正はどこだけで完結するようになりますか？

### パターン解説：Facade パターン

Facadeパターンは、サブシステム（銀行APIなど）の一連のインターフェースに対する統合された窓口を提供し、サブシステムを使いやすくするパターンです。

#### パターンの骨格

Facadeは、サブシステムのクラス群を「Facadeクラス」で包み込み、クライアントに対してはシンプルな窓口を提供します。

```mermaid
classDiagram
    class Facade {
        +operation()
    }
    class SubsystemA {
        +doWork()
    }
    class SubsystemB {
        +doSomething()
    }
    Facade --> SubsystemA
    Facade --> SubsystemB

```

#### この章の実装との対応

```mermaid
classDiagram
    class BankTransferService {
        +performTransfer()
    }
    class BankGateway { ... }
    class SecurityAuthenticator { ... }
    BankTransferService --> BankGateway
    BankTransferService --> SecurityAuthenticator

```

`TransferProcessor` は `BankGateway` や `SecurityAuthenticator` を直接呼ぶ必要はなくなり、`BankTransferService` を通すことで、安全かつ単純に振り込み処理を行えるようになりました。

#### 使いどころと限界

* **使うと良い状況**：サブシステムが複雑で、クライアントが直接扱うには手順が多すぎる場合。または、サブシステムとクライアントの依存関係を減らしたい場合。
* **使わない方が良い状況**：サブシステムが十分に単純であり、Facadeを介すことでかえってコードが複雑になる場合。

【過剰コード：ただのラッパーに過ぎない例】

```cpp
// facadeを導入しても元のメソッドをそのまま呼ぶだけで
// 隠蔽の効果がない場合
class SimpleFacade {
    OriginalClass sub;
public:
    void doIt() { sub.doIt(); } // facadeの意味が薄い
};

```

### この章のまとめ

この章の冒頭で示した「得られること」4点を、あらためて確認します。

**得られること1**（依存の広がりの識別）：フェーズ1の責任チェック表を通じて、`TransferService` が銀行APIの個々の呼び出し手順をすべて直接知っている状態を確認しました。「依存の広がり」という観点で、変動箇所を探す視点が養われたはずです。

**得られること2**（痛みの発生源の判断）：フェーズ4で、外部APIの詳細な呼び出し手順を自社コードが直接知っている接続形態が、変更の痛みの根本原因だと診断しました。この診断ができると、なぜ銀行側の仕様変更が業務ロジック全体に波及するのかが接続の形から読めるようになります。

**得られること3**（複雑な呼び出し手順のカプセル化）：フェーズ7で、`BankTransferService` を挟んだことで呼び出し元のコードが大幅にシンプルになった構造を確認しました。「複雑な処理を一つの窓口の後ろに隠す」という手法が、チームのコードレビューで説明できる状態になったと思います。

**得られること4**（境界線の引き方）：フェーズ5の課題定義とフェーズ2のヒアリングを通じて、「どの範囲を窓口の後ろに隠すか」はビジネスの境界線と一致させるべきだという判断基準を体験しました。境界線の引き方は「実装の都合」ではなく「誰の判断で変わるか」で決めるという原則です。

振り込み処理というドメインを通じて、外部依存の管理という設計上の判断を体験できたのではないかと思います。この章で辿った7つのフェーズは、どんな現場のコードにも同じように使える思考の型です。
