## 第7章 変わる通知先 ―― Observer パターン

―― 思考の型：一つの変化を、複数の相手にどう伝えるか

### この章の核心

**システム内で何かが起きたとき、その情報を必要としている相手が誰かを知りすぎていると、修正のたびに無関係なクラスまで変更することになる。**

---

### この章を読むと得られること

これまでの章では「何を変えるか」という変化を扱ってきました。この章の問いは方向が違います——「誰に伝えるか」です。在庫が変動したとき、通知先を増やすたびに在庫管理のコードを書き換えている——そんな設計の「伝言の密結合」が、この章のテーマです。

* **得られること1：** 「在庫の変動」という観点で、コードの変動箇所を識別できるようになる
* **得られること2：** 接続点（クラスとクラスのつなぎ目）が「具体×直接」（専用型のクラスを直接知っている状態）になっているクラスを見て、そこが変更の痛みの発生源だと判断できるようになる
* **得られること3：** 接続点の形を変えると変更がどのように局所化（変更の影響が1クラスだけで済む状態）されるかを、構造から説明できるようになる
* **得られること4：** 通知を送る側が通知先を具体的に知らなくても、動的に通知先を増やしたり減らしたりできる視点

## 🔵 フェーズ1：現状把握 ―― 変更が来る前にコードを把握する

### 1-1：システムの背景

このシステムは、あるアパレルメーカーの在庫管理システムを支える一部です。日々、全国の店舗から刻々と送られてくる売上データを受けて、倉庫にある在庫数を減らし、規定数を下回れば追加発注をかける、といった業務の流れを管理しています。

システムが立ち上がった当初は、在庫が減ったことを倉庫の担当者に「メール」で送るだけで十分でした。しかし、昨今のデジタル化の流れを受け、在庫状況をリアルタイムで「社内ダッシュボード」に反映させたり、在庫が少なくなったら「在庫担当者のチャット」に通知したりと、在庫の変動を追いかける相手がどんどん増えてきました。

コードを眺めてみると、在庫が減ったことを検知する InventoryManager クラスの中で、メール送信クラス、ダッシュボード更新クラス、チャット通知クラスといった、具体的な通知先クラスを直接呼び出す構成になっています。システムが小さかった頃は、これらすべてを InventoryManager が把握していても問題はありませんでした。

一見すると、このコードは処理が一つにまとまっており、何が起きているか非常に分かりやすく整理されているように見えます。このコードが今日までメーカーの在庫と店舗の円滑な連携を支えてきたことは確かです。

---

### 1-2：仕様表

読者の皆さんがコードを読む前に、このシステムが「現在何をしているのか」を一覧で整理しておきましょう。

| **機能名** | **担当クラス** | **入力** | **出力** |
| --- | --- | --- | --- |
| 在庫の減算 | InventoryManager | 商品ID(string), 数量(int) | 倉庫の在庫データベース更新 |
| 在庫減少の通知 | InventoryManager | なし（内部状態） | メール送信、ダッシュボード更新、チャット通知 |

---

### 1-3：クラス構成図

システムのクラス構成を可視化し、構造を確認します。

```mermaid
classDiagram
    class InventoryManager {
        -EmailNotifier email
        -DashboardUpdater dashboard
        -ChatNotifier chat
        +reduceStock(productId, quantity)
        -notifyAll(message)
    }
    class EmailNotifier {
        +send(message)
    }
    class DashboardUpdater {
        +update(message)
    }
    class ChatNotifier {
        +send(message)
    }
    InventoryManager --> EmailNotifier
    InventoryManager --> DashboardUpdater
    InventoryManager --> ChatNotifier

```

この図が示す通り、InventoryManager という単一のクラスが、通知先であるすべてのクラス（メール、ダッシュボード、チャット）を直接保持している構成になっています。

---

### 1-4：責任配置テーブル

各クラスが「何を知るべきか（責任）」を定義し、事実を確認します。

| **クラス名** | **責任（1文）** | **知るべきこと** |
| --- | --- | --- |
| InventoryManager | 在庫を減算し、関係者に通知する。 | 在庫数、在庫減少時の通知先クラスの実装。 |

この表から、InventoryManager が在庫管理という本来の責務に加えて、通知先クラスのインスタンス化や具体的な送信方法までを知っている状態が見て取れます。私自身、現場でこういうコードを見ると「このクラスは一体、何箇所に気を配ればいいのだろう…」と感じてしまうのですが、皆さんはいかがでしょうか。

---

### 1-5：依存グラフ

クラス間の「依存の方向」をマクロな視点で示します。

```mermaid
graph TD
    InventoryManager["InventoryManager"] --> EmailNotifier["EmailNotifier"]
    InventoryManager --> DashboardUpdater["DashboardUpdater"]
    InventoryManager --> ChatNotifier["ChatNotifier"]

```

InventoryManager に、通知先となるクラスが集中していることが分かります。

---

### 1-6：実装コード

それでは、実際にシステムを動かしているコードを見てみましょう。在庫が減った際に各通知先へメッセージを送る処理をシミュレートしています。

```cpp
#include <iostream>
#include <string>

using namespace std;

// 各通知先の具体的な実装
class EmailNotifier {
public:
    void send(string m) { cout << "Email: " << m << endl; }
};
class DashboardUpdater {
public:
    void update(string m) { cout << "Dashboard: " << m << endl; }
};
class ChatNotifier {
public:
    void send(string m) { cout << "Chat: " << m << endl; }
};

class InventoryManager {
private:
    EmailNotifier email;
    DashboardUpdater dashboard;
    ChatNotifier chat;

public:
    void reduceStock(string productId, int quantity) {
        cout << "商品 " << productId
             << " の在庫を " << quantity << " 減らしました。" << endl;
        
        // 在庫が減ったことを検知して通知する
        string message = "商品 " + productId + " の在庫が減少しました。";
        notifyAll(message);
    }

private:
    void notifyAll(string message) {
        // 通知先が増えるたびに、ここが修正される
        email.send(message);
        dashboard.update(message);
        chat.send(message);
    }
};

int main() {
    InventoryManager manager;
    manager.reduceStock("T-shirt-001", 5);
    return 0;
}

```

このコードを見ると、InventoryManager クラスがどの通知先クラスが存在し、どうやって通知を送るかをすべて直接知っていることが分かります。

---

### 1-7：実行結果

上記のコードを実行した結果は以下のようになります。

```text
商品 T-shirt-001 の在庫を 5 減らしました。
Email: 商品 T-shirt-001 の在庫が減少しました。
Dashboard: 商品 T-shirt-001 の在庫が減少しました。
Chat: 商品 T-shirt-001 の在庫が減少しました。

```

> このコードは正しく動く。これから変えていくのは「機能」ではなく「構造」だ。

---

### 1-8：責任チェック表

コードが実際に「知っていること」を一行ずつ照合し、その知識が誰の判断で変わるのかを観察します。

| **コードの行** | **持っている知識** | **管理者（観察）** |
| --- | --- | --- |
| email.send(message); | メール通知クラスの存在と送信方法 | 通知先を選定するシステム管理者 |
| dashboard.update(message); | ダッシュボードの存在と更新方法 | 画面表示を決めるUI担当者 |
| chat.send(message); | チャット通知クラスの存在と送信方法 | 連絡網を決めるチーム管理者 |

責任チェックで見えたことを散文で述べます。通知に関する処理が InventoryManager の中で直列に並んでいることが見えました。まだ「問題だ」と判定しませんが、通知先という「管理者が異なる知識」が同じ場所に並んでいることが見えた、という事実に留めておきます。

