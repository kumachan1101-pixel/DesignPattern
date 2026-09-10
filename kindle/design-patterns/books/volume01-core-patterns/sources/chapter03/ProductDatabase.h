#ifndef PRODUCTDATABASE_H_INCLUDED
#define PRODUCTDATABASE_H_INCLUDED

#include <iostream>
#include <vector>
#include <string>
#include <map>
#include <algorithm>
#include <stdexcept>

struct ProductInfo {
    std::string name;           // 商品名
    int    stock;          // 在庫数
    int    alertThreshold; // アラート閾値
};

// 商品マスタ（データ駆動バリデーション用）

class ProductDatabase {
private:
    std::map<std::string, ProductInfo> records;
public:
    ProductDatabase() {
        records["PRD001"] = {"ワイヤレスマウス", 50, 10};
        records["PRD002"] = {"USBハブ",           3,  5}; // 閾値以下
        records["PRD003"] = {"キーボード",         0,  5}; // 在庫なし
    }

    bool exists(const std::string& id) const {
        return records.count(id) > 0;
    }

    ProductInfo get(const std::string& id) const {
        return records.at(id);
    }

    void save(const std::string& id, const ProductInfo& info) {
        records[id] = info;           // 実行中の商品マスタへ追加
    }

    bool isBelowThreshold(const std::string& id,
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
    std::string channel;        // どの通知手段か
    std::string requestId;      // 非同期受付だけが設定する
};

// ログや結果で使う通知手段名を一か所に定義する

namespace ChannelName {
    const char* const EMAIL = "Email";
    const char* const DASHBOARD = "Dashboard";
    const char* const CHAT = "Chat";
    const char* const SMS = "SMS";
}

// 通知手段ごとに表現を変えるための、共通の在庫警告データ

struct StockAlert {
    std::string productId;
    std::string productName;
    int stock;
};

// 通知先が満たす必要がある契約（インターフェース）

// 非同期SMSの受付IDと最終配信状態を管理する

// 実運用でSMS基盤から後から届く結果の入口。在庫更新から独立させる

// 通知先1：メール通知（同期）
// メール基盤の呼び方（件名と本文、真偽値）は現状コードのまま変えない。
// 契約からその形へ変換する責任を、このクラスの中へ引き取る。

// 通知先2：ダッシュボード更新（同期）
// 画面更新は成否を返さない。その事実をどう契約へ写すかを、
// 通知元ではなくこのクラスが決める。

// 通知先3：チャット通知（同期）
// 空の投稿IDが失敗という約束も、このクラスの中で契約へ翻訳する。

// 新しい通知先の実装を追加し、組み立て側で登録する
// 通知先4：SMS通知（非同期。受付だけ返す）

// 通知元クラス（Subject に相当）

// 生成・所有・登録を一か所に閉じるアプリケーションの組み立て役

#endif  // PRODUCTDATABASE_H_INCLUDED
