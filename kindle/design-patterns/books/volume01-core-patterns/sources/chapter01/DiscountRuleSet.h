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
        ruleSelector.add(premium);           // Premiumは他施策と併用しない
        ruleSelector.add(summerAndCampaign); // 複合条件を単独条件より先にする
        ruleSelector.add(summer);
        ruleSelector.add(campaign);
        ruleSelector.add(none);              // 必ず一致するため最後にする
    }

    const RuleSelector& selector() const {
        return ruleSelector;
    }
};

#endif  // DISCOUNTRULESET_H_INCLUDED