フェーズ1で責任配置の観察が終わりました。次のフェーズ2では、現場に届いた変更要求を起点にして「何が変わり、何が変わらないか」の仮説を立て、関係者とのヒアリングを通じてそれを確定させていきます。実装と責任が一致しない箇所こそが、のちの問題の発生源になります。

---

## 🟠 フェーズ2：仮説立案 ―― 変更要求を受けて、変動と不変を整理する

### 2-1：届いた変更要求

ある週の月曜日、店舗運営部の田中部長から、在庫管理システムの改善依頼がメールで届きました。

「在庫が少なくなった時に、倉庫担当者のスマホへSMS（ショートメッセージ）で直接通知を送れるようにしたいんだ。今はメールだけだから、どうしても確認が遅れて発注が漏れることがあってね。来月の店舗改装のタイミングで運用を変えたいから、なんとか対応してくれないか？」

なるほど、倉庫担当者のスマホへのSMS通知ですね。確かに、バックヤードで作業中の担当者にとって、メールよりも気づきやすい手段が必要というのは、現場のオペレーションとして非常に理にかなっています。

ただ、ふとあの `InventoryManager` クラスの通知処理を思い出しました。あのクラスは、各通知先クラスを個別に保持し、`notifyAll` メソッドの中でそれぞれの送信メソッドを直列に呼び出していました。このまま新しい `SMSNotifier` クラスを書き足すと、また通知ロジックが一つ増え、クラスの中が通知先の知識で溢れかえってしまいそうです。

### 2-2：変動・不変の仮説テーブル

フェーズ1での観察と、今回届いた変更要求を材料にして、「何が変わりそうで、何が変わらなそうか」の仮説を整理してみます。

| **分類** | **仮説** | **根拠（フェーズ1の観察から）** |
| --- | --- | --- |
| 🔴 **変動しそう** | 通知の種類（メール、チャット、ダッシュボード、SMS） | 1-8で、通知先ごとの知識が `notifyAll` に混在していると観察したため。 |
| 🔴 **変動しそう** | 新しい通知先の追加や、古い通知先の廃止 | 1-8で、通知先の管理者がバラバラであると観察したため。 |
| 🟢 **不変** | 「在庫が少なくなった」というイベント発生そのもののロジック | 商品の在庫を管理するというシステム本来の目的であり、通知の手段とは独立しているため。 |

コードを読んだだけで「ここは間違いなく変わる」「ここは絶対に変わらない」と自分一人で断定してしまうのは危険です。今の設計思想では、新しい通知先が増えるたびに `InventoryManager` 自体を書き換える必要があると読み取れますが、本当に将来もこのまま追加し続ける運用でよいのか、関係者に直接確認します。

### 2-3：関係者ヒアリング

仮説を携えて、店舗運営部の田中部長と開発チームのミーティングを行いました。チームで話し合う価値がある部分だと思います。

**開発者：** 「田中部長、SMS通知の件承知しました。一点確認ですが、今回のような新しい通知手段は、今後もキャンペーンや業務効率化のたびに追加されていく予定でしょうか？」

**田中部長：** 「そうなんだよ。次は店舗のバックヤードにある音声通知システムと連携したいという話もあってね。しばらくは、新しい通知方法がどんどん増えていくと思うよ。」

**開発者：** 「なるほど。通知手段の入れ替わりは激しそうですね。では、通知のタイミング（在庫が少なくなった瞬間など）といった『通知の基準』自体は今後も変わらないと考えてよいでしょうか？」

**田中部長：** 「ああ、そこは変わらないよ。あくまで『在庫が切迫した時』に知らせるというルール自体は固定だ。」

**開発者：** 「承知しました。通知手段（先）は頻繁に増減するけれど、通知の基準（トリガー）は安定しているということですね。」

ヒアリングの結果、通知先という変動要素が今後も際限なく増え続けることが確定しました。これまでのように `InventoryManager` に新しい通知先をハードコードし続けるのは、システムの拡張性として限界がきているようです。

> **現実のヒアリングでは——** このシナリオでは相手がちょうど設計に役立つ情報を教えてくれています。現実には「変わるかどうか分からない」「たぶん変わらない」という答えが返ることも多いです。そのときは、コードの変更履歴（`git log`）や過去の障害記録を「ヒアリングの代わり」として使ってみてください。「過去に何度変わったか」が、「将来変わりやすいか」の最も正直な証拠です。

### 2-4：確定した変動/不変テーブル

ヒアリング結果を反映し、今回の設計で対象とすべき変動・不変を確定させました。

| **分類** | **具体的な内容** | **変わるタイミング** | **根拠（誰との確認か）** |
| --- | --- | --- | --- |
| 🔴 **変動する** | 通知先となるクラスの種類とその実装 | 業務要件の変更があるたび | 田中部長との合意 |
| 🔴 **変動する** | 通知先の増減（動的な登録） | 随時 | 田中部長との合意 |
| 🟢 **不変** | 「在庫減少」というイベントの発生タイミング | 変わらない | ロジックの骨格として合意 |

通知先という「管理者が異なる知識」が今後も増え続けることが確定しました。今の `InventoryManager` クラスにこれ以上責任を背負わせるのは、そろそろ限界かもしれません。

フェーズ2で「通知手段の入れ替わりが激しい」という現状が確定しました。次のフェーズ3では、その要求を今のコードのままで変更しようとしたときに何が起きるか、実際に試みてみましょう。

---

## 🟡 フェーズ3：問題特定 ―― 変更を試みて、痛みを発見する

### 3-1：変更シミュレーション

田中部長からの「倉庫担当者のスマホへSMSで通知を送りたい」という要求を、今のコードで実装しようと試みます。

まず、SMSを送るための SMSNotifier クラスを新規作成します。次に、通知の中心である InventoryManager クラスを開き、新しく作成した SMSNotifier クラスのインスタンスをメンバ変数として追加します。
当然、コンストラクタでこの新しいクラスを初期化しなければなりません。さらに、肝心の通知ロジックである notifyAll メソッドの中にも、sms.send(message); という行を書き加える必要があります。

ここでふと、ある懸念が頭をよぎります。「この先、在庫通知の種類がもっと増えたらどうなるのだろう？」と。
メール、ダッシュボード、チャットに続き、SMS、そして先ほど部長が言及した音声通知まで増えれば、InventoryManager クラスの notifyAll メソッドには何十行もの通知処理が並ぶことになります。さらに、通知先クラスが一つ増えるたびに、InventoryManager のメンバ変数を書き換え、コンストラクタを修正し、notifyAll を書き換えるという、同じような「掃除」を何度も繰り返すことになるのです。

### 3-2：変更影響グラフ

変更を試みた結果、コード内の依存関係がどうなっているかを図にしてみます。

```mermaid
graph LR
    T1["変更要求：SMS通知の追加"] -->|"メンバ変数と通知ロジックの修正"| A["InventoryManager.cpp"]
    A -->|"新規クラス作成"| B["SMSNotifier.cpp"]

```

変更を加えるたびに InventoryManager が修正対象となり、通知先が増えるほど、このクラスが知るべき知識がどんどん増幅していく様子が見て取れます。

### 3-3：痛みの言語化

「また InventoryManager を書き換えなきゃいけないのか…」

変更を試みる中で、エンジニアとして感じる「痛み」がはっきりと形になってきました。

1つ目は、修正のたびに「通知の中心地」である InventoryManager が汚染されていくという辛さです。本来、通知のタイミング（在庫が切迫した瞬間）さえ分かれば良いはずなのに、通知先が何で、どうやって送るかという詳細までをこのクラスが握りしめています。結果として、通知先が増えるたびにこのクラスを修正し続けなければならず、コードがどんどん肥大化していきます。このクラスは「在庫管理」という本来の責務に集中できていません。

