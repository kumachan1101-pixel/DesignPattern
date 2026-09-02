#ifndef ORDER_H_INCLUDED
#define ORDER_H_INCLUDED

#include <iostream>
#include <string>
#include <vector>
#include <functional>
#include <map>
#include <stdexcept>

namespace MemberType {
    const std::string Premium = "Premium";
    const std::string Regular = "Regular";
}

namespace CampaignCode {
    const std::string RegularCampaign = "REGULAR_CAMPAIGN";
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

struct CustomerInfo {
    std::string name;
    std::string memberType;
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

    bool exists(const std::string& id) const { return records.count(id) > 0; }
    CustomerInfo get(const std::string& id) const { return records.at(id); }
};

// 割引ルールの共通インターフェース（ルール差し替え構造）
// 支払計算の結果オブジェクト：小計・適用ルール名・支払金額

struct PaymentResult {
    int subtotal;
    int finalPrice;
    std::string appliedRule;
};

#endif  // ORDER_H_INCLUDED
