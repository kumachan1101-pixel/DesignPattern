#ifndef ORDER_H_INCLUDED
#define ORDER_H_INCLUDED

#include <iostream>
#include <string>
#include <vector>
#include <functional>
#include <map>
#include <stdexcept>

namespace MemberType {
    const std::string Premium = "Premium";  // 優待会員
    const std::string Regular = "Regular";  // 一般会員
}

// 開催中の施策を表すコード（入力と判定で同じ名前を使う）

namespace CampaignCode {
    // 通常キャンペーン
    const std::string RegularCampaign = "REGULAR_CAMPAIGN";
    // サマーセール
    const std::string SummerSale = "SUMMER_SALE";
}

class Item {
public:
    std::string name;
    int price;
    Item(std::string n, int p) : name(n), price(p) {}
};

class CampaignContext {
private:
    std::vector<std::string> activeCampaigns;
public:
    void activate(const std::string& code) {
        activeCampaigns.push_back(code);
    }

    bool isActive(const std::string& code) const {
        for (const auto& active : activeCampaigns) {
            if (active == code) return true;
        }

        return false;
    }
};

class Order {
public:
    std::string customerId;
    std::vector<Item> items;
};

// 顧客1件分の情報

struct CustomerInfo {
    std::string name;        // 顧客の氏名
    std::string memberType;  // 会員種別（MemberType の値）
};

// 金額計算の結果（小計と支払金額を一組で返す）

struct PaymentResult {
    int subtotal;    // 割引前の小計
    int finalPrice;  // 割引後の支払金額
};

class CustomerDatabase {
private:
    std::map<std::string, CustomerInfo> records;
public:
    CustomerDatabase() {
        records["C001"] = {"田中 一郎", "Premium"};
        records["C002"] = {"佐藤 花子", "Regular"};
        records["C003"] = {"鈴木 次郎", "Regular"};
    }

    bool exists(const std::string& id) const {
        return records.count(id) > 0;
    }
    CustomerInfo get(const std::string& id) const {
        return records.at(id);
    }
};

#endif  // ORDER_H_INCLUDED