2つ目は、通知先と通知元が「運命共同体」になっているという辛さです。通知先が新しいクラスに変わったり、設定が変わったりするたびに、なぜか全く無関係な通知元の InventoryManager まで再コンパイルや修正の対象になります。この密な結合があるせいで、通知先を追加・削除するたびに「他にどこが壊れるんだろう？」と不安になりながらコードを触らなければなりません。

フェーズ3で「変更のたびに通知元クラスが書き換わる」という痛みが確認できました。次のフェーズ4では、この痛みの構造的な原因を、責任の境界や接続形態の観点から言語化していきます。

---

## 🔴 フェーズ4：原因分析 ―― 「なぜ辛いのか」を構造的に言語化する

### 4-1：観察→原因テーブル

フェーズ3で観察した「痛み」と、その根本にある構造的な原因を対応させてみます。

| **観察** | **原因の方向** |
| --- | --- |
| 新しい通知先を追加するたびに、通知元の InventoryManager クラスの修正が必要になる | InventoryManager が、通知すべき相手の「具体的なクラス名」と「通知方法」を直接知っているから |
| 通知先のクラスが変わったり増えたりするたびに、通知元クラスが影響を受ける | 在庫管理という「変わらないもの」と、通知先という「変わるもの」が、同じクラスの中に混在しているから |

こうして整理すると、問題の本質が見えてきます。通知元である InventoryManager は、「在庫が減った」という事実を伝えたいだけなのに、その情報を「誰が」「どう受け取るか」という詳細な実装までを全部抱え込んでしまっているのです。これでは、通知先が増えるたびにこのクラスを汚していくことになり、影響範囲が広がり続けるのは避けられません。

### 4-2：変わるもの / 変わらないものテーブル

原因の方向性が見えたところで、「変わり続けるもの」と「変わってほしくないもの」を明確に切り分けます。

| **変わり続けるもの（🔴）** | **変わってほしくないもの（🟢）** |
| --- | --- |
| 通知先のクラス（メール、ダッシュボード、チャット等）、その追加や削除、および具体的な通知手段 | 「在庫が少なくなった」というイベントの発生通知そのもの、およびそのトリガーとなる在庫管理ロジック |

「在庫が少なくなった」という出来事は、通知先が増えようが減ろうがシステムの中では等しく起きています。この「イベント発生の事実」こそが、変わってほしくないコア部分です。一方、通知先はビジネスの都合で今後も変動し続けます。この「変わる側」をうまく分離できれば、通知元は常に安定した状態を保てるはずです。

### 4-3：接続形態を診断する

現在のシステムがどのような接続形態にあるのか、2×2マトリクスを用いて診断してみます。

今の InventoryManager クラスは、通知先である EmailNotifier や ChatNotifier といった具体的なクラスを直接インポートして、メソッドを直接呼び出しています。これをケーブルの比喩で例えるなら、Lightningケーブルで直差しの状態（具体×直接）だと言えます。

通知先の機能（機器）を、通知元のクラス（iPhone本体）に直接ケーブルでつないでいるような状態です。新しい通知先を追加しようとすれば、本体の回路をわざわざ開いて新しい差込口をはんだ付けし直すような大工事が必要になります。これでは、通知先が増えるたびに通知元のクラスが修正され、影響が飛び火するのは当然です。

|  | 直接（直差し） | 間接（アダプター経由） |
|:---:|:---|:---|
| **具体**（専用規格） | **← 現在地**　iPhone → [Lightning] → Apple純正ドック（Lightning端子） | iPhone → [Lightning] → [変換] → USB-A充電器（汎用端子） |
| **抽象**（汎用規格） | MacBook → [USB-C] → USB-C対応モニター（汎用端子） | MacBook → [USB-C] → [ハブ] → HDMI・USB-A・LAN |

このコードで言うと：

| ケーブル比喩 | コードの対応箇所 |
|---|---|
| 「具体」＝専用規格ケーブル | `EmailNotifier email;` / `DashboardUpdater dashboard;` / `ChatNotifier chat;` — 3つの通知先クラスを具体名で `InventoryManager` のメンバとして直接宣言している |
| 「直接」＝直差し | `email.send(message); dashboard.update(message); chat.send(message);` — インターフェースや登録リストを介さず、`notifyAll()` 内で3つを直接呼び出している |

現状の InventoryManager と各通知先は、その「変わる理由」が異なるため、このまま密接に接続させておくべきではありません。両者を切り離し、疎な関係にするべきだと判断できます。

フェーズ4で根本原因が言語化できました。次のフェーズ5では、解決すべき問題を具体的に定めます。


---

## 🟣 フェーズ5：課題定義 ―― 解くべき問題を具体的に定める

フェーズ4で、「通知元クラス（`InventoryManager`）が通知先クラスの具体名を知りすぎている」という構造の問題を特定しました。しかし、単に「分ける」と決めただけでは、どのように分けるべきかという指針がまだ定まっていません。

ここで、解くべき課題を4つの視点で具体化し、対策案を検討するための土台を作ります。

### 5-1：接続点の特定

フェーズ4の分析から、`InventoryManager` と各通知先の間には、以下のような接続点（ジョイント）が存在することが分かります。

* 接続点A：`InventoryManager` ←→ `EmailNotifier` の境界
* 接続点B：`InventoryManager` ←→ `DashboardUpdater` の境界
* 接続点C：`InventoryManager` ←→ `ChatNotifier` の境界

合計で3つの接続点が存在します。通知先が増えるたびにこの境界線が増えていくことが、これまで私たちが直面してきた「grep地獄」や「影響範囲の拡大」の直接的な原因です。これらの接続点を、個別の具体クラスから切り離すことが今回の重要な課題です。

### 5-2：非機能制約の確認

接続の形を設計するにあたって、システム上の制約を確認しておきます。

| **確認項目** | **内容** | **この章での判断** |
| --- | --- | --- |
| 変更頻度 | この接続点はどのくらいの頻度で変わるか | 高（通知先の増減が頻繁に発生する） |
| パフォーマンス | ホットパスか（高頻度で呼ばれるか） | いいえ（在庫減少は重要だが、即時性を過度に問うホットパスではない） |
| 通知遅延 | 在庫変動イベントが多発する場合、全通知先への配信に遅延が出るか | 要確認（セール期間中に在庫が短時間で急減すると、通知先が数十のシステムに連鎖イベントが発生する。同期通知では呼び出し元がすべての通知完了を待つ設計になり、処理時間が増大する） |
| メモリ | 間接層の追加でオーバーヘッドが問題になるか | いいえ（通知先の数は限定的で、メモリへの影響は軽微） |

通常の在庫変動イベントではパフォーマンス上の問題はありません。ただし、セール期間中に在庫が急変動すると、通知先の数に比例して処理時間が増大します。通知先の増加を見越した設計において、この点は接続形態の選択に影響します。

### 5-3：クライアントへの影響範囲

分離対象である通知先クラスを呼び出しているのは、`InventoryManager` クラスそのものです。したがって、ここでの「クライアント」は `InventoryManager` になります。

接続点の形を変えるということは、`InventoryManager` の `notifyAll` メソッド周辺のコードを大幅に書き換えることを意味します。このクラスは通知ロジックの心臓部にあたるため、ここをリファクタリングして「通知先を意識しなくていい構造」に作り変えることは、今後の変更耐性を大きく左右する重要な修正になります。

### 5-4：課題まとめ表

これまでの情報を一覧に整理します。

| **接続点** | **分けた理由** | **非機能制約** | **クライアント影響** |
| --- | --- | --- | --- |
| 接続点A〜C | 通知先が頻繁に変わるため、通知元と通知先を疎結合にしたい | 通常は低頻度・セール時にイベントが集中し通知先数に比例して処理時間増大 | `InventoryManager` の通知ロジックに影響 |

