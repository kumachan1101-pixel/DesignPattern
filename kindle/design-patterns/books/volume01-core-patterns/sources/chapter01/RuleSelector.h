#ifndef RULESELECTOR_H_INCLUDED
#define RULESELECTOR_H_INCLUDED

#include "Order.h"
#include "IDiscountRule.h"
#include "Discounts.h"

class RuleSelector {
private:
    std::vector<std::reference_wrapper<
            const IDiscountRule>> rules;
public:
    void add(const IDiscountRule& rule) {
        rules.push_back(std::cref(rule));
    }

    const IDiscountRule& select(
            const std::string& memberType,
            const CampaignContext& context) const {
        // 競合方針は組み立て側の登録順で表す。
        // Selectorは個別条件を知らず、最初に一致したものを返す。
        for (const auto& registered : rules) {
            const IDiscountRule& rule = registered.get();

            if (rule.matches(memberType, context)) return rule;
        }

        throw std::logic_error("適用可能な割引ルールがありません");
    }
};

#endif  // RULESELECTOR_H_INCLUDED
