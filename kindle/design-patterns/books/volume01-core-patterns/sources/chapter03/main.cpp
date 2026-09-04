#include "Notifiers.h"
#include "InventoryManager.h"


int main() {
    // 組み立て側が依存を生成・所有し、InventoryManagerへ注入・登録する
    ProductDatabase  productDatabase;
    StockEventLog    eventLog;
    DeliveryStatusLog deliveryStatusLog;
    SMSDeliveryCallback smsCallback(deliveryStatusLog);
    EmailNotifier    email;
    DashboardUpdater dashboard;
    ChatNotifier     chat;
    SMSNotifier      sms(false);   // false: 受付成功→保留を返す
    InventoryManager manager(productDatabase,
                             eventLog, deliveryStatusLog);

    manager.attach(&email);
    manager.attach(&dashboard);
    manager.attach(&chat);
    manager.attach(&sms);

    // PRD001: 在庫50、閾値10 → 5減らしても閾値超えのまま
    cout << "--- 行1: 在庫が閾値を超えたまま減少（通知なし） ---" << endl;
    manager.reduceStock("PRD001", 5);
    cout << endl;

    // PRD002: 在庫3、閾値5 → 最初から閾値以下。SMSは保留を返す
    cout << "--- 行2: 在庫が閾値以下に減少（同期3件＋非同期SMS） ---" << endl;
    manager.reduceStock("PRD002", 1);
    cout << endl;

    cout << "--- 行2の後日結果: SMS-1が配信完了 ---" << endl;
    smsCallback.receive("SMS-1", true);
    cout << endl;

    cout << "--- 行3: 在庫が補充された（閾値超え） ---" << endl;
    manager.replenishStock("PRD001", 20);
    cout << endl;

    // PRD003: 在庫0 → 出庫エラー
    cout << "--- 行4: 在庫0の出庫操作 ---" << endl;
    manager.reduceStock("PRD003", 1);
    cout << endl;

    // 行5: 存在しない商品IDのエラー確認
    cout << "--- 行5: 存在しない商品IDを操作する ---" << endl;
    manager.reduceStock("PRD999", 1);
    cout << endl;

    // 行6: SMSを受付失敗する設定へ差し替え、部分失敗を確認する
    cout << "--- 行6: SMSだけ受付失敗（部分失敗） ---" << endl;
    SMSNotifier smsFail(true);     // true: 受付失敗を返す
    manager.detach(&sms);
    manager.attach(&smsFail);
    manager.reduceStock("PRD002", 1);

    cout << "--- 行7: SMS受付後に最終配信失敗 ---" << endl;
    manager.detach(&smsFail);
    manager.attach(&sms);
    manager.reduceStock("PRD002", 1);
    smsCallback.receive("SMS-2", false);

    cout << "\n--- 行8: 在庫変動ログ ---\n";
    eventLog.printAll();

    return 0;
}