この表から、私たちの目指すべき方向性が明確になりました。通知先が何であろうと、`InventoryManager` はその詳細を知らずに「通知を送る」という行為だけを行えるようにすればよいのです。

フェーズ5で「何を解くか」が確定しました。次のフェーズ6では、この課題に対してどのような構造を導入すべきか、コストと将来性を見極めて対策案を検討します。

## 🟢 フェーズ6：対策案検討 ―― 解決策を並べ、コストで選ぶ

変更要求に対する解決策を、接続形態（具体・抽象 × 直接・間接）の観点から5つの案として整理しました。どの案にも一長一短があります。開発の文脈に応じて、最適な選択肢を冷静に見極めていきましょう。

### 6-1：接続の形 2×2マトリクス

現在の接続形態（Lightning直差し＝具体×直接）から、通知の柔軟性を高めるためにどの方向へ移動すべきかを整理します。

| 接続形態 | ケーブル例 | 特徴 |
|:---:|:---|:---|
| **具体×直接**（← 現在地） | iPhone → [Lightning] → Apple純正ドック（Lightning端子） | 専用端子のみ対応。差し替え不可 |
| **具体×間接** | iPhone → [Lightning] → [変換] → USB-A充電器（汎用端子） | 変換器を挟むが規格は専用のまま |
| **抽象×直接** | MacBook → [USB-C] → USB-C対応モニター（汎用端子） | どのメーカーでも同じ口で繋がる |
| **抽象×間接** | MacBook → [USB-C] → [ハブ] → HDMI・USB-A・LAN | ハブを介して多様な機器へ展開可能 |

---

#### 案0：現状維持 ―― 構造を変えない

**この形の考え方：**
クラスの分割も接続形態の変更もしない。既存の `notifyAll` メソッドの中に、新しい通知先への処理を `if` 文やメソッド呼び出しとして書き足す。将来的な通知先の増減が極めて稀で、工数を最小限に抑えたい場合に合理的な選択。

**構造図：**

```mermaid
graph LR
    IM["InventoryManager"]
    OFS["OrderFulfillmentService"]
    EN["EmailNotifier"]
    DU["DashboardUpdater"]
    CN["ChatNotifier"]
    IM -->|"具体×直接"| EN
    IM -->|"具体×直接"| DU
    IM -->|"具体×直接"| CN
    OFS -->|"具体×直接"| EN
    OFS -->|"具体×直接"| DU
    OFS -->|"具体×直接"| CN
    style EN fill:#ffeecc,stroke:#cc8800
    style DU fill:#ffeecc,stroke:#cc8800
    style CN fill:#ffeecc,stroke:#cc8800
```

両呼び出し元がそれぞれ同じ具体通知クラスを個別に直接抱え込み、通知ロジックと通知先の知識が両方に重複して存在している。

【コード例】

```cpp
// 呼び出し元1：在庫変動を管理するクラス
class InventoryManager {
    EmailNotifier email;
    DashboardUpdater dashboard;
    ChatNotifier chat;
public:
    void reduceStock(string productId, int quantity) {
        string message = "商品 " + productId + " の在庫が減少しました。";
        // ← 具体：通知先クラスを直接呼び出している
        email.send(message);
        dashboard.update(message);
        chat.send(message);
    }
};

// 呼び出し元2：出荷完了を管理するクラス
// ← 同じ通知ロジックをここにも丸ごと複製する（重複の発生）
class OrderFulfillmentService {
    EmailNotifier email;        // ← 同じ具体クラスをここでも直接保持
    DashboardUpdater dashboard;
    ChatNotifier chat;
public:
    void notifyShipped(string orderId) {
        string message = "注文 " + orderId + " が出荷されました。";
        // ← InventoryManagerと同じ通知ロジックがそのまま重複する
        email.send(message);
        dashboard.update(message);
        chat.send(message);
    }
};

```

このコードを見ると、`InventoryManager` と `OrderFulfillmentService` の両方が、同じ通知先クラスを個別に抱え込み、同じ通知ロジックを重複して持っていることが分かります。通知先が1つ増えれば、2つのクラスをそれぞれ修正しなければなりません。

**呼び出し側から見た違い（main() 例）：**

```cpp
// 案0（現状維持）の呼び出し側
int main() {
    // 在庫変動の呼び出し元
    InventoryManager manager;
    manager.reduceStock("T-shirt-001", 5); // ← 内部にEmailNotifierなどが直書き

    // 出荷完了の呼び出し元
    OrderFulfillmentService fulfillment;
    fulfillment.notifyShipped("ORDER-001"); // ← 同じ通知ロジックが重複して存在
    return 0;
}
```

**動作図：**

```mermaid
sequenceDiagram
    participant main
    participant IM as InventoryManager
    participant OFS as OrderFulfillmentService
    participant EN as EmailNotifier
    participant DU as DashboardUpdater
    participant CN as ChatNotifier
    main->>IM: reduceStock("T-shirt-001", 5)
    Note over IM: 通知先クラスを内部に直接保持
    IM->>EN: email.send(message)
    EN-->>IM: 完了
    IM->>DU: dashboard.update(message)
    DU-->>IM: 完了
    IM->>CN: chat.send(message)
    CN-->>IM: 完了
    IM-->>main: 在庫更新完了
    main->>OFS: notifyShipped("ORDER-001")
    Note over OFS: ← 同じ通知先クラスを重複して保持・呼び出し
    OFS->>EN: email.send(message)
    EN-->>OFS: 完了
    OFS->>DU: dashboard.update(message)
    DU-->>OFS: 完了
    OFS->>CN: chat.send(message)
    CN-->>OFS: 完了
    OFS-->>main: 出荷通知完了
```

一文要約：通知先クラスが各呼び出し元の内部に直接ハードコードされているため、同じ通知ロジックが2か所で並行して走り、通知先が1つ増えれば両方を修正しなければならない。

**この形のトレードオフ：**

* 変更容易性：低（通知先が増えるたびに `InventoryManager` と `OrderFulfillmentService` の両方を修正する必要がある）
* テスト容易性：低（特定の通知だけをテストするための切り離しができない）
* 実装コスト：低（今のコードに1行足すだけ）

---

#### 案1：具体×直接 ―― クラスは分けるが参照は具体型のまま

**この形の考え方：**
通知ロジックを個別のクラスに切り出すが、通知元はそれらの「具体的なクラス」を直接メンバとして保持する。責務の分離は進むが、通知先クラスのインスタンスを直接管理し続けるため、通知先の増減による通知元の影響は避けられない。

**構造図：**

```mermaid
graph LR
    IM["InventoryManager"]
    OFS["OrderFulfillmentService"]
    EN["EmailNotifier"]
    CN["ChatNotifier"]
    IM -->|"具体×直接"| EN
    IM -->|"具体×直接"| CN
    OFS -->|"具体×直接"| EN
    OFS -->|"具体×直接"| CN
    style EN fill:#ffeecc,stroke:#cc8800
    style CN fill:#ffeecc,stroke:#cc8800
```

`InventoryManager` と `OrderFulfillmentService` の両方が同じ具体通知クラスへの直接依存を持ち、新しい通知先が増えるたびに両方の呼び出し元で修正が発生する。

【コード例】

