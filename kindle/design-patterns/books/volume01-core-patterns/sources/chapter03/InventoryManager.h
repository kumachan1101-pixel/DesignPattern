#ifndef INVENTORYMANAGER_H_INCLUDED
#define INVENTORYMANAGER_H_INCLUDED

#include "ProductDatabase.h"
#include "INotification.h"

class InventoryManager {
private:
    // 非所有ポインタ。登録中の通知先はInventoryManagerより長く生存すること。
    std::vector<INotification*> observers;
    ProductDatabase& db;

public:
    explicit InventoryManager(ProductDatabase& database)
        : db(database) {}

    // nullと重複登録を拒否する
    bool attach(INotification* o) {
        if (o == nullptr) return false;

        if (std::find(observers.begin(), observers.end(), o)
                != observers.end()) {
            return false;
        }

        observers.push_back(o);

        return true;
    }

    void reduceStock(std::string productId, int quantity) {
        if (!db.exists(productId)) {
            std::cout << "[エラー] 商品ID " << productId
                 << " はマスタに存在しません。処理を中断します。"
                 << std::endl;
            return;
        }

        ProductInfo info = db.get(productId);

        if (quantity <= 0 || quantity > info.stock) {
            std::cout << "[エラー] 商品 " << productId
                 << "（" << info.name << "）"
                 << " は " << quantity << " 個出庫できません。現在在庫: "
                 << info.stock << std::endl;
            return;
        }

        int before = info.stock;
        info.stock -= quantity;
        db.save(productId, info);
        std::cout << "商品 " << productId
             << "（" << info.name << "）"
             << " の在庫を " << quantity << " 減らしました。"
             << " 在庫: " << before
             << " -> " << info.stock << std::endl;

        if (db.isBelowThreshold(productId, info.stock)) {
            notifyAll({productId, info.name, info.stock});
        }
    }

    void replenishStock(std::string productId, int quantity) {
        if (!db.exists(productId)) {
            std::cout << "[エラー] 商品ID " << productId
                 << " はマスタに存在しません。処理を中断します。"
                 << std::endl;
            return;
        }

        ProductInfo info = db.get(productId);

        if (quantity <= 0) {
            std::cout << "[エラー] 商品 " << productId
                 << "（" << info.name << "） は " << quantity
                 << " 個補充できません。現在在庫: "
                 << info.stock << std::endl;
            return;
        }

        int before = info.stock;
        info.stock += quantity;
        db.save(productId, info);
        std::cout << "商品 " << productId
             << "（" << info.name << "）\n"
             << "  在庫を " << quantity
             << " 補充しました。在庫: " << before
             << " -> " << info.stock
             << "（通知なし）" << std::endl;
    }

private:
    // 各通知先の受付結果を集計する。通知先の種類ごとに分岐しない
    void notifyAll(const StockAlert& alert) {
        int accepted = 0, pending = 0, failed = 0;

        for (auto* o : observers) {
            DeliveryResult r = o->send(alert);

            if (r.status == ACCEPTED) {
                accepted++;
            } else if (r.status == PENDING) {
                pending++;
                std::cout << "  保留: " << r.channel
                     << " 受付ID=" << r.requestId << std::endl;
            } else {
                failed++;
                std::cout << "  失敗: " << r.channel << std::endl;
            }
        }

        std::cout << "[受付結果] 成功:" << accepted
             << " 保留:" << pending
             << " 失敗:" << failed << std::endl;
    }
};

#endif  // INVENTORYMANAGER_H_INCLUDED
