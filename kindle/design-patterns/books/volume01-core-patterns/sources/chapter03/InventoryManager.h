#ifndef INVENTORYMANAGER_H_INCLUDED
#define INVENTORYMANAGER_H_INCLUDED

#include "ProductDatabase.h"
#include "INotification.h"
#include "DeliveryStatusLog.h"

class InventoryManager {
private:
    // 非所有ポインタ。登録中の通知先はInventoryManagerより長く生存すること。
    vector<INotification*> observers;
    ProductDatabase&        db;
    DeliveryStatusLog&      deliveryStatusLog;

public:
    InventoryManager(ProductDatabase& database,
                     DeliveryStatusLog& statusLog)
        : db(database), deliveryStatusLog(statusLog) {}

    // nullと重複登録を拒否する
    bool attach(INotification* o) {
        if (o == nullptr) return false;

        if (find(observers.begin(), observers.end(), o)
                != observers.end()) {
            return false;
        }

        observers.push_back(o);

        return true;
    }

    // 破棄前や購読停止時に登録を解除する
    void detach(INotification* o) {
        observers.erase(
            remove(observers.begin(), observers.end(), o),
            observers.end());
    }

    void reduceStock(string productId, int quantity) {
        if (!db.exists(productId)) {
            cout << "[エラー] 商品ID " << productId
                 << " はマスタに存在しません。処理を中断します。"
                 << endl;
            return;
        }

        ProductInfo info = db.get(productId);

        if (quantity <= 0 || quantity > info.stock) {
            cout << "[エラー] 商品 " << productId
                 << " は " << quantity << " 個出庫できません。現在在庫: "
                 << info.stock << endl;
            return;
        }

        int before = info.stock;
        info.stock -= quantity;
        db.save(productId, info);
        cout << "商品 " << productId << "（" << info.name << "）"
             << " の在庫を " << quantity << " 減らしました。"
             << " 在庫: " << before
             << " -> " << info.stock << endl;

        if (db.isBelowThreshold(productId, info.stock)) {
            notifyAll({productId, info.name,
                       info.stock, info.alertThreshold});
        }
    }

    void replenishStock(string productId, int quantity) {
        if (!db.exists(productId)) {
            cout << "[エラー] 商品ID " << productId
                 << " はマスタに存在しません。処理を中断します。"
                 << endl;
            return;
        }

        ProductInfo info = db.get(productId);
        int before = info.stock;
        info.stock += quantity;
        db.save(productId, info);
        cout << "商品 " << productId << "（" << info.name << "）\n"
             << "  在庫を " << quantity
             << " 補充しました。在庫: " << before
             << " -> " << info.stock
             << "（通知なし）" << endl;
    }

private:
    // 各通知先の受付結果を集計する。通知先の種類ごとに分岐しない
    void notifyAll(const StockAlert& alert) {
        int accepted = 0, pending = 0, failed = 0;

        for (auto* o : observers) {
            DeliveryResult r = o->send(alert);
            deliveryStatusLog.record(r);

            if (r.status == ACCEPTED) {
                accepted++;
            } else if (r.status == PENDING) {
                pending++;
                cout << "  保留: " << r.channel
                     << " 受付ID=" << r.requestId << endl;
            } else {
                failed++;
                cout << "  失敗: " << r.channel << endl;
            }
        }

        cout << "[受付結果] 成功:" << accepted
             << " 保留:" << pending
             << " 失敗:" << failed << endl;
    }
};

#endif  // INVENTORYMANAGER_H_INCLUDED