```cpp
// 呼び出し元1：在庫変動を管理するクラス
class InventoryManager {
    // ← 具体：EmailNotifierという具体型を直接知っている
    EmailNotifier email;
    ChatNotifier chat;
public:
    void reduceStock(string productId, int quantity) {
        string message = "商品 " + productId + " の在庫が減少しました。";
        email.send(message); // ← 直接：具体クラスのメソッドを直接呼んでいる
        chat.send(message);
    }
};

// 呼び出し元2：出荷完了を管理するクラス
// ← 選択ロジック（どの具体クラスを使うか）がここでも重複する
class OrderFulfillmentService {
    EmailNotifier email;  // ← 同じ具体クラスをここでも直接インスタンス化
    ChatNotifier chat;
public:
    void notifyShipped(string orderId) {
        string message = "注文 " + orderId + " が出荷されました。";
        email.send(message); // ← どのクラスを選ぶかという判断がここでも重複
        chat.send(message);
    }
};

```

このコードを見ると、`InventoryManager` と `OrderFulfillmentService` の両方が「`EmailNotifier` と `ChatNotifier` を使う」という選択ロジックを各自で保持していることが分かります。通知先を1つ追加・変更するたびに、両方のクラスを修正する必要があります。

**呼び出し側から見た違い（main() 例）：**

```cpp
// 案1（具体×直接）の呼び出し側
int main() {
    // 在庫変動の呼び出し元：具体クラスを直接生成して渡す
    InventoryManager manager;
    manager.reduceStock("T-shirt-001", 5); // ← 内部で具体クラスが直接使われる

    // 出荷完了の呼び出し元：同様に具体クラスを直接使う
    OrderFulfillmentService fulfillment;
    fulfillment.notifyShipped("ORDER-001"); // ← 選択ロジックが重複して存在
    return 0;
}
```

**動作図：**

```mermaid
sequenceDiagram
    participant main
    participant IM as InventoryManager
    participant OFS as OrderFulfillmentService
    participant EN as EmailNotifier
    participant CN as ChatNotifier
    main->>IM: reduceStock("T-shirt-001", 5)
    Note over IM: EmailNotifier・ChatNotifier を直接保持
    IM->>EN: email.send(message)
    EN-->>IM: 完了
    IM->>CN: chat.send(message)
    CN-->>IM: 完了
    IM-->>main: 在庫更新完了
    main->>OFS: notifyShipped("ORDER-001")
    Note over OFS: ← 同じ具体クラスへの依存・選択ロジックが重複
    OFS->>EN: email.send(message)
    EN-->>OFS: 完了
    OFS->>CN: chat.send(message)
    CN-->>OFS: 完了
    OFS-->>main: 出荷通知完了
```

一文要約：クラスは分かれたが「どの具体クラスを使うか」という選択ロジックを両方の呼び出し元がそれぞれ保持しており、呼び出し経路が2本並んで重複している。

**この形のトレードオフ：**

* 変更容易性：低〜中（責務は分かれたが、通知先を変えるたびに `InventoryManager` と `OrderFulfillmentService` の両方の修正が必要）
* テスト容易性：低（具体クラスへの依存が強いため切り離せない）
* 実装コスト：中（切り出しの工数が発生する）

---

#### 案2：抽象×直接 ―― インターフェースを挟み、型だけで接続する

**この形の考え方：**
すべての通知先クラスに共通のインターフェース（契約）を持たせることで、通知元は「具体的な型」ではなく「インターフェース型」だけを知る状態にする。この構造を **Observer パターン** と呼ぶ。通知元はリストで通知先を管理し、実行時に通知先を登録・解除できる。

**構造図：**

```mermaid
graph LR
    main["main()"]
    IM["InventoryManager"]
    OFS["OrderFulfillmentService"]
    IN[/"INotification\n≪interface≫"/]
    EN["EmailNotifier"]
    main -->|"具体で生成"| EN
    main -->|"注入"| IM
    main -->|"注入"| OFS
    IM -->|"抽象×直接(注入)"| IN
    OFS -->|"抽象×直接(注入)"| IN
    EN -.->|"実装"| IN
    style main fill:#e8ffe8,stroke:#448844
    style IN fill:#cce8ff,stroke:#4488cc
    style EN fill:#ffeecc,stroke:#cc8800
```

`main()` だけが具体クラスを知り、`InventoryManager` と `OrderFulfillmentService` は `INotification*` のリストを保持するだけで具体的な通知クラスを一切知らずに済む。

【コード例】

```cpp
class INotification { // ← これを Observer パターンと呼ぶ
public:
    virtual ~INotification() = default;
    virtual void send(string m) = 0;
};

// 呼び出し元1：在庫変動を管理するクラス
class InventoryManager {
    // ← 抽象：INotification*型で受け取り、具体クラスを知らない
    vector<INotification*> observers;
public:
    void attach(INotification* o) { observers.push_back(o); }
    void reduceStock(string productId, int quantity) {
        string message = "商品 " + productId + " の在庫が減少しました。";
        for(auto* o : observers) o->send(message); // ← 直接：インターフェース経由で直接呼ぶ
    }
};

// 呼び出し元2：出荷完了を管理するクラス
// ← 同じインターフェース型を外から受け取るため、重複も密結合も生じない
class OrderFulfillmentService {
    vector<INotification*> observers; // ← 抽象：具体クラスを知らない
public:
    void attach(INotification* o) { observers.push_back(o); }
    void notifyShipped(string orderId) {
        string message = "注文 " + orderId + " が出荷されました。";
        for(auto* o : observers) o->send(message);
    }
};

```

このコードを見ると、`InventoryManager` も `OrderFulfillmentService` も、具体的な通知クラスを一切知らずに済んでいることが分かります。どのクラスを使うかは外側（呼び出し側）で決めてインターフェース経由で渡すだけです。

**呼び出し側から見た違い（main() 例）：**

```cpp
// 案2（抽象×直接）の呼び出し側
int main() {
    EmailNotifier email;    // ← 具体：呼び出し側だけが具体クラスを生成

    // 在庫変動の呼び出し元：インターフェース経由で注入
    InventoryManager manager;
    manager.attach(&email);
    manager.reduceStock("T-shirt-001", 5);

    // 出荷完了の呼び出し元：同じインターフェース経由で注入（重複なし）
    OrderFulfillmentService fulfillment;
    fulfillment.attach(&email); // ← 同じ具体クラスを共有することも可能
    fulfillment.notifyShipped("ORDER-001");
    return 0;
}
```

**この形のトレードオフ：**

* 変更容易性：中〜高（通知先の追加は通知元を触らずに登録処理だけで済む）
* テスト容易性：高（スタブをインターフェースに差し込める）
* 実装コスト：中（インターフェース定義と管理構造の導入が必要）

---

#### 案3：具体×間接 ―― 仲介クラスを置くが、具体型を知っている

**この形の考え方：**
`InventoryManager` と通知先の間に「通知マネージャー」を置く。`InventoryManager` は通知マネージャーだけを知り、通知マネージャーが通知先の具体型を管理する。

**構造図：**

```mermaid
graph LR
    IM["InventoryManager"]
    OFS["OrderFulfillmentService"]
    NM["NotificationManager"]
    EN["EmailNotifier"]
    SN["SlackNotifier"]
    EC["ERPConnector"]
    IM -->|"具体×間接"| NM
    OFS -->|"具体×間接"| NM
    NM -->|"具体×直接"| EN
    NM -->|"具体×直接"| SN
    NM -->|"具体×直接"| EC
    style NM fill:#ffffcc,stroke:#aaaa44
    style EN fill:#ffeecc,stroke:#cc8800
    style SN fill:#ffeecc,stroke:#cc8800
    style EC fill:#ffeecc,stroke:#cc8800
```

両呼び出し元は共有の `NotificationManager` だけを知り、複合条件付き通知ロジック（在庫ゼロはSlack優先など）が仲介役の一箇所に集約されている。

【コード例】

