#ifndef DISCOUNTRULESET_H_INCLUDED
#define DISCOUNTRULESET_H_INCLUDED

#include "Order.h"
#include "IDiscountRule.h"
#include "Discounts.h"
#include "RuleSelector.h"

class DiscountRuleSet {
private:
    PremiumDiscount premium;
    SummerSaleAndCampaignDiscount summerAndCampaign;
    SummerSaleDiscount summer;
    CampaignDiscount campaign;
    NoDiscount none;
    RuleSelector ruleSelector;
public:
    DiscountRuleSet() {
        // Premiumは他施策と併用しない
        ruleSelector.add(premium);
        ruleSelector.add(summerAndCampaign); // 複合条件を単独条件より先にする
        ruleSelector.add(summer);
        ruleSelector.add(campaign);
        ruleSelector.add(none);              // 必ず一致するため最後にする
    }

    // ルールの実体はこのクラスが所有し、Selectorはその参照だけを持つ。
    // コピーすると複製側のSelectorが元の実体を指したままになるため、禁じる。
    DiscountRuleSet(const DiscountRuleSet&) = delete;
    DiscountRuleSet& operator=(const DiscountRuleSet&) = delete;

    const RuleSelector& selector() const {
        return ruleSelector;
    }
};

#endif  // DISCOUNTRULESET_H_INCLUDED
