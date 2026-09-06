#ifndef PAYMENTCALCULATOR_H_INCLUDED
#define PAYMENTCALCULATOR_H_INCLUDED

#include "Order.h"
#include "IDiscountRule.h"
#include "RuleSelector.h"

class PaymentCalculator {
private:
    const IDiscountRule& rule;
public:
    explicit PaymentCalculator(const IDiscountRule& r)
            : rule(r) {}

    int calculate(const Order& order) const {
        int subtotal = 0;

        for (const auto& item : order.items) subtotal +=
            item.price;
        return rule.apply(subtotal);
    }
};

class CartPreviewService {
private:
    CustomerDatabase& db;
    const RuleSelector& selector;
public:
    CartPreviewService(CustomerDatabase& db,
                       const RuleSelector& selector)
        : db(db), selector(selector) {}

    int getEstimatedTotal(
            const Order& order,
            const CampaignContext& context) const {
        if (!db.exists(order.customerId))
            throw std::invalid_argument("未登録の顧客IDです");
        if (order.items.empty())
            throw std::invalid_argument("注文が空です");

        const CustomerInfo customer = db.get(order.customerId);
        const IDiscountRule& rule =
            selector.select(customer.memberType, context);
        PaymentCalculator calculator(rule);

        return calculator.calculate(order);
    }
};

class CheckoutResultRenderer {
public:
    void showOrderResult(const CustomerInfo& customer,
                         const Order& order,
                         const CampaignContext& context,
                         int subtotal,
                         int finalPrice) {
        std::cout << customer.name << " さんの注文:";

        for (const auto& item : order.items) {
            std::cout << " " << item.name << " " << item.price
                      << "円";
        }

        std::cout << "\n  条件: 会員=" << customer.memberType
                  << ", キャンペーン="
          << (context.isActive(CampaignCode::RegularCampaign)
                      ? "あり" : "なし");
        std::cout << "\n  小計 " << subtotal
                  << "円 → 支払金額 " << finalPrice << "円\n";
    }
};

class OrderProcessor {
private:
    CustomerDatabase& db;
    CheckoutResultRenderer& renderer;
    const RuleSelector& selector;
public:
    OrderProcessor(CustomerDatabase& db,
                   CheckoutResultRenderer& renderer,
                   const RuleSelector& selector)
        : db(db), renderer(renderer), selector(selector) {}

    void process(const Order& order,
                 const CampaignContext& context) {
        if (!db.exists(order.customerId)) {
            std::cout << "エラー: 顧客ID " << order.customerId
                      << " は登録されていません\n";
            return;
        }

        if (order.items.empty()) {
            std::cout << "エラー: 注文が空です\n";
            return;
        }

        // 顧客情報の取得（実運用ではDB/API。接続失敗などに備える）
        CustomerInfo customer;
        try {
            customer = db.get(order.customerId);
        } catch (const std::exception&) {
            std::cout << "エラー: 顧客情報の取得に失敗しました\n";
            return;
        }

        const IDiscountRule& rule =
            selector.select(customer.memberType, context);
        PaymentCalculator calculator(rule);

        const int finalPrice = calculator.calculate(order);
        int subtotal = 0;
        for (const auto& item : order.items) {
            subtotal += item.price;
        }
        renderer.showOrderResult(customer, order, context,
                                 subtotal, finalPrice);
    }
};

#endif  // PAYMENTCALCULATOR_H_INCLUDED