```cpp
#include <iostream>
#include <string>
using namespace std;

// 具体的な通知先クラス群
class EmailNotifier {
public:
    void send(string m) { cout << "Email: " << m << endl; }
};
class SlackNotifier {
public:
    void send(string m) { cout << "Slack緊急通知: " << m << endl; }
};
class ERPConnector {
public:
    void sync(string m) { cout << "ERP同期: " << m << endl; }
};

// ← 具体：NotificationManagerは各通知クラスの具体型を直接知っている
// ← 間接：呼び出し側はManagerのみ知り、内部のクラス群は見えない
class NotificationManager {
    EmailNotifier email;
    SlackNotifier slack;
    ERPConnector erp;
public:
    // 在庫ゼロ：Slack即時通知 + メール + ERP同期
    void notifyStockOut(string productId) {
        string msg = "【在庫ゼロ】商品 " + productId;
        slack.send(msg);     // ← 緊急度が高い場合はSlackを優先
        email.send(msg);
        erp.sync(msg);
    }
    // 在庫減少：メール通知 + ERP同期（Slackは不要）
    void notifyLowStock(string productId, int remaining) {
        string msg = "【在庫減少】商品 " + productId
                     + " 残り" + to_string(remaining) + "点";
        email.send(msg);
        erp.sync(msg);
    }
    // 出荷完了：ERP同期のみ
    void notifyShipped(string productId) {
        string msg = "【出荷完了】商品 " + productId;
        erp.sync(msg);
    }
};

// 呼び出し元1：在庫変動を管理するクラス
class InventoryManager {
    NotificationManager notifier; // ← 間接：具体通知クラスはManagerの中に隠れている
public:
    void reduceStock(string productId, int quantity, int remaining) {
        cout << "商品 " << productId
             << " の在庫を " << quantity << " 減らしました。" << endl;
        if (remaining == 0) {
            notifier.notifyStockOut(productId);
        } else {
            notifier.notifyLowStock(productId, remaining);
        }
    }
};

// 呼び出し元2：出荷完了を管理するクラス
class OrderFulfillmentService {
    NotificationManager notifier; // ← 同じNotificationManagerを使い回す
public:
    void completeShipment(string productId) {
        cout << "商品 " << productId << " の出荷が完了しました。" << endl;
        notifier.notifyShipped(productId);
    }
};
```

このコードを見ると、`NotificationManager` は依然として各通知クラスの具体型を知っており、通知先が増えればManagerの修正が必要です。しかし、「在庫ゼロはSlack即時通知、在庫減少はメール通知」のような複合条件と、`InventoryManager`（在庫変動）と `OrderFulfillmentService`（出荷完了）という複数の発行元が同じ通知ロジックを重複なく共有できる点に、この形の価値があります。

**呼び出し側から見た違い（main() 例）：**

```cpp
// 案3（具体×間接）の呼び出し側
int main() {
    // 在庫変動の呼び出し元
    InventoryManager invManager;
    // ← 間接：NotificationManagerが内部に隠れており呼び出し側には見えない
    invManager.reduceStock("T-shirt-001", 5, 0);  // 在庫ゼロ → Slack+Email+ERP
    invManager.reduceStock("Pants-002", 2, 3);     // 在庫減少 → Email+ERP

    // 出荷完了の呼び出し元
    OrderFulfillmentService fulfillment;
    // ← 同じ通知ロジックをOrderFulfillmentServiceも重複なく使える
    fulfillment.completeShipment("T-shirt-001");   // 出荷完了 → ERPのみ
    return 0;
}
```

**この形のトレードオフ：**

* 変更容易性：中（通知先増減の修正はマネージャーに閉じる）
* テスト容易性：中（マネージャーをスタブ化すれば通知元のテストは可能）
* 実装コスト：中（仲介クラスの作成が必要）

---

#### 案4：抽象×間接 ―― インターフェース＋仲介役を両立する

**この形の考え方：**
インターフェース（案2）と仲介役（案3）を組み合わせ、通知先を抽象化しつつ、仲介役（マネージャー）を通じて疎結合を維持する。通知元は「通知先リストを管理する抽象的なマネージャー」を知るだけという、極めて疎結合な構造。

**構造図：**

```mermaid
graph LR
    main["main()"]
    IM["InventoryManager"]
    OFS["OrderFulfillmentService"]
    INM[/"INotificationManager\n≪interface≫"/]
    NM["NotificationManager"]
    IN[/"INotification\n≪interface≫"/]
    EN["EmailNotifier"]
    main -->|"具体で生成"| NM
    main -->|"具体で生成"| EN
    main -->|"注入"| IM
    main -->|"注入"| OFS
    IM -->|"抽象×間接(注入)"| INM
    OFS -->|"抽象×間接(注入)"| INM
    NM -.->|"実装"| INM
    NM -->|"抽象×直接"| IN
    EN -.->|"実装"| IN
    style main fill:#e8ffe8,stroke:#448844
    style INM fill:#cce8ff,stroke:#4488cc
    style IN fill:#cce8ff,stroke:#4488cc
    style NM fill:#ffffcc,stroke:#aaaa44
    style EN fill:#ffeecc,stroke:#cc8800
```

`InventoryManager` と `OrderFulfillmentService` は `INotificationManager*` という抽象インターフェースしか知らず、具体的な実装の知識は `main()` の組み立て部分だけに閉じている。

【コード例】

```cpp
class INotificationManager { // ← 抽象：マネージャーのインターフェース
public:
    virtual ~INotificationManager() = default;
    virtual void sendAll(string m) = 0;
};

class NotificationManager : public INotificationManager {
    // ← 抽象：INotification*型で受け取り、具体実装を知らない
    // ← 間接：Managerを経由するため内部クラス群が見えない
    vector<INotification*> observers;
public:
    void addObserver(INotification* o) { observers.push_back(o); }
    void sendAll(string m) override {
        for(auto* o : observers) o->send(m);
    }
};

// 呼び出し元1：在庫変動を管理するクラス
class InventoryManager {
    INotificationManager* mgr; // ← 抽象：具体マネージャーを知らない
public:
    InventoryManager(INotificationManager* m) : mgr(m) {}
    void reduceStock(string productId, int quantity) {
        string message = "商品 " + productId + " の在庫が減少しました。";
        mgr->sendAll(message); // ← 間接：Managerを経由して通知
    }
};

// 呼び出し元2：出荷完了を管理するクラス
// ← 同じ抽象マネージャーを外から受け取るため、重複も密結合も生じない
class OrderFulfillmentService {
    INotificationManager* mgr; // ← 抽象：同じ抽象インターフェースで受け取る
public:
    OrderFulfillmentService(INotificationManager* m) : mgr(m) {}
    void notifyShipped(string orderId) {
        string message = "注文 " + orderId + " が出荷されました。";
        mgr->sendAll(message); // ← 間接：Managerを経由して通知
    }
};

```

このコードを見ると、`InventoryManager` も `OrderFulfillmentService` も、抽象マネージャーのインターフェースだけを知り、具体的な通知クラスについては何も知らなくて済んでいることが分かります。

**呼び出し側から見た違い（main() 例）：**

```cpp
// 案4（抽象×間接）の呼び出し側
int main() {
    EmailNotifier email;          // ← 具体：組み立て側だけが具体型を知る
    NotificationManager mgr;
    mgr.addObserver(&email);

    // 在庫変動の呼び出し元：抽象マネージャーのみ見えて具体実装は隠れる
    InventoryManager manager(&mgr);
    manager.reduceStock("T-shirt-001", 5);

    // 出荷完了の呼び出し元：同じ抽象マネージャーを共有（重複なし）
    OrderFulfillmentService fulfillment(&mgr);
    fulfillment.notifyShipped("ORDER-001");
    return 0;
}
```

**この形のトレードオフ：**

