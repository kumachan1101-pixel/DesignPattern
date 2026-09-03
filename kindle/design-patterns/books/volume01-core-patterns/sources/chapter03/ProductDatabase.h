#ifndef PRODUCTDATABASE_H_INCLUDED
#define PRODUCTDATABASE_H_INCLUDED

#include <iostream>
#include <vector>
#include <string>
#include <map>
#include <algorithm>
using namespace std;

struct ProductInfo {
    string name;           // 商品名
    int    stock;          // 在庫数
    int    alertThreshold; // アラート閾値
};

// 商品マスタ（データ駆動バリデーション用）

class ProductDatabase {
private:
    map<string, ProductInfo> records;
public:
    ProductDatabase() {
        records["PRD001"] = {"ワイヤレスマウス", 50, 10};
        records["PRD002"] = {"USBハブ",           3,  5}; // 閾値以下
        records["PRD003"] = {"キーボード",         0,  5}; // 在庫なし
    }

    bool exists(const string& id) const {
        return records.count(id) > 0;
    }

    ProductInfo get(const string& id) const {
        return records.at(id);
    }

    void save(const string& id, const ProductInfo& info) {
        records[id] = info;           // 実行中の商品マスタへ追加
    }

    bool isBelowThreshold(const string& id,
                          int currentStock) const {
        return currentStock <= records.at(id).alertThreshold;
    }
};

// 通知の受付結果と、非同期SMSの最終配信結果
enum DeliveryStatus {
    ACCEPTED, PENDING, FAILED, DELIVERED, DELIVERY_FAILED
};

struct DeliveryResult {
    DeliveryStatus status; // 受付成功・保留・受付失敗・配信完了・配信失敗
    string channel;        // どの通知手段か
    string requestId;      // 非同期受付だけが設定する
};

// 通知手段ごとに表現を変えるための、共通の在庫警告データ

struct StockAlert {
    string productId;
    string productName;
    int stock;
    int threshold;
};

// 通知先が満たす必要がある契約（インターフェース）

struct StockEvent {
    std::string productId;
    std::string productName;
    std::string eventType;  // "入荷", "出荷", "閾値警告"
    int amount;
    int stockBefore;
    int stockAfter;
};

// 在庫変動ログを管理するクラス

class StockEventLog {
    std::vector<StockEvent> records;
public:
    void add(const std::string& productId,
             const std::string& productName,
             const std::string& eventType, int amount,
             int stockBefore, int stockAfter) {
        records.push_back({productId, productName, eventType,
                           amount, stockBefore, stockAfter});
    }

    void printAll() const {
        // 要求ID4：商品ID・変更前→変更後・単位をそろえて残す
        for (const auto& r : records) {
            std::cout << "[" << r.productId << "] "
                      << r.productName
                      << " " << r.eventType << " " << r.amount
                      << "個 (" << r.stockBefore << "->"
                      << r.stockAfter
                      << ")" << std::endl;
        }
    }

    int size() const { return (int)records.size(); }
};

// 非同期SMSの受付IDと最終配信状態を管理する

// SMS基盤から後日届くコールバックの入口。在庫更新から独立させる

// 通知先1：メール通知（同期）
// メール基盤の呼び方（件名と本文、真偽値）は1-4のまま変えない。
// 契約からその形へ変換する責任を、このクラスの中へ引き取る。

// 通知先2：ダッシュボード更新（同期）
// 画面更新は成否を返さない。その事実をどう契約へ写すかを、
// 通知元ではなくこのクラスが決める。

// 通知先3：チャット通知（同期）
// 空の投稿IDが失敗という約束も、このクラスの中で契約へ翻訳する。

// 新しい通知先の実装を追加し、組み立て側で登録する
// 通知先4：SMS通知（非同期。受付だけ返す）

// 通知元クラス（Subject に相当）

#endif  // PRODUCTDATABASE_H_INCLUDED
