#include "InventoryApplication.h"


int main() {
    // mainは具体的な通知先や登録順を知らない
    InventoryApplication app;

    // PRD001: 在庫50、閾値10 → 5減らしても閾値超えのまま
    cout << "--- ケース1: 在庫が閾値を超えたまま減少（通知なし） ---" << endl;
    app.inventory().reduceStock("PRD001", 5);
    cout << endl;

    // PRD002: 在庫3、閾値5 → 最初から閾値以下。SMSは保留を返す
    cout << "--- ケース2: 在庫が閾値以下に減少"
            "（同期3件＋非同期SMS） ---" << endl;
    app.inventory().reduceStock("PRD002", 1);
    cout << endl;

    cout << "--- ケース2のコールバック模擬: SMS-1が配信完了 ---" << endl;
    app.smsDelivery().receive("SMS-1", true);
    cout << endl;

    cout << "--- ケース3: 在庫が補充された（閾値超え） ---" << endl;
    app.inventory().replenishStock("PRD001", 20);
    cout << endl;

    // PRD003: 在庫0 → 出庫エラー
    cout << "--- ケース4: 在庫0の出庫操作 ---" << endl;
    app.inventory().reduceStock("PRD003", 1);
    cout << endl;

    // ケース5: 存在しない商品IDのエラー確認
    cout << "--- ケース5: 存在しない商品IDを操作する ---" << endl;
    app.inventory().reduceStock("PRD999", 1);
    cout << endl;

    // ケース6: SMSを受付失敗する設定へ差し替え、部分失敗を確認する
    cout << "--- ケース6: SMSだけ受付失敗（部分失敗） ---" << endl;
    // 失敗動作の別構成も、具体通知の生成・登録は組み立て役へ任せる
    InventoryApplication failureApp(true);
    failureApp.inventory().reduceStock("PRD002", 1);

    cout << "--- ケース7: SMSを受け付ける ---" << endl;
    app.inventory().reduceStock("PRD002", 1);
    cout << "--- ケース7のコールバック模擬: SMS-2が配信失敗 ---" << endl;
    app.smsDelivery().receive("SMS-2", false);

    cout << endl;
    cout << "--- ケース8: 0個の補充を拒否する ---" << endl;
    app.inventory().replenishStock("PRD001", 0);

    return 0;
}