* 変更容易性：高（通知先も、通知元も、お互いを全く知らなくて済む）
* テスト容易性：高（マネージャーも各通知先も独立してテスト可能）
* 実装コスト：高（クラス数と層が増え、構造の理解にコストがかかる）

---

### 6-7：評価軸

対策案を比較するための「ものさし」を先に宣言します。全章で共通の3軸に加え、パフォーマンスへの影響をVETO（拒否権）として設定します。

| **評価軸** | **意味** | **ウェイト** |
| --- | --- | --- |
| 変更容易性 | 変更要求（通知先の増減）に対し、触る場所が最小で済むか | ×3 |
| テスト容易性 | 通知先をスタブ/モックに差し替えて通知元を独立してテストできるか | ×2 |
| 可読性 | インターフェースやマネージャーの導入による構造の理解コスト | ×1 |

> **注：** このウェイト（変更容易性×3など）は本書の例です。チームの変更頻度・テスト文化に合わせて、比較を始める前にチームで合意してください。スコアは「答えを決める計算式」ではなく、「チームの議論を整理する道具」です。

**採点基準（章共通）：**

| 点数 | 変更容易性 | テスト容易性 | 可読性 |
| --- | --- | --- | --- |
| 3 | 1クラス追加のみで完結 | スタブ1つで完全に切り離せる | クラス増なし・直感的に理解可能 |
| 2 | 2〜3クラスの修正が必要 | 一部スタブが必要だが可能 | クラス1〜2個増・標準的な構造 |
| 1 | 4クラス以上の波及 | 実装に強く依存し困難 | インターフェースや中間層が複雑に増殖 |

**パフォーマンスの VETO 判定：**
フェーズ5の課題定義で、本システムの通知処理は「ホットパスではない」と判断されました。したがって、今回の比較においてパフォーマンスによる足切りは行わず、スコアリングを優先して最適な構造を選定します。

---

### 6-8：コスト天秤

5つの案を、現在の実装コストと、将来発生する変更コストの観点で比較します。

| **案** | **現在の対応コスト** | **未来の対応コスト** |
| --- | --- | --- |
| 案0：構造を変えない | 低 | 高 |
| 案1：具体×直接 | 低〜中 | 高 |
| 案2：抽象×直接 | 中 | 低〜中 |
| 案3：具体×間接 | 中 | 中 |
| 案4：抽象×間接 | 高 | 低 |

**ステップ1：採点表**

| 案 | 変更容易性（×3） | テスト容易性（×2） | 可読性（×1） |
| --- | --- | --- | --- |
| 案0：構造を変えない | 1 | 1 | 3 |
| 案1：具体×直接 | 1 | 2 | 3 |
| 案2：抽象×直接 | 3 | 3 | 2 |
| 案3：具体×間接 | 2 | 2 | 2 |
| 案4：抽象×間接 | 3 | 3 | 1 |

**ステップ2：加重合計表**

| 案 | 加重スコア | 判定 |
| --- | --- | --- |
| 案0 | 1×3＋1×2＋3×1＝8 |  |
| 案1 | 1×3＋2×2＋3×1＝10 |  |
| 案2 | 3×3＋3×2＋2×1＝17 | ← 採用候補 |
| 案3 | 2×3＋2×2＋2×1＝12 |  |
| 案4 | 3×3＋3×2＋1×1＝16 |  |

---

### 6-9：採用案の決定

**採用する案：** 案2（抽象×直接 ―― これを Observer パターンと呼ぶ）

**理由：**
未来のコストを最小化しつつ、現在の実装コストを許容範囲内に抑えるバランスが最も優れているためです。案4（抽象×間接）も高い将来性がありますが、今回のような通知管理であれば、案2の単純な登録・通知構造で十分目的を達成できると判断しました。

---

### 6-10：耐久テスト

フェーズ2のヒアリングで挙がった「将来の変更」に対し、案2で対応できるかテストします。

| **変更シナリオ** | **触る場所** | **コスト評価** |
| --- | --- | --- |
| 新しい通知先「音声通知システム」を追加する | `AudioNotifier` を作成し、`attach` するのみ | 低 |
| 既存の「ダッシュボード通知」を廃止する | `detach` を呼び出すのみ（クラスの削除は不要） | 低 |

案2を採用することで、通知元クラス（`InventoryManager`）のコードを一切変更することなく、安全に通知先の増減に対応できることが実証できました。

## 🟤 フェーズ7：対策実施 ―― 決断し、変化に強い設計を手に入れる

採用案である Observer パターンを実装し、通知元と通知先の依存関係を劇的に改善します。この設計によって、通知元の InventoryManager は「誰に通知するか」を一切知ることなく、「通知を送る」という自分の責務だけを果たすようになります。

### 7-1：解決後のコード（全体）

インターフェース INotification を定義し、通知先クラスがこれを実装するようにします。InventoryManager は INotification* のリストを管理するだけで済みます。

```cpp
#include <iostream>
#include <vector>
#include <string>
#include <algorithm>

using namespace std;

// 通知先が満たすべき契約（インターフェース）
class INotification {
public:
    virtual ~INotification() = default;
    virtual void send(string m) = 0;
};

// 具体的な通知先
class EmailNotifier : public INotification {
public:
    void send(string m) override { cout << "Email: " << m << endl; }
};

class ChatNotifier : public INotification {
public:
    void send(string m) override { cout << "Chat: " << m << endl; }
};

// ← 新しい通知先を追加する場合は、このクラスを1つ増やすだけ（ここだけ変わる）
class SMSNotifier : public INotification {
public:
    void send(string m) override { cout << "SMS: " << m << endl; }
};

// 通知元クラス
class InventoryManager {
private:
    vector<INotification*> observers; // ← 具体的な実装クラスを知らない

public:
    // 通知先の登録（ここだけ変わる）
    void attach(INotification* o) { observers.push_back(o); }

    void reduceStock(string productId, int quantity) {
        cout << "商品 " << productId
             << " の在庫を " << quantity << " 減らしました。" << endl;
        notifyAll("商品 " + productId + " の在庫が減少しました。");
    }

private:
    void notifyAll(string message) {
        // 通知先が何であれ、一律に通知を送る
        for (auto* o : observers) {
            o->send(message);
        }
    }
};

int main() {
    // 依存の組み立て（BatchApplication相当）
    InventoryManager manager;
    EmailNotifier email;
    ChatNotifier chat;
    SMSNotifier sms;

    manager.attach(&email);
    manager.attach(&chat);
    manager.attach(&sms); // ← 柔軟に通知先を追加可能

    manager.reduceStock("T-shirt-001", 5);
    return 0;
}

```

このコードにより、InventoryManager は通知先の具体的な実装に一切依存しなくなりました。新しい通知方法が増えても InventoryManager を修正する必要はありません。

### 7-2：変更影響グラフ（改善後）

フェーズ3で行った「SMS通知を追加する」という要求を、改善後の構造で見てみましょう。

```mermaid
graph LR
    T1["変更要求：SMS通知の追加"] --> F1["SMSNotifier.cpp（新規追加のみ）"]
    T1 -. "影響なし" .-> A["InventoryManager.cpp ✅"]
    T1 -. "影響なし" .-> B["EmailNotifier.cpp ✅"]

```

フェーズ3のグラフと比較して、新しい通知先の追加という要求が、新規クラスの作成と登録処理（attach）だけに閉じるようになりました。既存の通知元クラスや他の通知先クラスには一切影響が及んでいません。

### 7-3：変更シナリオ表

この設計で手に入れた「変更への耐性」を整理します。

