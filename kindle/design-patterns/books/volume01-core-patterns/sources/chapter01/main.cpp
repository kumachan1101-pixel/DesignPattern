#include "PaymentCalculator.h"


int main() {
    CustomerDatabase db;
    CheckoutResultRenderer renderer;

    DiscountRuleSet discountRules;

    OrderProcessor processor(db, renderer, discountRules.selector());
    CartPreviewService preview(db, discountRules.selector());

    // C001（Premium）/ キャンペーンなし / サマーセールなし → 20%引き
    std::cout << "--- 行1: Premium割引 ---\n";
    Order order1;
    order1.customerId = "C001";
    order1.items.push_back(Item("ワイヤレスイヤホン", 10000));
    CampaignContext context1;
    PaymentResult preview1 = preview.getEstimatedTotal(order1, context1);
    std::cout << "  カートプレビュー: "
              << preview1.finalPrice << "円\n";
    processor.process(order1, context1);

    // C001（Premium）/ キャンペーンあり / サマーセール中 → Premium優先
    std::cout << "\n--- 行2: Premium排他 ---\n";
    Order order2;
    order2.customerId = "C001";
    order2.items.push_back(Item("ワイヤレスイヤホン", 10000));
    CampaignContext context2;
    context2.activate(CampaignCode::RegularCampaign);
    context2.activate(CampaignCode::SummerSale);
    PaymentResult preview2 = preview.getEstimatedTotal(order2, context2);
    std::cout << "  カートプレビュー: "
              << preview2.finalPrice << "円\n";
    processor.process(order2, context2);

    // C002（Regular）/ キャンペーンあり / サマーセール中 → 逐次割引
    std::cout << "\n--- 行3: 逐次割引 ---\n";
    Order order3;
    order3.customerId = "C002";
    order3.items.push_back(Item("ワイヤレスイヤホン", 10000));
    CampaignContext context3;
    context3.activate(CampaignCode::RegularCampaign);
    context3.activate(CampaignCode::SummerSale);
    PaymentResult preview3 = preview.getEstimatedTotal(order3, context3);
    std::cout << "  カートプレビュー: "
              << preview3.finalPrice << "円\n";
    processor.process(order3, context3);

    // C002（Regular）/ サマーセールのみ → 5%引き
    std::cout << "\n--- 行4: サマーセール単独 ---\n";
    Order order4;
    order4.customerId = "C002";
    order4.items.push_back(Item("ワイヤレスイヤホン", 10000));
    CampaignContext context4;
    context4.activate(CampaignCode::SummerSale);
    PaymentResult preview4 = preview.getEstimatedTotal(order4, context4);
    std::cout << "  カートプレビュー: "
              << preview4.finalPrice << "円\n";
    processor.process(order4, context4);

    // C002（Regular）/ キャンペーンのみ → 10%引き（変更前と同じ）
    std::cout << "\n--- 行4b: キャンペーン単独 ---\n";
    Order order4b;
    order4b.customerId = "C002";
    order4b.items.push_back(Item("ワイヤレスイヤホン", 10000));
    CampaignContext context4b;
    context4b.activate(CampaignCode::RegularCampaign);
    PaymentResult preview4b = preview.getEstimatedTotal(order4b, context4b);
    std::cout << "  カートプレビュー: "
              << preview4b.finalPrice << "円\n";
    processor.process(order4b, context4b);

    // C003（Regular）/ 割引なし
    std::cout << "\n--- 行5: 割引なし ---\n";
    Order order5;
    order5.customerId = "C003";
    order5.items.push_back(Item("スマホケース", 3000));
    CampaignContext context5;
    PaymentResult preview5 = preview.getEstimatedTotal(order5, context5);
    std::cout << "  カートプレビュー: "
              << preview5.finalPrice << "円\n";
    processor.process(order5, context5);

    // エラー条件も、正常系と同じ最終コードで確認する
    std::cout << "\n--- 行6: 未登録顧客 ---\n";
    Order unknown;
    unknown.customerId = "UNKNOWN";
    unknown.items.push_back(Item("ケーブル", 1000));
    processor.process(unknown, context5);

    std::cout << "\n--- 行7: 空注文 ---\n";
    Order empty;
    empty.customerId = "C002";
    processor.process(empty, context5);

    return 0;
}
