#include "InventoryApplication.h"


int main() {
    // mainは具体的な通知先や登録順を知らない
    InventoryApplication app;

    // PRD001: 在庫50、閾値10 → 5減らしても閾値超えのまま
    std::cout
        << "--- ケース1: 在庫が閾値を超えたまま減少"
           "（通知なし） ---"
        << std::endl;
    app.inventory().reduceStock("PRD001", 5);
    std::cout << std::endl;

    // PRD002: 在庫3、閾値5 → 最初から閾値以下。SMSは保留を返す
    std::cout << "--- ケース2: 在庫が閾値以下に減少"
            "（同期3件＋非同期SMS） ---" << std::endl;
    app.inventory().reduceStock("PRD002", 1);
    std::cout << std::endl;

    std::cout
        << "--- ケース2のコールバック模擬: "
           "SMS-1が配信完了 ---"
        << std::endl;
    app.smsDelivery().receive("SMS-1", true);
    std::cout << std::endl;

    std::cout << "--- ケース3: 在庫が補充された（閾値超え） ---" << std::endl;
    app.inventory().replenishStock("PRD001", 20);
    std::cout << std::endl;

    // PRD003: 在庫0 → 出庫エラー
    std::cout << "--- ケース4: 在庫0の出庫操作 ---" << std::endl;
    app.inventory().reduceStock("PRD003", 1);
    std::cout << std::endl;

    // ケース5: 存在しない商品IDのエラー確認
    std::cout << "--- ケース5: 存在しない商品IDを操作する ---" << std::endl;
    app.inventory().reduceStock("PRD999", 1);
    std::cout << std::endl;

    // ケース6: SMSを受付失敗する設定へ差し替え、部分失敗を確認する
    std::cout << "--- ケース6: SMSだけ受付失敗（部分失敗） ---" << std::endl;
    // 失敗動作の別構成も、具体通知の生成・登録は組み立て役へ任せる
    InventoryApplication failureApp(true);
    failureApp.inventory().reduceStock("PRD002", 1);

    std::cout << "--- ケース7: SMSを受け付ける ---" << std::endl;
    app.inventory().reduceStock("PRD002", 1);
    std::cout
        << "--- ケース7のコールバック模擬: "
           "SMS-2が配信失敗 ---"
        << std::endl;
    app.smsDelivery().receive("SMS-2", false);

    std::cout << std::endl;
    std::cout << "--- ケース8: 0個の補充を拒否する ---" << std::endl;
    app.inventory().replenishStock("PRD001", 0);

    return 0;
}