| **シナリオ** | **変わるクラス（触る場所）** | **変わらないクラス** |
| --- | --- | --- |
| 新しい通知先「音声通知」を追加する | AudioNotifier（新規作成）、main（登録処理） | InventoryManager, EmailNotifier 等すべての既存クラス |
| 既存の「メール通知」を廃止する | main（登録処理を削除） | InventoryManager, EmailNotifier（クラス自体は残る） |
| 通知の基準を変更する | InventoryManager | INotification, 各通知先クラス |

変更が来ても、触るのは新規作成するクラスか、組み立てを行うコードだけ——それがこの設計で手に入れたものだ。諦めたものは、通知のたびにインターフェースを経由するというわずかな間接性と、Observerの登録・解除を管理するクラス数の増加だ。

---

### 7-4：接続形態の確認 ── この設計はどの接続か

フェーズ4-3で診断した通り、変更前のコードは **具体×直接** の状態でした。
採用した Observer パターンでは、接続形態が **抽象×直接（USB-C直差し）** へと変化しています。

**「抽象×直接」の証拠となるコード：**

```cpp
class InventoryManager {
    vector<INotification*> observers; // ← インターフェース型 = 「抽象」の証拠
public:
    void notifyAll(string message) {
        for (auto* o : observers) o->send(message); // ← 直接呼び出し = 「直接」の証拠
    }
};
```

- `vector<INotification*>` の要素型が `INotification*`（純粋仮想クラス）→ **「抽象」** の証拠（具体的な通知クラス名を知らない）
- `o->send(message)` は中間クラスを挟まない直接呼び出し → **「直接」** の証拠

「通知先を差し替えたい（Observer を自由に追加・変更したい）」という動機から、**抽象×直接** が選ばれました。

### 整理・振り返り・パターン解説

第7章の締めくくりとして、私たちが辿ってきた7フェーズの思考プロセスを振り返ります。このプロセスを意識的に回すことで、通知先のような「変動する相手」に対しても、依存を恐れずに設計できる力が身につくはずです。

#### 7フェーズとこの章でやったこと

| **フェーズ** | **この章でやったこと** |
| --- | --- |
| 🔵 フェーズ1：現状把握 | 在庫管理システムにおいて、通知元と複数の通知先クラスが密接に結合している構造を観察した。 |
| 🟠 フェーズ2：仮説立案 | 在庫通知の運用担当者へのヒアリングを通じ、通知先が今後も頻繁に入れ替わることを「変動要因」として確定した。 |
| 🟡 フェーズ3：問題特定 | 新しい通知手段を追加しようとすると、既存の通知元クラスを毎回修正しなければならないという「痛み」を確認した。 |
| 🔴 フェーズ4：原因分析 | 通知元が、通知先の具体的な実装を直接知っていることが、影響範囲を広げる根本原因だと特定した。 |
| 🟣 フェーズ5：課題定義 | ホットパスではないため間接層を許容し、通知元と通知先を疎結合にする接続形態を課題とした。 |
| 🟢 フェーズ6：対策案検討 | 案0〜案4を比較し、インターフェースを導入する Observer パターン構造（案2）を採用した。 |
| 🟤 フェーズ7：対策実施 | 通知元はインターフェースのリストを保持するだけに留め、通知先を動的に登録・解除できる構造を実現した。 |

#### 各クラスの最終的な責任

最終的なクラス構成は以下の通り整理されました。これにより、個別のクラスが特定の責任に集中できる体制が整いました。

| **クラス名** | **責任（1文）** | **変わる理由** |
| --- | --- | --- |
| `INotification` | 通知先が実装すべき通知受け取りの契約を提供する。 | なし（抽象） |
| `InventoryManager` | 在庫を減算し、登録された通知先にイベントを通知する。 | 在庫管理のビジネスルールが変わる場合 |
| `EmailNotifier` 他 | 通知を受け取り、個別の手段でメッセージを送信する。 | 各通知手段のプロトコル変更がある場合 |

> **このプロセスを回した結果にたどり着いた構造こそが Observer パターン です。**

#### 振り返り：「この章を読むと得られること」は手に入ったか

| **得られること** | **この章のどこで示したか** |
| --- | --- |
| 変動箇所の識別力 | フェーズ2の変動/不変テーブルで特定しました。 |
| 接続形態の診断力 | フェーズ4のケーブル比喩診断で明らかにしました。 |
| 構造改善の説明力 | フェーズ7の変更影響グラフ対比で証明しました。 |

#### 振り返り：3つの設計原則はどう適用されたか

* **原則1「変わるものをカプセル化せよ」の現れ**
* **具体化された場所：** 各通知先クラス（`EmailNotifier`, `ChatNotifier` など）
* **解説：** 送信という「変わる理由」を個別のクラスに分離し、具体的な実装を隠蔽しました。


* **原則2「実装ではなくインターフェースに対してプログラムせよ」の現れ**
* **具体化された場所：** `INotification` インターフェース
* **解説：** 通知元は具体的な通知先クラスを知らず、インターフェースを通じて通知を送るようになりました。


* **原則3「継承よりコンポジションを優先せよ」の現れ**
* **具体化された場所：** `InventoryManager` 内の `vector<INotification*>`
* **解説：** 継承階層で通知先を増やすのではなく、コンポジション（登録）によって動的に通知先を管理する構造にしました。



---

### あなたのコードで考えてみてください

この章で辿った思考プロセスを、あなた自身のコードに当てはめてみましょう。

1. **変動の兆候を探す：** あなたのコードに「ある処理が完了したとき、複数の箇所に通知や後処理を追加する必要があった」メソッドがありますか？
2. **変える理由を問う：** 通知先（ログ、メール、画面更新など）の増減は、誰の判断で決まりますか？その判断が通知元のコードに埋め込まれていませんか？
3. **結合の強さを測る：** 通知先を1つ追加するとき、通知元のクラスを直接書き換える必要がありますか？そのとき既存の通知ロジックが壊れる可能性はどのくらいですか？
4. **分けた後を想像する：** もし「通知元」と「通知先」が互いの具体クラスを知らなくて済むとしたら、新しい通知先の追加は何ファイルの変更で完結しますか？

---

### パターン解説：Observer パターン

Observer（観察者）という名の通り、あるオブジェクトの状態変化を、複数の「観察者」に自動的に通知する仕組みです。

#### パターンの骨格

「通知を送る側（Subject）」が「通知を受け取る側（Observer）」のリストを保持し、状態が変化したときに一斉に通知を送ります。

```mermaid
classDiagram
    class Subject {
        +attach(Observer)
        +notify()
    }
    class Observer {
        <<interface>>
        +update()
    }
    class ConcreteObserver {
        +update()
    }
    Subject o-- Observer
    Observer <|.. ConcreteObserver

```

#### この章の実装との対応

`InventoryManager` が `Subject`（通知を送る側）、`INotification` が `Observer`（抽象ロール）、`EmailNotifier` 等が `ConcreteObserver`（具象観察者）に対応します。

#### 使いどころと限界

* **使うと良い状況**：ある状態の変化を、複数の相手に即座に伝えたい場合。また、通知先が将来増えることが分かっている場合。
* **使わない方が良い状況**：通知先が全く変わらない場合。通知先が単一であり、処理の順序や確実性が強く求められるような同期処理には向かない場合があります。

【過剰コード：変化の予定がないものまでパターン化した例】

```cpp
// そもそも通知先がメール一択で、今後も増える予定がないなら、
// 複雑な登録リストを管理するObserverパターンは過剰です。

```

### この章のまとめ

接続点の形を「直差し」から「アダプター経由の抽象的な接続」に変えたことで、通知元は通知先の具体的な存在を知らずに済みます。これにより、通知先が増減しても通知元のコードは「閉じたまま（修正不要）」でいられるようになりました。</INotification*>